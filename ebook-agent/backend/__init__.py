"""E-BookStore 客服 AI 助手：合并后的 Agent 后端。

一个客服助手，四个工具：

    check_inventory(isbn)               本店实时库存
    get_competitor_price(isbn)          竞品（模拟）价格
    search_book_catalog(query, ...)     按主题检索书目
    query_store_policy(question, ...)   政策库 RAG 检索

这里用模块级 __getattr__ 做惰性再导出，而不是在包导入时就把子模块拉进来。
原因：``backend.config`` 在导入时会把 ``.env`` 读进环境变量，
如果 ``import backend`` 就顺带触发了它，任何「先设环境变量、再导入」的用法
（测试夹具就是）都会失效 —— 配置已经被读走了。
"""

from __future__ import annotations

import importlib
from typing import Any

_LAZY_EXPORTS = {
    "UnifiedAssistant": "backend.assistant.agent",
    "AssistantResult": "backend.assistant.agent",
    "AssistantStep": "backend.assistant.agent",
    "LocalUnifiedLLM": "backend.assistant.offline",
    "TOOL_SCHEMAS": "backend.assistant.tools",
    "TOOL_NAMES": "backend.assistant.tools",
    "UnifiedRegistry": "backend.assistant.tools",
    "UnifiedToolOutcome": "backend.assistant.tools",
    "describe_tools": "backend.assistant.tools",
    "BookstoreTools": "backend.tools",
    "ToolRegistry": "backend.tools",
    "build_registry": "backend.tools",
}

__all__ = sorted(_LAZY_EXPORTS)


def __getattr__(name: str) -> Any:
    module_path = _LAZY_EXPORTS.get(name)
    if module_path is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return getattr(importlib.import_module(module_path), name)


def __dir__() -> list[str]:
    return __all__
