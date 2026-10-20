"""RAG 第一步：文档加载。

作业要求「准备一份书店的退换货与会员政策文本文档」。知识库原文放在
``data/policy.txt``，本模块负责把它读成结构化的 ``PolicyDocument``：

- 去掉分隔线、页码标记这类只服务于排版的装饰行，保留条款正文；
- 记录标题、版本、生效日期与来源路径，供检索结果里做引用（Citation）;
- 统计字符数与行数，用于在文档里报告知识库规模。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .config import RAG


class CorpusError(RuntimeError):
    """知识库文件缺失或不可读。"""

    def __init__(self, message: str, hint: str) -> None:
        super().__init__(message)
        self.hint = hint


#: 只服务于排版的装饰行：整行由分隔线、页码或空白组成。
#: 政策原文用 ─（U+2500）画分隔线，中文文档里也常用 ── 或 ——，都要认。
DECORATION_PATTERN = re.compile(r"^[\s\-—_=*·─━│┄┅]+$")
#: 文档头部的「文档编号：…」「生效日期：…」这类元信息行。
META_PATTERN = re.compile(r"^(文档编号|生效日期|适用范围|版本)\s*[:：]\s*(.+)$")


@dataclass(frozen=True)
class PolicyDocument:
    """一份待索引的政策文档。

    ``title`` 是完整抬头（店名 + 文档名），``label`` 是用于引用时写在块首的短名。
    块首那一行会一起参与向量化，所以它得是「人也能看懂、检索也能命中」的形式。
    """

    title: str
    label: str
    source: str
    text: str
    metadata: dict[str, str]

    @property
    def char_count(self) -> int:
        return len(self.text)

    @property
    def line_count(self) -> int:
        return len(self.text.splitlines())

    def to_summary(self) -> dict:
        return {
            "title": self.title,
            "label": self.label,
            "source": self.source,
            "chars": self.char_count,
            "lines": self.line_count,
            **self.metadata,
        }


def clean_text(raw: str) -> str:
    """去掉排版装饰，压缩多余空行，统一换行符。"""
    lines = [line.replace("\r\n", "\n").rstrip() for line in raw.splitlines()]
    kept = [line for line in lines if not DECORATION_PATTERN.match(line)]
    text = "\n".join(kept)
    # 连续 3 个以上空行压成 1 个空行：原文用空行分段，多留没有意义。
    return re.sub(r"\n{3,}", "\n\n", text).strip("\n")


def load_policy_document(path: Path | None = None) -> PolicyDocument:
    """读取知识库原文。

    :raises CorpusError: 文件不存在或读不出内容
    """
    path = path or RAG.corpus_path
    if not path.is_file():
        raise CorpusError(
            f"知识库文件不存在：{path}",
            hint="确认 data/policy.txt 存在，或用环境变量 RAG_CORPUS_PATH 指定别的路径。",
        )

    raw = path.read_text(encoding="utf-8")
    text = clean_text(raw)
    if not text:
        raise CorpusError(
            f"知识库文件内容为空：{path}",
            hint="检查文件是否被清空或编码不是 UTF-8。",
        )

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    heading = lines[:3]
    title = " ".join(heading[:2]) if len(heading) >= 2 else (heading[0] if heading else path.stem)
    # 引用用的短名取第二行（「退换货与会员政策（知识库原文）」），抬头第一行是店名。
    subject = heading[1] if len(heading) >= 2 and not META_PATTERN.match(heading[1]) else ""
    label = subject.split("（")[0].strip() or (heading[0] if heading else path.stem)

    metadata: dict[str, str] = {}
    for line in text.splitlines()[:20]:
        matched = META_PATTERN.match(line.strip())
        if matched:
            metadata[matched.group(1)] = matched.group(2).strip()

    return PolicyDocument(
        title=title,
        label=label,
        source=str(path),
        text=text,
        metadata=metadata,
    )
