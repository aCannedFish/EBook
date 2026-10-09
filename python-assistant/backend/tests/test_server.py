"""HTTP 接口测试。

前端实际调用的就是这几个接口，所以它们的返回结构必须稳定：
toolCalls 是前端展示「函数调用卡片」的唯一数据来源。
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.server import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_health_reports_offline_mode(client):
    body = client.get("/api/assistant/health").json()
    assert body["status"] == "ok"
    assert body["modelMode"] == "offline:rule-based"


def test_tools_endpoint_exposes_model_visible_schemas(client):
    tools = client.get("/api/assistant/tools").json()["tools"]
    names = [tool["function"]["name"] for tool in tools]
    assert names == ["check_inventory", "get_competitor_price"]


def test_chat_returns_reply_and_tool_calls(client):
    response = client.post(
        "/api/assistant/chat",
        json={
            "message": "帮我查一下 ISBN为978-3-00-000000-4 的书还有多少本，顺便看看别家卖多少钱"
        },
    )
    assert response.status_code == 200
    body = response.json()

    assert body["requestId"]
    assert [call["name"] for call in body["toolCalls"]] == [
        "check_inventory",
        "get_competitor_price",
    ]
    assert all(call["ok"] for call in body["toolCalls"])
    assert body["toolCalls"][0]["arguments"] == {"isbn": "978-3-00-000000-4"}
    assert body["toolCalls"][0]["result"]["stockQty"] == 30
    assert "30 本" in body["reply"]
    assert body["stoppedReason"] == "completed"


def test_chat_surfaces_tool_failure_to_the_client(client):
    """ISBN 不合法时，前端要能拿到失败原因，而不是只有一句含糊的回复。"""
    body = client.post(
        "/api/assistant/chat", json={"message": "ISBN为12345 的书还有多少本"}
    ).json()

    [call] = body["toolCalls"]
    assert call["ok"] is False
    assert call["result"]["error"]["code"] == "INVALID_ISBN_FORMAT"
    assert call["result"]["error"]["retryable"] is False


def test_chat_retries_transient_upstream_timeout(client):
    body = client.post(
        "/api/assistant/chat",
        json={"message": "ISBN为978-7-00-000000-8 的书还有几本？另外帮我对比一下其他平台的价格"},
    ).json()

    price_calls = [call for call in body["toolCalls"] if call["name"] == "get_competitor_price"]
    assert len(price_calls) == 2
    assert price_calls[0]["ok"] is False
    assert price_calls[0]["result"]["error"]["code"] == "UPSTREAM_TIMEOUT"
    assert price_calls[1]["ok"] is True


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
