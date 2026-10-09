"""向量化与向量库的测试。"""

from __future__ import annotations

import math

import pytest

from backend.config import EmbeddingSettings
from backend.embedding import (
    BIGRAM_PREFIX,
    UNIGRAM_PREFIX,
    EmbeddingError,
    OpenAIEmbedder,
    LocalSemanticEmbedder,
    TfidfEmbedder,
    build_embedder,
    cosine_similarity,
    extract_features,
)
from backend.vector_store import VectorStore, build_store


class TestFeatureExtraction:
    def test_chinese_produces_unigrams_and_bigrams(self):
        features = extract_features("塑封")
        assert f"{UNIGRAM_PREFIX}塑" in features
        assert f"{BIGRAM_PREFIX}塑封" in features

    def test_english_produces_word_and_trigrams(self):
        features = extract_features("Microservice")
        assert "w:microservice" in features
        assert "3:mic" in features

    def test_short_english_word_is_kept_whole(self):
        features = extract_features("Go")
        assert features == ["w:go"]

    def test_digits_are_features(self):
        assert "w:2026" in extract_features("2026 年生效")


class TestTfidfEmbedder:
    def test_requires_fit(self):
        with pytest.raises(EmbeddingError) as error:
            TfidfEmbedder().embed(["随便一句话"])
        assert "fit" in error.value.hint

    def test_dimensions_match_vocabulary(self, chunks, embedder):
        assert embedder.dimensions == len(embedder.vocabulary) > 500
        assert embedder.name == f"local-tfidf-{embedder.dimensions}d"

    def test_vectors_are_normalized(self, embedder):
        vector = embedder.embed(["塑封已拆还能退吗"])[0]
        assert math.isclose(
            math.sqrt(sum(value * value for value in vector)), 1.0, rel_tol=1e-9
        )

    def test_embedding_is_deterministic(self, chunks):
        texts = [chunk.text for chunk in chunks[:5]]
        first = TfidfEmbedder().fit(texts).embed(texts)
        second = TfidfEmbedder().fit(texts).embed(texts)
        assert first == second

    def test_idf_downweights_common_features(self, chunks):
        """「本店」几乎每块都有，「塑封」只在少数块里，后者的权重必须更高。"""
        embedder = TfidfEmbedder().fit([chunk.text for chunk in chunks])
        assert (
            embedder.idf[f"{BIGRAM_PREFIX}塑封"] > embedder.idf[f"{BIGRAM_PREFIX}本店"]
        )

    def test_unknown_feature_does_not_enter_vector(self, chunks, embedder):
        known = embedder.embed(["塑封拆封规则"])[0]
        padded = embedder.embed(["塑封拆封规则 zzzzqqqq 不存在的词"])[0]
        # 语料里没有的特征不进向量，只有已知特征的权重被重新归一化。
        assert sum(padded) != 0
        assert known != padded

    def test_relevance_ranking(self, chunks, embedder):
        """「拆了塑封还能退吗」必须比「发票怎么开」更接近第六条。"""
        target = next(chunk for chunk in chunks if chunk.clause.startswith("第六条"))
        other = next(chunk for chunk in chunks if chunk.clause.startswith("第二十二条"))
        query = embedder.embed(["拆了塑封还能退吗"])[0]
        target_vector = embedder.embed([target.text])[0]
        other_vector = embedder.embed([other.text])[0]
        assert (
            cosine_similarity(query, target_vector)
            > cosine_similarity(query, other_vector) * 2
        )


class TestCosineSimilarity:
    def test_identical_vectors(self):
        assert math.isclose(cosine_similarity([1.0, 2.0], [1.0, 2.0]), 1.0)

    def test_orthogonal_vectors(self):
        assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0

    def test_zero_and_mismatched_vectors(self):
        assert cosine_similarity([], [1.0]) == 0.0
        assert cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0
        assert cosine_similarity([1.0, 2.0], [1.0]) == 0.0


class TestLocalSemanticEmbedder:
    """验证语义模型加载、编码配置与失败处理；真实模型由采集脚本验证。"""

    def test_uses_cpu_model_and_normalized_batch_encoding(self, monkeypatch):
        import numpy as np

        captured = {}

        class FakeModel:
            """只记录编码请求，不下载模型权重。"""

            def get_sentence_embedding_dimension(self):
                return 2

            def encode(self, texts, **kwargs):
                captured.update(texts=texts, **kwargs)
                return np.array([[0.6, 0.8] for _ in texts])

        monkeypatch.setattr(
            "backend.embedding.load_semantic_model", lambda name: FakeModel()
        )
        embedder = LocalSemanticEmbedder("test-model")
        assert embedder.embed(["拆了塑封还能退吗"]) == [[0.6, 0.8]]
        assert captured["normalize_embeddings"] is True
        assert captured["texts"] == ["拆了塑封还能退吗"]
        assert embedder.dimensions == 2
        assert embedder.embed([]) == []

    def test_load_failure_does_not_silently_become_tfidf(self, monkeypatch):
        def fail(name):
            raise OSError("model unavailable")

        monkeypatch.setattr("backend.embedding.load_semantic_model", fail)
        with pytest.raises(EmbeddingError, match="无法加载本地"):
            LocalSemanticEmbedder("missing-model")


