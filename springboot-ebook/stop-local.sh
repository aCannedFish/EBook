#!/usr/bin/env bash
set -euo pipefail

CONTAINER_NAME="ebook-mysql-local"

docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
echo "Stopped and removed MySQL container: $CONTAINER_NAME"
