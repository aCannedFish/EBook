"""HTTP 接口测试。"""

from __future__ import annotations

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from backend import server  # noqa: E402


@pytest.fixture(scope="module")
def client():
    return TestClient(server.app)


class TestHealth:
    def test_reports_index_and_tools(self, client):
        payload = client.get("/api/guide/health").json()
        assert payload["status"] == "ok"
        assert payload["rag"] == "ready"
        assert payload["catalogSize"] >= 10
        assert payload["tools"] == ["search_book_catalog", "query_store_policy"]
        assert payload["ragStats"]["count"] > 0
        assert payload["llmConfigured"] is False  # 测试环境里没有配密钥


class TestPolicySearch:
    def test_returns_passages_with_scores(self, client):
        response = client.post(
            "/api/guide/policy/search", json={"question": "拆了塑封还能退吗"}
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["count"] >= 1
        assert payload["passages"][0]["clause"].startswith("第六条")
        assert payload["index"]["dimensions"] > 0

    def test_custom_top_k(self, client):
        payload = client.post(
            "/api/guide/policy/search", json={"question": "退货", "topK": 1}
        ).json()
        assert len(payload["passages"]) == 1

    def test_invalid_top_k_is_rejected(self, client):
        assert (
            client.post(
                "/api/guide/policy/search", json={"question": "退货", "topK": 99}
            ).status_code
            == 422
        )

    def test_empty_question_is_rejected(self, client):
        assert (
            client.post("/api/guide/policy/search", json={"question": ""}).status_code
            == 422
        )

    def test_uncovered_question_returns_no_passages(self, client):
        payload = client.post(
            "/api/guide/policy/search", json={"question": "海外直邮的书可以退吗"}
        ).json()
        assert payload["count"] == 0


class TestChat:
    def test_react_chain_in_response(self, client):
        response = client.post(
            "/api/guide/chat",
            json={"message": "我想买一本关于微服务的书，另外拆了塑封还能退吗？"},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["modelMode"] == "offline:rule-based"
        assert [step["action"] for step in payload["steps"]] == [
            "search_book_catalog",
            "query_store_policy",
        ]
        assert payload["stoppedReason"] == "completed"
        assert "第六条" in payload["reply"]

    def test_remote_model_requires_key(self, client):
        response = client.post(
            "/api/guide/chat", json={"message": "你好", "useRemoteModel": True}
        )
        assert response.status_code == 400
        assert "LLM_API_KEY" in response.json()["detail"]

    def test_empty_message_is_rejected(self, client):
        assert client.post("/api/guide/chat", json={"message": ""}).status_code == 422


def test_tools_schema_endpoint(client):
    payload = client.get("/api/guide/tools").json()
    assert [item["function"]["name"] for item in payload["tools"]] == [
        "search_book_catalog",
        "query_store_policy",
    ]


def test_server_logs_actual_thought_action_and_observation(client, caplog):
    """评分日志必须包含决策和工具观测，只有动作摘要不足以核对链路。"""
    import logging

    with caplog.at_level(logging.INFO, logger="ebook.guide.server"):
        response = client.post(
            "/api/guide/chat",
            json={"message": "我想买一本关于微服务的书，另外拆了塑封还能退吗？"},
        )
    assert response.status_code == 200
    for step in response.json()["steps"]:
        assert f"Thought: {step['thought']}" in caplog.text
        assert f"Action: {step['action']}" in caplog.text
        assert f"Observation: {step['observation']}" in caplog.text
