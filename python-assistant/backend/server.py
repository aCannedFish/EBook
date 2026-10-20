"""书城 AI 服务：合并后的客服助手、接口设计与登录身份共用一套后端。

合并后的助手把四次作业里的三条链路收在一个入口：

- 作业2 的 Function Calling：模型拿到 ``tools`` 列表，返回 ``tool_calls``，
  本地执行后以 ``tool`` 消息回填；
- 作业3 的 RAG 与 ReAct：政策库分块 + 向量检索，执行过程按
  Thought → Action → Observation 逐步记录；
- 两侧共用的登录身份：先由原书城校验 JWT，再用同一身份读取书目与库存。

数据边界：库存与书目通过当前顾客的 JWT 读取 Spring Boot 书城，政策来自本项目的
知识库。竞争对手报价按课程要求模拟，所有工具观测都由实际执行产生。
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import uuid
from functools import lru_cache

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .assistant.agent import AssistantStep, UnifiedAssistant
from .assistant.offline import LocalUnifiedLLM
from .assistant.prompt import SYSTEM_PROMPT
from .assistant.tools import TOOL_NAMES, TOOL_SCHEMAS, UnifiedRegistry
from .catalog import BookstoreOutOfReach, HttpInventoryBackend, InventoryBackend
from .config import LLM, TOOLS
from .guide.catalog import Book, Catalog
from .guide.tools import BookstoreTools as GuideBookstoreTools
from .llm import ModelAPIError, build_client
from .tools import BookstoreTools as InventoryToolset

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s | %(message)s")
logger = logging.getLogger("ebook.assistant.server")


def _allowed_origins() -> list[str]:
    """开发环境只允许书城前端回环来源；部署时可指定白名单。"""
    configured = os.environ.get("ASSISTANT_ALLOWED_ORIGINS", "").strip()
    if configured:
        return [value.strip() for value in configured.split(",") if value.strip()]
    return [f"http://{host}:{port}" for host in ("localhost", "127.0.0.1", "[::1]")
            for port in ("5173", "4173")]


ALLOWED_ORIGINS = _allowed_origins()
app = FastAPI(title="EBook 书城 AI 服务", version="3.0.0")
app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS, allow_credentials=False,
                   allow_methods=["GET", "POST", "OPTIONS"], allow_headers=["*"])
# 测试可显式注入注册表；正常请求均使用各自身份创建工具，避免跨用户共享可变状态。
app.state.registry = None


def require_inventory(authorization: str | None = Header(default=None)) -> HttpInventoryBackend:
    """先由原书城校验 JWT，再将同一身份用于后续工具查询。"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "请先登录书城并携带 Bearer Token")
    inventory = HttpInventoryBackend(TOOLS.bookstore_api_base or "http://127.0.0.1:8080",
                                     authorization=authorization)
    try:
        inventory.get_json("/api/v1/users/me")
    except BookstoreOutOfReach as error:
        cause = error.__cause__
        if isinstance(cause, urllib.error.HTTPError) and cause.code in (401, 403):
            raise HTTPException(cause.code, "书城登录身份无效，请重新登录") from error
        raise HTTPException(503, "书城业务后端暂时不可用") from error
    return inventory


class ChatRequest(BaseModel):
    """前端对话输入；历史只接受普通消息，不接受覆盖系统提示词。"""
    message: str = Field(..., min_length=1, max_length=2000)
    history: list[dict] = Field(default_factory=list)


class StepView(BaseModel):
    """一步执行记录：模型的理由、动作、参数与真实观测。"""
    index: int
    thought: str
    action: str
    arguments: dict
    ok: bool
    durationMs: int
    observation: str
    result: dict | None = None
    parseError: str | None = None


class ChatResponse(BaseModel):
    requestId: str
    reply: str
    steps: list[StepView]
    rounds: int
    stoppedReason: str
    modelMode: str


@lru_cache(maxsize=1)
def policy_index():
    """知识库仅构建一次；书目每请求现取，政策索引不随登录身份变化。"""
    from .guide.rag import RagPipeline

    return RagPipeline().build()


