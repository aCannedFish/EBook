"""HTTP 接口测试。

前端实际调用的就是这几个接口，所以它们的返回结构必须稳定：
``steps`` 同时承载函数调用（作业2）与 Thought -> Action -> Observation（作业3），
是界面展示执行过程的唯一数据来源。
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.assistant.tools import UnifiedRegistry
from backend.catalog import MockInventoryBackend
from backend.guide.catalog import DEFAULT_CATALOG
from backend.guide.tools import BookstoreTools as GuideBookstoreTools
from backend.server import app, require_inventory
from backend.tools import BookstoreTools as InventoryToolset


@pytest.fixture
def client(policy_index):
    """注入一份固定的工具注册表：库存用模拟数据，书目用课程演示目录。

    政策索引由会话级夹具提供（离线 TF-IDF），不依赖网络与模型下载。
    """
    app.state.registry = UnifiedRegistry(
        inventory_tools=InventoryToolset(inventory=MockInventoryBackend()),
        guide_tools=GuideBookstoreTools(catalog=DEFAULT_CATALOG, index=policy_index),
    )
    app.dependency_overrides[require_inventory] = lambda: MockInventoryBackend()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    app.state.registry = None


def test_health_reports_offline_mode_and_merged_tools(client):
    body = client.get("/api/assistant/health").json()
    assert body["status"] == "ok"
    assert body["modelMode"] == "offline:rule-based"
    assert body["inventorySource"] == "springboot-ebook"
    assert body["tools"] == [
        "check_inventory",
        "get_competitor_price",
        "search_book_catalog",
        "query_store_policy",
    ]


def test_tools_endpoint_exposes_model_visible_schemas(client):
    tools = client.get("/api/assistant/tools").json()["tools"]
    assert [tool["function"]["name"] for tool in tools] == [
        "check_inventory",
        "get_competitor_price",
        "search_book_catalog",
        "query_store_policy",
    ]
    # 每个 Schema 都要有描述与参数定义，否则模型无法判断何时调用。
    for tool in tools:
        function = tool["function"]
        assert function["description"]
        assert function["parameters"]["type"] == "object"


def test_chat_returns_reply_and_steps(client):
    response = client.post(
        "/api/assistant/chat",
        json={
            "message": "帮我查一下 ISBN为978-3-00-000000-4 的书还有多少本，顺便看看别家卖多少钱"
        },
    )
    assert response.status_code == 200
    body = response.json()

    assert body["requestId"]
    assert [step["action"] for step in body["steps"]] == [
        "check_inventory",
        "get_competitor_price",
    ]
    assert all(step["ok"] for step in body["steps"])
    assert all(step["thought"] for step in body["steps"])
    assert body["steps"][0]["arguments"] == {"isbn": "978-3-00-000000-4"}
    assert body["steps"][0]["result"]["stockQty"] == 30
    assert "30 本" in body["reply"]
    assert body["stoppedReason"] == "completed"


def test_chat_surfaces_tool_failure_to_the_client(client):
    """ISBN 不合法时，前端要能拿到失败原因，而不是只有一句含糊的回复。"""
    body = client.post(
        "/api/assistant/chat", json={"message": "ISBN为12345 的书还有多少本"}
    ).json()

    [step] = body["steps"]
    assert step["ok"] is False
    assert step["result"]["error"]["code"] == "INVALID_ISBN_FORMAT"
    assert step["result"]["error"]["retryable"] is False
    assert "核对" in body["reply"]


def test_chat_retries_transient_upstream_timeout(client):
    body = client.post(
        "/api/assistant/chat",
        json={"message": "ISBN为978-7-00-000000-8 的书还有几本？另外帮我对比一下其他平台的价格"},
    ).json()

    price_steps = [step for step in body["steps"] if step["action"] == "get_competitor_price"]
    assert len(price_steps) == 2
    assert price_steps[0]["ok"] is False
    assert price_steps[0]["result"]["error"]["code"] == "UPSTREAM_TIMEOUT"
    assert price_steps[1]["ok"] is True


def test_chat_routes_catalog_then_policy(client):
    body = client.post(
        "/api/assistant/chat",
        json={"message": "我想买一本关于微服务的书，另外如果我买了不喜欢，拆了塑封还能退吗？"},
    ).json()

    assert [step["action"] for step in body["steps"]] == [
        "search_book_catalog",
        "query_store_policy",
    ]
    assert all(step["ok"] for step in body["steps"])


def test_chat_accepts_history(client):
    body = client.post(
        "/api/assistant/chat",
        json={
            "message": "ISBN为978-3-00-000000-4 那本呢？",
            "history": [
                {"role": "user", "content": "你好"},
                {"role": "assistant", "content": "你好，请提供 ISBN。"},
            ],
        },
    ).json()
    assert "30 本" in body["reply"]


@pytest.mark.parametrize("payload", [{}, {"message": ""}])
def test_chat_rejects_empty_message(client, payload):
    assert client.post("/api/assistant/chat", json=payload).status_code == 422


@pytest.mark.parametrize(
    "origin",
    ["http://localhost:5173", "http://127.0.0.1:5173", "http://[::1]:5173"],
)
def test_cors_allows_every_loopback_spelling_of_the_dev_server(client, origin):
    """Vite 只监听 localhost 时在 macOS 上可能只绑到 ::1，浏览器发的 Origin 就是 [::1]。
    漏掉它会 400，前端会退化成「连不上助手服务」。"""
    response = client.options(
        "/api/assistant/chat",
        headers={"Origin": origin, "Access-Control-Request-Method": "POST"},
    )
    assert response.headers.get("access-control-allow-origin") == origin


def test_cors_rejects_unknown_origin(client):
    response = client.options(
        "/api/assistant/chat",
        headers={"Origin": "http://evil.example.com", "Access-Control-Request-Method": "POST"},
    )
    assert response.headers.get("access-control-allow-origin") is None


def test_chat_requires_bookstore_identity():
    with TestClient(app) as client:
        response = client.post("/api/assistant/chat", json={"message": "查库存"})
    assert response.status_code == 401
