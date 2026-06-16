#!/usr/bin/env bash
set -euo pipefail

CONTAINER_NAME="ebook-mysql-local"
BACKEND_PORT="${BACKEND_PORT:-8080}"

stop_port_listener() {
  local port="$1"
  local pids
  pids="$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)"
  if [ -n "$pids" ]; then
    echo "Stopping process(es) on port $port: $pids"
    kill $pids 2>/dev/null || true
    sleep 1
    pids="$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)"
    if [ -n "$pids" ]; then
      kill -9 $pids 2>/dev/null || true
    fi
  else
    echo "No process listening on port $port."
  fi
}

stop_port_listener "$BACKEND_PORT"

docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
echo "Stopped and removed MySQL container: $CONTAINER_NAME"
echo "Local backend stack stopped."
