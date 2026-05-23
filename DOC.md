# 电子书城后端技术文档（完整版）

> **文档类型**：技术原理 + 项目实现（综合版）  
> **覆盖范围**：`springboot-ebook` 后端工程；前端仅说明与后端的契约与联调要点。  
> **阅读方式**：建议先读 [第零部分](#第零部分-基础概念导读是什么--为什么--本项目中的体现)（概念与原理），再读第一～十三部分（在本项目中的设计与实现）。  
> **说明**：本文在原有项目文档基础上，参考课程材料（JSON/Fetch/CORS、Java 平台、Servlet/Spring Boot）做了**归纳与扩展**；表述经整理，不收录课堂零碎速记原文。  
> 代码路径均相对于仓库根目录 `EBook/`。

---

## 目录

- [第零部分 基础概念导读](#第零部分-基础概念导读是什么--为什么--本项目中的体现)
- [第一部分 系统语境与设计抉择](#第一部分-系统语境与设计抉择)
- [第二部分 依赖与运行时底座](#第二部分-依赖与运行时底座)
- [第三部分 Spring Boot 启动与配置机制](#第三部分-spring-boot-启动与配置机制)
- [第四部分 分层架构与各层职责边界](#第四部分-分层架构与各层职责边界)
- [第五部分 Spring Web MVC 与 HTTP/JSON 处理](#第五部分-spring-web-mvc-与-httpjson-处理)
- [第六部分 数据持久化](#第六部分-数据持久化jdbc连接池sql-脚本与-jpa)
- [第七部分 Spring Data JPA 与 Repository](#第七部分-spring-data-jpa-与-repository-机制)
- [第八部分 领域模型 Entity](#第八部分-领域模型entity-与数据库映射)
- [第九部分 DTO、校验与 API 契约](#第九部分-dto校验与对外-api-契约)
- [第十部分 业务服务层实现剖析](#第十部分-业务服务层实现剖析)
- [第十一部分 异常处理与错误语义](#第十一部分-异常处理与错误语义)
- [第十二部分 跨域、安全模型与前后端协作](#第十二部分-跨域安全模型与前后端协作)
- [第十三部分 完整请求生命周期示例](#第十三部分-完整请求生命周期示例)
- [附录 A REST API 一览](#附录-a-rest-api-一览)
- [附录 B 已知局限与可演进方向](#附录-b-已知局限与可演进方向)

---

# 第零部分 基础概念导读（是什么 · 为什么 · 本项目中的体现）

> 阅读建议：若你对 Spring、JPA、DTO 等尚不熟悉，**先读本部分**，再读后续「在本项目里如何用」的章节。  
> 每一节按同一结构组织：**是什么** → **为什么需要** → **在本项目中的体现**。

---

## 0.1 前后端分离与「后端 API 服务」

### 是什么

**前后端分离**指：用户界面（HTML/组件、样式、浏览器里的逻辑）由**前端工程**负责；数据存储、业务规则、权限等由**后端服务**负责。二者通常跑在不同端口（本项目：前端 `5173`，后端 `8080`），通过 **HTTP 网络请求**交换数据。

**后端 API 服务**是一类长期运行的程序：监听端口，等待请求，返回结果。它不生成完整网页，只返回**结构化数据**（本项目为 JSON）。

### 为什么需要

- 前端可独立迭代 UI（换框架、做移动端）而不改 Java 代码；
- 后端可服务多个客户端（Web、App）；
- 职责清晰，便于团队分工与测试。

### 在本项目中的体现

- 后端模块：`springboot-ebook/`，入口 `EbookBackendApplication`；
- 前端模块：`react-ebook/`（本文不展开），通过 `fetch` 调用 `http://localhost:8080/api/v1/...`。

---

## 0.2 HTTP 与 REST
### 是什么

**HTTP（HyperText Transfer Protocol）** 是浏览器与服务器之间的**请求—响应**协议。一次交互包含：

- **请求**：方法（GET/POST 等）、URL、头（Headers）、可选 body；
- **响应**：状态码（200/404/400 等）、头、body。

**REST（Representational State Transfer）** 是一种用 HTTP **设计 API 的风格**（不是某一家公司的产品）。常见约定：

- 用 **URL 表示资源**（如 `/api/v1/books` 表示书集合）；
- 用 **HTTP 方法表示动作**（GET 查询、POST 创建或提交动作、PATCH 部分更新、DELETE 删除）；
- 用 **JSON** 作为资源的常见表示形式。

**同源（Origin）** 由协议、主机、端口共同决定，例如 `http://localhost:5173` 与 `http://localhost:8080` 端口不同，即**不同源**。浏览器默认限制跨源脚本读取另一源的响应，需配合 CORS（见 [0.19](#019-cors跨域资源共享) 与第十二部分）。

### 常见 HTTP 状态码（后端应明确返回）

| 状态码 | 含义 | 本项目典型场景 |
|--------|------|----------------|
| **200 OK** | 成功，有响应体 | GET 列表、PATCH 更新成功 |
| **201 Created** | 已创建资源 | `POST /users/register` |
| **400 Bad Request** | 请求不合法（参数、校验） | `@Valid` 失败、`IllegalArgumentException` |
| **404 Not Found** | 资源不存在 | 书/用户/订单找不到 |
| **500 Internal Server Error** | 服务端未处理异常 | 应避免；演示项目依赖全局异常处理转为 4xx |

**幂等性**（Idempotency）：多次相同请求的效果与一次相同。GET、PUT、DELETE 通常视为幂等；POST 创建资源一般**不**幂等。设计 API 时区分「查询」与「有副作用的动作」，有助于前端重试与缓存策略。

### 为什么需要

统一、可预测的接口让前端、测试工具、文档都能按同一套规则工作；HTTP 是互联网最通用的应用层协议；明确状态码可减少前后端对「失败原因」的歧义。

### 在本项目中的体现

| HTTP | 路径示例 | 含义 |
|------|----------|------|
| GET | `/api/v1/books` | 获取书目列表 |
| POST | `/api/v1/users/login` | 提交登录凭据 |
| PATCH | `/api/v1/orders/1/ORD-xxx` | 修改订单状态 |
| DELETE | `/api/v1/cart/1/items/3` | 删除购物车中某本书 |

Controller 上的 `@GetMapping`、`@PostMapping` 等把 Java 方法绑定到 REST 风格 URL（见第五部分）。注册接口返回 **201** 而非一律 200。

---


## 0.3 JSON
### 是什么

**JSON（JavaScript Object Notation）** 是一种**与语言无关的文本格式**，用来表示结构化数据，例如：

```json
{
  "id": 1,
  "username": "DefaultUser",
  "email": "student@example.com"
}
```

历史上 Web 也曾用 **XML** 交换数据。XML 标签冗长、解析成本高（DOM 建树占内存，SAX 流式解析实现复杂）。JSON 采用键值对与数组，**信息密度更高**，成为 REST API 的事实标准。

**JSON 与 JavaScript 对象不是同一概念**（混用易出错）：

| 规则 | JSON | JavaScript 对象 |
|------|------|-----------------|
| 键 | 必须是双引号字符串 | 可无引号 |
| 尾随逗号 | 不允许 | 允许 |
| 值类型 | 仅 string/number/bool/null/array/object | 还可含函数、`undefined` |
| 特殊数值 | 不允许 `NaN`、`Infinity` | 允许 |

前端应使用 `JSON.stringify` / `JSON.parse`（或 `fetch` 配合 `response.json()`），不要手写拼接易错字符串。后端由 **Jackson** 完成 Java 类型与 JSON 的互转。

**JSON Schema**（可选）：描述 JSON 应满足的结构，类似 XML 的 DTD/XSD，可在联调前约束字段类型与长度；本项目以 **DTO + Bean Validation** 在服务端校验为主。

### 为什么需要

HTTP body 需要双方都懂的格式。JSON 简洁、可读，且与浏览器生态契合。在关系库中，把整段 JSON 塞进 TEXT 字段虽可行，但**不利于按字段查询与索引**；本项目采用规范表结构 + JPA 映射，而非「文档型一列 JSON」。

### 安全注意

- **输入校验**：所有来自客户端的 JSON 字段应在 DTO 上声明约束（`@NotBlank` 等），并在 Service 中做业务校验；不要拼接 SQL 字符串。
- **NoSQL 注入**（若将来使用文档库）：勿把未校验的 JSON 直接当作查询操作符；关系型 + JPA 参数绑定可降低 SQL 注入风险。
- **XSS**：JSON 本身不执行脚本，但若前端把未转义内容插入 `innerHTML` 仍可能 XSS；后端返回数据时避免混入 HTML。

### 在本项目中的体现

- 请求：登录 body `{"username":"...","password":"..."}` → `UserLoginRequest`；
- 响应：`UserResponse`、`List<Book>` 等由 Jackson 序列化；
- 购物车/订单 API 使用专用 DTO，控制对外字段（如不返回 `password`）。

---


## 0.4 关系型数据库与 MySQL

### 是什么

**关系型数据库**把数据存放在**表（table）**里，表由**行**和**列**组成；表与表之间可通过**外键**建立关系（如订单行引用 `user_id`、`book_id`）。使用 **SQL** 语言查询和修改数据。

**MySQL** 是一种具体的数据库**产品**（开源、常用、课程环境常见），在本项目中作为唯一持久化存储。

### 为什么需要

应用重启、服务器关机后，用户、订单、购物车仍须保存。**内存中的 Java 对象**会随进程结束而消失，必须把数据写入磁盘上的数据库。

### 在本项目中的体现

- 库名：`ebook_backend`；
- 五张表：`users`、`books`、`cart_items`、`orders`、`order_items`（定义见 `schema.sql`）；
- 演示数据见 `data.sql`（如默认用户 `DefaultUser`、8 本书）。

---

## 0.5 SQL、DDL 与 DML

### 是什么

**SQL（Structured Query Language）** 是与关系型数据库对话的语言。

- **DDL（Data Definition Language）**：定义结构，如 `CREATE TABLE`、`DROP TABLE`；
- **DML（Data Manipulation Language）**：操作数据，如 `INSERT`、`SELECT`、`UPDATE`、`DELETE`。

### 为什么需要

表结构必须事先定义；应用运行时要按条件查书、插订单。JPA 底层仍会生成 SQL，但开发者也可用手写脚本初始化库表。

### 在本项目中的体现

- `schema.sql`：DDL，删表并重建四表及外键、唯一约束；
- `data.sql`：DML，插入种子用户与图书；
- 运行时 CRUD：多数由 Hibernate 根据 Repository 方法**自动生成** SQL（日志中 `show-sql=true` 可见）。

---

## 0.6 JDBC 与数据源（DataSource）

### 是什么

**JDBC（Java Database Connectivity）** 是 Java 访问数据库的**标准 API**。核心抽象包括：

- `Connection`：与数据库的一次连接；
- `Statement` / `PreparedStatement`：执行 SQL；
- `ResultSet`：查询结果集。

**数据源（DataSource）** 是更上层的工厂：向应用提供连接，通常由**连接池**管理（见下节）。

应用代码一般不直接写 `DriverManager.getConnection`，而是由 Spring 注入 `DataSource`，再交给 JPA 使用。

### 为什么需要

统一接口使 Java 可切换不同数据库（换驱动 jar 即可）；连接池避免「每个请求新建 TCP 连接」的性能问题。

### 在本项目中的体现

- 驱动：`com.mysql.cj.jdbc.Driver`（`application.properties`）；
- 连接 URL：`jdbc:mysql://localhost:3306/ebook_backend?...`；
- Spring Boot 自动配置 **HikariCP** 作为 `DataSource` 实现。

---

## 0.7 连接池（以 HikariCP 为例）
### 是什么

**连接池**预先创建若干条到数据库的 `Connection`，放在池中复用。请求来时**借**一条，用完**还**回池中，而不是每次请求都新建 TCP 连接并认证。

**HikariCP** 是 Java 生态中性能较好的一种连接池实现；Spring Boot 2+ 默认采用它。

若每次 HTTP 请求都 `new Connection()`，数据库端要反复握手、鉴权，高并发下会成为瓶颈。池化把连接成本摊到启动阶段，运行时主要做「借还」。

### 在本项目中的体现

启动日志中的 `HikariPool-1 - Starting...` 即池初始化。连接失败（库不存在、密码错误）时，池在启动阶段 `checkFailFast` 失败，应用无法就绪。业务线程从池中取连接 → JPA/Hibernate 执行 SQL → 归还连接；与「一连接一线程」的 Servlet 模型配合（见第六部分）。

---


## 0.8 ORM、JPA 与 Hibernate

### 是什么

- **ORM（Object-Relational Mapping，对象关系映射）**：用 **Java 对象** 表示数据库行，用 **类的属性** 表示列，由框架在对象与 SQL 之间转换。
- **JPA（Jakarta Persistence API）**：Java 官方的 ORM **规范**（一组接口与注解约定），不绑定具体实现。
- **Hibernate**：最流行的 JPA **实现**；Spring Data JPA 默认使用 Hibernate 生成 SQL、管理实体生命周期。

可以类比：**JPA 是插座标准，Hibernate 是某个品牌的插头**。

### 为什么需要

手写 JDBC 映射每一列很繁琐且易错。ORM 让你对 `bookRepository.save(book)` 操作对象，由框架生成 `INSERT`/`UPDATE`。

### 在本项目中的体现

- 实体类：`entity/Book.java` 等，带 `@Entity`、`@Table`、`@Column`；
- `spring-boot-starter-data-jpa` 引入 Hibernate；
- `spring.jpa.hibernate.ddl-auto=none` 表示**不让** Hibernate 自动改表，表结构由 `schema.sql` 管。

---

## 0.9 实体（Entity）

### 是什么

**实体**在 JPA 中指**与数据库表一行一一对应**的 Java 类。通常：

- 一个类对应一张表；
- 一个对象对应一行；
- 主键字段用 `@Id` 标记。

实体主要用于**持久化层**内部，表示「数据库里长什么样」。

### 为什么需要

ORM 需要知道 Java 类型与表结构的对应关系，才能正确读写。实体是这种映射的载体。

### 在本项目中的体现

| 实体类 | 表 |
|--------|-----|
| `User` | `users` |
| `Book` | `books` |
| `CartItem` | `cart_items` |
| `OrderEntity` | `orders` |
| `OrderItem` | `order_items`（无独立 Repository，经订单头级联持久化） |

例如 `User` 的 `username` 字段映射 `users.username` 列（见 `entity/User.java`）。

---

## 0.10 DTO（Data Transfer Object，数据传输对象）

### 是什么

**DTO** 是专门用于**在不同层或不同系统之间传递数据**的类，常见命名：`UserResponse`、`CartItemRequest`。它通常：

- **没有**复杂业务行为（多为 getter/setter）；
- 字段集合**针对某次 API 调用**裁剪，不必与数据库表一一对应；
- 与 **Entity 分离**：Entity 面向表，DTO 面向接口契约。

### 为什么需要（为什么用 DTO）

1. **安全**：`User` 实体含 `password`，若直接返回实体，JSON 可能泄露密码。`UserResponse` 不含 password。
2. **解耦**：数据库加列不一定改 API；API 可组合多表字段为一个响应，而不暴露表结构。
3. **语义清晰**：对外字段名可与内部不同，如 `OrderResponse.id` 实际存的是业务订单号 `orderNo`。
4. **入参校验**：`UserLoginRequest` 只收登录需要的字段，并加 `@NotBlank` 等注解。

**不用 DTO 可以吗？** 可以。本项目 `Book` 无敏感信息，Controller 直接返回 `List<Book>`。一旦涉及密码、字段重命名或裁剪，DTO 几乎是惯例。

### 在本项目中的体现

- 请求 DTO：`dto/UserLoginRequest.java`、`dto/CartItemRequest.java` 等；
- 响应 DTO：`dto/UserResponse.java`、`dto/CartItemResponse.java`、`dto/OrderResponse.java`；
- 转换位置：`UserService.toResponse(User)` 把 Entity 拷贝到 DTO；`CartService.toResponse(CartItem)` 同理。

---

## 0.11 Repository（仓储）

### 是什么

在领域驱动设计（DDD）里，**Repository** 表示「像集合一样访问聚合根」的抽象：按 id 取对象、保存对象，**隐藏** SQL 与 JDBC 细节。

在 Spring Data JPA 中，Repository 是一个 **Java 接口**，继承 `JpaRepository` 后即具备基本 CRUD；还可通过**方法名**声明查询。

### 为什么需要

Service 层应表达「查用户」「存订单」，而不是满屏 `SELECT * FROM ...`。Repository 是持久化能力的边界，便于替换实现（测试时可用内存假实现）。

### 在本项目中的体现

```java
public interface UserRepository extends JpaRepository<User, Long> {
    Optional<User> findByUsername(String username);
}
```

Spring 在启动时生成该接口的**实现类（代理）**，注入到 `UserService`。详见第七部分。

---

## 0.12 分层架构（Controller / Service / Repository）

### 是什么

**分层架构**把代码按职责切成水平层，常见 Web 后端三层：

| 层 | 职责 |
|----|------|
| **表现层 / 控制层** | 处理 HTTP，解析参数，返回响应 |
| **业务层 / 服务层** | 业务规则、流程编排 |
| **持久层 / 数据访问层** | 读写数据库 |

规则：**上层可调用下层，下层不调用上层**（Controller → Service → Repository）。

### 为什么需要

避免「一个类里又写 SQL 又写 HTTP 又写打折规则」。改业务只动 Service；换数据库访问方式主要动 Repository。

### 在本项目中的体现

- `controller/*` → `service/*` → `repository/*` → `entity/*`；
- 加购数量上限在 `CartService`，不在 `CartController`；
- SQL 由 JPA 生成，不在 Controller 中出现。

---

## 0.13 Spring 框架与 Spring Boot
### 是什么

**Spring** 是 Java 生态的**应用开发框架**，核心包括 IoC 容器、AOP、事务、MVC 等（本项目主要用 MVC 与事务基础设施）。

**Spring Boot** 在 Spring 之上提供：内嵌 Web 服务器（默认 Tomcat）、**自动配置**（按 classpath 与 `application.properties` 装配 DataSource、JPA 等）、Starter 依赖聚合，减少 XML 与样板代码。

**Jakarta EE**（原 Java EE）是一套**企业级规范**（Servlet、JPA、Validation 等）。Spring Boot 3 基于 **Jakarta 命名空间**（`jakarta.*`），不再使用 `javax.servlet` 等旧包名。Spring 可视为在规范之上的一套**实现与编程模型**；内嵌 Tomcat 使部署从「打 WAR 丢进外部容器」变为「`java -jar` 单进程启动」。

**注解（Annotation）** 是附在类/方法上的元数据；对编译生成的字节码无本质改变，但 Spring 在启动时**扫描**注解（如 `@RestController`、`@Service`），决定注册哪些 Bean、如何映射 URL——属于「配置即代码」。

### 为什么需要

从零拼装 Spring + Tomcat + Hibernate 工作量大。Spring Boot 让「引入 starter 即可使用 JPA」成为常态，适合课程与中小型 API 服务。

### 在本项目中的体现

- 启动类：`EbookBackendApplication`（`@SpringBootApplication`）；
- 依赖：`spring-boot-starter-web`、`spring-boot-starter-data-jpa` 等；
- 配置：`application.properties`；包名使用 `jakarta.persistence`、`jakarta.validation`。

---


## 0.14 IoC、依赖注入（DI）与 Bean

### 是什么

- **IoC（Inversion of Control，控制反转）**：对象的创建与依赖关系不由业务类自己 `new`，而交给**容器**（Spring 的 `ApplicationContext`）。
- **DI（Dependency Injection，依赖注入）**：容器把依赖「注入」到类中（常见为**构造器注入**）。
- **Bean**：由 Spring 容器管理的对象实例，如 `UserService`、`BookController` 各是一个 Bean。

### 为什么需要

- 降低耦合：`CartController` 只依赖 `CartService` 接口行为，不关心谁实现；
- 便于测试：可注入 Mock 的 Repository；
- 统一生命周期：单例 Bean 默认只创建一次，共享使用。

### 在本项目中的体现

```java
public CartController(CartService cartService) {
    this.cartService = cartService;
}
```

没有 `new CartService()`。Spring 在启动时创建 `CartService` Bean，再创建 `CartController` 并传入。带 `@Service`、`@RestController`、`@Repository`（接口由 `@EnableJpaRepositories` 注册）的类都会被扫描为 Bean。

---

## 0.15 Spring MVC 与 Controller

### 是什么

**Spring MVC** 是 Spring 的 **Web 模块**，基于 Servlet，核心有一个 **`DispatcherServlet`（前端控制器）**：接收所有 HTTP 请求，查表找到该调用哪个 Controller 方法，执行后再把返回值写成响应。

**Controller** 是 MVC 中的 **C**：负责接收请求、调用业务、返回结果。`@RestController` 表示返回值直接作为 HTTP body（通常为 JSON）。

### 为什么需要

把「URL 路由」「参数解析」「内容协商」从业务代码中分离。你只需在方法上写 `@GetMapping("/books")`，框架处理其余协议细节。

### 在本项目中的体现

- `BookController`、`CartController` 等；
- 一次请求的完整路径见第五部分、第十三部分。

---

## 0.16 Service 层

### 是什么

**Service**（服务层）是介于 Controller 与 Repository 之间的**业务逻辑层**。一个 Service 类通常对应一个业务领域（用户、购物车、订单），方法表达用例：「登录」「加购」「结算」。

在 Spring 中用 `@Service` 标注，本质仍是 Bean，只是语义上标明「这里放业务规则」。

### 为什么需要

同一规则可能被多个接口复用（如「用户必须存在」在购物车与订单中都要检查）。集中在 Service 避免重复；也便于单元测试业务而不启动 HTTP。

### 在本项目中的体现

- `UserService.login`：校验密码；
- `CartService.addToCart`：数量上限 4、UPSERT 购物车行；
- `CartService.checkout`：调用 `OrderService.createOrders` 并删除购物车行。

---

## 0.17 Bean Validation（Jakarta Validation）

### 是什么

**Bean Validation** 是 Java 对「对象字段约束」的标准，如「不能为空」「长度范围」。注解写在字段上（`@NotBlank`、`@NotNull`），由校验器在运行时检查。

**Hibernate Validator** 是其参考实现；Spring 在 Controller 参数上加 `@Valid` 时自动触发校验。

### 为什么需要

基础格式错误（空用户名）应在进入 Service **之前**拦截，返回 400，而不是与「密码错误」等业务错误混在一起，也减轻 Service 负担。

### 在本项目中的体现

`UserLoginRequest` 上 `@NotBlank`；`CartItemRequest` 上 `@NotNull`（bookId）。失败时 `MethodArgumentNotValidException` → `ApiExceptionHandler` → HTTP 400 + `{ "message": "..." }`。

---

## 0.18 全局异常处理（`@RestControllerAdvice`）

### 是什么

若每个 Controller 方法都写 `try-catch`，代码臃肿且错误格式不统一。**全局异常处理**用一个类集中捕获指定异常类型，转换为固定结构的 HTTP 响应。

`@RestControllerAdvice` 组合了「全局」+「REST 响应体」。

### 为什么需要

客户端（前端）希望错误时总能解析 `message` 字段。统一处理保证所有接口行为一致。

### 在本项目中的体现

`exception/ApiExceptionHandler.java`：将 `IllegalArgumentException` 转为 400，`ResourceNotFoundException` 转为 404。

---

## 0.19 CORS（跨域资源共享）
### 是什么

浏览器的**同源策略**规定：页面来自 `http://localhost:5173` 时，默认不能让页面中的 JavaScript 随意读取 `http://localhost:8080` 的响应（**协议、主机、端口**任一不同即为跨源）。

**CORS（Cross-Origin Resource Sharing）** 是标准机制：服务器在响应头中声明允许的来源、方法、头信息，浏览器才放行前端读取响应。

**简单请求**与**预检（Preflight）**：

- 部分 GET、简单 POST 可能直接发送；
- 带 `Content-Type: application/json` 的 POST、自定义头等属于**非简单请求**：浏览器会先发 **`OPTIONS`** 预检，询问服务器是否允许，通过后再发真实 `POST`/`PATCH` 等。

Spring Boot 中常见配置方式（本项目用第一种）：

1. **`WebMvcConfigurer#addCorsMappings`**（全局 MVC 层，本项目 `CorsConfig`）；
2. `@CrossOrigin` 标注在单个 Controller；
3. `CorsFilter`（Servlet 过滤器层，更底层）。

若需携带 Cookie 或 `Authorization`，前端 `fetch` 需设置 `credentials: 'include'`，且服务端 `allowedOrigins` 不能为 `*`，须指定具体源。

### 为什么需要

前后端分离几乎必然跨源。未配置 CORS 时，网络面板可能看到请求已到达后端，但浏览器仍向 JS 报错，导致「后端正常、前端失败」的假象。

### 在本项目中的体现

`config/CorsConfig.java` 对 `/api/**` 允许源 `http://localhost:5173` 及 GET/POST/PUT/PATCH/DELETE/OPTIONS。详见第十二部分与 `react-ebook/src/api/backendApi.js`。

---


## 0.20 Maven 与 Starter
### 是什么

**Maven** 是 Java 的**构建与依赖管理**工具。`pom.xml` 声明坐标与版本，Maven 从中央仓库（或镜像）下载 jar，并驱动编译、测试、打包。

典型生命周期命令：

| 命令 | 作用 |
|------|------|
| `mvn clean` | 清理 `target/` |
| `mvn test` | 运行单元测试 |
| `mvn package` | 编译并打 jar |
| `mvn install` | 安装到本地仓库 |

**Spring Boot Starter** 是一组**传递依赖 + 自动配置**的打包：例如 `spring-boot-starter-web` 引入 Spring MVC、Jackson、内嵌 Tomcat，且版本由 `spring-boot-starter-parent` BOM 对齐。

**Maven Wrapper（`mvnw`）**：项目自带脚本与固定 Maven 版本，保证团队环境一致，无需全局安装同版本 Maven。

### 为什么需要

手动管理几十个 jar 的版本极易冲突。Parent POM + Starter 解决「能编译、能运行」的最低成本；标准目录结构（`src/main/java`）降低协作成本。

### 在本项目中的体现

`pom.xml` 继承 `spring-boot-starter-parent:3.2.4`，四个 starter；`mvn package` 生成可执行 fat jar。依赖检索可参考 [Maven Repository](https://mvnrepository.com/)。

---


## 0.21 浏览器异步通信与 Fetch API

### 是什么

早期 Web 每次交互往往**整页刷新**。**AJAX**（Asynchronous JavaScript and XML）指在后台发 HTTP 请求、用返回数据**局部更新 DOM**，用户无需等待整页重载。如今数据格式以 **JSON** 为主，但「异步请求 + 局部更新」的思想不变。

**Fetch API** 是现代浏览器内置的 HTTP 客户端，基于 **Promise**，可配合 `async/await`：

```javascript
const response = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) });
if (!response.ok) throw new Error("HTTP " + response.status);
const json = await response.json();
```

与老式 **XMLHttpRequest（XHR）** 相比，Fetch 链式调用更简洁；需注意：**网络错误**走 `catch`，**4xx/5xx** 通常仍 resolve，须检查 `response.ok`。

### 为什么需要

电子书城前端在加购、登录、结算时只更新状态与局部 UI，避免整页刷新；异步不阻塞浏览器主线程，交互更流畅。

### 在本项目中的体现

`react-ebook/src/api/backendApi.js` 封装 `fetch`，统一 Base URL、`Content-Type: application/json`、错误时解析 `{ message }`。跨域依赖后端 CORS（[0.19](#019-cors跨域资源共享)）。

---

## 0.22 Java 平台：字节码、JVM 与类加载

### 是什么

**Java** 是编程**语言与规范**；常见实现有 OpenJDK、Oracle JDK 等。源码 `.java` 经 **javac** 编译为**字节码**（`.class`），由 **JVM** 加载并执行。字节码是平台无关的中间表示，体现「一次编写，到处运行」。

**JIT（Just-In-Time）**：JVM 运行时将热点字节码编译为本地机器码，长时间运行后性能接近原生；启动阶段可能较慢。

**类加载器**（双亲委派）：Bootstrap → Platform → Application，子加载器先委托父加载器查找类，避免核心类被篡改。Tomcat 等容器可为**每个 Web 应用**分配独立 ClassLoader，实现应用隔离。

### 为什么需要

理解「为何是 jar + JVM 而非单一 exe」有助于排查 `ClassNotFoundException`、依赖冲突与 Spring Boot fat jar 结构。

### 在本项目中的体现

`mvn package` 产出含依赖的可执行 jar；`java -jar` 启动内嵌 Tomcat 与 Spring 容器。使用 **Java 17**（`pom.xml` 中 `java.version`）。

---

## 0.23 Servlet、Filter 与请求链路

### 是什么

**Servlet** 是 Java Web 的**标准接口**：`service(request, response)` 处理 HTTP。传统部署将 WAR 放入 **Tomcat** 等容器；Spring Boot **内嵌 Tomcat**，仍基于 Servlet API。

请求进入后大致经过：

```text
Connector → Filter 链（可选：编码、CORS、安全）→ DispatcherServlet → Controller → ...
```

**Filter** 在 Servlet 之前/之后拦截请求，适合横切逻辑（日志、认证、CORS）。Spring MVC 的 `DispatcherServlet` 是**前端控制器**，统一分发到 `@RestController` 方法。

### 为什么需要

知道「请求先到 Tomcat 再到 Spring」有助于理解 CORS 预检、404 是容器还是 Spring 抛出、以及为何 `@RestController` 能直接写 JSON。

### 在本项目中的体现

`spring-boot-starter-web` 注册 `DispatcherServlet`；业务入口为 `controller` 包下各类。完整链路见第五部分、第十三部分。

---

## 0.24 面向对象、接口与分层原则

### 是什么

Java **纯面向对象**：除基本类型外，逻辑落在类与方法中。常见实践：

- **封装**：字段私有，通过 getter/setter 或构造器暴露；
- **继承与多态**：子类可替代父类引用，运行时调用实际类型的方法；
- **接口（interface）**：声明能力契约，与实现分离；便于测试与替换。

**SOLID**（简述）：单一职责（一类一事）、开闭（扩展而非修改）、里氏替换、接口隔离、依赖倒置（依赖抽象）。企业项目中 **Controller / Service / Repository** 分层即依赖倒置的体现：上层依赖接口，持久化细节下沉。

### 为什么需要

接口稳定的、实现可替换，是 Spring Data JPA「只写 Repository 接口、无实现类」的理论基础（见 [0.11](#011-repository仓储)）。

### 在本项目中的体现

`UserRepository extends JpaRepository<User, Long>`；`CartService` 编排业务，不直接写 SQL。禁止在 Controller 中写持久化逻辑（见第四部分）。

---



## 0.25 事务（Transaction）概念

### 是什么

**事务**是一组数据库操作的原子单元：**要么全部成功提交，要么全部回滚**。典型场景：转账扣款与加款必须同时成功。

在 Spring 中，常用 `@Transactional` 标注方法，由框架在方法前后开启/提交/回滚 JDBC 事务。

### 为什么需要

`checkout` 包含「插入订单」与「删除购物车行」两步，若第一步成功、第二步失败，会出现数据不一致。事务可把多步绑在一起。

### 在本项目中的体现

当前 **未** 在 `CartService.checkout` 上声明 `@Transactional`（见附录 B）。Repository 的单个 `save` 仍有默认短事务。理解事务概念有助于说明未来改进方向。

---

## 0.26 `Optional` 与 `ResponseEntity`

### 是什么

- **`Optional<T>`**：Java 8 容器，表示「可能有值可能没有」，避免用 `null` 表示「查不到」。
- **`ResponseEntity<T>`**：Spring 对 HTTP 响应的封装，可指定**状态码**、**头**、**body**，如 `201 Created`。

### 为什么需要

- `Optional` 强制调用方处理缺失：`orElseThrow(...)`；
- `ResponseEntity` 表达 REST 语义（注册成功返回 201 而非一律 200）。

### 在本项目中的体现

- `bookRepository.findById(id).orElseThrow(...)`；
- `UserController.register` 返回 `ResponseEntity.status(HttpStatus.CREATED).body(...)`。

---

## 0.27 概念关系总览

```text
                    [ 浏览器 / React ]
                            │ HTTP + JSON
                            ▼
              ┌─────────────────────────────┐
              │  Spring MVC (Controller)     │  ← REST 入口，DTO 入参/出参
              └──────────────┬──────────────┘
                             │
              ┌──────────────▼──────────────┐
              │  Service                     │  ← 业务规则
              └──────────────┬──────────────┘
                             │
              ┌──────────────▼──────────────┐
              │  Repository (接口)           │  ← 持久化抽象
              └──────────────┬──────────────┘
                             │ JPA / Hibernate
              ┌──────────────▼──────────────┐
              │  Entity                      │  ← 表映射
              └──────────────┬──────────────┘
                             │ JDBC
              ┌──────────────▼──────────────┐
              │  DataSource (HikariCP)       │
              └──────────────┬──────────────┘
                             ▼
                        MySQL (SQL)
```

**DTO** 横切在 Controller 边界：请求进入时 JSON→Request DTO→Service；返回时 Entity→Response DTO→JSON。

---

# 第一部分 系统语境与设计抉择

## 1.1 后端在整体系统中的位置

本项目采用**前后端分离**：浏览器中的 React 应用负责 UI 与路由；`springboot-ebook` 作为**无状态（演示级）的 JSON API 服务**，职责限定为：

1. 解析 HTTP 请求（路径、方法、JSON 体）；
2. 执行业务规则并访问 MySQL；
3. 将结果编码为 JSON 响应，或返回结构化错误。

后端**不**渲染 HTML，**不**托管前端静态资源（封面图片由前端 `public/assets` 提供；数据库 `books` 表无 `cover` 列）。

## 1.2 架构风格：经典三层 + DTO

```text
┌─────────────────────────────────────────────────────────┐
│ Presentation  │  controller.*   REST 适配、参数绑定      │
├───────────────┼─────────────────────────────────────────┤
│ Application   │  service.*      业务规则、流程编排        │
├───────────────┼─────────────────────────────────────────┤
│ Persistence   │  repository.*   持久化抽象（接口）       │
│               │  entity.*       ORM 映射对象              │
└─────────────────────────────────────────────────────────┘
                          │
                     MySQL ebook_backend
```

**DTO 与 Entity 的分离**：概念定义见 [0.10 DTO](#010-dto-datatransfer-object数据传输对象)。本项目里，`User` 含 `password` 必须用 `UserResponse` 对外；`Book` 无敏感字段，Controller 可直接返回 `List<Book>`；购物车/订单用 DTO 是为裁剪字段或将 `orderNo` 映射为 JSON 的 `id`。

## 1.3 有意未采用的技术

| 技术 | 未采用原因（本项目） |
|------|----------------------|
| Spring Security / JWT | 课程规模演示；用 URL 路径中的 `userId` 标识用户，登录态由前端 `localStorage` 保存 |
| `@Transactional` 显式声明 | 未编写；依赖 Spring Data 仓库方法默认事务；复杂流程见 [附录 B](#附录-b-已知局限与可演进方向) |
| Redis / 消息队列 | 购物车、订单直接落 MySQL |
| Flyway/Liquibase | 使用 `schema.sql` + `data.sql` + `spring.sql.init` |

理解这些**缺席**与理解**存在**的技术同样重要，答辩或评审时可用于说明边界。

---

# 第二部分 依赖与运行时底座

## 2.1 Maven 与 Spring Boot Parent

`pom.xml` 继承 `spring-boot-starter-parent:3.2.4`，其作用是：

- **统一依赖版本**（BOM）：避免手动对齐 Spring Framework、Hibernate、Tomcat 等版本；
- **插件约定**：`spring-boot-maven-plugin` 打包可执行 fat jar；
- **`java.version=17`**：编译与测试的目标字节码级别。

```20:22:springboot-ebook/pom.xml
    <properties>
        <java.version>17</java.version>
    </properties>
```

## 2.2 各 Starter 在技术栈中的真实角色

### `spring-boot-starter-web`

引入：

- **Spring MVC**（`DispatcherServlet`、控制器映射、`HttpMessageConverter`）；
- **内嵌 Tomcat**（默认监听 8080）；
- **Jackson**（JSON 与 Java 类型互转）。

没有单独引入 `spring-webflux`，故本项目是 **Servlet 阻塞模型**：每个请求占用一个 Tomcat 线程，直到 Service/Repository 完成。

### `spring-boot-starter-data-jpa`

引入：

- **Spring Data JPA**（Repository 抽象）；
- **Hibernate**（JPA 实现）；
- **`spring-boot-starter-jdbc`**（间接）→ **HikariCP** 数据源。

### `mysql-connector-j`

MySQL 8 的 JDBC 驱动，运行时连接 `jdbc:mysql://...`。

### `spring-boot-starter-validation`

引入 **Hibernate Validator**（Jakarta Validation 实现），使 `@NotBlank`、`@NotNull` 等在 Controller 入参上生效。

## 2.3 运行时进程结构

执行 `EbookBackendApplication.main` 后，单 JVM 进程内大致存在：

```text
JVM
 └── Spring ApplicationContext（IoC 容器）
      ├── DataSource (HikariCP)
      ├── EntityManagerFactory (Hibernate)
      ├── *Repository 代理 Bean
      ├── *Service Bean
      ├── *Controller Bean
      ├── ApiExceptionHandler
      ├── CorsConfig → WebMvcConfigurer
      └── Embedded Tomcat
```

**IoC（控制反转）**体现在：业务类不写 `new BookRepository()`，而是通过构造器声明依赖，由容器在启动时注入实现。

---

# 第三部分 Spring Boot 启动与配置机制

## 3.1 启动类与组件扫描

```6:11:springboot-ebook/src/main/java/com/ebook/backend/EbookBackendApplication.java
@SpringBootApplication
public class EbookBackendApplication {

    public static void main(String[] args) {
        SpringApplication.run(EbookBackendApplication.class, args);
    }
}
```

`@SpringBootApplication` 组合了：

- `@Configuration`：允许 `@Bean` 配置类（如 `CorsConfig`）；
- `@EnableAutoConfiguration`：根据 classpath **自动装配** DataSource、JPA、Tomcat 等；
- `@ComponentScan`：默认扫描 `com.ebook.backend` 及其子包，注册带 `@Service`、`@RestController`、`@Repository`（通过 `@EnableJpaRepositories` 间接）的类。

## 3.2 `application.properties` 逐项说明

```1:14:springboot-ebook/src/main/resources/application.properties
spring.application.name=springboot-ebook

spring.datasource.url=${DB_URL:jdbc:mysql://localhost:3306/ebook_backend?createDatabaseIfNotExist=true&useUnicode=true&characterEncoding=UTF-8&serverTimezone=UTC}
spring.datasource.username=${DB_USERNAME:root}
spring.datasource.password=${DB_PASSWORD:...}
spring.datasource.driver-class-name=com.mysql.cj.jdbc.Driver

spring.jpa.hibernate.ddl-auto=none
spring.jpa.show-sql=true
spring.jpa.properties.hibernate.format_sql=true

spring.sql.init.mode=always
spring.sql.init.encoding=UTF-8
```

| 配置 | 技术含义 |
|------|----------|
| `${DB_URL:默认值}` | Spring **属性占位符**；环境变量/启动参数可覆盖，便于 IDEA 与 `run-local.sh` 使用不同端口 |
| `createDatabaseIfNotExist=true` | MySQL Connector/J 在库不存在时先 `CREATE DATABASE`，再连接 |
| `ddl-auto=none` | **禁止** Hibernate 根据 Entity 自动 `CREATE/ALTER TABLE`；表结构完全由 `schema.sql` 定义，避免与手工 SQL 冲突 |
| `show-sql` / `format_sql` | 开发期在日志打印 Hibernate 生成的 SQL（生产应关闭） |
| `sql.init.mode=always` | **每次**启动执行 `schema.sql`、`data.sql`（见下节） |

## 3.3 SQL 脚本初始化 vs JPA 的职责划分

本项目采用**双轨制**：

| 职责 | 由谁负责 |
|------|----------|
| 表结构（DDL） | `schema.sql`：`DROP` + `CREATE` + 外键 |
| 种子数据（DML） | `data.sql`：`INSERT` 演示用户、8 本书、购物车、订单 |
| 运行时 CRUD | JPA/Hibernate + Repository |

启动顺序（简化）：

```text
1. 创建 DataSource
2. DataSourceScriptDatabaseInitializer 执行 schema.sql → data.sql
3. 初始化 EntityManagerFactory（读取 Entity 注解元数据）
4. 创建 Repository 代理
5. 启动 Tomcat，监听 8080
```

因此：**每次重启后端会清空并重建表数据**（`always` + `DROP TABLE`）。这是演示环境权衡，不是 JPA 固有行为。

`schema.sql` 片段说明设计意图：

```29:37:springboot-ebook/src/main/resources/schema.sql
CREATE TABLE cart_items (
    ...
    UNIQUE KEY uk_cart_user_book (user_id, book_id),
    CONSTRAINT fk_cart_user FOREIGN KEY (user_id) REFERENCES users(id),
    CONSTRAINT fk_cart_book FOREIGN KEY (book_id) REFERENCES books(id)
);
```

- **唯一约束** `(user_id, book_id)`：保证「同一用户同一本书」在购物车只有一行，Service 层 `findByUserIdAndBookId` + `save` 实现的是 **UPSERT 语义**（有则改数量，无则插入）。
- **外键**：防止插入不存在的 `user_id` / `book_id`；删除用户/书时需注意约束（当前脚本先 `DROP` 子表）。

---


## 3.5 Jakarta 命名空间与 Spring Boot 3

Spring Boot 3 / Spring Framework 6 要求 **Jakarta EE 9+** API：持久化、Servlet、Validation 等包名均为 `jakarta.*`。若依赖仍引用 `javax.persistence`、`javax.servlet`，会在编译或运行时报 `ClassNotFoundException`。

迁移要点：

- 源码 import 全部改为 `jakarta.*`；
- 第三方库须使用兼容 Jakarta 的版本；
- 内嵌 Tomcat 版本须支持 Servlet 5+（Spring Boot 3 已对齐）。

本项目 `pom.xml` 使用 Spring Boot 3.2.4，实体与 DTO 校验均基于 Jakarta 注解。



# 第四部分 分层架构与各层职责边界

## 4.1 Controller 层：HTTP 适配，不含业务

Controller 的职责是 **REST 语义 ↔ Java 方法** 的映射，应保持「薄」。

**构造器注入**示例（`CartController`）：

```23:27:springboot-ebook/src/main/java/com/ebook/backend/controller/CartController.java
    private final CartService cartService;

    public CartController(CartService cartService) {
        this.cartService = cartService;
    }
```

使用 `final` + 构造器注入的好处：

- 依赖不可变，利于测试与线程安全；
- 无需 `@Autowired` 字段注入，避免空指针与隐藏依赖。

**HTTP 动词与业务对应**：

| 方法注解 | 典型语义 | 本项目示例 |
|----------|----------|------------|
| `GET` | 查询，幂等 | `GET /api/v1/books` |
| `POST` | 创建/动作 | `POST .../items` 加购、`POST .../checkout` 结算 |
| `PATCH` | 部分更新 | 改购物车数量/勾选、改订单状态 |
| `DELETE` | 删除 | 移除购物车一行 |
| `PUT` | 全量替换 | 更新用户资料 |

`UserController.register` 使用 `ResponseEntity.status(HttpStatus.CREATED)`，在 REST 惯例中 **201** 表示资源已创建，区别于 200：

```29:32:springboot-ebook/src/main/java/com/ebook/backend/controller/UserController.java
    @PostMapping("/register")
    public ResponseEntity<UserResponse> register(@Valid @RequestBody UserRegisterRequest request) {
        return ResponseEntity.status(HttpStatus.CREATED).body(userService.register(request));
    }
```

## 4.2 Service 层：业务规则的唯一归属地

规则应出现在 Service，而非 Controller 或 Repository。例如：

- 加购数量上限 **4**；
- 结算只处理 `selected == true` 的行；
- 登录失败统一错误文案（防用户名枚举可再加强）；
- 订单状态仅允许 `pending` / `paid` / `cancelled`。

Service 之间可互相调用：`CartService` 依赖 `OrderService`，形成**应用层内编排**，Controller 不感知「结算要先建订单再删购物车」的顺序。

## 4.3 Repository 层：持久化接口，不含业务

Repository 是 **接口**，继承 `JpaRepository<Entity, IdType>` 即获得：

- `save`, `saveAll`, `findById`, `findAll`, `delete`, `deleteAll` 等；
- 分页、排序等（本项目未用）。

自定义方法由 **方法名解析** 生成查询（见第七部分）。

## 4.4 为何不把 SQL 写在 Controller

若违反分层，会出现：改库存规则要改 Controller、无法单测业务、事务边界混乱。本项目严格遵守「Controller → Service → Repository」单向依赖。

---

# 第五部分 Spring Web MVC 与 HTTP/JSON 处理

## 5.1 一次 HTTP 请求在 Spring MVC 中的路径

以 `POST /api/v1/cart/1/items` 为例：

```text
客户端 fetch
  → Tomcat Connector 接收 TCP
  → DispatcherServlet（前端控制器）
  → HandlerMapping 匹配 CartController.addItem
  → HandlerAdapter 调用方法
  → 解析 @PathVariable userId、@RequestBody → CartItemRequest（Jackson 反序列化）
  → 若 @Valid：触发 Bean Validation
  → 调用 cartService.addToCart(userId, request)
  → 返回值 List<CartItemResponse>
  → HttpMessageConverter（MappingJackson2HttpMessageConverter）序列化为 JSON
  → 写入 HTTP 响应体，Content-Type: application/json
```

**`@RestController`** = `@Controller` + `@ResponseBody`（类级别），方法返回值直接进入响应体，而非视图名。

## 5.2 参数绑定机制

| 注解 | 绑定来源 | 示例 |
|------|----------|------|
| `@PathVariable` | URI 模板 | `/cart/{userId}` → `Long userId` |
| `@RequestBody` | 请求体 JSON | `CartItemRequest` |
| `@Valid` | 校验请求体 | 失败抛 `MethodArgumentNotValidException` |

`BookController` 直接返回实体：

```21:24:springboot-ebook/src/main/java/com/ebook/backend/controller/BookController.java
    @GetMapping("/books")
    public List<Book> getAllBooks() {
        return bookService.findAll();
    }
```

Jackson 默认序列化 **getter 可见字段**：`Book` 的 `getTitle()` → JSON `"title"`（驼峰）。未标注 `@JsonIgnore` 的字段均会输出。

## 5.3 JSON 与 Java 类型

- 数字：`Long id` → JSON number；
- 布尔：`Boolean selected` → JSON boolean；
- 字符串：`String orderNo` → JSON string；
- 集合：`List<Book>` → JSON array。

**日期**：`OrderEntity.createdAt` 为 `LocalDateTime`，若返回给前端需依赖 Jackson 的 JSR-310 模块（Spring Boot 默认启用）；当前 `OrderResponse` **未暴露** `createdAt`，故订单 API 不传输时间字段。

## 5.4 PATCH 与部分更新语义

`CartItemUpdateRequest` 中 `qty`、`selected` 均为可选字段。Service 中：

```71:81:springboot-ebook/src/main/java/com/ebook/backend/service/CartService.java
        if (request.getQty() != null) {
            int qty = request.getQty();
            if (qty < 1 || qty > 4) {
                throw new IllegalArgumentException("qty must be between 1 and 4");
            }
            item.setQty(qty);
        }

        if (request.getSelected() != null) {
            item.setSelected(request.getSelected());
        }
```

这是典型的 **部分更新（PATCH 语义）**：只改请求里出现的字段，未出现的保持数据库原值。注意 `updateItem` 未加 `@Valid`，因字段均可空，校验落在 Service 数值范围判断。

---


## 5.5 前端 Fetch 与后端 JSON 契约（协作要点）

| 环节 | 前端 | 后端 |
|------|------|------|
| 序列化 | `JSON.stringify` 写入 body | Jackson 反序列化为 DTO |
| 反序列化 | `response.json()` | Jackson 序列化返回值 |
| 错误 | 读 `message` 字段展示 | `ApiExceptionHandler` 统一 JSON 错误体 |
| 类型 | 书 id 在 UI 可为 string，发 API 时转 number | `Long bookId` 与表一致 |

异步流程不阻塞 React 渲染；失败时区分网络异常与 HTTP 4xx/5xx（见 [0.21](#021-浏览器异步通信与-fetch-api)）。



# 第六部分 数据持久化：JDBC、连接池、SQL 脚本与 JPA

## 6.1 JDBC 在本项目中的位置

应用代码**不直接**编写 `Connection`、`PreparedStatement`。调用链是：

```text
Repository.save(entity)
  → Spring Data JPA 实现
  → EntityManager (Hibernate)
  → Session/JDBC
  → HikariCP 获取连接
  → MySQL 驱动执行 SQL
```

开发者操作的是 **对象图**（Entity），Hibernate 负责 **ORM（对象关系映射）**。

## 6.2 HikariCP 连接池

Spring Boot 2+ 默认数据源实现为 **HikariCP**。池化意义：

- 避免每个 HTTP 请求都新建 TCP 连接到 MySQL；
- 限制最大连接数，防止拖垮数据库；
- 连接复用降低延迟。

日志中 `HikariPool-1 - Starting...` 即池初始化；失败时（如库不存在、密码错误）在 `checkFailFast` 阶段抛错，应用无法完成启动——你之前在 IDEA 中遇到的 `Unknown database 'ebook_backend'` 即发生在此阶段，早于 Controller 就绪。

## 6.3 Hibernate 作为 JPA 实现

JPA 是**规范**（接口），Hibernate 是**实现**。关键行为：

### 实体状态（与本项目相关的部分）

| 状态 | 含义 | 典型操作 |
|------|------|----------|
| Transient | `new CartItem()` 未持久化 | `save()` 后变 Persistent |
| Persistent | 与当前 Session 关联 | `setQty` 后可能触发 UPDATE |
| Detached |  Session 关闭后 | 本项目较少显式处理 |

`cartItemRepository.save(item)`：若 `item.id == null`，Hibernate 生成 **INSERT**；若已有 id，根据状态可能 **UPDATE**。

### `GenerationType.IDENTITY`

```14:16:springboot-ebook/src/main/java/com/ebook/backend/entity/CartItem.java
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
```

对应 MySQL **`AUTO_INCREMENT`**：插入后由数据库生成主键，Hibernate 会回写到实体 `id` 字段。

### 列映射与命名

默认驼峰转下划线：`stockType` → `stock_type`。`OrderEntity` 显式指定：

```19:20:springboot-ebook/src/main/java/com/ebook/backend/entity/OrderEntity.java
    @Column(name = "order_no", nullable = false, unique = true, length = 40)
    private String orderNo;
```

```37:38:springboot-ebook/src/main/java/com/ebook/backend/entity/OrderEntity.java
    @Column(name = "created_at", insertable = false, updatable = false)
    private LocalDateTime createdAt;
```

- `insertable = false`：INSERT 语句**不包含** `created_at`，由数据库 `DEFAULT CURRENT_TIMESTAMP` 填充；
- `updatable = false`：后续 UPDATE 不改该列；
- 读取时仍可 `SELECT created_at` 映射到 `createdAt`（若查询包含该列）。

## 6.4 逻辑关系与物理外键

实体间未使用 JPA `@ManyToOne` 关联，而是用 **Long userId / bookId** 表达关系。这是有意简化：

- 避免懒加载、`JOIN FETCH` 等复杂度；
- 表结构与 SQL 作业脚本一致；
- 代价：无法通过 `cartItem.getBook()` 导航，需二次查询 `bookRepository.findById`。

数据库层外键仍保证引用完整性；ORM 层保持「扁平 POJO」。

---

# 第七部分 Spring Data JPA 与 Repository 机制

## 7.1 接口如何变成可执行的 Bean

编译期只有：

```java
public interface UserRepository extends JpaRepository<User, Long> {
    Optional<User> findByUsername(String username);
}
```

启动时 Spring Data 使用 **JDK 动态代理** 生成实现类，内部持有 `EntityManager`，根据方法名拼接 JPQL/SQL。

**接口与实现分离**在数据访问层的体现：业务代码依赖 `UserRepository` 接口，不依赖生成的 `UserRepositoryImpl`（类名因版本而异）。

## 7.2 查询方法命名规则（本项目实例）

| 方法名 | 推导含义 |
|--------|----------|
| `findByUsername` | `WHERE username = ?` |
| `findByUserId` | `WHERE user_id = ?` |
| `findByUserIdAndBookId` | `WHERE user_id = ? AND book_id = ?` |
| `findByUserIdOrderByCreatedAtDesc` | `WHERE user_id = ? ORDER BY created_at DESC` |
| `deleteByUserIdAndBookId` | `DELETE ... WHERE user_id = ? AND book_id = ?` |

`OrderRepository`：

```8:11:springboot-ebook/src/main/java/com/ebook/backend/repository/OrderRepository.java
public interface OrderRepository extends JpaRepository<OrderEntity, Long> {
    List<OrderEntity> findByUserIdOrderByCreatedAtDesc(Long userId);
    Optional<OrderEntity> findByOrderNoAndUserId(String orderNo, Long userId);
}
```

第二条用于**按业务订单号 + 用户**定位订单，防止用户 A 修改用户 B 的订单（在知道 `orderNo` 的前提下）；注意当前**未**在全局拦截器验证「路径 userId 与登录用户一致」，见安全模型。

## 7.3 `Optional` 作为返回类型

`findById`、`findByUsername` 返回 `Optional<T>`，强制调用方处理「不存在」：

```22:25:springboot-ebook/src/main/java/com/ebook/backend/service/BookService.java
    public Book findById(Long id) {
        return bookRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("book not found: " + id));
    }
```

避免 `NullPointerException` 与「魔法 null」在业务中传播。

## 7.4 `save` / `saveAll` 与批量插入

`orderRepository.save(order)` 一次保存订单头及其 `items` 明细（Hibernate 级联 INSERT）；是否批处理取决于 `hibernate.jdbc.batch_size` 等（本项目未调优）。**一次结算**只生成 **一条** `OrderEntity`（同一 `order_no`），购物车中每个已选商品对应一条 `OrderItem`，订单页按批次展示并汇总 `totalPrice`。

---

# 第八部分 领域模型：Entity 与数据库映射

## 8.1 五张表与实体

| 表 | 实体类 | 说明 |
|----|--------|------|
| `users` | `User` | 含 `password`（演示明文） |
| `books` | `Book` | 书目元数据 |
| `cart_items` | `CartItem` | 购物车行 |
| `orders` | `OrderEntity` | 订单头：一次结算一批次；类名避让用户模块 `User` 等 |
| `order_items` | `OrderItem` | 订单明细行；通过 `@OneToMany` 级联，**无** `OrderItemRepository` |

## 8.2 `User` 实体与隐私边界

```18:31:springboot-ebook/src/main/java/com/ebook/backend/entity/User.java
    @Column(nullable = false, unique = true, length = 60)
    private String username;
    @Column(nullable = false, length = 128)
    private String password;
    ...
    @Column(nullable = false, length = 30)
    private String level;
```

`UserService.toResponse` **手动**拷贝字段到 `UserResponse`，不拷贝 `password`——即使将来有人误把 `User` 当 `@RestController` 返回值，也应避免；当前 Controller 已统一返回 DTO。

## 8.3 `Book` 与 API 直接暴露

`Book` 字段与前端展示高度一致：`title`, `author`, `price`, `stockType`, `stockText`, `isbn` 等。前端 `normalizeBook` 用 `isbn` 关联本地封面路径，属于**前端展示层逻辑**，后端不参与。

## 8.4 `CartItem` 作为聚合内的「行」

购物车不是单独一张「购物车头表」，而是 **(userId, bookId) 多行模型**，等价于电商中的「购物车行项目」。`selected` 支持结算前勾选部分商品。

## 8.5 订单头、明细与价格快照

一次购物车结算对应 **一条** `OrderEntity`（`order_no` 唯一）和 **多条** `OrderItem`。明细上的 `unit_price` 在创建时从 `books.price` 复制，之后改书价不影响历史订单——常见 **快照** 设计。

```java
// OrderService.createOrders：单订单头 + 多明细行
OrderEntity order = new OrderEntity();
order.setOrderNo(generateOrderNo());
order.setUserId(userId);
order.setStatus("pending");
for (CartItem item : items) {
    OrderItem line = new OrderItem();
    line.setBookId(book.getId());
    line.setQty(item.getQty());
    line.setUnitPrice(book.getPrice());
    order.addItem(line);
}
orderRepository.save(order);
```

`OrderResponse` 对外字段：

- `id`：业务订单号 `orderNo`（非表自增 id）；
- `status`：整单状态（付款/取消作用于整批）；
- `items[]`：`bookId`、`qty`、`unitPrice`；
- `totalPrice`：各明细 `qty × unitPrice` 之和。

前端 `OrdersPage` 按订单头一行展示，明细列列出多本书，「订单总价」列显示 `totalPrice`。

---

# 第九部分 DTO、校验与对外 API 契约

> **前置阅读**：[0.10 DTO](#010-dto-datatransfer-object数据传输对象)、[0.17 Bean Validation](#017-bean-validationjakarta-validation)。本节侧重本项目中的具体类与数据流。

## 9.1 DTO 分类

| 类型 | 示例 | 方向 |
|------|------|------|
| Request DTO | `UserLoginRequest`, `CartItemRequest` | 客户端 → 服务端 |
| Response DTO | `UserResponse`, `CartItemResponse`, `OrderResponse`, `OrderItemResponse` | 服务端 → 客户端 |

`CartItemResponse` 仅含 `bookId, qty, selected`：书名、价格由前端用 `bookId` 关联已加载的 `books` 列表拼接——减少冗余传输，但增加前端 **join 逻辑**。

## 9.2 Bean Validation 流水线

`UserLoginRequest`：

```7:11:springboot-ebook/src/main/java/com/ebook/backend/dto/UserLoginRequest.java
    @NotBlank(message = "username is required")
    private String username;

    @NotBlank(message = "password is required")
    private String password;
```

Controller：

```35:36:springboot-ebook/src/main/java/com/ebook/backend/controller/UserController.java
    public ResponseEntity<UserResponse> login(@Valid @RequestBody UserLoginRequest request) {
        return ResponseEntity.ok(userService.login(request));
```

流程：

```text
JSON → UserLoginRequest
  → Validator 校验 @NotBlank
  → 失败：MethodArgumentNotValidException → ApiExceptionHandler → 400 + message
  → 成功：进入 UserService.login
```

业务校验（密码对错、用户名是否存在）在 Service 用 `IllegalArgumentException`，与「格式校验」分层。

## 9.3 错误响应契约

统一形如：

```json
{ "message": "invalid username or password" }
```

由 `ApiExceptionHandler` 保证。前端 `backendApi.js` 在 `!response.ok` 时解析 `body.message` 抛出 `Error`，供登录页显示。

---

# 第十部分 业务服务层实现剖析

## 10.1 `UserService`：注册与唯一性

```22:40:springboot-ebook/src/main/java/com/ebook/backend/service/UserService.java
    public UserResponse register(UserRegisterRequest request) {
        userRepository.findByUsername(request.getUsername()).ifPresent(user -> {
            throw new IllegalArgumentException("username already exists");
        });
        userRepository.findByEmail(request.getEmail()).ifPresent(user -> {
            throw new IllegalArgumentException("email already exists");
        });
        ...
        User saved = userRepository.save(user);
        return toResponse(saved);
    }
```

两次 `find` + `save` 各自在独立事务中（默认）。竞态下两请求同时注册同名仍可能有一个失败于数据库 **UNIQUE 约束**——演示级未做悲观锁。

登录：

```43:49:springboot-ebook/src/main/java/com/ebook/backend/service/UserService.java
    public UserResponse login(UserLoginRequest request) {
        User user = userRepository.findByUsername(request.getUsername())
                .orElseThrow(() -> new IllegalArgumentException("invalid username or password"));
        if (!user.getPassword().equals(request.getPassword())) {
            throw new IllegalArgumentException("invalid username or password");
        }
        return toResponse(user);
    }
```

用户名不存在与密码错误返回**相同文案**，降低通过错误信息枚举用户名的风险（简单防护）。

## 10.2 `CartService.addToCart`：UPSERT 与上限

逻辑步骤：

1. `ensureUser(userId)` — 用户必须存在；
2. `bookRepository.findById` — 书必须存在；
3. `findByUserIdAndBookId` — 有则取出行，无则 `new CartItem` 并设 `qty=0`；
4. `nextQty = min(oldQty + increment, 4)` — **业务规则**；
5. `save` — 持久化；
6. `getCartItems` — 返回全量列表（非仅新增行）。

数据库唯一索引与步骤 3 共同保证不会插入重复 `(userId, bookId)` 行。

## 10.3 `CartService.checkout`：跨服务编排

```93:104:springboot-ebook/src/main/java/com/ebook/backend/service/CartService.java
    public List<OrderResponse> checkout(Long userId) {
        ensureUser(userId);
        List<CartItem> selectedItems = cartItemRepository.findByUserId(userId)
                .stream()
                .filter(CartItem::getSelected)
                .toList();
        if (selectedItems.isEmpty()) {
            return List.of();
        }
        List<OrderResponse> createdOrders = orderService.createOrders(userId, selectedItems);
        cartItemRepository.deleteAll(selectedItems);
        return createdOrders;
    }
```

等价 SQL 语义（概念上）：

```sql
-- 1. 查 selected 的 cart_items
-- 2. INSERT INTO orders (...) 一条订单头
-- 3. INSERT INTO order_items (...) 每个选中商品一行
-- 4. DELETE FROM cart_items WHERE id IN (...)
```

**事务性说明**：方法未标注 `@Transactional`。`createOrders` 内 `saveAll` 与 `deleteAll` 可能在不同事务提交；极端情况下可能出现订单已创建但购物车未删。生产环境应在 `checkout` 上加 `@Transactional(rollbackFor = Exception.class)` 保证原子性（见附录 B）。

## 10.4 `OrderService.updateStatus`：状态机子集

```41:49:springboot-ebook/src/main/java/com/ebook/backend/service/OrderService.java
    public OrderResponse updateStatus(Long userId, String orderNo, String status) {
        ensureUser(userId);
        if (!List.of("pending", "paid", "cancelled").contains(status)) {
            throw new IllegalArgumentException("invalid status");
        }
        OrderEntity order = orderRepository.findByOrderNoAndUserId(orderNo, userId)
                .orElseThrow(() -> new ResourceNotFoundException("order not found: " + orderNo));
        order.setStatus(status);
        return toResponse(orderRepository.save(order));
    }
```

允许任意合法状态间跳转（未限制 `pending → paid` 单向）。课程演示足够；严格系统会定义转换表。

---

# 第十一部分 异常处理与错误语义

## 11.1 `@RestControllerAdvice` 的作用域

```11:12:springboot-ebook/src/main/java/com/ebook/backend/exception/ApiExceptionHandler.java
@RestControllerAdvice
public class ApiExceptionHandler {
```

该 Bean 对**所有** `@RestController` 生效。当 Controller 或 Service 抛出已注册异常，由对应 `@ExceptionHandler` 方法拦截，返回 `ResponseEntity`，**不会**落到 Tomcat 默认 HTML 错误页。

## 11.2 异常类型与 HTTP 状态映射

| 异常 | HTTP | 场景 |
|------|------|------|
| `IllegalArgumentException` | 400 Bad Request | 参数/业务规则违反（密码错误、qty 超范围） |
| `ResourceNotFoundException` | 404 Not Found | 书/用户/购物车行/订单不存在 |
| `MethodArgumentNotValidException` | 400 | `@Valid` 校验失败 |

`ResourceNotFoundException` 为自定义 unchecked 异常，继承 `RuntimeException`，无需在方法签名声明。

## 11.3 未捕获异常

若发生 `NullPointerException` 等，Spring Boot 默认 **500** 并返回 Whitelabel JSON（或 HTML，视 Accept 头）。本项目未自定义 `@ExceptionHandler(Exception.class)`。

---

# 第十二部分 跨域、安全模型与前后端协作

## 12.1 CORS 机制

浏览器**同源策略**阻止 `http://localhost:5173` 的 JS 直接读取 `http://localhost:8080` 的响应，除非目标服务器返回 CORS 头。

```15:19:springboot-ebook/src/main/java/com/ebook/backend/config/CorsConfig.java
                registry.addMapping("/api/**")
                        .allowedOrigins("http://localhost:5173")
                        .allowedMethods("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS")
                        .allowedHeaders("*");
```

`OPTIONS` 预检请求：对非简单请求（如 `Content-Type: application/json` 的 POST），浏览器先发 OPTIONS，Tomcat/Spring 返回允许的方法和源，再发真实请求。

`WebMvcConfigurer` 以 `@Bean` 注册，属于 Spring MVC 配置扩展点，而非 Servlet 过滤器手写 `Access-Control-Allow-Origin`。

## 12.2 当前「认证」模型（演示级）

**后端不维护 Session 或 JWT**。身份传递方式：

- 登录：`POST /users/login` 返回 `UserResponse`（含 `id`）；
- 后续：`/api/v1/cart/{userId}`、`/api/v1/orders/{userId}` 由前端在 URL 中填入 `userId`。

后端**信任**路径中的 `userId`，未校验请求是否来自该用户本人。任何知道 `userId=1` 的客户端都可操作 1 号用户的购物车——课程演示可接受，生产必须改为 Token 内嵌 subject 并与路径比对或取消路径中的 userId。

密码**明文**存储与比对，未使用 BCrypt。`User` 实体与 `users.password` 列直接对应。

## 12.3 与前端的契约（后端视角）

前端 `react-ebook/src/api/backendApi.js` 统一：

- Base URL：`VITE_API_BASE_URL` 或 `http://localhost:8080`；
- Header：`Content-Type: application/json`；
- 成功：`response.json()`；
- 失败：解析 `{ message }`。

路径与后端 Controller **一一对应**，例如：

```71:75:react-ebook/src/api/backendApi.js
export function addCartItem(userId, payload) {
  return request(`/api/v1/cart/${encodeURIComponent(userId)}/items`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}
```

`encodeURIComponent` 防止特殊字符破坏 URL。请求体 `bookId` 为 **数字**（Long），与库表 `books.id` 一致，而非前端早期的字符串 slug。

前端 `appStore` 在收到书列表后将 `id` 转为 `String` 便于 React key 与路由；发 API 时用 `Number(bookId)` 转回——这是**前端类型策略**，后端始终使用 Long。

---


## 12.4 前端 Fetch 配置要点

```javascript
// 典型 POST JSON（本项目 backendApi.js 模式）
await fetch(`${baseUrl}/api/v1/users/login`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ username, password }),
});
```

- 必须设置 `Content-Type: application/json` 才会触发 CORS **预检**（见 12.1）；
- 生产环境若使用 Cookie 会话，需 `credentials: "include"` 且后端配置具体 `allowedOrigins`；
- 演示项目使用 **localStorage 存 userId**，无 HttpOnly Cookie，故未启用 credentials。



# 第十三部分 完整请求生命周期示例

## 13.1 结算流程（端到端）

```text
[浏览器] 用户点击结算
    ↓ fetch POST /api/v1/cart/1/checkout
[Tomcat] 8080
    ↓
[DispatcherServlet]
    ↓
[CartController.checkout(1)]
    ↓
[CartService.checkout(1)]
    ├─ cartItemRepository.findByUserId(1)
    ├─ filter selected == true
    ├─ orderService.createOrders(1, items)
    │     ├─ new OrderEntity + 多个 OrderItem（单价快照）
    │     └─ orderRepository.save(order)  // 级联保存明细
    └─ cartItemRepository.deleteAll(selectedItems)
    ↓
[List<OrderResponse>] → JSON（通常仅 1 条，含 items 与 totalPrice）
    ↓
[浏览器] appStore 刷新 cart/orders，跳转订单页
```

## 13.2 登录流程与后续 API 依赖

```text
POST /api/v1/users/login
  → UserService 查 users 表
  → 返回 { id, username, email, ... }（无 password）

前端 setAuthenticatedUser → localStorage 存 userId

GET /api/v1/cart/{userId}
  → CartService.getCartItems
  → SELECT * FROM cart_items WHERE user_id = ?
```

## 13.3 图书列表的数据流

```text
GET /api/v1/books
  → BookService.findAll()
  → bookRepository.findAll()
  → Hibernate: select ... from books
  → List<Book> → JSON 数组

前端 normalizeBook：按 isbn 补 cover 字段（后端无此字段）
```

---

# 附录 A REST API 一览

| 方法 | 路径 | Controller 方法 | Service 核心 |
|------|------|-----------------|--------------|
| GET | `/api/v1/books` | `BookController.getAllBooks` | `BookService.findAll` |
| GET | `/api/v1/book/{id}` | `BookController.getBookById` | `BookService.findById` |
| POST | `/api/v1/users/register` | `UserController.register` | `UserService.register` |
| POST | `/api/v1/users/login` | `UserController.login` | `UserService.login` |
| GET | `/api/v1/users/{id}` | `UserController.getUser` | `UserService.getById` |
| PUT | `/api/v1/users/{id}` | `UserController.updateProfile` | `UserService.updateProfile` |
| GET | `/api/v1/cart/{userId}` | `CartController.getCart` | `CartService.getCartItems` |
| POST | `/api/v1/cart/{userId}/items` | `CartController.addItem` | `CartService.addToCart` |
| PATCH | `/api/v1/cart/{userId}/items/{bookId}` | `CartController.updateItem` | `CartService.updateCartItem` |
| DELETE | `/api/v1/cart/{userId}/items/{bookId}` | `CartController.removeItem` | `CartService.removeCartItem` |
| POST | `/api/v1/cart/{userId}/checkout` | `CartController.checkout` | `CartService.checkout` |
| GET | `/api/v1/orders/{userId}` | `OrderController.getOrders` | `OrderService.getOrders` |
| PATCH | `/api/v1/orders/{userId}/{orderNo}` | `OrderController.updateStatus` | `OrderService.updateStatus` |

---

# 附录 B 已知局限与可演进方向

| 议题 | 现状 | 演进建议 |
|------|------|----------|
| 事务 | `checkout` 多步无全局 `@Transactional` | 在 `CartService.checkout` 加事务注解 |
| 安全 | URL 中的 `userId` 可伪造 | Spring Security + JWT，从 Token 取 userId |
| 密码 | 明文 | `PasswordEncoder`（BCrypt） |
| 启动清库 | `sql.init.mode=always` | 生产改为 `never` + Flyway |
| 订单并发 | 无乐观锁 | `@Version` 或状态机 CAS |
| N+1 查询 | 购物车列表未 JOIN 书 | 可用 DTO 投影或 `@EntityGraph` |
| 封面 | 仅前端静态资源 | `books.cover_url` 或对象存储 URL |

---

**文档结束。** 本文将 Web 通信、Java 平台、Servlet/Spring 原理与电子书城项目实现融为一体；阅读时建议对照 `springboot-ebook/src/main/java` 与 `src/main/resources`。课程材料仅作知识来源，正文为整理后的技术说明。
