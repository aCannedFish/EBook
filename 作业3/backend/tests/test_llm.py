"""模型客户端与离线替身模型的测试。"""

from __future__ import annotations

import io
import json
import urllib.error

import pytest

from backend.config import LLM, EmbeddingSettings, LLMSettings
from backend.llm import (
    HttpChatClient,
    LocalReActLLM,
    ModelAPIError,
    broaden_book_arguments,
    build_client,
    build_plan,
    classify_clause,
    explain_http_error,
    simplify_policy_question,
    split_clauses,
)


class TestHttpErrorExplanation:
    @pytest.mark.parametrize(
        ("status", "expected"),
        [
            (404, "LLM_BASE_URL"),
            (401, "LLM_API_KEY"),
            (403, "权限"),
            (429, "限流"),
            (503, "服务商侧错误"),
            (418, "配置"),
        ],
    )
    def test_status_codes_map_to_actions(self, status, expected):
        error = explain_http_error(status, "https://example.com/v1/chat/completions", "boom")
        assert expected in error.hint
        assert error.report.startswith(f"模型接口返回 {status}")

    def test_message_includes_detail(self):
        error = explain_http_error(400, "http://x/v1/chat/completions", "bad request")
        assert "bad request" in str(error)


class TestClientConstruction:
    def test_requires_api_key(self):
        with pytest.raises(RuntimeError):
            build_client(LLMSettings("http://x/v1", "", "m", 5.0, 0.2))

    @pytest.mark.parametrize("sdk_available", [True, False])
    def test_builds_with_key(self, sdk_available):
        """装了 openai SDK 走 SDK，没装则退回标准库实现 —— 两条路径都要能构造。"""
        if not sdk_available:
            import builtins

            real_import = builtins.__import__

            def blocked(name, *args, **kwargs):
                if name == "openai":
                    raise ImportError("blocked for test")
                return real_import(name, *args, **kwargs)

            builtins.__import__ = blocked
            try:
                assert isinstance(build_client(LLMSettings("http://x/v1", "k", "m", 5.0, 0.2)), HttpChatClient)
            finally:
                builtins.__import__ = real_import
        else:
            assert build_client(LLMSettings("http://x/v1", "k", "m", 5.0, 0.2)) is not None

    def test_endpoint_and_normalization(self):
        assert LLM.endpoint.endswith("/chat/completions")
        settings = EmbeddingSettings("offline", "http://x/v1", "", "m", 0, 8, 5.0)
        assert settings.remote_ready is False


class TestHttpChatClient:
    def test_request_body_includes_stop_and_model(self, monkeypatch):
        captured = {}

        def fake_urlopen(request, timeout=None):
            captured["body"] = json.loads(request.data.decode("utf-8"))
            captured["url"] = request.full_url
            captured["auth"] = request.headers.get("Authorization")
            return io.BytesIO(
                json.dumps({"choices": [{"message": {"content": "Thought: ok"}, "finish_reason": "stop"}]}).encode()
            )

        monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
        client = HttpChatClient(LLMSettings("http://x/v1", "secret", "deepseek-chat", 5.0, 0.2))
        text = client.generate([{"role": "user", "content": "hi"}], stop=["\nObservation:"])

        assert text == "Thought: ok"
        assert captured["url"] == "http://x/v1/chat/completions"
        assert captured["auth"] == "Bearer secret"
        assert captured["body"]["stop"] == ["\nObservation:"]
        assert captured["body"]["model"] == "deepseek-chat"

    def test_tools_are_omitted_when_stop_only(self, monkeypatch):
        captured = {}

        def fake_urlopen(request, timeout=None):
            captured["body"] = json.loads(request.data.decode("utf-8"))
            return io.BytesIO(json.dumps({"choices": [{"message": {"content": ""}}]}).encode())

        monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
        client = HttpChatClient(LLMSettings("http://x/v1", "k", "m", 5.0, 0.2))
        client.generate([{"role": "user", "content": "hi"}])
        assert "stop" not in captured["body"]

    def test_http_error_is_translated(self, monkeypatch):
        def fake_urlopen(request, timeout=None):
            raise urllib.error.HTTPError("http://x/v1/chat/completions", 404, "Not Found", {}, io.BytesIO(b'{"detail":"Not Found"}'))

        monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
        client = HttpChatClient(LLMSettings("http://x/v1", "k", "m", 5.0, 0.2))
        with pytest.raises(ModelAPIError) as error:
            client.generate([{"role": "user", "content": "hi"}])
        assert "LLM_BASE_URL" in error.value.hint

    def test_connection_error_is_translated(self, monkeypatch):
        def fake_urlopen(request, timeout=None):
            raise urllib.error.URLError("connection refused")

        monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
        client = HttpChatClient(LLMSettings("http://x/v1", "k", "m", 5.0, 0.2))
        with pytest.raises(ModelAPIError) as error:
            client.generate([{"role": "user", "content": "hi"}])
        assert "无法连接" in str(error.value)


