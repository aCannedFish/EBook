# EBook 电子书城

《互联网应用开发技术》课程大作业项目：前后端分离的在线书店，支持顾客购书与管理员运营。

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React 18、React Router 6（Data Router）、Ant Design 6、Vite 5 |
| 后端 | Spring Boot 3.2、Spring Data JPA、Maven |
| 数据库 | MySQL 8 |
| 通信 | Fetch API + REST（`/api/v1/**`） |
| 客服助手 | Python 3.10+、FastAPI、大模型 Function Calling（`python-assistant/`） |
| 导购助手 | Python 3.10+、FastAPI、RAG（政策库检索）+ ReAct（`作业3/`） |

## 功能概览

### 顾客

- 登录 / 注册（重复密码、邮箱格式、用户名唯一校验）
- 浏览书城、搜索、查看书籍详情（含库存）
- 购物车增删改、勾选结算
- 我的订单（按日期范围、书名筛选）
- 个人购书统计
- 客服助手：用自然语言问某本书还有多少本、别家卖多少钱，由大模型调用后端 Skill 查询
- 导购助手：按主题荐书并解答退换货与会员政策，页面上完整展示 Thought → Action → Observation 推理链路

### 管理员

- 用户管理：禁用 / 解禁账号
- 书籍管理：增删改查、库存维护
- 全部订单查询与筛选
- 数据统计：热销榜、消费榜

管理员与顾客登录后侧栏菜单不同，由后端返回的 `level` / `admin` 字段驱动。

## 演示账号

| 角色 | 用户名 | 密码 |
|------|--------|------|
| 管理员 | `admin` | `admin123` |
| 顾客 | `DefaultUser` | `123456` |

## 快速启动

### 一键启动（推荐）

```bash
chmod +x run-all.sh stop-all.sh
./run-all.sh                 # 起书城后端（8080 + MySQL）与客服助手（8000）
./run-all.sh --with-frontend # 连前端（5173）一起起
./run-all.sh --with-guide    # 连导购助手（8010）一起起
./stop-all.sh                # 停止
```

后端在后台运行，日志写在 `.logs/` 下。脚本会等到各自健康检查通过才返回。
只想起其中一个用 `--bookstore`、`--assistant` 或 `--guide`。

导购助手（作业3）默认不在 `./run-all.sh` 里启动：它首次运行要装 `sentence-transformers`
并下载 BGE 中文模型，起得比另外两个慢。要看「导购助手」页面就加 `--with-guide`。

下面是分开手动启动的方式。

### 环境要求

- JDK 17+
- Node.js 18+（含 npm）
- Python 3.10+（客服助手后端）
- Docker Desktop（用于一键脚本启动 MySQL）
- Maven 3.8+（或依赖脚本自动构建）

### 1. 启动后端

```bash
cd springboot-ebook
chmod +x run-local.sh stop-local.sh
./run-local.sh
```

脚本会：

1. 若无 jar 则执行 `mvn clean package`
2. 启动 Docker MySQL 容器（端口 **3307**，库名 `ebook_backend`）
3. 在 **8080** 端口启动 Spring Boot

停止服务：

```bash
./stop-local.sh
```

会释放 8080 端口并移除 MySQL 容器。

### 2. 启动前端

```bash
cd react-ebook
npm install
npm run dev
```

浏览器访问 `http://localhost:5173`。前端默认请求 `http://localhost:8080`，可通过环境变量覆盖：

```bash
VITE_API_BASE_URL=http://localhost:8080 npm run dev
```

### 3. 启动客服助手后端（可选）

「客服助手」页面依赖一个独立的 Python 服务。不用这个页面的话可以跳过。

```bash
cd python-assistant
chmod +x run-local.sh stop-local.sh
./run-local.sh
```

首次运行会建 `.venv` 并安装依赖，之后监听 **8000**。未配置模型 API 时使用内置的
离线替身模型，功能完整、不联网。

要接真实模型，把配置写进 `python-assistant/.env`：

```bash
cd python-assistant && cp .env.example .env   # 填 LLM_BASE_URL / LLM_MODEL / LLM_API_KEY
```

