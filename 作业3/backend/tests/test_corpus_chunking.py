"""知识库加载与分块的测试。"""

from __future__ import annotations

import pytest

from backend.chunking import Chunk, chunk_stats, split_into_chunks
from backend.corpus import CorpusError, PolicyDocument, clean_text, load_policy_document


class TestCorpus:
    def test_loads_policy_document(self, document):
        assert "退换货" in document.title
        assert document.label == "退换货与会员政策"
        assert document.char_count > 3000
        assert document.metadata["生效日期"] == "2026-03-01"
        assert document.source.endswith("data/policy.txt")

    def test_removes_layout_decoration(self):
        raw = "标题\n───────\n第一条【目的】\n正文内容\n──\n\n\n\n第二条【范围】\n更多内容"
        cleaned = clean_text(raw)
        assert "─" not in cleaned
        assert "\n\n\n" not in cleaned
        assert "第一条【目的】" in cleaned

    def test_missing_file_reports_hint(self, tmp_path):
        with pytest.raises(CorpusError) as error:
            load_policy_document(tmp_path / "nope.txt")
        assert "RAG_CORPUS_PATH" in error.value.hint

    def test_empty_file_is_rejected(self, tmp_path):
        path = tmp_path / "empty.txt"
        path.write_text("   \n\n", encoding="utf-8")
        with pytest.raises(CorpusError):
            load_policy_document(path)


class TestChunking:
    def test_every_clause_becomes_a_chunk(self, document, chunks):
        clauses = {chunk.clause for chunk in chunks if chunk.clause}
        # 政策正文一共 25 条，逐条切分后应当一条不落。
        assert len(clauses) == 25
        assert all(chunk.text.startswith("《退换货与会员政策》") for chunk in chunks)

    def test_chunk_text_carries_heading_path(self, chunks):
        target = next(chunk for chunk in chunks if chunk.clause.startswith("第六条"))
        assert "第二章" in target.text
        assert "第六条【塑封与拆封规则】" in target.text
        assert target.section == "第二章  退换货政策"

    def test_chunks_respect_size_limit(self, document, chunks):
        # 前缀行是检索用的引用头，不计入正文长度限制。
        for chunk in chunks:
            assert len(chunk.text) <= 420 + 60

    def test_chunk_ids_and_ranges(self, chunks):
        assert [chunk.index for chunk in chunks] == list(range(len(chunks)))
        assert [chunk.id for chunk in chunks] == [
            f"policy-{i:04d}" for i in range(len(chunks))
        ]
        assert all(chunk.char_end > chunk.char_start for chunk in chunks)
        # 字符区间递增：块是按原文顺序切出来的。
        starts = [chunk.char_start for chunk in chunks]
        assert starts == sorted(starts)

    def test_split_is_deterministic(self, document):
        first = split_into_chunks(document, chunk_size=300, chunk_overlap=40)
        second = split_into_chunks(document, chunk_size=300, chunk_overlap=40)
        assert [chunk.text for chunk in first] == [chunk.text for chunk in second]

    def test_long_clause_is_split_with_overlap(self):
        body = "".join(
            f"第{index}句：这是用于验证重叠切分的句子。" for index in range(20)
        )
        document = PolicyDocument(
            title="测试政策",
            label="测试政策",
            source="memory",
            text=f"第一条【超长条款】\n{body}",
            metadata={},
        )
        pieces = split_into_chunks(document, chunk_size=120, chunk_overlap=30)
        assert len(pieces) > 1
        for previous, current in zip(pieces, pieces[1:]):
            tail = previous.text[-30:]
            head = current.text[: 30 + len("《测试政策》 第一条【超长条款】\n")]
            # 上一块的尾部内容应当出现在下一块里，保证跨块的语义不被切断。
            assert tail[-10:] in head or tail[-10:] in current.text

    def test_rejects_invalid_chunk_size(self, document):
        with pytest.raises(ValueError):
            split_into_chunks(document, chunk_size=0)

    def test_stats_shape(self, chunks):
        stats = chunk_stats(chunks)
        assert stats["count"] == len(chunks)
        assert stats["minChars"] <= stats["avgChars"] <= stats["maxChars"]
        assert stats["sections"] == 5
        assert chunk_stats([])["count"] == 0

    def test_chunk_to_dict_roundtrip_fields(self):
        chunk = Chunk(
            id="policy-0001",
            index=1,
            text="文本",
            section="第一章",
            clause="第一条【目的】",
            char_start=10,
            char_end=12,
        )
        payload = chunk.to_dict()
        assert payload["headingPath"] == "第一章 · 第一条【目的】"
        assert payload["chars"] == 2
