"""RAG 第四步：向量库与相似度检索。

政策库只有几十个块，用不着 FAISS 或向量数据库：一个列表装向量、
检索时逐条算余弦相似度，几十次浮点乘加在微秒级完成，
换成外部依赖只会让作业的复现成本变高。

``VectorStore`` 只做三件事：装块、按相似度排序、给出可解释的得分。
排序做了确定性处理（同分按块序号），这样每次运行的检索结果完全一致，
日志与文档里的引用才不会漂移。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from .chunking import Chunk
from .embedding import Embedder, cosine_similarity


@dataclass(frozen=True)
class ScoredChunk:
    """一条检索命中：块 + 相似度得分。"""

    chunk: Chunk
    score: float

    def to_dict(self, *, with_text: bool = True) -> dict:
        payload = {
            "id": self.chunk.id,
            "score": round(self.score, 4),
            "section": self.chunk.section,
            "clause": self.chunk.clause,
            "headingPath": self.chunk.heading_path,
            "charStart": self.chunk.char_start,
            "charEnd": self.chunk.char_end,
        }
        if with_text:
            payload["text"] = self.chunk.text
        return payload


class VectorStore:
    """内存向量库。"""

    def __init__(self, chunks: Sequence[Chunk], vectors: Sequence[Sequence[float]], embedder_name: str) -> None:
        if len(chunks) != len(vectors):
            raise ValueError(f"块数 {len(chunks)} 与向量数 {len(vectors)} 不一致")
        self._chunks = list(chunks)
        self._vectors = [list(vector) for vector in vectors]
        self.embedder_name = embedder_name

    def __len__(self) -> int:
        return len(self._chunks)

    @property
    def chunks(self) -> list[Chunk]:
        return list(self._chunks)

    @property
    def dimensions(self) -> int:
        return len(self._vectors[0]) if self._vectors else 0

    def search(
        self,
        query_vector: Sequence[float],
        top_k: int = 3,
        min_score: float = 0.0,
    ) -> list[ScoredChunk]:
        """返回相似度最高的若干块。

        ``min_score`` 是「检索不到就别硬答」的闸门：低于阈值的块不进结果，
        让上层工具能明确地告诉模型「知识库没覆盖这个问题」，
        而不是把一段不相关的政策塞给它当依据。
        """
        scored = [
            ScoredChunk(chunk=chunk, score=cosine_similarity(query_vector, vector))
            for chunk, vector in zip(self._chunks, self._vectors)
        ]
        scored = [item for item in scored if item.score >= min_score]
        scored.sort(key=lambda item: (-item.score, item.chunk.index))
        return scored[: max(top_k, 0)]

    def to_dict(self) -> dict:
        return {
            "embedder": self.embedder_name,
            "dimensions": self.dimensions,
            "count": len(self._chunks),
            "chunks": [chunk.to_dict() for chunk in self._chunks],
            "vectors": [[round(value, 6) for value in vector] for vector in self._vectors],
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "VectorStore":
        chunks = [
            Chunk(
                id=item["id"],
                index=item["index"],
                text=item["text"],
                section=item["section"],
                clause=item["clause"],
                char_start=item["charStart"],
                char_end=item["charEnd"],
            )
            for item in payload.get("chunks", [])
        ]
        return cls(chunks, payload.get("vectors", []), str(payload.get("embedder", "")))

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "VectorStore | None":
        if not path.is_file():
            return None
        try:
            return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError, KeyError):
            return None


def build_store(embedder: Embedder, chunks: Sequence[Chunk]) -> VectorStore:
    vectors = embedder.embed([chunk.text for chunk in chunks])
    return VectorStore(chunks=chunks, vectors=vectors, embedder_name=embedder.name)
