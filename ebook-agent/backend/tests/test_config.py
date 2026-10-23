"""配置加载的测试，重点是 .env 的查找与优先级。"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from backend.config import load_dotenv


@pytest.fixture
def env_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """写一个临时 .env，并在用例结束后清掉它注入的变量。"""

    def write(content: str) -> Path:
        path = tmp_path / ".env"
        path.write_text(content, encoding="utf-8")
        return path

    yield write

    for key in ("DOTENV_TEST_PLAIN", "DOTENV_TEST_QUOTED", "DOTENV_TEST_KEPT"):
        monkeypatch.delenv(key, raising=False)


def test_reads_plain_and_quoted_values(env_file):
    path = env_file(
        "\n".join(
            [
                "# 注释行应被忽略",
                "",
                "DOTENV_TEST_PLAIN=hello",
                'DOTENV_TEST_QUOTED="sk-quoted"',
                "export DOTENV_TEST_KEPT=exported",
            ]
        )
    )
    load_dotenv((path,))

    import os

    assert os.environ["DOTENV_TEST_PLAIN"] == "hello"
    assert os.environ["DOTENV_TEST_QUOTED"] == "sk-quoted"
    assert os.environ["DOTENV_TEST_KEPT"] == "exported", "export 前缀也要能解析"


def test_existing_environment_wins(env_file, monkeypatch):
    """命令行临时覆盖不应该被文件里的值盖掉。"""
    monkeypatch.setenv("DOTENV_TEST_PLAIN", "from-shell")
    load_dotenv((env_file("DOTENV_TEST_PLAIN=from-file"),))

    import os

    assert os.environ["DOTENV_TEST_PLAIN"] == "from-shell"


def test_missing_file_is_ignored(tmp_path: Path):
    load_dotenv((tmp_path / "不存在的.env",))


def test_lines_without_equals_are_skipped(env_file):
    load_dotenv((env_file("这不是一个键值对\n\n# 只有注释"),))


def test_dotenv_is_loaded_at_import_time(tmp_path: Path, monkeypatch):
    """.env 要在模块导入时就生效，而不是等到某处显式调用。"""
    monkeypatch.setenv("DOTENV_TEST_PLAIN", "before-reload")
    module = importlib.import_module("backend.config")
    assert module.load_dotenv is not None
    assert module.DOTENV_CANDIDATES, "必须声明 .env 的查找位置"
    assert any(path.name == ".env" for path in module.DOTENV_CANDIDATES)


# ---------------------------------------------------------------------------
# base_url 归一化
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        # 最常见的错法：把完整接口地址当成 base_url 填进来
        (
            "https://models.sjtu.edu.cn/api/v1/chat/completions",
            "https://models.sjtu.edu.cn/api/v1",
        ),
        ("https://api.deepseek.com/v1/chat/completions/", "https://api.deepseek.com/v1"),
        # 正常写法保持不变
        ("https://api.openai.com/v1", "https://api.openai.com/v1"),
        ("https://api.deepseek.com/v1/", "https://api.deepseek.com/v1"),
        # 带不带 /v1 都尊重用户，不做多余的改写
        ("https://api.deepseek.com", "https://api.deepseek.com"),
        ("http://localhost:11434/v1", "http://localhost:11434/v1"),
        ("", "https://api.openai.com/v1"),
    ],
)
def test_normalize_base_url(raw, expected):
    from backend.config import normalize_base_url

    assert normalize_base_url(raw) == expected


def test_normalize_base_url_only_strips_one_suffix():
    """重复的后缀只去一层，避免把路径吃光。"""
    from backend.config import normalize_base_url

    assert (
        normalize_base_url("https://x/v1/chat/completions/chat/completions")
        == "https://x/v1/chat/completions"
    )


def test_endpoint_is_what_the_sdk_actually_requests():
    from backend.config import LLMSettings

    settings = LLMSettings(
        base_url="https://api.deepseek.com/v1",
        api_key="k",
        model="deepseek-chat",
        timeout_seconds=1.0,
        temperature=0.0,
    )
    assert settings.endpoint == "https://api.deepseek.com/v1/chat/completions"


# ---------------------------------------------------------------------------
# 模型接口报错的解释
# ---------------------------------------------------------------------------


def test_404_points_at_base_url():
    from backend.llm import explain_http_error

    error = explain_http_error(404, "https://x/v1/chat/completions/chat/completions", "Not Found")
    assert "404" in str(error)
    assert "LLM_BASE_URL" in error.hint
    assert "/chat/completions" in error.hint


def test_401_points_at_api_key():
    from backend.llm import explain_http_error

    assert "LLM_API_KEY" in explain_http_error(401, "https://x/v1", "Unauthorized").hint
    assert "LLM_API_KEY" in explain_http_error(403, "https://x/v1", "Forbidden").hint


def test_429_and_5xx_are_not_blamed_on_config():
    from backend.llm import explain_http_error

    assert "限流" in explain_http_error(429, "https://x/v1", "Too Many Requests").hint
    assert "服务商" in explain_http_error(503, "https://x/v1", "unavailable").hint


def test_model_api_error_report_includes_hint():
    from backend.llm import ModelAPIError

    error = ModelAPIError("模型接口返回 404", "检查 LLM_BASE_URL")
    assert error.report == "模型接口返回 404（检查 LLM_BASE_URL）"
