"""生成作业2的提交文档与提交压缩包。

文档只写作业要求的内容：两个 Function 的定义与 Tool 配置、函数调用的拦截与回传、
前端对话界面、异常处理与 Self-Correction。正文套进课程作业模版（template.docx）。

提交压缩包按作业要求组织：只放自己编写的源码、脚本和文档，不放整个工程，
也不放第三方依赖或 Jar 包。

文档里的 Tool Schema 从 backend/tools.py 导入，演示链路从 docs/demo-trace.json 读，
日志从 docs/logs/ 读 —— 都是真实运行的产物，不是手写的。

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

from docx_template import check_template, render_docx, zip_tree  # noqa: E402

from backend.tools import TOOL_SCHEMAS  # noqa: E402

STUDENT_ID = os.environ.get("STUDENT_ID", "524031910113")
STUDENT_NAME = os.environ.get("STUDENT_NAME", "俞冠廷")

TEMPLATE = ROOT / "template.docx"
DOC_MD = ROOT / "docs" / "doc.md"
DOCX = ROOT / f"{STUDENT_ID}-作业2.docx"
ZIP = ROOT / f"{STUDENT_ID}-作业2.zip"
TRACE = ROOT / "docs" / "demo-trace.json"
LOGS = ROOT / "docs" / "logs"
SHOTS = ROOT / "docs" / "screenshots"

#: 版面可用宽度约 14.65 cm，图片留一点余量。
IMAGE_WIDTH = "14cm"

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
    "backend",
    "frontend",
    "scripts",
    "docs",
]
#: 缓存目录不进压缩包。
ARCHIVE_EXCLUDE_DIRS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}


def read(path: Path, fallback: str = "（缺失，请先运行 scripts/collect_logs.sh）") -> str:
    return path.read_text(encoding="utf-8").rstrip() if path.exists() else fallback


def trace_tables(traces: list[dict]) -> list[str]:
    """每个演示场景一张表：第几轮调用了什么函数、参数是什么、结果如何。"""
    out: list[str] = []
    for index, trace in enumerate(traces, start=1):
        out.append(f"**场景 {index}　{trace['title']}**")
        out.append("")
        out.append(f"用户提问：`{trace['question']}`")
        out.append("")
        if not trace["toolCalls"]:
            out.append("模型没有调用任何函数，直接向用户追问缺失的信息。")
            out.append("")
        else:
            # 列宽由 docx_template 按单元格内容自动分配，这里不用管排版。
            out.append("| 轮次 | 被拦截的函数调用 | 执行结果 | 耗时 |")
            out.append("|---|---|---|---|")
            for call in trace["toolCalls"]:
                arguments = json.dumps(call["arguments"], ensure_ascii=False)
                if call["ok"]:
                    if call["name"] == "check_inventory":
                        detail = f"✅ 库存 {call['result']['stockQty']} 本，{call['result']['price']} 元"
                    else:
                        detail = f"✅ 最低价 {call['result']['lowestPrice']} 元"
                else:
                    error = call["result"]["error"]
                    detail = f"❌ {error['code']}，retryable={str(error['retryable']).lower()}"
                out.append(
                    f"| 第 {call['round']} 轮 | `{call['name']}({arguments})` | {detail} | {call['durationMs']} ms |"
                )
            out.append("")
        out.append("助手回复：")
        out.append("")
        out.append("```text")
        out.append(trace["reply"])
        out.append("```")
        out.append("")
    return out


def build_markdown() -> str:
    out: list[str] = []
    add = out.append

    add("## 一、Function（Skill）定义")
    add("")
    add("### 1.1 交给模型的 JSON Schema")
    add("")
    add("两个 Skill 都以 OpenAI tools 格式声明。description 写清「什么时候该调用、什么时候不该调用」，"
        "参数用 JSON Schema 描述类型与约束 —— 模型只能依靠这些文字决定是否调用、传什么参数。")
    add("")
    add("```json")
    add(json.dumps(TOOL_SCHEMAS, ensure_ascii=False, indent=2))
    add("```")
    add("")
    add("### 1.2 本地模拟实现")
    add("")
    add("- `check_inventory`：先校验 ISBN 形态（去掉连字符后必须是 10 位或 13 位数字），再查数据源。"
        "数据源默认是内置的模拟目录 `MockInventoryBackend`，数据取自项目 "
        "`springboot-ebook/src/main/resources/data.sql` 的演示数据；"
        "设置环境变量 `BOOKSTORE_API_BASE` 后自动切换为 `HttpInventoryBackend`，"
        "直接读电子书城真实后端的 `GET /api/v1/books`。两者返回同一结构，上层不用改。")
    add("- `get_competitor_price`：模拟竞品比价接口，具备网络耗时、上游抖动、上游整体故障三种行为。"
        "报价由 ISBN 的数字位稳定推导，同一本书每次得到同一组结果，演示与测试都可复现。")
    add("")
    add("这里刻意不校验 EAN-13 校验位：项目演示数据里的 ISBN 是构造出来的，校验位并不合法，"
        "开启校验位检查会把全部演示数据误判成非法输入。")
    add("")

    add("## 二、配置给大模型的 Tool 列表")
    add("")
    add("每次请求都把上面两个 Schema 放进 `tools` 字段，`tool_choice` 设为 `auto`，"
        "由模型自行决定是否调用、调用哪一个、传什么参数。实际发出的请求体形态：")
    add("")
    add("```json")
    add(json.dumps(
        {
            "model": "<LLM_MODEL>",
            "messages": [
                {"role": "system", "content": "你是「E-BookStore 电子书城」的在线客服助手……"},
                {"role": "user", "content": "帮我查一下 ISBN为978-3-00-000000-4 的书还有多少本，顺便看看别家卖多少钱"},
            ],
            "tools": TOOL_SCHEMAS,
            "tool_choice": "auto",
        },
        ensure_ascii=False,
        indent=2,
    ))
    add("```")
    add("")
    add("客户端有两条等价路径：优先走 `openai` SDK（`OpenAICompatibleClient`），"
        "SDK 不可用时退回只用标准库的 `HttpChatClient`。两者请求体完全一致，"
        "改 `base_url` 即可切换 OpenAI / DeepSeek / 通义千问兼容模式等供应商。")
    add("")

    add("## 三、函数调用的拦截与回传")
    add("")
    add("`BookstoreAssistant.chat()` 是「拦截模型输出 → 本地执行 → 结果回传 → 生成回答」的落点，"
        "一轮用户提问内的流程：")
    add("")
    add("1. 组装 messages（system + 历史 + 本轮提问），连同 Tool 列表发给模型；")
    add("2. 模型返回的 assistant 消息里若带 `tool_calls`，不发给用户，而是拦截下来；")
    add("3. 打印函数名与参数，交给 `ToolRegistry.dispatch` 本地执行；")
    add("4. 把执行结果包装成 `role: \"tool\"` 的消息追加进上下文，回到第 1 步；")
    add("5. 模型不再要求调用函数时，它给出的自然语言内容就是最终回复。")
    add("")
    add("被拦截的每一次调用都会生成一条 `ToolEvent`。服务端日志（`docs/logs/server.log`）：")
    add("")
    add("```text")
    add(read(LOGS / "server.log"))
    add("```")
    add("")
    add("模型给出的 `arguments` 是字符串，且不保证是合法 JSON（长参数被截断、引号混用都很常见）。"
        "`ToolCallRequest.parse_arguments()` 永远返回 `(参数, 错误)` 二元组，解析失败时生成一条 "
        "`INVALID_JSON_ARGUMENTS` 的 tool 消息回传，让模型重新表述，而不是让整个对话崩掉。")
    add("")

    add("## 四、前端智能助手对话界面")
    add("")
    add("界面接在电子书城前端：左侧菜单新增「客服助手」，路由 `/assistant`，"
        "沿用站内既有的 React Router Data API 约定（`loader` 读数据、`action` 处理顶栏搜索），"
        "对话本身是客户端状态，直接调用助手后端的 `POST /api/assistant/chat`。")
    add("")
    add("页面把拦截到的函数名与参数做成了可见的卡片：函数名、参数、成功或失败、耗时、"
        "可展开的完整返回值；失败时额外显示回传给模型的纠错提示。")
    add("")
    for filename in (
        "ui-01-normal.png",
        "ui-02-self-correction.png",
        "ui-03-retry.png",
        "ui-04-no-isbn.png",
    ):
        shot = SHOTS / filename
        if shot.exists():
            add(f"![]({shot.as_posix()}){{width={IMAGE_WIDTH}}}")
            add("")
    add("以上截图不是把对话记录画成图片，而是把前后端跑起来、点击页面上的示例问题按钮、"
        "让后端真的跑一遍 Function Calling 之后截下来的，见 `scripts/capture_ui.py`。")
    add("")

    add("## 五、异常处理与 Self-Correction")
    add("")
    add("### 5.1 错误码与期望的模型行为")
    add("")
    add("| 错误码 | 触发条件 | retryable | 期望的模型行为 |")
    add("|---|---|---|---|")
    add("| `INVALID_ARGUMENT` | 缺少 isbn、类型不对、函数不存在、参数名不在 schema 里 | 否 / 是 | 按 schema 重新组织参数 |")
    add("| `INVALID_ISBN_FORMAT` | ISBN 去连字符后不是 10 位或 13 位数字 | 否 | 复述原值请用户确认，绝不自行补位 |")
    add("| `ISBN_NOT_FOUND` | 格式合法但书店目录里没有 | 否 | 如实告知未收录，不虚构书名与库存 |")
    add("| `UPSTREAM_TIMEOUT` | 比价接口耗时超过阈值，或上游抖动 | 是 | 原样重试一次 |")
    add("| `UPSTREAM_UNAVAILABLE` | 比价渠道整体不可用 | 否 | 不重试，告知用户只拿到本店价格 |")
    add("| `TOOL_INTERNAL_ERROR` | 工具内部未预期异常 | 否 | 告知用户暂时查不到 |")
    add("")
    add("三条防线：工具层的 `dispatch` 把所有失败收敛成 `{\"ok\": false, \"error\": {...}}`，"
        "异常栈对模型没有意义、`error.hint` 才有；循环层设连续失败上限（默认 3 次）与往返轮次上限"
        "（默认 6 轮），避免请求挂死；System Prompt 把 `retryable` 的语义、"
        "「不许编造库存」「不许猜 ISBN」写成明确规则，让模型知道该重试还是该换策略。")
    add("")
    add("### 5.2 五个场景的真实运行链路")
    add("")
    add("以下内容由 `python -m backend.cli --demo` 直接产出（`docs/demo-trace.json`），未经手工编辑。")
    add("")
    if TRACE.exists():
        out.extend(trace_tables(json.loads(TRACE.read_text(encoding="utf-8"))))
    else:
        add("（缺少 docs/demo-trace.json，请先运行 scripts/collect_logs.sh）")
        add("")
    add("### 5.3 命令行完整输出")
    add("")
    demo_shot = SHOTS / "terminal-agent-demo.png"
    if demo_shot.exists():
        add(f"![]({demo_shot.as_posix()}){{width={IMAGE_WIDTH}}}")
        add("")

    return "\n".join(out)


def main() -> int:
    check_template(TEMPLATE)

    DOC_MD.write_text(build_markdown(), encoding="utf-8")

    render_docx(
        DOC_MD,
        TEMPLATE,
        DOCX,
        student_id=STUDENT_ID,
        student_name=STUDENT_NAME,
        homework_no="2",
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
