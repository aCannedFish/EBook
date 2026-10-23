"""合并后的客服助手。

作业2 的库存/比价与作业3 的荐书/政策原本是两条各自独立的链路，这个包把它们合成
一个 Agent：

- ``tools``：四个工具共用一张 Schema 表与一套派发逻辑；
- ``agent``：ReAct 循环，用 Function Calling 下发动作、回填观测；
- ``offline``：不联网时的替身模型，同样会产出工具调用与执行记录；
- ``prompt``：合并后的系统提示词。

包内只做惰性导出，避免一 import 就把 ``.env`` 读进环境变量，
破坏「先设环境变量、再导入」的测试夹具。
"""

from __future__ import annotations

import importlib
from typing import Any

_LAZY_EXPORTS = {
    "UnifiedAssistant": "backend.assistant.agent",
    "AssistantResult": "backend.assistant.agent",
    "AssistantStep": "backend.assistant.agent",
    "SYSTEM_PROMPT": "backend.assistant.prompt",
    "TOOL_SCHEMAS": "backend.assistant.tools",
    "TOOL_NAMES": "backend.assistant.tools",
    "UnifiedRegistry": "backend.assistant.tools",
    "UnifiedToolOutcome": "backend.assistant.tools",
    "describe_tools": "backend.assistant.tools",
    "LocalUnifiedLLM": "backend.assistant.offline",
}

__all__ = sorted(_LAZY_EXPORTS)


def __getattr__(name: str) -> Any:
    module_path = _LAZY_EXPORTS.get(name)
    if module_path is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return getattr(importlib.import_module(module_path), name)


def __dir__() -> list[str]:
    return __all__
