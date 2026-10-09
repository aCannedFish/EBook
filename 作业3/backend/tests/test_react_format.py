"""ReAct 文本协议解析的测试。"""

from __future__ import annotations

from backend.react_format import (
    Step,
    extract_observation,
    format_action,
    format_step,
    iter_steps,
    parse_action_input,
    parse_decision,
    truncate,
)


class TestParseDecision:
    def test_action_with_json_input(self):
        decision = parse_decision(
            'Thought: 先查书目\nAction: search_book_catalog\nAction Input: {"query": "微服务"}'
        )
        assert decision.thought == "先查书目"
        assert decision.action == "search_book_catalog"
        assert decision.action_input_raw == '{"query": "微服务"}'
        assert decision.has_action and not decision.is_final
        assert not decision.error

    def test_final_answer(self):
        decision = parse_decision("Thought: 够了\nFinal Answer: 《微服务设计》有货。")
        assert decision.is_final
        assert decision.final_answer == "《微服务设计》有货。"

    def test_multiline_final_answer(self):
        decision = parse_decision("Final Answer: 第一行\n第二行\n第三行")
        assert decision.final_answer == "第一行\n第二行\n第三行"

    def test_tolerates_bold_markers_and_chinese_colons(self):
        decision = parse_decision("**思考**：先查政策\n**Action**：query_store_policy\n**Action Input**：{\"question\": \"运费谁出\"}")
        assert decision.action == "query_store_policy"
        assert "先查政策" in decision.thought

    def test_tolerates_code_fence_around_json(self):
        decision = parse_decision(
            "Thought: 查\nAction: query_store_policy\nAction Input: ```json\n{\"question\": \"退货\"}\n```"
        )
        arguments, error = parse_action_input(decision.action_input_raw)
        assert arguments == {"question": "退货"}
        assert error == ""

    def test_function_call_style_output(self):
        decision = parse_decision('Thought: 查书\nAction: search_book_catalog({"query": "微服务"})')
        assert decision.action == "search_book_catalog"
        assert decision.action_input_raw == '{"query": "微服务"}'

    def test_unparseable_output_reports_error(self):
        decision = parse_decision("我觉得应该先查一下这本书的库存。")
        assert decision.error
        assert "Action" in decision.error

    def test_thought_continuation_lines_are_kept(self):
        decision = parse_decision(
            "Thought: 第一行\n第二行\nAction: search_book_catalog\nAction Input: {\"query\": \"x\"}"
        )
        assert decision.thought == "第一行\n第二行"


class TestParseActionInput:
    def test_empty_input_is_empty_dict(self):
        assert parse_action_input("") == ({}, "")
        assert parse_action_input("   ") == ({}, "")

    def test_single_quotes_are_repaired(self):
        arguments, error = parse_action_input("{'query': '微服务'}")
        assert arguments == {"query": "微服务"}
        assert error == ""

    def test_invalid_json_reports_hint(self):
        arguments, error = parse_action_input('{"query": "微服务"')
        assert arguments is None
        assert "JSON" in error
        assert "双引号" in error

    def test_non_object_is_rejected(self):
        arguments, error = parse_action_input('["微服务"]')
        assert arguments is None
        assert "JSON 对象" in error


class TestSteps:
    def test_single_step(self):
        scratchpad = format_step("查书", "search_book_catalog", {"query": "微服务"}, '{"ok": true}')
        steps = iter_steps(scratchpad)
        assert len(steps) == 1
        assert steps[0].action == "search_book_catalog"
        assert steps[0].thought == "查书"

    def test_multiple_steps_are_not_merged(self):
        """回归用例：多条记录曾经被糊成一条，导致「这一步做没做过」全部判断错。"""
        first = format_step("先查书", "search_book_catalog", {"query": "微服务"}, '{"ok": true, "count": 3}')
        second = format_step("再查政策", "query_store_policy", {"question": "拆封能退吗"}, '{"ok": true, "count": 1}')
        steps = iter_steps(f"{first}\n\n{second}")
        assert [step.action for step in steps] == ["search_book_catalog", "query_store_policy"]
        assert steps[1].thought == "再查政策"
        assert steps[1].observation_raw.startswith('{"ok": true, "count": 1}')

    def test_observation_with_trailing_prompt_text(self):
        """观测后面跟着提示词收尾句是常态，解析必须只吃掉 JSON 对象本身。"""
        scratchpad = (
            'Thought: 查\nAction: search_book_catalog\nAction Input: {"query": "微服务"}\n'
            'Observation: {"ok": true, "count": 3}\n\n请输出下一步。'
        )
        steps = iter_steps(scratchpad)
        ok, payload = extract_observation(steps[0])
        assert ok is True
        assert payload["count"] == 3

    def test_unparsed_step_is_kept(self):
        steps = iter_steps("Thought: 我直接回答\nObservation: 没有动作")
        assert len(steps) == 1
        assert steps[0].action == ""


class TestExtractObservation:
    def test_truncated_observation_falls_back_to_regex(self):
        step = Step(
            index=1,
            thought="查书",
            action="search_book_catalog",
            action_input_raw="{}",
            observation_raw='{"ok": false, "error": {"code": "CATALOG_NO_MATCH", "message": "没有匹配',
        )
        ok, payload = extract_observation(step)
        assert ok is False
        assert payload["error"]["code"] == "CATALOG_NO_MATCH"
        assert payload["truncated"] is True

    def test_empty_observation(self):
        step = Step(index=1, thought="", action="", action_input_raw="", observation_raw="")
        assert extract_observation(step) == (None, None)

    def test_garbage_observation(self):
        step = Step(index=1, thought="", action="x", action_input_raw="", observation_raw="工具超时了")
        assert extract_observation(step) == (None, None)


class TestFormatting:
    def test_format_action(self):
        assert format_action("search_book_catalog", {"query": "微服务"}) == (
            'Action: search_book_catalog\nAction Input: {"query": "微服务"}'
        )

    def test_format_step_uses_placeholder_for_missing_thought(self):
        text = format_step("", "search_book_catalog", {}, "{}")
        assert "Thought:（模型未给出推理）" in text

    def test_truncate_marks_cut_content(self):
        text = truncate("x" * 100, 10)
        assert text.startswith("x" * 10)
        assert "观测已截断" in text
        assert truncate("short", 10) == "short"
        assert truncate("short", 0) == "short"
