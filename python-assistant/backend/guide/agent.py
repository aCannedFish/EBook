"""ReAct（Reason + Act）循环。

一次提问的执行过程：

1. 组装提示词：System Prompt（角色 + 工具说明书 + 输出格式）+ 用户提问 + 执行记录；
2. 让模型输出下一步：先 ``Thought`` 讲清为什么这么做，再给出 ``Action`` 与 ``Action Input``；
   生成时带 ``stop=["\\nObservation:"]``，模型不可能自己编造观测结果；
3. 解析输出：解析失败就把「格式错误 + 正确写法」当作观测回填，让模型重写一遍；
4. 执行动作：``ToolRegistry.dispatch`` 要么返回结果、要么返回结构化错误（不抛异常）；
5. 把 ``Observation`` 追加进执行记录，回到第 2 步；
6. 模型输出 ``Final Answer`` 时结束，它就是给用户的答复。

三条刹车：最大步数、连续失败上限、重复动作检测。没有它们，
模型一旦陷入「同样的动作反复调用」就会把请求挂死在这里。

循环本身不关心工具怎么实现、模型是远程还是离线替身 —— 它只认 ReAct 文本协议。
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Callable

from .config import AGENT, AgentSettings
from .llm import ChatClient, EMPTY_SCRATCHPAD, SCRATCHPAD_MARKER
from .react_format import (
    Decision,
    format_step,
    parse_action_input,
    parse_decision,
    truncate,
)
from .tools import ToolOutcome, ToolRegistry, build_registry, describe_tools

logger = logging.getLogger("ebook.guide")

#: 生成到观测之前就停下：观测必须来自真实执行，不能由模型续写。
STOP_SEQUENCES = ("\nObservation:", "Observation:")

REACT_SYSTEM_PROMPT = """你是「E-BookStore 电子书城」的导购助手。你可以调用工具查书目、查政策库，
然后根据工具返回的结果回答顾客。你的输出必须严格遵循 ReAct 格式。

【可用工具】
{tools}

【输出格式】每一步只做一件事，严格按下面三行输出，不要输出别的格式：

Thought: 你的推理，说明为什么现在要做这个动作
Action: 工具名（必须是上面列出的工具之一）
Action Input: 工具参数的 JSON 对象，例如 {{"query": "微服务"}}

工具执行结果会以 Observation 的形式出现在执行记录里，你**不要自己写 Observation**。
当你认为信息已经足够回答用户时，改用下面的格式结束：

Thought: 说明为什么现在可以回答了
Final Answer: 给顾客的答复（中文，先结论后细节）

【必须遵守】
1. 关于书目、价格、库存、退换货与会员政策的任何结论，都必须来自 Observation。
   没有查到的信息不要猜；工具报错时读 error.hint 决定是换个参数重试还是如实告知。
2. 一次只能输出一个 Action。用户同时问了多件事时，按顺序一个个来。
3. 政策回答必须写明条款号（例如「第二章 第六条【塑封与拆封规则】」）并引用条款原文，
   不得把常识或电商惯例当成本店政策。
4. 检索不到时不要硬答。retryable 为 true 可以换一个更宽的关键词重试一次；
   仍然查不到就如实说明「政策库没有覆盖」，并建议联系在线客服。
5. 找书时如果用户给了预算、要求现货，就用 max_price、in_stock_only 传进参数。
6. 答复用中文，直接给结论，不要把 JSON、工具名这些实现细节说给顾客听。
   自然连贯地表达，避免频繁使用粗体、分隔线或长标题。
