#!/usr/bin/env bash
# 把主仓库里与本作业相关的源码导出到 作业2/ 下，供单独打包提交。
#
# 作业要求「勿压缩整个工程提交」，所以这里只导出本作业写的那部分：
#   - python-assistant/backend/  助手后端（含单元测试）
#   - react-ebook 里的助手界面（三个新增文件 + 对已有文件的改动 diff）
#
# 之所以用脚本导出而不是手工复制，是为了让 作业2/ 里的内容与主仓库保持一致：
# 改了主仓库的代码，重跑一次脚本即可。

set -euo pipefail

cd "$(dirname "$0")/.."
REPO_ROOT="$(cd .. && pwd)"

rm -rf backend
cp -R "$REPO_ROOT/python-assistant/backend" backend
find backend -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find backend -name ".pytest_cache" -type d -exec rm -rf {} + 2>/dev/null || true

cp "$REPO_ROOT/python-assistant/requirements.txt" requirements.txt
cp "$REPO_ROOT/python-assistant/pytest.ini" pytest.ini
cp "$REPO_ROOT/python-assistant/.env.example" .env.example
cp "$REPO_ROOT/python-assistant/run-local.sh" run-local.sh
cp "$REPO_ROOT/python-assistant/stop-local.sh" stop-local.sh
chmod +x run-local.sh stop-local.sh

mkdir -p frontend
FRONTEND_SRC="$REPO_ROOT/react-ebook/src"
cp "$FRONTEND_SRC/api/assistantApi.js"      frontend/assistantApi.js
cp "$FRONTEND_SRC/pages/AssistantPage.jsx"  frontend/AssistantPage.jsx
cp "$FRONTEND_SRC/pages/AssistantPage.css"  frontend/AssistantPage.css

# 接入前端需要改动的既有文件：注册路由、加入口、加搜索槽位、配开发代理、加 Markdown 依赖。
git -C "$REPO_ROOT" diff -- \
  react-ebook/src/App.jsx \
  react-ebook/src/components/DashboardLayout.jsx \
  react-ebook/src/data/appStore.js \
  react-ebook/vite.config.js \
  react-ebook/package.json \
  > frontend/integration.patch

echo "已从主仓库导出："
echo "  backend/  $(find backend -name '*.py' | wc -l | tr -d ' ') 个 Python 文件"
echo "  frontend/ $(ls -1 frontend | wc -l | tr -d ' ') 个文件"
