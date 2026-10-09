"""测试公共夹具。

只做一件事：保证测试默认在离线模式下跑，不依赖网络、API Key，也不受本地 .env 影响。

这里必须「置空」而不是「删除」这些变量：
backend.config 在导入时会把 .env 读进 os.environ，而它只填充**尚未存在**的键。
把 LLM_API_KEY 设成空字符串，.env 里的真实密钥就不会被读进来，
测试也就不会打到真实模型上（既慢又会产生费用）。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

os.environ["LLM_API_KEY"] = ""
os.environ["LLM_BASE_URL"] = "https://api.openai.com/v1"
os.environ["LLM_MODEL"] = "gpt-4o-mini"
os.environ["BOOKSTORE_API_BASE"] = ""

# 让 `pytest` 能在 python-assistant/ 或 作业2/ 目录下直接运行，而不必先 pip install -e .
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture
def registry():
    from backend.tools import build_registry

    return build_registry()
