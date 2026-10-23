#!/usr/bin/env bash
# 仅停止当前书城前端。
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
exec "$ROOT_DIR/stop-all.sh" --frontend
