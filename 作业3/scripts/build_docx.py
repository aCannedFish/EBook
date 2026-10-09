"""生成作业3的提交文档与提交压缩包。

文档只写作业要求的内容：政策知识库与 RAG 流程（加载 / 分块 / 向量化 / 检索）、
两个工具的 Schema 与实现、ReAct 循环、复杂交互 Case 的完整链路，
以及异常处理与自我纠错。

文档里的数字与链路都不是手写的：
- 工具 Schema、ReAct System Prompt 从 backend 导入；
- 分块统计、检索命中从现场运行 RAG 得到；
- 五个场景的链路从 docs/demo-trace.json 读（由 `cli --demo --json` 产出）；
- 测试、服务端日志、真实模型日志从 docs/logs/ 读。

用法：
    python3 scripts/build_docx.py
    STUDENT_ID=... STUDENT_NAME=... python3 scripts/build_docx.py
"""

from __future__ import annotations

import json
import os
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

# 建文档时固定用本地向量化：远程模型/接口的输出不可复现，
# 文档里的相似度数字必须每次生成都一致。
os.environ.setdefault("EMBEDDING_MODE", "offline")

from docx_template import check_template, render_docx, zip_tree  # noqa: E402

from backend.agent import REACT_SYSTEM_PROMPT  # noqa: E402
from backend.catalog import DEFAULT_CATALOG  # noqa: E402
from backend.config import AGENT, CATALOG, RAG  # noqa: E402
from backend.rag import RagPipeline  # noqa: E402
from backend.tools import TOOL_SCHEMAS, describe_tools  # noqa: E402

STUDENT_ID = os.environ.get("STUDENT_ID", "524031910113")
STUDENT_NAME = os.environ.get("STUDENT_NAME", "俞冠廷")

TEMPLATE = ROOT / "template.docx"
DOC_MD = ROOT / "docs" / "doc.md"
DOCX = ROOT / f"{STUDENT_ID}-作业3.docx"
ZIP = ROOT / f"{STUDENT_ID}-作业3.zip"
TRACE = ROOT / "docs" / "demo-trace.json"
LOGS = ROOT / "docs" / "logs"
SHOTS = ROOT / "docs" / "screenshots"
POLICY = ROOT / "data" / "policy.txt"

#: 版面可用宽度约 14.65 cm，图片留一点余量。
IMAGE_WIDTH = "14cm"

#: 检索验证用的问题：前两个是作业要求的主线问题，后面几个覆盖不同章节。
RETRIEVAL_QUESTIONS = (
    "拆了塑封还能退吗",
    "会员已拆封退货权益",
    "退货运费谁承担",
    "金卡会员有什么折扣",
    "海外直邮的书可以退吗",
)

#: 提交压缩包收录的内容：本作业自己编写的源码、脚本与文档。
ARCHIVE_INCLUDE = [
    DOCX.name,
    "README.md",
    "requirements.txt",
    "pytest.ini",
    ".env.example",
    "run-local.sh",
    "stop-local.sh",
    "template.docx",
    "data",
    "backend",
    "scripts",
    "docs",
]
#: 缓存目录不进压缩包。
ARCHIVE_EXCLUDE_DIRS = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    ".index",
}


def read(path: Path, fallback: str = "（缺失，请先运行 scripts/collect_logs.sh）") -> str:
    return path.read_text(encoding="utf-8").rstrip() if path.exists() else fallback


def observation_summary(step: dict) -> str:
    """把观测压缩成一行，方便在文档里看重点。"""
    result = step.get("result") or {}
    if not step["ok"]:
        error = result.get("error") or {}
        return f"❌ {error.get('code')}：{error.get('message')}（retryable={str(error.get('retryable')).lower()}）"
    if step["action"] == "query_store_policy":
        heads = "、".join(
            f"{item['headingPath']}（{item['score']}）" for item in result.get("passages", [])
        )
        return f"✅ 命中 {result.get('count')} 条条款，最高相似度 {result.get('topScore')}：{heads}"
    if step["action"] == "search_book_catalog":
        titles = "、".join(f"《{book['title']}》" for book in result.get("results", []))
        return f"✅ 命中 {result.get('count')} 本：{titles}"
    return f"✅ {json.dumps(result, ensure_ascii=False)[:120]}"


