#!/usr/bin/env bash
# 停止客服助手后端。PORT 与 run-local.sh 保持一致。

set -euo pipefail

PORT="${PORT:-8000}"

pids="$(lsof -tiTCP:"$PORT" -sTCP:LISTEN 2>/dev/null || true)"
if [ -z "$pids" ]; then
  echo "No process listening on port $PORT."
  exit 0
fi

echo "Stopping process(es) on port $PORT: $pids"
kill $pids 2>/dev/null || true
sleep 1

pids="$(lsof -tiTCP:"$PORT" -sTCP:LISTEN 2>/dev/null || true)"
if [ -n "$pids" ]; then
  kill -9 $pids 2>/dev/null || true
fi

echo "Assistant backend stopped."
