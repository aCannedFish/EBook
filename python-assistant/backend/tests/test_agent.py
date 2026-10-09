"""Function Calling 循环的测试。

用 ScriptedLLM 扮演模型：按剧本逐次返回「调用某个函数」或「给出最终回答」，
从而把循环逻辑（拦截、回传、重试、兜底）与真实模型的不确定性隔离开。
"""

from __future__ import annotations

import json

import pytest

from backend.agent import SYSTEM_PROMPT, BookstoreAssistant, ToolEvent
from backend.catalog import MockInventoryBackend
from backend.config import AgentSettings
from backend.llm import AssistantTurn, LocalRuleBasedLLM, ToolCallRequest
from backend.tools import BookstoreTools, ToolRegistry


class ScriptedLLM:
    """按剧本行事的替身模型。剧本用完后继续返回最后一条。"""

    def __init__(self, turns: list[AssistantTurn]) -> None:
        self._turns = turns
        self.calls: list[list[dict]] = []

    def complete(self, messages: list[dict], tools: list[dict]) -> AssistantTurn:
        self.calls.append([dict(message) for message in messages])
        index = min(len(self.calls) - 1, len(self._turns) - 1)
        return self._turns[index]


def turn_calling(name: str, arguments: str, call_id: str = "call_1") -> AssistantTurn:
    return AssistantTurn(
        tool_calls=(ToolCallRequest(id=call_id, name=name, arguments_raw=arguments),),
        finish_reason="tool_calls",
    )


def make_registry(**overrides) -> ToolRegistry:
    defaults = {
        "inventory": MockInventoryBackend(),
        "competitor_latency_seconds": 0.0,
        "transient_timeout_isbns": frozenset(),
        "permanently_down_isbns": frozenset(),
    }
    return ToolRegistry(BookstoreTools(**{**defaults, **overrides}))


def make_assistant(client, registry=None, **agent_overrides) -> BookstoreAssistant:
    return BookstoreAssistant(
        client=client,
        registry=registry or make_registry(),
        settings=AgentSettings(**{"max_tool_rounds": 6, "max_consecutive_tool_errors": 3, **agent_overrides}),
    )


# ---------------------------------------------------------------------------


def test_system_prompt_forbids_fabricating_stock():
    """System Prompt 是「不许编造库存」这条约束唯一的落点，改动它会直接改变模型行为。"""
    assert "不得凭常识估计或编造" in SYSTEM_PROMPT
    assert "retryable" in SYSTEM_PROMPT
    assert "不要猜测 ISBN" in SYSTEM_PROMPT


def test_happy_path_intercepts_tool_then_answers():
    client = ScriptedLLM(
        [
            turn_calling("check_inventory", '{"isbn": "978-3-00-000000-4"}'),
            AssistantTurn(content="《Introduction To Algorithms》还有 30 本。"),
        ]
    )
    result = make_assistant(client).chat("算法导论还有多少本？")

    assert result.reply == "《Introduction To Algorithms》还有 30 本。"
    assert result.rounds == 2
    assert result.stopped_reason == "completed"

    [event] = result.tool_events
    assert event.name == "check_inventory"
    assert event.arguments == {"isbn": "978-3-00-000000-4"}
    assert event.ok is True
    assert event.payload["stockQty"] == 30


def test_tool_result_is_fed_back_into_context():
    """回传是关键：第二轮请求里必须能看到 tool 角色消息。"""
    client = ScriptedLLM(
        [
            turn_calling("check_inventory", '{"isbn": "978-3-00-000000-4"}'),
            AssistantTurn(content="done"),
        ]
    )
    make_assistant(client).chat("查一下")

    second_request = client.calls[1]
    tool_messages = [message for message in second_request if message["role"] == "tool"]
    assert len(tool_messages) == 1
    assert tool_messages[0]["tool_call_id"] == "call_1"
    assert tool_messages[0]["name"] == "check_inventory"

    assistant_messages = [message for message in second_request if message["role"] == "assistant"]
    assert assistant_messages[-1]["tool_calls"][0]["function"]["name"] == "check_inventory"

    # 原始用户提问与 system prompt 仍在上下文里。
    assert second_request[0]["role"] == "system"
    assert any(message.get("content") == "查一下" for message in second_request)


def test_on_tool_call_callback_exposes_name_and_arguments():
    """作业要求「拦截模型输出并打印需要调用的函数名及参数」。"""
    captured: list[ToolEvent] = []
    client = ScriptedLLM(
        [
            turn_calling("check_inventory", '{"isbn": "978-3-00-000000-4"}'),
            AssistantTurn(content="ok"),
        ]
    )
    assistant = make_assistant(client)
    assistant._on_tool_call = captured.append  # noqa: SLF001 - 测试直接注入回调
    assistant.chat("查一下")

    assert len(captured) == 1
    line = captured[0].log_line()
    assert "[TOOL CALL] check_inventory" in line
    assert '"isbn": "978-3-00-000000-4"' in line


def test_malformed_arguments_are_returned_to_the_model_instead_of_raising():
    client = ScriptedLLM(
        [
            turn_calling("check_inventory", '{"isbn": "978-3-00-000000-4"'),
            turn_calling("check_inventory", '{"isbn": "978-3-00-000000-4"}', call_id="call_2"),
            AssistantTurn(content="补上引号后查到了。"),
        ]
    )
    result = make_assistant(client).chat("查一下")

    first = result.tool_events[0]
    assert first.ok is False
    assert first.parse_error is not None
    assert first.payload["error"]["code"] == "INVALID_JSON_ARGUMENTS"
    assert first.payload["error"]["retryable"] is True

    # 模型按 hint 修正后，第二次成功。
    assert result.tool_events[1].ok is True
    assert result.reply == "补上引号后查到了。"


