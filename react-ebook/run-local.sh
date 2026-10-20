#!/usr/bin/env bash
# 安装缺失的前端依赖并启动当前书城；端口管理由根目录的服务脚本负责。
set -euo pipefail
# 直接调用组件脚本时也走同一套端口清理和进程管理。
if [[ "${EBOOK_SERVICE_CHILD:-0}" != "1" ]]; then
  SERVICE_PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
  exec "$SERVICE_PROJECT_DIR/run-all.sh" --frontend
fi
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"
if [[ ! -d node_modules ]]; then
  npm ci --no-audit --no-fund
fi
exec npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