任何 OpenAI 兼容接口都行（OpenAI / DeepSeek / 通义千问），`.env.example` 里给了三家的现成写法。
环境变量优先于 `.env`，临时换模型可以 `LLM_MODEL=gpt-4o ./run-local.sh`。
完整变量表见 [python-assistant/README.md](python-assistant/README.md)。

停止：

```bash
cd python-assistant && ./stop-local.sh
```

前端通过 Vite 代理的同源路径 `/assistant-api` 访问它（见 `react-ebook/vite.config.js`），
所以开发时不涉及跨域。

### 4. 启动导购助手后端（可选）

「导购助手」页面（`/guide`）依赖作业3 的 RAG + ReAct 服务。它单独占一个端口，
这样能和客服助手同时跑，两个页面也就能同时演示：

```bash
cd 作业3
chmod +x run-local.sh stop-local.sh
PORT=8010 ./run-local.sh          # 监听 8010
```

首次运行会建 `.venv`、安装依赖并下载 BGE 中文向量模型（约 100 MB）。
未配置模型 API 时，对话部分使用内置的离线替身模型，ReAct 链路完整、不联网。

要接真实模型，把配置写进 `作业3/.env`（字段说明见 `作业3/.env.example`）：

```bash
cd 作业3 && cp .env.example .env   # 填 LLM_BASE_URL / LLM_MODEL / LLM_API_KEY
```

前端通过 Vite 代理的同源路径 `/guide-api` 访问它。停止：

```bash
cd 作业3 && PORT=8010 ./stop-local.sh
```

### 手动启动后端（可选）

若已有 MySQL，可设置环境变量后直接运行：

```bash
cd springboot-ebook
mvn spring-boot:run
```

常用变量（见 `application.properties`）：

| 变量 | 默认值 |
|------|--------|
| `DB_URL` | `jdbc:mysql://localhost:3306/ebook_backend?...` |
| `DB_USERNAME` | `root` |
| `DB_PASSWORD` | （见本地配置） |

> 每次启动会执行 `schema.sql` + `data.sql` 重建演示数据（`spring.sql.init.mode=always`）。

## 仓库结构

```text
EBook/
├── react-ebook/                 # 前端
│   ├── src/
│   │   ├── pages/               # 页面 + loader/action（View 层）
│   │   ├── components/          # 可复用 UI 组件
│   │   ├── api/                 # 后端 API 封装（Service 层）
│   │   ├── data/                # appStore 状态仓库、Data.json
│   │   ├── routes/              # 鉴权、布局、错误边界
│   │   └── utils/               # 角色、校验、封面路径、格式化
│   └── public/assets/           # 书籍封面等静态资源
│
└── springboot-ebook/            # 后端
    ├── src/main/java/com/ebook/backend/
    │   ├── controller/          # REST 控制器
    │   ├── service/             # 业务接口
    │   ├── service/impl/        # 业务实现（Spring 注入）
    │   ├── service/support/     # 权限、库存等辅助类
    │   ├── repository/          # Spring Data JPA
    │   ├── entity/              # JPA 实体
    │   └── dto/                 # 请求/响应 DTO
    ├── src/main/resources/
    │   ├── schema.sql           # 表结构
    │   ├── data.sql             # 演示数据
    │   └── application.properties
    ├── run-local.sh
    └── stop-local.sh

└── python-assistant/           # 客服助手后端（Python）
    ├── backend/
    │   ├── tools.py            # check_inventory / get_competitor_price 两个 Skill
    │   ├── catalog.py          # 库存数据源（内置模拟目录 / 真实后端）
    │   ├── llm.py              # 模型客户端 + 离线替身模型
    │   ├── agent.py            # Function Calling 循环与异常处理
    │   ├── server.py           # FastAPI 接口
    │   ├── cli.py              # 命令行入口与演示场景
    │   └── tests/              # 单元测试
    ├── requirements.txt
    ├── run-local.sh
    └── stop-local.sh

└── 作业3/                      # 导购助手（RAG + ReAct，独立服务，默认 8010）
    ├── data/policy.txt         # 退换货与会员政策知识库原文
    ├── backend/                # 加载 → 分块 → 向量化 → 检索 + ReAct 循环
    └── run-local.sh
```

