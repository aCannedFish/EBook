#!/usr/bin/env python3
"""把 dialog/turns.json 导出成 prompts.md。

提交文档里的 Prompt 与多轮对话由 build_docx.py 直接读 turns.json 生成，
这个脚本只是额外导出一份纯文本，方便复制粘贴到别处。

用法：
    python3 scripts/build_prompts.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TURNS = ROOT / "dialog" / "turns.json"
OUTPUT = ROOT / "prompts.md"


def main() -> int:
    data = json.loads(TURNS.read_text(encoding="utf-8"))

    lines = [
        "# 作业1 Prompt 与多轮对话全文",
        "",
        "由 `python3 scripts/build_prompts.py` 从 `dialog/turns.json` 生成，",
        "与提交文档中的内容一致。",
        "",
        f"对话模型：{data['model']}",
        "",
    ]
    for round_data in data["rounds"]:
        lines.append(f"## {round_data['title']}")
        lines.append("")
        for message in round_data["messages"]:
            lines.append(f"### {message['label']}")
            lines.append("")
            lines.append(message["text"])
            lines.append("")

    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"{OUTPUT.relative_to(ROOT)}  已生成（{OUTPUT.stat().st_size / 1024:.0f} KB）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
