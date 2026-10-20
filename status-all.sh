#!/usr/bin/env bash
# 显示三个固定端口的当前状态和访问地址。
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$ROOT_DIR/scripts/services.py" status
