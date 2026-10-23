"""命令行入口：交互问答与内置演示。

    # 交互式对话（有 API Key 走真实模型，没有则用离线替身模型）
    python -m backend.cli

    # 跑一遍内置的演示场景，打印完整链路
    python -m backend.cli --demo

    # 顺带把链路导出成 JSON，供生成文档使用
    python -m backend.cli --demo --json ../docs/demo-trace.json

    # 单次提问
    python -m backend.cli "ISBN为978-3-00-000000-4 的书还有多少本？"
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .assistant.agent import AssistantStep, UnifiedAssistant
from .assistant.offline import LocalUnifiedLLM
from .assistant.tools import UnifiedRegistry
from .catalog import build_inventory_backend
from .config import LLM
from .guide.catalog import DEFAULT_CATALOG
from .guide.tools import BookstoreTools as GuideBookstoreTools
from .llm import build_client
from .tools import BookstoreTools as InventoryToolset

#: 演示场景覆盖作业2 与作业3 要求的全部形态：正常库存、非法 ISBN 自纠、
#: 上游瞬时故障重试、上游整体不可用、找书 + 政策两跳。
DEMO_SCENARIOS: tuple[tuple[str, str], ...] = (
    (
        "正常链路：本店库存 + 竞品比价",
        "帮我查一下 ISBN为978-3-00-000000-4 的书还有多少本，顺便看看别家卖多少钱",
    ),
    (
        "非法入参：ISBN 位数不对，模型按错误提示向用户确认",
        "ISBN为12345 的书还有多少本，顺便看看别家卖多少钱",
    ),
    (
        "上游抖动：比价接口第一次超时，重试后成功",
        "ISBN为978-7-00-000000-8 的书还有几本？另外帮我对比一下其他平台的价格",
    ),
    (
        "上游故障：比价渠道整体不可用，重试无意义，应如实告知",
        "ISBN为978-2-00-000000-3 的库存和竞品价格分别是多少",
    ),
    (
        "找书 + 政策：先查书目，再检索退换货政策",
        "我想买一本关于微服务的书，另外如果我买了不喜欢，拆了塑封还能退吗？",
    ),
)


def make_assistant(
    use_remote: bool | None = None,
    on_step=None,
) -> tuple[UnifiedAssistant, str]:
    """构造合并后的助手。返回 (助手, 模型模式)。"""
    if use_remote is None:
        use_remote = LLM.configured

    registry = UnifiedRegistry(
        inventory_tools=InventoryToolset(inventory=build_inventory_backend()),
        guide_tools=GuideBookstoreTools(catalog=DEFAULT_CATALOG),
    )
    client = build_client() if use_remote else LocalUnifiedLLM()
    mode = f"remote:{LLM.model}" if use_remote else "offline:rule-based"
    return UnifiedAssistant(client=client, registry=registry, on_step=on_step), mode


def print_trace(step: AssistantStep) -> None:
    """打印一步 ReAct 链路：Thought / Action / Observation。"""
    print(f"  │ Thought: {step.thought or '（模型未给出推理）'}")
    print(f"  │ Action: {step.action}({json.dumps(step.arguments, ensure_ascii=False)})")
    print(f"  │ Observation: {step.observation}")
    print(f"  │ 耗时 {step.duration_ms} ms")


def run_scenario(title: str, question: str, use_remote: bool | None = None) -> dict:
    print("=" * 88)
    print(f"场景：{title}")
    print(f"用户：{question}")
    print("-" * 88)

    assistant, mode = make_assistant(use_remote=use_remote)
    result = assistant.chat(question)

    for step in result.steps:
        print_trace(step)

    print(f"助手（{mode}，共 {result.rounds} 轮，结束原因 {result.stopped_reason}）：")
    for line in result.reply.splitlines():
        print(f"  {line}")
    print()

    return {"title": title, "modelMode": mode, **result.to_dict()}


def run_demo(json_out: Path | None, use_remote: bool | None = None) -> int:
    traces = [
        run_scenario(title, question, use_remote=use_remote)
        for title, question in DEMO_SCENARIOS
    ]
    if json_out is not None:
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text(
            json.dumps(traces, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"链路已导出：{json_out}")
    return 0


def run_repl() -> int:
    assistant, mode = make_assistant()
    print(f"E-BookStore 客服助手（{mode}）。输入 exit 退出。")
    history: list[dict] = []
    while True:
        try:
            question = input("\n你：").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if question.lower() in {"exit", "quit", "q"}:
            return 0
        if not question:
            continue

        result = assistant.chat(question, history=history)
        for step in result.steps:
            print_trace(step)
        print(f"助手：{result.reply}")
        # 只把问答文本带进下一轮；工具轨迹由服务端按每次请求重新执行。
        history.extend(
            [
                {"role": "user", "content": question},
                {"role": "assistant", "content": result.reply},
            ]
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="E-BookStore 客服助手")
    parser.add_argument("question", nargs="?", help="单次提问；省略则进入交互模式")
    parser.add_argument("--demo", action="store_true", help="跑内置演示场景")
    parser.add_argument("--offline", action="store_true", help="强制使用离线替身模型")
    parser.add_argument(
        "--remote", action="store_true", help="强制使用真实模型接口（需要 LLM_API_KEY）"
    )
    parser.add_argument("--json", dest="json_out", type=Path, help="把链路导出为 JSON")
    args = parser.parse_args(argv)

    if args.offline and args.remote:
        parser.error("--offline 与 --remote 不能同时使用")
    use_remote = False if args.offline else (True if args.remote else None)

    if args.demo:
        return run_demo(args.json_out, use_remote=use_remote)

    if args.question:
        assistant, mode = make_assistant(use_remote=use_remote, on_step=print_trace)
        result = assistant.chat(args.question)
        print(f"助手（{mode}）：{result.reply}")
        return 0

    return run_repl()


if __name__ == "__main__":
    sys.exit(main())
