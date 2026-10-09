"""HTTP 服务：把 RAG 与 ReAct 能力暴露成接口。

    python -m backend.server            # 127.0.0.1:8000
    curl http://127.0.0.1:8000/api/guide/health
    curl -X POST http://127.0.0.1:8000/api/guide/policy/search \
         -H 'Content-Type: application/json' -d '{"question":"拆了塑封还能退吗"}'
    curl -X POST http://127.0.0.1:8000/api/guide/chat \
         -H 'Content-Type: application/json' \
         -d '{"message":"我想买一本关于微服务的书，另外拆了塑封还能退吗？"}'

三个接口对应作业的三块验证点：``policy/search`` 直接看 RAG 检索结果，
``chat`` 看 ReAct 链路，``health`` 看索引是否就绪。
"""

from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .agent import ReActAgent
from .config import LLM, RAG
from .llm import LocalReActLLM, ModelAPIError, build_client
from .tools import BookstoreTools, PolicyIndexError, build_registry

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("ebook.guide.server")

app = FastAPI(title="E-BookStore 导购助手（RAG + ReAct）", version="1.0.0")

#: 与作业2同样的白名单：Vite 只监听 localhost 时，macOS 上浏览器发的 Origin
#: 可能是 http://[::1]:5173，漏掉它会拿到 400。
#: 部署到别的域名时用 GUIDE_ALLOWED_ORIGINS 覆盖（逗号分隔）。
DEFAULT_ALLOWED_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://[::1]:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
    "http://[::1]:4173",
)


def allowed_origins() -> list[str]:
    raw = os.environ.get("GUIDE_ALLOWED_ORIGINS", "").strip()
    if not raw:
        return list(DEFAULT_ALLOWED_ORIGINS)
    return [item.strip() for item in raw.split(",") if item.strip()]


app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#: 进程级共享：索引只建一次，之后所有请求复用。
TOOLS = BookstoreTools()


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="顾客的自然语言提问")
    useRemoteModel: bool = Field(False, description="true 时强制走真实模型接口")


class PolicySearchRequest(BaseModel):
    question: str = Field(..., min_length=1)
    topK: int = Field(RAG.top_k, ge=1, le=6)


def build_agent(use_remote: bool) -> tuple[ReActAgent, str]:
    if use_remote:
        client = build_client()
        mode = f"remote:{LLM.model}"
    else:
        client = LocalReActLLM()
        mode = "offline:rule-based"
    registry = build_registry(TOOLS)
    return (
        ReActAgent(
            client=client,
            registry=registry,
            on_step=lambda step: logger.info(step.log_trace()),
        ),
        mode,
    )


@app.get("/api/guide/health")
def health() -> dict[str, Any]:
    try:
        stats = TOOLS.ensure_index().stats()
        rag_status = "ready"
    except PolicyIndexError as error:
        stats = {"error": str(error), "hint": error.hint}
        rag_status = "unavailable"
    return {
        "status": "ok",
        "rag": rag_status,
        "ragStats": stats,
        "catalogSize": len(TOOLS.catalog),
        "tools": list(build_registry(TOOLS).names),
        "llmConfigured": LLM.configured,
        "llmModel": LLM.model,
    }


@app.post("/api/guide/policy/search")
def policy_search(request: PolicySearchRequest) -> dict[str, Any]:
    """只跑 RAG 检索，用来单独验证「分块 + 向量化 + 相似度检索」这一段。"""
    try:
        index = TOOLS.ensure_index()
    except PolicyIndexError as error:
        raise HTTPException(
            status_code=503, detail={"message": str(error), "hint": error.hint}
        ) from error

    passages = index.retrieve(request.question, top_k=request.topK)
    return {
        "question": request.question,
        "minScore": RAG.min_score,
        "count": len(passages),
        "passages": [item.to_dict() for item in passages],
        "index": index.stats(),
    }


@app.post("/api/guide/chat")
def chat(request: ChatRequest) -> dict[str, Any]:
    """跑一次完整的 ReAct 问答，返回链路与最终答复。"""
    if request.useRemoteModel and not LLM.configured:
        raise HTTPException(
            status_code=400, detail="未配置 LLM_API_KEY，无法使用真实模型"
        )

    logger.info("用户提问：%s", request.message)
    agent, mode = build_agent(request.useRemoteModel)
    try:
        result = agent.run(request.message)
    except ModelAPIError as error:
        logger.error("模型接口错误：%s", error.report)
        raise HTTPException(status_code=502, detail=error.report) from error

    logger.info(
        "回复（%s，%d 轮，%s）：%s",
        mode,
        result.rounds,
        result.stopped_reason,
        result.reply,
    )
    return {"modelMode": mode, **result.to_dict()}


@app.get("/api/guide/tools")
def tools_schema() -> dict[str, Any]:
    """给前端/文档用的工具 Schema。"""
    return {"tools": build_registry(TOOLS).schemas}


def main() -> None:
    import uvicorn

    # 端口从环境变量读：与客服助手（python-assistant，默认 8000）同时跑时，
    # 用 PORT=8010 起本服务，前端通过 Vite 代理的 /guide-api 访问。
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT") or os.environ.get("GUIDE_PORT") or 8000)
    logger.info("导购助手服务：http://%s:%d/api/guide/health", host, port)
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
