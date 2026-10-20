#!/usr/bin/env bash
# 停止选定服务，清理进程组及端口；停止后端时保留 MySQL 持久化数据。
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
services=()
for argument in "$@"; do
  case "$argument" in
    --frontend) services+=(frontend) ;;
    --backend|--bookstore) services+=(backend) ;;
    --agent|--assistant|--guide) services+=(agent) ;;
    *) echo "用法：./stop-all.sh [--frontend|--backend|--agent]"; exit 1 ;;
  esac
done
if [[ ${#services[@]} -eq 0 ]]; then
  services=(backend agent frontend)
fi
exec python3 "$ROOT_DIR/scripts/services.py" stop "${services[@]}"