def test_retryable_failure_can_be_retried_by_the_model():
    registry = make_registry(transient_timeout_isbns=frozenset({"9787000000008"}))
    client = ScriptedLLM(
        [
            turn_calling("get_competitor_price", '{"isbn": "978-7-00-000000-8"}'),
            turn_calling("get_competitor_price", '{"isbn": "978-7-00-000000-8"}', call_id="call_2"),
            AssistantTurn(content="重试后拿到报价了。"),
        ]
    )
    result = make_assistant(client, registry=registry).chat("帮我比价")

    assert result.tool_events[0].ok is False
    assert result.tool_events[0].payload["error"]["code"] == "UPSTREAM_TIMEOUT"
    assert result.tool_events[0].payload["error"]["retryable"] is True
    assert result.tool_events[1].ok is True
    assert result.reply == "重试后拿到报价了。"


def test_non_retryable_failure_is_reported_to_the_model():
    registry = make_registry(permanently_down_isbns=frozenset({"9782000000003"}))
    client = ScriptedLLM(
        [
            turn_calling("get_competitor_price", '{"isbn": "978-2-00-000000-3"}'),
            AssistantTurn(content="比价渠道不可用，只能给你本店价格。"),
        ]
    )
    result = make_assistant(client, registry=registry).chat("帮我比价")

    error = result.tool_events[0].payload["error"]
    assert error["code"] == "UPSTREAM_UNAVAILABLE"
    assert error["retryable"] is False
    assert "重试" in error["hint"]


def test_max_rounds_stops_an_endless_tool_loop():
    client = ScriptedLLM([turn_calling("check_inventory", '{"isbn": "978-3-00-000000-4"}')])
    result = make_assistant(client, max_tool_rounds=3).chat("查一下")

    assert result.stopped_reason == "max_rounds"
    assert result.rounds == 3
    assert len(result.tool_events) == 3
    assert "没能给出准确结果" in result.reply


def test_consecutive_error_limit_stops_the_loop():
    client = ScriptedLLM([turn_calling("no_such_tool", "{}")])
    result = make_assistant(
        client, max_tool_rounds=10, max_consecutive_tool_errors=3
    ).chat("查一下")

    assert result.stopped_reason == "tool_error_limit"
    assert len(result.tool_events) == 3
    assert "没能拿到可靠数据" in result.reply


def test_multiple_tool_calls_in_one_turn_are_all_executed():
    client = ScriptedLLM(
        [
            AssistantTurn(
                tool_calls=(
                    ToolCallRequest("call_a", "check_inventory", '{"isbn": "978-3-00-000000-4"}'),
                    ToolCallRequest("call_b", "get_competitor_price", '{"isbn": "978-3-00-000000-4"}'),
                ),
                finish_reason="tool_calls",
            ),
            AssistantTurn(content="库存和报价都拿到了。"),
        ]
    )
    result = make_assistant(client).chat("库存和比价都要")

    assert [event.name for event in result.tool_events] == [
        "check_inventory",
        "get_competitor_price",
    ]
    assert all(event.ok for event in result.tool_events)


def test_history_is_prepended_to_context():
    client = ScriptedLLM([AssistantTurn(content="好的。")])
    make_assistant(client).chat(
        "那这本呢？",
        history=[
            {"role": "user", "content": "《量子物理》还有货吗？"},
            {"role": "assistant", "content": "请提供 ISBN。"},
        ],
    )
    roles = [message["role"] for message in client.calls[0]]
    assert roles == ["system", "user", "assistant", "user"]


# ---------------------------------------------------------------------------
# 与离线替身模型串起来的端到端检查
# ---------------------------------------------------------------------------


def test_offline_assistant_end_to_end():
    assistant = BookstoreAssistant(
        client=LocalRuleBasedLLM(), registry=make_registry(), settings=AgentSettings(6, 3)
    )
    result = assistant.chat(
        "帮我查一下 ISBN为978-3-00-000000-4 的书还有多少本，顺便看看别家卖多少钱"
    )

    assert [event.name for event in result.tool_events] == [
        "check_inventory",
        "get_competitor_price",
    ]
    assert all(event.ok for event in result.tool_events)
    assert "30 本" in result.reply
    assert "其他平台报价" in result.reply


def test_offline_assistant_asks_for_isbn_when_missing():
    assistant = BookstoreAssistant(
        client=LocalRuleBasedLLM(), registry=make_registry(), settings=AgentSettings(6, 3)
    )
    result = assistant.chat("《量子物理》还有货吗？")
    assert result.tool_events == []
    assert "ISBN" in result.reply


def test_offline_assistant_does_not_retry_an_unfixable_isbn():
    assistant = BookstoreAssistant(
        client=LocalRuleBasedLLM(), registry=make_registry(), settings=AgentSettings(6, 3)
    )
    result = assistant.chat("ISBN为12345 的书还有多少本，顺便看看别家卖多少钱")

    assert len(result.tool_events) == 1, "ISBN 本身不合法时不该再拿它去调比价接口"
    assert result.tool_events[0].payload["error"]["code"] == "INVALID_ISBN_FORMAT"
    assert "核对" in result.reply


def test_result_is_json_serializable():
    assistant = BookstoreAssistant(
        client=LocalRuleBasedLLM(), registry=make_registry(), settings=AgentSettings(6, 3)
    )
    payload = assistant.chat("ISBN为978-3-00-000000-4 的库存").to_dict()
    assert json.loads(json.dumps(payload, ensure_ascii=False)) == payload
    assert set(payload) == {"reply", "toolCalls", "rounds", "stoppedReason"}
