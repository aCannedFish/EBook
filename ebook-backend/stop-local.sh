#!/usr/bin/env bash
# 仅停止当前书城后端和本项目开发数据库，保留 MySQL 容器与数据卷。
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
exec "$ROOT_DIR/stop-all.sh" --backend
