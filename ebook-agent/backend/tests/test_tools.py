"""Skill 定义与本地执行逻辑的测试。"""

from __future__ import annotations

import json

import pytest

from backend.catalog import MockInventoryBackend, normalize_isbn
from backend.tools import TOOL_SCHEMAS, BookstoreTools, ToolRegistry, build_registry


# ---------------------------------------------------------------------------
# Function Schema
# ---------------------------------------------------------------------------


def test_schema_has_the_two_required_skills():
    names = [schema["function"]["name"] for schema in TOOL_SCHEMAS]
    assert names == ["check_inventory", "get_competitor_price"]


@pytest.mark.parametrize("schema", TOOL_SCHEMAS, ids=lambda s: s["function"]["name"])
def test_schema_is_model_ready(schema):
    """模型只能靠 description 和参数类型做决策，这几项缺一不可。"""
    assert schema["type"] == "function"
    function = schema["function"]
    assert len(function["description"]) > 30, "description 太短，模型无法判断调用时机"
    parameters = function["parameters"]
    assert parameters["type"] == "object"
    assert parameters["required"] == ["isbn"]
    assert parameters["properties"]["isbn"]["type"] == "string"
    assert parameters["additionalProperties"] is False


def test_tool_schemas_are_json_serializable():
    """Tool 列表要原样放进请求体，不能含非 JSON 类型。"""
    assert json.loads(json.dumps(TOOL_SCHEMAS, ensure_ascii=False)) == TOOL_SCHEMAS


# ---------------------------------------------------------------------------
# 参数校验
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("978-3-00-000000-4", "9783000000004"),
        ("9783000000004", "9783000000004"),
        (" 978 3 00 000000 4 ", "9783000000004"),
        ("080442957x", "080442957X"),
    ],
)
def test_normalize_isbn(raw, expected):
    assert normalize_isbn(raw) == expected


# ---------------------------------------------------------------------------
# check_inventory
# ---------------------------------------------------------------------------


def test_check_inventory_returns_stock():
    tools = BookstoreTools(inventory=MockInventoryBackend())
    result = tools.check_inventory("978-3-00-000000-4")
    assert result["title"] == "Introduction To Algorithms"
    assert result["stockQty"] == 30
    assert result["inStock"] is True
    assert result["price"] == 99


def test_check_inventory_flags_low_stock():
    tools = BookstoreTools(inventory=MockInventoryBackend())
    result = tools.check_inventory("978-6-00-000000-7")
    assert result["stockQty"] == 3
    assert result["stockText"] == "库存紧张"


@pytest.mark.parametrize("bad", ["12345", "", "   ", "978-3-00-000000", "abcdefghij"])
def test_check_inventory_rejects_bad_isbn(bad):
    from backend.tools import InvalidArgumentError, InvalidIsbnFormatError

    tools = BookstoreTools(inventory=MockInventoryBackend())
    with pytest.raises((InvalidIsbnFormatError, InvalidArgumentError)):
        tools.check_inventory(bad)


def test_check_inventory_reports_missing_isbn_argument():
    from backend.tools import InvalidArgumentError

    tools = BookstoreTools(inventory=MockInventoryBackend())
    with pytest.raises(InvalidArgumentError):
        tools.check_inventory(None)


def test_check_inventory_reports_unknown_isbn():
    from backend.tools import IsbnNotFoundError

    tools = BookstoreTools(inventory=MockInventoryBackend())
    with pytest.raises(IsbnNotFoundError):
        tools.check_inventory("978-9-99-999999-9")


# ---------------------------------------------------------------------------
# get_competitor_price
# ---------------------------------------------------------------------------


def test_competitor_price_success_and_determinism():
    tools = BookstoreTools(
        inventory=MockInventoryBackend(),
        competitor_latency_seconds=0.0,
        transient_timeout_isbns=frozenset(),
        permanently_down_isbns=frozenset(),
    )
    first = tools.get_competitor_price("978-3-00-000000-4")
    second = tools.get_competitor_price("978-3-00-000000-4")
    assert first == second, "同一 ISBN 必须得到同一组报价，否则测试无法复现"
    assert first["lowestPrice"] == min(quote["price"] for quote in first["quotes"])


