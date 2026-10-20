"""按课程模版生成四份报告；正文只覆盖对应要求，事实取自本项目的真实运行证据。"""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "python-assistant"))
from report_document import build_report
from backend.tools import TOOL_SCHEMAS

DOCS = ROOT / "docs/assignments"
OUTPUT = ROOT / "deliverables"


def read(hw: int, name: str):
    return json.loads((DOCS / f"hw{hw}" / name).read_text(encoding="utf-8"))


def block(language: str, content: str) -> str:
    return f"```{language}\n{content.strip()}\n```\n"


def picture(hw: int, filename: str, caption: str) -> str:
    path = DOCS / f"hw{hw}/screenshots/{filename}.png"
    if not path.is_file():
        raise FileNotFoundError(path)
    return f"![{caption}](screenshots/{filename}.png)\n"


def report_one() -> str:
    """保留实际使用的完整 Prompt，并说明两轮真实模型输出与运行接口的对应关系。"""
    conversation = read(1, "conversation.json")
    spec = read(1, "openapi.json")
    messages = conversation["messages"]
    system = next(message["content"] for message in messages if message["role"] == "system")
    users = [message["content"] for message in messages if message["role"] == "user"]
    lines = [
        "## 一、提示词", "",
        "为现有 EBook 书城生成 OpenAPI 契约。System Prompt 固定项目身份、真实接口、字段和输出格式；"
        "User Prompt 分别要求生成与复核。两轮对话均通过书城的接口设计页面所连接的真实模型 API 执行。", "",
        "完整 System Prompt：", "", block("text", system),
    ]
    for number, message in enumerate(users, 1):
        lines.extend([f"第{number}轮完整 User Prompt：", "", block("text", message)])
    lines.extend([
        "## 二、输出约束", "",
        "提示词限定 OpenAPI 3.0.3 JSON，禁止 Markdown 围栏、注释、YAML 和额外解释。请求同时设置 "
        "response_format 为 json_object。生成后先做 JSON 解析，再核对真实路径、分页默认值、状态码、"
        "Schema 和 Bearer 鉴权声明；最终两轮产物均通过 OpenAPI 规范校验。", "",
        "最终文件为 openapi.json。模型生成的库存请求 Schema 如下：", "",
        block("json", json.dumps(spec["components"]["schemas"]["StockInput"], ensure_ascii=False, indent=2)),
        "## 三、接口设计", "",
        "接口直接对应 springboot-ebook 的 BookController，不再另建作业专用服务。", "",
        "| 方法 | 资源路径 | 功能 | 成功响应 |",
        "|---|---|---|---|",
        "| GET | /api/v1/books | 分页与分类过滤 | 200 BookPage |",
        "| GET | /api/v1/books/{id} | 查询单本图书 | 200 Book |",
        "| POST | /api/v1/books | 管理员新增图书 | 201 Book，附 Location |",
        "| PATCH | /api/v1/books/{id}/stock | 管理员更新库存 | 200 Book |", "",
        "路径使用资源名词，操作由 HTTP 方法表达。新增与库存修改都使用 JSON 请求体，管理员身份来自 JWT。", "",
        "## 四、参数响应", "",
        "列表参数 page 从0开始，默认0；size 默认20，范围1至100；category 精确过滤分类，"
        "keyword 匹配书名、作者或分类，isbn 支持去除连字符后匹配。响应 BookPage 包含 "
        "items、page、size、totalElements 和 totalPages，items 中每条记录为现有书城的 Book DTO。", "",
        "新增图书请求包含书名、作者、出版社、ISBN、分类、售卖形式、简介、整数价格和非负库存，"
        "封面地址为可选字段。库存部分更新仅要求 stockQty。错误响应至少包含 message，"
        "400 表示参数错误，401 表示未通过 Token 验证，403 表示权限不足，404 表示图书不存在。", "",
        "使用 JWT 访问运行中的书城，size=2 实际返回两条书目；category=算法 只返回该分类的一条记录。"
        "这些响应保存在 runtime-evidence.json，与生成的分页和分类契约一致。", "",
        "## 五、多轮对话", "",
        f"实际对话模型为 {conversation['model']}。第一轮生成完整契约，第二轮再次核对分页、分类、"
        "错误状态码及库存更新。两轮均返回合法 JSON；资源路径、方法、operationId 及分页约束保持一致。"
        "Few-Shot 以 stockQty=37 示例约束库存请求的字段名、类型和最小值。", "",
        picture(1, "contract-conversation", "书城中的两轮真实接口设计对话"), "",
        picture(1, "contract-json", "第二轮模型返回的JSON在页面展开"), "",
    ])
    return "\n".join(lines)


