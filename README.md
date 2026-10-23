# EBook 书城

四次课程作业均集成在原书城中。React 页面访问 Spring Boot 的图书、购物车、订单和用户接口；一个 Python 客服助手通过当前用户的 JWT 读取同一份书目与库存，并在同一对话中处理库存、比价、荐书和门店政策。

## 启停

环境需要 JDK 21、Maven 3.8+、Node.js 18+、Python 3.10+、Docker Desktop 和 lsof。启动 Docker Desktop 后，在项目根目录执行：

```bash
./run-all.sh
./status-all.sh
./stop-all.sh
```

默认同时启动三个服务。启动前会清理选定端口上的残留进程，因此 5173、8080、8000 应专用于本项目。脚本等待各服务的 HTTP 接口就绪后显示地址；某个服务启动失败时会回收本次启动的进程，详细信息保存在 `.logs/`。

| 服务 | 地址 | 端口 |
|---|---|---|
| React 前端 | http://127.0.0.1:5173 | 5173 |
| 书城后端 | http://127.0.0.1:8080 | 8080 |
| Agent | http://127.0.0.1:8000 | 8000 |
| Swagger UI | http://127.0.0.1:8080/swagger-ui/index.html | 8080 |
| 开发 MySQL | 127.0.0.1:3307 | 3307 |

也可单独启动和停止某个服务：

```bash
./run-all.sh --frontend
./run-all.sh --backend
./run-all.sh --agent
./stop-all.sh --frontend
./stop-all.sh --backend
./stop-all.sh --agent
```

三个组件各自目录中的 `run-local.sh`、`stop-local.sh` 也会进入同一套管理流程。停止脚本会关闭记录的进程组、检查并释放目标端口；停止后端还会停止本项目管理的 MySQL 容器，保留容器和数据卷。重复启动相当于重启选定服务，重复停止可以安全执行。

后端脚本优先使用 `JAVA_HOME` 中的 JDK 21，其次查找 `.tools/jdk21/` 或 macOS 已安装的 JDK 21。首次构建会下载 Maven 依赖。前端缺少 `node_modules` 时执行 `npm ci`；Agent 首次建立 `.venv` 并安装 `requirements.txt`。首次加载政策向量模型时需要下载 `BAAI/bge-small-zh-v1.5`，缓存位于 `.tools/huggingface/`，后续复用本地文件。

未指定 `DB_URL` 时，后端脚本使用专属容器 `ebook-mysql-integrated`、数据卷 `ebook-mysql-integrated-data`，以 UTF-8 初始化空数据库。已有表时不会重复执行建表和演示数据脚本。需要连接自备 MySQL 时可设置 `DB_URL`、`DB_USERNAME`、`DB_PASSWORD`，停止脚本不管理外部数据库。

## 登录

演示用户为 `DefaultUser / 123456`，管理员为 `admin / admin123`。登录后，前端保存 JWT，并随业务及 Agent 请求发送 Bearer 凭证；到期或收到 401 后返回登录页。管理员可以维护图书、库存与用户，普通用户只能访问自己的购物车、订单和资料。

## 功能

| 作业 | 实现位置 | 运行入口 |
|---|---|---|
| 1 | `ebook-agent/backend/api_design.py`、`ApiDesignPage.jsx`、原书城 `BookController` | 管理员登录后打开 `/contract` |
| 2 | `ebook-agent/backend/assistant/`、`backend/tools.py`、`backend/catalog.py` | `/assistant` |
| 3 | `ebook-agent/backend/assistant/`、`backend/guide/`、`data/policy.txt` | `/assistant` |
| 4 | `ebook-backend` 中 JWT 过滤器、安全配置和虚拟线程配置 | 书城业务接口及 Swagger UI |

助手页面为 `/assistant`，左侧可以新建会话或打开历史会话。会话按登录用户保存在服务端，切页、刷新和重新登录后都可以继续；不同用户不能读取彼此的会话。页面通过 `/api/assistant/sessions` 管理会话，通过 `/{id}/messages` 提交问题，通过 `/{id}/events` 接收实时进度。`/api/assistant/chat` 保留为一次性同步问答接口。

