"""政策知识库与书目检索：合并后的客服助手在此之上提供 RAG 工具。

两个工具：
    search_book_catalog(query, ...)   按主题检索书目
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
    "RagPipeline": "backend.guide.rag",
    "RagIndex": "backend.guide.rag",
    "load_policy_document": "backend.guide.corpus",
    "split_into_chunks": "backend.guide.chunking",
    "BookstoreTools": "backend.guide.tools",
    "ToolRegistry": "backend.guide.tools",
    "TOOL_SCHEMAS": "backend.guide.tools",
    "build_registry": "backend.guide.tools",
    "LocalReActLLM": "backend.guide.llm",
}

__all__ = sorted(_LAZY_EXPORTS)


def __getattr__(name: str) -> Any:
    module_path = _LAZY_EXPORTS.get(name)
    if module_path is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return getattr(importlib.import_module(module_path), name)


def __dir__() -> list[str]:
    return __all__
