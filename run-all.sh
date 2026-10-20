#!/usr/bin/env bash
# 默认启动前端、书城后端和统一 Agent；指定参数可只启动某个服务。
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
services=()
for argument in "$@"; do
  case "$argument" in
    --frontend) services+=(frontend) ;;
    --backend|--bookstore) services+=(backend) ;;
    --agent|--assistant|--guide) services+=(agent) ;;
    --with-frontend|--with-guide) ;; # 保留旧命令兼容性，默认已包含这些服务。
    *) echo "用法：./run-all.sh [--frontend|--backend|--agent]"; exit 1 ;;
  esac
done
if [[ ${#services[@]} -eq 0 ]]; then
  services=(backend agent frontend)
fi
exec python3 "$ROOT_DIR/scripts/services.py" start "${services[@]}"
