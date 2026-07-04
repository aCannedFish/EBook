# EBook 电子书城

《互联网应用开发技术》课程大作业项目：前后端分离的在线书店，支持顾客购书与管理员运营。

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React 18、React Router 6（Data Router）、Ant Design 6、Vite 5 |
| 后端 | Spring Boot 3.2、Spring Data JPA、Maven |
| 数据库 | MySQL 8 |
| 通信 | Fetch API + REST（`/api/v1/**`） |

## 功能概览

### 顾客

- 登录 / 注册（重复密码、邮箱格式、用户名唯一校验）
- 浏览书城、搜索、查看书籍详情（含库存）
- 购物车增删改、勾选结算
- 我的订单（按日期范围、书名筛选）
- 个人购书统计

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

### 环境要求

- JDK 17+
- Node.js 18+（含 npm）
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
```

