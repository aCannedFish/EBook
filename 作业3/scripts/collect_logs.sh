#!/usr/bin/env bash
# 从当前源码重新采集必需证据；Python 入口会校验结果并回收临时服务。
set -euo pipefail
cd "$(dirname "$0")/.."
PYTHON="${PYTHON:-python3}"
exec "$PYTHON" scripts/collect_evidence.py
