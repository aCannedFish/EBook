"""大模型客户端 + 离线替身模型。

与作业2的 Function Calling 版本相比，这一版多了一个 ``stop`` 参数：
ReAct 靠文本协议回环，模型生成到 ``Observation:`` 之前就必须停下 ——
观测结果必须由本地工具真实执行后写入，绝不能由模型自己编。

- ``HttpChatClient`` / ``OpenAICompatibleClient``：OpenAI 兼容接口的两个实现
  （SDK 优先、标准库兜底），请求体一致。
- ``LocalReActLLM``：不联网的替身模型。它读同一份提示词与执行记录，
  用规则模拟一次真实的 ReAct 决策，因此没有 API Key 也能完整演示
  Thought → Action → Observation → Final Answer 的链路，单元测试也靠它把
  「循环逻辑」和「网络 + 模型随机性」解耦。
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Protocol, Sequence

from .config import LLM, LLMSettings
from .react_format import (
    Step,
    extract_observation,
    format_action,
    iter_steps,
    parse_action_input,
)

QUESTION_MARKER = "用户提问："
SCRATCHPAD_MARKER = "执行记录："
EMPTY_SCRATCHPAD = "（尚未执行任何动作）"


class ChatClient(Protocol):
    """对话模型协议。"""

    def generate(self, messages: list[dict], stop: Sequence[str] | None = None) -> str:
        ...


class ModelAPIError(RuntimeError):
    """模型接口调用失败。message 是现象，hint 是排查方向。"""

    def __init__(self, message: str, hint: str = "") -> None:
        super().__init__(message)
        self.hint = hint

    @property
    def report(self) -> str:
        return f"{self}" + (f"（{self.hint}）" if self.hint else "")


def explain_http_error(status: int, endpoint: str, detail: str) -> ModelAPIError:
    """把 HTTP 状态码翻译成可执行的排查建议。"""
    message = f"模型接口返回 {status}：{detail}"
    if status == 404:
        hint = (
            f"请求地址是 {endpoint}。404 通常是 LLM_BASE_URL 填错："
            "它应该填到 /v1 为止（如 https://models.sjtu.edu.cn/api/v1），不要再带 /chat/completions。"
        )
    elif status in (401, 403):
        hint = "LLM_API_KEY 无效或没有该模型的权限，检查密钥与模型名是否属于同一个服务商。"
    elif status == 429:
        hint = "触发了服务商的限流，稍后重试或换一个模型。"
    elif status >= 500:
        hint = "服务商侧错误，不是本地配置问题，稍后重试。"
    else:
        hint = "检查 LLM_BASE_URL / LLM_MODEL / LLM_API_KEY 三项配置。"
    return ModelAPIError(message, hint)


# ---------------------------------------------------------------------------
# 真实模型客户端
# ---------------------------------------------------------------------------


class HttpChatClient:
    """只用标准库实现的 OpenAI 兼容客户端（兜底方案）。"""

    def __init__(self, settings: LLMSettings) -> None:
        self._settings = settings

    def generate(self, messages: list[dict], stop: Sequence[str] | None = None) -> str:
        body: dict = {
            "model": self._settings.model,
            "messages": messages,
            "temperature": self._settings.temperature,
        }
        if stop:
            body["stop"] = list(stop)

        request = urllib.request.Request(
            self._settings.endpoint,
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._settings.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self._settings.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")[:300]
            raise explain_http_error(error.code, self._settings.endpoint, detail) from error
        except urllib.error.URLError as error:
            raise ModelAPIError(
                f"无法连接模型接口：{error.reason}",
                f"检查网络，以及 LLM_BASE_URL（{self._settings.base_url}）是否可达。",
            ) from error

        choice = (payload.get("choices") or [{}])[0]
        return str((choice.get("message") or {}).get("content") or "")


class OpenAICompatibleClient:
    """走 openai SDK 的客户端。装不上 SDK 时由 ``build_client`` 退回标准库实现。"""

    def __init__(self, settings: LLMSettings) -> None:
        from openai import OpenAI  # 延迟导入，便于无依赖环境退回标准库实现

        self._settings = settings
        self._client = OpenAI(
            base_url=settings.base_url,
            api_key=settings.api_key,
            timeout=settings.timeout_seconds,
        )

    def generate(self, messages: list[dict], stop: Sequence[str] | None = None) -> str:
        from openai import APIConnectionError, APIStatusError

        kwargs: dict = {
            "model": self._settings.model,
            "messages": messages,
            "temperature": self._settings.temperature,
        }
        if stop:
            kwargs["stop"] = list(stop)

        try:
            response = self._client.chat.completions.create(**kwargs)
        except APIStatusError as error:
            raise explain_http_error(
                error.status_code, self._settings.endpoint, str(error.message)[:300]
            ) from error
        except APIConnectionError as error:
            raise ModelAPIError(
                f"无法连接模型接口：{error}",
                f"检查网络，以及 LLM_BASE_URL（{self._settings.base_url}）是否可达。",
            ) from error
        return response.choices[0].message.content or ""


def build_client(settings: LLMSettings | None = None) -> ChatClient:
    """按配置构造客户端。未配置 API Key 时抛错，由调用方决定是否改用替身模型。"""
    settings = settings or LLM
    if not settings.configured:
        raise RuntimeError("未配置 LLM_API_KEY；可改用 LocalReActLLM 在离线模式下运行。")
    try:
        return OpenAICompatibleClient(settings)
    except ImportError:
        return HttpChatClient(settings)


# ---------------------------------------------------------------------------
# 离线替身模型：规则版 ReAct
# ---------------------------------------------------------------------------

#: 出现这些词才算「找书 / 荐书」意图。只凭一个「买」字不够 ——
#: 「买了不喜欢能退吗」是政策问题，不是找书问题。
BOOK_INTENT_KEYWORDS = (
    "书", "图书", "书籍", "推荐", "读物", "教材", "小说", "读本", "专著",
)
#: 出现这些词即判定为政策意图。政策词优先级高于找书词。
POLICY_INTENT_KEYWORDS = (
    "退", "换货", "退款", "退货", "拆", "塑封", "包装", "会员", "金卡", "银卡", "钻石",
    "折扣", "积分", "运费", "邮费", "发票", "价保", "政策", "包邮", "权益", "无理由",
    "签收", "取件", "投诉", "优惠券", "开票",
)
MEMBER_LEVEL_KEYWORDS = ("金卡", "钻石", "银卡", "会员等级", "会员卡")

#: 拆句的分隔符：句末标点，以及「另外」「还有」这类并列连接词。
CLAUSE_SPLIT_PATTERN = re.compile(
    r"[。；！？\n]+|，(?:另外|还有|以及|顺便|同时|并且|而且|再者|再加)|(?:另外|还有|以及|顺便|同时|并且|而且|再者)"
)
#: 书名主题里的填充词，提取关键词时剥掉。
TOPIC_STOPWORDS = (
    "我想", "想买", "买一本", "买本", "一本", "看看", "看一看", "找一本", "找找", "帮我",
    "给我", "推荐", "有没有", "有木有", "关于", "方面的", "方面", "的", "书", "图书", "书籍",
    "读物", "请问", "麻烦", "一下", "吗", "呢", "啊", "以及", "还有", "另外", "和", "与",
    "几个", "几本", "本", "我", "想要", "要", "买", "读", "看", "可以", "能", "讲", "介绍",
)
PRICE_PATTERN = re.compile(
    r"(?:预算|不超过|控制在|低于|少于)?\s*(\d+(?:\.\d+)?)\s*"
    r"(?:元|块|块钱|rmb|人民币)?\s*(?:以内|以下|之内|左右|封顶|上下|之内|以内)"
)
BUDGET_PATTERN = re.compile(r"预算\s*(?:是|为|在)?\s*(\d+(?:\.\d+)?)")
IN_STOCK_HINTS = ("有货", "现货", "马上", "立刻", "今天", "着急", "尽快", "库存")


@dataclass
class PlanItem:
    """离线模型对「用户这句话要办的事」的拆解结果。"""

    kind: str  # "book" | "policy"
    action: str
    arguments: dict
    source_clause: str

    @property
    def key(self) -> str:
        return f"{self.action}:{json.dumps(self.arguments, ensure_ascii=False, sort_keys=True)}"


@dataclass
class LocalReActLLM:
    """不联网的替身模型，用规则模拟一次真实的 ReAct 决策。

    它做四件事，与真实模型在 ReAct 循环里的行为一一对应：

    1. 把用户提问拆成若干子问题并判断意图（找书 / 问政策），形成行动计划；
    2. 每一步先输出 ``Thought`` 说明为什么做这个动作，再输出 ``Action`` 与 ``Action Input``；
    3. 读回 ``Observation``：失败且 ``retryable`` 时换个参数重试一次
       （放宽关键词、去掉过滤条件），不可重试时放弃这条路径并如实说明；
    4. 信息够了输出 ``Final Answer``，政策结论逐条引用检索到的条款号。

    它只替换「模型」这一层：工具执行、观测回填、解析容错走的都是正式代码路径。
    """

    #: 已重试过的动作键，避免对同一个失败无限重试。
    retried: set[str] = field(default_factory=set)

    def generate(self, messages: list[dict], stop: Sequence[str] | None = None) -> str:
        question, scratchpad = self._split_prompt(messages)
        steps = iter_steps(scratchpad)
        plan = build_plan(question)

        if not plan:
            return self._no_intent_answer(question)

        attempts = self._collect_attempts(steps)

        # ---- 第一步：处理找书意图 ----------------------------------------
        book_item = next((item for item in plan if item.kind == "book"), None)
        if book_item is not None:
            decision = self._decide_book(book_item, attempts)
            if decision is not None:
                return decision

        # ---- 第二步：依次处理政策意图（含会员权益这类补充检索）------------
        for item in [entry for entry in plan if entry.kind == "policy"]:
            decision = self._decide_policy(item, attempts)
            if decision is not None:
                return decision

        return self._final_answer(question, plan, attempts)

    # -- 提示词拆解 ---------------------------------------------------------

    @staticmethod
    def _split_prompt(messages: list[dict]) -> tuple[str, str]:
        """从提示词里取回「用户提问」与「执行记录」。

        两条信息都放在同一条 user 消息里，用标记分隔：离线模型没有真正的对话记忆，
        只能像真实模型那样从上下文里读回已经发生的事。
        """
        content = ""
        for message in reversed(messages):
            if message.get("role") == "user":
                content = str(message.get("content") or "")
                break
        question = content
        scratchpad = ""
        if QUESTION_MARKER in content:
            question = content.split(QUESTION_MARKER, 1)[1]
        if SCRATCHPAD_MARKER in question:
            question, scratchpad = question.split(SCRATCHPAD_MARKER, 1)
        question = question.strip()
        # 执行记录后面还跟着提示词收尾的那句「请输出下一步」，属于脚手架，不是记录本身。
        for tail in ("请输出下一步",):
            marker = f"\n\n{tail}"
            if marker in scratchpad:
                scratchpad = scratchpad.split(marker, 1)[0]
        if EMPTY_SCRATCHPAD in scratchpad:
            scratchpad = ""
        return question, scratchpad.strip()

    # -- 决策 ---------------------------------------------------------------

    def _decide_book(self, item: PlanItem, attempts: dict) -> str | None:
        history = attempts.get(item.action, [])
        if not history:
            thought = (
                f"用户想找书，关键词是「{item.arguments.get('query')}」。"
                "先检索书目，看有没有匹配的图书和库存。"
            )
            return self._act(thought, item.action, item.arguments)

        arguments, ok, payload = history[-1]
        if ok:
            return None  # 已经拿到结果，交给后面的步骤

        error = (payload or {}).get("error", {})
        retry_key = f"book-broaden:{item.key}"
        if error.get("retryable") and retry_key not in self.retried:
            self.retried.add(retry_key)
            broadened = broaden_book_arguments(item.arguments)
            thought = (
                f"上一次检索「{item.arguments.get('query')}」失败：{error.get('message')}。"
                f"错误提示 {error.get('hint')}"
                f"我按提示把条件放宽为「{broadened.get('query')}」，"
                "去掉价格与有货限制再试一次。"
            )
            return self._act(thought, item.action, broadened)

        return None  # 放弃找书，继续处理政策问题

    def _decide_policy(self, item: PlanItem, attempts: dict) -> str | None:
        history = attempts.get(item.action, [])
        current = json.dumps(item.arguments.get("question"), ensure_ascii=False)
        mine = [
            entry
            for entry in history
            if json.dumps(entry[0].get("question"), ensure_ascii=False) == current
        ]

        if not mine:
            if item.source_clause:
                thought = (
                    f"用户还问了政策问题「{item.source_clause}」。"
                    "这是退换货/会员政策，必须查政策库拿条款原文，不能凭常识回答。"
                )
            else:
                thought = (
                    f"前一条政策只覆盖了一般规则，还需要补充检索「{item.arguments.get('question')}」，"
                    "看会员等级是否有额外权益。"
                )
            return self._act(thought, item.action, item.arguments)

        arguments, ok, payload = mine[-1]
        if not ok:
            error = (payload or {}).get("error", {})
            retry_key = f"policy-retry:{current}"
            if error.get("retryable") and retry_key not in self.retried:
                self.retried.add(retry_key)
                simpler = simplify_policy_question(str(item.arguments.get("question") or ""))
                thought = (
                    f"检索「{item.arguments.get('question')}」没有命中相关条款："
                    f"{error.get('message')}。{error.get('hint')}"
                    f"我把问题改写成政策原文的说法「{simpler}」再检索一次。"
                )
                return self._act(thought, item.action, {"question": simpler, "top_k": 3})
        return None

    # -- 结果组装 -----------------------------------------------------------

    def _act(self, thought: str, action: str, arguments: dict) -> str:
        return f"Thought: {thought}\n{format_action(action, arguments)}"

    def _no_intent_answer(self, question: str) -> str:
        return (
            "Thought: 这句话里既没有找书的需求，也没有政策问题，我不需要调用工具。\n"
            "Final Answer: 我是 E-BookStore 的导购助手，可以帮你做两件事："
            "一是按主题推荐书目（例如「有没有关于微服务的书」），"
            "二是解答退换货与会员政策（例如「拆了塑封还能退吗」）。"
            f"你刚才说的「{question.strip()[:40]}」我还没理解到具体需求，"
            "可以说得再具体一点。"
        )

    def _final_answer(self, question: str, plan: list[PlanItem], attempts: dict) -> str:
        book_item = next((item for item in plan if item.kind == "book"), None)
        policy_items = [item for item in plan if item.kind == "policy"]

        sections: list[str] = []
        if book_item is not None:
            sections.append(self._describe_books(book_item, attempts))
        for item in policy_items:
            sections.append(self._describe_policy(item, attempts))

        if not sections:
            sections.append("这次没有拿到可用的工具结果。")

        thoughts: list[str] = []
        if book_item is not None:
            thoughts.append("书目已查过")
        if policy_items:
            thoughts.append("政策条款已查过")
        thought = (
            "，".join(thoughts) + "，信息已经足够，可以给出最终答复了。"
            "答复里要写清书名、价格与库存，政策结论要标出条款号。"
        )
        body = "\n\n".join(section for section in sections if section)
        return f"Thought: {thought}\nFinal Answer: {body}"

    @staticmethod
    def _collect_attempts(steps: list[Step]) -> dict[str, list[tuple[dict, bool, dict | None]]]:
        """把观测记录按工具名归拢，供决策使用。"""
        attempts: dict[str, list[tuple[dict, bool, dict | None]]] = {}
        for step in steps:
            if not step.action:
                continue
            arguments, _ = parse_action_input(step.action_input_raw)
            ok, payload = extract_observation(step)
            attempts.setdefault(step.action, []).append(
                (arguments or {}, bool(ok), payload)
            )
        return attempts

    def _describe_books(self, item: PlanItem, attempts: dict) -> str:
        history = attempts.get("search_book_catalog", [])
        success = next((payload for _, ok, payload in reversed(history) if ok and payload), None)
        if success is None:
            failure = next(
                (payload for _, ok, payload in reversed(history) if payload and not ok), None
            )
            message = ((failure or {}).get("error") or {}).get("message", "工具没有返回结果")
            return f"关于找书：我查了书目但没有查到可推荐的图书（{message}）。"

        lines: list[str] = []
        used_query = str(success.get("query") or "")
        planned_query = str(item.arguments.get("query") or "")
        if used_query and planned_query and used_query != planned_query:
            # 发生过自我纠错：说明原来的关键词没命中，换宽的词才查到的。
            lines.append(
                f"关于找书：目录里没有「{planned_query}」直接相关的书，"
                f"我把关键词放宽成「{used_query}」后找到这些："
            )
        else:
            lines.append(f"关于找书（检索词：{used_query}）：")

        filters = success.get("filters") or {}
        note: list[str] = []
        if filters.get("maxPrice"):
            note.append(f"价格 {filters['maxPrice']} 元以内")
        if filters.get("inStockOnly"):
            note.append("只看有货")
        if note:
            lines.append("筛选条件：" + "、".join(note) + "。")
        for index, book in enumerate(success.get("results") or [], start=1):
            stock = "有货，库存 {} 本".format(book["stockQty"]) if book["inStock"] else "暂时缺货"
            lines.append(
                f"{index}. 《{book['title']}》{book['author']} 著，{book['publisher']} "
                f"{book['year']} 年版，售价 {book['price']} 元，{stock}，"
                f"评分 {book['rating']}。{book['summary']}"
            )
        out_of_stock = success.get("outOfStockMatches") or []
        if out_of_stock:
            lines.append(
                "另外这些书也匹配主题但当前缺货：" + "、".join(f"《{title}》" for title in out_of_stock) + "。"
            )
        return "\n".join(lines)

    def _describe_policy(self, item: PlanItem, attempts: dict) -> str:
        asked = str(item.arguments.get("question") or "")
        history = attempts.get("query_store_policy", [])
        matched = [
            (args, payload)
            for args, ok, payload in history
            if ok and payload and str(args.get("question") or "") == asked and payload.get("passages")
        ]
        if not matched:
            # 检索被改写后重试成功的情况：问题的字面不同，但它回答的仍是同一条子问题。
            matched = [
                (args, payload)
                for args, ok, payload in history
                if ok
                and payload
                and payload.get("passages")
                and _overlap_ratio(asked, str(args.get("question") or "")) > 0.34
            ]
        if not matched:
            failure = next(
                (
                    payload
                    for args, ok, payload in reversed(history)
                    if payload
                    and not ok
                    and _overlap_ratio(asked, str(args.get("question") or "")) > 0.34
                ),
                None,
            )
            detail = ((failure or {}).get("error") or {}).get("message", "政策库没有返回相关条款")
            return (
                f"关于政策问题「{asked}」：政策库中没有检索到直接对应的条款（{detail}），"
                "这个我没有依据回答，建议以在线客服的答复为准。"
            )

        args, payload = matched[-1]
        passages = payload.get("passages") or []
        if args.get("question") != asked:
            title = f"关于政策问题「{asked}」（政策库检索用词：「{args.get('question')}」）："
        else:
            title = f"关于政策问题「{asked}」："
        lines = [title]
        for passage in passages:
            body = _passage_body(passage["text"], passage.get("clause") or "")
            lines.append(
                f"· 《退换货与会员政策》{passage['headingPath']}"
                f"（相似度 {passage['score']}）：{body}"
            )
        # 结论行只挑与问题最贴近的那一句，而不是把整段再贴一遍 ——
        # 引用要完整（上面已经给了原文），结论要短。
        top_body = _passage_body(passages[0]["text"], passages[0].get("clause") or "")
        conclusion = _most_relevant_line(top_body, asked)
        if conclusion:
            lines.append(f"综合上述条款，与本问题最相关的一句是：{conclusion}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# 规则：意图拆解与问题改写
# ---------------------------------------------------------------------------


def split_clauses(question: str) -> list[str]:
    """把用户提问拆成子句，供逐句判断意图。"""
    return [clause.strip(" ，,、") for clause in CLAUSE_SPLIT_PATTERN.split(question) if clause.strip(" ，,、")]


def classify_clause(clause: str) -> str | None:
    """判断一个子句的意图。政策词优先：含「退/拆/会员」的子句即使带「书」也按政策处理。"""
    if any(keyword in clause for keyword in POLICY_INTENT_KEYWORDS):
        return "policy"
    if any(keyword in clause for keyword in BOOK_INTENT_KEYWORDS):
        return "book"
    return None


def extract_topic(clause: str) -> str:
    """从子句里提取检索主题词。

    先试「关于 X 的书」「讲 X 的书」这类模板；模板不匹配时，
    剥掉价格条件、有货要求与口语填充词，再从剩下的片段里挑主题词。
    挑法不是「取最长的片段」—— 那样会选中「最好有现货」这种修饰语，
    而是取**最后一个**实词片段：中文里定语在前、中心语在后
    （「100 元以内的微服务书」的主题是「微服务」，不是「100 元以内」）。
    """
    matched = re.search(r"关于(.{1,24}?)的", clause)
    if matched:
        return matched.group(1).strip()
    matched = re.search(r"(?:讲|介绍|写的是|写的|关于)\s*(.{1,24}?)(?:的书|的图书|方面)", clause)
    if matched:
        return matched.group(1).strip()

    text = PRICE_PATTERN.sub(" ", clause)
    text = BUDGET_PATTERN.sub(" ", text)
    for hint in IN_STOCK_HINTS:
        text = text.replace(hint, " ")
    for word in sorted(TOPIC_STOPWORDS, key=len, reverse=True):
        text = text.replace(word, " ")

    tokens = [
        token
        for token in re.split(r"[\s，,、。！？!?：:；;（）()《》]+", text)
        if token and not token.isdigit() and not _is_price_leftover(token) and not _is_filler_token(token)
    ]
    if not tokens:
        return clause.strip()
    return tokens[-1][:24]


#: 口语修饰词的字符集合。剔掉「有现货」「最好」「要」这类词之后，
#: 剩下的最后一个实词片段才是主题词。
FILLER_CHARS = set("有要的想买个本点最好希望能可以请给帮我你他它们和与或是在吗呢吧了啊着过把就都还也才")


def _is_filler_token(token: str) -> bool:
    return all(char in FILLER_CHARS for char in token)


def _is_price_leftover(token: str) -> bool:
    """判断片段是否只是价格/条件的残渣，例如「元以内」「左右」。"""
    stripped = token.strip()
    if not stripped:
        return True
    if re.fullmatch(r"[\d.]+", stripped):
        return True
    return all(char in "元块以内左右上下以下封顶预算不超过少于低于控制在是的最" for char in stripped)


def build_plan(question: str) -> list[PlanItem]:
    """把提问拆成行动计划，顺序即调用顺序。

    「会员 + 拆封退货」这种问题需要两跳检索：第一条讲一般的拆封规则，
    第二条才讲会员的已拆封退货权益。所以命中该组合时，
    计划里会多出一条显式的补充检索 —— 多跳检索是检索规划的一部分，
    不是循环里的特例分支。
    """
    plan: list[PlanItem] = []
    seen: set[str] = set()

    def add(item: PlanItem) -> None:
        if item.key not in seen:
            seen.add(item.key)
            plan.append(item)

    for clause in split_clauses(question):
        kind = classify_clause(clause)
        if kind is None:
            continue
        if kind == "book":
            add(
                PlanItem(
                    kind="book",
                    action="search_book_catalog",
                    arguments=build_book_arguments(clause),
                    source_clause=clause,
                )
            )
            continue

        add(
            PlanItem(
                kind="policy",
                action="query_store_policy",
                arguments={"question": clause, "top_k": 3},
                source_clause=clause,
            )
        )
        if needs_member_follow_up(clause):
            add(
                PlanItem(
                    kind="policy",
                    action="query_store_policy",
                    arguments={"question": "会员已拆封退货权益", "top_k": 3},
                    source_clause="",
                )
            )
    return plan


def needs_member_follow_up(clause: str) -> bool:
    """判断是否需要追加一次会员权益检索。"""
    mentions_level = any(word in clause for word in MEMBER_LEVEL_KEYWORDS)
    mentions_unsealed = any(word in clause for word in ("拆", "塑封", "无理由"))
    return mentions_level and mentions_unsealed


def build_book_arguments(clause: str) -> dict:
    """从找书子句里抽出检索词与可选过滤条件。"""
    arguments: dict = {"query": extract_topic(clause)}

    price = PRICE_PATTERN.search(clause) or BUDGET_PATTERN.search(clause)
    if price:
        arguments["max_price"] = int(float(price.group(1)))

    if any(hint in clause for hint in IN_STOCK_HINTS):
        arguments["in_stock_only"] = True

    return arguments


def broaden_book_arguments(arguments: dict) -> dict:
    """检索失败后的放宽策略：换成更宽的主题词，并去掉价格与有货限制。

    真实模型在这里做的事是一样的 —— 读 error.hint，
    把「Rust 异步编程」放宽成「编程」，而不是原样重发同一个请求。
    """
    return {"query": _shorten_query(str(arguments.get("query") or ""))}


#: 放宽检索时可用的上位主题词。目录里的书都挂在这些大类下面，
#: 用一个上位词重试，比继续猜长尾关键词更容易拿到结果。
BROAD_TOPICS = (
    "编程", "架构", "微服务", "算法", "计算机", "物理", "历史", "文学", "经济", "教材",
)


def _shorten_query(query: str) -> str:
    """把「Rust 异步编程」这类没命中的长关键词换成一个更宽的主题词。"""
    cleaned = query.strip()
    if not cleaned:
        return "编程"
    for topic in BROAD_TOPICS:
        if topic in cleaned:
            return topic
    latin = re.match(r"[A-Za-z][A-Za-z0-9\-_]*", cleaned)
    if latin:
        # 只有英文词且没命中：换成大类，避免拿着一个目录里根本不存在的词反复查。
        return "编程"
    return cleaned[:2]


def simplify_policy_question(question: str) -> str:
    """政策检索失败后的改写：剥掉口语铺垫，只留政策关键词。"""
    keywords = [word for word in POLICY_INTENT_KEYWORDS if word in question]
    if not keywords:
        return question[:12]
    # 「拆」+「塑封」这类组合词信息量最大，优先取长词。
    keywords.sort(key=len, reverse=True)
    core = keywords[:2]
    if "拆" in question and "塑封" in question:
        return "塑封已拆 无理由退货"
    if "退" in question:
        return "七天无理由退货 " + "".join(core)
    return "".join(core)


def _overlap_ratio(left: str, right: str) -> float:
    """两个问题的字符重合度，用于把观测结果与它对应的子问题对上。"""
    if not left or not right:
        return 0.0
    left_set, right_set = set(left), set(right)
    return len(left_set & right_set) / max(len(left_set), 1)


def _passage_body(text: str, clause: str) -> str:
    """取出条款正文。

    块文本的第一行是「《政策》章 · 条」的引用头（它参与向量化，但不该进答复），
    第二行往往又是条标题本身，也要去掉，剩下才是真正要引用的条款正文。
    """
    lines = text.split("\n")
    body = lines[1:] if len(lines) > 1 else lines
    if body and clause:
        head = body[0].strip()
        # 条标题形如「第六条【塑封与拆封规则】」，取「第六条」比对即可。
        clause_number = clause.split("【")[0].strip()
        if clause_number and head.startswith(clause_number):
            body = body[1:]
    return "\n".join(body).strip()


#: 状态的极性标记。用户问「拆了塑封还能退吗」时，答案在「塑封已拆」那一款；
#: 问「还没拆能退吗」时，答案在「塑封未拆」那一款。两款用字高度重合，
#: 只按字面重合度挑会挑错，所以先按极性把方向相反的候选剔掉。
DONE_MARKERS = ("已", "已经", "拆了", "拆开", "用了", "买了", "收到货")
NOT_DONE_MARKERS = ("未", "没", "还没", "尚未", "不曾")


def _polarity(text: str) -> str | None:
    """判断一段文字讲的是「已经发生」还是「还没发生」。判断不出时返回 None。"""
    has_done = any(marker in text for marker in DONE_MARKERS)
    has_not_done = any(marker in text for marker in NOT_DONE_MARKERS)
    if has_done and not has_not_done:
        return "done"
    if has_not_done and not has_done:
        return "not_done"
    return None


def _most_relevant_line(body: str, question: str) -> str:
    """从条款正文里挑出与问题最贴近的一行，作为结论引用。

    规则版的选择方式：先按状态极性把方向相反的候选剔掉，再按与问题的字符重合度排序，
    重合度相同时取靠前的那一款（前款通常是一般规则，后面的款是例外）。

    例如问「拆了塑封还能退吗」：「（一）塑封未拆：可直接申请七天无理由退货」
    和「（二）塑封已拆：原则上不支持七天无理由退货」命中的字几乎一样，
    但它们讲的是相反的两件事 —— 极性过滤保证引用的是回答用户那一款。
    挑不出来时返回空串，不硬凑结论。
    """
    candidates = [
        line.strip()
        for line in body.splitlines()
        if len(line.strip()) >= 8 and not line.strip().endswith(("：", ":"))
    ]
    if not candidates:
        return ""

    wanted = _polarity(question)
    if wanted is not None:
        aligned = [line for line in candidates if _polarity(line) in (wanted, None)]
        if aligned:
            candidates = aligned

    question_chars = set(question)
    scored = [
        (len(question_chars & set(line)), -index, line)
        for index, line in enumerate(candidates)
    ]
    matches, _, best = max(scored)
    return best if matches / max(len(question_chars), 1) > 0.2 else ""
