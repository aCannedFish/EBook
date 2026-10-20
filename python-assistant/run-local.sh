#!/usr/bin/env bash
# 启动客服助手后端（FastAPI，默认 127.0.0.1:8000）。
#
# 与 springboot-ebook/run-local.sh 保持一致的使用方式：
#   首次运行会建虚拟环境并装依赖，之后直接启动。
#

set -euo pipefail
# 直接调用组件脚本时也走同一套端口清理和进程管理。
if [[ "${EBOOK_SERVICE_CHILD:-0}" != "1" ]]; then
  SERVICE_PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
  exec "$SERVICE_PROJECT_DIR/run-all.sh" --agent
fi

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
PORT=8000
HOST=127.0.0.1

if ! command -v python3 >/dev/null 2>&1; then
  echo "Error: python3 not found. Please install Python 3.10+."
  exit 1
fi

# 指定端口的旧进程由 scripts/services.py 在启动前清理。
if [ ! -d "$VENV_DIR" ]; then
  echo "Creating virtual environment (.venv)..."
  python3 -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

echo "Installing dependencies..."
python -m pip install --disable-pip-version-check -q -r "$ROOT_DIR/requirements.txt"

# 从 .env 里读一个键，仅用于启动时把配置打印出来。
# 真正生效的是 backend/config.py 里的 load_dotenv，这里不参与配置加载。
env_value() {
  local key="$1"
  [ -f "$ROOT_DIR/.env" ] || return 0
  sed -n "s/^[[:space:]]*$key=//p" "$ROOT_DIR/.env" | tail -1 | tr -d '"' | tr -d "'"
}

echo
echo "Bookstore AI backend: http://${HOST}:${PORT}"
echo "健康检查：curl http://${HOST}:${PORT}/api/assistant/health"

api_key="${LLM_API_KEY:-$(env_value LLM_API_KEY)}"
if [ -z "$api_key" ]; then
  echo "未配置模型 API，将使用内置的离线替身模型（功能完整，不联网）。"
  echo "要接真实模型：cp .env.example .env，填好 LLM_BASE_URL / LLM_API_KEY / LLM_MODEL 后重启。"
else
  echo "使用真实模型：${LLM_MODEL:-$(env_value LLM_MODEL)} @ ${LLM_BASE_URL:-$(env_value LLM_BASE_URL)}"
fi
echo "按 Ctrl+C 停止。"
echo

export BOOKSTORE_API_BASE="${BOOKSTORE_API_BASE:-http://127.0.0.1:8080}"
export HF_HOME="${HF_HOME:-$ROOT_DIR/../.tools/huggingface}"
export EMBEDDING_MODE="${EMBEDDING_MODE:-local}"
export RAG_MIN_SCORE="${RAG_MIN_SCORE:-0.55}"
cd "$ROOT_DIR"
exec python -m uvicorn backend.server:app --host "$HOST" --port "$PORT"
