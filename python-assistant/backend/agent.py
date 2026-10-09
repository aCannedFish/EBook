"""Function Calling 循环。

这是「拦截模型输出 → 本地执行 → 结果回传 → 生成回答」这四步的落点：
``BookstoreAssistant.chat`` 反复询问模型，每当模型要求调用函数，就把请求拦截下来、
打印函数名与参数、本地执行、把结果以 tool 角色消息塞回上下文，直到模型给出自然语言回答。

异常处理集中在这一层，分三处：
- 参数不是合法 JSON  -> 生成一条 tool 错误消息回传，让模型重新表述参数；
- 工具执行失败       -> 由 tools.dispatch 收敛成结构化错误，连同 hint 一起回传；
- 循环失控           -> 超过最大轮次或连续错误上限时中止，返回可解释的兜底话术。
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Callable, Iterable

from .config import AGENT, AgentSettings
from .llm import AssistantTurn, ChatClient, ToolCallRequest
from .tools import ToolOutcome, ToolRegistry, build_registry

logger = logging.getLogger("ebook.assistant")

SYSTEM_PROMPT = """你是「E-BookStore 电子书城」的在线客服助手，负责解答顾客关于图书库存与价格的问题。

【必须遵守】
1. 任何关于库存数量、是否有货、本店售价、其他平台价格的结论，都必须来自工具返回的数据。
   没有工具结果时，明确说明「我需要先查一下」，不得凭常识估计或编造。
2. 不要猜测 ISBN。用户没给 ISBN 时，先请用户提供；用户给的值看起来不像 ISBN 时，
   把原值复述一遍请其确认，不要自己补位、改位或替换成相近的 ISBN。
3. 工具返回 {"ok": false} 时，读 error.code 与 error.hint：
   retryable 为 true 可以原样重试一次；否则换策略或如实告知用户，
   绝不能把失败包装成「应该还有货」这类模糊说法。
