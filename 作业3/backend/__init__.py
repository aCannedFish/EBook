"""E-BookStore 导购助手：RAG（政策库检索）+ ReAct Agent。

两个工具：
    search_book_catalog(query, ...)   模拟查书
    query_store_policy(question, ...) 调用 RAG 检索政策库

这里用模块级 ``__getattr__`` 做惰性再导出，而不是在包导入时把子模块全拉进来：
``backend.config`` 在导入时会把 ``.env`` 读进环境变量，如果 ``import backend``
就顺带触发了它，任何「先设环境变量再导入」的用法（测试夹具就是）都会失效 ——
配置已经被读走了。
"""

from __future__ import annotations

import importlib
from typing import Any

_LAZY_EXPORTS = {
    "ReActAgent": "backend.agent",
    "AgentResult": "backend.agent",
    "ReActStep": "backend.agent",
    "REACT_SYSTEM_PROMPT": "backend.agent",
    "RagPipeline": "backend.rag",
    "RagIndex": "backend.rag",
    "load_policy_document": "backend.corpus",
    "split_into_chunks": "backend.chunking",
    "BookstoreTools": "backend.tools",
    "ToolRegistry": "backend.tools",
    "TOOL_SCHEMAS": "backend.tools",
    "build_registry": "backend.tools",
    "LocalReActLLM": "backend.llm",
}

__all__ = sorted(_LAZY_EXPORTS)


def __getattr__(name: str) -> Any:
    module_path = _LAZY_EXPORTS.get(name)
    if module_path is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return getattr(importlib.import_module(module_path), name)


def __dir__() -> list[str]:
    return __all__
