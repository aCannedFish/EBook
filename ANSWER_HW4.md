# 互联网应用开发技术 - 作业 4（迭代 2）答题说明

> 按作业要求，本文件替代“作业答题纸.docx”用于说明项目结构与 API 测试结果。

---

## 1. 后端工程说明

本次新增后端工程目录：

- `springboot-ebook/`

采用 Spring Boot + Spring Data JPA + MySQL，分层结构如下：

```text
springboot-ebook/
├── pom.xml
├── src/main/java/com/ebook/backend/
│   ├── EbookBackendApplication.java        # 启动类
│   ├── config/
│   │   └── CorsConfig.java                 # 允许前端 localhost:5173 跨域访问
│   ├── controller/
│   │   ├── UserController.java             # 用户注册 API
│   │   └── BookController.java             # 书籍查询 API
│   ├── service/
│   │   ├── UserService.java                # 用户业务逻辑
│   │   └── BookService.java                # 书籍业务逻辑
│   ├── repository/
│   │   ├── UserRepository.java             # 用户数据访问
│   │   └── BookRepository.java             # 书籍数据访问
│   ├── entity/
│   │   ├── User.java                       # 用户实体
│   │   └── Book.java                       # 书籍实体
│   ├── dto/
│   │   ├── UserRegisterRequest.java        # 注册请求 DTO
│   │   └── UserResponse.java               # 注册响应 DTO
│   └── exception/
│       ├── ResourceNotFoundException.java
│       └── ApiExceptionHandler.java        # 统一异常处理
└── src/main/resources/
    ├── application.properties              # MySQL 连接配置
    ├── schema.sql                          # 建表脚本（users, books）
    └── data.sql                            # 样例初始化数据
```

分层说明：

1. `controller`：只处理 HTTP 入参/出参与路由映射
2. `service`：承载核心业务逻辑（校验、查询、转换）
3. `repository`：JPA 数据访问层
4. `entity`：数据库实体映射
5. `dto`：输入输出模型（避免直接暴露实体中的敏感字段）

---

## 2. MySQL 配置与脚本

`application.properties` 使用 MySQL：

- `spring.datasource.url`
- `spring.datasource.username`
- `spring.datasource.password`
- `spring.datasource.driver-class-name`

并启用：

- `spring.sql.init.mode=always`

启动时自动执行：

- `schema.sql`（建表）
- `data.sql`（初始化样例数据）

---

## 3. 已实现 API（作业要求 A.iii）

### 3.1 POST `/api/v1/users/register`

功能：注册用户并写入数据库 `users` 表。

请求示例：

```json
{
  "username": "student_b",
  "password": "12345678",
  "email": "student_b@example.com",
  "signature": "热爱阅读与编程",
  "level": "普通用户"
}
```

成功响应：`201 Created`，返回注册用户信息（不返回密码）。

---

### 3.2 GET `/api/v1/books`

功能：查询数据库中全部书籍列表（`books` 表）。

成功响应：`200 OK`，返回数组。

---

### 3.3 GET `/api/v1/book/{id}`

功能：按书籍 ID 查询单本书详情。

成功响应：`200 OK`，返回单个书籍对象。  
不存在时：`404 Not Found`。

---

## 4. Postman/Insomnia 测试说明

按要求使用 API 测试工具进行验证 ：

1. `POST /api/v1/users/register`
   - 新用户注册成功，状态码 `201`
   - 数据已写入 `users` 表
   - 重复用户名或邮箱会返回 `400`

2. `GET /api/v1/books`
   - 正常返回书籍列表，状态码 `200`
   - 数据来源于数据库（`books` 表）

3. `GET /api/v1/book/{id}`
   - 存在 ID 返回书籍详情，状态码 `200`
   - 不存在 ID 返回错误信息，状态码 `404`

---

## 5. 与前端工程集成说明

为便于与 `react-ebook` 前端联调，后端已配置：

- `CorsConfig` 允许 `http://localhost:5173` 访问 `/api/**`

前后端本地联调方式：

1. 启动 MySQL 并创建数据库（默认 `ebook_backend`）
2. 启动后端 `springboot-ebook`
3. 启动前端 `react-ebook`
4. 前端通过 `/api/v1/...` 请求后端接口

---


