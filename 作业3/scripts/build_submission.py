"""从本次运行证据生成 Markdown 报告和作业3提交压缩包。

压缩包使用明确的文件白名单，排除旧报告、其他作业、第三方依赖、模型权重、
环境密钥及运行缓存。清单记录各文件的 SHA-256，便于核对证据与提交源码。
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STUDENT_ID = os.environ.get("STUDENT_ID", "524031910113")
STUDENT_NAME = os.environ.get("STUDENT_NAME", "俞冠廷")
REPORT = ROOT / f"{STUDENT_ID}-作业3.md"
ARCHIVE = ROOT / f"{STUDENT_ID}-作业3.zip"
SCRIPT_FILES = (
    "collect_evidence.py",
    "collect_logs.sh",
    "run_remote_demo.py",
    "build_submission.py",
)
DOC_FILES = (
    "demo-trace.json",
    "remote-trace.json",
    "rag-evidence.json",
    "policy-vectors.json",
    "http-evidence.json",
    "evidence-status.json",
)
LOG_FILES = ("tests.txt", "demo.txt", "rag-stats.txt", "server.log", "demo-remote.txt")


def load_json(name: str):
    """读取采集脚本产出的证据，缺失时停止构建。"""
    return json.loads((ROOT / "docs" / name).read_text(encoding="utf-8"))


def render_trace(trace: dict) -> str:
    """按原有顺序展示决策、动作参数和完整工具返回值。"""
    lines = [
        f"用户：{trace['question']}",
        "",
        f"模型模式：{trace['modelMode']}",
        "",
        "```text",
    ]
    for step in trace["steps"]:
        lines.extend(
            [
                f"[{step['index']}] Thought: {step['thought']}",
                f"Action: {step['action']}",
                "Action Input: " + json.dumps(step["arguments"], ensure_ascii=False),
                "Observation: "
                + json.dumps(step["result"], ensure_ascii=False, indent=2),
                "",
            ]
        )
    lines.extend([f"Final Answer: {trace['reply']}", "```", ""])
    return "\n".join(lines)


def build_report() -> str:
    """把评分要求、实现与实际验证证据组织成可直接阅读的报告。"""
    status = load_json("evidence-status.json")
    rag = load_json("rag-evidence.json")
    stats = rag["stats"]
    offline = load_json("demo-trace.json")
    remote = load_json("remote-trace.json") if status["remoteModelVerified"] else []
    tests = (ROOT / "docs/logs/tests.txt").read_text(encoding="utf-8").strip()
    if not re.search(r"\d+ passed", tests) or re.search(r"\d+ failed", tests):
        raise RuntimeError("当前测试日志没有证明全部通过")
    main_trace = remote[0] if remote else offline[0]
    actions = [step["action"] for step in main_trace["steps"]]
    assert actions[0] == "search_book_catalog" and "query_store_policy" in actions[1:]
    assert main_trace["stoppedReason"] == "completed"
    lines = [
        "# 作业3",
        "",
        "课程：应用系统体系架构",
        "",
        f"学号：{STUDENT_ID}　姓名：{STUDENT_NAME}",
        "",
        "## 任务",
        "",
        "实现书店导购 Agent，根据顾客的自然语言需求推荐图书，并通过 RAG 检索书店的退换货与会员政策。"
        "Agent 按 ReAct 协议逐步调用工具，使用真实工具返回的 Observation 生成最终答复。",
        "",
        "本次提交采用独立的作业3目录，沿用当前项目已有的 Python Agent、工具注册和 HTTP 服务结构。"
        "模拟书目不依赖 Spring Boot 或数据库，评阅时可直接运行。政策、书目、库存和价格均为作业模拟数据。",
        "",
        f"证据采集时间：{status['collectedAt']}（UTC+08:00）。",
        "",
        "## 要求核对",
        "",
        "| 评分要求 | 实现 | 运行证据 |",
        "|---|---|---|",
        "| 文档加载、切分与 Embedding | corpus.py、chunking.py、embedding.py | data/policy.txt、docs/policy-vectors.json、rag-stats.txt |",
        "| 可用的 RAG 工具 | rag.py、vector_store.py、query_store_policy | rag-evidence.json、http-evidence.json |",
        "| 完整 ReAct 循环 | agent.py、react_format.py | 复杂示例的多轮执行链路与 test_agent.py |",
        "| 按意图先后调用工具 | 模型输出 Action，ToolRegistry 派发 | 主例先 search_book_catalog，再 query_store_policy |",
        "| 清晰执行日志 | CLI 和 HTTP 均记录 Thought、Action、Observation | docs/logs/demo-remote.txt、demo.txt、server.log |",
        "",
        "## 政策语料",
        "",
        "原文位于 data/policy.txt，包含退换货、退款运费、会员等级、折扣积分、拆封退货权益与附则。"
        "普通拆封退货规则见第六条，质量问题例外见第七条，金卡和钻石会员权益见第二十条。"
        "这三个条款使复杂示例既能回答一般规则，也能说明适用条件与例外。",
        "",
        f"加载后共 {stats['document']['chars']} 字符、{stats['document']['lines']} 行，"
        f"分为 {stats['sections']} 章、{stats['count']} 个块。",
        "",
        "## RAG 流程",
        "",
        "1. 加载 UTF-8 政策文档，清除装饰分隔线，保留条款、标题和版本信息。",
        "2. 按章节与条款分块；超长条款按句子拆分，正文窗口上限 420 字符，重叠 60 字符。"
        "每个块附加章节与条款标题，保留块编号与原文偏移，便于引用和回查。",
        f"3. 使用 {stats['embedder']} 在本地 CPU 批量编码，生成 {stats['dimensions']} 维稠密语义向量并做 L2 归一化。"
        "模型首次运行时下载，后续编码可使用本地缓存；提交包不包含模型权重。",
        "4. 将文档向量与分块一起存入内存向量库。查询使用同一个编码器，计算余弦相似度，按分数取前三项。",
        "5. query_store_policy 返回条款正文、块编号、标题路径与分数，Agent 依据这些内容答复。",
        "",
        "本地 BGE 演示的最低分数设为 0.55，用于过滤弱相关结果。相似度只衡量相关程度，"
        "不能单独证明某项政策适用；回答仍需检查返回条款的条件。另保留 TF-IDF 模式用于无需下载模型的单元测试，"
        "测试阈值为 0.12。正式提交的演示和向量证据均来自 BGE 语义模型。",
        "",
        "docs/policy-vectors.json 包含全部分块、向量和模型名称；采集脚本验证了块数与向量数一致，"
        "向量长度一致、数值有限且归一化。修改语料、分块参数或编码器后，索引指纹失效并重建。",
        "",
        "### 检索结果",
        "",
        "| 查询 | 预期条款 | 实际首条 | 分数 |",
        "|---|---|---|---|",
    ]
    for entry in rag["retrievals"]:
        hit = entry["passages"][0]
        lines.append(
            f"| {entry['question']} | {entry['expectedClause']} | {hit['clause']} | {hit['score']} |"
        )
    lines.extend(
        [
            "",
            "## 工具",
            "",
            "| 工具 | 参数 | 返回内容 |",
            "|---|---|---|",
            "| search_book_catalog | query；可选 category、max_price、in_stock_only、limit | 模拟书名、作者、简介、售价、库存及匹配依据 |",
            "| query_store_policy | question；可选 top_k | 语义检索命中的政策正文、编号、标题与相似度 |",
            "",
            "两个工具均通过 ToolRegistry.dispatch 执行。参数由 Schema 校验；没有命中或执行失败时返回"
            "包含 code、message、retryable、hint 的结构化错误，Agent 可调整参数重试或明确说明无法确认。",
            "",
            "## ReAct 循环",
            "",
            "每一轮向模型传入系统提示词、顾客问题和此前的执行记录。模型先生成 Thought，"
            "再提出一个 Action 和 JSON 参数。程序解析并执行该工具，将真实返回值作为 Observation 加回上下文，"
            "再请求模型决定下一步。模型生成 Final Answer 时结束；默认最多六轮、连续三次错误终止，"
            "重复工具和参数组合会被拦截。",
            "",
            "模型生成使用 Observation 停止标记，观测由程序执行工具后写入。远程模型根据提示词自主选择动作，"
            "循环内部没有固定的“查书后一定查政策”分支；离线规则模型作为复现与测试替身保留。",
            "",
            "## 复杂示例",
            "",
            "主例使用作业文档给出的提问，包含微服务荐书与拆封退货两个意图。"
            "先查书目，再检索政策，最后将书目结果与第六条及其例外条件合并回答。",
            "",
        ]
    )
    if remote:
        lines.extend(
            [
                f"本次主例由真实模型 {main_trace['modelMode']} 执行，"
                f"共 {main_trace['rounds']} 轮，结束状态为 {main_trace['stoppedReason']}。"
                "完整文本日志见 docs/logs/demo-remote.txt，结构化记录见 docs/remote-trace.json。",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "当前未配置真实模型密钥，主例由 offline:rule-based 替身模型执行；"
                "真实模型接口已实现，但本次证据未验证远程推理。",
                "",
            ]
        )
    lines.append(render_trace(main_trace))
    lines.extend(
        [
            "## 补充场景",
            "",
            "| 场景 | 模型模式 | 工具顺序 | 状态 |",
            "|---|---|---|---|",
        ]
    )
    for trace in remote[1:] + offline:
        sequence = " → ".join(step["action"] for step in trace["steps"])
        lines.append(
            f"| {trace['title']} | {trace['modelMode']} | {sequence} | {trace['stoppedReason']} |"
        )
    lines.extend(
        [
            "",
            "会员场景在一般拆封规则之外检索第二十条，处理金卡会员的额外权益；"
            "预算和现货条件传入查书工具。只问书目或只问政策时，仅调用相应工具。"
            "Rust 书目没有命中时，替身模型放宽关键词重试，并在回复中说明原主题未命中。",
            "",
            "## 运行验证",
            "",
            "单元测试覆盖分块、TF-IDF 测试替身、向量库、工具派发、ReAct 解析、重试与循环限制、"
            "HTTP 接口和完整日志。语义模型的实际编码与检索由 collect_evidence.py 单独验证。",
            "",
            "```text",
            tests,
            "```",
            "",
            "HTTP 演示在独立临时端口完成：健康检查返回索引就绪；chat 返回完整步骤与最终答复；"
            "policy/search 命中第六条。响应保存为 docs/http-evidence.json，服务日志保存为 docs/logs/server.log。",
            "",
            "## 复现",
            "",
            "需要 Python 3.10+。在解压后的作业目录执行：",
            "",
            "```bash",
            "python3 -m venv .venv",
            "source .venv/bin/activate",
            "python -m pip install -r requirements.txt",
            "python -m backend.cli --offline --stats",
            "python -m backend.cli --offline --demo",
            "```",
            "",
            "上述 --offline 仅选择规则对话模型；政策仍使用默认的本地语义 Embedding。"
            "模型首次运行需访问 Hugging Face，也可用 EMBEDDING_LOCAL_MODEL 指定已下载的模型目录。",
            "",
            "真实模型配置复制自 .env.example，在 .env 中填写 LLM_BASE_URL、LLM_MODEL 和 LLM_API_KEY 后执行：",
            "",
            "```bash",
            'python -m backend.cli --remote "我想买一本关于微服务的书，另外如果我买了不喜欢，拆了塑封还能退吗？"',
            "./run-local.sh",
            "```",
            "",
            "重采集与打包：",
            "",
            "```bash",
            "python scripts/collect_evidence.py",
            "python scripts/build_submission.py",
            "```",
            "",
            "采集脚本可读取本目录 .env；在原项目中也可复用 python-assistant/.env 的对话模型配置。"
            "未找到密钥时如实记录跳过远程演示；必需测试、语义检索或 HTTP 演示失败时终止。",
            "",
            "## 提交内容",
            "",
            "压缩包包含本次作业源码、测试、启动及采集脚本、模拟政策、Markdown 说明、运行日志与 JSON 证据。"
            "不包含原书城工程、其他作业、Jar、虚拟环境、模型权重、API 密钥及缓存。"
            "MANIFEST.json 记录文件清单和 SHA-256，checklist 中逐项记录五个评分点。",
            "",
            "## 参考资料",
            "",
            "1. Yao et al. ReAct: Synergizing Reasoning and Acting in Language Models. ICLR 2023. "
            "[论文原文](https://arxiv.org/abs/2210.03629)。参考其交替执行决策与工具动作的结构。",
            "2. Xiao et al. C-Pack: Packed Resources For General Chinese Embeddings. SIGIR 2024. "
            "[论文原文](https://arxiv.org/abs/2309.07597)。参考中文语义 Embedding 模型背景。",
            "3. [BAAI 官方模型说明](https://huggingface.co/BAAI/bge-small-zh-v1.5)。核对中文模型与编码方式。",
            "4. [Sentence Transformers 官方用法](https://www.sbert.net/docs/sentence_transformer/usage/usage.html)。核对模型加载与编码接口。",
            "",
        ]
    )
    return "\n".join(lines)


def submission_files() -> list[Path]:
    """明确选择与本次作业相关的文件，避免递归收录整个工程。"""
    files = [REPORT]
    files.extend(
        ROOT / name
        for name in (
            "README.md",
            "requirements.txt",
            "pytest.ini",
            ".env.example",
            "run-local.sh",
            "stop-local.sh",
        )
    )
    files.extend(
        path
        for path in (ROOT / "backend").rglob("*.py")
        if "__pycache__" not in path.parts
    )
    files.append(ROOT / "data/policy.txt")
    files.extend(ROOT / "scripts" / name for name in SCRIPT_FILES)
    files.extend(
        ROOT / "docs" / name for name in DOC_FILES if (ROOT / "docs" / name).exists()
    )
    files.extend(ROOT / "docs/logs" / name for name in LOG_FILES)
    for path in files:
        if not path.is_file():
            raise FileNotFoundError(f"提交文件缺失：{path.relative_to(ROOT)}")
    return sorted(files)


def main() -> None:
    """生成报告和校验清单，将当前白名单文件压缩为可上传的提交包。"""
    REPORT.write_text(build_report(), encoding="utf-8")
    files = submission_files()
    manifest = {
        "assignment": "作业3",
        "studentId": STUDENT_ID,
        "evidence": load_json("evidence-status.json"),
        "checklist": {
            "document_chunking_embedding": "verified with local BGE and policy-vectors.json",
            "rag_tool": "verified with four retrieval queries and HTTP policy search",
            "react_loop": "verified with multi-round traces and loop tests",
            "intent_routing": "catalog before policy in complex case",
            "thought_action_observation_logs": "present in CLI and HTTP logs",
        },
        "files": [
            {
                "path": path.relative_to(ROOT).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
            for path in files
        ],
    }
    (ROOT / "MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    with zipfile.ZipFile(ARCHIVE, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.relative_to(ROOT).as_posix())
        archive.write(ROOT / "MANIFEST.json", "MANIFEST.json")
    print(f"报告：{REPORT.name}")
    print(
        f"提交包：{ARCHIVE.name}（{len(files) + 1} 个文件，{ARCHIVE.stat().st_size / 1024:.1f} KB）"
    )


if __name__ == "__main__":
    main()
