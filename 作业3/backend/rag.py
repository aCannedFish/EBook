"""RAG 流程门面：加载 → 分块 → 向量化 → 建库 → 检索。

``RagPipeline.build()`` 把四步串起来，并在 ``.index/`` 下缓存结果：
缓存指纹由「语料内容 + 分块参数 + 向量化模型名」三者算出来，
任何一项变了指纹就变，旧缓存自动失效 —— 不会出现「改了政策文档，
检索结果还是旧的」这种最难查的问题。缓存只影响启动耗时，不影响结果。

``RagIndex.retrieve()`` 是工具层 ``query_store_policy`` 唯一依赖的入口。
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Sequence

from .chunking import Chunk, chunk_stats, split_into_chunks
from .config import EMBEDDING, RAG, EmbeddingSettings, RagSettings
from .corpus import PolicyDocument, load_policy_document
from .embedding import Embedder, build_embedder
from .vector_store import ScoredChunk, VectorStore, build_store


def compute_fingerprint(
    document: PolicyDocument,
    embedder_name: str,
    settings: RagSettings,
) -> str:
    """索引指纹：语料内容与全部影响结果的参数。"""
    digest = hashlib.sha256()
    digest.update(document.text.encode("utf-8"))
    digest.update(f"|size={settings.chunk_size}|overlap={settings.chunk_overlap}".encode("utf-8"))
    digest.update(f"|embedder={embedder_name}".encode("utf-8"))
    return digest.hexdigest()[:16]


@dataclass
class RagIndex:
    """建好的索引：块、向量与元数据。"""

    document: PolicyDocument
    chunks: list[Chunk]
    store: VectorStore
    embedder: Embedder
    embedder_note: str
    fingerprint: str
    from_cache: bool = False

    def stats(self) -> dict:
        return {
            "document": self.document.to_summary(),
            "embedder": self.embedder.name,
            "embedderNote": self.embedder_note,
            "dimensions": self.store.dimensions,
            "fingerprint": self.fingerprint,
            "fromCache": self.from_cache,
            **chunk_stats(self.chunks),
        }

    def retrieve(
        self,
        question: str,
        top_k: int | None = None,
        min_score: float | None = None,
    ) -> list[ScoredChunk]:
        settings = RAG
        top_k = settings.top_k if top_k is None else top_k
        min_score = settings.min_score if min_score is None else min_score
        if not question.strip():
            return []
        query_vector = self.embedder.embed([question])[0]
        return self.store.search(query_vector, top_k=top_k, min_score=min_score)

    def to_cache(self) -> dict:
        return {
            "fingerprint": self.fingerprint,
            "embedderNote": self.embedder_note,
            "document": self.document.to_summary(),
            "store": self.store.to_dict(),
        }


@dataclass
class RagPipeline:
    """加载语料、建索引、缓存与复用的入口。"""

    settings: RagSettings = RAG
    embedding_settings: EmbeddingSettings = EMBEDDING
    #: 记录上一次构建用的说明（本地 / 远程 / 回退），启动日志会打印。
    last_note: str = field(default="", init=False)

    def build(self, force: bool = False) -> RagIndex:
        document = load_policy_document(self.settings.corpus_path)
        embedder, describe_path = build_embedder(
            self.embedding_settings, with_cache=self.settings.use_cache
        )

        # 先分块，因为指纹里的向量化模型名只有 fit 之后才稳定
        #（本地实现 fit 出词表后维度才是确定的）。
        chunks = split_into_chunks(
            document,
            chunk_size=self.settings.chunk_size,
            chunk_overlap=self.settings.chunk_overlap,
        )
        fitted = embedder.fit([chunk.text for chunk in chunks])
        note = describe_path(fitted.name)
        self.last_note = note
        fingerprint = compute_fingerprint(document, fitted.name, self.settings)

        if not force and self.settings.use_cache:
            cached = self._load_cache(fingerprint, document)
            if cached is not None:
                cached.embedder = fitted
                cached.embedder_note = note
                return cached

        store = build_store(fitted, chunks)
        index = RagIndex(
            document=document,
            chunks=chunks,
            store=store,
            embedder=fitted,
            embedder_note=note,
            fingerprint=fingerprint,
            from_cache=False,
        )
        self._save_cache(index)
        return index

    def _load_cache(self, fingerprint: str, document: PolicyDocument) -> RagIndex | None:
        path = self.settings.index_cache
        if not path.is_file():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
        if payload.get("fingerprint") != fingerprint:
            return None
        store = VectorStore.from_dict(payload.get("store") or {})
        if len(store) == 0:
            return None
        return RagIndex(
            document=document,
            chunks=store.chunks,
            store=store,
            embedder=None,  # 由 build() 回填
            embedder_note=str(payload.get("embedderNote", "")),
            fingerprint=fingerprint,
            from_cache=True,
        )

    def _save_cache(self, index: RagIndex) -> None:
        if not self.settings.use_cache:
            return
        try:
            path = self.settings.index_cache
            path.parent.mkdir(parents=True, exist_ok=True)
            # 写的是带指纹与说明的完整索引，不是裸的向量库 ——
            # 「写进去的格式」和「读出来的格式」必须一致，否则缓存永远读不中。
            path.write_text(
                json.dumps(index.to_cache(), ensure_ascii=False), encoding="utf-8"
            )
        except OSError:
            # 缓存写不进去不该影响检索本身：目录只读、磁盘满都只是「下次重建」而已。
            pass


def build_index(force: bool = False, pipeline: RagPipeline | None = None) -> RagIndex:
    return (pipeline or RagPipeline()).build(force=force)


def format_passages(passages: Sequence[ScoredChunk]) -> str:
    """把检索结果拼成给模型看的引用块（Observation 里用）。"""
    blocks = []
    for item in passages:
        blocks.append(f"[{item.chunk.id}] {item.chunk.heading_path}（相似度 {item.score:.3f}）\n{item.chunk.text}")
    return "\n\n".join(blocks)
