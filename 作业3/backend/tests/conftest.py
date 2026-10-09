"""测试夹具。

这里在导入任何 backend 模块之前把环境变量定死，原因：
``backend.config`` 在导入时就会把环境变量与 .env 读进模块级常量，
配置一旦读走就没法在用例里改。所以：

- ``EMBEDDING_MODE=offline``：测试不联网，也不让 .env 里的密钥影响结果；
- ``RAG_USE_CACHE=0``：不读写磁盘缓存，用例之间互不污染。

需要在用例里改配置的地方，用 ``dataclasses.replace`` 造一份新的设置对象传进去，
而不是改环境变量 —— 设置对象都是 frozen dataclass，替换比打补丁清楚。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ["EMBEDDING_MODE"] = "offline"
os.environ["RAG_USE_CACHE"] = "0"
os.environ["RAG_MIN_SCORE"] = "0.12"
os.environ["LLM_API_KEY"] = ""
os.environ.pop("EMBEDDING_API_KEY", None)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest  # noqa: E402

from backend.chunking import split_into_chunks  # noqa: E402
from backend.corpus import load_policy_document  # noqa: E402
from backend.embedding import TfidfEmbedder  # noqa: E402
from backend.rag import RagPipeline  # noqa: E402
from backend.tools import BookstoreTools  # noqa: E402


@pytest.fixture(scope="session")
def document():
    return load_policy_document()


@pytest.fixture(scope="session")
def chunks(document):
    return split_into_chunks(document, chunk_size=420, chunk_overlap=60)


@pytest.fixture(scope="session")
def embedder(chunks):
    return TfidfEmbedder().fit([chunk.text for chunk in chunks])


@pytest.fixture(scope="session")
def index():
    """整个测试会话共用一个索引：重建一次几十毫秒，但没必要每个用例都重建。"""
    return RagPipeline().build()


@pytest.fixture
def tools(index):
    """带现成索引的工具实例，避免工具内部再建一次索引。"""
    return BookstoreTools(index=index)
