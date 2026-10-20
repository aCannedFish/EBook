# 书城 Agent

本目录是 EBook 的统一 Python 服务，默认监听 http://127.0.0.1:8000，同时提供库存客服和政策导购。React 书城的 `/assistant` 和 `/guide` 页面调用该服务，并使用同一份登录 JWT 读取 Spring Boot 书目，数据库由原书城维护。

## 启停

在项目根目录执行 `./run-all.sh` 启动完整书城。单独管理 Agent 可以运行根目录的 `./run-all.sh --agent`、`./stop-all.sh --agent`，也可以在本目录执行 `./run-local.sh`、`./stop-local.sh`。这些入口共用端口清理和进程管理，日志为根目录 `.logs/ai-server.log`。

首次启动会创建 Python 3.10+ 虚拟环境并安装依赖。先启动书城后端，再登录 React 页面进行对话。Agent 不保存用户密码，不用固定管理员 Token 代替当前顾客。

## 配置

复制 `.env.example` 为 `.env`，设置 `LLM_BASE_URL`、`LLM_API_KEY`、`LLM_MODEL` 后重启。报告中的真实联调使用已配置的模型 API；没有密钥时可以使用界面明确标记的离线演示。接口设计页面始终要求真实模型。

`BOOKSTORE_API_BASE` 默认为 `http://127.0.0.1:8080`。政策编码器默认为 `BAAI/bge-small-zh-v1.5`，生成 512 维归一化向量，首次运行下载至项目 `.tools/huggingface/`；索引缓存位于本目录 `.index/`。政策文本、分块参数或编码器变化时会重建缓存。

## 实现

| 模块 | 作用 |
|---|---|
| `backend/agent.py` | 配置 Function Schema，解析 tool_calls，执行工具并回填 role=tool |
| `backend/tools.py` | `check_inventory` 和模拟 `get_competitor_price`，统一异常及重试提示 |
| `backend/catalog.py` | 转发当前用户 JWT，从原书城读取书目和实时库存 |
| `backend/guide/corpus.py` | 加载、清洗政策并按条款和长度切分 |
| `backend/guide/embedding.py`、`rag.py` | 文档与查询向量化、余弦相似度和 Top-K 政策检索 |
| `backend/guide/agent.py`、`react_format.py` | 解析 Thought、Action、Action Input，执行工具并追加 Observation |
| `backend/api_design.py` | 真实模型生成 OpenAPI JSON，验证格式与现有书城接口是否一致 |
| `backend/server.py` | 同一个 FastAPI 应用承载上述接口，验证调用者身份并建立请求范围的工具 |

政策见 `data/policy.txt`，属于课程模拟数据。查书工具只返回书城真实字段，不补造年份、评分和销量。库存来自本机数据库，竞品报价按要求模拟；超时演示书目 `9787000000008` 第一次比价失败，模型根据工具提示再次调用后成功。

## 接口

| 方法与路径 | 用途 |
|---|---|
| GET `/api/assistant/health` | 模型及服务状态 |
| POST `/api/assistant/chat` | 库存客服，返回自然语言答复与实际 toolCalls |
| GET `/api/guide/health` | 政策分块、向量维数和书目状态 |
| POST `/api/guide/policy/search` | 直接测试政策检索 |
| POST `/api/guide/chat` | ReAct 导购，返回完整 steps 和最终答复 |
| GET `/api/design/conversation` | 管理员读取已保存的真实接口设计对话 |
| POST `/api/design/chat` | 管理员调用真实模型生成契约 |

对话、导购和接口设计操作需要 `Authorization: Bearer <JWT>`；JWT 来自原书城 `/api/v1/users/login`。凭证只用于本机书城鉴权，不进入模型消息。对话上下文只接受用户和助手消息，库存和政策工具由服务端执行。

## 测试

在本目录执行 `.venv/bin/python -m pytest`。测试使用独立夹具及临时本机 HTTP 服务，不调用真实模型网关。真实联调响应、原始截图与模板报告见项目根目录的 `docs/assignments/` 和 `deliverables/`。
