#!/usr/bin/env bash
# 停止 run-local.sh 启动的服务（默认端口 8000）。
#
#   PORT=8001 ./stop-local.sh

set -euo pipefail

PORT="${PORT:-8000}"
pids="$(lsof -tiTCP:"$PORT" -sTCP:LISTEN 2>/dev/null || true)"

if [ -z "$pids" ]; then
  echo "端口 $PORT 上没有正在运行的服务。"
  exit 0
fi

echo "停止端口 $PORT 上的进程：$pids"
# shellcheck disable=SC2086
kill $pids 2>/dev/null || true
sleep 0.5
# shellcheck disable=SC2086
kill -9 $pids 2>/dev/null || true
echo "已停止。"
