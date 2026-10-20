"""书城共用 AI 服务：Function Calling、ReAct 导购与接口设计共用一套登录身份。

数据边界：库存与书目通过当前顾客的 JWT 读取 Spring Boot 书城，政策来自
本项目的文本知识库。竞争对手报价按课程要求模拟，所有工具观测由实际执行产生。
"""

from __future__ import annotations

import logging
import os
import urllib.error
import uuid
from functools import lru_cache

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .agent import BookstoreAssistant, ToolEvent
from .catalog import BookstoreOutOfReach, HttpInventoryBackend, InventoryBackend
from .config import LLM, TOOLS
from .llm import LocalRuleBasedLLM, ModelAPIError, build_client
from .tools import TOOL_SCHEMAS, build_registry

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
app = FastAPI(title="EBook 书城 AI 服务", version="2.0.0")
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


def _build_assistant(inventory: InventoryBackend, on_tool_call=None):
    """每个请求独立创建模型与工具状态；库存始终使用当前顾客的实时数据源。"""
    registry = app.state.registry or build_registry(inventory)
    client = build_client() if LLM.configured else LocalRuleBasedLLM()
    mode = f"remote:{LLM.model}" if LLM.configured else "offline:rule-based"
    return BookstoreAssistant(client=client, registry=registry, on_tool_call=on_tool_call), mode


@app.get("/api/assistant/health")
def health() -> dict:
    return {"status": "ok", "modelMode": f"remote:{LLM.model}" if LLM.configured else "offline:rule-based",
            "inventorySource": "springboot-ebook", "guideInSameService": True}


@app.get("/api/assistant/tools")
def list_tools() -> dict:
    return {"tools": TOOL_SCHEMAS}


@app.post("/api/assistant/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, inventory: InventoryBackend = Depends(require_inventory)):
    request_id = uuid.uuid4().hex[:12]
    logger.info("[%s] 用户提问：%s", request_id, payload.message)

    def record(event: ToolEvent) -> None:
        logger.info("[%s] %s", request_id, event.log_line())

    assistant, mode = _build_assistant(inventory, on_tool_call=record)
    history = [entry for entry in payload.history[-12:]
               if entry.get("role") in {"user", "assistant"} and isinstance(entry.get("content"), str)]
    try:
        result = assistant.chat(payload.message, history=history)
    except ModelAPIError as error:
        raise HTTPException(502, error.report) from error
    logger.info("[%s] 最终答复：%s", request_id, result.reply)
    return ChatResponse(requestId=request_id, modelMode=mode, **result.to_dict())


@lru_cache(maxsize=1)
def policy_index():
    """知识库仅构建一次，文档与查询使用相同的编码器和向量空间。"""
    from .guide.rag import RagPipeline
    return RagPipeline().build()


def live_catalog(inventory: HttpInventoryBackend):
    """把现有书城 DTO 映射为可检索条目，不为缺少的出版年、评分编造数值。"""
    from .guide.catalog import Book, Catalog
    books = [Book(isbn=book["isbn"], title=book["title"], author=book["author"],
                  publisher=book["publisher"], year=0, price=book["price"],
                  category=book["category"], tags=(), summary=book["description"],
                  stock_qty=book["stockQty"], rating=0.0, sales=0)
             for book in inventory.fetch_books()]
    return Catalog(books, source="bookstore-api")


class GuideRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    useRemoteModel: bool | None = None


class PolicySearchRequest(BaseModel):
    question: str = Field(..., min_length=1)
    topK: int = Field(3, ge=1, le=6)


@app.get("/api/guide/health")
def guide_health(inventory: HttpInventoryBackend = Depends(require_inventory)):
    index = policy_index()
    return {"status": "ok", "rag": "ready", "ragStats": index.stats(),
            "llmConfigured": LLM.configured, "catalogSize": len(inventory.fetch_books()),
            "catalogSource": "springboot-ebook"}


@app.get("/api/guide/tools")
def guide_tools():
    from .guide.tools import TOOL_SCHEMAS
    return {"tools": TOOL_SCHEMAS}


@app.post("/api/guide/policy/search")
def policy_search(payload: PolicySearchRequest, inventory=Depends(require_inventory)):
    index = policy_index()
    hits = index.retrieve(payload.question, top_k=payload.topK)
    return {"question": payload.question, "passages": [hit.to_dict() for hit in hits],
            "count": len(hits), "index": index.stats()}


@app.post("/api/guide/chat")
def guide_chat(payload: GuideRequest, inventory=Depends(require_inventory)):
    from .guide.agent import ReActAgent
    from .guide.llm import LocalReActLLM, build_client as guide_client, ModelAPIError as GuideModelError
    from .guide.tools import BookstoreTools, build_registry as guide_registry
    remote = LLM.configured if payload.useRemoteModel is None else payload.useRemoteModel
    if remote and not LLM.configured:
        raise HTTPException(400, "未配置真实模型 API")
    tools = BookstoreTools(catalog=live_catalog(inventory), index=policy_index())
    agent = ReActAgent(client=guide_client() if remote else LocalReActLLM(),
                      registry=guide_registry(tools), on_step=lambda step: logger.info(step.log_trace()))
    try:
        result = agent.run(payload.message)
    except GuideModelError as error:
        raise HTTPException(502, error.report) from error
    return {"modelMode": f"remote:{LLM.model}" if remote else "offline:rule-based", **result.to_dict()}


def main() -> None:
    import uvicorn
    uvicorn.run("backend.server:app", host="127.0.0.1", port=8000)




@app.get("/api/design/conversation")
def design_conversation(inventory=Depends(require_inventory)):
    """供书城中的接口设计页展示真实模型调用记录，刷新页面后仍可复核。"""
    import json
    from .api_design import OUTPUT, SYSTEM_PROMPT
    user = inventory.get_json("/api/v1/users/me")
    if not user.get("admin"):
        raise HTTPException(403, "仅管理员可生成接口文档")
    path = OUTPUT / "conversation.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}], "model": LLM.model}


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