4. 回答用中文，先给结论再给细节，不要输出 JSON 原文，也不要出现「根据工具返回」这类实现细节。
5. 同一次回答里不要重复调用同一个函数超过两次。"""


@dataclass
class ToolEvent:
    """一次函数调用的可观测记录：被拦截下来的函数名、参数与执行结果。"""

    round_index: int
    name: str
    arguments: dict
    ok: bool
    payload: dict
    duration_ms: int
    parse_error: str | None = None

    def to_dict(self) -> dict:
        return {
            "round": self.round_index,
            "name": self.name,
            "arguments": self.arguments,
            "ok": self.ok,
            "durationMs": self.duration_ms,
            "result": self.payload,
            "parseError": self.parse_error,
        }

    def log_line(self) -> str:
        args = json.dumps(self.arguments, ensure_ascii=False)
        status = "ok" if self.ok else f"failed:{self.payload.get('error', {}).get('code')}"
        return (
            f"[TOOL CALL] {self.name}({args}) -> {status} "
            f"({self.duration_ms}ms) round={self.round_index}"
        )


@dataclass
class ChatResult:
    """一次用户提问的完整结果。"""

    reply: str
    tool_events: list[ToolEvent] = field(default_factory=list)
    rounds: int = 0
    stopped_reason: str = "completed"
    messages: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "reply": self.reply,
            "toolCalls": [event.to_dict() for event in self.tool_events],
            "rounds": self.rounds,
            "stoppedReason": self.stopped_reason,
        }


class BookstoreAssistant:
    """把模型、工具、对话历史串成一次问答。"""

    def __init__(
        self,
        client: ChatClient,
        registry: ToolRegistry | None = None,
        settings: AgentSettings | None = None,
        system_prompt: str = SYSTEM_PROMPT,
        on_tool_call: Callable[[ToolEvent], None] | None = None,
    ) -> None:
        self._client = client
        self._registry = registry or build_registry()
        self._settings = settings or AGENT
        self._system_prompt = system_prompt
        self._on_tool_call = on_tool_call

    @property
    def tool_schemas(self) -> list[dict]:
        """交给大模型识别的 Tool 列表。"""
        return self._registry.schemas

    def chat(self, user_message: str, history: Iterable[dict] | None = None) -> ChatResult:
        messages: list[dict] = [{"role": "system", "content": self._system_prompt}]
        messages.extend(history or [])
        messages.append({"role": "user", "content": user_message})

        events: list[ToolEvent] = []
        consecutive_errors = 0
        stopped_reason = "completed"

        for round_index in range(1, self._settings.max_tool_rounds + 1):
            turn = self._client.complete(messages, self.tool_schemas)
            messages.append(turn.to_message())

            if not turn.wants_tools:
                return ChatResult(
                    reply=turn.content,
                    tool_events=events,
                    rounds=round_index,
                    stopped_reason=stopped_reason,
                    messages=messages,
                )

            for call in turn.tool_calls:
                event, tool_message = self._run_tool_call(call, round_index)
                events.append(event)
                messages.append(tool_message)

                # 交给调用方的事件回调（服务端用它带 requestId 记录日志）；
                # 没人订阅时才在这里兜底打印，避免同一行日志出现两次。
                if self._on_tool_call is not None:
                    self._on_tool_call(event)
                else:
                    logger.info(event.log_line())

                consecutive_errors = 0 if event.ok else consecutive_errors + 1

            if consecutive_errors >= self._settings.max_consecutive_tool_errors:
                stopped_reason = "tool_error_limit"
                logger.warning("连续 %d 次工具调用失败，中止循环", consecutive_errors)
                break

        else:
            stopped_reason = "max_rounds"

        # 走到这里说明循环被兜底终止：不再追问模型，直接给一句可解释的话。
        return ChatResult(
            reply=self._fallback_reply(events, stopped_reason),
            tool_events=events,
            rounds=self._settings.max_tool_rounds,
            stopped_reason=stopped_reason,
            messages=messages,
        )

    # -- 内部 ---------------------------------------------------------------

    def _run_tool_call(
        self, call: ToolCallRequest, round_index: int
    ) -> tuple[ToolEvent, dict]:
        """执行单次调用，并把结果包装成一条 tool 角色消息。"""
        arguments, parse_error = call.parse_arguments()

        if parse_error is not None:
            # 模型给的参数不是合法 JSON：不执行，直接把错误回传让它重新表述。
            payload = {
                "ok": False,
                "error": {
                    "code": "INVALID_JSON_ARGUMENTS",
                    "message": parse_error,
                    "retryable": True,
                    "hint": (
                        f"请重新调用 {call.name}，arguments 必须是 JSON 对象，"
                        '例如 {"isbn": "978-3-00-000000-4"}。'
                    ),
                },
            }
            logger.warning("[TOOL CALL] %s 参数解析失败：%s", call.name, parse_error)
            event = ToolEvent(
                round_index=round_index,
                name=call.name,
                arguments={},
                ok=False,
                payload=payload,
                duration_ms=0,
                parse_error=parse_error,
            )
            return event, {
                "role": "tool",
                "tool_call_id": call.id,
                "name": call.name,
                "content": json.dumps(payload, ensure_ascii=False),
            }

        outcome: ToolOutcome = self._registry.dispatch(call.name, arguments)
        event = ToolEvent(
            round_index=round_index,
            name=outcome.name,
            arguments=outcome.arguments,
            ok=outcome.ok,
            payload=outcome.payload,
            duration_ms=outcome.duration_ms,
        )
        return event, outcome.to_tool_message(call.id)

    @staticmethod
    def _fallback_reply(events: list[ToolEvent], stopped_reason: str) -> str:
        if stopped_reason == "max_rounds":
            return (
                "这个问题我查了几轮还没能给出准确结果，先不给你不确定的信息。"
                "麻烦确认一下 ISBN，或者稍后再试。"
            )
        failures = [
            f"{event.name}（{event.payload.get('error', {}).get('message', '未知错误')}）"
            for event in events
            if not event.ok
        ]
        detail = "；".join(failures[-2:]) if failures else "工具连续调用失败"
        return (
            f"抱歉，查询过程中连续出错，我没能拿到可靠数据，就不猜了。"
            f"出错的是：{detail}。请稍后重试。"
        )
