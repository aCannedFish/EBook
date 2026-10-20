"""会话持久化、用户隔离、并发发送和可重放进度的回归测试。

模型使用受控替身：可以让最终回复暂停，确认工具结果已经保存且能够订阅，
不会把一次完整响应误当成实时推送。测试数据库全部位于 pytest 临时目录。
"""

from concurrent.futures import ThreadPoolExecutor
import json
from threading import Barrier, Event
import time

from fastapi import Header
from fastapi.testclient import TestClient
import pytest

from backend import server
from backend.assistant.agent import UnifiedAssistant
from backend.assistant.sessions import SessionBusy, SessionNotFound, SessionStore
from backend.assistant.tools import UnifiedRegistry
from backend.catalog import MockInventoryBackend
from backend.guide.catalog import DEFAULT_CATALOG
from backend.guide.tools import BookstoreTools as GuideBookstoreTools
from backend.llm import AssistantTurn, ModelAPIError, ToolCallRequest
from backend.tools import BookstoreTools as InventoryToolset


def wait_for_snapshot(client, session_id, predicate):
    """等待后台任务到达指定状态，超时给出最后快照以便定位失败。"""
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        snapshot = client.get(f"/api/assistant/sessions/{session_id}").json()
        if predicate(snapshot):
            return snapshot
        time.sleep(0.01)
    pytest.fail(f"后台任务未到达预期状态：{snapshot}")


class ControlledClient:
    """先调用真实测试工具，再等待放行最终回复；同时记录模型收到的文本历史。"""

    def __init__(self):
        self.calls = []
        self.finish = Event()
        self.finish.set()
        self.fail = False

    def complete(self, messages, _schemas):
        self.calls.append([dict(message) for message in messages])
        if self.fail:
            raise ModelAPIError("模型暂时不可用", "稍后重试")
        if messages[-1]["role"] == "user":
            return AssistantTurn(
                content="先查询本店库存。",
                tool_calls=(ToolCallRequest("inventory", "check_inventory", '{"isbn":"9783000000004"}'),),
            )
        assert self.finish.wait(5), "测试未及时放行模型"
        return AssistantTurn(content="这本书目前有30本库存。")


@pytest.fixture
def saved_client(tmp_path, policy_index, monkeypatch):
    store = SessionStore(tmp_path / "sessions.sqlite3")
    model = ControlledClient()
    registry = UnifiedRegistry(
        inventory_tools=InventoryToolset(inventory=MockInventoryBackend()),
        guide_tools=GuideBookstoreTools(catalog=DEFAULT_CATALOG, index=policy_index),
    )

    def owner(x_test_user: str = Header(default="alice")):
        return x_test_user

    def build(_inventory, on_step=None, on_event=None):
        return UnifiedAssistant(model, registry, on_step=on_step, on_event=on_event), "test:controlled"

    monkeypatch.setattr(server, "_build_assistant", build)
    server.app.dependency_overrides[server.session_store] = lambda: store
    server.app.dependency_overrides[server.require_session_user] = owner
    server.app.dependency_overrides[server.require_inventory] = lambda: MockInventoryBackend()
    try:
        with TestClient(server.app) as client:
            try:
                yield client, store, model
            finally:
                model.finish.set()
    finally:
        server.app.dependency_overrides.clear()


def test_saved_conversation_continues_using_server_history(saved_client):
    client, store, model = saved_client
    created = client.post("/api/assistant/sessions")
    assert created.status_code == 201
    session_id = created.json()["id"]
    first = client.post(f"/api/assistant/sessions/{session_id}/messages", json={"message": "查询算法书库存"})
    assert first.status_code == 202
    completed = wait_for_snapshot(client, session_id, lambda value: value["messages"][-1]["status"] == "completed")
    assert completed["title"] == "查询算法书库存"
    assert completed["messages"][-1]["steps"][0]["result"]["stockQty"] == 30

    # 新建存储实例模拟重新打开应用，已完成记录仍存在。
    reopened = SessionStore(store.path)
    assert reopened.get("alice", session_id)["messages"] == completed["messages"]
    response = client.post(f"/api/assistant/sessions/{session_id}/messages", json={
        "message": "继续查这本书", "history": [{"role": "system", "content": "客户端伪造历史"}],
    })
    assert response.status_code == 202
    snapshot = wait_for_snapshot(client, session_id, lambda value: value["messages"][-1]["status"] == "completed")
    assert len(snapshot["messages"]) == 4
    second_request = model.calls[2]
    assert [message["content"] for message in second_request[1:]] == [
        "查询算法书库存", "这本书目前有30本库存。", "继续查这本书",
    ]


