"""运行期配置。

配置来源两处，后者不覆盖前者（便于临时用环境变量覆盖文件配置）：
1. 进程环境变量；
2. 作业目录下的 ``.env``（复制 ``.env.example`` 改名即可）。

所有配置都有默认值：不配任何东西也能跑 —— 未配置 ``LLM_API_KEY`` 时用内置的
离线替身模型，未配置向量化接口时用本地的确定性向量化实现。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

#: 作业目录（backend/ 的上一级）。语料、索引缓存、.env 都相对它定位，
#: 因此从仓库根跑还是从作业目录跑，找到的都是同一份文件。
PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT.parent

DOTENV_CANDIDATES = (PROJECT_ROOT / ".env", Path.cwd() / ".env")


def load_dotenv(paths: tuple[Path, ...] = DOTENV_CANDIDATES) -> None:
    """把 .env 里的键值对写进 os.environ，已存在的键不覆盖。"""
    for path in paths:
        if not path.is_file():
            continue
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[len("export ") :].strip()
            key, separator, value = line.partition("=")
            if not separator:
                continue
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


load_dotenv()


def _env_str(name: str, default: str = "") -> str:
    raw = os.environ.get(name)
    return default if raw is None else raw.strip()


def _env_float(name: str, default: float) -> float:
    try:
        return float(_env_str(name) or default)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    try:
        return int(_env_str(name) or default)
    except ValueError:
        return default


def _env_path(name: str, default: Path) -> Path:
    raw = _env_str(name)
    if not raw:
        return default
    path = Path(raw).expanduser()
    return path if path.is_absolute() else (PROJECT_ROOT / path)


DEFAULT_BASE_URL = "https://api.openai.com/v1"


def normalize_base_url(raw: str) -> str:
    """把 base_url 归一化成「服务根 + /v1」的形式。

    SDK 会在 base_url 后面自己拼 ``/chat/completions``，填成完整接口地址会变成
    ``.../chat/completions/chat/completions``，服务端只回一个看不出原因的 404。
    """
    url = (raw or DEFAULT_BASE_URL).strip().rstrip("/")
    for suffix in ("/chat/completions", "/completions", "/embeddings"):
        if url.endswith(suffix):
            return url[: -len(suffix)].rstrip("/")
    return url


@dataclass(frozen=True)
class LLMSettings:
    """OpenAI 兼容的对话接口配置。"""

    base_url: str
    api_key: str
    model: str
    timeout_seconds: float
    temperature: float

    @classmethod
    def from_env(cls) -> "LLMSettings":
        return cls(
            base_url=normalize_base_url(_env_str("LLM_BASE_URL")),
            api_key=_env_str("LLM_API_KEY"),
            model=_env_str("LLM_MODEL", "gpt-4o-mini"),
            timeout_seconds=_env_float("LLM_TIMEOUT_SECONDS", 30.0),
            temperature=_env_float("LLM_TEMPERATURE", 0.2),
        )

    @property
    def configured(self) -> bool:
        return bool(self.api_key.strip())

    @property
    def endpoint(self) -> str:
        return f"{self.base_url}/chat/completions"


@dataclass(frozen=True)
class EmbeddingSettings:
    """向量化配置。

    local（默认）使用本地 BGE 语义模型；offline 使用 TF-IDF 测试替身。
    remote 强制调用远程 embeddings；auto 尝试远程，失败回退 TF-IDF。
    local 加载失败会报错，日志不会把词法向量标注为语义向量。
    """

    mode: str
    base_url: str
    api_key: str
    model: str
    dimensions: int
    batch_size: int
    timeout_seconds: float
    local_model: str = "BAAI/bge-small-zh-v1.5"

    @classmethod
    def from_env(cls) -> "EmbeddingSettings":
        llm = LLMSettings.from_env()
        mode = (_env_str("EMBEDDING_MODE", "local") or "local").lower()
        if mode not in {"local", "auto", "offline", "remote"}:
            mode = "local"
        return cls(
            mode=mode,
            base_url=normalize_base_url(_env_str("EMBEDDING_BASE_URL") or llm.base_url),
            api_key=_env_str("EMBEDDING_API_KEY") or llm.api_key,
            model=_env_str("EMBEDDING_MODEL", "text-embedding-3-small"),
            dimensions=_env_int("EMBEDDING_DIMENSIONS", 0),
            batch_size=max(1, _env_int("EMBEDDING_BATCH_SIZE", 32)),
            timeout_seconds=_env_float("EMBEDDING_TIMEOUT_SECONDS", 30.0),
            local_model=_env_str("EMBEDDING_LOCAL_MODEL", "BAAI/bge-small-zh-v1.5"),
        )

    @property
    def remote_ready(self) -> bool:
        return self.mode != "offline" and bool(self.api_key.strip())

    @property
    def endpoint(self) -> str:
        return f"{self.base_url}/embeddings"


@dataclass(frozen=True)
class RagSettings:
    """分块与检索参数。"""

    corpus_path: Path
    chunk_size: int
    chunk_overlap: int
    top_k: int
    min_score: float
    index_cache: Path
    use_cache: bool

    @classmethod
    def from_env(cls) -> "RagSettings":
        chunk_size = max(120, _env_int("RAG_CHUNK_SIZE", 420))
        overlap = max(0, _env_int("RAG_CHUNK_OVERLAP", 60))
        return cls(
            corpus_path=_env_path(
                "RAG_CORPUS_PATH", PROJECT_ROOT / "data" / "policy.txt"
            ),
            chunk_size=chunk_size,
            # 重叠必须小于块长，否则切分不收敛。
            chunk_overlap=min(overlap, chunk_size // 2),
            top_k=max(1, _env_int("RAG_TOP_K", 3)),
            # 相似度闸门。0.12 是照着当前语料与本地 TF-IDF 向量化标定的：
            # 真实命中的条款在 0.18~0.45，而知识库没覆盖的问题（如「海外直邮能退吗」）
            # 最高只有 0.07 左右。换成远程语义向量后分布不同，需要重新标定。
            min_score=_env_float(
                "RAG_MIN_SCORE",
                0.55 if _env_str("EMBEDDING_MODE", "local") == "local" else 0.12,
            ),
            index_cache=_env_path(
                "RAG_INDEX_CACHE", PROJECT_ROOT / ".index" / "policy-index.json"
            ),
            use_cache=_env_str("RAG_USE_CACHE", "1") not in {"0", "false", "False"},
        )


@dataclass(frozen=True)
class AgentSettings:
    """ReAct 循环配置。"""

    max_steps: int
    max_consecutive_errors: int
    observation_max_chars: int

    @classmethod
    def from_env(cls) -> "AgentSettings":
        return cls(
            max_steps=max(2, _env_int("AGENT_MAX_STEPS", 6)),
            max_consecutive_errors=max(1, _env_int("AGENT_MAX_CONSECUTIVE_ERRORS", 3)),
            # 观测结果回填给模型时必须截断：检索到的原文可能很长，
            # 整段塞回去会把上下文顶满，也会让模型开始复述噪声。
            # 默认值按「3 条政策条款 + JSON 外壳」估算，正常结果不会被切到；
            # 真被切了，react_format 的正则兜底仍能读出 ok 与错误码。
            observation_max_chars=max(
                400, _env_int("AGENT_OBSERVATION_MAX_CHARS", 3000)
            ),
        )


@dataclass(frozen=True)
class CatalogSettings:
    """模拟书目检索配置。"""

    default_limit: int
    max_limit: int
    #: 命中质量闸门：归一化得分低于该值的书不进结果。
    #: 没有闸门时，「Rust 异步编程」会因为「编程」二字命中一堆无关的书 ——
    #: 有结果但答非所问，比明确说「没查到」更糟。
    min_score: float

    @classmethod
    def from_env(cls) -> "CatalogSettings":
        return cls(
            default_limit=max(1, _env_int("CATALOG_DEFAULT_LIMIT", 3)),
            max_limit=max(1, _env_int("CATALOG_MAX_LIMIT", 10)),
            min_score=_env_float("CATALOG_MIN_SCORE", 1.0),
        )


LLM = LLMSettings.from_env()
EMBEDDING = EmbeddingSettings.from_env()
RAG = RagSettings.from_env()
AGENT = AgentSettings.from_env()
CATALOG = CatalogSettings.from_env()
