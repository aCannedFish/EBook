"""不联网时的替身模型：四个工具都会用，且同样产出 Tool Call 与执行记录。

真实的 Function Calling 里模型自己决定调哪个函数、传什么参数；这里用规则复刻同一件事：

1. 拆意图：有 ISBN 就查库存（问到价格再比价），没有 ISBN 就按主题找书、
   按子句判断要不要查政策；
2. 每一步先给一句 Thought，再发 Tool Call（参数是 JSON 对象）；
3. 读回观测：失败且 retryable 时换参数重试一次 —— 书目放宽关键词、政策改写问法、
   库存/比价原样重试；ISBN 本身不合法就不重试，直接请用户确认；
4. 信息够了输出最终答复，政策结论逐条引用条款号。

它只替换「模型」这一层，工具执行、观测回填、循环控制、重复动作检测
走的都是正式代码路径，所以离线也能完整演示作业2 与作业3 要求的链路。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from ..guide.llm import (
    LocalReActLLM,
    PlanItem,
    _overlap_ratio,
    broaden_book_arguments,
    build_plan,
    classify_clause,
    simplify_policy_question,
    split_clauses,
)
from ..llm import (
    AssistantTurn,
    ISBN_LEVEL_ERRORS,
    LocalRuleBasedLLM,
    PRICE_KEYWORDS,
    ToolCallRequest,
)

#: 库存类子句的关键词：出现这些词、且给了 ISBN 时，先查本店库存。
STOCK_HINTS = ("多少本", "几本", "库存", "有货", "现货", "还有", "有没有", "卖多少")


@dataclass
class LocalUnifiedLLM(LocalReActLLM):
    """离线替身模型：把四个工具的计划、重试与答复组织成 Tool Call。"""

    #: 用来生成稳定的 tool_call id（同一请求内唯一即可）。
    call_seq: int = field(default=0)

    def complete(self, messages: list[dict], tools: list[dict]) -> AssistantTurn:
        question = self._last_user_question(messages)
        attempts = self._collect_tool_attempts(messages)
        plan = self._plan(question)

        if not plan:
            return AssistantTurn(content=self._no_intent_answer(question))

        # ISBN 本身不合法时，后面的比价与找书都没有意义，直接给确认书号的说法。
        isbn = LocalRuleBasedLLM._extract_isbn(question)
        if isbn and self._isbn_unusable(isbn, attempts):
            plan = [item for item in plan if item.kind == "inventory"]

        for item in plan:
            turn = self._decide(item, attempts)
            if turn is not None:
                return turn

        return AssistantTurn(content=self._final_answer(question, plan, attempts))

    @staticmethod
    def _isbn_unusable(isbn: str, attempts: dict) -> bool:
        for args, ok, payload in attempts.get("check_inventory", []):
            if args.get("isbn") != isbn or ok:
                continue
            code = ((payload or {}).get("error") or {}).get("code")
            if code in ISBN_LEVEL_ERRORS:
                return True
        return False

    # -- 计划 ---------------------------------------------------------------

    def _plan(self, question: str) -> list[PlanItem]:
        """把提问拆成按顺序执行的工具调用。"""
        isbn = LocalRuleBasedLLM._extract_isbn(question)
        if not isbn:
            return self._catalog_and_policy_plan(question)

        plan = [
            PlanItem(
                kind="inventory",
                action="check_inventory",
                arguments={"isbn": isbn},
                source_clause=question,
            )
        ]
        if any(word in question for word in PRICE_KEYWORDS):
            plan.append(
                PlanItem(
                    kind="price",
                    action="get_competitor_price",
                    arguments={"isbn": isbn},
                    source_clause=question,
                )
            )

        # 「ISBN 为…的书还有多少本」已经由库存查询覆盖，不能再当成找书需求，
        # 否则会把一串数字当关键词去检索书目。
        rest = "，".join(
            clause
            for clause in split_clauses(question)
            if not self._mentions_isbn(clause, isbn)
            and not any(hint in clause for hint in STOCK_HINTS)
        )
        if rest.strip():
            plan.extend(self._catalog_and_policy_plan(rest))
        return plan

    @staticmethod
    def _mentions_isbn(clause: str, isbn: str) -> bool:
        digits = "".join(char for char in isbn if char.isdigit())
        compact = "".join(char for char in clause if char.isdigit())
        return bool(digits) and digits in compact

    @staticmethod
    def _catalog_and_policy_plan(question: str) -> list[PlanItem]:
        """复用导购侧的规划：找书在前、政策在后，会员权益会追加一次检索。"""
        plan: list[PlanItem] = []
        seen: set[str] = set()

        for clause in split_clauses(question):
            if classify_clause(clause) is None:
                continue
            for item in build_plan(clause):
                if item.key in seen:
                    continue
                seen.add(item.key)
                plan.append(item)
        return plan

    # -- 决策 ---------------------------------------------------------------

    def _decide(self, item: PlanItem, attempts: dict) -> AssistantTurn | None:
        history = self._history_for(item, attempts)

        if not history:
            return self._call(item, self._first_thought(item))

        _, ok, payload = history[-1]
        if ok:
            return None  # 已拿到结果，交给最终答复

        error = (payload or {}).get("error") or {}
        if error.get("code") in ISBN_LEVEL_ERRORS:
            # ISBN 本身不可用：换参数重试也是白调，留到答复里请用户确认。
            return None
        if not error.get("retryable") or item.key in self.retried:
            return None

        self.retried.add(item.key)
        retry_arguments = self._retry_arguments(item)
        thought = (
            f"上一次 {item.action} 没有成功：{error.get('message')}。"
            f"{error.get('hint')}"
            f"我按提示改成「{self._describe_arguments(retry_arguments)}」再试一次。"
        )
        return self._call(item, thought, retry_arguments)

    def _history_for(self, item: PlanItem, attempts: dict) -> list[tuple[dict, bool, dict | None]]:
        history = attempts.get(item.action, [])
        if item.kind in {"inventory", "price"}:
            isbn = item.arguments.get("isbn")
            return [entry for entry in history if entry[0].get("isbn") == isbn]
        if item.kind == "book":
            return list(history)
        asked = str(item.arguments.get("question") or "")
        return [
            entry
            for entry in history
            if str(entry[0].get("question") or "") == asked
            or _overlap_ratio(asked, str(entry[0].get("question") or "")) > 0.34
        ]

    @staticmethod
    def _retry_arguments(item: PlanItem) -> dict:
        if item.kind == "book":
            return broaden_book_arguments(item.arguments)
        if item.kind == "policy":
            return {
                "question": simplify_policy_question(str(item.arguments.get("question") or "")),
                "top_k": 3,
            }
        return dict(item.arguments)

    # -- 动作与理由 ---------------------------------------------------------

    def _call(self, item: PlanItem, thought: str, arguments: dict | None = None) -> AssistantTurn:
        payload = arguments if arguments is not None else item.arguments
        self.call_seq += 1
        return AssistantTurn(
            content=thought,
            tool_calls=(
                ToolCallRequest(
                    id=f"call_{item.action}_{self.call_seq}",
                    name=item.action,
                    arguments_raw=json.dumps(payload, ensure_ascii=False),
                ),
            ),
            finish_reason="tool_calls",
        )

    @staticmethod
    def _first_thought(item: PlanItem) -> str:
        if item.kind == "inventory":
            return f"用户要查 ISBN {item.arguments.get('isbn')} 的库存，先查本店实时库存与售价。"
        if item.kind == "price":
            return "用户还想和其他平台比价，再查一次竞品报价。"
        if item.kind == "book":
            return (
                f"用户想找「{item.arguments.get('query')}」相关的书，"
                "先检索书目看有没有匹配的版本与库存。"
            )
        return (
            f"用户问了政策问题「{item.arguments.get('question')}」，"
            "这属于退换货或会员规则，必须查政策库拿条款原文，不能凭常识回答。"
        )

    @staticmethod
    def _describe_arguments(arguments: dict) -> str:
        return "，".join(f"{key}={value}" for key, value in arguments.items())

    # -- 读取执行记录 -------------------------------------------------------

    @staticmethod
    def _last_user_question(messages: list[dict]) -> str:
        for message in reversed(messages):
            if message.get("role") == "user":
                return str(message.get("content") or "")
        return ""

    @classmethod
    def _collect_tool_attempts(
        cls, messages: list[dict]
    ) -> dict[str, list[tuple[dict, bool, dict | None]]]:
        """按工具名归拢已经执行过的调用，供决策判断「还要不要再来一次」。

        assistant 消息里带着 tool_calls，紧跟其后的 tool 消息才是结果；
        两边靠 call id 对上，所以这里维护一个待配对的表。
        """
        attempts: dict[str, list[tuple[dict, bool, dict | None]]] = {}
        pending: dict[str, tuple[str, dict]] = {}

        for message in messages:
            role = message.get("role")
            if role == "assistant":
                for call in message.get("tool_calls") or []:
                    function = call.get("function") or {}
                    try:
                        arguments = json.loads(function.get("arguments") or "{}")
                    except json.JSONDecodeError:
                        arguments = {}
                    pending[str(call.get("id"))] = (
                        str(function.get("name") or ""),
                        arguments if isinstance(arguments, dict) else {},
                    )
                continue

            if role != "tool":
                continue
            name, arguments = pending.pop(str(message.get("tool_call_id")), (None, {}))
            name = name or str(message.get("name") or "")
            try:
                payload = json.loads(message.get("content") or "{}")
            except json.JSONDecodeError:
                payload = None
            ok = bool(payload and payload.get("ok"))
            attempts.setdefault(name, []).append((arguments, ok, payload))

        return attempts

    # -- 最终答复 -----------------------------------------------------------

    def _final_answer(self, question: str, plan: list[PlanItem], attempts: dict) -> str:
        sections: list[str] = []
        for item in plan:
            if item.kind == "inventory":
                sections.append(self._describe_inventory(item, attempts))
            elif item.kind == "price":
                sections.append(self._describe_prices(item, attempts))
            elif item.kind == "book":
                sections.append(self._describe_books(item, attempts))
            elif item.kind == "policy":
                sections.append(self._describe_policy(item, attempts))

        body = "\n\n".join(section for section in sections if section)
        if not body:
            return self._no_intent_answer(question)
        return body

    def _describe_inventory(self, item: PlanItem, attempts: dict) -> str:
        isbn = item.arguments.get("isbn")
        history = [
            entry for entry in attempts.get("check_inventory", []) if entry[0].get("isbn") == isbn
        ]
        success = next((payload for _, ok, payload in reversed(history) if ok and payload), None)

        if success is None:
            failure = next(
                (payload for _, ok, payload in reversed(history) if payload and not ok), None
            )
            error = (failure or {}).get("error") or {}
            message = error.get("message", "库存接口没有返回结果")
            if error.get("code") == "INVALID_ISBN_FORMAT":
                return (
                    f"关于库存：你给的 ISBN「{isbn}」格式不对（{message}），"
                    "我无法确认是哪一本书。麻烦核对书号后再发我，10 位或 13 位都可以。"
                )
            return f"关于库存：本店库存没查到（{message}），先不给你不确定的数字。"

        lines = [
            f"《{success['title']}》（{success['author']}，ISBN {success['isbn']}）"
            f"本店当前库存 {success['stockQty']} 本，状态「{success['stockText']}」，"
            f"售价 {success['price']} 元。"
        ]
        if success["stockQty"] <= 5:
            lines.append("库存偏紧，要买的话建议尽快下单。")
        return "\n".join(lines)

    def _describe_prices(self, item: PlanItem, attempts: dict) -> str:
        isbn = item.arguments.get("isbn")
        history = [
            entry
            for entry in attempts.get("get_competitor_price", [])
            if entry[0].get("isbn") == isbn
        ]
        success = next((payload for _, ok, payload in reversed(history) if ok and payload), None)
        if success is None:
            failure = next(
                (payload for _, ok, payload in reversed(history) if payload and not ok), None
            )
            message = ((failure or {}).get("error") or {}).get(
                "message", "比价接口没有返回结果"
            )
            return f"关于比价：这次没拿到其他平台的报价（{message}）。"

        quotes = success.get("quotes") or []
        detail = "；".join(
            f"{quote['platform']} {quote['price']} 元"
            f"（{'有货' if quote['inStock'] else '缺货'}，{quote['deliveryDays']} 天到）"
            for quote in quotes
        )
        cheapest = min(quotes, key=lambda quote: quote["price"])
        lines = [f"其他平台报价：{detail}。最低价出现在 {cheapest['platform']}。"]

        stock = next(
            (
                payload
                for args, ok, payload in reversed(attempts.get("check_inventory", []))
                if ok and payload and args.get("isbn") == isbn
            ),
            None,
        )
        if stock:
            diff = stock["price"] - cheapest["price"]
            if diff > 0:
                lines.append(f"本店售价比最低价贵 {diff} 元。")
            elif diff < 0:
                lines.append(f"本店售价比最低价便宜 {-diff} 元。")
            else:
                lines.append("本店售价与最低价持平。")
        return "\n".join(lines)

    def _no_intent_answer(self, question: str) -> str:
        return (
            "我是 E-BookStore 的客服助手，可以帮你查某本书的库存和各家价格、"
            "按主题找书，也能解答退换货与会员政策。"
            f"你刚才说的「{question.strip()[:40]}」我还没听出具体要查什么，"
            "补一句要查的书或政策问题就行。"
        )
