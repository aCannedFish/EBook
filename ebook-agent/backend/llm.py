"""大模型客户端。

三层结构：

- ``AssistantTurn`` / ``ToolCallRequest``：把不同供应商的响应归一化成同一份结构，
  循环层因此不需要知道底层是 OpenAI、DeepSeek 还是别的兼容接口。
- ``OpenAICompatibleClient``：走 openai SDK；装不上时自动退回到只用标准库的
  ``HttpChatClient``，两者的请求体完全一致。
- ``LocalRuleBasedLLM``：不联网的替身模型。没有 API Key 时用它跑通整条
  「模型 → 工具 → 模型」链路，单元测试也依赖它，从而让循环逻辑与网络解耦。
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Protocol

from .config import LLM, LLMSettings


# ---------------------------------------------------------------------------
# 归一化的响应结构
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ToolCallRequest:
    """模型发出的一次函数调用请求。"""

    id: str
    name: str
    arguments_raw: str

    def parse_arguments(self) -> tuple[dict | None, str | None]:
        """解析参数。

        模型给出的 arguments 是**字符串**，且不保证是合法 JSON（长参数被截断、
        中英文引号混用都很常见）。所以这里永远返回二元组而不抛异常，
        由调用方决定是回传错误让模型重来，还是直接失败。
        """
        try:
            parsed = json.loads(self.arguments_raw or "{}")
        except json.JSONDecodeError as error:
            return None, f"参数不是合法 JSON：{error.msg}（原文：{self.arguments_raw!r}）"
        if not isinstance(parsed, dict):
            return None, f"参数必须是 JSON 对象，收到 {type(parsed).__name__}"
        return parsed, None


@dataclass
class AssistantTurn:
    """模型的一次回复：要么是自然语言，要么是若干函数调用，要么两者都有。"""

    content: str = ""
    tool_calls: tuple[ToolCallRequest, ...] = ()
    finish_reason: str = ""

    @property
    def wants_tools(self) -> bool:
        return bool(self.tool_calls)

    def to_message(self) -> dict:
        """转回 OpenAI 消息格式，用于追加到对话上下文。"""
        message: dict[str, Any] = {"role": "assistant", "content": self.content or None}
        if self.tool_calls:
            message["tool_calls"] = [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {"name": call.name, "arguments": call.arguments_raw},
                }
                for call in self.tool_calls
            ]
        return message


class ChatClient(Protocol):
    """模型客户端协议。"""

    def complete(self, messages: list[dict], tools: list[dict]) -> AssistantTurn:
        ...


class ModelAPIError(RuntimeError):
    """模型接口调用失败。

    message 是给使用者看的现象，hint 是给配置者看的排查方向。
    两者分开，是因为 404 / 401 这类错误的原始信息（`{'detail': 'Not Found'}`）
    指向不了任何具体配置项，直接抛给用户等于没提示。
    """

    def __init__(self, message: str, hint: str) -> None:
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
            "它应该填到 /v1 为止（如 https://api.deepseek.com/v1），"
            "不要再带 /chat/completions；也确认 LLM_MODEL 在服务商的模型列表里。"
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


def _normalize_response(message: dict, finish_reason: str) -> AssistantTurn:
    calls = []
    for raw in message.get("tool_calls") or []:
        function = raw.get("function") or {}
        calls.append(
            ToolCallRequest(
                id=str(raw.get("id") or f"call_{len(calls)}"),
                name=str(function.get("name") or ""),
                arguments_raw=str(function.get("arguments") or "{}"),
            )
        )
    return AssistantTurn(
        content=str(message.get("content") or ""),
        tool_calls=tuple(calls),
        finish_reason=finish_reason,
    )


class HttpChatClient:
    """只用标准库实现的 OpenAI 兼容客户端（兜底方案）。"""

    def __init__(self, settings: LLMSettings) -> None:
        self._settings = settings

    def complete(self, messages: list[dict], tools: list[dict]) -> AssistantTurn:
        body = {
            "model": self._settings.model,
            "messages": messages,
            "temperature": self._settings.temperature,
        }
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"

        request = urllib.request.Request(
            f"{self._settings.base_url.rstrip('/')}/chat/completions",
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._settings.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(
                request, timeout=self._settings.timeout_seconds
            ) as response:
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
        return _normalize_response(choice.get("message") or {}, choice.get("finish_reason") or "")


class OpenAICompatibleClient:
    """走 openai SDK 的客户端。

    SDK 内部已经处理了重试、超时与 base_url 拼接；这里只负责把响应归一化。
    如果环境里没有安装 openai，``build_client`` 会退回 HttpChatClient。
    """

    def __init__(self, settings: LLMSettings) -> None:
        from openai import OpenAI  # 延迟导入，便于无依赖环境退回标准库实现

        self._settings = settings
        self._client = OpenAI(
            base_url=settings.base_url,
            api_key=settings.api_key,
            timeout=settings.timeout_seconds,
        )

    def complete(self, messages: list[dict], tools: list[dict]) -> AssistantTurn:
        from openai import APIConnectionError, APIStatusError

        kwargs: dict[str, Any] = {
            "model": self._settings.model,
            "messages": messages,
            "temperature": self._settings.temperature,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

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

        choice = response.choices[0]
        return _normalize_response(
            choice.message.model_dump(exclude_none=True),
            choice.finish_reason or "",
        )


def build_client(settings: LLMSettings | None = None) -> ChatClient:
    """按配置构造客户端。未配置 API Key 时抛出，由调用方决定是否改用替身模型。"""
    settings = settings or LLM
    if not settings.configured:
        raise RuntimeError(
            "未配置 LLM_API_KEY。可以设置环境变量后重试，"
            "或用 LocalRuleBasedLLM 在离线模式下跑通整条链路。"
        )
    try:
        return OpenAICompatibleClient(settings)
    except ImportError:
        return HttpChatClient(settings)


# ---------------------------------------------------------------------------
# 离线替身模型
# ---------------------------------------------------------------------------

ISBN_LABEL_PATTERN = re.compile(r"ISBN\s*[为是:：]?\s*([0-9][0-9\-\s]{2,24})", re.IGNORECASE)
ISBN_PATTERN = re.compile(r"\d[\d\-\s]{7,20}\d")
#: 这些错误说明 ISBN 本身有问题，换一个函数再调用同一个 ISBN 也不会成功。
ISBN_LEVEL_ERRORS = frozenset({"INVALID_ISBN_FORMAT", "INVALID_ARGUMENT", "ISBN_NOT_FOUND"})
STOCK_KEYWORDS = ("库存", "还有", "多少本", "有货", "缺货", "本店", "剩")
PRICE_KEYWORDS = ("别家", "竞品", "比价", "其他平台", "他家", "多少钱", "价格", "报价")


@dataclass
class LocalRuleBasedLLM:
    """不联网的替身模型，用固定规则模拟一次真实的 Function Calling 决策。

    它做三件事，与真实模型在 Function Calling 中的行为一一对应：
    1. 从用户提问里判断该调用哪些函数、参数是什么；
    2. 读回工具结果，遇到 retryable 的错误就重试，遇到不可重试的错误就换策略；
    3. 信息够了就用自然语言总结。

    之所以要有它：没有 API Key 时也能完整演示「拦截模型输出 → 执行 → 回传 → 生成回答」，
    并且让 agent 的循环逻辑可以被单元测试覆盖，而不用把测试绑在网络和模型随机性上。
    """

    #: 记录已经重试过的调用，避免对同一个错误无限重试。
    retried: set[str] = field(default_factory=set)

    def complete(self, messages: list[dict], tools: list[dict]) -> AssistantTurn:
        question = self._last_user_question(messages)
        completed = self._completed_calls(messages)

        isbn = self._extract_isbn(question)
        if not isbn:
            return AssistantTurn(
                content="我需要 ISBN 才能查。请把书的 ISBN 发给我，10 位或 13 位都可以。"
            )

        wanted = ["check_inventory"]
        if any(word in question for word in PRICE_KEYWORDS):
            wanted.append("get_competitor_price")

        for name in wanted:
            outcome = completed.get(name)
            if outcome is None:
                return self._tool_call(name, isbn)
            if not outcome["ok"]:
                error = outcome["error"]
                key = f"{name}:{error['code']}"
                if error.get("retryable") and key not in self.retried:
                    self.retried.add(key)
                    # 瞬时故障：原样再试一次。
                    return self._tool_call(name, isbn)
                if error["code"] in ISBN_LEVEL_ERRORS:
                    # ISBN 本身不可用（位数不对、目录里没有），换函数再调一次也是白调。
                    break
                # 其他不可重试错误：放弃这个函数，继续能做的部分。
                continue

        return AssistantTurn(content=self._summarize(question, wanted, completed))

    # -- 内部工具 -----------------------------------------------------------

    @staticmethod
    def _last_user_question(messages: list[dict]) -> str:
        for message in reversed(messages):
            if message.get("role") == "user":
                return str(message.get("content") or "")
        return ""

    @staticmethod
    def _extract_isbn(question: str) -> str:
        # 先认清「ISBN为…」这种带标签的写法，它能捞到 12345 这类明显不合法但用户确实给了的值；
        # 拿不到再退回「一串足够长的数字」这个宽松规则。
        labeled = ISBN_LABEL_PATTERN.search(question)
        if labeled:
            return labeled.group(1).strip(" -")
        match = ISBN_PATTERN.search(question)
        return match.group(0).strip() if match else ""

    @staticmethod
    def _completed_calls(messages: list[dict]) -> dict[str, dict]:
        """把 tool 角色的消息按函数名归拢，供决策使用。"""
        results: dict[str, dict] = {}
        for message in messages:
            if message.get("role") != "tool":
                continue
            try:
                payload = json.loads(message.get("content") or "{}")
            except json.JSONDecodeError:
                continue
            name = message.get("name") or ""
            if name:
                results[name] = payload
        return results

    @staticmethod
    def _tool_call(name: str, isbn: str) -> AssistantTurn:
        return AssistantTurn(
            tool_calls=(
                ToolCallRequest(
                    id=f"call_{name}",
                    name=name,
                    arguments_raw=json.dumps({"isbn": isbn}, ensure_ascii=False),
                ),
            ),
            finish_reason="tool_calls",
        )

    def _summarize(self, question: str, wanted: list[str], completed: dict[str, dict]) -> str:
        stock = completed.get("check_inventory")
        competitor = completed.get("get_competitor_price")
        lines: list[str] = []

        if stock and stock.get("ok"):
            lines.append(
                f"《{stock['title']}》（{stock['author']}，ISBN {stock['isbn']}）"
                f"本店当前库存 {stock['stockQty']} 本，状态「{stock['stockText']}」，"
                f"售价 {stock['price']} 元。"
            )
            if stock["stockQty"] <= 5:
                lines.append("库存偏紧，要买的话建议尽快下单。")
        elif stock and not stock.get("ok"):
            lines.append(f"本店库存没查到：{stock['error']['message']}。")
            if stock["error"]["code"] == "INVALID_ISBN_FORMAT":
                lines.append("你给的 ISBN 位数不对，麻烦核对一下再发给我。")

        if "get_competitor_price" in wanted:
            if competitor and competitor.get("ok"):
                cheapest = min(competitor["quotes"], key=lambda quote: quote["price"])
                detail = "；".join(
                    f"{quote['platform']} {quote['price']} 元"
                    f"（{'有货' if quote['inStock'] else '缺货'}，{quote['deliveryDays']} 天到）"
                    for quote in competitor["quotes"]
                )
                lines.append(f"其他平台报价：{detail}。最低价出现在 {cheapest['platform']}。")
                if stock and stock.get("ok"):
                    diff = stock["price"] - cheapest["price"]
                    if diff > 0:
                        lines.append(f"本店比最低价贵 {diff} 元。")
                    elif diff < 0:
                        lines.append(f"本店比最低价便宜 {-diff} 元。")
                    else:
                        lines.append("本店与最低价持平。")
            elif competitor:
                lines.append(f"比价接口这次没返回结果：{competitor['error']['message']}。")

        if not lines:
            lines.append("这次没能查到有效信息，请稍后再试或换一个 ISBN。")
        return "\n".join(lines)