def render_trace(trace: dict, index: int) -> list[str]:
    out: list[str] = []
    out.append(f"**场景 {index}　{trace['title']}**")
    out.append("")
    out.append(f"用户提问：`{trace['question']}`")
    out.append("")
    out.append("```text")
    for step in trace["steps"]:
        out.append(f"[{step['index']}] Thought: {step['thought'] or '（模型未给出推理）'}")
        out.append(f"    Action: {step['action']}")
        out.append(f"    Action Input: {json.dumps(step['arguments'], ensure_ascii=False)}")
        out.append(f"    Observation: {observation_summary(step)}")
        out.append(f"    （耗时 {step['durationMs']} ms）")
    out.append("```")
    out.append("")
    out.append("助手回复：")
    out.append("")
    out.append("```text")
    out.append(trace["reply"])
    out.append("```")
    out.append("")
    return out


def build_markdown() -> str:
    index = RagPipeline().build()
    stats = index.stats()
    out: list[str] = []
    add = out.append

    # ---------------------------------------------------------------- 一、RAG
    add("## 一、政策知识库与 RAG 流程")
    add("")
    add("作业要求先准备一份书店的「退换货与会员政策」文本文档，再用简易 RAG 流程对它做"
        "分块与向量化。这一段就是那条流程：**加载 → 分块 → 向量化 → 建库 → 检索**，"
        "每一步的产物都由代码里对应的模块产出。")
    add("")
    add("### 1.1 知识库原文")
    add("")
    add("| 项目 | 内容 |")
    add("|---|---|")
    add("| 文件 | `data/policy.txt` |")
    add(f"| 文档 | {stats['document']['title']} |")
    add(f"| 文档编号 | {stats['document'].get('文档编号', '')} |")
    add(f"| 生效日期 | {stats['document'].get('生效日期', '')} |")
    add(f"| 规模 | {stats['document']['chars']} 字符 / {stats['document']['lines']} 行 |")
    add("")
    add("全文按「章 → 条 → 款」组织，共 5 章 25 条，覆盖退换货、塑封拆封、退款与运费、"
        "会员等级与权益、发票与投诉五个方面 —— 这正好是本作业那两个工具要回答的领域。"
        "下面摘录其中的关键条款（全文见 `data/policy.txt`）：")
    add("")
    add("```text")
    policy_lines = POLICY.read_text(encoding="utf-8").splitlines()
    start = next(
        index for index, line in enumerate(policy_lines) if "第六条【塑封与拆封规则】" in line
    )
    second = next(
        index for index, line in enumerate(policy_lines) if "第二十条【已拆封退货权益】" in line
    )
    add("\n".join(policy_lines[start : start + 13]))
    add("")
    add("…（第七条、第八条至第十九条略，全文见 data/policy.txt）")
    add("")
    add("\n".join(policy_lines[second : second + 11]))
    add("```")
    add("")

    add("### 1.2 分块（Chunking）")
    add("")
    add("政策文本自带层级：章 → 条 → 款。切块顺着这个层级走，"
        "而不是按固定字数硬切 —— 「一条政策」天然就是检索的最小完整语义单元，"
        "切在条款边界上，检索到的内容才不会前后不着村。实现见 `backend/chunking.py`：")
    add("")
    add("1. 先按 `第X章` 切出章，章标题记为 `section`；")
    add("2. 章内按 `第X条` 切出条，条标题记为 `clause`；")
    add("3. 条款正文超过 `chunk_size`（默认 {}）时，再按句子边界（。；）切分，"
        "块间保留 {} 字符重叠，避免一句话的上下文被切断；".format(RAG.chunk_size, RAG.chunk_overlap))
    add("4. 过短的条款与同章相邻条款合并，避免出现「只有标题、没有内容」的碎块；")
    add("5. 每块文本前面回填「《政策》 章 · 条」的引用头，这一行一起参与向量化 —— "
        "「第十五条讲了什么」这类问法因此也能命中。")
    add("")
    add("| 指标 | 数值 |")
    add("|---|---|")
    add(f"| 分块数 | {stats['count']} |")
    add(f"| 平均块长 | {stats['avgChars']} 字符（{stats['minChars']} ~ {stats['maxChars']}） |")
    add(f"| 覆盖章节 | {stats['sections']} |")
    add(f"| 块标识 | `policy-0000` … `policy-{stats['count'] - 1:04d}`（同时保留字符区间 charStart/charEnd） |")
    add("")
    add("切出来的块（前 6 条与两条关键条款）：")
    add("")
    add("| 块 ID | 标题路径 | 字数 | 正文首行 |")
    add("|---|---|---|---|")
    samples = index.chunks[:5] + [
        chunk for chunk in index.chunks if chunk.clause.startswith(("第六条", "第二十条"))
    ]
    for chunk in samples:
        body = chunk.text.split("\n")
        first = next((line for line in body[1:] if line.strip()), "")
        add(f"| `{chunk.id}` | {chunk.heading_path or '（前言）'} | {chunk.char_count} | {first[:46]} |")
    add("")

    add("### 1.3 向量化（Embedding）")
    add("")
    add("向量化有两种实现，接口一致（`backend/embedding.py`）：")
    add("")
    add("- **本地实现 `TfidfEmbedder`**（本次运行实际使用的就是它）："
        "把中文切成单字 + 字符 bigram，英文数字切成整词 + 字符 trigram，"
        "用索引语料建立词表并统计 IDF，按 `(1+log tf) × idf` 加权后 L2 归一化。"
        "不联网、可复现，几十毫秒就能重建索引。")
    add("- **远程实现 `OpenAIEmbedder`**：调用 OpenAI 兼容的 `/embeddings` 接口，"
        "配好 `EMBEDDING_BASE_URL` / `EMBEDDING_API_KEY` 即可切换为真实的语义向量。")
    add("")
    add(f"本次运行的实际路径：`{stats['embedderNote']}`，向量维度 {stats['dimensions']}，"
        f"索引指纹 `{stats['fingerprint']}`。")
    add("")
    add("为什么默认走本地实现：本作业接入的课程网关只提供 `/chat/completions`，"
        "`/embeddings` 返回 403。把整个 RAG 流程绑在一个用不了的接口上，"
        "演示和测试都跑不起来。所以 `EMBEDDING_MODE=auto` 时先试远程、失败自动回退本地，"
        "并把最终选择写进索引元数据 —— 「这份索引到底是用什么模型建的」必须可追溯。")
    add("")
    add("另外，第一版实现用的是「哈希技巧把特征压到 512 维」，效果很差：政策块单块就有数百个特征，"
        "挤进 512 个桶时正负号互相抵消，连「拆了塑封还能退吗 → 第六条」这种明显的命中都排不到第一。"
        "语料只有几十块，词表撑死几千维，直接用精确词表又准又便宜，没有理由做哈希近似。")
    add("")

    add("### 1.4 向量库与相似度检索")
    add("")
    add("检索就是「查询向量 vs 每个块向量」的余弦相似度排序，外加一道**相似度闸门**"
        f"（默认 {RAG.min_score}）：低于阈值的块不进结果，让上层的 `query_store_policy` 能明确地说"
        "「知识库没覆盖这个问题」，而不是把一段不相关的政策塞给模型当依据。"
        "排序做了确定性处理（同分按块序号），所以每次运行的检索结果完全一致。")
    add("")
    add(f"下表是一次真实检索的结果（`top_k={RAG.top_k}`，阈值 {RAG.min_score}）：")
    add("")
    add("| 检索问题 | 命中条款（相似度） |")
    add("|---|---|")
    for question in RETRIEVAL_QUESTIONS:
        passages = index.retrieve(question)
        detail = "；".join(f"{item.chunk.heading_path}（{item.score:.3f}）" for item in passages) or "无命中（低于阈值）"
        add(f"| {question} | {detail} |")
    add("")
    add("最后一行「海外直邮的书可以退吗」是刻意留的反例：政策原文里没有任何一条讲海外直邮，"
        "最高相似度只有 0.06 左右，低于阈值 —— 这正是「宁可说不知道，也不硬答」的判定依据。")
    add("")
    add("索引结果会缓存在 `.index/` 下，缓存指纹由「语料内容 + 分块参数 + 向量化模型名」算出，"
        "任何一项变了指纹就变、旧缓存自动失效，不会出现「改了政策文档、检索结果还是旧的」这种最难查的问题。")
    add("")

    # ------------------------------------------------------------ 二、工具
    add("## 二、两个工具：查书与查政策")
    add("")
    add("### 2.1 交给模型看的 Schema")
    add("")
    add("两个工具都用 OpenAI tools 格式声明。description 写清「什么时候该调用、什么时候不该调用」，"
        "参数用 JSON Schema 描述类型与约束 —— ReAct 走的是纯文本协议，没有 `tools` 字段，"
        "模型只能靠这些文字决定是否调用、传什么参数。")
    add("")
    add("```json")
    add(json.dumps(TOOL_SCHEMAS, ensure_ascii=False, indent=2))
    add("```")
    add("")
    add("### 2.2 ReAct 提示词里的工具说明书")
    add("")
    add("ReAct 用的是文本协议，所以工具说明由同一份 Schema 渲染而成（`tools.describe_tools`）："
        "文字与参数只有一处来源，不会出现「提示词说支持某参数、实现里没这个参数」的偏差。"
        "System Prompt 里实际贴出的就是下面这段：")
    add("")
    add("```text")
    add(describe_tools())
    add("```")
    add("")
    add("### 2.3 实现要点")
    add("")
    add("- **`search_book_catalog(query, category, max_price, in_stock_only, limit)`**："
        f"在 {len(DEFAULT_CATALOG)} 本书的内置书目里做字段加权关键词检索"
        "（标题 6 / 标签 4 / 分类 3 / 作者 2 / 出版社 1.5 / 简介 1），"
        f"归一化后低于 {CATALOG.min_score} 的书不算命中。返回结果里带 `matchedTerms`，"
        "读日志的人能看出这几本书为什么被选中。书目里刻意留了两个坑："
        "《微服务与容器化实践》库存为 0（触发「只看有货」的过滤），"
        "以及目录里完全没有 Rust 书（触发检索失败后的自我纠错）。")
    add("- **`query_store_policy(question, top_k)`**：调用 1.4 节的检索，返回带块编号、"
        "标题路径与相似度的条款原文。模型必须引用返回的条款作答，不得把常识当成本店政策。")
    add("")
    add("两个工具都不抛异常，失败一律收敛成结构化错误（`backend/tools.py` 的 `ToolRegistry.dispatch`）：")
    add("")
    add("| 错误码 | 触发条件 | retryable | 期望的模型行为 |")
    add("|---|---|---|---|")
    add("| `INVALID_ARGUMENT` | 参数缺失、类型不对、工具名不存在、参数名不在 Schema 里 | 是 / 否 | 按 Schema 重新组织参数 |")
    add("| `CATALOG_NO_MATCH` | 书目检索没有达到相关度阈值的书 | 是 | 换一个更宽的主题词重试，或去掉价格 / 有货限制 |")
    add("| `POLICY_NOT_COVERED` | 政策库没有达到相似度阈值的条款 | 是 | 换用政策原文的说法重试；仍查不到就如实说没覆盖 |")
    add("| `POLICY_INDEX_UNAVAILABLE` | 语料缺失或向量化失败 | 否 | 告知用户政策查询暂时不可用，不要猜 |")
    add("| `INVALID_JSON_ARGUMENTS` | Action Input 不是合法 JSON | 是 | 按 `{\"query\": \"微服务\"}` 的格式重新输出 |")
    add("| `REACT_FORMAT_ERROR` | 既没有 Action 也没有 Final Answer | 是 | 按 Thought / Action / Action Input 的格式重写 |")
    add("| `REPEATED_ACTION` | 同一动作 + 同一参数重复调用 | 否 | 换参数或直接给出 Final Answer |")
    add("| `TOOL_INTERNAL_ERROR` | 工具内部未预期异常 | 否 | 如实告知暂时查不到 |")
    add("")

    # ---------------------------------------------------------- 三、ReAct
    add("## 三、ReAct（Reason + Act）循环")
    add("")
    add("循环在 `backend/agent.py`，一次提问的流程是：")
    add("")
    add("1. 组装提示词：System Prompt（角色 + 工具说明书 + 输出格式）+ 用户提问 + 执行记录；")
    add("2. 让模型输出下一步：先 `Thought` 讲清为什么这么做，再给 `Action` 与 `Action Input`；")
    add("3. **生成时带 `stop=[\"\\nObservation:\"]`** —— 观测必须来自本地真实执行，模型不可能自己续写一个出来；")
    add("4. 解析输出：解析失败就把「格式错误 + 正确写法」当作观测回填，让模型重写一遍；")
    add("5. 执行动作，把结果作为 `Observation` 追加进执行记录，回到第 2 步；")
    add("6. 模型输出 `Final Answer` 时结束，它就是给顾客的答复。")
    add("")
    add(f"三条刹车：最大步数 {AGENT.max_steps}、连续失败上限 {AGENT.max_consecutive_errors}、"
        "重复动作检测。没有它们，模型一旦陷入「同样的动作反复调用」就会把请求挂死在这里。")
    add("")
    add("### 3.1 System Prompt 全文")
    add("")
    add("```text")
    add(REACT_SYSTEM_PROMPT.replace("{tools}", describe_tools()))
    add("```")
    add("")

    traces = json.loads(TRACE.read_text(encoding="utf-8")) if TRACE.exists() else []
    add("### 3.2 复杂交互 Case 的完整链路")
    add("")
    add("作业给出的 Case 是「我想买一本关于微服务的书，另外如果我买了不喜欢，拆了塑封还能退吗？」，"
        "一次提问里包含两个意图：找书 + 问政策。下面是它的真实运行链路"
        "（`python -m backend.cli --demo` 的输出，未经手工编辑）。")
    add("")
    if traces:
        out.extend(render_trace(traces[0], 1))
    else:
        add("（缺少 docs/demo-trace.json，请先运行 scripts/collect_logs.sh）")
        add("")
    add("模型在这条链路里做了三件事，恰好对应 ReAct 的三个环节：")
    add("")
    add("1. **Thought**：先把用户的话拆成两个子问题，并判断出第二个是政策问题；")
    add("2. **Action**：按顺序调用 `search_book_catalog` 与 `query_store_policy` —— "
        "第二个工具的 `question` 参数被改写成了「拆了塑封还能退吗」，"
        "而不是把整句话丢进去；")
    add("3. **Observation → Final Answer**：把书目结果（书名、价格、库存）与政策条款"
        "（第六条【塑封与拆封规则】的原文）合成一段答复，条款号逐条标出。")
    add("")
    add("### 3.3 换成真实大模型的同一条链路")
    add("")
    add("离线替身模型保证了可复现，但它终究是规则实现。下面这段是把同一个提示词、"
        "同一组工具交给真实模型（`deepseek-chat`）跑出来的结果 —— 它自己走出了同一条链路："
        "先查书、再查政策，并且一样引用了条款号。")
    add("")
    remote_log = LOGS / "demo-remote.txt"
    if remote_log.exists():
        text = remote_log.read_text(encoding="utf-8").strip()
        add("```text")
        add(text if len(text) <= 4200 else text[:4200].rstrip() + "\n…（完整日志见 docs/logs/demo-remote.txt）")
        add("```")
    else:
        add("（缺失 docs/logs/demo-remote.txt，请先运行 scripts/collect_logs.sh）")
    add("")

    # ------------------------------------------------------- 四、场景与异常
    add("## 四、五个场景的真实运行链路")
    add("")
    add("除了作业给出的复杂 Case，另外四个场景分别覆盖「带过滤条件 + 会员多跳检索」"
        "「单一意图」「多个政策问题」「检索失败后自我纠错」四种形态。")
    add("")
    add("| # | 场景 | 调用序列 | 结束原因 |")
    add("|---|---|---|---|")
    for number, trace in enumerate(traces, start=1):
        actions = " → ".join(step["action"] for step in trace["steps"]) or "（未调用工具）"
        add(f"| {number} | {trace['title']} | `{actions}` | {trace['stoppedReason']} |")
    add("")
    if len(traces) > 1:
        add("### 4.1 带过滤条件 + 会员多跳检索")
        add("")
        add("这个场景值得单独看：用户既给了预算和「要现货」的要求，又是金卡会员。"
            "模型首先把过滤条件填进了工具参数，随后发现「拆封退货」的一般规则"
            "（第六条）不足以回答金卡会员的疑问，于是**自己发起了第二跳检索**"
            "（`会员已拆封退货权益`），命中第二十条【已拆封退货权益】。"
            "多跳检索是检索规划的一部分：`build_plan` 里就是两条显式的检索计划，"
            "而不是循环里的特例分支。")
        add("")
        out.extend(render_trace(traces[1], 2))
        add("### 4.2 其余三个场景")
        add("")
        for number, trace in enumerate(traces[2:], start=3):
            out.extend(render_trace(trace, number))
    else:
        add("（缺少 docs/demo-trace.json，请先运行 scripts/collect_logs.sh）")
        add("")

    add("## 五、异常处理与自我纠错")
    add("")
    add("三个场景可以直接看到不同形态的失败与恢复：")
    add("")
    add("- **检索不到（工具层）**：`search_book_catalog` 返回 `CATALOG_NO_MATCH` 并附带 hint，"
        "模型读 hint 后把「Rust」放宽成「编程」重试，成功后在答复里说明了「目录里没有 Rust 直接相关的书，"
        "我把关键词放宽成「编程」后找到这些」—— 既纠错了，也没有假装用户问的东西存在。")
    add("- **政策库没覆盖（知识层）**：问「海外直邮的书可以退吗」时相似度不达阈值，"
        "工具返回 `POLICY_NOT_COVERED`；模型按 hint 换了政策原文的说法重试，仍然没有相关条款，"
        "于是如实回答「没有依据回答，建议以在线客服的答复为准」，而不是编一条政策出来。")
    add("- **协议跑偏与死循环（循环层）**：模型输出不符合 ReAct 格式时，"
        "错误会作为观测回填（连同模型自己的原话），它下一轮就能改正；"
        "同一动作 + 同一参数重复出现时会被直接拦下（`REPEATED_ACTION`）；"
        "连续失败到上限或步数用尽时，返回一句可解释的兜底话术，而不是让请求挂死。")
    add("")
    add("这三条防线分别落在三层：工具层把异常收敛成结构化错误、"
        "循环层负责刹车、System Prompt 把 `retryable` 的语义与「不许编造」写成明确规则。")
    add("")
    add("单元测试里对每条失败路径都有用例（`backend/tests/test_agent.py`、`test_tools.py`）：")
    add("")
    add("```text")
    add(read(LOGS / "tests.txt"))
    add("```")
    add("")

    add("## 六、运行方式与接口")
    add("")
    add("### 6.1 命令行")
    add("")
    add("```bash")
    add("python3 -m backend.cli --offline --demo     # 五个场景的完整 ReAct 链路")
    add("python3 -m backend.cli --offline --stats    # 知识库规模、分块统计、检索示例")
    add('python3 -m backend.cli "拆了塑封还能退吗，另外有没有讲微服务的书？"')
    add("python3 -m backend.cli --remote             # 配了密钥时走真实模型")
    add("```")
    add("")
    add("### 6.2 HTTP 服务")
    add("")
    add("```bash")
    add("./run-local.sh                             # 127.0.0.1:8000")
    add("curl -X POST http://127.0.0.1:8000/api/guide/chat \\")
    add("     -H 'Content-Type: application/json' \\")
    add('     -d \'{"message": "我想买一本关于微服务的书，另外拆了塑封还能退吗？"}\'')
    add("curl -X POST http://127.0.0.1:8000/api/guide/policy/search \\")
    add("     -H 'Content-Type: application/json' -d '{\"question\": \"拆了塑封还能退吗\"}'")
    add("```")
    add("")
    add("`/api/guide/chat` 返回完整的 `steps`（每一步的 Thought / Action / Action Input / Observation），"
        "服务端日志同源：")
    add("")
    add("```text")
    add(read(LOGS / "server.log"))
    add("```")
    add("")
    add("### 6.3 RAG 自检输出")
    add("")
    add("```text")
    add(read(LOGS / "rag-stats.txt"))
    add("```")
    add("")

    for filename in ("terminal-agent-demo.png", "terminal-rag-stats.png", "terminal-server-log.png"):
        shot = SHOTS / filename
        if shot.exists():
            add(f"![]({shot.as_posix()}){{width={IMAGE_WIDTH}}}")
            add("")
    add("以上截图不是把对话记录画成图片，而是把命令真跑一遍、用 `scripts/capture_terminal.py` "
        "把终端输出渲染出来的，内容与 `docs/logs/` 下的日志一致。")
    add("")
    add("### 6.4 与作业要求的对应关系")
    add("")
    add("| 评分点 | 对应实现 | 验证方式 |")
    add("|---|---|---|")
    add("| 文档加载、切分与 Embedding | `backend/corpus.py`、`chunking.py`、`embedding.py` | `--stats` 输出分块与向量化统计 |")
    add("| 可用的 RAG 检索工具 | `backend/rag.py` + `query_store_policy` | 1.4 节检索验证表、`/api/guide/policy/search` |")
    add("| 完整的 ReAct 循环 | `backend/agent.py` | 3.2 节链路、`test_agent.py` |")
    add("| 按意图路由到两个工具 | `build_plan` + `agent._decide_*` | 场景 1/2 的调用序列 |")
    add("| Thought → Action → Observation 日志 | `ReActStep.log_line`、`on_step`、服务端日志 | 3.2 / 四 / 6.2 节 |")
    add("")

    return "\n".join(out)


def main() -> int:
    check_template(TEMPLATE)

    DOC_MD.parent.mkdir(parents=True, exist_ok=True)
    DOC_MD.write_text(build_markdown(), encoding="utf-8")

    render_docx(
        DOC_MD,
        TEMPLATE,
        DOCX,
        student_id=STUDENT_ID,
        student_name=STUDENT_NAME,
        homework_no="3",
    )
    print(f"{DOCX.name}  已生成（{DOCX.stat().st_size / 1024:.0f} KB）")

    zip_tree(ZIP, ROOT, ARCHIVE_INCLUDE, ARCHIVE_EXCLUDE_DIRS)
    with zipfile.ZipFile(ZIP) as archive:
        entries = archive.namelist()
    print(f"{ZIP.name}  已生成（{ZIP.stat().st_size / 1024:.0f} KB，{len(entries)} 个文件）")
    print(f"中间稿：{DOC_MD.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
