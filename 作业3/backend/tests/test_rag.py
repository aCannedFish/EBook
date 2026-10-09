"""RAG 流程（加载 → 分块 → 向量化 → 建库 → 检索）与缓存的测试。"""

from __future__ import annotations

from dataclasses import replace

from backend.chunking import split_into_chunks
from backend.config import RAG
from backend.corpus import PolicyDocument
from backend.rag import RagPipeline, compute_fingerprint, format_passages


class TestIndexBuild:
    def test_stats_describe_the_index(self, index):
        stats = index.stats()
        assert stats["count"] == len(index.chunks) >= 26
        assert stats["dimensions"] == index.store.dimensions > 500
        assert stats["document"]["chars"] > 3000
        assert stats["fromCache"] is False
        assert stats["fingerprint"]

    def test_fingerprint_is_stable_and_content_sensitive(self, index, document):
        assert compute_fingerprint(document, index.embedder.name, RAG) == index.fingerprint
        other = replace(RAG, chunk_size=RAG.chunk_size + 1)
        assert compute_fingerprint(document, index.embedder.name, other) != index.fingerprint

    def test_fingerprint_ignores_non_content_metadata(self, index, document):
        """缓存指纹只认语料内容与参数，不认路径之类的元信息。"""
        renamed = PolicyDocument(
            title="另一个标题",
            label=document.label,
            source="/tmp/other.txt",
            text=document.text,
            metadata={"生效日期": "1999-01-01"},
        )
        assert compute_fingerprint(renamed, index.embedder.name, RAG) == index.fingerprint


class TestRetrieval:
    def test_finds_the_sealing_clause(self, index):
        hits = index.retrieve("拆了塑封还能退吗")
        assert hits
        assert hits[0].chunk.clause.startswith("第六条")

    def test_finds_the_member_benefit_clause(self, index):
        hits = index.retrieve("会员已拆封退货权益", top_k=2)
        assert hits[0].chunk.clause.startswith("第二十条")

    def test_respects_top_k(self, index):
        assert len(index.retrieve("退货", top_k=2)) <= 2

    def test_uncovered_question_returns_nothing(self, index):
        assert index.retrieve("海外直邮的书可以退吗") == []

    def test_blank_question_returns_nothing(self, index):
        assert index.retrieve("   ") == []

    def test_scores_are_sorted_and_bounded(self, index):
        hits = index.retrieve("退货运费谁承担", top_k=3)
        scores = [hit.score for hit in hits]
        assert scores == sorted(scores, reverse=True)
        assert all(0 < score <= 1 for score in scores)

    def test_format_passages_for_observation(self, index):
        text = format_passages(index.retrieve("拆了塑封还能退吗"))
        assert "[policy-" in text
        assert "第六条" in text
        assert "相似度" in text


class TestIndexCache:
    def test_cache_is_reused_and_invalidated(self, tmp_path, document):
        settings = replace(RAG, index_cache=tmp_path / "policy-index.json", use_cache=True)
        pipeline = RagPipeline(settings=settings)

        first = pipeline.build()
        assert first.from_cache is False

        second = pipeline.build()
        assert second.from_cache is True
        assert second.fingerprint == first.fingerprint
        assert [chunk.text for chunk in second.chunks] == [chunk.text for chunk in first.chunks]

        # 改了分块参数：指纹变了，缓存必须失效。
        changed = RagPipeline(settings=replace(settings, chunk_size=260))
        assert changed.build().from_cache is False

        assert pipeline.build(force=True).from_cache is False

    def test_cache_disabled_never_reads_disk(self, tmp_path):
        settings = replace(RAG, index_cache=tmp_path / "policy-index.json", use_cache=False)
        pipeline = RagPipeline(settings=settings)
        assert pipeline.build().from_cache is False
        assert pipeline.build().from_cache is False
        assert not settings.index_cache.exists()

    def test_corrupt_cache_falls_back_to_rebuild(self, tmp_path):
        settings = replace(RAG, index_cache=tmp_path / "policy-index.json", use_cache=True)
        settings.index_cache.parent.mkdir(parents=True, exist_ok=True)
        settings.index_cache.write_text("{ 不是合法 JSON", encoding="utf-8")
        assert RagPipeline(settings=settings).build().from_cache is False


def test_embedder_path_note_is_reported(index):
    assert index.embedder_note.startswith("local:")
    assert index.embedder.name in index.embedder_note


def test_chunk_count_matches_chunker(document, index):
    assert len(index.chunks) == len(split_into_chunks(document, RAG.chunk_size, RAG.chunk_overlap))
