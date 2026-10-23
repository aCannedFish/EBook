"""测试公共夹具。

只做一件事：保证测试默认在离线模式下跑，不依赖网络、API Key，也不受本地 .env 影响。

这里必须「置空」而不是「删除」这些变量：
backend.config 在导入时会把 .env 读进 os.environ，而它只填充**尚未存在**的键。
把 LLM_API_KEY 设成空字符串，.env 里的真实密钥就不会被读进来，
测试也就不会打到真实模型上（既慢又会产生费用）。

政策检索同理：把向量化模式定成离线 TF-IDF，测试不下载模型、不读缓存。
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
os.environ["EMBEDDING_MODE"] = "offline"
os.environ["RAG_USE_CACHE"] = "0"
os.environ["RAG_MIN_SCORE"] = "0.12"

# 让 `pytest` 能在 ebook-agent/ 目录下直接运行，而不必先 pip install -e .
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture
def registry():
    from backend.tools import build_registry

    return build_registry()


@pytest.fixture(scope="session")
def policy_index():
    """离线 TF-IDF 索引：重建一次几十毫秒，整个测试会话共用。"""
    from backend.guide.rag import RagPipeline

    return RagPipeline().build()
