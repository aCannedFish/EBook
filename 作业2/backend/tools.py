"""Function (Skill) 定义与本地模拟执行。

本模块是作业要求的两个 Skill：
  - ``check_inventory(isbn)``      查询书店实时库存
  - ``get_competitor_price(isbn)`` 查询竞品（模拟）价格

两个函数都遵循同一套约定，这一点是整个异常处理设计的基础：

1. schema 用 OpenAI tools 格式声明，description 写清「这个函数什么时候该被调用、
   什么时候不该被调用」，参数用 JSON Schema 描述类型和约束 —— 模型只能依靠这些文字
   决定是否调用、传什么参数，写得含糊就会乱调。
2. 函数本身可以被直接调用（单元测试、CLI 都这么用）；但在 Function Calling 循环里
   一律走 ``dispatch``，由它把异常统一收敛成结构化错误。
3. 不向模型抛异常，而是返回 ``{"ok": false, "error": {...}}``。异常栈对模型没有意义，
   ``error.hint`` 才有 —— 它是自纠错（self-correction）的唯一输入。
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Callable

from .catalog import (
    BookstoreOutOfReach,
    InventoryBackend,
    build_inventory_backend,
    is_isbn_shaped,
    normalize_isbn,
)
from .config import TOOLS


# ---------------------------------------------------------------------------
# 异常
# ---------------------------------------------------------------------------


class ToolError(Exception):
    """工具层异常基类。

    code 是给模型和前端看的稳定标识，hint 是给模型的修复建议。
    retryable 表示「原样重试是否可能成功」。
    """

    code = "TOOL_ERROR"
    retryable = False

    def __init__(self, message: str, hint: str, *, retryable: bool | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.hint = hint
        if retryable is not None:
            self.retryable = retryable


class InvalidArgumentError(ToolError):
    """参数缺失或类型不对。"""

    code = "INVALID_ARGUMENT"


class InvalidIsbnFormatError(ToolError):
    """ISBN 不符合格式要求（长度 / 字符集）。"""

    code = "INVALID_ISBN_FORMAT"


class IsbnNotFoundError(ToolError):
    """格式合法但书店目录里没有这本书。"""

    code = "ISBN_NOT_FOUND"


class UpstreamTimeoutError(ToolError):
    """上游接口超时。"""

    code = "UPSTREAM_TIMEOUT"
    retryable = True


class UpstreamUnavailableError(ToolError):
    """上游接口整体不可用，重试无意义。"""

    code = "UPSTREAM_UNAVAILABLE"


# ---------------------------------------------------------------------------
# 参数校验
# ---------------------------------------------------------------------------


def _require_isbn(isbn: Any) -> str:
    if isbn is None or (isinstance(isbn, str) and not isbn.strip()):
        raise InvalidArgumentError(
            "缺少必填参数 isbn",
            hint="必须传入 isbn 参数，值取自用户的提问或前一次 check_inventory 的结果。",
        )
    if not isinstance(isbn, str):
        raise InvalidArgumentError(
            f"参数 isbn 必须是字符串，收到 {type(isbn).__name__}",
            hint="把 isbn 写成字符串，例如 \"978-3-00-000000-4\"。",
        )
    normalized = normalize_isbn(isbn)
    if not is_isbn_shaped(normalized):
        raise InvalidIsbnFormatError(
            f"ISBN {isbn!r} 格式不合法：去掉连字符后应为 10 位或 13 位数字",
            hint=(
                "不要自行补全或猜测 ISBN。请向用户复述你收到的值并请其确认；"
                "若用户给的是书名，先请用户提供 ISBN。"
            ),
        )
    return normalized


# ---------------------------------------------------------------------------
# Skill 实现
# ---------------------------------------------------------------------------


@dataclass
class BookstoreTools:
    """两个 Skill 的实现。

    ``competitor_failures`` 记录每个 ISBN 已经触发过多少次模拟抖动，
    用来实现「首次超时、重试成功」这种真实世界最常见的上游故障形态。
    """

    inventory: InventoryBackend
    competitor_latency_seconds: float = TOOLS.competitor_latency_seconds
    competitor_timeout_seconds: float = TOOLS.competitor_timeout_seconds
    transient_timeout_isbns: frozenset[str] = TOOLS.transient_timeout_isbns
    permanently_down_isbns: frozenset[str] = TOOLS.permanently_down_isbns

    def __post_init__(self) -> None:
        self.competitor_failures: dict[str, int] = {}

    # -- Skill 1 ------------------------------------------------------------
    def check_inventory(self, isbn: str) -> dict:
        """查询书店实时库存。

        :raises InvalidArgumentError: isbn 缺失或类型不对
        :raises InvalidIsbnFormatError: isbn 格式不合法
        :raises IsbnNotFoundError: 书店目录中没有该书
        """
        normalized = _require_isbn(isbn)
        try:
            stock = self.inventory.find_by_isbn(normalized)
        except BookstoreOutOfReach as error:
            raise UpstreamUnavailableError(
                str(error),
                hint="书店后端当前不可达，请如实告知用户暂时查不到库存，不要编造数量。",
            ) from error

        if stock is None:
            raise IsbnNotFoundError(
                f"书店目录中没有 ISBN 为 {normalized} 的图书",
                hint=(
                    "换用目录中确实存在的 ISBN，或如实告知用户这本书没有收录，"
                    "不要虚构书名与库存。"
                ),
            )

        payload = stock.to_payload()
        payload["source"] = "bookstore-inventory"
        return payload

    # -- Skill 2 ------------------------------------------------------------
    def get_competitor_price(self, isbn: str) -> dict:
        """查询竞品（模拟）价格。

        :raises UpstreamTimeoutError: 上游超时，可重试
        :raises UpstreamUnavailableError: 上游不可用，重试无意义
        """
        normalized = _require_isbn(isbn)

        if normalized in self.permanently_down_isbns:
            raise UpstreamUnavailableError(
                f"竞品比价服务对 ISBN {normalized} 返回 503",
                hint="该渠道暂时不可用，重试没有意义；请告知用户只拿到了本店价格。",
            )

        # 模拟网络耗时：超过阈值就判定为超时。
        time.sleep(self.competitor_latency_seconds)
        if self.competitor_latency_seconds > self.competitor_timeout_seconds:
            raise UpstreamTimeoutError(
                f"调用竞品比价接口耗时 {self.competitor_latency_seconds:.2f}s，"
                f"超过 {self.competitor_timeout_seconds:.2f}s 阈值",
                hint="这是瞬时故障，原样重试一次通常就能成功。",
            )

        attempts = self.competitor_failures.get(normalized, 0)
        if normalized in self.transient_timeout_isbns and attempts == 0:
            self.competitor_failures[normalized] = attempts + 1
            raise UpstreamTimeoutError(
                f"竞品比价接口对 ISBN {normalized} 响应超时（第 1 次）",
                hint="上游抖动，原样重试一次即可，不用修改参数。",
            )
        self.competitor_failures[normalized] = attempts + 1

        # 用 ISBN 数字位稳定地推导出报价，保证同一本书每次得到同一组结果。
        seed = sum(int(ch) for ch in normalized if ch.isdigit())
        base = 45 + seed % 40
        quotes = [
            {"platform": "博文轩", "price": base, "currency": "CNY", "inStock": True, "deliveryDays": 2},
            {"platform": "云书房", "price": base + 6, "currency": "CNY", "inStock": True, "deliveryDays": 1},
            {
                "platform": "知微书城",
                "price": max(base - 5, 1),
                "currency": "CNY",
                "inStock": seed % 3 != 0,
                "deliveryDays": 4,
            },
        ]
        return {
            "isbn": normalized,
            "quotes": quotes,
            "lowestPrice": min(quote["price"] for quote in quotes),
            "source": "competitor-price-mock",
        }


# ---------------------------------------------------------------------------
# Tool Schema（交给大模型的 tools 列表）
# ---------------------------------------------------------------------------

TOOL_SCHEMAS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "check_inventory",
            "description": (
                "查询电子书城本店的实时库存与售价。当用户询问某本书还有多少本、"
                "是否有货、能不能买到、本店卖多少钱，或需要判断库存是否足够时调用。"
                "必须先从用户的话里拿到 ISBN 再调用；如果用户只给了书名，"
                "不要猜测 ISBN，先向用户索要。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "isbn": {
                        "type": "string",
                        "description": (
                            "图书的国际标准书号，10 位或 13 位，可带连字符，"
                            "例如 978-3-00-000000-4 或 9783000000004。"
                        ),
                    }
                },
                "required": ["isbn"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_competitor_price",
            "description": (
                "查询其他平台（竞品）对同一本书的报价，用于和本店价格做对比。"
                "仅当用户明确要求比价、询问别家卖多少钱时才调用；"
                "如果只是问本店库存，不要调用本函数。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "isbn": {
                        "type": "string",
                        "description": "图书的 ISBN，与 check_inventory 使用的是同一个值。",
                    }
                },
                "required": ["isbn"],
                "additionalProperties": False,
            },
        },
    },
]

TOOL_NAMES = tuple(schema["function"]["name"] for schema in TOOL_SCHEMAS)


# ---------------------------------------------------------------------------
# 统一派发
# ---------------------------------------------------------------------------


@dataclass
class ToolOutcome:
    """一次工具调用的完整结果，供循环层记录日志、回传模型、展示在前端。"""

    name: str
    arguments: dict
    ok: bool
    payload: dict
    duration_ms: int

    def to_tool_message(self, call_id: str) -> dict:
        """转成回传给大模型的 tool 角色消息。"""
        return {
            "role": "tool",
            "tool_call_id": call_id,
            "name": self.name,
            "content": json.dumps(self.payload, ensure_ascii=False),
        }


class ToolRegistry:
    """把 schema、实现、派发逻辑绑在一起。"""

    def __init__(self, tools: BookstoreTools) -> None:
        self._tools = tools
        self._handlers: dict[str, Callable[..., dict]] = {
            "check_inventory": tools.check_inventory,
            "get_competitor_price": tools.get_competitor_price,
        }

    @property
    def schemas(self) -> list[dict]:
        return TOOL_SCHEMAS

    def dispatch(self, name: str, arguments: dict) -> ToolOutcome:
        """执行一次工具调用。**任何**失败都以结构化错误返回，不向上抛异常。"""
        started = time.perf_counter()
        try:
            handler = self._handlers.get(name)
            if handler is None:
                raise InvalidArgumentError(
                    f"不存在名为 {name} 的函数",
                    hint=f"可用的函数只有：{'、'.join(self._handlers)}。请改用其中之一。",
                )
            payload = {"ok": True, **handler(**arguments)}
            ok = True
        except ToolError as error:
            payload = {
                "ok": False,
                "error": {
                    "code": error.code,
                    "message": error.message,
                    "retryable": error.retryable,
                    "hint": error.hint,
                },
            }
            ok = False
        except TypeError as error:
            # 模型给了一个 schema 里没声明的参数名，或漏了必填参数。
            payload = {
                "ok": False,
                "error": {
                    "code": "INVALID_ARGUMENT",
                    "message": f"参数与函数签名不匹配：{error}",
                    "retryable": True,
                    "hint": f"{name} 只接受名为 isbn 的字符串参数，请按 schema 重新调用。",
                },
            }
            ok = False
        except Exception as error:  # noqa: BLE001 - 兜底，避免任何异常打断对话
            payload = {
                "ok": False,
                "error": {
                    "code": "TOOL_INTERNAL_ERROR",
                    "message": f"{type(error).__name__}: {error}",
                    "retryable": False,
                    "hint": "该工具内部错误，请告知用户暂时无法查询。",
                },
            }
            ok = False

        return ToolOutcome(
            name=name,
            arguments=arguments,
            ok=ok,
            payload=payload,
            duration_ms=int((time.perf_counter() - started) * 1000),
        )


def build_registry() -> ToolRegistry:
    return ToolRegistry(BookstoreTools(inventory=build_inventory_backend()))
