#!/usr/bin/env bash
# 启动导购助手 HTTP 服务（FastAPI，默认 127.0.0.1:8000）。
#
#   PORT=8001 ./run-local.sh
#
# 不配模型密钥也能跑：未配置时使用内置的离线替身模型（功能完整、不联网）。

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
PORT="${PORT:-8000}"
HOST="${HOST:-127.0.0.1}"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Error: python3 not found. Please install Python 3.10+."
  exit 1
fi

# 端口被占用时直接退出，否则 uvicorn 会在后台 bind 失败，
# 而健康检查仍然能打通那个残留的旧进程，排查起来很绕。
existing="$(lsof -tiTCP:"$PORT" -sTCP:LISTEN 2>/dev/null || true)"
if [ -n "$existing" ]; then
  echo "Error: port $PORT is already in use by PID $existing."
  echo "请先停止它：./stop-local.sh   或换端口：PORT=8001 ./run-local.sh"
  exit 1
fi

if [ ! -d "$VENV_DIR" ]; then
  echo "Creating virtual environment (.venv)..."
  python3 -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

echo "Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r "$ROOT_DIR/requirements.txt"

env_value() {
  local key="$1"
  [ -f "$ROOT_DIR/.env" ] || return 0
  sed -n "s/^[[:space:]]*$key=//p" "$ROOT_DIR/.env" | tail -1 | tr -d '"' | tr -d "'"
}

echo
echo "导购助手服务：http://${HOST}:${PORT}"
echo "健康检查：curl http://${HOST}:${PORT}/api/guide/health"

api_key="${LLM_API_KEY:-$(env_value LLM_API_KEY)}"
if [ -z "$api_key" ]; then
  echo "未配置模型 API，将使用内置的离线替身模型（ReAct 链路完整，不联网）。"
  echo "要接真实模型：cp .env.example .env，填好 LLM_BASE_URL / LLM_API_KEY / LLM_MODEL 后重启。"
else
  echo "使用真实模型：${LLM_MODEL:-$(env_value LLM_MODEL)} @ ${LLM_BASE_URL:-$(env_value LLM_BASE_URL)}"
fi
echo "按 Ctrl+C 停止。"
echo

cd "$ROOT_DIR"
exec python -m uvicorn backend.server:app --host "$HOST" --port "$PORT"
