#!/usr/bin/env bash
# 启动原书城：选择 Java 21，保留已有 MySQL 数据，只初始化全新的空开发库。
set -euo pipefail
# 直接调用组件脚本时也走同一套端口清理和进程管理。
if [[ "${EBOOK_SERVICE_CHILD:-0}" != "1" ]]; then
  SERVICE_PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
  exec "$SERVICE_PROJECT_DIR/run-all.sh" --backend
fi
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$ROOT_DIR/.." && pwd)"
CONTAINER_NAME="ebook-mysql-integrated"

if [[ -n "${JAVA_HOME:-}" ]] && "$JAVA_HOME/bin/java" -version 2>&1 | head -n 1 | grep -q '"21\.'; then
  BOOKSTORE_JAVA_HOME="$JAVA_HOME"
elif [[ -d "$REPO_DIR/.tools/jdk21" ]]; then
  BOOKSTORE_JAVA_HOME="$(find "$REPO_DIR/.tools/jdk21" -path '*/Contents/Home' -type d -maxdepth 3 | head -n 1)"
else
  BOOKSTORE_JAVA_HOME="$(/usr/libexec/java_home -v 21 2>/dev/null || true)"
fi
if [[ -z "$BOOKSTORE_JAVA_HOME" ]] || ! "$BOOKSTORE_JAVA_HOME/bin/java" -version 2>&1 | head -n 1 | grep -q '"21\.'; then
  echo "请安装 JDK 21 并设置 JAVA_HOME。" >&2
  exit 1
fi
export JAVA_HOME="$BOOKSTORE_JAVA_HOME"
export PATH="$JAVA_HOME/bin:$PATH"

if [[ -z "${DB_URL:-}" ]]; then
  if ! docker info >/dev/null 2>&1; then
    echo "请先启动 Docker Desktop，或通过 DB_URL 指定现有 MySQL。" >&2
    exit 1
  fi
  if ! docker inspect "$CONTAINER_NAME" >/dev/null 2>&1; then
    docker run -d --name "$CONTAINER_NAME" -e MYSQL_ROOT_PASSWORD=root \
      -e MYSQL_DATABASE=ebook_backend -p 127.0.0.1:3307:3306 \
      -v ebook-mysql-integrated-data:/var/lib/mysql mysql:8.0 >/dev/null
  else
    docker start "$CONTAINER_NAME" >/dev/null
  fi
  for _ in $(seq 1 60); do
    if docker exec "$CONTAINER_NAME" mysqladmin ping -uroot -proot --silent >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done
  # 使用 UTF-8 导入中文书名、分类和角色；已有表时绝不运行 DROP TABLE 脚本。
  table_count="$(docker exec "$CONTAINER_NAME" mysql -uroot -proot -N -s \
    -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='ebook_backend'" 2>/dev/null)"
  if [[ "$table_count" == "0" ]]; then
    docker exec -i "$CONTAINER_NAME" mysql -uroot -proot --default-character-set=utf8mb4 ebook_backend < "$ROOT_DIR/src/main/resources/schema.sql"
    docker exec -i "$CONTAINER_NAME" mysql -uroot -proot --default-character-set=utf8mb4 ebook_backend < "$ROOT_DIR/src/main/resources/data.sql"
  fi
  mkdir -p "$REPO_DIR/.logs"
  python3 - "$REPO_DIR" <<'PYDB'
import json
from pathlib import Path
import sys
project = Path(sys.argv[1])
(project / ".logs/mysql-managed.json").write_text(json.dumps({
    "project": str(project), "container": "ebook-mysql-integrated"
}))
PYDB
  export DB_URL="jdbc:mysql://127.0.0.1:3307/ebook_backend?useUnicode=true&characterEncoding=UTF-8&serverTimezone=UTC"
  export DB_USERNAME=root
  export DB_PASSWORD=root
else
  # 外部数据库由调用者管理，不保留本项目容器的停止标记。
  rm -f "$REPO_DIR/.logs/mysql-managed.json"
fi
cd "$ROOT_DIR"
mvn -q -DskipTests package
exec "$JAVA_HOME/bin/java" -jar target/springboot-ebook-0.0.1-SNAPSHOT.jar \
  --server.address=127.0.0.1 --server.port=8080
