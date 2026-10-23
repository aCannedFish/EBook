# 书城 Agent

本目录是 EBook 的统一 Python 服务，默认监听 http://127.0.0.1:8000。React 书城只有一个客服助手入口 `/assistant`；用户可以在同一对话里查询库存、比较价格、寻找图书和询问政策。助手使用当前用户的 JWT 读取 Spring Boot 书目，数据库由原书城维护。

## 启停

在项目根目录执行 `./run-all.sh` 启动完整书城。单独管理 Agent 可以运行根目录的 `./run-all.sh --agent`、`./stop-all.sh --agent`，也可以在本目录执行 `./run-local.sh`、`./stop-local.sh`。这些入口共用端口清理和进程管理，日志为根目录 `.logs/ai-server.log`。

首次启动会创建 Python 3.10+ 虚拟环境并安装依赖。先启动书城后端，再登录 React 页面进行对话。Agent 不保存用户密码，不用固定管理员 Token 代替当前顾客。

## 配置

复制 `.env.example` 为 `.env`，设置 `LLM_BASE_URL`、`LLM_API_KEY`、`LLM_MODEL` 后重启。报告中的真实联调使用已配置的模型 API；没有密钥时可以使用界面明确标记的离线演示。接口设计页面始终要求真实模型。

`BOOKSTORE_API_BASE` 默认为 `http://127.0.0.1:8080`。政策编码器默认为 `BAAI/bge-small-zh-v1.5`，生成 512 维归一化向量，首次运行下载至项目 `.tools/huggingface/`；索引缓存位于本目录 `.index/`。政策文本、分块参数或编码器变化时会重建缓存。

## 实现

| 模块 | 作用 |
|---|---|
| `backend/assistant/agent.py` | 在 ReAct 循环中解析 Function Calling；把模型理由记为 Thought、函数调用记为 Action、工具结果记为 Observation |
| `backend/assistant/tools.py` | 合并四种 Function Schema 与统一工具注册、派发 |
| `backend/assistant/sessions.py` | 按用户保存会话、消息和可重放事件，同一会话串行处理问题 |
| `backend/assistant/prompt.py`、`offline.py` | 统一模型提示词与离线替身 |
| `backend/tools.py` | `check_inventory`、模拟 `get_competitor_price`，统一异常及重试提示 |
| `backend/catalog.py` | 转发当前用户 JWT，从原书城读取书目和实时库存 |
| `backend/guide/corpus.py` | 加载、清洗政策并按条款和长度切分 |
| `backend/guide/embedding.py`、`rag.py` | 文档与查询向量化、余弦相似度和 Top-K 政策检索 |
| `backend/guide/react_format.py` | ReAct 文本格式工具；统一 Agent 复用其中的观测截断函数 |
| `backend/api_design.py` | 真实模型生成 OpenAPI JSON，验证格式与现有书城接口是否一致 |
| `backend/server.py` | 同一个 FastAPI 应用承载上述接口，验证调用者身份并建立请求范围的工具 |

政策见 `data/policy.txt`，属于课程模拟数据。查书工具只返回书城真实字段，不补造年份、评分和销量。库存来自本机数据库，竞品报价按要求模拟；超时演示书目 `9787000000008` 第一次比价失败，模型根据工具提示再次调用后成功。

## 接口

| 方法与路径 | 用途 |
|---|---|
| GET `/api/assistant/health` | 模型状态与四个可用工具 |
| GET `/api/assistant/tools` | 四个 Function Schema |
| POST `/api/assistant/chat` | 一次性同步问答，返回答复和完整步骤 |
| GET `/api/assistant/sessions` | 当前用户的历史会话列表 |
| POST `/api/assistant/sessions` | 新建会话，返回201 |
| GET `/api/assistant/sessions/{id}` | 读取消息、步骤及事件游标 |
| POST `/api/assistant/sessions/{id}/messages` | 保存问题并启动后台问答，立即返回202与当前快照 |
| GET `/api/assistant/sessions/{id}/events?after={cursor}` | SSE 逐步推送模型等待、工具开始、工具结果及最终答复，支持按游标补齐 |
| GET `/api/design/conversation` | 管理员读取已保存的真实接口设计对话 |
| POST `/api/design/chat` | 管理员调用真实模型生成契约 |

客服对话和接口设计操作需要 `Authorization: Bearer <JWT>`；JWT 来自原书城 `/api/v1/users/login`。凭证只用于本机书城鉴权，不进入模型消息。对话上下文只接受用户和助手消息，库存、书目和政策工具由服务端执行。助手每次将四个工具 Schema 一起交给模型；用户同时问库存、荐书和政策时，Agent 根据模型工具调用逐步处理，并把每次工具结果回填上下文。

React 客服页面使用会话接口。用户身份从书城校验结果中取得，服务端读取最近六轮已完成的问答作为上下文；客户端不能指定其他用户或伪造会话历史。同一会话生成期间再次发送问题返回409，其他用户访问返回404。关闭页面只断开订阅，后台任务继续；重新打开会话时先读取快照，再从游标订阅后续事件。

会话默认存放在项目根目录 `.local-data/assistant/sessions.sqlite3`，可通过 `ASSISTANT_SESSION_DB` 改变路径。SQLite 的消息更新与事件记录使用同一个事务，JWT、密码和模型密钥不会存入会话库。重启保留历史，未完成的回复会标记中断；该数据库不随源码打包。

## 测试

在本目录执行 `.venv/bin/python -m pytest`。测试使用独立夹具及临时本机 HTTP 服务，不调用真实模型网关。真实联调响应、原始截图与模板报告见项目根目录的 `docs/assignments/` 和 `deliverables/`。
