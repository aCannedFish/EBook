#!/usr/bin/env bash
# 收集文档里要用的真实运行输出。
# 每个文件都是下面命令的原样输出，没有手工编辑过的内容。

set -euo pipefail

cd "$(dirname "$0")/.."
mkdir -p docs/logs

echo "==> 单元测试"
python3 -m pytest backend/tests -q 2>&1 | tail -n 15 > docs/logs/tests.txt
cat docs/logs/tests.txt

echo
echo "==> 命令行演示（五个场景）"
python3 -m backend.cli --offline --demo --json docs/demo-trace.json > docs/logs/demo.txt 2>&1
tail -n 3 docs/logs/demo.txt

echo
echo "==> 服务端日志"
if [ "${COLLECT_SERVER_LOG:-0}" = "1" ] && [ -f /tmp/assistant-server.log ]; then
  # 从真实运行中的服务里取最近一次对话的日志。
  grep -E "用户提问|TOOL CALL|回复" /tmp/assistant-server.log | tail -n 24 > docs/logs/server.log
else
  # 没在跑服务时，起一个临时服务打一次请求，把日志抓下来。
  python3 -m backend.server > /tmp/ebook-assistant-collect.log 2>&1 &
  server_pid=$!
  trap 'kill "$server_pid" 2>/dev/null || true' EXIT
  for _ in $(seq 1 40); do
    curl -sf http://127.0.0.1:8000/api/assistant/health > /dev/null && break
    sleep 0.25
  done
  curl -s -X POST http://127.0.0.1:8000/api/assistant/chat \
    -H 'Content-Type: application/json' \
    -d '{"message":"帮我查一下 ISBN为978-3-00-000000-4 的书还有多少本，顺便看看别家卖多少钱"}' \
    > /dev/null
  curl -s -X POST http://127.0.0.1:8000/api/assistant/chat \
    -H 'Content-Type: application/json' \
    -d '{"message":"ISBN为12345 的书还有多少本"}' \
    > /dev/null
  sleep 0.5
  grep -E "用户提问|TOOL CALL|回复" /tmp/ebook-assistant-collect.log | tail -n 24 > docs/logs/server.log
  kill "$server_pid" 2>/dev/null || true
fi
cat docs/logs/server.log

echo
echo "日志已写入 docs/logs/"
