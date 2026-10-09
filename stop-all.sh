#!/usr/bin/env bash
# 一键停止 run-all.sh 启动的服务。
#
#   ./stop-all.sh                 # 停两个后端
#   ./stop-all.sh --with-frontend # 连前端一起停

set -euo pipefail

cd "$(dirname "$0")"

WITH_FRONTEND=0
if [ "${1:-}" = "--with-frontend" ]; then
  WITH_FRONTEND=1
fi

echo "停止书城后端（8080 + MySQL 容器）..."
./springboot-ebook/stop-local.sh

echo
echo "停止客服助手（8000）..."
./python-assistant/stop-local.sh

echo
echo "停止导购助手（作业3，8010）..."
if [ -n "$(lsof -tiTCP:8010 -sTCP:LISTEN 2>/dev/null || true)" ]; then
  (cd 作业3 && PORT=8010 ./stop-local.sh)
else
  echo "端口 8010 上没有正在运行的服务。"
fi

if [ "$WITH_FRONTEND" = 1 ]; then
  echo
  echo "停止前端（5173）..."
  pids="$(lsof -tiTCP:5173 -sTCP:LISTEN 2>/dev/null || true)"
  if [ -n "$pids" ]; then
    kill $pids 2>/dev/null || true
    sleep 1
    pids="$(lsof -tiTCP:5173 -sTCP:LISTEN 2>/dev/null || true)"
    [ -n "$pids" ] && kill -9 $pids 2>/dev/null || true
  fi
  echo "前端已停止。"
fi

echo
echo "当前监听状态："
for port in 5173 8000 8010 8080 3307; do
  if [ -n "$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)" ]; then
    echo "  $port  仍被占用"
  else
    echo "  $port  空闲"
  fi
done