class TestIntentPlanning:
    def test_split_clauses_handles_conjunctions(self):
        clauses = split_clauses("我想买一本微服务的书，另外拆了塑封还能退吗？运费谁出")
        assert clauses == ["我想买一本微服务的书", "拆了塑封还能退吗", "运费谁出"]

    @pytest.mark.parametrize(
        ("clause", "expected"),
        [
            ("我想买一本关于微服务的书", "book"),
            ("拆了塑封还能退吗", "policy"),
            ("买了不喜欢能退吗", "policy"),
            ("今天天气不错", None),
        ],
    )
    def test_clause_classification(self, clause, expected):
        assert classify_clause(clause) == expected

    def test_policy_keywords_win_over_book_keywords(self):
        # 「书」是找书词，但「退」是政策词：政策优先，否则会去查一本不存在的书。
        assert classify_clause("这本书拆了塑封能退吗") == "policy"

    def test_plan_order_follows_the_question(self):
        plan = build_plan("我想买一本关于微服务的书，另外如果我买了不喜欢，拆了塑封还能退吗？")
        assert [item.kind for item in plan] == ["book", "policy"]
        assert plan[0].arguments["query"] == "微服务"

    def test_member_question_adds_a_second_policy_hop(self):
        plan = build_plan("我是金卡会员，拆了塑封还能退吗？")
        assert [item.arguments["question"] for item in plan] == [
            "我是金卡会员，拆了塑封还能退吗",
            "会员已拆封退货权益",
        ]

    def test_member_question_without_unsealing_stays_single_hop(self):
        plan = build_plan("金卡会员有什么折扣？")
        assert len(plan) == 1

    def test_duplicate_clauses_are_collapsed(self):
        plan = build_plan("退货政策是什么？退货政策是什么？")
        assert len(plan) == 1


class TestRewriteRules:
    def test_broaden_uses_upper_topic(self):
        assert broaden_book_arguments({"query": "Rust 异步编程"}) == {"query": "编程"}

    def test_broaden_keeps_chinese_topic_prefix(self):
        assert broaden_book_arguments({"query": "烘焙甜点"}) == {"query": "烘焙"}

    def test_broaden_with_empty_query(self):
        assert broaden_book_arguments({}) == {"query": "编程"}

    def test_simplify_policy_question_keeps_sealing_keywords(self):
        assert simplify_policy_question("如果我买了不喜欢，拆了塑封还能退吗") == "塑封已拆 无理由退货"

    def test_simplify_policy_question_without_keywords(self):
        assert simplify_policy_question("怎么办呀") == "怎么办呀"


class TestLocalReActLLM:
    def test_first_step_for_book_question(self):
        output = LocalReActLLM().generate(
            [
                {"role": "system", "content": "..."},
                {"role": "user", "content": "用户提问：我想买一本关于微服务的书\n\n执行记录：\n（尚未执行任何动作）\n\n请输出下一步。"},
            ]
        )
        assert output.startswith("Thought:")
        assert "Action: search_book_catalog" in output
        assert '{"query": "微服务"}' in output

    def test_no_intent_answers_directly(self):
        output = LocalReActLLM().generate(
            [{"role": "user", "content": "用户提问：你好\n\n执行记录：\n（尚未执行任何动作）"}]
        )
        assert "Final Answer:" in output
        assert "导购助手" in output

    def test_retry_only_happens_once(self):
        model = LocalReActLLM()
        first = model.generate([{"role": "user", "content": "用户提问：有没有讲 Rust 的书？\n\n执行记录：\n（尚未执行任何动作）"}])
        assert '{"query": "Rust"}' in first

        scratchpad = "\n".join(
            [
                "Thought: 先查书",
                "Action: search_book_catalog",
                'Action Input: {"query": "Rust"}',
                'Observation: {"ok": false, "error": {"code": "CATALOG_NO_MATCH", "message": "没查到", "retryable": true, "hint": "放宽关键词"}}',
            ]
        )
        second = model.generate(
            [{"role": "user", "content": f"用户提问：有没有讲 Rust 的书？\n\n执行记录：\n{scratchpad}"}]
        )
        assert '{"query": "编程"}' in second

        scratchpad += "\n\n" + second.replace("Thought: ", "Thought: ") + "\n" + 'Observation: {"ok": false, "error": {"code": "CATALOG_NO_MATCH", "message": "还是没查到", "retryable": true, "hint": "放宽"}}'
        third = model.generate(
            [{"role": "user", "content": f"用户提问：有没有讲 Rust 的书？\n\n执行记录：\n{scratchpad}"}]
        )
        # 已经放宽过一次，不再重试，直接给结论。
        assert "Final Answer:" in third
        assert "放宽" in third or "没有" in third

    def test_prompt_markers_are_stripped(self):
        messages = [
            {
                "role": "user",
                "content": "用户提问：退货运费谁承担？\n\n执行记录：\n（尚未执行任何动作）\n\n请输出下一步。",
            }
        ]
        question, scratchpad = LocalReActLLM._split_prompt(messages)
        assert question == "退货运费谁承担？"
        assert scratchpad == ""
