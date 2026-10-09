"""生成作业1的提交文档与提交压缩包。

文档只写作业要求的内容：完整 Prompt、多轮对话截图、最终生成的 JSON 规范文件。
正文套进课程作业模版（template.docx），输出文件名与压缩包名都用「学号-作业1」。

Prompt 正文由 dialog/turns.json 现场读取，规范正文由 openapi.json 现场读取，
所以改了 Prompt 或改了规范，重跑一次脚本，文档就跟着更新。

用法：
    python3 scripts/build_docx.py
    STUDENT_ID=... STUDENT_NAME=... python3 scripts/build_docx.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from docx_template import check_template, render_docx, zip_files  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

STUDENT_ID = os.environ.get("STUDENT_ID", "524031910113")
STUDENT_NAME = os.environ.get("STUDENT_NAME", "俞冠廷")

SPEC_PATH = ROOT / "openapi.json"
TURNS_PATH = ROOT / "dialog" / "turns.json"
TEMPLATE = ROOT / "template.docx"
DOC_MD = ROOT / "dialog" / "doc.md"
DOCX = ROOT / f"{STUDENT_ID}-作业1.docx"
ZIP = ROOT / f"{STUDENT_ID}-作业1.zip"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def build_markdown(spec: dict, turns: dict) -> str:
    out: list[str] = []
    add = out.append

    # 模型回复里含 ```json 代码块，外层围栏用四个反引号，否则会被内层提前闭合。
    def quoted(text: str) -> None:
        add("````text")
        add(text)
        add("````")
        add("")

    add("## 一、完整 Prompt 与多轮对话")
    add("")

    system_messages = [
        message
        for round_data in turns["rounds"]
        for message in round_data["messages"]
        if message["role"] == "user" and "System Prompt" in message["label"]
    ]
    confirmations = [
        message
        for round_data in turns["rounds"]
        for message in round_data["messages"]
        if message["role"] == "assistant" and round_data["id"] == "01"
    ]

    add("### 1.1 System Prompt")
    add("")
    for message in system_messages:
        quoted(message["text"])
    for message in confirmations:
        add("模型确认：")
        add("")
        quoted(message["text"])

    add("### 1.2 多轮对话")
    add("")
    index = 0
    for round_data in turns["rounds"]:
        user_messages = [
            message
            for message in round_data["messages"]
            if message["role"] == "user" and "System Prompt" not in message["label"]
        ]
        if not user_messages:
            continue

        index += 1
        add(f"**第 {index} 轮　{round_data['title'].split('·')[-1].strip()}**")
        add("")
        for message in user_messages:
            add("用户：")
            add("")
            quoted(message["text"])
        for message in round_data["messages"]:
            if message["role"] == "assistant":
                add("助手：")
                add("")
                quoted(message["text"])

    add("## 二、最终生成的 OpenAPI 3.0 规范")
    add("")
    add("以下 JSON 即随压缩包提交的 `openapi.json`，可直接被 Swagger Editor / Swagger UI 加载。")
    add("")
    add("```json")
    add(SPEC_PATH.read_text(encoding="utf-8").rstrip())
    add("```")
    add("")

    return "\n".join(out)


def main() -> int:
    check_template(TEMPLATE)

    spec = load(SPEC_PATH)
    turns = load(TURNS_PATH)
    DOC_MD.write_text(build_markdown(spec, turns), encoding="utf-8")

    render_docx(
        DOC_MD,
        TEMPLATE,
        DOCX,
        student_id=STUDENT_ID,
        student_name=STUDENT_NAME,
        homework_no="1",
    )
    print(f"{DOCX.name}  已生成（{DOCX.stat().st_size / 1024:.0f} KB）")

    # 提交要求：文档 + 最终 JSON 规范文件。文件名按「学号-作业1」。
    zip_files(ZIP, [(DOCX, DOCX.name), (SPEC_PATH, SPEC_PATH.name)])
    print(f"{ZIP.name}  已生成（{ZIP.stat().st_size / 1024:.0f} KB）")
    print(f"中间稿：{DOC_MD.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
