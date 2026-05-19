#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
JAR_PATH="$ROOT_DIR/target/springboot-ebook-0.0.1-SNAPSHOT.jar"
CONTAINER_NAME="ebook-mysql-local"
MYSQL_PORT="3307"

if ! command -v java >/dev/null 2>&1; then
  echo "Error: Java not found. Please install JDK 17+."
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "Error: Docker not found. Please install Docker Desktop."
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "Error: Docker daemon is not running. Please start Docker Desktop first."
  exit 1
fi

if [ ! -f "$JAR_PATH" ]; then
  if command -v mvn >/dev/null 2>&1; then
    echo "Jar not found, building with Maven..."
    (cd "$ROOT_DIR" && mvn -q clean package -DskipTests)
  else
    echo "Error: $JAR_PATH not found and mvn is unavailable."
    echo "Please run 'mvn clean package' first."
    exit 1
  fi
fi

if ! docker ps --format '{{.Names}}' | grep -qx "$CONTAINER_NAME"; then
  docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
  echo "Starting MySQL container ($CONTAINER_NAME)..."
  docker run -d \
    --name "$CONTAINER_NAME" \
    -e MYSQL_ROOT_PASSWORD=root \
    -e MYSQL_DATABASE=ebook_hw4 \
    -p "$MYSQL_PORT:3306" \
    mysql:8.0 >/dev/null
fi

echo "Waiting for MySQL to be ready..."
for _ in {1..60}; do
  if docker logs "$CONTAINER_NAME" 2>&1 | grep -q "MySQL init process done. Ready for start up."; then
    break
  fi
  sleep 1
done

for _ in {1..60}; do
  if docker logs "$CONTAINER_NAME" 2>&1 | grep -q "ready for connections. Version: .* port: 3306"; then
    break
  fi
  sleep 1
done

if ! docker logs "$CONTAINER_NAME" 2>&1 | grep -q "ready for connections. Version: .* port: 3306"; then
  echo "Error: MySQL container did not become ready in time."
  exit 1
fi

echo "Starting backend at http://localhost:8080 ..."
cd "$ROOT_DIR"
DB_URL="jdbc:mysql://localhost:${MYSQL_PORT}/ebook_hw4?useUnicode=true&characterEncoding=UTF-8&serverTimezone=UTC" \
DB_USERNAME="root" \
DB_PASSWORD="root" \
java -jar "$JAR_PATH"