def report_two() -> str:
    """以实时库存变化和实际超时重试说明完整 Function Calling 闭环。"""
    live = read(2, "inventory-live.json")["body"]
    correction = read(2, "self-correction.json")["body"]
    price_calls = [call for call in correction["toolCalls"] if call["name"] == "get_competitor_price"]
    lines = [
        "## 一、函数定义", "",
        "客服助手位于原 React 书城的 /assistant 页面。Python 服务定义 check_inventory(isbn) "
        "和 get_competitor_price(isbn)，把以下 Function Schema 放入每次模型请求的 tools 列表：", "",
        block("json", json.dumps(TOOL_SCHEMAS, ensure_ascii=False, indent=2)),
        "## 二、调用解析", "",
        "模型返回 tool_calls 后，客户端读取每次调用的 id、function.name 和 function.arguments。"
        "参数使用 JSON 解析为对象，再由 ToolRegistry 根据函数名派发。JSON 无法解析、参数不是对象、"
        "缺少 ISBN 或出现未知函数时，会生成结构化错误供下一轮模型处理。", "",
        "拦截点记录轮次、函数名、参数和执行结果；前端直接显示接口返回的 toolCalls，方便核对实际调用。", "",
        picture(2, "inventory-function-calling", "原书城页面触发两个函数调用"), "",
        "## 三、本地执行", "",
        "check_inventory 携带当前顾客的 JWT 调用 Spring Boot 的书目接口，按 ISBN 读取现有数据库记录。"
        "书籍管理页面、订单扣库存和客服查询使用同一个 books 表。get_competitor_price 按课程要求模拟"
        "外部报价，返回平台、价格、到货时间和 source=competitor-price-mock。", "",
        "联调时先通过原书城的库存 PATCH 接口把算法书库存临时改为37，再让真实模型查询。"
        "check_inventory 返回37本，模型最终回复也使用该结果；验证结束后恢复原库存30本。"
        "请求和响应保存在 inventory-live.json。", "",
        "## 四、结果回填", "",
        "每个本地结果转为 role=tool 的消息，tool_call_id 与模型原调用 id 对应，content 为 JSON 结果。"
        "把原 assistant/tool_calls 消息和全部 tool 消息追加到上下文后，再调用模型生成自然语言答复。"
        "前端显示回复，同时保留函数调用卡片和完整返回值。", "",
        f"本次库存与比价问答由 {live['modelMode']} 执行，结束状态为 {live['stoppedReason']}。", "",
        picture(2, "inventory-reply", "真实模型根据37本库存与模拟报价生成答复"), "",
        "## 五、异常纠错", "",
        "工具统一返回 code、message、retryable 和 hint。错误 ISBN 会得到 INVALID_ISBN_FORMAT，"
        "模型据此请用户确认；可重试的模拟接口超时返回 UPSTREAM_TIMEOUT，提示原样重试一次。", "",
        f"实际超时用例中，第{price_calls[0]['round']}轮的 get_competitor_price 返回超时；"
        f"模型读取该 tool 结果后，在第{price_calls[-1]['round']}轮再次调用同一函数并成功。"
        "两次调用分属不同模型轮次，说明重试是依据回填结果作出的后续决策。循环另设最大轮次与连续错误限制。", "",
        picture(2, "timeout-self-correction", "超时结果回填后由模型发起重试"), "",
    ]
    return "\n".join(lines)


