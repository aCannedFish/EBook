"""命令行入口：交互问答、RAG 自检与内置演示。

# 交互式对话（配了 API Key 走真实模型，否则用离线替身模型）
python -m backend.cli

# 跑一遍内置的五个场景，打印完整的 Thought → Action → Observation 链路
python -m backend.cli --demo

# 顺带导出链路 JSON，供生成作业文档使用
python -m backend.cli --demo --json ../docs/demo-trace.json

# 看 RAG 索引规模：语料、分块、向量维度、检索示例
python -m backend.cli --stats

# 单次提问
python -m backend.cli "我想买一本关于微服务的书，另外如果我买了不喜欢，拆了塑封还能退吗？"
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .agent import AgentResult, ReActAgent, ReActStep
from .config import LLM, RAG
from .llm import LocalReActLLM, build_client
from .rag import RagPipeline
from .tools import BookstoreTools, build_registry

#: 五个演示场景，覆盖作业要求的复杂交互 Case 与各类失败路径。
DEMO_SCENARIOS: tuple[tuple[str, str], ...] = (
    (
        "复杂交互 Case：找书 + 拆封退货（作业示例）",
        "我想买一本关于微服务的书，另外如果我买了不喜欢，拆了塑封还能退吗？",
    ),
    (
        "带过滤条件 + 会员多跳检索：预算、现货、金卡权益",
        "我想买一本 100 元以内的微服务书，最好有现货；另外我是金卡会员，拆了塑封还能退吗？",
    ),
    (
        "只查书：单一意图，一次工具调用就够",
        "有没有讲 Kubernetes 的书？",
    ),
    (
        "只查政策：两个政策问题分别检索",
        "退货运费谁承担？另外金卡会员有什么折扣？",
    ),
    (
        "检索失败自纠错：目录里没有 Rust 书，放宽关键词重试",
        "有没有讲 Rust 的书？",
    ),
)


def make_agent(
    use_remote: bool | None = None, tools: BookstoreTools | None = None, on_step=None
):
    """构造 Agent。返回 ``(agent, 模型模式说明)``。"""
    if use_remote is None:
        # 没配 API Key 就用离线替身模型：整条链路照跑，只是「模型」这一层是规则实现。
        use_remote = LLM.configured

    client = build_client() if use_remote else LocalReActLLM()
    mode = f"remote:{LLM.model}" if use_remote else "offline:rule-based"
    registry = build_registry(tools)
    return ReActAgent(client=client, registry=registry, on_step=on_step), mode


def print_step(step: ReActStep) -> None:
    """打印一步 ReAct 链路。"""
    print(f"  [{step.index}] Thought: {step.thought or '（模型未给出推理）'}")
    print(f"      Action: {step.action}")
    print(f"      Action Input: {json.dumps(step.arguments, ensure_ascii=False)}")
    if step.parse_error:
        print(f"      （解析错误：{step.parse_error}）")
    payload = step.payload or {}
    if step.ok and step.action == "query_store_policy":
        print(
            f"      Observation: 命中 {payload.get('count')} 条条款，"
            f"最高相似度 {payload.get('topScore')}"
        )
        for passage in payload.get("passages", []):
            print(
                f"        - [{passage['id']}] {passage['headingPath']}（{passage['score']}）"
            )
    elif step.ok and step.action == "search_book_catalog":
        titles = "、".join(
            f"《{book['title']}》" for book in payload.get("results", [])
        )
        print(f"      Observation: 命中 {payload.get('count')} 本：{titles}")
    else:
        print(f"      Observation: {json.dumps(payload, ensure_ascii=False)}")
    if step.ok:
        print("      Observation JSON:")
        for line in json.dumps(payload, ensure_ascii=False, indent=2).splitlines():
            print(f"        {line}")
    print(f"      （耗时 {step.duration_ms} ms）")


def print_stats(tools: BookstoreTools | None = None) -> dict:
    """打印 RAG 索引与书目规模。"""
    tools = tools or BookstoreTools()
    pipeline = RagPipeline()
    index = pipeline.build()
    stats = index.stats()
    print("=" * 88)
    print("RAG 索引")
    print("-" * 88)
    print(
        f"  文档      ：{stats['document']['title']}（{stats['document']['source']}）"
    )
    print(
        f"  语料规模  ：{stats['document']['chars']} 字符 / {stats['document']['lines']} 行"
    )
    print(
        f"  分块      ：{stats['count']} 块，平均 {stats['avgChars']} 字符"
        f"（{stats['minChars']} ~ {stats['maxChars']}）"
    )
    print(f"  章节数    ：{stats['sections']}")
    print(f"  向量化    ：{stats['embedder']}，维度 {stats['dimensions']}")
    print(f"  向量化路径：{stats['embedderNote']}")
    print(f"  索引指纹  ：{stats['fingerprint']}（缓存命中：{stats['fromCache']}）")
    print(
        f"  书目      ：{len(tools.catalog)} 本，"
        f"分类 {len(tools.catalog.categories())} 个"
    )

    print("-" * 88)
    print(f"检索示例（阈值 {RAG.min_score}，返回 {RAG.top_k} 条）")
    for question in ("拆了塑封还能退吗", "金卡会员有什么折扣", "退货运费谁承担"):
        passages = index.retrieve(question)
        heads = "、".join(
            f"{item.chunk.heading_path}({item.score:.3f})" for item in passages
        )
        print(f"  「{question}」-> {heads or '无命中'}")
    print()
    return stats


def run_scenario(title: str, question: str, use_remote: bool | None = None) -> dict:
    print("=" * 88)
    print(f"场景：{title}")
    print(f"用户：{question}")
    print("-" * 88)

    agent, mode = make_agent(use_remote=use_remote)
    result: AgentResult = agent.run(question)

    for step in result.steps:
        print_step(step)
    print("-" * 88)
    print(f"助手（{mode}，{result.rounds} 轮，结束原因 {result.stopped_reason}）：")
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
    agent, mode = make_agent()
    print(f"E-BookStore 导购助手（ReAct，{mode}）。输入 exit 退出。")
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
        result = agent.run(question)
        for step in result.steps:
            print_step(step)
        print(f"助手：{result.reply}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="E-BookStore 导购助手（RAG + ReAct）")
    parser.add_argument("question", nargs="?", help="单次提问；省略则进入交互模式")
    parser.add_argument("--demo", action="store_true", help="跑内置的五个演示场景")
    parser.add_argument("--stats", action="store_true", help="打印 RAG 索引与检索示例")
    parser.add_argument(
        "--offline",
        action="store_true",
        help="使用规则对话模型；Embedding 由 EMBEDDING_MODE 单独配置",
    )
    parser.add_argument(
        "--remote", action="store_true", help="强制使用真实模型接口（需要 LLM_API_KEY）"
    )
    parser.add_argument(
        "--rebuild-index", action="store_true", help="忽略缓存重建政策索引"
    )
    parser.add_argument("--json", dest="json_out", type=Path, help="把链路导出为 JSON")
    args = parser.parse_args(argv)

    if args.offline and args.remote:
        parser.error("--offline 与 --remote 不能同时使用")
    use_remote = False if args.offline else (True if args.remote else None)

    tools = BookstoreTools()
    if args.rebuild_index:
        tools.ensure_index(force=True)

    if args.stats:
        print_stats(tools)
        return 0

    if args.demo:
        return run_demo(args.json_out, use_remote=use_remote)

    if args.question:
        agent, mode = make_agent(use_remote=use_remote, tools=tools, on_step=print_step)
        result = agent.run(args.question)
        print(f"助手（{mode}）：{result.reply}")
        return 0

    return run_repl()


if __name__ == "__main__":
    sys.exit(main())
