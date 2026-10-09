#!/usr/bin/env python3
"""把终端输出渲染成图片，用于文档里贴「ReAct 链路」「RAG 自检」与「测试结果」。

渲染的是真实执行结果：本脚本只负责排版，不负责编造内容。
输入文件由 scripts/collect_logs.sh 用真实命令生成。

用法：
    python3 scripts/capture_terminal.py
"""

from __future__ import annotations

import html
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
LOGS = ROOT / "docs" / "logs"
SHOTS = ROOT / "docs" / "screenshots"

BROWSERS = [
    Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
    Path("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"),
]

WIDTH = 1400
MAX_HEIGHT = 12000

#: (输出文件名, 输入日志文件, 窗口标题)
TARGETS = [
    ("terminal-server-log.png", "server.log", "uvicorn backend.server:app — 服务端日志"),
    ("terminal-agent-demo.png", "demo.txt", "python -m backend.cli --demo — 五个场景的完整 ReAct 链路"),
    ("terminal-rag-stats.png", "rag-stats.txt", "python -m backend.cli --stats — 知识库与检索自检"),
    ("terminal-tests.png", "tests.txt", "python -m pytest backend/tests -q — 单元测试"),
]

PAGE = """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>{title}</title>
<style>
  body {{ margin: 0; background: #0d1117; }}
  .term {{ width: {width}px; font-family: "SF Mono", Menlo, Consolas, monospace; }}
  .bar {{ display: flex; align-items: center; gap: 10px; padding: 12px 18px;
          background: #161b22; border-bottom: 1px solid #30363d; }}
  .dots {{ display: flex; gap: 7px; }}
  .dots i {{ width: 12px; height: 12px; border-radius: 50%; display: block; }}
  .dots i:nth-child(1) {{ background: #ff5f57; }}
  .dots i:nth-child(2) {{ background: #febc2e; }}
  .dots i:nth-child(3) {{ background: #28c840; }}
  .bar span {{ color: #8b949e; font-size: 13px; }}
  pre {{ margin: 0; padding: 18px 20px 22px; color: #c9d1d9; font-size: 12.5px;
         line-height: 1.65; white-space: pre-wrap; overflow-wrap: anywhere; }}
</style></head>
<body><div class="term">
  <div class="bar"><div class="dots"><i></i><i></i><i></i></div><span>{title}</span></div>
  <pre>{body}</pre>
</div></body></html>
"""


def find_browser() -> Path:
    for candidate in BROWSERS:
        if candidate.exists():
            return candidate
    found = shutil.which("google-chrome") or shutil.which("chromium")
    if found:
        return Path(found)
    raise SystemExit("找不到 Chrome / Edge，无法截图")


def shoot(browser: Path, page_path: Path, out_path: Path) -> tuple[int, int]:
    height = 600
    while height <= MAX_HEIGHT:
        subprocess.run(
            [
                str(browser), "--headless=new", "--disable-gpu", "--hide-scrollbars",
                "--force-device-scale-factor=2", "--virtual-time-budget=3000",
                f"--window-size={WIDTH},{height}", f"--screenshot={out_path}",
                page_path.as_uri(),
            ],
            capture_output=True, check=False,
        )
        with Image.open(out_path) as image:
            rgb = image.convert("RGB")
            background = rgb.getpixel((5, rgb.height - 5))
            bottom = 0
            for y in range(rgb.height - 1, -1, -1):
                row = rgb.crop((0, y, rgb.width, y + 1)).getcolors(maxcolors=1 << 16)
                if row is None or not (len(row) == 1 and row[0][1] == background):
                    bottom = y
                    break
            if bottom >= rgb.height - 12:
                height = int(height * 1.6) + 200
                continue
            cropped = rgb.crop((0, 0, rgb.width, min(rgb.height, bottom + 8)))
            cropped.save(out_path)
            return cropped.size
    raise SystemExit(f"内容过高，无法截图：{out_path.name}")


def main() -> int:
    browser = find_browser()
    SHOTS.mkdir(parents=True, exist_ok=True)

    missing = [name for _, name, _ in TARGETS if not (LOGS / name).exists()]
    if missing:
        raise SystemExit(f"缺少日志文件 {missing}，请先运行 scripts/collect_logs.sh")

    with tempfile.TemporaryDirectory() as tmp:
        for filename, source, title in TARGETS:
            body = html.escape((LOGS / source).read_text(encoding="utf-8").rstrip())
            page_path = Path(tmp) / f"{filename}.html"
            page_path.write_text(
                PAGE.format(title=html.escape(title), width=WIDTH, body=body), encoding="utf-8"
            )
            out_path = SHOTS / filename
            width, height = shoot(browser, page_path, out_path)
            print(f"{filename}  {width}x{height}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
