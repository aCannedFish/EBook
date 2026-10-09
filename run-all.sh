#!/usr/bin/env bash
# 一键启动后端服务（书城 Spring Boot + 客服助手 Python）。
#
#   ./run-all.sh                 # 起两个后端
#   ./run-all.sh --with-frontend # 连前端开发服务器一起起
#   ./run-all.sh --with-guide    # 连导购助手（作业3，8010）一起起
#   ./run-all.sh --assistant     # 只起助手
#   ./run-all.sh --bookstore     # 只起书城后端
#   ./run-all.sh --guide         # 只起导购助手
#
# 两个后端都在后台运行，日志写到 .logs/ 下，脚本打印完状态就退出。
# 停止用 ./stop-all.sh。

set -euo pipefail

cd "$(dirname "$0")"
ROOT_DIR="$(pwd)"
LOG_DIR="$ROOT_DIR/.logs"
mkdir -p "$LOG_DIR"

WITH_FRONTEND=0
START_BOOKSTORE=1
START_ASSISTANT=1
START_GUIDE=0

while [ $# -gt 0 ]; do
  case "$1" in
    --with-frontend) WITH_FRONTEND=1 ;;
    --with-guide) START_GUIDE=1 ;;
    --assistant) START_BOOKSTORE=0; START_GUIDE=0 ;;
    --bookstore) START_ASSISTANT=0; START_GUIDE=0 ;;
    --guide) START_BOOKSTORE=0; START_ASSISTANT=0; START_GUIDE=1 ;;
    -h|--help)
      sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *) echo "未知参数：$1（用 --help 看用法）" >&2; exit 1 ;;
  esac
  shift
done

wait_for() {
  local url="$1" name="$2" log="$3" seconds="${4:-180}"
  printf '等待 %s 就绪' "$name"
  for _ in $(seq 1 "$seconds"); do
    if curl -sf -o /dev/null --max-time 2 "$url"; then
      echo " —— 就绪"
      return 0
    fi
    printf '.'
    sleep 1
  done
  echo
  echo "错误：$name 在 ${seconds}s 内没有就绪，日志尾部："
  tail -n 20 "$log" | sed 's/^/    /'
  return 1
}

already_listening() {
  [ -n "$(lsof -tiTCP:"$1" -sTCP:LISTEN 2>/dev/null || true)" ]
}

if [ "$START_BOOKSTORE" = 1 ]; then
  if already_listening 8080; then
    echo "8080 已被占用，跳过书城后端（如需重启先跑 ./stop-all.sh）。"
  else
    echo "启动书城后端（8080 + Docker MySQL 3307）..."
    nohup ./springboot-ebook/run-local.sh > "$LOG_DIR/springboot.log" 2>&1 &
    echo "  日志：.logs/springboot.log"
  fi
fi

if [ "$START_ASSISTANT" = 1 ]; then
  if already_listening 8000; then
    echo "8000 已被占用，跳过客服助手（如需重启先跑 ./stop-all.sh）。"
  else
    echo "启动客服助手（8000）..."
    nohup ./python-assistant/run-local.sh > "$LOG_DIR/assistant.log" 2>&1 &
    echo "  日志：.logs/assistant.log"
  fi
fi

echo

if [ "$START_GUIDE" = 1 ]; then
  if already_listening 8010; then
    echo "8010 已被占用，跳过导购助手（如需重启先跑 ./stop-all.sh）。"
  else
    echo "启动导购助手（作业3，8010）..."
    (cd "$ROOT_DIR/作业3" && PORT=8010 nohup ./run-local.sh > "$LOG_DIR/guide.log" 2>&1 &)
    echo "  日志：.logs/guide.log"
  fi
fi

echo

if [ "$START_BOOKSTORE" = 1 ]; then
  wait_for "http://127.0.0.1:8080/api/v1/books" "书城后端" "$LOG_DIR/springboot.log"
fi
if [ "$START_ASSISTANT" = 1 ]; then
  wait_for "http://127.0.0.1:8000/api/assistant/health" "客服助手" "$LOG_DIR/assistant.log" 60
fi
if [ "$START_GUIDE" = 1 ]; then
  # 首次启动要装依赖、建政策索引（BGE 还要下模型），超时给宽一点。
  wait_for "http://127.0.0.1:8010/api/guide/health" "导购助手" "$LOG_DIR/guide.log" 300
fi

if [ "$WITH_FRONTEND" = 1 ]; then
  if already_listening 5173; then
    echo "5173 已被占用，跳过前端。"
  else
    echo "启动前端（5173）..."
    nohup npm run dev --prefix react-ebook > "$LOG_DIR/frontend.log" 2>&1 &
    echo "  日志：.logs/frontend.log"
    wait_for "http://127.0.0.1:5173" "前端" "$LOG_DIR/frontend.log" 60 || true
  fi
fi

echo
echo "就绪。浏览器打开 http://localhost:5173 （演示账号 DefaultUser / 123456）。"
echo "停止全部服务：./stop-all.sh"
