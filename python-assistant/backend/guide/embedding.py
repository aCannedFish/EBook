"""RAG 向量化实现。

默认使用预训练中文 BGE 模型生成 512 维稠密语义向量，并在本地 CPU 推理。
远程 OpenAI 兼容接口与本地 TF-IDF 作为可选模式保留。TF-IDF 是词法向量，
仅用于不下载模型的离线测试；正式演示使用语义 Embedding。
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import urllib.error
import urllib.request
from collections import Counter
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Protocol, Sequence

from .config import EMBEDDING, EmbeddingSettings

#: 中文连续片段。政策文本里专有词几乎都在 CJK 段内。
CJK_RUN_PATTERN = re.compile(r"[一-鿿]+")
#: 英文 / 数字 / 连字符片段，例如 spring、microservice、2026、e-bookstore。
WORD_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9\-_]*|\d+")


class EmbeddingError(RuntimeError):
    """向量化失败。"""

    def __init__(self, message: str, hint: str = "") -> None:
        super().__init__(message)
        self.hint = hint


#: 特征前缀。前缀用来区分特征类型，也顺带避免了不同类型的特征撞成同一个键。
UNIGRAM_PREFIX = "1:"
BIGRAM_PREFIX = "2:"
TRIGRAM_PREFIX = "3:"
WORD_PREFIX = "w:"

#: 各类型特征的权重：bigram / 整词是主特征，unigram 只作补充。
#: 中文查询很短（「拆了塑封还能退吗」只有 7 个 bigram），
#: 光靠 bigram 时，问句里「了塑」「封还」这种跨词边界的组合会稀释相似度 ——
#: 补上单字特征后，命中「塑」「封」「退」也能贡献分数；
#: 而常见单字（的、是、本）会被 IDF 压下去，不会引入新的噪声。
FEATURE_WEIGHTS = {
    UNIGRAM_PREFIX: 0.5,
    BIGRAM_PREFIX: 1.0,
    TRIGRAM_PREFIX: 1.0,
    WORD_PREFIX: 1.0,
}


def extract_features(text: str) -> list[str]:
    """把一段文本切成带类型前缀的特征。

    中文取单字 + 字符 bigram；英文数字取整词 + 字符 trigram
    （trigram 让 ``microservice`` 与 ``microservices`` 也能部分匹配）。
    """
    features: list[str] = []

    for run in CJK_RUN_PATTERN.findall(text):
        features.extend(f"{UNIGRAM_PREFIX}{char}" for char in run)
        if len(run) == 1:
            continue
        features.extend(
            f"{BIGRAM_PREFIX}{run[index : index + 2]}" for index in range(len(run) - 1)
        )

    for word in WORD_PATTERN.findall(text):
        lowered = word.lower()
        features.append(f"{WORD_PREFIX}{lowered}")
        if len(lowered) <= 3:
            continue
        features.extend(
            f"{TRIGRAM_PREFIX}{lowered[index : index + 3]}"
            for index in range(len(lowered) - 2)
        )

    return features


class Embedder(Protocol):
    """向量化实现需要满足的接口。"""

    @property
    def name(self) -> str: ...

    @property
    def dimensions(self) -> int: ...

    def fit(self, corpus_texts: Sequence[str]) -> "Embedder":
        """用索引语料校准权重（如 IDF）。默认实现返回自身。"""

    def embed(self, texts: Sequence[str]) -> list[list[float]]: ...


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    """余弦相似度。向量都已归一化时等价于点积，这里仍然做完整计算以防万一。"""
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    norm_left = math.sqrt(sum(a * a for a in left))
    norm_right = math.sqrt(sum(b * b for b in right))
    if norm_left == 0.0 or norm_right == 0.0:
        return 0.0
    return dot / (norm_left * norm_right)


@dataclass(frozen=True)
class TfidfEmbedder:
    """本地确定性向量化：词表 + TF-IDF + L2 归一化。

    维度就是语料词表大小，特征与维度一一对应，没有哈希碰撞。

    一开始的实现用的是「哈希技巧把特征压到 512 维」，结果相似度几乎全是噪声：
    政策库单块就有数百个特征（单字 + bigram + 英文 trigram），
    挤进 512 个桶时正负号互相抵消，连「拆了塑封还能退吗 → 第六条」这种
    明显的命中都排不到第一。语料只有几十块，词表撑死几千维，
    直接用精确词表又准又便宜，没有任何理由去做哈希近似。

    ``fit`` 用索引语料建词表并统计 IDF；查询时沿用同一个已 fit 的实例，
    所以「文档向量」和「查询向量」在同一个空间里。
    查询里出现语料从未有过的词时，它对相似度没有贡献 —— 这正是我们想要的语义：
    知识库没讲过的概念，不该把分数顶上去。
    """

    vocabulary: dict[str, int] = field(default_factory=dict)
    idf: dict[str, float] = field(default_factory=dict)

    @property
    def name(self) -> str:
        return f"local-tfidf-{len(self.vocabulary)}d"

    @property
    def dimensions(self) -> int:
        return len(self.vocabulary)

    def fit(self, corpus_texts: Sequence[str]) -> "TfidfEmbedder":
        """用索引语料建立词表并计算 IDF 权重：``log((1+N)/(1+df)) + 1``。

        平滑处理后，从未出现在语料里的特征权重最高，出现在每个块里的特征权重趋近 1，
        「本店」「商品」这类到处都有的词因此被压下去。
        """
        total = max(len(corpus_texts), 1)
        document_frequency: Counter[str] = Counter()
        for text in corpus_texts:
            document_frequency.update(set(extract_features(text)))
        # 排序后再编号：词表顺序固定，向量维度含义每次都一样。
        vocabulary = {
            feature: index for index, feature in enumerate(sorted(document_frequency))
        }
        idf = {
            feature: math.log((1 + total) / (1 + count)) + 1.0
            for feature, count in document_frequency.items()
        }
        return TfidfEmbedder(vocabulary=vocabulary, idf=idf)

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not self.vocabulary:
            raise EmbeddingError(
                "TfidfEmbedder 尚未 fit：词表为空，无法生成向量",
                hint="先用索引语料调用 fit()，再对文档与查询调用 embed()。",
            )
        return [self._vector(text) for text in texts]

    def _vector(self, text: str) -> list[float]:
        counts = Counter(extract_features(text))
        vector = [0.0] * len(self.vocabulary)

        for feature, count in counts.items():
            index = self.vocabulary.get(feature)
            if index is None:
                continue  # 语料里没有的特征：不进向量
            weight = (1.0 + math.log(count)) * FEATURE_WEIGHTS.get(feature[:2], 1.0)
            vector[index] = weight * self.idf.get(feature, 1.0)

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0.0:
            return vector
        return [value / norm for value in vector]


@lru_cache(maxsize=2)
def load_semantic_model(model_name: str):
    """共享 CPU 模型实例，避免每次构造 Agent 都重新加载模型权重。"""
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name, device="cpu")


class LocalSemanticEmbedder:
    """使用预训练中文 BGE 模型生成归一化的稠密语义向量。

    模型首次使用时下载到 Hugging Face 缓存，后续推理在本地 CPU 完成。
    v1.5 支持不加查询前缀的短文本检索；文档与查询使用同一编码器。
    加载失败时明确报错，避免把 TF-IDF 的结果误报为语义 Embedding。
    """

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        try:
            self._model = load_semantic_model(model_name)
        except Exception as error:
            raise EmbeddingError(
                f"无法加载本地 Embedding 模型 {model_name}：{type(error).__name__}",
                hint="安装 requirements.txt 并确认首次下载可访问 Hugging Face；"
                "可通过 EMBEDDING_LOCAL_MODEL 指定已下载的模型目录。",
            ) from error

    @property
    def name(self) -> str:
        return f"sentence-transformers:{self.model_name}"

    @property
    def dimensions(self) -> int:
        return int(self._model.get_sentence_embedding_dimension())

    def fit(self, corpus_texts: Sequence[str]) -> "LocalSemanticEmbedder":
        """使用预训练权重，无需在政策语料上重新训练。"""
        return self

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """批量编码并做 L2 归一化，让余弦分数可直接比较。"""
        if not texts:
            return []
        vectors = self._model.encode(
            list(texts),
            batch_size=16,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return vectors.tolist()


class OpenAIEmbedder:
    """调用 OpenAI 兼容 ``/embeddings`` 接口的向量化实现。

    只用标准库，避免为了一个 HTTP 调用再引入 SDK；请求体与官方接口一致。
    """

    def __init__(self, settings: EmbeddingSettings | None = None) -> None:
        self._settings = settings or EMBEDDING
        self._dimensions = self._settings.dimensions or 0

    @property
    def name(self) -> str:
        return f"openai:{self._settings.model}"

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def fit(self, corpus_texts: Sequence[str]) -> "OpenAIEmbedder":
        return self

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        batch_size = self._settings.batch_size
        for start in range(0, len(texts), batch_size):
            vectors.extend(self._embed_batch(list(texts[start : start + batch_size])))
        if vectors and not self._dimensions:
            self._dimensions = len(vectors[0])
        return vectors

    def _embed_batch(self, batch: list[str]) -> list[list[float]]:
        body: dict = {"model": self._settings.model, "input": batch}
        if self._settings.dimensions:
            body["dimensions"] = self._settings.dimensions
        request = urllib.request.Request(
            self._settings.endpoint,
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._settings.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(
                request, timeout=self._settings.timeout_seconds
            ) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")[:200]
            raise EmbeddingError(
                f"向量化接口返回 {error.code}：{detail}",
                hint=(
                    f"请求地址 {self._settings.endpoint}。403/404 通常表示该网关不提供 "
                    "embeddings 接口，改用 EMBEDDING_MODE=offline 或换一家支持 embedding 的服务商。"
                ),
            ) from error
        except urllib.error.URLError as error:
            raise EmbeddingError(
                f"无法连接向量化接口：{error.reason}",
                hint=f"检查网络，以及 EMBEDDING_BASE_URL（{self._settings.base_url}）是否可达。",
            ) from error

        data = payload.get("data") or []
        if len(data) != len(batch):
            raise EmbeddingError(
                f"向量化接口返回 {len(data)} 条结果，期望 {len(batch)} 条",
                hint="接口可能不支持批量输入，把 EMBEDDING_BATCH_SIZE 设为 1 再试。",
            )
        ordered = sorted(data, key=lambda item: item.get("index", 0))
        return [list(item.get("embedding") or []) for item in ordered]


class CachedEmbedder:
    """给任意实现加一层磁盘缓存。

    查询向量每次都要算，重复调用远程接口既慢又费钱；缓存键是
    ``模型名 + 文本哈希``，换了模型自然失效。
    """

    def __init__(self, inner: Embedder, cache_path: Path) -> None:
        self._inner = inner
        self._cache_path = cache_path
        self._cache: dict[str, list[float]] = {}
        self._dirty = False
        self._load()

    @property
    def name(self) -> str:
        return self._inner.name

    @property
    def dimensions(self) -> int:
        return self._inner.dimensions

    def fit(self, corpus_texts: Sequence[str]) -> "CachedEmbedder":
        inner = self._inner.fit(corpus_texts)
        # fit 之后模型名变了（多了 -idf），缓存键随之变化，不需要清理旧缓存。
        return (
            CachedEmbedder(inner, self._cache_path)
            if inner is not self._inner
            else self
        )

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        keys = [self._key(text) for text in texts]
        missing = [
            (key, text) for key, text in zip(keys, texts) if key not in self._cache
        ]
        if missing:
            fresh = self._inner.embed([text for _, text in missing])
            for (key, _), vector in zip(missing, fresh):
                self._cache[key] = vector
            self._dirty = True
            self._save()
        return [self._cache[key] for key in keys]

    # -- 内部 ---------------------------------------------------------------

    def _key(self, text: str) -> str:
        digest = hashlib.sha256(
            f"{self._inner.name}|{text}".encode("utf-8")
        ).hexdigest()
        return digest[:32]

    def _load(self) -> None:
        if not self._cache_path.is_file():
            return
        try:
            payload = json.loads(self._cache_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return
        if payload.get("embedder") == self._inner.name:
            self._cache = {
                key: list(value)
                for key, value in (payload.get("vectors") or {}).items()
            }

    def _save(self) -> None:
        if not self._dirty:
            return
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._cache_path.write_text(
            json.dumps(
                {"embedder": self._inner.name, "vectors": self._cache},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        self._dirty = False


def build_embedder(settings: EmbeddingSettings | None = None, with_cache: bool = True):
    """按配置构造向量化实现。返回 ``(embedder, describe)``。

    ``describe(name)`` 用最终的模型名生成一句说明，说明实际走了哪条路径
    （远程 / 本地 / 远程失败回退）。之所以要做成回调而不是直接返回字符串：
    本地实现的维度要 fit 之后才确定，名字在 fit 之前是不完整的，
    「启动日志里写着 0 维」这种自相矛盾的信息比没有信息更误导人。
    """
    settings = settings or EMBEDDING

    def wrap(inner: Embedder) -> Embedder:
        return (
            CachedEmbedder(inner, settings_cache_path(settings))
            if with_cache
            else inner
        )

    if settings.mode == "local":
        return (
            wrap(LocalSemanticEmbedder(settings.local_model)),
            lambda name: f"local:{name}（CPU 语义 Embedding）",
        )

    if settings.mode == "offline" or not settings.remote_ready:
        reason = (
            "EMBEDDING_MODE=offline"
            if settings.mode == "offline"
            else "未配置向量化接口密钥"
        )
        return wrap(TfidfEmbedder()), lambda name: f"local:{name}（{reason}）"

    remote = OpenAIEmbedder(settings)
    try:
        remote.embed(["探活"])
    except EmbeddingError as error:
        if settings.mode == "remote":
            raise
        # 先把错误文本取出来：except 块结束时 `error` 这个名字会被 Python 删掉，
        # 闭包里的 lambda 之后再引用它就会 NameError。
        reason = str(error)
        return (
            wrap(TfidfEmbedder()),
            lambda name: f"local:{name}（远程失败回退：{reason}）",
        )

    return wrap(remote), lambda name: f"remote:{name}"


def settings_cache_path(settings: EmbeddingSettings) -> Path:
    """缓存文件与索引缓存放同一个目录。"""
    from .config import RAG  # 局部导入，避免 config 与 embedding 互相引用

    return RAG.index_cache.parent / "embedding-cache.json"


def embed_all(embedder: Embedder, texts: Iterable[str]) -> list[list[float]]:
    return embedder.embed(list(texts))