每次模型请求都注册四个 Function Schema；Function Calling 解析动作、执行工具并回填结果，ReAct 循环记录 Thought、Action 和 Observation，直到模型给出最终答复。页面在工具开始和完成时立即更新步骤，生成任务在切页后继续，返回时会恢复已有结果。`check_inventory` 查询实际 MySQL 库存，竞品报价按作业要求模拟；`search_book_catalog` 查询同一份书目，`query_store_policy` 对政策文档进行分块、512 维 Embedding 和余弦 Top-K 检索。书目中没有的年份、评分和销量不会补造。

客服会话数据库默认为 `.local-data/assistant/sessions.sqlite3`，重启服务会保留。可通过 `ASSISTANT_SESSION_DB` 设置其他持久化路径。数据库不进入 Git 或课程源码包；服务重启前未完成的回复会标记中断，已保存的消息与步骤仍可查看。

书目接口使用 `/api/v1/books`：GET 支持 `page=0`、`size=20`、`category`、`keyword`、`isbn`；GET `/{id}` 查询详情；管理员 POST 创建返回 201 和 Location，PATCH `/{id}/stock` 更新库存。原购物车、下单、订单与统计继续使用现有业务层和数据库。

## 模型配置

将 `ebook-agent/.env.example` 复制为 `.env`，填写 OpenAI 兼容模型接口的 `LLM_BASE_URL`、`LLM_API_KEY` 和 `LLM_MODEL`，重启 Agent 即可。密钥仅用于模型网关鉴权，不会出现在报告、截图或提交包中。未配置密钥时，统一客服助手可明确切换为离线演示；接口契约生成要求真实模型。

Agent 将书目字段、工具结果和检索到的课程模拟政策发送给模型。顾客 JWT 仅转发给本机书城以校验身份、读取书目，不进入模型提示词。订单、购物车、用户资料和密码不作为模型工具数据。

## 代码结构

```text
ebook-frontend/      原 React 书城及统一客服助手页面
ebook-backend/       原 Spring Boot 书城、JWT、Java 21 虚拟线程
ebook-agent/         统一 Agent，包含 Function Calling 与 RAG/ReAct
scripts/services.py  端口清理、进程组管理、就绪检查
scripts/homework/    真实联调、截图、OpenAPI 校验与报告生成脚本
scripts/book_import/ 新增课程书目的来源记录、封面下载和种子数据导入
docs/assignments/    四次作业的正文、实际响应和浏览器截图
deliverables/        模板填写的四份报告和提交压缩包
```

实现参考课程提供的 `BookStore_s4` 分层及 Spring Security 组织方式、`course-retrieval-agent` 的检索工具设计，以及 `12 LLM Simple RAG.ipynb` 中 Embedding 列表、余弦相似度和 Top-K 检索流程。代码注释说明这些思路在现有书城中的衔接位置。

## 验证

```bash
# 先启动本项目开发数据库；测试使用单独的 ebook_integration_test 库。
cd ebook-backend
mvn test

cd ../ebook-agent
.venv/bin/python -m pytest

cd ../ebook-frontend
npm run build
```

Java 测试使用 JDK 21，覆盖 JWT 缺失、篡改、过期、越权、201/204 状态、分页与库存修改，并发送 200 个真实并发 HTTP 查询验证虚拟线程。Python 测试覆盖函数调用、异常回填、政策切分、向量检索、ReAct 解析和路由。报告中的截图由真实 Chromium 对正在运行的书城页面直接采集，原图及 SHA-256 记录位于 `docs/assignments/`。

报告生成需安装 `requirements-docs.txt`，再执行 `python scripts/homework/build_reports.py`；模板保存在 `scripts/homework/templates/作业模版.docx`。真实模型重新联调脚本会调用配置的模型 API，执行前应确认仅使用课程模拟数据。
