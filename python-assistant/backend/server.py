"""HTTP 服务：把 Function Calling 循环暴露给电子书城前端。

接口：
    POST /api/assistant/chat    一次问答，返回回复与本次触发的全部函数调用
    GET  /api/assistant/tools   当前交给大模型的 Tool 列表（排查用）
    GET  /api/assistant/health  健康检查与当前模型模式

启动：
    uvicorn backend.server:app --port 8000 --reload
或：
    python -m backend.server
"""

from __future__ import annotations

import logging
import os
import uuid

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .agent import BookstoreAssistant, ToolEvent
from .config import LLM
from .llm import LocalRuleBasedLLM, ModelAPIError, build_client
from .tools import build_registry

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s | %(message)s",
)
logger = logging.getLogger("ebook.assistant.server")


def _allowed_origins() -> list[str]:
    """前端开发服务器的来源白名单。

    Vite 只监听 localhost 时，在 macOS 上可能只绑到 IPv6 的 ::1，
    浏览器据此发出的 Origin 就是 http://[::1]:5173 —— 和 127.0.0.1 不是同一个来源，
    漏掉它会让预检请求直接 400。所以三种回环写法都列上。
    生产环境用 ASSISTANT_ALLOWED_ORIGINS 覆盖（逗号分隔）。
    """
    configured = os.environ.get("ASSISTANT_ALLOWED_ORIGINS", "").strip()
    if configured:
        return [origin.strip() for origin in configured.split(",") if origin.strip()]

    hosts = ("localhost", "127.0.0.1", "[::1]")
    ports = ("5173", "4173")
    return [f"http://{host}:{port}" for host in hosts for port in ports]


ALLOWED_ORIGINS = _allowed_origins()


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="用户提问")
    history: list[dict] = Field(
        default_factory=list,
        description="之前的对话消息（OpenAI 格式），用于多轮上下文；只保留最近若干条",
    )


class ToolCallView(BaseModel):
    round: int
    name: str
    arguments: dict
    ok: bool
    durationMs: int
    result: dict
    parseError: str | None = None


class ChatResponse(BaseModel):
    requestId: str
    reply: str
    toolCalls: list[ToolCallView]
    rounds: int
    stoppedReason: str
    modelMode: str


def _build_assistant(on_tool_call=None) -> tuple[BookstoreAssistant, str]:
    """按配置返回助手实例与实际使用的模型模式。

    每次请求都新建客户端：LocalRuleBasedLLM 会记录「哪些错误已经重试过」，
    这份状态属于一次对话，跨请求复用会让第二次提问不再重试。
    """
    registry = app.state.registry
    if LLM.configured:
        return (
            BookstoreAssistant(client=build_client(), registry=registry, on_tool_call=on_tool_call),
            f"remote:{LLM.model}",
        )
    return (
        BookstoreAssistant(
            client=LocalRuleBasedLLM(), registry=registry, on_tool_call=on_tool_call
        ),
        "offline:rule-based",
    )


app = FastAPI(
    title="E-BookStore 客服助手 API",
    description="基于 Function Calling 的图书库存与比价问答服务。",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)
app.state.registry = build_registry()


@app.get("/api/assistant/health")
def health() -> dict:
    return {
        "status": "ok",
        "modelMode": f"remote:{LLM.model}" if LLM.configured else "offline:rule-based",
        "llmBaseUrl": LLM.base_url if LLM.configured else None,
    }


@app.get("/api/assistant/tools")
def list_tools() -> dict:
    """把 Tool 列表原样吐出来，便于确认模型看到的就是这份 schema。"""
    return {"tools": app.state.registry.schemas}


@app.post("/api/assistant/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    request_id = uuid.uuid4().hex[:12]
    logger.info("[%s] 用户提问：%s", request_id, payload.message)

    def log_tool_call(event: ToolEvent) -> None:
        # 作业要求：拦截模型输出并打印需要调用的函数名及参数。
        logger.info("[%s] %s", request_id, event.log_line())

    assistant, model_mode = _build_assistant(on_tool_call=log_tool_call)

    try:
        result = assistant.chat(payload.message, history=payload.history[-12:])
    except ModelAPIError as error:
        # 配置类错误（URL 写错、密钥无效）不吞掉：把排查方向一并返回，
        # 否则前端只看到一句「NotFoundError」，看不出是 LLM_BASE_URL 多写了一段。
        logger.error("[%s] 模型接口调用失败：%s", request_id, error.report)
        return ChatResponse(
            requestId=request_id,
            reply=f"助手暂时不可用：{error}。{error.hint}",
            toolCalls=[],
            rounds=0,
            stoppedReason="model_error",
            modelMode=model_mode,
        )
    except Exception as error:  # noqa: BLE001 - 兜底，保证接口永远返回可展示的内容
        logger.exception("[%s] 对话失败", request_id)
        return ChatResponse(
            requestId=request_id,
            reply=f"助手暂时不可用（{type(error).__name__}），请稍后重试。",
            toolCalls=[],
            rounds=0,
            stoppedReason="error",
            modelMode=model_mode,
        )

    logger.info("[%s] 回复：%s", request_id, result.reply.replace("\n", " "))
    return ChatResponse(
        requestId=request_id,
        modelMode=model_mode,
        **result.to_dict(),
    )


def main() -> None:
    import uvicorn

    uvicorn.run("backend.server:app", host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    main()
