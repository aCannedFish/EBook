"""RAG 第二步：分块（Chunking）。

政策文档是有层级结构的：章 → 条 → 款。切块顺着这个结构走，比按固定字数硬切好，
因为「一条政策」天然就是检索的最小完整语义单元 —— 切在条款边界上，
检索到的内容不会前后不着村。

策略（``split_into_chunks``）：

1. 先按 ``第X章`` 切出章，章标题记进 ``section``；
2. 章内按 ``第X条`` 切出条，条标题记进 ``clause``；
3. 条款正文超过 ``chunk_size`` 时，再按句子边界（。；）切分，块间保留
   ``chunk_overlap`` 个字符的重叠，避免一句话的上下文被切断；
4. 过短的条款（少于 ``MIN_CHUNK_CHARS``）与同章相邻条款合并，避免产生
   只装了标题、没有任何内容的碎块；
5. 每块的文本前面回填「书名 · 章 · 条」的路径 —— 这一行会一起参与向量化，
   让「第十五条讲了什么」这类问法也能命中。

分块结果 ``Chunk`` 里同时留下字符区间（``char_start`` / ``char_end``），
引用时可以精确指回原文位置。
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .corpus import PolicyDocument

#: 章标题：第一章、第二章 …
CHAPTER_PATTERN = re.compile(r"^第[一二三四五六七八九十百零\d]+章")
#: 条标题：第一条【目的】
CLAUSE_PATTERN = re.compile(r"^第[一二三四五六七八九十百零\d]+条")
#: 句子边界。中文里「；」分隔的并列款通常是完整意思，也当作边界。
SENTENCE_PATTERN = re.compile(r"[^。！？；\n]*[。！？；\n]?")

#: 短于这个长度的块会尝试与相邻块合并。
MIN_CHUNK_CHARS = 60


@dataclass(frozen=True)
class Chunk:
    """一个可被检索的最小单元。"""

    id: str
    index: int
    text: str
    section: str
    clause: str
    char_start: int
    char_end: int

    @property
    def heading_path(self) -> str:
        parts = [part for part in (self.section, self.clause) if part]
        return " · ".join(parts)

    @property
    def char_count(self) -> int:
        return len(self.text)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "index": self.index,
            "section": self.section,
            "clause": self.clause,
            "headingPath": self.heading_path,
            "charStart": self.char_start,
            "charEnd": self.char_end,
            "chars": self.char_count,
            "text": self.text,
        }


@dataclass
class _RawBlock:
    """切分中间态：一段带标题路径的正文。"""

    section: str
    clause: str
    text: str
    char_start: int


def _split_sentences(text: str) -> list[str]:
    return [
        piece
        for piece in (match.group(0) for match in SENTENCE_PATTERN.finditer(text))
        if piece
    ]


def _slice_long_block(
    block: _RawBlock, chunk_size: int, overlap: int
) -> list[_RawBlock]:
    """把超长正文按句子边界切成多段，段间保留重叠。"""
    sentences = _split_sentences(block.text)
    pieces: list[_RawBlock] = []
    buffer = ""
    cursor = block.char_start

    for sentence in sentences:
        if buffer and len(buffer) + len(sentence) > chunk_size:
            pieces.append(
                _RawBlock(block.section, block.clause, buffer.strip(), cursor)
            )
            # 下一段从当前段尾部回退 overlap 个字符，保证跨段的句子仍有上下文。
            tail = buffer[-overlap:] if overlap > 0 else ""
            cursor = cursor + len(buffer) - len(tail)
            buffer = tail + sentence
        else:
            buffer += sentence

    if buffer.strip():
        pieces.append(_RawBlock(block.section, block.clause, buffer.strip(), cursor))
    return pieces or [block]


def _split_clauses(text: str, offset: int) -> list[_RawBlock]:
    """按条切分；第一条之前的抬头文字归入「前言」。"""
    blocks: list[_RawBlock] = []
    section = ""
    clause = ""
    buffer: list[str] = []
    buffer_start = offset
    cursor = offset

    def flush() -> None:
        nonlocal buffer
        if buffer:
            blocks.append(
                _RawBlock(section, clause, "\n".join(buffer).strip(), buffer_start)
            )
            buffer = []

    for line in text.splitlines():
        stripped = line.strip()
        line_start = cursor
        cursor += len(line) + 1  # splitlines 丢掉的换行符补回来，字符区间才和原文对得上

        if not stripped:
            continue
        if CHAPTER_PATTERN.match(stripped):
            flush()
            section = stripped
            clause = ""
            continue
        if CLAUSE_PATTERN.match(stripped):
            flush()
            clause = stripped
            buffer = [stripped]
            buffer_start = line_start
            continue
        if not buffer:
            buffer_start = line_start
        buffer.append(stripped)

    flush()
    return blocks


def _merge_short_blocks(blocks: list[_RawBlock], chunk_size: int) -> list[_RawBlock]:
    """过短的块并入同章相邻块，避免出现只有标题没有内容的碎块。"""
    merged: list[_RawBlock] = []
    for block in blocks:
        previous = merged[-1] if merged else None
        combine_length = len(previous.text) + len(block.text) + 1 if previous else 0
        if (
            previous is not None
            and previous.section == block.section
            and len(previous.text) < MIN_CHUNK_CHARS
            and combine_length <= chunk_size
        ):
            merged[-1] = _RawBlock(
                previous.section,
                previous.clause,
                f"{previous.text}\n{block.text}",
                previous.char_start,
            )
            continue
        merged.append(block)
    return merged


def split_into_chunks(
    document: PolicyDocument,
    chunk_size: int = 320,
    chunk_overlap: int = 60,
) -> list[Chunk]:
    """把政策文档切成带标题路径的块。"""
    if chunk_size <= 0:
        raise ValueError("chunk_size 必须为正整数")
    overlap = min(max(chunk_overlap, 0), chunk_size // 2)

    blocks = _split_clauses(document.text, 0)
    blocks = _merge_short_blocks(blocks, chunk_size)

    pieces: list[_RawBlock] = []
    for block in blocks:
        if len(block.text) > chunk_size:
            pieces.extend(_slice_long_block(block, chunk_size, overlap))
        else:
            pieces.append(block)

    chunks: list[Chunk] = []
    for index, piece in enumerate(pieces):
        prefix = f"《{document.label}》"
        for part in (piece.section, piece.clause):
            if part:
                prefix += f" {part}"
        text = f"{prefix}\n{piece.text}".strip()
        chunks.append(
            Chunk(
                id=f"policy-{index:04d}",
                index=index,
                text=text,
                section=piece.section,
                clause=piece.clause,
                char_start=piece.char_start,
                char_end=piece.char_start + len(piece.text),
            )
        )
    return chunks


def chunk_stats(chunks: list[Chunk]) -> dict:
    """分块统计，文档里用来量化说明切分结果。"""
    if not chunks:
        return {"count": 0, "avgChars": 0, "minChars": 0, "maxChars": 0, "sections": 0}
    lengths = [chunk.char_count for chunk in chunks]
    return {
        "count": len(chunks),
        "avgChars": round(sum(lengths) / len(lengths)),
        "minChars": min(lengths),
        "maxChars": max(lengths),
        "sections": len({chunk.section for chunk in chunks if chunk.section}),
    }