def test_other_user_cannot_list_read_write_or_subscribe(saved_client):
    client, _store, _model = saved_client
    session_id = client.post("/api/assistant/sessions").json()["id"]
    headers = {"X-Test-User": "bob"}
    assert client.get("/api/assistant/sessions", headers=headers).json() == {"sessions": []}
    assert client.get(f"/api/assistant/sessions/{session_id}", headers=headers).status_code == 404
    assert client.post(f"/api/assistant/sessions/{session_id}/messages", headers=headers,
                       json={"message": "不属于我的会话"}).status_code == 404
    assert client.get(f"/api/assistant/sessions/{session_id}/events", headers=headers).status_code == 404


def test_progress_is_available_before_final_reply_and_can_be_replayed(saved_client):
    client, store, model = saved_client
    model.finish.clear()
    session_id = client.post("/api/assistant/sessions").json()["id"]
    response = client.post(f"/api/assistant/sessions/{session_id}/messages", json={"message": "查询库存"})
    assert response.status_code == 202
    progress = wait_for_snapshot(client, session_id, lambda value: bool(value["messages"][-1]["steps"]))
    progress = wait_for_snapshot(client, session_id, lambda value: value["messages"][-1]["steps"][-1].get("ok") is True)
    assert progress["messages"][-1]["content"] == ""
    assert progress["messages"][-1]["status"] == "running"
    events = store.events_after(session_id, 0)
    step_states = [event["data"]["message"]["steps"][0]["status"] for event in events
                   if event["data"]["message"].get("steps")]
    assert step_states == ["running", "completed"]
    conflict = client.post(f"/api/assistant/sessions/{session_id}/messages", json={"message": "重复提交"})
    assert conflict.status_code == 409

    # 在没有前端连接的情况下放行模型，任务仍完成；随后从已有游标取回最终回复。
    model.finish.set()
    wait_for_snapshot(client, session_id, lambda value: value["messages"][-1]["status"] == "completed")
    stream = client.get(f"/api/assistant/sessions/{session_id}/events?after={progress['cursor']}")
    assert stream.headers["content-type"].startswith("text/event-stream")
    assert stream.headers["x-accel-buffering"] == "no"
    frames = [frame for frame in stream.text.split("\n\n") if "event: message" in frame]
    payloads = [json.loads(next(line[6:] for line in frame.splitlines() if line.startswith("data: "))) for frame in frames]
    assert payloads[-1]["message"]["content"] == "这本书目前有30本库存。"
    assert payloads[-1]["message"]["status"] == "completed"
    assert "event: done" in stream.text


def test_restart_marks_unfinished_turn_and_allows_followup(tmp_path):
    path = tmp_path / "sessions.sqlite3"
    store = SessionStore(path)
    session_id = store.create("alice")["id"]
    message_id, _ = store.start_turn("alice", session_id, "第一次问题")
    store.update_message(session_id, message_id, {"steps": [{"index": 1, "status": "running"}]})
    recovered = SessionStore(path)
    last = recovered.get("alice", session_id)["messages"][-1]
    assert last["status"] == "interrupted"
    assert last["steps"][0]["status"] == "interrupted"
    _next_id, history = recovered.start_turn("alice", session_id, "继续提问")
    assert history == []


def test_model_failure_is_saved_and_does_not_leave_session_locked(saved_client):
    client, _store, model = saved_client
    model.fail = True
    session_id = client.post("/api/assistant/sessions").json()["id"]
    client.post(f"/api/assistant/sessions/{session_id}/messages", json={"message": "查询库存"})
    snapshot = wait_for_snapshot(client, session_id, lambda value: value["messages"][-1]["status"] == "failed")
    assert "模型暂时不可用" in snapshot["messages"][-1]["content"]
    model.fail = False
    assert client.post(f"/api/assistant/sessions/{session_id}/messages", json={"message": "重试查询"}).status_code == 202
    wait_for_snapshot(client, session_id, lambda value: value["messages"][-1]["status"] == "completed")


def test_simultaneous_sends_reserve_only_one_turn(tmp_path):
    store = SessionStore(tmp_path / "sessions.sqlite3")
    session_id = store.create("alice")["id"]
    barrier = Barrier(2)

    def send():
        barrier.wait()
        try:
            store.start_turn("alice", session_id, "并发问题")
            return "accepted"
        except SessionBusy:
            return "busy"

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(lambda _: send(), range(2))) == ["accepted", "busy"]
    assert len(store.get("alice", session_id)["messages"]) == 2
    with pytest.raises(SessionNotFound):
        store.get("bob", session_id)


@pytest.mark.parametrize("message", ["", "   ", "x" * 2001])
def test_invalid_question_creates_no_messages(saved_client, message):
    client, _store, _model = saved_client
    session_id = client.post("/api/assistant/sessions").json()["id"]
    assert client.post(f"/api/assistant/sessions/{session_id}/messages", json={"message": message}).status_code == 422
    assert client.get(f"/api/assistant/sessions/{session_id}").json()["messages"] == []
