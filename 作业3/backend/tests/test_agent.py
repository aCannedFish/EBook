"""ReAct 循环的测试。

用两种「模型」跑同一套循环：
- ``LocalReActLLM``（离线替身模型）跑端到端用例，覆盖作业要求的复杂交互 Case；
- ``ScriptedClient``（按剧本返回固定文本）跑异常路径，精确控制模型输出，
  把「解析失败」「重复动作」「连续失败」这些分支逼出来。
"""

from __future__ import annotations

import json

import pytest

from backend.agent import REACT_SYSTEM_PROMPT, ReActAgent
from backend.config import AGENT
from backend.llm import LocalReActLLM
from backend.tools import build_registry

COMPLEX_QUESTION = "我想买一本关于微服务的书，另外如果我买了不喜欢，拆了塑封还能退吗？"


class ScriptedClient:
    """按剧本依次返回模型输出；剧本用完后重复最后一条。"""

    def __init__(self, outputs: list[str]) -> None:
        self._outputs = list(outputs)
        self.calls: list[list[dict]] = []
        self.stops: list[tuple[str, ...] | None] = []

    def generate(self, messages: list[dict], stop=None) -> str:
        self.calls.append(messages)
        self.stops.append(tuple(stop) if stop else None)
        if len(self._outputs) > 1:
            return self._outputs.pop(0)
        return self._outputs[0]


@pytest.fixture
def agent(tools):
    return ReActAgent(client=LocalReActLLM(), registry=build_registry(tools))


class TestComplexCase:
    def test_calls_catalog_then_policy(self, agent):
        result = agent.run(COMPLEX_QUESTION)
        assert result.actions == ["search_book_catalog", "query_store_policy"]
        assert result.stopped_reason == "completed"

    def test_reply_combines_books_and_policy(self, agent):
        result = agent.run(COMPLEX_QUESTION)
        assert "微服务" in result.reply
        assert "库存" in result.reply
        assert "第六条【塑封与拆封规则】" in result.reply
        assert "塑封已拆" in result.reply

    def test_every_step_has_thought_action_observation(self, agent):
        result = agent.run(COMPLEX_QUESTION)
        assert result.steps
        for step in result.steps:
            assert step.thought
            assert step.action
            assert step.observation.startswith("{")
            assert step.ok is True
            assert step.payload["ok"] is True

    def test_steps_serialize_for_the_report(self, agent):
        payload = agent.run(COMPLEX_QUESTION).to_dict()
        assert payload["question"] == COMPLEX_QUESTION
        assert payload["rounds"] == len(payload["steps"]) + 1
        first = payload["steps"][0]
        assert first["action"] == "search_book_catalog"
        assert first["arguments"] == {"query": "微服务"}
        assert first["result"]["count"] >= 1

    def test_policy_only_question_skips_catalog(self, agent):
        result = agent.run("退货运费谁承担？")
        assert result.actions == ["query_store_policy"]
        assert "第十二条【运费承担】" in result.reply

    def test_conclusion_line_follows_the_question_polarity(self, agent):
        """「拆了塑封」和「还没拆塑封」问的是相反的两款，引用不能引错。"""
        unsealed = agent.run("拆了塑封还能退吗").reply
        assert "（二）塑封已拆：原则上不支持七天无理由退货" in unsealed

        sealed = agent.run("还没拆塑封能退吗").reply
        assert "（一）塑封未拆：可直接申请七天无理由退货" in sealed

    def test_member_question_triggers_two_hop_retrieval(self, agent):
        result = agent.run("我是金卡会员，拆了塑封还能退吗？")
        assert result.actions == ["query_store_policy", "query_store_policy"]
        assert result.steps[1].arguments["question"] == "会员已拆封退货权益"
        assert "第二十条【已拆封退货权益】" in result.reply

    def test_book_filters_are_used(self, agent):
        result = agent.run("我想买一本 100 元以内的微服务书，最好有现货；")
        assert result.steps[0].arguments == {"query": "微服务", "max_price": 100, "in_stock_only": True}
        assert all(book["price"] <= 100 for book in result.steps[0].payload["results"])

    def test_missing_topic_falls_back_to_broadening(self, agent):
        result = agent.run("有没有讲 Rust 的书？")
        assert [step.arguments["query"] for step in result.steps] == ["Rust", "编程"]
        assert result.steps[0].ok is False
        assert "放宽" in result.steps[1].thought
        assert "没有「Rust」直接相关的书" in result.reply

    def test_uncovered_policy_is_admitted(self, agent):
        result = agent.run("海外直邮的书可以退吗？")
        assert result.steps[0].ok is False
        assert result.steps[0].payload["error"]["code"] == "POLICY_NOT_COVERED"
        assert "客服" in result.reply

    def test_no_intent_question_gets_guidance(self, agent):
        result = agent.run("你好呀")
        assert result.actions == []
        assert "导购助手" in result.reply
        assert result.rounds == 1


