# 互联网应用开发技术 — 迭代 2 答题说明

> **课程**：互联网应用开发技术  
> **迭代**：2（前后端贯通）  
> **文档日期**：2026-05-21  
> **项目仓库**：`EBook`（`react-ebook` + `springboot-ebook`）

本文档用于替代作业答题纸，对照《迭代 2 细则》说明：**是否符合要求**、**系统架构**、**已实现功能**、**技术细节**、**前后端联合运行方法**，以及评分要点与代码的对应关系。

---

## 目录

1. [迭代 2 符合性自查](#1-迭代-2-符合性自查)
2. [项目总体架构](#2-项目总体架构)
3. [前端工程结构与设计理由](#3-前端工程结构与设计理由)
4. [后端工程结构与设计理由](#4-后端工程结构与设计理由)
5. [数据库设计](#5-数据库设计)
6. [已实现功能清单](#6-已实现功能清单)
7. [REST API 与 JSON 约定](#7-rest-api-与-json-约定)
8. [前后端通信全流程（评分 C.ii）](#8-前后端通信全流程评分-cii)
9. [数据库访问与持久化过程（评分 A）](#9-数据库访问与持久化过程评分-a)
10. [前后端联合运行方法](#10-前后端联合运行方法)
11. [提交清单](#11-提交清单)
12. [自评与可改进点](#12-自评与可改进点)

---

## 1. 迭代 2 符合性自查

### 1.1 迭代要求（第 1 节）

| 细则条目 | 要求摘要 | 本项目实现 | 结论 |
|----------|----------|------------|------|
| **A 前端** | React + React Router + Ant Design；页面联动（加购→购物车可见，下单→订单可见） | `react-ebook` 使用 React 18、React Router 6 Data Router、Ant Design 6；加购/结算后通过 `redirect` 与 `loader` 刷新对应页面 | **符合** |
| **B 后端** | 图书列表、详情、订单列表；建议购物车/下单持久化到数据库 | `BookController`、`CartController`、`OrderController`、`UserController` 提供完整 REST API；购物车与订单写入 MySQL | **符合**（含加分项） |
| **C 通信** | Fetch 异步；展示数据来自后端；后端读 MySQL 返回 JSON | `src/api/backendApi.js` 统一 `fetch`；`appStore` 通过 API 加载书籍/购物车/订单 | **符合** |
| **D 数据访问** | Spring Data JDBC 或 JPA（已用 JPA 可不改） | `spring-boot-starter-data-jpa` + `JpaRepository` | **符合** |
| **E 总体** | 展示数据来自库；用户操作反映到库 | 书籍/购物车/订单/登录均走后端；仅登录态与封面兜底使用浏览器本地辅助数据 | **符合** |

### 1.2 评分标准对照（共 20 分）

| 评分项 | 分值 | 对应实现 | 自评 |
|--------|------|----------|------|
| **A.i** 正确连接数据库并说明流程 | 2 | `application.properties` + JPA + `schema.sql`/`data.sql` 初始化；见 [§9](#9-数据库访问与持久化过程评分-a) | 可得 |
| **A.ii** 正确使用 Repository / SQL | 2 | `BookRepository`、`CartItemRepository` 等声明式方法 + `save`/`delete` | 可得 |
| **A.iii** 实体类抽象 | 1 | `entity/Book`、`User`、`CartItem`、`OrderEntity` | 可得 |
| **B** 登录、书单、详情、加购、下单（各 1 分） | 5 | 均已实现且数据来自/写入数据库 | 可得 |
| **C.i** 异步 + 合理 JSON | 2 | Fetch + DTO 响应 | 可得 |
| **C.ii** 详述请求全链路 | 3 | 见 [§8](#8-前后端通信全流程评分-cii) | 可得 |
| **D.i** 前端结构合理 | 2 | `api` / `pages` / `components` / `data` / `routes` | 可得 |
| **D.ii** 后端分层 | 2 | Controller → Service → Repository → Entity | 可得 |
| **D.iii** 接口与实现分离 | 1 | **Repository 为 interface**（Spring Data JPA）；Service 为具体 `@Service` 类 | 基本符合* |

\* **说明（D.iii）**：数据访问层通过 `JpaRepository<T, ID>` 接口与 Hibernate 实现分离；Controller 只依赖 Service，不直接访问 Repository。Service 层未再单独抽取 Java `interface`，符合 Spring Boot 常见写法；若阅卷严格要求 Service 也做 interface，可在后续迭代补充 `BookService` 等接口，当前以 Repository 层体现“接口与实现分离”为主。

### 1.3 与细则的细微差异（答辩时可说明）

| 项目 | 说明 |
|------|------|
| `Data.json` 仍保留 | 仅用于：**封面路径按 ISBN 兜底**（数据库未存 cover 字段）、登录页 UI 默认值；**业务书籍/购物车/订单不以 JSON 为准** |
| 顶栏搜索 | 搜索词保存在前端 `appStore.searchByPage`，在 loader 返回的数据上做客户端过滤；不影响“书籍来自数据库”的评分点 |
| 登录会话 | 用户名、`userId` 存 `localStorage`；**密码校验在后端数据库**完成 |
| 密码存储 | 演示项目为明文比对（`UserService.login`），生产环境应改为哈希 |

**结论：当前作业整体满足迭代 2 要求，可按 20 分标准准备答辩与演示。**

---

## 2. 项目总体架构

```text
┌─────────────────────────────────────────────────────────────────┐
│  浏览器 (http://localhost:5173)                                  │
│  React + React Router (loader/action) + Ant Design               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐ │
│  │  pages   │→ │ appStore │→ │ backendApi│→│ fetch (JSON)     │ │
│  └──────────┘  └──────────┘  └──────────┘  └────────┬─────────┘ │
└──────────────────────────────────────────────────────│──────────┘
                                                       │ HTTP
                                                       ▼
┌─────────────────────────────────────────────────────────────────┐
│  Spring Boot (http://localhost:8080)                             │
│  ┌────────────┐  ┌────────────┐  ┌──────────────┐  ┌─────────┐ │
│  │ Controller │→ │  Service   │→ │ Repository   │→│  JPA    │ │
│  └────────────┘  └────────────┘  └──────────────┘  └────┬────┘ │
└─────────────────────────────────────────────────────────│────────┘
                                                          ▼
                                              ┌───────────────────┐
                                              │  MySQL (ebook_backend) │
                                              │  users / books /     │
                                              │  cart_items / orders │
                                              └───────────────────┘
```

**数据流原则**：

- **读**：页面 `loader` → `appStore.ensureXxxLoaded()` → `fetch` → Controller → Service → Repository → MySQL → JSON → 前端 state → UI。
- **写**：表单/按钮 → 路由 `action` → `appStore` 写函数 → `fetch`（POST/PATCH/DELETE）→ 后端持久化 → 重新 `loader` 或更新 state → UI 刷新。

---

## 3. 前端工程结构与设计理由

路径：`react-ebook/src/`

```text
src/
├── api/
│   └── backendApi.js       # Service 层：封装所有 fetch 请求
├── components/             # 可复用 UI（BookCard、DashboardLayout、ResourceTable…）
├── data/
│   ├── Data.json           # 静态辅助：封面路径映射、演示文案（非业务主数据源）
│   └── appStore.js         # 前端状态仓库：loader/action 唯一读写入口
├── pages/                  # View + 路由 loader/action（按页面模块内聚）
│   ├── LoginPage.jsx
│   ├── BooksPage.jsx
│   ├── BookDetailPage.jsx
│   ├── CartPage.jsx
│   ├── OrdersPage.jsx
│   └── UserPage.jsx
├── routes/
│   ├── Root.jsx            # 受保护布局（顶栏、侧栏、Outlet）
│   ├── authRouteHandlers.js
│   └── RouteErrorBoundary.jsx
├── App.jsx                 # 仅路由装配
├── main.jsx                # 入口 + Ant Design 样式
└── styles.css
```

| 目录/文件 | 角色（对应课堂 Component / Service / View） | 设计理由 |
|-----------|-----------------------------------------------|----------|
| `api/backendApi.js` | **Service** | 集中管理 `API_BASE_URL`、`fetch`、错误解析；页面与 store 不直接拼 URL |
| `pages/*.jsx` | **View** + 路由逻辑 | 每页自带 `loader`/`action`，符合 React Router Data API；“组件只渲染，写操作走 action” |
| `components/` | **Component** | `BookCard`、`ResourceTable` 等跨页复用，避免列表页重复布局代码 |
| `data/appStore.js` | 状态层（类似轻量 Store） | 统一缓存书籍/购物车/订单；对后端 ID（数字）做 `String` 规范化，便于 React `key` 与路由参数一致 |
| `routes/` | 路由基础设施 | 登录守卫 `requireAuthLoader`、共享 `DashboardLayout`、错误边界与 `/logout` |
| `App.jsx` | 路由表 | 只负责 `createBrowserRouter` 装配，业务不堆在入口文件 |

**技术栈版本**（见 `package.json`）：React 18.3、React Router 6.30、Ant Design 6.3、Vite 5.4。

---

## 4. 后端工程结构与设计理由

路径：`springboot-ebook/src/main/java/com/ebook/backend/`

```text
backend/
├── EbookBackendApplication.java   # 启动类
├── config/
│   └── CorsConfig.java            # 允许前端 5173 跨域访问 /api/**
├── controller/                    # 控制层：REST 入参/出参
│   ├── BookController.java
│   ├── UserController.java
│   ├── CartController.java
│   └── OrderController.java
├── service/                       # 服务层：业务规则、事务性组合
│   ├── BookService.java
│   ├── UserService.java
│   ├── CartService.java
│   └── OrderService.java
├── repository/                    # 数据访问层（Spring Data JPA 接口）
│   ├── BookRepository.java
│   ├── UserRepository.java
│   ├── CartItemRepository.java
│   └── OrderRepository.java
├── entity/                        # 实体层：与表一一映射
│   ├── Book.java
│   ├── User.java
│   ├── CartItem.java
│   └── OrderEntity.java
├── dto/                           # 请求/响应 DTO（不暴露密码等敏感字段）
├── exception/
│   ├── ResourceNotFoundException.java
│   └── ApiExceptionHandler.java   # 统一 JSON 错误响应
└── (resources)
    ├── application.properties
    ├── schema.sql                 # 建表
    └── data.sql                   # 种子数据（8 本书、演示用户、示例购物车/订单）
```

| 分层 | 职责 | 本项目示例 |
|------|------|------------|
| **Controller** | HTTP 映射、参数校验（`@Valid`）、返回 JSON | `GET /api/v1/books` → `bookService.findAll()` |
| **Service** | 业务逻辑：登录校验、加购数量上限、结算生成订单 | `CartService.checkout` 调用 `OrderService.createOrders` 并删除已结算购物车行 |
| **Repository** | 持久化 CRUD，不含 UI 逻辑 | `findByUserIdAndBookId`、`findByUserIdOrderByCreatedAtDesc` |
| **Entity** | 表结构映射 | `CartItem` ↔ `cart_items` |
| **DTO** | 对外 JSON 形状 | `UserResponse` 不含 `password`；`CartItemResponse` 只含 `bookId/qty/selected` |

---

## 5. 数据库设计

### 5.1 脚本位置（提交用）

| 文件 | 作用 |
|------|------|
| `springboot-ebook/src/main/resources/schema.sql` | `DROP` + `CREATE` 四张表 |
| `springboot-ebook/src/main/resources/data.sql` | 初始用户、**8 本书**、示例购物车与订单 |

启动时 `spring.sql.init.mode=always`，每次启动会**重建表并重新导入种子数据**（适合演示；生产应改为 `never` 或 Flyway）。

### 5.2 表结构摘要

| 表名 | 说明 | 主要字段 |
|------|------|----------|
| `users` | 用户 | `id`, `username`(唯一), `password`, `email`, `signature`, `level` |
| `books` | 书籍 | `id`, `title`, `author`, `price`, `category`, `publisher`, `isbn`, `stock_type`, `description`… |
| `cart_items` | 购物车 | `user_id`, `book_id`, `qty`, `selected`；`(user_id, book_id)` 唯一 |
| `orders` | 订单 | `order_no`(唯一), `user_id`, `book_id`, `qty`, `unit_price`, `status`, `created_at` |

外键：`cart_items`、`orders` 均引用 `users.id` 与 `books.id`。

### 5.3 演示账号与数据量

- **体验账号**：用户名 `同学A`，密码 `123456`（`data.sql` 插入，`id` 一般为 `1`）。
- **书籍**：8 本（与前端 `Data.json` 书目一致，避免联调时只显示 4 本的问题）。
- **初始购物车**（用户 1）：书 id 1 数量 1、书 id 3 数量 2。
- **初始订单**（用户 1）：2 条示例订单（`paid` / `pending`）。

---

## 6. 已实现功能清单

### 6.1 普通用户功能（评分 B，每项 1 分）

| 功能 | 前端入口 | 后端 API | 持久化 |
|------|----------|----------|--------|
| **登录** | `/login`，`loginAction` → `loginUser()` | `POST /api/v1/users/login` | 校验 `users` 表用户名密码 |
| **书籍列表** | `/books`，`booksLoader` → `ensureBooksLoaded()` | `GET /api/v1/books` | 读 `books` |
| **书籍详情** | `/books/:bookId`，`fetchAndStoreBookById` | `GET /api/v1/book/{id}` | 读 `books` |
| **加入购物车** | 列表/详情「加入购物车」→ `addToCart` | `POST /api/v1/cart/{userId}/items` | 写 `cart_items`（同书累加，上限 4） |
| **下订单** | `/cart` 结算 → `checkoutSelected` | `POST /api/v1/cart/{userId}/checkout` | 选中项 → `orders`，并删除对应 `cart_items` |

### 6.2 页面联动（评分 B + A）

| 用户操作 | 联动结果 |
|----------|----------|
| 详情页/列表页「加入购物车」 | `redirect` 到 `/cart`，`cartLoader` 从后端拉取，**立即看到新书** |
| 购物车勾选后「结算」 | `redirect` 到 `/orders`，`ordersLoader` 拉取，**新订单出现在列表** |
| 退出后重新登录 | 购物车、订单仍从数据库按 `userId` 加载（**持久化**） |

### 6.3 扩展功能（超出最低要求）

| 功能 | 说明 |
|------|------|
| 用户注册 | `POST /api/v1/users/register` |
| 用户资料修改 | `PUT /api/v1/users/{id}` |
| 购物车改数量/勾选/删除 | `PATCH` / `DELETE` 购物车项 API |
| 订单状态更新 | `PATCH /api/v1/orders/{userId}/{orderNo}`（`pending` / `paid` / `cancelled`） |

---

## 7. REST API 与 JSON 约定

基础地址：`http://localhost:8080`（可通过前端环境变量 `VITE_API_BASE_URL` 覆盖）。

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/books` | 全部图书列表 |
| GET | `/api/v1/book/{id}` | 图书详情 |
| POST | `/api/v1/users/register` | 注册 |
| POST | `/api/v1/users/login` | 登录，body: `{ "username", "password" }` |
| GET | `/api/v1/users/{id}` | 用户信息 |
| PUT | `/api/v1/users/{id}` | 更新资料 |
| GET | `/api/v1/cart/{userId}` | 购物车列表 |
| POST | `/api/v1/cart/{userId}/items` | 加购，body: `{ "bookId": 1, "qty": 1 }` |
| PATCH | `/api/v1/cart/{userId}/items/{bookId}` | 更新 `qty` / `selected` |
| DELETE | `/api/v1/cart/{userId}/items/{bookId}` | 删除一项 |
| POST | `/api/v1/cart/{userId}/checkout` | 结算选中项，返回新订单列表 |
| GET | `/api/v1/orders/{userId}` | 订单列表 |
| PATCH | `/api/v1/orders/{userId}/{orderNo}` | 更新订单状态 |

**JSON 设计要点**：

- 响应用 **DTO**（如 `UserResponse`），避免把实体密码返回前端。
- 书籍 `id`、订单 `bookId` 在后端为 **Long**；前端 `normalizeBook` 转为 **String** 统一路由与组件比较。
- 订单对外主键使用业务号 `orderNo`（映射为前端 `order.id`）。
- 错误时 `ApiExceptionHandler` 返回 `{ "message": "..." }`，`backendApi.js` 解析后展示给用户。

---

## 8. 前后端通信全流程（评分 C.ii）

以下按细则要求，分三条典型链路说明：**发出请求 → Java 处理 → 访问数据库 → 组装 JSON → 前端展示**。

### 8.1 书籍列表页加载

```text
1. 用户访问 /books（已登录）
2. booksLoader() 调用 requireAuthSnapshot()，再 await ensureBooksLoaded()
3. appStore.ensureBooksLoaded()
      → backendApi.fetchBooks()
      → fetch("GET http://localhost:8080/api/v1/books")
4. BookController.getAllBooks()
      → BookService.findAll()
      → BookRepository.findAll()  // JPA 生成 SELECT
      → MySQL 表 books
5. 返回 List<Book> 序列化为 JSON 数组
6. appStore 执行 normalizeBook()（补 cover：按 isbn 查 Data.json 映射）
7. booksLoader 将 snapshot.books 交给 BooksPage
8. BooksPage 按 search 关键词 filter 后，BookCard 网格渲染
```

### 8.2 书籍详情页「加入购物车」

```text
1. 用户在 /books/3 点击「加入购物车」（Form POST）
2. bookDetailAction：intent=add-to-cart → await addToCart("3")
3. appStore.addToCart(bookId)
      → addCartItem(userId, { bookId: 3, qty: 1 })
      → fetch POST /api/v1/cart/1/items  Body: {"bookId":3,"qty":1}
4. CartController.addItem → CartService.addToCart
      → 查 users / books 是否存在
      → cartItemRepository.findByUserIdAndBookId 或新建 CartItem
      → qty 累加（max 4），save()
      → 返回当前用户完整购物车 List<CartItemResponse>
5. appStore 更新 state.cartItems
6. throw redirect("/cart")
7. cartLoader：ensureBooksLoaded + ensureCartLoaded（GET 购物车 API）
8. CartPage 表格展示含新书的行
```

### 8.3 购物车「结算」生成订单

```text
1. 用户在 /cart 勾选商品，点击结算
2. cartAction：intent=checkout → await checkoutSelected()
3. appStore.checkoutSelected()
      → checkoutCart(userId)  // POST /api/v1/cart/{userId}/checkout
4. CartService.checkout
      → 查询 selected=true 的 cart_items
      → OrderService.createOrders：每条生成 OrderEntity（status=pending，单价来自 books.price）
      → orderRepository.saveAll()
      → cartItemRepository.deleteAll(已结算行)
5. 返回 List<OrderResponse> JSON
6. appStore：ensureCartLoaded(true) + ensureOrdersLoaded(true)
7. redirect("/orders")
8. ordersLoader → GET /api/v1/orders/{userId} → OrdersPage 展示新订单
```

### 8.4 登录（数据库校验账号）

```text
1. LoginPage 提交 username/password
2. loginAction → loginUser({ username, password })
      → POST /api/v1/users/login
3. UserService.login
      → userRepository.findByUsername
      → 比对 password 字段
      → 组装 UserResponse（含 id，不含 password）
4. setAuthenticatedUser(user)：localStorage 存 username、userId
5. redirect("/books") → 后续请求携带 userId 访问购物车/订单 API
```

---

## 9. 数据库访问与持久化过程（评分 A）

### 9.1 连接配置

文件：`springboot-ebook/src/main/resources/application.properties`

- `spring.datasource.url`：JDBC 指向 MySQL 库 `ebook_backend`（本地脚本使用端口 **3307**）。
- `spring.datasource.username` / `password`：可通过环境变量 `DB_URL`、`DB_USERNAME`、`DB_PASSWORD` 覆盖。
- `spring.jpa.hibernate.ddl-auto=none`：表结构由 `schema.sql` 管理，不由 Hibernate 自动改表。
- `spring.sql.init.mode=always`：启动执行 `schema.sql` + `data.sql`。

### 9.2 完整处理过程（答辩口述版）

1. **启动**：`EbookBackendApplication` 启动 Spring 容器。  
2. **数据源**：自动配置 `DataSource`（HikariCP 连接池）连 MySQL。  
3. **初始化 SQL**：`schema.sql` 建表，`data.sql` 插入种子数据。  
4. **JPA**：Hibernate 根据 `@Entity` 映射表结构；`@Repository` 接口由 Spring 生成实现类。  
5. **读操作**：Service 调用 `repository.findXxx()` → JPA 生成 SQL → `ResultSet` 映射为 Entity → Controller 转 JSON（或先转 DTO）。  
6. **写操作**：Service 修改 Entity 后 `repository.save()` / `delete()` → JPA 生成 `INSERT`/`UPDATE`/`DELETE`。  
7. **异常**：`ResourceNotFoundException` 等由 `ApiExceptionHandler` 转为 HTTP 4xx + JSON `message`。

### 9.3 实体与 Repository 示例

- **实体**：`Book` 类字段与 `books` 表列对应（`@Entity` + `@Table`）。  
- **Repository**：`CartItemRepository extends JpaRepository<CartItem, Long>`，并声明 `findByUserIdAndBookId` 等方法，由 Spring Data 按方法名生成查询。

---

## 10. 前后端联合运行方法

### 10.1 环境要求

| 组件 | 版本要求 |
|------|----------|
| JDK | 17+ |
| Node.js | 18+（用于 `npm`） |
| Docker Desktop | 用于 `run-local.sh` 启动 MySQL 容器 |
| Maven | 可选（脚本可自动 `mvn package`） |

### 10.2 启动后端（推荐）

```bash
cd springboot-ebook
chmod +x run-local.sh stop-local.sh
./run-local.sh
```

脚本将：

1. 若不存在则构建 `target/springboot-ebook-0.0.1-SNAPSHOT.jar`；  
2. 启动 Docker 容器 `ebook-mysql-local`（主机端口 **3307** → 容器 3306）；  
3. 以 `DB_URL=jdbc:mysql://localhost:3307/ebook_backend...`、`DB_PASSWORD=root` 启动 Spring Boot。

验证后端：

```bash
curl http://localhost:8080/api/v1/books
# 应返回 8 本书的 JSON 数组
```

停止 MySQL 容器：

```bash
cd springboot-ebook
./stop-local.sh
```

### 10.3 启动前端

**新开一个终端**：

```bash
cd react-ebook
npm install
npm run dev
```

浏览器访问终端提示地址，一般为：**http://localhost:5173**。

可选：自定义后端地址：

```bash
# react-ebook 目录下
echo 'VITE_API_BASE_URL=http://localhost:8080' > .env.local
```

### 10.4 联调演示步骤（建议按此顺序操作）

1. 确认后端 `GET /api/v1/books` 返回 **8** 条记录。  
2. 打开前端 `http://localhost:5173`，进入登录页。  
3. 点击 **「直接进入书城」** 或登录：`同学A` / `123456`。  
4. **书籍列表**应显示 8 本书（数据来自 MySQL）。  
5. 进入任意 **详情页** → **加入购物车** → 自动跳转购物车，可见对应书籍。  
6. 勾选商品 → **结算** → 跳转 **订单页**，可见新订单（`pending`）。  
7. （可选）退出登录再次登录，购物车/订单仍存在，证明 **数据库持久化**。

### 10.5 常见问题

| 现象 | 原因 | 处理 |
|------|------|------|
| 只显示 4 本书 | 旧版 `data.sql` 仅 4 条或未重启后端 | 确认 `data.sql` 有 8 条 `INSERT`，重新 `./run-local.sh` |
| 前端报跨域错误 | 后端未启动或端口不对 | 确认 8080 已监听；`CorsConfig` 已允许 `5173` |
| 登录后购物车为空 | 未带 `userId` 或用了新注册用户 | 用 `同学A` 演示账号或先加购再查看 |
| 封面不显示 | 数据库存的是书目信息，封面路径在前端 `Data.json` 按 ISBN 映射 | 属设计取舍，不影响书目与价格来自库 |

### 10.6 使用自有 MySQL（不用 Docker 脚本）

修改 `application.properties` 或启动前设置环境变量指向你的实例，并手动执行 `schema.sql`、`data.sql` 建库建表后：

```bash
cd springboot-ebook
mvn clean package -DskipTests
DB_URL='jdbc:mysql://localhost:3306/ebook_backend?...' \
DB_USERNAME=root \
DB_PASSWORD=你的密码 \
java -jar target/springboot-ebook-0.0.1-SNAPSHOT.jar
```

---

## 11. 提交清单

| 提交项 | 路径 | 注意 |
|--------|------|------|
| React 源码 | `react-ebook/` | **不要**提交 `node_modules/` |
| Spring Boot 源码 | `springboot-ebook/` | **不要**提交 `target/`、本地 `lib/` |
| 数据库 SQL | `schema.sql`、`data.sql` | 已在 `src/main/resources/` |
| 说明文档 | 本文 `ANSWER_IT2.md` | 建议与代码一并提交 |

---

## 12. 自评与可改进点

### 12.1 优势（对应高分点）

- 前后端完整贯通，购物车与订单 **落库**，满足细则 E 与 B 的联动要求。  
- 使用 **Fetch + JSON + JPA + 分层架构**，文档与代码路径清晰，便于答辩演示全链路。  
- 前端 **Data Router**（loader/action）与 `appStore` 职责分离，结构符合迭代 2 对前端工程化的要求。

### 12.2 后续可改进（不影响本次达标）

- Service 层增加 Java `interface` + `impl`，进一步强化 D.iii。  
- 密码 BCrypt 加密；登录改为 JWT 或 Session。  
- 书籍表增加 `cover_url` 字段，彻底去掉对 `Data.json` 的封面依赖。  
- 搜索改为后端分页查询 API。  
- `spring.sql.init.mode` 在生产环境改为 `never`，使用 Flyway/Liquibase 管理迁移。

---

**文档结束。** 答辩时可结合本仓库源码路径，按 [§8](#8-前后端通信全流程评分-cii) 任选「列表加载 / 加购 / 结算」一条链路现场单步说明。
