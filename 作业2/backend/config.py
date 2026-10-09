"""运行期配置。

配置来源有两处，后者不覆盖前者：
1. 进程环境变量（命令行 export 的，优先级最高）；
2. 助手目录下的 ``.env`` 文件（复制 ``.env.example`` 改名即可，适合长期本地配置）。

所有配置都有默认值，不配置任何东西也能跑起来 —— 未设置 ``LLM_API_KEY`` 时
使用内置的离线替身模型。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

#: .env 的查找位置：先看包所在目录的上一级（python-assistant/），再看当前工作目录。
#: 两个都读，所以无论从仓库根跑还是从助手目录跑，配置都生效。
DOTENV_CANDIDATES = (
    Path(__file__).resolve().parent.parent / ".env",
    Path.cwd() / ".env",
)


def load_dotenv(paths: tuple[Path, ...] = DOTENV_CANDIDATES) -> None:
    """把 .env 里的键值对写进 os.environ。

    已经存在的环境变量不覆盖 —— 临时用 `LLM_MODEL=xxx ./run-local.sh` 覆盖文件里的配置，
    应该符合直觉。只做最简单的 KEY=VALUE 解析，不引入 python-dotenv 依赖。
    """
    for path in paths:
        if not path.is_file():
            continue
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[len("export "):].strip()
            key, separator, value = line.partition("=")
            if not separator:
                continue
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


load_dotenv()


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


DEFAULT_BASE_URL = "https://api.openai.com/v1"


def normalize_base_url(raw: str) -> str:
    """把 base_url 归一化成「服务根 + /v1」的形式。

    OpenAI 的 SDK 会在 base_url 后面自己拼 ``/chat/completions``，
    所以 base_url 填成完整的接口地址会变成 ``.../chat/completions/chat/completions``，
    服务端返回 404 NotFoundError —— 这个错误信息完全看不出是 URL 多写了一段。
    这里直接把多出来的后缀去掉，并且只去掉一次。
    """
    url = (raw or DEFAULT_BASE_URL).strip().rstrip("/")
    for suffix in ("/chat/completions", "/completions"):
        if url.endswith(suffix):
            return url[: -len(suffix)].rstrip("/")
    return url


@dataclass(frozen=True)
class LLMSettings:
    """OpenAI 兼容接口配置。

    base_url 指向即可切换供应商，例如：
      OpenAI          https://api.openai.com/v1
      DeepSeek        https://api.deepseek.com/v1
      通义千问兼容模式 https://dashscope.aliyuncs.com/compatible-mode/v1
    """

    base_url: str
    api_key: str
    model: str
    timeout_seconds: float
    temperature: float

    @classmethod
    def from_env(cls) -> "LLMSettings":
        return cls(
            base_url=normalize_base_url(os.environ.get("LLM_BASE_URL", "")),
            api_key=os.environ.get("LLM_API_KEY", ""),
            model=os.environ.get("LLM_MODEL", "gpt-4o-mini"),
            timeout_seconds=_env_float("LLM_TIMEOUT_SECONDS", 30.0),
            temperature=_env_float("LLM_TEMPERATURE", 0.2),
        )

    @property
    def configured(self) -> bool:
        return bool(self.api_key.strip())

    @property
    def endpoint(self) -> str:
        """真正被请求的地址。SDK 会在 base_url 后面拼 /chat/completions。"""
        return f"{self.base_url.rstrip('/')}/chat/completions"


@dataclass(frozen=True)
class ToolSettings:
    """工具层配置。"""

    #: 设置后 check_inventory 改从真实后端取库存；留空则使用内置模拟目录。
    bookstore_api_base: str
    #: 模拟外部比价接口的单次调用耗时（秒），用于演示超时与重试。
    competitor_latency_seconds: float
    #: 比价接口的超时阈值（秒）。超过该值即判定为上游超时。
    competitor_timeout_seconds: float
    #: 首次调用必定超时、重试才成功的一组 ISBN（模拟上游抖动）。
    transient_timeout_isbns: frozenset[str]
    #: 永久不可用的一组 ISBN（模拟上游整体故障，重试也没有意义）。
    permanently_down_isbns: frozenset[str]

    @classmethod
    def from_env(cls) -> "ToolSettings":
        return cls(
            bookstore_api_base=os.environ.get("BOOKSTORE_API_BASE", "").rstrip("/"),
            competitor_latency_seconds=_env_float("COMPETITOR_LATENCY_SECONDS", 0.4),
            competitor_timeout_seconds=_env_float("COMPETITOR_TIMEOUT_SECONDS", 1.0),
            # 量子物理：第一次比价超时，重试成功。
            transient_timeout_isbns=frozenset({"9787000000008"}),
            # Intorduction to Computing Systems：比价渠道整体不可用，重试无意义。
            permanently_down_isbns=frozenset({"9782000000003"}),
        )


@dataclass(frozen=True)
class AgentSettings:
    """Function Calling 循环配置。"""

    #: 单轮用户提问内允许的最大「模型 → 工具 → 模型」往返次数。
    max_tool_rounds: int
    #: 工具连续失败多少次后不再把错误丢回模型，直接给出兜底话术。
    max_consecutive_tool_errors: int

    @classmethod
    def from_env(cls) -> "AgentSettings":
        return cls(
            max_tool_rounds=_env_int("AGENT_MAX_TOOL_ROUNDS", 6),
            max_consecutive_tool_errors=_env_int("AGENT_MAX_TOOL_ERRORS", 3),
        )


LLM = LLMSettings.from_env()
TOOLS = ToolSettings.from_env()
AGENT = AgentSettings.from_env()