def live_catalog(inventory: InventoryBackend) -> Catalog:
    """把现有书城 DTO 映射为可检索条目，不为缺少的出版年、评分编造数值。"""
    books = [
        Book(
            isbn=book["isbn"],
            title=book["title"],
            author=book["author"],
            publisher=book.get("publisher") or "",
            year=0,
            price=book["price"],
            category=book.get("category") or "",
            tags=(),
            summary=book.get("description") or book.get("category") or "",
            stock_qty=book["stockQty"],
            rating=0.0,
            sales=0,
        )
        for book in inventory.fetch_books()
    ]
    return Catalog(books, source="bookstore-api")


def build_registry(inventory: InventoryBackend) -> UnifiedRegistry:
    """四个工具共用当前登录身份：库存/比价直连书城，书目与政策走本地索引。"""
    guide_tools = GuideBookstoreTools(catalog=live_catalog(inventory), index=policy_index())
    return UnifiedRegistry(
        inventory_tools=InventoryToolset(inventory=inventory),
        guide_tools=guide_tools,
    )


def _build_assistant(inventory: InventoryBackend, on_step=None):
    """每个请求独立创建模型与工具状态；库存始终使用当前顾客的实时数据源。"""
    registry = app.state.registry or build_registry(inventory)
    client = build_client() if LLM.configured else LocalUnifiedLLM()
    mode = f"remote:{LLM.model}" if LLM.configured else "offline:rule-based"
    return UnifiedAssistant(client=client, registry=registry, on_step=on_step), mode


@app.get("/api/assistant/health")
def health() -> dict:
    return {
        "status": "ok",
        "modelMode": f"remote:{LLM.model}" if LLM.configured else "offline:rule-based",
        "inventorySource": "springboot-ebook",
        "tools": list(TOOL_NAMES),
    }


@app.get("/api/assistant/tools")
def list_tools() -> dict:
    return {"tools": TOOL_SCHEMAS}


@app.post("/api/assistant/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, inventory: InventoryBackend = Depends(require_inventory)):
    request_id = uuid.uuid4().hex[:12]
    logger.info("[%s] 用户提问：%s", request_id, payload.message)

    def record(step: AssistantStep) -> None:
        logger.info("[%s] %s", request_id, step.log_trace())

    assistant, mode = _build_assistant(inventory, on_step=record)
    history = [entry for entry in payload.history[-12:]
               if entry.get("role") in {"user", "assistant"} and isinstance(entry.get("content"), str)]
    try:
        result = assistant.chat(payload.message, history=history)
    except ModelAPIError as error:
        raise HTTPException(502, error.report) from error
    logger.info("[%s] 最终答复：%s", request_id, result.reply)
    return ChatResponse(requestId=request_id, modelMode=mode, **result.to_dict())


def main() -> None:
    import uvicorn
    uvicorn.run("backend.server:app", host="127.0.0.1", port=8000)


@app.get("/api/design/conversation")
def design_conversation(inventory=Depends(require_inventory)):
    """供书城中的接口设计页展示真实模型调用记录，刷新页面后仍可复核。"""
    from .api_design import OUTPUT, SYSTEM_PROMPT as DESIGN_SYSTEM_PROMPT

    user = inventory.get_json("/api/v1/users/me")
    if not user.get("admin"):
        raise HTTPException(403, "仅管理员可生成接口文档")
    path = OUTPUT / "conversation.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {
        "messages": [{"role": "system", "content": DESIGN_SYSTEM_PROMPT}], "model": LLM.model}


@app.post("/api/design/chat")
def design_chat(payload: ChatRequest, inventory=Depends(require_inventory)):
    from .api_design import generate

    user = inventory.get_json("/api/v1/users/me")
    if not user.get("admin"):
        raise HTTPException(403, "仅管理员可生成接口文档")
    try:
        return generate(payload.message, payload.history)
    except (ValueError, AssertionError, RuntimeError) as error:
        raise HTTPException(502, str(error)) from error


if __name__ == "__main__":
    main()