def report_three() -> str:
    """说明共享书目、政策向量库和实际 ReAct 过程。"""
    stats = read(3, "rag-index.json")["body"]["ragStats"]
    result = read(3, "react-case.json")["body"]
    trace = []
    for step in result["steps"]:
        payload = step["result"]
        if step["action"] == "search_book_catalog":
            summary = {"source": payload["source"], "count": payload["count"],
                       "titles": [book["title"] for book in payload["results"]]}
        else:
            summary = {"source": payload["source"], "count": payload["count"],
                       "clauses": [item["clause"] for item in payload["passages"]]}
        trace.extend([f"Thought: {step['thought']}", f"Action: {step['action']}",
                      "Action Input: " + json.dumps(step["arguments"], ensure_ascii=False),
                      "Observation 摘要: " + json.dumps(summary, ensure_ascii=False), ""])
    return "\n".join([
        "## 一、政策向量化", "",
        "书城的退换货与会员政策存放在 python-assistant/data/policy.txt，包含5章25条课程模拟政策。"
        "加载时清除排版分隔线，保留版本、章节和条款信息；按条款分块，超长内容按句子拆分，"
        "窗口420字符、重叠60字符，每块保留标题和编号。", "",
        f"本次清洗后共{stats['document']['chars']}字符，产生{stats['count']}个分块。"
        f"使用 {stats['embedder']} 在本地生成{stats['dimensions']}维稠密向量并做L2归一化。"
        "文档和查询使用同一编码器，分块及全部向量保存在 policy-vectors.json。", "",
        "## 二、政策检索", "",
        "RAG 参照课程 Simple RAG 示例：逐块计算 Embedding，保存为内存向量列表，对查询向量逐项计算"
        "余弦相似度，再取 Top-K。query_store_policy 默认返回前三条、过滤低于0.55的结果，"
        "结果含条款正文、章节、块编号和分数。模型据这些观测回答政策问题，并引用条款。", "",
        "索引缓存指纹包含政策文本、分块参数和编码器名称。语料或参数变化后重建索引；没有达到阈值的"
        "条款时返回 POLICY_NOT_COVERED，避免将弱相关内容直接作为依据。", "",
        "## 三、ReAct循环", "",
        "导购位于原书城 /guide 页面，与库存客服共用同一 Python 服务。每轮将用户问题和此前记录传给模型，"
        "解析 Thought、Action 与 Action Input，实际执行工具后写入 Observation，再进行下一轮。"
        "模型输出 Final Answer 时结束；同时限制步数、连续错误次数和重复动作。", "",
        "模型生成在 Observation 标记处停止；观测由程序执行工具后提供。完整步骤同源返回给前端并写入日志。", "",
        "## 四、工具路由", "",
        "search_book_catalog 通过当前顾客的 JWT 读取现有书城目录，按标题、分类、作者和简介匹配需求，"
        "价格和现货条件可以传入过滤。query_store_policy 调用共享政策向量库。"
        "用户同时问荐书和退货时，模型先选择查书工具，取得结果后再检索政策。", "",
        picture(3, "react-bookstore", "导购读取原书城中的微服务书目"), "",
        "## 五、执行链路", "",
        "实际用户提问为“我想买一本关于微服务的书，另外如果我买了不喜欢，拆了塑封还能退吗？”。"
        f"本次使用 {result['modelMode']}，共{result['rounds']}轮，结束状态为{result['stoppedReason']}。"
        "以下摘录实际 Thought 和参数，并将观测内容按书名或条款号作摘要；原始完整结果见 react-case.json 和运行日志。", "",
        block("text", "\n".join(trace)),
        picture(3, "react-policy", "模型继续检索政策并取得第六条等条款"), "",
        "最终答复同时推荐数据库中的微服务图书，并依据第六条说明一般拆封退货规则，补充质量问题和会员权益例外。", "",
        picture(3, "react-reply", "原书城页面显示实际导购答复"), "",
    ])