class TestLoopGuards:
    def test_duplicate_action_is_rejected(self, tools):
        repeated = (
            'Thought: 再查一次\nAction: search_book_catalog\nAction Input: {"query": "微服务"}'
        )
        client = ScriptedClient([repeated])
        result = ReActAgent(client=client, registry=build_registry(tools)).run("微服务")
        # 第一次是真查（成功），之后每次都是同一动作同一参数：第二次起被拦下。
        assert result.steps[0].ok is True
        assert result.steps[1].payload["error"]["code"] == "REPEATED_ACTION"
        assert result.stopped_reason == "error_limit"
        assert "连续出错" in result.reply

    def test_max_steps_is_enforced(self, tools):
        outputs = [
            f'Thought: 第{i}次\nAction: search_book_catalog\nAction Input: {{"query": "微服务{i}"}}'
            for i in range(10)
        ]
        settings = type(AGENT)(max_steps=3, max_consecutive_errors=9, observation_max_chars=3000)
        # 每一轮都失败（查不到），但参数不同，所以触发的是「步数上限」而不是「重复动作」。
        result = ReActAgent(
            client=ScriptedClient(outputs), registry=build_registry(tools), settings=settings
        ).run("微服务")
        assert result.stopped_reason == "max_steps"
        assert len(result.steps) == 3
        assert "不确定" in result.reply

    def test_consecutive_failures_stop_the_loop(self, tools):
        outputs = [
            f'Thought: 试{i}\nAction: search_book_catalog\nAction Input: {{"query": "不存在{i}"}}'
            for i in range(5)
        ]
        result = ReActAgent(
            client=ScriptedClient(outputs), registry=build_registry(tools)
        ).run("找本不存在的书")
        assert result.stopped_reason == "error_limit"
        assert len(result.steps) == AGENT.max_consecutive_errors

    def test_unknown_tool_is_reported_back(self, tools):
        client = ScriptedClient(
            [
                'Thought: 我试试\nAction: order_book\nAction Input: {"isbn": "x"}',
                "Thought: 换一个\nFinal Answer: 好的。",
            ]
        )
        result = ReActAgent(client=client, registry=build_registry(tools)).run("帮我下单")
        assert result.steps[0].payload["error"]["code"] == "INVALID_ARGUMENT"
        assert "search_book_catalog" in result.steps[0].payload["error"]["hint"]
        assert result.reply == "好的。"


class TestProtocolHandling:
    def test_format_error_is_observed_and_recovered(self, tools):
        client = ScriptedClient(
            ["我先想想应该查什么书。", "Thought: 好\nFinal Answer: 那就这样。"]
        )
        result = ReActAgent(client=client, registry=build_registry(tools)).run("问题")
        assert result.steps[0].parse_error
        assert result.steps[0].action == "(未解析)"
        assert result.steps[0].payload["error"]["code"] == "REACT_FORMAT_ERROR"
        assert result.reply == "那就这样。"
        # 第二轮提示词里带着上一轮的错误与模型自己的原话。
        second_prompt = client.calls[1][1]["content"]
        assert "REACT_FORMAT_ERROR" in second_prompt
        assert "我先想想应该查什么书。" in second_prompt

    def test_invalid_json_arguments_are_observed(self, tools):
        client = ScriptedClient(
            [
                'Thought: 查书\nAction: search_book_catalog\nAction Input: {"query": "微服务"',
                "Thought: 修好了\nFinal Answer: 完成。",
            ]
        )
        result = ReActAgent(client=client, registry=build_registry(tools)).run("找书")
        assert result.steps[0].payload["error"]["code"] == "INVALID_JSON_ARGUMENTS"
        assert result.steps[0].arguments == {}

    def test_stop_sequences_are_passed_to_the_model(self, tools):
        client = ScriptedClient(["Thought: 好\nFinal Answer: 嗯。"])
        ReActAgent(client=client, registry=build_registry(tools)).run("问题")
        assert client.stops[0] == ("\nObservation:", "Observation:")

    def test_thought_is_optional(self, tools):
        client = ScriptedClient(['Action: search_book_catalog\nAction Input: {"query": "微服务"}'])
        result = ReActAgent(client=client, registry=build_registry(tools)).run("找书")
        assert result.steps[0].thought == ""
        assert "（模型未给出推理）" in result.scratchpad

    def test_observation_is_truncated_before_refill(self, tools):
        settings = type(AGENT)(max_steps=3, max_consecutive_errors=3, observation_max_chars=400)
        client = ScriptedClient(
            [
                'Thought: 查政策\nAction: query_store_policy\nAction Input: {"question": "退货"}',
                "Thought: 够了\nFinal Answer: 见条款。",
            ]
        )
        result = ReActAgent(
            client=client, registry=build_registry(tools), settings=settings
        ).run("退货政策")
        assert len(result.steps[0].observation) < 600
        assert "观测已截断" in result.steps[0].observation


class TestPromptAndCallbacks:
    def test_system_prompt_describes_tools_and_format(self, agent):
        prompt = agent.system_prompt
        assert "search_book_catalog" in prompt
        assert "query_store_policy" in prompt
        assert "Thought" in prompt and "Action Input" in prompt
        assert "Final Answer" in prompt
        assert "条款" in prompt
        assert "{tools}" not in REACT_SYSTEM_PROMPT.format(tools="x")

    def test_user_message_carries_scratchpad(self, tools):
        client = ScriptedClient(["Thought: 好\nFinal Answer: 行。"])
        ReActAgent(client=client, registry=build_registry(tools)).run("微服务有货吗")
        content = client.calls[0][1]["content"]
        assert "用户提问：微服务有货吗" in content
        assert "执行记录：" in content
        assert "（尚未执行任何动作）" in content

    def test_on_step_callback_receives_each_step(self, tools):
        seen = []
        ReActAgent(
            client=LocalReActLLM(), registry=build_registry(tools), on_step=seen.append
        ).run(COMPLEX_QUESTION)
        assert [step.action for step in seen] == ["search_book_catalog", "query_store_policy"]
        assert seen[0].log_line().startswith("[REACT] step=1")

    def test_result_reply_and_steps_are_json_serializable(self, agent):
        payload = json.dumps(agent.run(COMPLEX_QUESTION).to_dict(), ensure_ascii=False)
        assert '"stoppedReason": "completed"' in payload
