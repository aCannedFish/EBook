#!/usr/bin/env python3
"""Expand DOC.md by synthesizing course notes into structured sections (no raw paste)."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = Path("/tmp/doc_base.md").read_text(encoding="utf-8")


def replace_section(text: str, start_header: str, end_header: str, new_body: str) -> str:
    """Replace content between two ## headers (start inclusive as header line only)."""
    pattern = (
        rf"({re.escape(start_header)}\n)(.*?)(\n{re.escape(end_header)})"
    )
    m = re.search(pattern, text, flags=re.DOTALL)
    if not m:
        raise SystemExit(f"Section not found: {start_header!r} -> {end_header!r}")
    return text[: m.start()] + m.group(1) + new_body + m.group(3) + text[m.end() :]


def insert_before(text: str, marker: str, block: str) -> str:
    if marker not in text:
        raise SystemExit(f"Marker not found: {marker!r}")
    return text.replace(marker, block + "\n\n" + marker, 1)


HEADER = """# 电子书城后端技术文档（完整版）

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

"""

# Strip old header through first ---
old_header_end = BASE.find("\n---\n\n# 第零部分")
if old_header_end == -1:
    raise SystemExit("Cannot find 第零部分 in base doc")
doc = HEADER + BASE[old_header_end + len("\n---\n\n") :]

SEC_02 = """### 是什么

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

"""

SEC_03 = """### 是什么

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

"""

SEC_07 = """### 是什么

**连接池**预先创建若干条到数据库的 `Connection`，放在池中复用。请求来时**借**一条，用完**还**回池中，而不是每次请求都新建 TCP 连接并认证。

**HikariCP** 是 Java 生态中性能较好的一种连接池实现；Spring Boot 2+ 默认采用它。

若每次 HTTP 请求都 `new Connection()`，数据库端要反复握手、鉴权，高并发下会成为瓶颈。池化把连接成本摊到启动阶段，运行时主要做「借还」。

### 在本项目中的体现

启动日志中的 `HikariPool-1 - Starting...` 即池初始化。连接失败（库不存在、密码错误）时，池在启动阶段 `checkFailFast` 失败，应用无法就绪。业务线程从池中取连接 → JPA/Hibernate 执行 SQL → 归还连接；与「一连接一线程」的 Servlet 模型配合（见第六部分）。

---

"""

SEC_13 = """### 是什么

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

"""

SEC_19 = """### 是什么

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

"""

SEC_20 = """### 是什么

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

"""

NEW_021_024 = """## 0.21 浏览器异步通信与 Fetch API

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

"""

PART3_ADD = """
## 3.5 Jakarta 命名空间与 Spring Boot 3

Spring Boot 3 / Spring Framework 6 要求 **Jakarta EE 9+** API：持久化、Servlet、Validation 等包名均为 `jakarta.*`。若依赖仍引用 `javax.persistence`、`javax.servlet`，会在编译或运行时报 `ClassNotFoundException`。

迁移要点：

- 源码 import 全部改为 `jakarta.*`；
- 第三方库须使用兼容 Jakarta 的版本；
- 内嵌 Tomcat 版本须支持 Servlet 5+（Spring Boot 3 已对齐）。

本项目 `pom.xml` 使用 Spring Boot 3.2.4，实体与 DTO 校验均基于 Jakarta 注解。

"""

PART5_ADD = """
## 5.5 前端 Fetch 与后端 JSON 契约（协作要点）

| 环节 | 前端 | 后端 |
|------|------|------|
| 序列化 | `JSON.stringify` 写入 body | Jackson 反序列化为 DTO |
| 反序列化 | `response.json()` | Jackson 序列化返回值 |
| 错误 | 读 `message` 字段展示 | `ApiExceptionHandler` 统一 JSON 错误体 |
| 类型 | 书 id 在 UI 可为 string，发 API 时转 number | `Long bookId` 与表一致 |

异步流程不阻塞 React 渲染；失败时区分网络异常与 HTTP 4xx/5xx（见 [0.21](#021-浏览器异步通信与-fetch-api)）。

"""

PART12_ADD = """
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

"""

# Apply replacements
doc = replace_section(doc, "## 0.2 HTTP 与 REST", "## 0.3 JSON", SEC_02)
doc = replace_section(doc, "## 0.3 JSON", "## 0.4 关系型数据库与 MySQL", SEC_03)
doc = replace_section(doc, "## 0.7 连接池（以 HikariCP 为例）", "## 0.8 ORM、JPA 与 Hibernate", SEC_07)
doc = replace_section(doc, "## 0.13 Spring 框架与 Spring Boot", "## 0.14 IoC、依赖注入（DI）与 Bean", SEC_13)
doc = replace_section(doc, "## 0.19 CORS（跨域资源共享）", "## 0.20 Maven 与 Starter", SEC_19)
doc = replace_section(doc, "## 0.20 Maven 与 Starter", "## 0.21 事务（Transaction）概念", SEC_20)

doc = insert_before(doc, "## 0.21 事务（Transaction）概念", NEW_021_024)
doc = doc.replace("## 0.21 事务（Transaction）概念", "## 0.25 事务（Transaction）概念")
doc = doc.replace("## 0.22 `Optional` 与 `ResponseEntity`", "## 0.26 `Optional` 与 `ResponseEntity`")
doc = doc.replace("## 0.23 概念关系总览", "## 0.27 概念关系总览")

# Part 3: insert before # 第四部分
doc = insert_before(doc, "# 第四部分 分层架构与各层职责边界", PART3_ADD)

# Part 5: insert before # 第六部分
doc = insert_before(doc, "# 第六部分 数据持久化", PART5_ADD)

# Part 12: insert before # 第十三部分
doc = insert_before(doc, "# 第十三部分 完整请求生命周期示例", PART12_ADD)

# Footer
doc = doc.replace(
    "**文档结束。** 本文从依赖、配置、Web 层、ORM、Repository 代理、业务编排到前后端契约，按技术机制而非功能列表组织；阅读时建议对照 `springboot-ebook/src/main/java` 与 `src/main/resources` 下的对应文件。",
    "**文档结束。** 本文将 Web 通信、Java 平台、Servlet/Spring 原理与电子书城项目实现融为一体；阅读时建议对照 `springboot-ebook/src/main/java` 与 `src/main/resources`。课程材料仅作知识来源，正文为整理后的技术说明。",
)

(ROOT / "DOC.md").write_text(doc, encoding="utf-8")
print(f"Wrote {ROOT / 'DOC.md'} ({len(doc.splitlines())} lines)")