## 主要路由

| 路径 | 说明 |
|------|------|
| `/login` | 登录 / 注册 |
| `/books` | 书城列表 |
| `/books/:bookId` | 书籍详情 |
| `/cart` | 购物车 |
| `/orders` | 我的订单 |
| `/stats` | 购书统计 / 数据统计 |
| `/assistant` | 客服助手（对话式库存与比价查询） |
| `/guide` | 导购助手（荐书 + 政策问答，展示 ReAct 推理链路） |
| `/user` | 用户资料 |
| `/admin/books` | 书籍管理（管理员） |
| `/admin/users` | 用户管理（管理员） |
| `/admin/orders` | 全部订单（管理员） |

## API 摘要

前缀：`/api/v1`

| 模块 | 代表接口 |
|------|----------|
| 用户 | `POST /users/login`、`POST /users/register`、`PUT /users/admin/{id}/enabled` |
| 图书 | `GET /books`、`GET /book/{id}`、`POST/PUT/DELETE /books` |
| 购物车 | `GET/POST/PATCH/DELETE /cart/{userId}/...`、`POST /cart/{userId}/checkout` |
| 订单 | `GET /orders/{userId}`、`GET /orders/admin/all`、`PATCH /orders/{userId}/{orderNo}` |
| 统计 | `GET /stats/admin/book-sales`、`GET /stats/admin/user-spending`、`GET /stats/my/{userId}` |

客服助手是独立服务，前缀 `/api/assistant`（默认 `http://localhost:8000`）：

| 接口 | 说明 |
|---|---|
| `POST /api/assistant/chat` | 一次问答，返回回复与本次触发的全部函数调用 |
| `GET /api/assistant/tools` | 当前交给大模型的 Tool 列表 |
| `GET /api/assistant/health` | 健康检查与当前模型模式 |

导购助手（作业3）也是独立服务，前缀 `/api/guide`（默认 `http://localhost:8010`）：

| 接口 | 说明 |
|---|---|
| `POST /api/guide/chat` | 一次 ReAct 问答，返回回复与每一步的 Thought / Action / Observation |
| `POST /api/guide/policy/search` | 只跑 RAG 检索，返回命中的政策条款、条款号与相似度 |
| `GET /api/guide/tools` | 当前交给模型的 Tool 列表 |
| `GET /api/guide/health` | 健康检查、索引规模与向量化实现 |

两个助手页都通过 Vite 代理访问各自服务（`/assistant-api` → 8000，`/guide-api` → 8010），
所以开发时不涉及跨域。生产构建默认直连本机端口，部署到别的地址时用
`VITE_ASSISTANT_API_BASE_URL` / `VITE_GUIDE_API_BASE_URL` 覆盖。

管理员写操作需在 Query 中传 `operatorId`（当前登录用户 id）。

## 架构要点

**前端**

- React Router Data API：`loader` 读数据、`action` 写数据，页面组件只负责展示
- `appStore.js` 作为前端内存仓库，统一对接 `backendApi.js`
- `DashboardLayout` 在受保护父路由中共享，顶栏搜索通过各页 `handle.searchPlaceholder` 配置

**后端**

- Controller → Service（接口）→ ServiceImpl → Repository → Entity
- 对外只返回 DTO，不暴露 Entity 与密码字段
- 订单头 `OrderEntity` 与明细 `OrderItem` 使用 `@OneToMany(cascade = ALL)` 级联保存
- 结算时 `@Transactional` 扣减 `stock_qty` 并清空购物车已选行

**数据库表**

`users`、`books`、`cart_items`、`orders`、`order_items`

## 构建与测试

```bash
# 前端生产构建
cd react-ebook && npm run build

# 后端编译与测试
cd springboot-ebook && mvn test

# 客服助手测试
python3 -m pytest python-assistant/backend/tests -q

# 导购助手（作业3）测试
cd 作业3 && .venv/bin/python -m pytest backend/tests -q
```