7. 仅提供查书和政策查询，不能代为下单、操作购物车或安排补货提醒，也不要承诺这些操作。
   书目中的售价不等于政策中的定价，信息不足时不能断言某本书符合定价限制。"""


@dataclass
class ReActStep:
    """一步 ReAct 记录：思考、动作、观测。"""

    index: int
    thought: str
    action: str
    arguments: dict
    ok: bool
    payload: dict | None
    observation: str
    duration_ms: int = 0
    parse_error: str = ""

    @property
    def action_input_raw(self) -> str:
        return json.dumps(self.arguments, ensure_ascii=False)

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

    def log_line(self) -> str:
        status = (
            "ok"
            if self.ok
            else f"failed:{((self.payload or {}).get('error') or {}).get('code')}"
        )
        return (
            f"[REACT] step={self.index} action={self.action}({self.action_input_raw}) "
            f"-> {status} ({self.duration_ms}ms)"
        )

    def log_trace(self) -> str:
        """记录完整决策与实际工具观测，供作业日志核对执行链路。"""
        return (
            f"{self.log_line()}\n"
            f"Thought: {self.thought}\n"
            f"Action: {self.action}\n"
            f"Action Input: {self.action_input_raw}\n"
            f"Observation: {self.observation}"
        )


@dataclass
class AgentResult:
    """一次提问的完整结果。"""

    question: str
    reply: str
    steps: list[ReActStep] = field(default_factory=list)
    rounds: int = 0
    stopped_reason: str = "completed"
    scratchpad: str = ""

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


class ReActAgent:
    """把模型、工具与 ReAct 协议串成一次问答。"""

    def __init__(
        self,
        client: ChatClient,
        registry: ToolRegistry | None = None,
        settings: AgentSettings | None = None,
        system_prompt: str | None = None,
        on_step: Callable[[ReActStep], None] | None = None,
    ) -> None:
        self._client = client
        self._registry = registry or build_registry()
        self._settings = settings or AGENT
        self._system_prompt = (system_prompt or REACT_SYSTEM_PROMPT).format(
            tools=describe_tools(self._registry.schemas)
        )
        self._on_step = on_step

    @property
    def system_prompt(self) -> str:
        """给文档与调试用的完整 System Prompt。"""
        return self._system_prompt

    def run(self, question: str) -> AgentResult:
        scratchpad = ""
        steps: list[ReActStep] = []
        consecutive_errors = 0
        stopped_reason = "completed"

        for index in range(1, self._settings.max_steps + 1):
            output = self._client.generate(
                self._messages(question, scratchpad), stop=STOP_SEQUENCES
            )
            decision = parse_decision(output)

            if decision.is_final:
                reply = decision.final_answer.strip()
                if decision.thought:
                    # 收尾的思考也记进日志，方便看模型是凭什么判定「够了」。
                    logger.info(
                        "[REACT] step=%d final: %s",
                        index,
                        decision.thought.splitlines()[0],
                    )
                return AgentResult(
                    question=question,
                    reply=reply,
                    steps=steps,
                    rounds=index,
                    stopped_reason="completed",
                    scratchpad=scratchpad,
                )

            step, observation = self._execute(decision, output, index, steps)
            steps.append(step)
            # 没解析出 Thought 时，把模型原样输出的内容留在记录里，它下一轮才看得到自己写错了什么；
            # 格式没错、只是没写 Thought 的情况，就老老实实标注「未给出推理」。
            thought = decision.thought or (output.strip() if decision.error else "")
            scratchpad = f"{scratchpad}\n\n{format_step(thought, step.action, step.arguments, observation)}".strip()

            if self._on_step is not None:
                self._on_step(step)
            else:
                logger.info(step.log_trace())

            consecutive_errors = 0 if step.ok else consecutive_errors + 1
            if consecutive_errors >= self._settings.max_consecutive_errors:
                stopped_reason = "error_limit"
                logger.warning("连续 %d 步失败，中止 ReAct 循环", consecutive_errors)
                break
        else:
            stopped_reason = "max_steps"

        return AgentResult(
            question=question,
            reply=self._fallback_reply(steps, stopped_reason),
            steps=steps,
            rounds=len(steps),
            stopped_reason=stopped_reason,
            scratchpad=scratchpad,
        )

    # -- 内部 ---------------------------------------------------------------

    def _messages(self, question: str, scratchpad: str) -> list[dict]:
        """System + User（提问与执行记录放在同一条 user 消息里）。

        执行记录刻意放在 user 侧：ReAct 的上下文是「模型每轮重新读一遍全部记录」，
        而观测内容是工具产出的数据，不是模型的输出，放在 user 侧更贴近它真实的来源。
        """
        content = (
            f"用户提问：{question}\n\n"
            f"{SCRATCHPAD_MARKER}\n{scratchpad or EMPTY_SCRATCHPAD}\n\n"
            "请输出下一步。"
        )
        return [
            {"role": "system", "content": self._system_prompt},
            {"role": "user", "content": content},
        ]

    def _execute(
        self,
        decision: Decision,
        output: str,
        index: int,
        previous: list[ReActStep],
    ) -> tuple[ReActStep, str]:
        """执行一步动作，返回步骤记录与要回填的观测文本。"""
        if decision.error:
            payload = self._error_payload(
                "REACT_FORMAT_ERROR",
                decision.error,
                retryable=True,
                hint=(
                    "请重新输出，格式为「Thought: …」换行「Action: 工具名」换行"
                    '「Action Input: {"参数": "值"}」；信息足够时用「Final Answer: …」结束。'
                ),
            )
            observation = truncate(
                json.dumps(payload, ensure_ascii=False),
                self._settings.observation_max_chars,
            )
            return (
                ReActStep(
                    index=index,
                    thought=decision.thought,
                    action="(未解析)",
                    arguments={},
                    ok=False,
                    payload=payload,
                    observation=observation,
                    parse_error=decision.error,
                ),
                observation,
            )

        arguments, parse_error = parse_action_input(decision.action_input_raw)
        if parse_error:
            payload = self._error_payload(
                "INVALID_JSON_ARGUMENTS",
                parse_error,
                retryable=True,
                hint=(
                    f"请重新调用 {decision.action}，Action Input 必须是合法 JSON 对象，"
                    '例如 {"query": "微服务"}。'
                ),
            )
            observation = truncate(
                json.dumps(payload, ensure_ascii=False),
                self._settings.observation_max_chars,
            )
            return (
                ReActStep(
                    index=index,
                    thought=decision.thought,
                    action=decision.action,
                    arguments={},
                    ok=False,
                    payload=payload,
                    observation=observation,
                    parse_error=parse_error,
                ),
                observation,
            )

        # 重复动作检测：同一动作 + 同一参数再来一次，说明模型卡住了。
        repeated = any(
            step.action == decision.action and step.arguments == arguments
            for step in previous
        )
        if repeated:
            payload = self._error_payload(
                "REPEATED_ACTION",
                f"动作 {decision.action} 已经用同样的参数执行过",
                retryable=False,
                hint=(
                    "不要重复调用同样的动作。请换一个参数或换一个工具，"
                    "或者用已有观测直接给出 Final Answer。"
                ),
            )
            observation = truncate(
                json.dumps(payload, ensure_ascii=False),
                self._settings.observation_max_chars,
            )
            return (
                ReActStep(
                    index=index,
                    thought=decision.thought,
                    action=decision.action,
                    arguments=arguments,
                    ok=False,
                    payload=payload,
                    observation=observation,
                ),
                observation,
            )

        started = time.perf_counter()
        outcome: ToolOutcome = self._registry.dispatch(decision.action, arguments)
        duration_ms = int((time.perf_counter() - started) * 1000)
        observation = truncate(
            json.dumps(outcome.payload, ensure_ascii=False),
            self._settings.observation_max_chars,
        )
        return (
            ReActStep(
                index=index,
                thought=decision.thought,
                action=outcome.name,
                arguments=outcome.arguments,
                ok=outcome.ok,
                payload=outcome.payload,
                observation=observation,
                duration_ms=duration_ms,
            ),
            observation,
        )

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
    def _fallback_reply(steps: list[ReActStep], stopped_reason: str) -> str:
        if stopped_reason == "max_steps":
            return (
                "这个问题我查了几轮还是没能拿到确定的结果，先不给你不确定的信息。"
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
            f"出错的是：{detail}。请稍后重试，或直接联系在线客服。"
        )
