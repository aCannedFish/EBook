"""合并后的客服助手：工具契约与 ReAct 循环的测试。

用 ScriptedLLM 扮演模型：按剧本逐次返回「调用某个函数」或「给出最终回答」，
从而把循环逻辑（拦截、回填、重试、兜底）与真实模型的不确定性隔离开。
离线部分则直接用 LocalUnifiedLLM 跑真实工具，检查路由顺序与自我纠错。
"""

from __future__ import annotations

import json

import pytest

from backend.assistant.agent import UnifiedAssistant
from backend.assistant.offline import LocalUnifiedLLM
from backend.assistant.prompt import SYSTEM_PROMPT
from backend.assistant.tools import TOOL_NAMES, UnifiedRegistry
from backend.catalog import MockInventoryBackend
from backend.config import AgentSettings
from backend.guide.catalog import DEFAULT_CATALOG
from backend.guide.tools import BookstoreTools as GuideBookstoreTools
from backend.llm import AssistantTurn, ToolCallRequest
from backend.tools import BookstoreTools as InventoryToolset


class ScriptedLLM:
    """按剧本行事的替身模型。剧本用完后继续返回最后一条。"""

    def __init__(self, turns: list[AssistantTurn]) -> None:
        self._turns = turns
        self.calls: list[list[dict]] = []

    def complete(self, messages: list[dict], tools: list[dict]) -> AssistantTurn:
        self.calls.append([dict(message) for message in messages])
        index = min(len(self.calls) - 1, len(self._turns) - 1)
        return self._turns[index]


def turn_calling(
    name: str, arguments: str, call_id: str = "call_1", thought: str = ""
) -> AssistantTurn:
    return AssistantTurn(
        content=thought,
        tool_calls=(ToolCallRequest(id=call_id, name=name, arguments_raw=arguments),),
        finish_reason="tool_calls",
    )


def make_registry(index=None, **overrides) -> UnifiedRegistry:
    defaults = {
        "inventory": MockInventoryBackend(),
        "competitor_latency_seconds": 0.0,
        "transient_timeout_isbns": frozenset(),
        "permanently_down_isbns": frozenset(),
    }
    return UnifiedRegistry(
        inventory_tools=InventoryToolset(**{**defaults, **overrides}),
        guide_tools=GuideBookstoreTools(catalog=DEFAULT_CATALOG, index=index),
    )


def make_assistant(client, registry=None, **agent_overrides) -> UnifiedAssistant:
    settings = AgentSettings(
        **{"max_tool_rounds": 6, "max_consecutive_tool_errors": 3, **agent_overrides}
    )
    return UnifiedAssistant(client=client, registry=registry or make_registry(), settings=settings)


# ---------------------------------------------------------------------------
# 工具契约
# ---------------------------------------------------------------------------


def test_tool_schemas_expose_four_merged_tools():
    assert TOOL_NAMES == (
        "check_inventory",
        "get_competitor_price",
        "search_book_catalog",
        "query_store_policy",
    )


def test_registry_dispatches_each_tool():
    registry = make_registry()
    for name in TOOL_NAMES:
        assert registry.dispatch(name, {}) is not None


def test_unknown_tool_returns_structured_error():
    outcome = make_registry().dispatch("no_such_tool", {})
    assert outcome.ok is False
    assert outcome.payload["error"]["code"] == "UNKNOWN_TOOL"
    assert "check_inventory" in outcome.payload["error"]["hint"]


def test_system_prompt_keeps_the_merged_constraints():
    """提示词是「不许编造、按 hint 自纠、政策要写条款号」这几条约束的落点。"""
    assert "不要猜测 ISBN" in SYSTEM_PROMPT
    assert "retryable" in SYSTEM_PROMPT
    assert "条款号" in SYSTEM_PROMPT
    assert "Thought" in SYSTEM_PROMPT
    assert "search_book_catalog" in SYSTEM_PROMPT
    assert "query_store_policy" in SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# 循环
# ---------------------------------------------------------------------------


def test_happy_path_records_thought_action_observation():
    client = ScriptedLLM(
        [
            turn_calling(
                "check_inventory",
                '{"isbn": "978-3-00-000000-4"}',
                thought="先查这本还有没有货。",
            ),
            AssistantTurn(content="《Introduction To Algorithms》还有 30 本。"),
        ]
    )
    result = make_assistant(client).chat("算法导论还有多少本？")

    assert result.reply == "《Introduction To Algorithms》还有 30 本。"
    assert result.rounds == 2
    assert result.stopped_reason == "completed"

    [step] = result.steps
    assert step.action == "check_inventory"
    assert step.arguments == {"isbn": "978-3-00-000000-4"}
    assert step.thought == "先查这本还有没有货。"
    assert step.ok is True
    assert step.payload["stockQty"] == 30
    assert '"stockQty": 30' in step.observation


