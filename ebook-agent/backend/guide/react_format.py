"""ReAct 文本协议的解析与格式化。

ReAct（Reason + Act）用纯文本约定来回：模型输出 ``Thought`` 说明推理，
再输出 ``Action`` 与 ``Action Input`` 提出要执行的动作；执行方把结果以
``Observation`` 追加回上下文，模型继续下一轮，直到输出 ``Final Answer``。

本模块只负责「协议」这一层：

- ``parse_decision``：从模型输出里解析出这一次想干什么（含中英文冒号、Markdown 粗体等容错）；
- ``parse_action_input``：解析 Action Input 的 JSON（模型经常给出非严格 JSON，
  解析失败要能给出可回填给模型的错误，而不是让循环崩掉）；
- ``format_step`` / ``iter_steps``：拼装与回读上下文里的步骤记录；
- ``extract_observation``：从记录里取回上一次的工具结果。

把协议单独拆出来，是因为它同时被 agent（拼上下文、解析决策）和离线替身模型
（读回观测、推断下一步）使用；放在 agent 里会造成循环导入。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

def _marker_pattern(names: str) -> re.Pattern:
    """一行一个标记的模式。

    容错范围来自真实模型的输出习惯：加粗（``**Thought**：``）、中文冒号、
    列表符号（``- Action:``）、标题符号（``## Thought:``）。
    ``Action Input`` 必须排在 ``Action`` 之后匹配，否则
    ``Action Input: {...}`` 会被当成一个叫 "Input: {...}" 的动作。
    """
    return re.compile(
        r"^[\s>*_#\-]*(?:" + names + r")[\s*_]*[:：]\s*(.*)$",
        re.IGNORECASE,
    )


#: 模型可能写成 ``Thought:`` / ``**Thought**:`` / ``思考：``，都要认。
_LINE_PATTERNS = {
    "thought": _marker_pattern("Thought|思考"),
    "action": _marker_pattern("Action|行动|动作"),
    "action_input": _marker_pattern(r"Action\s*Input|行动输入|动作输入"),
    "final_answer": _marker_pattern(r"Final\s*Answer|最终答案|最终回答"),
}

#: Action Input 后面可能跟着代码块围栏，解析前先撕掉。
FENCE_PATTERN = re.compile(r"^```[a-zA-Z]*\s*|\s*```$")

#: 工具名允许的字符集：模型偶尔会写出 `search_book_catalog(query="x")` 这种调用形式。
ACTION_NAME_PATTERN = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*(?:\((.*)\))?\s*$", re.DOTALL)


@dataclass
class Decision:
    """模型一次输出解析后的结果。"""

    thought: str = ""
    action: str = ""
    action_input_raw: str = ""
    final_answer: str = ""
    error: str = ""

    @property
    def is_final(self) -> bool:
        return bool(self.final_answer.strip())

    @property
    def has_action(self) -> bool:
        return bool(self.action.strip())


@dataclass
class Step:
    """上下文里的一条步骤记录。"""

    index: int
    thought: str
    action: str
    action_input_raw: str
    observation_raw: str

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "thought": self.thought,
            "action": self.action,
            "actionInput": self.action_input_raw,
            "observation": self.observation_raw,
        }


def _strip_fence(text: str) -> str:
    return FENCE_PATTERN.sub("", text.strip()).strip()


def parse_decision(text: str) -> Decision:
    """解析模型的一次输出。

    逐行扫描而不是整体匹配：模型经常在 ``Final Answer`` 前面写注释、
    或者在 JSON 里换行，用行首匹配才能既容错又稳定。
    """
    decision = Decision()
    thought_lines: list[str] = []
    answer_lines: list[str] = []
    mode = "thought"

    for raw_line in (text or "").splitlines():
        line = raw_line.rstrip()
        matched = False
        for key, pattern in _LINE_PATTERNS.items():
            found = pattern.match(line)
            if not found:
                continue
            value = found.group(1).strip()
            matched = True
            if key == "thought":
                mode = "thought"
                thought_lines.append(value)
            elif key == "action":
                mode = "action"
                decision.action = value
            elif key == "action_input":
                mode = "action_input"
                decision.action_input_raw = value
            else:
                mode = "answer"
                answer_lines.append(value)
            break
        if matched:
            continue
        # 续行：属于上一个小节的正文（多行 JSON、多段最终回答）。
        if mode == "thought" and line.strip():
            thought_lines.append(line.strip())
        elif mode == "answer":
            answer_lines.append(line)
        elif mode == "action_input" and line.strip():
            decision.action_input_raw += "\n" + line.strip()
        elif mode == "action" and line.strip():
            decision.action += " " + line.strip()

    decision.thought = "\n".join(part for part in thought_lines if part).strip()
    decision.final_answer = "\n".join(answer_lines).strip()
    decision.action_input_raw = _strip_fence(decision.action_input_raw)

    # 模型写成 `search_book_catalog(query="微服务")` 时，把函数名与实参拆开。
    if decision.action and not decision.action_input_raw:
        call = ACTION_NAME_PATTERN.match(decision.action)
        if call and call.group(2):
            decision.action = call.group(1)
            decision.action_input_raw = call.group(2).strip()

    if not decision.is_final and not decision.has_action:
        decision.error = (
            "输出里既没有 Action 也没有 Final Answer。"
            "请严格按格式输出：Thought 一行，随后 Action 与 Action Input，"
            "或者在信息足够时输出 Final Answer。"
        )
    return decision


def parse_action_input(raw: str) -> tuple[dict | None, str]:
    """解析 Action Input。

    返回 ``(参数, 错误说明)``，永不抛异常 —— 解析失败的错误是要回填给模型让它改的，
    不是给调用方崩的。
    """
    text = (raw or "").strip()
    if not text:
        return {}, ""
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as error:
        # 常见的单引号 JSON：'{'query': '微服务'}'，尽力修一次再报错。
        repaired = _repair_single_quotes(text)
        if repaired is not None:
            return repaired, ""
        return None, (
            f"Action Input 不是合法 JSON：{error.msg}。"
            '正确写法形如 {"query": "微服务"}，键与字符串都用双引号。'
        )
    if not isinstance(parsed, dict):
        return None, (
            f"Action Input 必须是 JSON 对象，收到 {type(parsed).__name__}。"
            '例如 {"query": "微服务"}。'
        )
    return parsed, ""


def _repair_single_quotes(text: str) -> dict | None:
    if "'" not in text or '"' in text:
        return None
    try:
        parsed = json.loads(text.replace("'", '"'))
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def format_action(action: str, arguments: dict) -> str:
    return f"Action: {action}\nAction Input: {json.dumps(arguments, ensure_ascii=False)}"


def format_step(
    thought: str,
    action: str,
    arguments: dict,
    observation: str,
) -> str:
    """拼装一条完整的 Thought → Action → Observation 记录。"""
    return "\n".join(
        [
            f"Thought: {thought}" if thought else "Thought:（模型未给出推理）",
            format_action(action, arguments),
            f"Observation: {observation}",
        ]
    )


def iter_steps(scratchpad: str) -> list[Step]:
    """回读上下文里的步骤记录。

    以 ``Thought`` 为一条记录的开头：每见到一个新的 ``Thought`` 就收尾上一条,
    否则多条记录会糊成一条 —— 观测与动作对不上，离线模型据此判断「这一步做没做过」
    就会全部判断错，表现为把同一个动作反复重发。
    """
    steps: list[Step] = []
    thought = ""
    action = ""
    action_input = ""
    observation: list[str] = []
    mode = ""

    def flush() -> None:
        nonlocal thought, action, action_input, observation
        if action or observation:
            steps.append(
                Step(
                    index=len(steps) + 1,
                    thought=thought,
                    action=action,
                    action_input_raw=action_input,
                    observation_raw="\n".join(observation).strip(),
                )
            )
        thought, action, action_input, observation = "", "", "", []

    for raw_line in (scratchpad or "").splitlines():
        if raw_line.startswith("Observation:"):
            mode = "observation"
            observation.append(raw_line[len("Observation:") :].strip())
            continue

        matched = False
        for key, pattern in _LINE_PATTERNS.items():
            if key == "final_answer":
                continue
            found = pattern.match(raw_line)
            if not found:
                continue
            matched = True
            value = found.group(1).strip()
            if key == "thought":
                flush()  # 新的 Thought 就是新的一条记录
                mode = "thought"
                thought = value
            elif key == "action":
                if action:
                    # 同一条记录里出现第二个 Action：只可能是上一条缺了 Thought。
                    flush()
                mode = "action"
                action = value
            else:
                mode = "action_input"
                action_input = value
            break
        if matched:
            continue
        if mode == "observation":
            observation.append(raw_line)
    flush()
    return steps


#: 观测被截断时的兜底解析：截断的 JSON 解不出来，但状态字段通常还在前面。
OK_FIELD_PATTERN = re.compile(r'"ok"\s*:\s*(true|false)')
ERROR_CODE_PATTERN = re.compile(r'"code"\s*:\s*"([A-Z_]+)"')
ERROR_MESSAGE_PATTERN = re.compile(r'"message"\s*:\s*"([^"]{0,200})"')


def extract_observation(step: Step) -> tuple[bool | None, dict | None]:
    """从一条步骤里取回工具结果。

    返回 ``(ok, payload)``。观测被截断时完整 JSON 解析会失败，
    此时退一步用正则捞出 ``ok`` 与错误码 —— 否则离线模型会把自己成功的调用
    当成失败，进而反复重试同一个动作。
    """
    raw = step.observation_raw.strip()
    if not raw:
        return None, None

    payload = _decode_object_prefix(raw)
    if payload is None:
        matched = OK_FIELD_PATTERN.search(raw)
        if not matched:
            return None, None
        ok = matched.group(1) == "true"
        code = ERROR_CODE_PATTERN.search(raw)
        message = ERROR_MESSAGE_PATTERN.search(raw)
        payload = {
            "ok": ok,
            "truncated": True,
            "error": {"code": code.group(1) if code else "", "message": message.group(1) if message else ""},
        }
        return ok, payload

    return bool(payload.get("ok")), payload


def _decode_object_prefix(raw: str) -> dict | None:
    """解析以 JSON 对象开头、后面可能还挂着别的内容的观测。

    观测后面跟着提示词里那句「请输出下一步」是常态（它紧跟在执行记录之后），
    直接 ``json.loads`` 会因为多出这段文字而失败 —— 于是工具明明成功了，
    模型却把结果当成失败，转而反复重试。这里改用增量解析：
    只吃掉第一个完整的 JSON 对象，后面的文字不影响结果。
    """
    start = raw.find("{")
    if start < 0:
        return None
    try:
        payload, _ = json.JSONDecoder().raw_decode(raw[start:])
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def truncate(text: str, limit: int) -> str:
    """截断过长的观测，并在末尾标注被截断，避免模型把截断当成完整结果。"""
    if limit <= 0 or len(text) <= limit:
        return text
    return text[:limit].rstrip() + f"\n…（观测已截断，原长 {len(text)} 字符）"
