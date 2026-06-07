# 互联网应用开发技术 — 作业 5 答题说明

> **课程**：互联网应用开发技术  
> **作业**：5（Spring Data JPA + DTO 层重构）  
> **文档日期**：2026-06-04  
> **项目仓库**：`EBook/`（`react-ebook` + `springboot-ebook`）  
> **说明**：本文档替代「作业答题纸.docx」中的文字说明部分；**项目结构截图与 Postman 测试结果截图请自行粘贴到答题纸或本文档对应位置**。

---

## 目录

1. [作业 5 符合性自查](#1-作业-5-符合性自查)
2. [后端工程结构说明](#2-后端工程结构说明)
3. [Spring Data JPA 与 DTO 设计](#3-spring-data-jpa-与-dto-设计)
4. [三个核心 API（契约未变）](#4-三个核心-api契约未变)
5. [Postman 测试记录（待补充截图）](#5-postman-测试记录待补充截图)
6. [运行与验证方法](#6-运行与验证方法)
7. [评分标准自评](#7-评分标准自评)
8. [与迭代 3 的关系](#8-与迭代-3-的关系)

---

## 1. 作业 5 符合性自查

对照《作业 5》PDF（2026-06-04）要求：

| 细则 | 要求摘要 | 本项目实现 | 结论 |
|------|----------|------------|------|
| **A.i** | 采用 Spring Data JPA 重构后端 | `spring-boot-starter-data-jpa`；`UserRepository`、`BookRepository` 等继承 `JpaRepository`；Hibernate 生成 SQL | **符合** |
| **A.ii** | 增加 DTO 层，屏蔽底层数据来源 | `UserRegisterRequest` / `UserResponse`；`BookResponse`；Controller 只暴露 DTO，不直接返回 Entity（Book 作业要求范围内） | **符合** |
| **A.iii.1** | `POST /api/v1/users/register` 不变 | `UserController.register` → `UserService.register` → `UserRepository.save` | **符合** |
| **A.iii.2** | `GET /api/v1/books` 不变 | `BookController.getAllBooks` → `BookService.listAll` → `BookRepository.findAll` → `BookResponse` | **符合** |
| **A.iii.3** | `GET /api/v1/book/{id}` 不变 | `BookController.getBookById` → `BookService.getById` → `BookRepository.findById` → `BookResponse` | **符合** |
| **A.iv** | Postman / Insomnia 测试 | 见 [§5](#5-postman-测试记录待补充截图)（由本人补充截图） | **待完成截图** |
| **A.v** | 答题纸：结构说明 + Postman 截图 | 本文档 + 自行粘贴截图 | **待完成截图** |
| **B** | 可作为迭代 3 基础 | 迭代 2 已扩展购物车/订单 API；作业 5 聚焦 User/Book 的 JPA+DTO | **符合** |

**结论**：代码层面已满足作业 5 对 **User、Book 两个实体** 的 JPA 访问与 DTO 封装要求；三个核心 API 路径与 JSON 字段与作业 4 保持一致，前端无需改动。

---

## 2. 后端工程结构说明

> **【此处可粘贴 IDE 中 `springboot-ebook/src/main/java/com/ebook/backend` 包结构截图】**

```text
springboot-ebook/
├── pom.xml
├── run-local.sh / stop-local.sh
└── src/main/
    ├── java/com/ebook/backend/
    │   ├── EbookBackendApplication.java
    │   ├── config/
    │   │   └── CorsConfig.java
    │   ├── controller/          # 表现层：REST 入口，只使用 DTO
    │   │   ├── UserController.java    ← 作业5：register
    │   │   ├── BookController.java    ← 作业5：books / book/{id}
    │   │   ├── CartController.java    # 迭代2扩展
    │   │   └── OrderController.java   # 迭代2扩展
    │   ├── service/             # 业务层：Entity ↔ DTO 转换
    │   │   ├── UserService.java
    │   │   ├── BookService.java
    │   │   ├── CartService.java
    │   │   └── OrderService.java
    │   ├── repository/          # 数据访问层：Spring Data JPA 接口
    │   │   ├── UserRepository.java
    │   │   ├── BookRepository.java
    │   │   ├── CartItemRepository.java
    │   │   └── OrderRepository.java
    │   ├── entity/              # 持久化模型（JPA @Entity）
    │   │   ├── User.java
    │   │   ├── Book.java
    │   │   ├── CartItem.java
    │   │   ├── OrderEntity.java
    │   │   └── OrderItem.java
    │   ├── dto/                 # 传输模型（作业5重点）
    │   │   ├── UserRegisterRequest.java
    │   │   ├── UserResponse.java
    │   │   ├── BookResponse.java        ← 作业5新增
    │   │   └── …（购物车/订单 DTO，迭代2）
    │   └── exception/
    │       └── ApiExceptionHandler.java
    └── resources/
        ├── application.properties
        ├── schema.sql
        └── data.sql
```

**分层职责（作业 5 评分点 A）**：

| 层 | 职责 | User / Book 示例 |
|----|------|------------------|
| **Controller** | HTTP 路由、参数校验、返回 DTO | `register(@Valid UserRegisterRequest)` → `UserResponse` |
| **Service** | 业务规则、Entity ↔ DTO 转换 | `UserService.toResponse(User)`；`BookService.toResponse(Book)` |
| **Repository** | JPA 数据访问（接口，无实现类） | `userRepository.save(user)`；`bookRepository.findAll()` |
| **Entity** | 与 MySQL 表一一映射 | `User` → `users`；`Book` → `books` |
| **DTO** | 对外 API 契约，屏蔽持久化细节 | 不含 `password`；Book 不暴露 JPA 注解 |

---

## 3. Spring Data JPA 与 DTO 设计

### 3.1 JPA 依赖与配置

`pom.xml` 引入：

- `spring-boot-starter-data-jpa`（含 Hibernate）
- `mysql-connector-j`

`application.properties`：

- `spring.datasource.url` 指向 MySQL 库 `ebook_backend`
- `spring.jpa.hibernate.ddl-auto=none`（表结构由 `schema.sql` 管理）
- `spring.sql.init.mode=always`（演示环境每次启动重建种子数据）

### 3.2 User：Request DTO → Entity → Response DTO

```text
POST /api/v1/users/register
  JSON body
    → UserRegisterRequest（@Valid 校验）
    → UserService.register
         → UserRepository.findByUsername / findByEmail（JPA 派生查询）
         → new User() + userRepository.save（JPA INSERT）
         → UserResponse（不含 password）
    → 201 Created + JSON
```

关键代码位置：

- 请求 DTO：`dto/UserRegisterRequest.java`
- 响应 DTO：`dto/UserResponse.java`
- 实体：`entity/User.java`（`@Entity` `@Table(name="users")`）
- 仓储：`repository/UserRepository.java`（`extends JpaRepository<User, Long>`）

### 3.3 Book：Entity → Response DTO（作业 5 重构点）

**重构前**：`BookController` 直接返回 `Book` 实体。  
**重构后**：`BookService` 通过 `toResponse(Book)` 转为 `BookResponse`，Controller 只返回 DTO。

```text
GET /api/v1/books
  → BookService.listAll()
  → bookRepository.findAll()        // JPA
  → stream().map(this::toResponse)    // Entity → DTO
  → List<BookResponse> JSON

GET /api/v1/book/{id}
  → BookService.getById(id)
  → bookRepository.findById(id)       // JPA
  → toResponse(book) 或 404
  → BookResponse JSON
```

JSON 字段名与重构前一致（`id`, `title`, `author`, `price`, `stockType` 等），**前端 `backendApi.js` 无需修改**。

### 3.4 为何需要 DTO 层（作业 A.ii）

- **安全**：`User` 含 `password`，不能直接序列化到 JSON。
- **解耦**：API 契约与表结构分离；下学期若部分数据迁到 Redis/MongoDB，可只改 Service 组装逻辑，Controller 与前端 URL 不变。
- **演进**：订单已采用 `OrderResponse` + `OrderItemResponse`；Book 作业 5 补齐同一模式。

---

## 4. 三个核心 API（契约未变）

### 4.1 POST `/api/v1/users/register`

**功能**：注册新用户并写入 `users` 表。

**请求头**：`Content-Type: application/json`

**请求体示例**：

```json
{
  "username": "TestUser01",
  "password": "123456",
  "email": "test01@example.com",
  "signature": "热爱阅读",
  "level": "普通用户"
}
```

**成功**：`201 Created`

```json
{
  "id": 2,
  "username": "TestUser01",
  "email": "test01@example.com",
  "signature": "热爱阅读",
  "level": "普通用户"
}
```

**失败**：`400`，如用户名重复 `{ "message": "username already exists" }`

---

### 4.2 GET `/api/v1/books`

**功能**：从数据库查询全部书籍。

**成功**：`200 OK`，JSON 数组，元素为 `BookResponse` 结构。

---

### 4.3 GET `/api/v1/book/{id}`

**功能**：按主键查询单本书。

**示例**：`GET /api/v1/book/1`

**成功**：`200 OK`，单个 `BookResponse` 对象。  
**失败**：`404 Not Found`，`{ "message": "book not found: 999" }`

---

## 5. Postman 测试记录（待补充截图）

> 请使用 Postman 或 Insomnia 测试下列三项，并将 **请求界面 + 响应 Status/Body** 截图粘贴到答题纸或下方占位区。

### 5.1 测试环境

| 项 | 值 |
|----|-----|
| 后端 Base URL | `http://localhost:8080` |
| 启动方式 | `cd springboot-ebook && ./run-local.sh` |
| 数据库 | Docker MySQL 3307 / 库名 `ebook_backend` |

### 5.2 测试用例清单

| # | 方法 | URL | 预期状态码 | 验证要点 |
|---|------|-----|------------|----------|
| 1 | POST | `/api/v1/users/register` | 201 | 返回用户 id，无 password；库中可查到新用户 |
| 2 | GET | `/api/v1/books` | 200 | 返回数组，长度 ≥ 8（种子数据） |
| 3 | GET | `/api/v1/book/1` | 200 | 返回 id=1 的书目详情 |
| 4 | GET | `/api/v1/book/99999` | 404 | 返回 message 错误信息 |

### 5.3 截图占位

**（1）POST register 成功 — 201**

> 【粘贴 Postman 截图】

**（2）GET books 成功 — 200**

> 【粘贴 Postman 截图】

**（3）GET book/{id} 成功 — 200**

> 【粘贴 Postman 截图】

**（4）可选：GET book/{id} 不存在 — 404**

> 【粘贴 Postman 截图】

---

## 6. 运行与验证方法

### 6.1 仅测后端（Postman）

```bash
cd springboot-ebook
chmod +x run-local.sh
./run-local.sh
```

确认日志出现 `Tomcat started on port(s): 8080` 后，在 Postman 中访问 §4 的三个 API。

### 6.2 前后端联调（可选）

```bash
# 终端 1
cd springboot-ebook && ./run-local.sh

# 终端 2
cd react-ebook && npm run dev
```

浏览器打开 `http://localhost:5173`，登录 `DefaultUser` / `123456`，验证书城列表与详情仍正常（证明 Book DTO 重构未破坏 JSON 契约）。

---

## 7. 评分标准自评

| 评分项 | 分值 | 对应实现 | 自评 |
|--------|------|----------|------|
| **A** Spring Boot 结构合理，DTO 封装 Repository | 1.5 | Controller → Service(DTO) → Repository(JPA) → Entity；Book/User 均不直接向 API 暴露 Entity | 可得 |
| **B.1** register API 使用 JPA | 1.5 | `UserRepository.save` + 派生查询 | 可得 |
| **B.2** GET books API 使用 JPA | 1.5 | `BookRepository.findAll` + `BookResponse` | 可得 |
| **B.3** GET book/{id} API 使用 JPA | 1.5 | `BookRepository.findById` + `BookResponse` | 可得 |
| **合计** | **6** | | **6**（截图补全后提交） |

---

## 8. 与迭代 3 的关系

作业说明指出：本次作业不必独立存在，可作为**迭代 3** 的基础。

当前仓库在迭代 2 已扩展：

- 购物车 / 订单 REST API 与 MySQL 持久化
- 订单头 + 订单明细（`OrderEntity` + `OrderItem`，同一批次合并展示）
- 前端 `react-ebook` 通过 `fetch` 全链路联调

作业 5 提交的**评分范围**仍是 User/Book 三个核心 API 的 JPA + DTO；迭代 3 可在同一工程上继续扩展功能，无需另起项目。

---

## 9. 提交清单

压缩包建议结构（文件名按课程要求改为 `学号-作业5.rar`）：

```text
学号-作业5/
├── react-ebook/          # 前端工程（不含 node_modules）
├── springboot-ebook/     # 后端工程
├── ANSWER_HW5.md         # 本答题说明
├── ANSWER_IT2.md         # 迭代2说明（可选）
└── （答题纸.docx 或含截图的 PDF）
```

**注意**：勿压缩提交 `node_modules/`、`target/` 等构建产物。

---

**文档结束。** Postman 截图由本人测试后补充即可提交。