def test_competitor_price_transient_timeout_then_success():
    from backend.tools import UpstreamTimeoutError

    tools = BookstoreTools(
        inventory=MockInventoryBackend(),
        competitor_latency_seconds=0.0,
        transient_timeout_isbns=frozenset({"9787000000008"}),
    )
    with pytest.raises(UpstreamTimeoutError) as error:
        tools.get_competitor_price("978-7-00-000000-8")
    assert error.value.retryable is True

    # 第二次调用应当成功 —— 这正是「重试可修复」的语义。
    assert tools.get_competitor_price("978-7-00-000000-8")["lowestPrice"] > 0


def test_competitor_price_permanent_outage_is_not_retryable():
    from backend.tools import UpstreamUnavailableError

    tools = BookstoreTools(
        inventory=MockInventoryBackend(),
        competitor_latency_seconds=0.0,
        permanently_down_isbns=frozenset({"9782000000003"}),
    )
    with pytest.raises(UpstreamUnavailableError) as error:
        tools.get_competitor_price("978-2-00-000000-3")
    assert error.value.retryable is False


def test_competitor_price_timeout_when_latency_exceeds_threshold():
    from backend.tools import UpstreamTimeoutError

    tools = BookstoreTools(
        inventory=MockInventoryBackend(),
        competitor_latency_seconds=0.0,
        competitor_timeout_seconds=-1.0,  # 任何耗时都会超阈值
    )
    with pytest.raises(UpstreamTimeoutError):
        tools.get_competitor_price("978-3-00-000000-4")


# ---------------------------------------------------------------------------
# dispatch：任何失败都必须变成结构化错误，不得向外抛异常
# ---------------------------------------------------------------------------


def test_dispatch_success_envelope(registry):
    outcome = registry.dispatch("check_inventory", {"isbn": "978-3-00-000000-4"})
    assert outcome.ok is True
    assert outcome.payload["ok"] is True
    assert outcome.name == "check_inventory"
    assert outcome.duration_ms >= 0


def test_dispatch_unknown_tool(registry):
    outcome = registry.dispatch("delete_everything", {})
    assert outcome.ok is False
    assert outcome.payload["error"]["code"] == "INVALID_ARGUMENT"
    assert "check_inventory" in outcome.payload["error"]["hint"]


def test_dispatch_unexpected_kwarg_is_reported_not_raised(registry):
    outcome = registry.dispatch("check_inventory", {"isbn": "9783000000004", "qty": 3})
    assert outcome.ok is False
    assert outcome.payload["error"]["code"] == "INVALID_ARGUMENT"


def test_dispatch_swallows_internal_exception():
    """工具内部炸了也不能把异常抛回循环层，否则整轮对话直接中断。"""

    class ExplodingTools(BookstoreTools):
        def check_inventory(self, isbn: str) -> dict:  # noqa: D102
            raise ValueError("boom")

    registry = ToolRegistry(ExplodingTools(inventory=MockInventoryBackend()))
    outcome = registry.dispatch("check_inventory", {"isbn": "9783000000004"})
    assert outcome.ok is False
    assert outcome.payload["error"]["code"] == "TOOL_INTERNAL_ERROR"


def test_tool_message_shape(registry):
    outcome = registry.dispatch("check_inventory", {"isbn": "978-3-00-000000-4"})
    message = outcome.to_tool_message("call_abc")
    assert message["role"] == "tool"
    assert message["tool_call_id"] == "call_abc"
    assert message["name"] == "check_inventory"
    assert json.loads(message["content"])["stockQty"] == 30


def test_build_registry_exposes_both_schemas(registry):
    names = [schema["function"]["name"] for schema in registry.schemas]
    assert set(names) == {"check_inventory", "get_competitor_price"}
