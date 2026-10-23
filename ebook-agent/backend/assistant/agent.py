"""ReAct 循环：用 Function Calling 下发动作，逐步记录 Thought / Action / Observation。

一次提问的执行过程：

1. 组装消息：System Prompt + 最近几轮对话 + 用户提问，同时把四个工具的 Schema
   放进 ``tools`` 字段；
2. 请求模型。模型每次返回两样东西：一段说明（Thought）和一组 ``tool_calls``（Action）；
3. 逐个执行 ``tool_calls``，拿到结果（Observation），再以 ``tool`` 消息回填上下文；
4. 回到第 2 步。模型不再要求调用工具时，它给出的自然语言就是最终答复。

这正是「Function Calling + ReAct」的结合点：动作由结构化的 Tool Call 表达，
循环本身仍是 ReAct 的「判断下一步 → 执行 → 读结果 → 再判断」。
两者都保留，是因为作业2 要求解析 Tool Call，作业3 要求展示 Thought -> Action -> Observation，
合并后它们跑在同一个循环里，而不是两条互不相干的链路。

三条刹车防止循环失控：最大轮次、连续失败上限、重复动作检测。
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Callable, Iterable

from ..config import AGENT as AGENT_SETTINGS
from ..config import AgentSettings
from ..guide.config import AGENT as GUIDE_AGENT_SETTINGS
from ..guide.react_format import truncate
from ..llm import ChatClient, ToolCallRequest
from .prompt import SYSTEM_PROMPT
from .tools import UnifiedRegistry, UnifiedToolOutcome

logger = logging.getLogger("ebook.assistant")

#: 回填与展示观测时的截断长度：政策条款原文可能很长，整段塞回上下文会挤掉别的内容。
OBSERVATION_MAX_CHARS = GUIDE_AGENT_SETTINGS.observation_max_chars


@dataclass
class AssistantStep:
    """一步执行记录：模型的理由、动作、参数与观测。"""

    index: int
    thought: str
    action: str
    arguments: dict
    ok: bool
    payload: dict | None
    observation: str
    duration_ms: int = 0
    parse_error: str = ""

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "thought": self.thought,
            "action": self.action,
            "arguments": self.arguments,
            "ok": self.ok,
            "durationMs": self.duration_ms,
            "observation": self.observation,
            "result": self.payload,
            "parseError": self.parse_error or None,
        }

    def log_trace(self) -> str:
        """完整打印一步链路，供运行日志与作业证据核对。"""
        status = "ok" if self.ok else f"failed:{((self.payload or {}).get('error') or {}).get('code')}"
        return (
            f"[REACT] step={self.index} action={self.action}"
            f"({json.dumps(self.arguments, ensure_ascii=False)}) -> {status}"
            f" ({self.duration_ms}ms)\n"
            f"Thought: {self.thought or '（模型未给出推理）'}\n"
            f"Action: {self.action}\n"
            f"Action Input: {json.dumps(self.arguments, ensure_ascii=False)}\n"
            f"Observation: {self.observation}"
        )


@dataclass
class AssistantResult:
    """一次用户提问的完整结果。"""

    question: str
    reply: str
    steps: list[AssistantStep] = field(default_factory=list)
    rounds: int = 0
    stopped_reason: str = "completed"

    @property
    def actions(self) -> list[str]:
        return [step.action for step in self.steps]

    def to_dict(self) -> dict:
        return {
            "question": self.question,
            "reply": self.reply,
            "rounds": self.rounds,
            "stoppedReason": self.stopped_reason,
            "steps": [step.to_dict() for step in self.steps],
        }


class UnifiedAssistant:
    """把模型、合并后的工具集与对话历史串成一次问答。"""

    def __init__(
        self,
        client: ChatClient,
        registry: UnifiedRegistry,
        settings: AgentSettings | None = None,
        system_prompt: str = SYSTEM_PROMPT,
        on_step: Callable[[AssistantStep], None] | None = None,
        on_event: Callable[[str, dict], None] | None = None,
    ) -> None:
        self._client = client
        self._registry = registry
        self._settings = settings or AGENT_SETTINGS
        self._system_prompt = system_prompt
        self._on_step = on_step
        self._on_event = on_event

    @property
    def tool_schemas(self) -> list[dict]:
        return self._registry.schemas

    @property
    def system_prompt(self) -> str:
        return self._system_prompt

    def chat(self, question: str, history: Iterable[dict] | None = None) -> AssistantResult:
        messages: list[dict] = [{"role": "system", "content": self._system_prompt}]
        messages.extend(self._clean_history(history))
        messages.append({"role": "user", "content": question})

        steps: list[AssistantStep] = []
        #: 已经成功执行过的「工具 + 参数」。失败的动作允许重试（作业2 的瞬时故障重试），
        #: 成功的动作再调一次才是模型卡住的信号。
        executed: dict[str, bool] = {}
        consecutive_errors = 0

        for round_index in range(1, self._settings.max_tool_rounds + 1):
            self._emit("thinking", {"round": round_index})
            turn = self._client.complete(messages, self._registry.schemas)
            messages.append(turn.to_message())

            if not turn.wants_tools:
                reply = (turn.content or "").strip() or self._empty_reply()
                return AssistantResult(
                    question=question,
                    reply=self._link_reply(reply, steps),
                    steps=steps,
                    rounds=round_index,
                    stopped_reason="completed",
                )

            # 模型在要求调用工具的同时给出的说明就是这一步的 Thought。
            thought = (turn.content or "").strip()

            for call in turn.tool_calls:
                arguments, parse_error = call.parse_arguments()
                self._emit("step_started", {
                    "index": len(steps) + 1, "thought": thought,
                    "action": call.name, "arguments": arguments or {},
                    "status": "running", "parseError": parse_error,
                })
                step = self._run_tool_call(call, thought, len(steps) + 1, executed)
                steps.append(step)
                messages.append(self._tool_message(call, step))

                if self._on_step is not None:
                    self._on_step(step)
                else:
                    logger.info(step.log_trace())
                self._emit("step_completed", {**step.to_dict(), "status": "completed"})

                consecutive_errors = 0 if step.ok else consecutive_errors + 1

            if consecutive_errors >= self._settings.max_consecutive_tool_errors:
                logger.warning("连续 %d 次工具调用失败，中止循环", consecutive_errors)
                return AssistantResult(
                    question=question,
                    reply=self._fallback_reply(steps, "tool_error_limit"),
                    steps=steps,
                    rounds=round_index,
                    stopped_reason="tool_error_limit",
                )

        logger.warning("达到最大轮次 %d，中止循环", self._settings.max_tool_rounds)
        return AssistantResult(
            question=question,
            reply=self._fallback_reply(steps, "max_rounds"),
            steps=steps,
            rounds=self._settings.max_tool_rounds,
            stopped_reason="max_rounds",
        )

    # -- 单步执行 -----------------------------------------------------------

    def _emit(self, event: str, payload: dict) -> None:
        """把模型等待、工具开始和真实结果交给实时订阅方，原有同步调用保持兼容。"""
        if self._on_event is not None:
            self._on_event(event, payload)

    def _run_tool_call(
        self,
        call: ToolCallRequest,
        thought: str,
        index: int,
        executed: dict[str, bool],
    ) -> AssistantStep:
        arguments, parse_error = call.parse_arguments()

        if parse_error is not None:
            # 参数不是合法 JSON：不执行，把错误回传让模型重新表述。
            payload = self._error_payload(
                "INVALID_JSON_ARGUMENTS",
                parse_error,
                retryable=True,
                hint=(
                    f"请重新调用 {call.name}，arguments 必须是 JSON 对象，"
                    '例如 {"isbn": "978-3-00-000000-4"}。'
                ),
            )
            return self._step(call.name, {}, thought, index, False, payload, 0, parse_error)

        key = f"{call.name}:{json.dumps(arguments, ensure_ascii=False, sort_keys=True)}"
        if executed.get(key) is True:
            # 同样的动作 + 同样的参数在已经成功的前提下再来一次，说明模型卡住了。
            # 上一轮失败则允许重试：瞬时故障重试是作业2 要求的能力。
            payload = self._error_payload(
                "REPEATED_ACTION",
                f"{call.name} 已经用同样的参数成功执行过",
                retryable=False,
                hint="不要重复调用已经成功的动作；请换参数、换工具，或用已有结果直接回答。",
            )
            return self._step(call.name, arguments, thought, index, False, payload, 0)

        started = time.perf_counter()
        outcome: UnifiedToolOutcome = self._registry.dispatch(call.name, arguments)
        duration_ms = int((time.perf_counter() - started) * 1000)
        executed[key] = outcome.ok
        return self._step(
            outcome.name, outcome.arguments, thought, index, outcome.ok,
            outcome.payload, duration_ms,
        )

    def _step(
        self,
        action: str,
        arguments: dict,
        thought: str,
        index: int,
        ok: bool,
        payload: dict,
        duration_ms: int,
        parse_error: str = "",
    ) -> AssistantStep:
        return AssistantStep(
            index=index,
            thought=thought,
            action=action,
            arguments=arguments,
            ok=ok,
            payload=payload,
            observation=truncate(json.dumps(payload, ensure_ascii=False), OBSERVATION_MAX_CHARS),
            duration_ms=duration_ms,
            parse_error=parse_error,
        )

    @staticmethod
    def _tool_message(call: ToolCallRequest, step: AssistantStep) -> dict:
        # 回填给模型的是完整结果；截断只用于日志与界面展示，
        # 否则长政策条款会被切成半段 JSON，模型读不回来。
        content = json.dumps(step.payload, ensure_ascii=False) if step.payload else "{}"
        return {
            "role": "tool",
            "tool_call_id": call.id,
            "name": step.action,
            "content": content,
        }

    # -- 回复中的图书链接 ---------------------------------------------------

    @staticmethod
    def _link_reply(reply: str, steps: list[AssistantStep]) -> str:
        """把回复里的书名换成工具给出的详情页链接。

        模型偶尔会自己编造域名（例如 ``example.com``）或只写书名，所以在服务端
        按工具结果做一次兜底：已有 Markdown 链接的改成正确地址，裸书名补上链接。
        只使用工具返回的 ``/books/<id>``，不从前端或用户输入拼 URL。
        """
        links: dict[str, str] = {}
        for step in steps:
            payload = step.payload or {}
            if step.action == "search_book_catalog":
                candidates = payload.get("results") or []
            elif step.action == "check_inventory":
                candidates = [payload]
            else:
                candidates = []
            for book in candidates:
                title = book.get("title")
                url = book.get("detailUrl")
                if isinstance(title, str) and title.strip() and isinstance(url, str) \
                        and url.startswith("/books/"):
                    links[title.strip()] = url

        if not links:
            return reply

        def replace_link(match: re.Match) -> str:
            label, target = match.group(1), match.group(2)
            for title, url in links.items():
                if title in label:
                    return f"[{label}]({url})"
            return match.group(0)

        text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", replace_link, reply)
        # 跳过已经成形的 Markdown 链接，只给剩下的裸书名补链接。
        parts = re.split(r"(\[[^\]]+\]\([^)]+\))", text)
        for index, part in enumerate(parts):
            if re.fullmatch(r"\[[^\]]+\]\([^)]+\)", part):
                continue
            for title, url in sorted(links.items(), key=lambda item: len(item[0]), reverse=True):
                token = f"《{title}》"
                if token in part:
                    part = part.replace(token, f"[{token}]({url})")
            parts[index] = part
        return "".join(parts)

    # -- 兜底 ---------------------------------------------------------------

    @staticmethod
    def _clean_history(history: Iterable[dict] | None) -> list[dict]:
        """只接受普通的 user / assistant 文本消息，历史里不允许夹带系统提示词。"""
        cleaned: list[dict] = []
        for entry in list(history or [])[-12:]:
            role = entry.get("role")
            content = entry.get("content")
            if role in {"user", "assistant"} and isinstance(content, str) and content.strip():
                cleaned.append({"role": role, "content": content})
        return cleaned

    @staticmethod
    def _error_payload(code: str, message: str, *, retryable: bool, hint: str) -> dict:
        return {
            "ok": False,
            "error": {
                "code": code,
                "message": message,
                "retryable": retryable,
                "hint": hint,
            },
        }

    @staticmethod
    def _empty_reply() -> str:
        return "这个问题我暂时没有查到可用的结果，可以换个说法再问一次。"

    @staticmethod
    def _fallback_reply(steps: list[AssistantStep], stopped_reason: str) -> str:
        if stopped_reason == "max_rounds":
            return (
                "这个问题我查了几轮还没能给出准确结果，先不给你不确定的信息。"
                "麻烦把问题说得再具体一点，或者稍后再试。"
            )
        failures = [
            f"{step.action}（{((step.payload or {}).get('error') or {}).get('message', '未知错误')}）"
            for step in steps
            if not step.ok
        ]
        detail = "；".join(failures[-2:]) if failures else "工具连续调用失败"
        return (
            "抱歉，查询过程中连续出错，我没能拿到可靠数据，就不猜了。"
            f"出错的是：{detail}。请稍后重试。"
        )