def report_four() -> str:
    """围绕原书城的接口、Java21、JWT与真实401/200证据写作。"""
    return "\n".join([
        "## 一、接口设计", "",
        "高并发与鉴权改造直接加入原 springboot-ebook，不另建作业后端。原有 MySQL、JPA、图书管理、"
        "购物车、订单和统计功能继续使用。GET /api/v1/books 提供分页列表，GET /api/v1/books/{id} "
        "返回图书 JSON，POST 新增返回201与Location，PATCH /books/{id}/stock 更新库存，资源不存在返回404。", "",
        "## 二、虚拟线程", "",
        "项目使用 Spring Boot 3.3.5，以 Java21 编译和运行。application.properties 设置 "
        "spring.threads.virtual.enabled=true；VirtualThreadConfig 把 Tomcat 协议处理器的执行器设为 "
        "Executors.newVirtualThreadPerTaskExecutor()。BookService 在查询前默认 Thread.sleep(50) 模拟慢查询。", "",
        "真实网络测试同时发送200个图书查询，全部返回200，且响应头 X-Runtime-Thread 均为 virtual-thread。"
        "运行接口直接返回当前请求线程的 isVirtual()，截图中 Java 版本为21且 requestThreadVirtual=true。", "",
        picture(4, "virtual-thread-runtime", "原书城请求实际运行于Java21虚拟线程"), "",
        "## 三、JWT生成", "",
        "项目集成 JJWT 0.12.6。原有 POST /api/v1/users/login 校验书城账号密码后，返回 user、accessToken、"
        "tokenType和expiresIn。JwtTokenService 使用HS256签名，sub绑定用户主键，附带username、role、"
        "iss、jti、iat与exp，有效期默认3600秒。前端保存Token，并在后续业务及AI请求中携带Authorization。", "",
        block("java", '''return Jwts.builder()
        .subject(user.getId().toString())
        .issuer("ebook-bookstore")
        .id(UUID.randomUUID().toString())
        .issuedAt(Date.from(now))
        .expiration(Date.from(now.plusSeconds(ttlSeconds)))
        .signWith(key, Jwts.SIG.HS256)
        .compact();'''),
        "上述为签发关键逻辑，实际代码还写入username和role。签名密钥从配置读取，强度不足时由密钥库拒绝。", "",
        "## 四、无状态鉴权", "",
        "SecurityConfig 使用 SessionCreationPolicy.STATELESS，关闭表单登录、HTTP Basic和请求会话缓存。"
        "JwtAuthenticationFilter 提取Bearer Token，校验签名、签发方和有效期；再读取现有用户记录，"
        "核对账号是否启用以及当前权限。请求结束后清理认证上下文，不创建Session或服务端Token表。", "",
        "CurrentUser 将路径userId和查询operatorId与已认证身份绑定，普通用户无法伪造管理员编号或访问他人"
        "购物车、订单、资料。AI服务将同一顾客JWT转发给书城读取库存。登录响应没有Set-Cookie；"
        "未携带或篡改Token返回401，权限不足返回403。", "",
        "## 五、鉴权测试", "",
        "在同一书城的 Swagger UI 实际执行 GET /api/v1/books/1。首次未设置Authorization，服务器返回401，"
        "响应体提示需要有效的Bearer Token。截图保留实际请求地址、状态行和响应体。", "",
        picture(4, "jwt-401", "未携带Token的实际401响应"), "",
        "使用原书城登录接口签发的Token，通过Swagger的Authorize设置Bearer凭证，再执行相同查询。"
        "服务器返回200和数据库中Digital Fundamentals的图书记录，响应头同时标明virtual-thread。", "",
        picture(4, "jwt-200", "携带合法Token的实际200响应"), "",
    ])


def main() -> None:
    """先生成可审阅的Markdown正文，再从同一内容生成四份课程模版报告。"""
    for number, factory in enumerate([report_one, report_two, report_three, report_four], 1):
        source = DOCS / f"hw{number}/report.md"
        source.write_text(factory(), encoding="utf-8")
        build_report(source, OUTPUT / f"524031910113-作业{number}.docx", number)


if __name__ == "__main__":
    main()
