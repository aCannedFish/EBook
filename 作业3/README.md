# 作业3

书店导购 Agent，包含政策文档加载、分块、语义 Embedding、RAG 检索和 ReAct 循环。复杂示例同时处理微服务荐书与拆封退货问题，按顺序调用 `search_book_catalog`、`query_store_policy`，打印 Thought、Action、Action Input、Observation 和最终答复。

提交包为 `524031910113-作业3.zip`，报告为 `524031910113-作业3.md`。报告、源码和运行证据按作业文档的五个评分点组织。书目与政策为课程模拟数据。

## 运行

需要 Python 3.10+。在本目录执行：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m backend.cli --offline --stats
python -m backend.cli --offline --demo
```

默认使用 `BAAI/bge-small-zh-v1.5` 生成 512 维中文语义向量，首次运行需要下载模型，后续由本地 CPU 编码。也可将 `EMBEDDING_LOCAL_MODEL` 设为已下载的模型目录。模型权重保存在 Hugging Face 缓存中，不随作业提交。

`--offline` 只选择规则对话模型，Embedding 模式由 `EMBEDDING_MODE` 单独配置。完全不下载模型的测试演示可使用：

```bash
EMBEDDING_MODE=offline RAG_MIN_SCORE=0.12 python -m backend.cli --offline --demo
```

该模式使用 TF-IDF 词法向量；正式提交日志和向量证据使用 BGE 语义 Embedding。

## 真实模型

复制 `.env.example` 为 `.env`，填入对话模型配置：

```bash
cp .env.example .env
# 编辑 LLM_BASE_URL、LLM_MODEL、LLM_API_KEY
python -m backend.cli --remote "我想买一本关于微服务的书，另外如果我买了不喜欢，拆了塑封还能退吗？"
```

对话模型支持 OpenAI 兼容接口。模型自主输出动作，循环执行工具并回填 Observation。未配置密钥时，默认用规则模型复现流程。`.env` 不进入提交包。

## HTTP

```bash
./run-local.sh
curl http://127.0.0.1:8000/api/guide/health
curl -X POST http://127.0.0.1:8000/api/guide/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"我想买一本关于微服务的书，另外拆了塑封还能退吗？"}'
```

HTTP chat 默认使用规则模型；请求中添加 `"useRemoteModel":true` 使用已配置的真实模型。policy/search 直接检索政策，tools 返回工具 Schema。服务日志和 chat 响应均保留完整执行链路。

端口可用 `PORT` 覆盖（如 `PORT=8010 ./run-local.sh`）。书城前端「导购助手」页面（`/guide`）通过 Vite 代理 `/guide-api` 调用本服务，联调时用 **8010**，避免与客服助手（`python-assistant`，8000）冲突；仓库根目录 `./run-all.sh --with-guide` 会按这个端口启动。

## 网页端

前端页面在 `react-ebook/src/pages/GuidePage.jsx`（路由 `/guide`，左侧菜单「导购助手」）。它把 `POST /api/guide/chat` 返回的 `steps` 直接渲染成聊天窗口里的推理链路：

- 每一步一张卡片：Thought、Action（工具名 + Action Input）、Observation，标注成功/失败与耗时；
- 查书目时列出书名、价格、库存与相关度；查政策时列出命中的条款号、相似度与条款原文（RAG 引用可核对）；
- 失败时显示回传给模型的 `error.hint`，「查看完整观测」可展开回填给模型的原始 JSON；
- 顶部标签显示政策库块数、向量维度与在售书目数，右上开关可在离线替身模型与真实模型之间切换（需已配置密钥）。

对应文件：`react-ebook/src/api/guideApi.js`（请求封装）、`react-ebook/src/pages/GuidePage.css`（样式），
路由与菜单接在 `App.jsx`、`components/DashboardLayout.jsx`。

## 验证

```bash
python -m pytest backend/tests -q
python scripts/collect_evidence.py
python scripts/build_submission.py
```

单元测试固定使用 TF-IDF 替身和 0.12 阈值；采集脚本使用实际 BGE 模型和 0.55 阈值，验证归一化向量、四类政策查询、五个场景及 HTTP 请求。临时服务使用独立端口并在采集结束后退出，避免混入其他作业的运行记录。阈值用于过滤弱相关结果，回答仍须检查条款条件，不能凭相似度判断政策适用。

真实模型演示脚本优先读取环境变量和本目录 `.env`，在原项目中还可复用 `python-assistant/.env`。没有密钥时记录跳过；必需验证失败会使采集脚本退出。

## 文件

| 文件 | 作用 |
|---|---|
| `data/policy.txt` | 自编的退换货与会员政策原文 |
| `backend/corpus.py`、`chunking.py` | 加载、清洗和按条款分块 |
| `backend/embedding.py`、`vector_store.py`、`rag.py` | 语义向量化、余弦检索与索引缓存 |
| `backend/catalog.py`、`tools.py` | 模拟查书与政策查询工具 |
| `backend/llm.py`、`react_format.py`、`agent.py` | 模型接口、ReAct 协议与循环 |
| `backend/cli.py`、`server.py` | 命令行与 HTTP 入口 |
| `backend/tests/` | 单元测试与回归检查 |
| `docs/policy-vectors.json`、`rag-evidence.json` | 实际分块、语义向量及检索证据 |
| `docs/remote-trace.json`、`demo-trace.json` | 真实模型和规则模型的结构化执行记录 |
| `docs/http-evidence.json`、`logs/` | HTTP 响应、测试与完整运行日志 |
| `scripts/collect_evidence.py`、`build_submission.py` | 实际采集与白名单打包 |
| `MANIFEST.json` | 提交文件、SHA-256 与五项评分要求核对 |

压缩包仅收录本作业源码、脚本、政策、报告和运行证据；排除原书城工程、其他作业、第三方依赖、Jar、模型权重、虚拟环境、运行缓存和密钥。
