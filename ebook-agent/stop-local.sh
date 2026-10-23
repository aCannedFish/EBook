#!/usr/bin/env bash
# 仅停止统一 Agent，包括 Function Calling 和 RAG/ReAct 服务。
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
exec "$ROOT_DIR/stop-all.sh" --agent
