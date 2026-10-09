#!/usr/bin/env python3
"""用真实大模型跑一遍 ReAct 链路，作为离线演示之外的补充证据。

离线替身模型（``LocalReActLLM``）保证链路可复现，但它终归是规则实现；
这份日志回答的是另一个问题：换成一个真正的模型、只给它同一份提示词，
它会不会自己走出同一条「先查书、再查政策」的链路。

密钥来源，按优先级：
1. 环境变量 ``LLM_API_KEY``；
2. 本目录的 ``.env``；
3. 主仓库 ``python-assistant/.env``（课程网关的配置通常放在那里）。

都没有时不报错，只打印一行说明并正常退出 —— 采集脚本不该因为没配密钥就整体失败。

用法：
    python3 scripts/run_remote_demo.py
"""

from __future__ import annotations

import os
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

#: 密钥来源。注意必须在本进程导入 backend.config 之前设置好环境变量 ——
#: 配置是模块导入时读走的，导入之后再设就晚了。
DOTENV_CANDIDATES = (
    ROOT / ".env",
    ROOT.parent / "python-assistant" / ".env",
)

QUESTIONS = (
    (
        "复杂交互 Case：找书 + 拆封退货",
        "我想买一本关于微服务的书，另外如果我买了不喜欢，拆了塑封还能退吗？",
    ),
    (
        "预算、现货与会员权益",
        "我想买一本 100 元以内的微服务书，最好有现货；另外我是金卡会员，拆了塑封还能退吗？",
    ),
)


def load_env_file(path: Path) -> None:
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if not separator:
            continue
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key.startswith("LLM_") and key not in os.environ:
            os.environ[key] = value


def main() -> int:
    for candidate in DOTENV_CANDIDATES:
        load_env_file(candidate)

    if not os.environ.get("LLM_API_KEY", "").strip():
        print(
            "未找到 LLM_API_KEY（环境变量、本目录 .env、python-assistant/.env 都没有）。"
        )
        print("本次跳过真实模型演示；离线替身模型的链路见 docs/logs/demo.txt。")
        return 0

    # 向量化保持本地语义模型：本演示同时验证真实模型与 RAG 工具，
    # 与向量化走远程还是本地无关，固定本地能让两次运行的检索结果完全一致。
    os.environ.setdefault("EMBEDDING_MODE", "local")

    from backend.cli import make_agent, print_step

    print(
        f"模型：{os.environ.get('LLM_MODEL', '(未设置)')} @ {os.environ.get('LLM_BASE_URL', '')}"
    )
    print()

    traces = []
    for title, question in QUESTIONS:
        print("=" * 88)
        print(f"场景：{title}")
        print(f"用户：{question}")
        print("-" * 88)

        agent, mode = make_agent(use_remote=True)
        result = agent.run(question)
        for step in result.steps:
            print_step(step)
        print("-" * 88)
        print(f"助手（{mode}，{result.rounds} 轮，结束原因 {result.stopped_reason}）：")
        for line in result.reply.splitlines():
            print(f"  {line}")
        print()
        traces.append({"title": title, "modelMode": mode, **result.to_dict()})
        if result.stopped_reason != "completed":
            raise RuntimeError(f"真实模型演示未完成：{result.stopped_reason}")
        actions = result.actions
        if (
            not actions
            or actions[0] != "search_book_catalog"
            or "query_store_policy" not in actions[1:]
        ):
            raise RuntimeError("真实模型演示没有按顺序完成查书与查政策")
    trace_path = ROOT / "docs" / "remote-trace.json"
    trace_path.write_text(
        json.dumps(traces, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