def test_tool_result_is_fed_back_into_context():
    """回传是关键：第二轮请求里必须能看到带结果的 tool 角色消息。"""
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
    assert json.loads(tool_messages[0]["content"])["stockQty"] == 30

    assistant_messages = [message for message in second_request if message["role"] == "assistant"]
    assert assistant_messages[-1]["tool_calls"][0]["function"]["name"] == "check_inventory"

    assert second_request[0]["role"] == "system"
    assert any(message.get("content") == "查一下" for message in second_request)


def test_on_step_callback_exposes_the_full_chain():
    """作业要求打印函数名与参数，作业3 要求 Thought -> Action -> Observation。"""
    captured = []
    client = ScriptedLLM(
        [
            turn_calling(
                "check_inventory",
                '{"isbn": "978-3-00-000000-4"}',
                thought="先查库存。",
            ),
            AssistantTurn(content="ok"),
        ]
    )
    assistant = make_assistant(client)
    assistant._on_step = captured.append  # noqa: SLF001 - 测试直接注入回调
    assistant.chat("查一下")

    assert len(captured) == 1
    trace = captured[0].log_trace()
    assert "Thought: 先查库存。" in trace
    assert "Action: check_inventory" in trace
    assert "Action Input:" in trace
    assert "Observation:" in trace


def test_malformed_arguments_are_returned_to_the_model():
    client = ScriptedLLM(
        [
            turn_calling("check_inventory", '{"isbn": "978-3-00-000000-4"'),
            turn_calling("check_inventory", '{"isbn": "978-3-00-000000-4"}', call_id="call_2"),
            AssistantTurn(content="补上引号后查到了。"),
        ]
    )
    result = make_assistant(client).chat("查一下")

    first = result.steps[0]
    assert first.ok is False
    assert first.parse_error is not None
    assert first.payload["error"]["code"] == "INVALID_JSON_ARGUMENTS"
    assert first.payload["error"]["retryable"] is True

    assert result.steps[1].ok is True
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

    assert result.steps[0].ok is False
    assert result.steps[0].payload["error"]["code"] == "UPSTREAM_TIMEOUT"
    assert result.steps[0].payload["error"]["retryable"] is True
    assert result.steps[1].ok is True
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

    error = result.steps[0].payload["error"]
    assert error["code"] == "UPSTREAM_UNAVAILABLE"
    assert error["retryable"] is False
    assert "重试" in error["hint"]


def test_repeated_action_is_blocked_without_executing_twice():
    registry = make_registry()
    client = ScriptedLLM(
        [
            turn_calling("check_inventory", '{"isbn": "978-3-00-000000-4"}'),
            turn_calling("check_inventory", '{"isbn": "978-3-00-000000-4"}', call_id="call_2"),
            AssistantTurn(content="好了。"),
        ]
    )
    result = make_assistant(client, registry=registry).chat("查一下")

    assert result.steps[0].ok is True
    assert result.steps[1].ok is False
    assert result.steps[1].payload["error"]["code"] == "REPEATED_ACTION"


def test_max_rounds_stops_an_endless_tool_loop():
    # 每轮换一个 ISBN，避免触发重复动作检测，从而真的走到轮次上限。
    client = ScriptedLLM(
        [
            turn_calling("check_inventory", '{"isbn": "978-3-00-000000-4"}', call_id="c1"),
            turn_calling("check_inventory", '{"isbn": "978-7-00-000000-8"}', call_id="c2"),
            turn_calling("check_inventory", '{"isbn": "978-2-00-000000-3"}', call_id="c3"),
        ]
    )
    result = make_assistant(client, max_tool_rounds=3).chat("查一下")

    assert result.stopped_reason == "max_rounds"
    assert result.rounds == 3
    assert len(result.steps) == 3
    assert "没能给出准确结果" in result.reply


def test_consecutive_error_limit_stops_the_loop():
    client = ScriptedLLM([turn_calling("no_such_tool", "{}")])
    result = make_assistant(client, max_tool_rounds=10, max_consecutive_tool_errors=3).chat(
        "查一下"
    )

    assert result.stopped_reason == "tool_error_limit"
    assert len(result.steps) == 3
    assert "没能拿到可靠数据" in result.reply


