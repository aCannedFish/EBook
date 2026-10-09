"""E-BookStore 客服 AI 助手：Function Calling 后端。

对外只有两个 Skill：
    check_inventory(isbn)       查询书店实时库存
    get_competitor_price(isbn)  查询竞品（模拟）价格

这里用模块级 __getattr__ 做惰性再导出，而不是在包导入时就把子模块拉进来。
原因：``backend.config`` 在导入时会把 ``.env`` 读进环境变量，
如果 ``import backend`` 就顺带触发了它，任何「先设环境变量、再导入」的用法
（测试夹具就是）都会失效 —— 配置已经被读走了。
"""

from __future__ import annotations

import importlib
from typing import Any

_LAZY_EXPORTS = {
    "BookstoreAssistant": "backend.agent",
    "ChatResult": "backend.agent",
    "ToolEvent": "backend.agent",
    "BookstoreTools": "backend.tools",
    "TOOL_SCHEMAS": "backend.tools",
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