class TestEmbedderSelection:
    """``build_embedder`` 的三条路径：本地、远程、远程失败回退。"""

    def settings(self, mode: str) -> EmbeddingSettings:
        return EmbeddingSettings(
            mode, "http://x/v1", "secret", "text-embedding-3-small", 0, 8, 5.0
        )

    def test_offline_mode_uses_local_embedder(self):
        embedder, describe = build_embedder(self.settings("offline"), with_cache=False)
        assert isinstance(embedder, TfidfEmbedder)
        assert "EMBEDDING_MODE=offline" in describe(embedder.fit(["塑封"]).name)

    def test_missing_key_uses_local_embedder(self):
        settings = EmbeddingSettings("auto", "http://x/v1", "", "m", 0, 8, 5.0)
        embedder, describe = build_embedder(settings, with_cache=False)
        assert isinstance(embedder, TfidfEmbedder)
        assert "未配置" in describe(embedder.fit(["塑封"]).name)

    def test_remote_success_reports_remote(self, monkeypatch):
        monkeypatch.setattr(
            OpenAIEmbedder, "embed", lambda self, texts: [[1.0, 0.0]] * len(texts)
        )
        embedder, describe = build_embedder(self.settings("auto"), with_cache=False)
        assert isinstance(embedder, OpenAIEmbedder)
        assert describe(embedder.name) == "remote:openai:text-embedding-3-small"

    def test_remote_failure_falls_back_to_local(self, monkeypatch):
        """回归用例：回退说明里引用了 except 块里的变量，闭包稍后再取值会 NameError。"""

        def boom(self, texts):
            raise EmbeddingError("接口返回 403", hint="该网关不提供 embeddings")

        monkeypatch.setattr(OpenAIEmbedder, "embed", boom)
        embedder, describe = build_embedder(self.settings("auto"), with_cache=False)
        assert isinstance(embedder, TfidfEmbedder)
        note = describe(embedder.fit(["塑封已拆"]).name)
        assert "远程失败回退" in note
        assert "403" in note

    def test_remote_mode_propagates_failure(self, monkeypatch):
        def boom(self, texts):
            raise EmbeddingError("接口返回 403")

        monkeypatch.setattr(OpenAIEmbedder, "embed", boom)
        with pytest.raises(EmbeddingError):
            build_embedder(self.settings("remote"), with_cache=False)


class TestVectorStore:
    def test_search_orders_by_similarity(self, chunks, embedder):
        store = build_store(embedder, chunks)
        query = embedder.embed(["金卡会员有几次已拆封退货权益"])[0]
        hits = store.search(query, top_k=3, min_score=0.0)
        assert len(hits) == 3
        assert hits[0].score >= hits[1].score >= hits[2].score
        assert hits[0].chunk.clause.startswith("第二十条")

    def test_min_score_filters_weak_hits(self, chunks, embedder):
        store = build_store(embedder, chunks)
        query = embedder.embed(["海外直邮的书可以退吗"])[0]
        assert store.search(query, top_k=3, min_score=0.9) == []

    def test_mismatched_lengths_are_rejected(self, chunks, embedder):
        with pytest.raises(ValueError):
            VectorStore(chunks=chunks, vectors=[], embedder_name="x")

    def test_serialization_roundtrip(self, chunks, embedder):
        store = build_store(embedder, chunks)
        restored = VectorStore.from_dict(store.to_dict())
        assert len(restored) == len(store)
        assert restored.chunks[0].text == chunks[0].text
        query = embedder.embed(["退货运费谁承担"])[0]
        assert [item.chunk.id for item in restored.search(query, 3, 0.0)] == [
            item.chunk.id for item in store.search(query, 3, 0.0)
        ]

    def test_search_without_text_option(self, chunks, embedder):
        store = build_store(embedder, chunks)
        hit = store.search(embedder.embed(["退货流程"])[0], 1, 0.0)[0]
        assert "text" not in hit.to_dict(with_text=False)