def test_multiple_tool_calls_in_one_turn_are_all_executed():
    client = ScriptedLLM(
        [
            AssistantTurn(
                content="库存和报价一起查。",
                tool_calls=(
                    ToolCallRequest("call_a", "check_inventory", '{"isbn": "978-3-00-000000-4"}'),
                    ToolCallRequest(
                        "call_b", "get_competitor_price", '{"isbn": "978-3-00-000000-4"}'
                    ),
                ),
                finish_reason="tool_calls",
            ),
            AssistantTurn(content="库存和报价都拿到了。"),
        ]
    )
    result = make_assistant(client).chat("库存和比价都要")

    assert [step.action for step in result.steps] == [
        "check_inventory",
        "get_competitor_price",
    ]
    assert all(step.ok for step in result.steps)
    assert all(step.thought == "库存和报价一起查。" for step in result.steps)


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


def test_offline_assistant_queries_stock_then_price():
    assistant = make_assistant(LocalUnifiedLLM())
    result = assistant.chat(
        "帮我查一下 ISBN为978-3-00-000000-4 的书还有多少本，顺便看看别家卖多少钱"
    )

    assert [step.action for step in result.steps] == [
        "check_inventory",
        "get_competitor_price",
    ]
    assert all(step.ok for step in result.steps)
    assert "30 本" in result.reply
    assert "其他平台报价" in result.reply
    assert all(step.thought for step in result.steps)


def test_offline_assistant_does_not_retry_an_unfixable_isbn():
    assistant = make_assistant(LocalUnifiedLLM())
    result = assistant.chat("ISBN为12345 的书还有多少本，顺便看看别家卖多少钱")

    assert len(result.steps) == 1, "ISBN 本身不合法时不该再拿它去调比价接口"
    assert result.steps[0].payload["error"]["code"] == "INVALID_ISBN_FORMAT"
    assert "核对" in result.reply


def test_offline_assistant_routes_catalog_before_policy(policy_index):
    assistant = make_assistant(LocalUnifiedLLM(), registry=make_registry(index=policy_index))
    result = assistant.chat("我想买一本关于微服务的书，另外如果我买了不喜欢，拆了塑封还能退吗？")

    assert [step.action for step in result.steps] == [
        "search_book_catalog",
        "query_store_policy",
    ]
    assert all(step.ok for step in result.steps)
    assert "微服务" in result.reply
    assert "条款" in result.reply


def test_result_is_json_serializable():
    payload = make_assistant(LocalUnifiedLLM()).chat("ISBN为978-3-00-000000-4 的库存").to_dict()
    assert json.loads(json.dumps(payload, ensure_ascii=False)) == payload
    assert set(payload) == {"question", "reply", "rounds", "stoppedReason", "steps"}


def test_tool_payloads_carry_book_detail_urls():
    """工具结果要带详情页地址，模型和前端都不需要自己拼 URL。"""
    from backend.assistant.agent import AssistantStep
    from backend.catalog import BookStock
    from backend.guide.catalog import Book

    book = Book(
        isbn="9787111407010", title="算法导论", author="Cormen", publisher="机械工业出版社",
        year=2013, price=128, category="计算机", tags=(), summary="", stock_qty=12,
        rating=0.0, sales=0, book_id=47,
    )
    assert book.to_payload()["detailUrl"] == "/books/47"

    stock = BookStock(
        isbn="9787111407010", title="算法导论", author="Cormen", price=128,
        category="计算机", stock_qty=12, stock_text="有货", book_id=47,
    )
    assert stock.to_payload()["detailUrl"] == "/books/47"

    step = AssistantStep(
        index=1, thought="", action="search_book_catalog", arguments={}, ok=True,
        payload={"ok": True, "results": [{"title": "算法导论", "detailUrl": "/books/47"}]},
        observation="",
    )
    reply = UnifiedAssistant._link_reply(
        "推荐 [《算法导论》](https://example.com/books/1)，也可以看《算法导论》。",
        [step],
    )
    assert "example.com" not in reply
    assert reply.count("(/books/47)") == 2


def test_plain_book_title_without_tool_url_is_not_linked():
    """没有工具给出的地址时保持纯文本，避免拼出不可信的链接。"""
    from backend.assistant.agent import AssistantStep

    step = AssistantStep(
        index=1, thought="", action="search_book_catalog", arguments={}, ok=True,
        payload={"ok": True, "results": [{"title": "算法导论"}]}, observation="",
    )
    assert UnifiedAssistant._link_reply("推荐《算法导论》。", [step]) == "推荐《算法导论》。"
