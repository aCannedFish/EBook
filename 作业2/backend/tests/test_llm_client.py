"""模型客户端的测试。

真实模型没法在单元测试里调用，但「怎么把模型返回的 tool_calls 解析成结构化请求」
完全可以用一个假的 OpenAI 兼容服务端来覆盖 —— 这正是最容易写错、
又最不容易被发现的地方（比如把 arguments 当成 dict 而不是字符串）。
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from backend.config import LLMSettings
from backend.llm import AssistantTurn, HttpChatClient, ToolCallRequest


class _StubHandler(BaseHTTPRequestHandler):
    """按脚本返回一次 /chat/completions 响应。"""

    response_body: dict = {}
    received: dict = {}

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler 的接口
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8")
        type(self).received = json.loads(raw)

        payload = json.dumps(self.response_body, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args) -> None:  # 静音
        return


@pytest.fixture
def stub_server():
    server = HTTPServer(("127.0.0.1", 0), _StubHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server
    server.shutdown()
    server.server_close()


@pytest.fixture
def client_for(stub_server):
    def build(body: dict) -> tuple[HttpChatClient, str]:
        _StubHandler.response_body = body
        _StubHandler.received = {}
        base_url = f"http://127.0.0.1:{stub_server.server_port}/v1"
        settings = LLMSettings(
            base_url=base_url,
            api_key="test-key",
            model="stub-model",
            timeout_seconds=5.0,
            temperature=0.0,
        )
        return HttpChatClient(settings), base_url

    return build


def _completion(message: dict, finish_reason: str = "stop") -> dict:
    return {"choices": [{"index": 0, "message": message, "finish_reason": finish_reason}]}


def test_plain_text_answer(client_for):
    client, _ = client_for(_completion({"role": "assistant", "content": "还有 30 本。"}))
    turn = client.complete([{"role": "user", "content": "hi"}], [])

    assert isinstance(turn, AssistantTurn)
    assert turn.content == "还有 30 本。"
    assert turn.wants_tools is False


def test_tool_list_is_sent_to_the_model(client_for):
    """Tool 列表必须原样出现在请求体里，模型才可能返回 tool_calls。"""
    client, _ = client_for(_completion({"role": "assistant", "content": "ok"}))
    tools = [
        {
            "type": "function",
            "function": {
                "name": "check_inventory",
                "description": "查询库存",
                "parameters": {"type": "object", "properties": {"isbn": {"type": "string"}}},
            },
        }
    ]
    client.complete([{"role": "user", "content": "hi"}], tools)

    sent = _StubHandler.received
    assert sent["tools"] == tools
    assert sent["tool_choice"] == "auto"
    assert sent["model"] == "stub-model"


def test_tool_call_is_parsed_into_request(client_for):
    client, _ = client_for(
        _completion(
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_abc",
                        "type": "function",
                        "function": {
                            "name": "check_inventory",
                            "arguments": '{"isbn": "978-3-00-000000-4"}',
                        },
                    }
                ],
            },
            finish_reason="tool_calls",
        )
    )
    turn = client.complete([{"role": "user", "content": "hi"}], [])

    assert turn.wants_tools is True
    [call] = turn.tool_calls
    assert call.id == "call_abc"
    assert call.name == "check_inventory"
    assert call.arguments_raw == '{"isbn": "978-3-00-000000-4"}'

    arguments, error = call.parse_arguments()
    assert error is None
    assert arguments == {"isbn": "978-3-00-000000-4"}


def test_tool_call_with_broken_json_arguments_does_not_raise(client_for):
    client, _ = client_for(
        _completion(
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {"name": "check_inventory", "arguments": '{"isbn": '},
                    }
                ],
            },
            finish_reason="tool_calls",
        )
    )
    [call] = client.complete([{"role": "user", "content": "hi"}], []).tool_calls
    arguments, error = call.parse_arguments()
    assert arguments is None
    assert "不是合法 JSON" in error


def test_tool_call_arguments_that_are_not_an_object_are_rejected(client_for):
    client, _ = client_for(
        _completion(
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {"name": "check_inventory", "arguments": '["9783000000004"]'},
                    }
                ],
            },
            finish_reason="tool_calls",
        )
    )
    [call] = client.complete([{"role": "user", "content": "hi"}], []).tool_calls
    arguments, error = call.parse_arguments()
    assert arguments is None
    assert "必须是 JSON 对象" in error


def test_assistant_turn_is_serialized_back_into_message():
    turn = AssistantTurn(
        content="",
        tool_calls=(ToolCallRequest("call_1", "check_inventory", '{"isbn": "x"}'),),
    )
    message = turn.to_message()
    assert message["role"] == "assistant"
    assert message["content"] is None
    assert message["tool_calls"] == [
        {
            "id": "call_1",
            "type": "function",
            "function": {"name": "check_inventory", "arguments": '{"isbn": "x"}'},
        }
    ]


def test_missing_api_key_is_reported_clearly():
    from backend.llm import build_client

    settings = LLMSettings(
        base_url="https://example.invalid/v1",
        api_key="",
        model="m",
        timeout_seconds=1.0,
        temperature=0.0,
    )
    with pytest.raises(RuntimeError, match="LLM_API_KEY"):
        build_client(settings)


def test_openai_sdk_client_against_stub_server(client_for):
    """走 openai SDK 的那条路径也要验证 —— 它的响应解析与标准库实现不同。

    SDK 缺失时跳过，而不是失败：部署环境不一定装了 openai。
    """
    pytest.importorskip("openai")
    from backend.llm import OpenAICompatibleClient

    _, base_url = client_for(
        _completion(
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_sdk",
                        "type": "function",
                        "function": {
                            "name": "get_competitor_price",
                            "arguments": '{"isbn": "978-3-00-000000-4"}',
                        },
                    }
                ],
            },
            finish_reason="tool_calls",
        )
    )
    settings = LLMSettings(
        base_url=base_url,
        api_key="test-key",
        model="stub-model",
        timeout_seconds=5.0,
        temperature=0.0,
    )
    turn = OpenAICompatibleClient(settings).complete([{"role": "user", "content": "hi"}], [])

    assert turn.wants_tools is True
    [call] = turn.tool_calls
    assert call.id == "call_sdk"
    assert call.name == "get_competitor_price"
    assert call.parse_arguments()[0] == {"isbn": "978-3-00-000000-4"}
