"""合并后的工具注册表：四个工具共用一张 Schema 表与一套派发逻辑。

四个工具来自两处实现，但对外只有一个契约：

===================  ==========================================  ==================
工具                  实现                                        来源
===================  ==========================================  ==================
check_inventory       backend.tools.BookstoreTools               作业2
get_competitor_price  backend.tools.BookstoreTools               作业2
search_book_catalog   backend.guide.tools.BookstoreTools         作业3
query_store_policy    backend.guide.tools.BookstoreTools（RAG）   作业3
===================  ==========================================  ==================

派发层的约定与原实现一致：任何失败都收敛成 ``{"ok": false, "error": {...}}``，
不向上抛异常。``error.hint`` 是模型自我纠错的唯一输入，所以两套异常类型都要接住。
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Callable

from ..guide.tools import (
    BookstoreTools as GuideBookstoreTools,
    TOOL_SCHEMAS as GUIDE_SCHEMAS,
    ToolError as GuideToolError,
    describe_tools,
)
from ..tools import (
    BookstoreTools as InventoryToolset,
    TOOL_SCHEMAS as INVENTORY_SCHEMAS,
    ToolError as InventoryToolError,
)

#: 交给大模型的完整工具列表。顺序固定：先库存/比价，再书目/政策，
#: 与用户「先问这本书有没有，再问推荐和政策」的习惯一致。
TOOL_SCHEMAS: list[dict] = [*INVENTORY_SCHEMAS, *GUIDE_SCHEMAS]

TOOL_NAMES: tuple[str, ...] = tuple(schema["function"]["name"] for schema in TOOL_SCHEMAS)


@dataclass
class UnifiedToolOutcome:
    """一次工具调用的结果，供循环层记录步骤、回填模型、展示在前端。"""

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

    def log_line(self) -> str:
        status = "ok" if self.ok else f"failed:{self.payload.get('error', {}).get('code')}"
        return f"[TOOL] {self.name} -> {status} ({self.duration_ms}ms)"


class UnifiedRegistry:
    """把四个工具的 Schema、实现与派发绑在一起。"""

    def __init__(
        self,
        inventory_tools: InventoryToolset | None = None,
        guide_tools: GuideBookstoreTools | None = None,
    ) -> None:
        self.inventory_tools = inventory_tools or InventoryToolset()
        self.guide_tools = guide_tools or GuideBookstoreTools()
        self._handlers: dict[str, Callable[..., dict]] = {
            "check_inventory": self.inventory_tools.check_inventory,
            "get_competitor_price": self.inventory_tools.get_competitor_price,
            "search_book_catalog": self.guide_tools.search_book_catalog,
            "query_store_policy": self.guide_tools.query_store_policy,
        }

    @property
    def schemas(self) -> list[dict]:
        return TOOL_SCHEMAS

    @property
    def names(self) -> tuple[str, ...]:
        return TOOL_NAMES

    def dispatch(self, name: str, arguments: dict) -> UnifiedToolOutcome:
        """执行一次工具调用。**任何**失败都以结构化错误返回，不向上抛异常。"""
        started = time.perf_counter()
        try:
            handler = self._handlers.get(name)
            if handler is None:
                raise ValueError(f"不存在名为 {name} 的工具")
            if not isinstance(arguments, dict):
                raise TypeError("arguments 必须是 JSON 对象")
            payload = {"ok": True, **handler(**arguments)}
            ok = True
        except (InventoryToolError, GuideToolError) as error:
            payload = self._error_payload(
                error.code, error.message, retryable=error.retryable, hint=error.hint
            )
            ok = False
        except ValueError as error:
            # 未知工具名：告诉模型可用的四个名字，它下一轮就能改对。
            payload = self._error_payload(
                "UNKNOWN_TOOL",
                str(error),
                retryable=True,
                hint=f"可用工具只有：{'、'.join(self._handlers)}。请改用其中之一。",
            )
            ok = False
        except TypeError as error:
            # 模型用了 Schema 里没声明的参数名，或漏了必填参数。
            payload = self._error_payload(
                "INVALID_ARGUMENT",
                f"参数与工具签名不匹配：{error}",
                retryable=True,
                hint=(
                    "只使用 Schema 里声明过的参数名：check_inventory 与 "
                    "get_competitor_price 只需 isbn，search_book_catalog 至少要 query，"
                    "query_store_policy 至少要 question。"
                ),
            )
            ok = False
        except Exception as error:  # noqa: BLE001 - 兜底，避免任何异常打断对话
            payload = self._error_payload(
                "TOOL_INTERNAL_ERROR",
                f"{type(error).__name__}: {error}",
                retryable=False,
                hint="工具内部错误，请如实告知用户暂时无法查询。",
            )
            ok = False

        return UnifiedToolOutcome(
            name=name,
            arguments=arguments if isinstance(arguments, dict) else {},
            ok=ok,
            payload=payload,
            duration_ms=int((time.perf_counter() - started) * 1000),
        )

    @staticmethod
    def _error_payload(code: str, message: str, *, retryable: bool, hint: str) -> dict:
        return {
            "ok": False,
            "error": {
                "code": code,
                "message": message,
                "retryable": retryable,
                "hint": hint,
            },
        }
