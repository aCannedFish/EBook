---
title: Web后端03：Spring Boot
categories:
  - Note(Web)
tags:
  - Spring
  - Spring Boot
abbrlink: 8003
date: 2026-05-14 17:20:00
cover: /img/background3.png
katex: true
---

# 回放速记

## Spring Boot

- Spring Boot 是 Spring 的一部分
- 为什么需要内嵌服务器
- **业务逻辑 Business Logic**，很多不需要自己写代码，交给第三方，如 **JDBC**
- 前后端交互走 http 协议，后端和数据库交流需要一个连接，传递 SQL 语句
- 每次像 http 创建连接，完成后断掉，效率很低，怎么办？
- 维护一个实例池维护一系列连接。数据库请求连接时从池子中拿一个连接，完成后放回连接池。
- 连接池怎么管？链接需要复用，一个链接本质上是一个线程
- Java->SQL，SQL->Java对象
- **事务管理 Transaction**
- 原子操作，保证事务的完整性，同时完成或者失败
- **异步 Async**
- **安全 Security**
- 后端要有一套机制来管理用户的认证，授权和审计（AAA server，Authentication, Authorization, Auditing）
- 这套机制就是 Jakarta EE 中的规范，Spring 就是实现了这套规范的框架
- 实现这些功能就是遵循 J EE 的 Server，如 Tomcat，wildfly，它们属于一种中间件，在app和system之间提供了一个抽象层，提供了很多功能，如连接池，事务管理，安全等


## 部署

- .war 包 app 部署到 Tomcat 中
- Tomcat 需要一个配置文件，告诉它如何生成需要的服务的类，数据库的 url 和版本
- 运行流程：应用运行在Tomcat中。前端请求抵达时，Tomcat解析请求，找到对应的类并调用其方法。这种设计方法称之为proxy。一层层代理之后回到应用本身的某一个对象上。这一系列代理称之为应用的一个容器，它们将应用包裹起来，使其功能更加完备
- 配置文件：在maven中使用xml文件，即pom.xml。还有一张JSON-like写法的配置文件application.properties，告诉Spring Boot如何运行，如数据库的url，用户名和密码等
- Annotation：在Java中，注解是一种特殊的语法结构，用于在代码中添加元数据。Spring Boot使用注解来简化配置和开发过程。例如，@SpringBootApplication注解标记一个类为Spring Boot应用的入口点，@RestController注解标记一个类为RESTful控制器，@Autowired注解用于自动注入依赖等。通过使用注解，开发者可以更方便地配置和管理应用程序的组件和行为
- 注解不是给编译器看的，有无注解生成的字节码是一样的，注解是给框架看的，框架通过反射机制读取注解来决定如何处理代码中的类和方法。例如，Spring Boot会扫描带有特定注解的类，并根据这些注解来自动配置应用程序的组件和行为。这种方式使得开发者可以更专注于业务逻辑，而不需要编写大量的配置代码

## 运行

- 前端cpu占用少，主要渲染页面
- 后端cpu占用多，主要处理请求，访问数据库，执行业务逻辑等
- 当前端撑不住时，可以再启动一个前端实例，后端也可以启动多个实例来处理，但是这个时候面临如何管理这些实例的问题
- 后端实际上可以拆分成多个服务，以电子书城为例，可以拆分成用户服务，订单服务，库存服务等，每个服务都可以独立部署和扩展，这就是微服务架构
- 比如用户登录崩了，但是没登录的用户还可以浏览商品
- 容器，注册表，IP 透明（这部分没懂，需要详细介绍）

## 编译
 - JIT（Just-In-Time）编译器：Java虚拟机（JVM）在运行时会将字节码编译成机器码，以提高性能。JIT编译器会根据程序的运行情况动态优化代码，使得Java应用能够在保持平台无关性的同时获得接近原生代码的性能。这也是为什么Java应用在长时间运行后性能会逐渐提升的原因之一，因为JIT编译器会不断优化热点代码路径。
 - AOT 提前编译（Ahead-Of-Time Compilation）：与JIT编译不同，AOT编译是在应用程序运行之前将Java代码编译成机器码。这种方式可以减少应用程序启动时间，因为不需要在运行时进行编译。AOT编译适用于需要快速启动的应用场景，如微服务和云原生应用。Spring Boot 3.0引入了对AOT编译的支持，使得Spring Boot应用能够更快地启动和运行。

## 项目初始化

## API

- REST -> HTTP : GET, POST, PUT, DELETE
- HTTP -> url -> resource，资源有增删改查四个动作
- 描述性状态转移 REST：在前端和后端之间传递数据
- @PostMapping("/api/v1/users/register")：这个注解告诉Spring Boot，当有一个HTTP POST请求发送到/api/v1/users/register这个URL时，应该调用这个方法来处理请求。这个URL通常用于用户注册功能，前端会发送包含用户注册信息的POST请求到这个URL，后端会处理这个请求并返回相应的结果，如注册成功或失败的消息
- @GetMapping("/api/v1/books")：这个注解告诉Spring Boot，当有一个HTTP GET请求发送到/api/v1/books这个URL时，应该调用这个方法来处理请求。这个URL通常用于获取书籍列表的功能，前端会发送一个GET请求到这个URL，后端会查询数据库中的书籍信息并返回给前端，以供显示或进一步处理
- @RequestBody：这个注解告诉Spring Boot，从HTTP请求的正文中提取数据，并将其转换为方法参数的类型。例如，在用户注册的场景中，前端会发送一个包含用户信息的JSON对象作为POST请求的正文，后端使用@RequestBody注解将这个JSON对象转换为一个UserDTO对象，方便在方法中使用和处理用户注册逻辑
- 应当将 url 看成一种资源，而不是一个动作。对于资源的操作应该使用HTTP方法来表达，如GET表示获取资源，POST表示创建资源，PUT表示更新资源，DELETE表示删除资源。这种设计原则使得API更加符合RESTful风格，易于理解和使用。例如，/api/v1/users/register这个URL应该被视为一个用户注册资源，而不是一个特定的动作，这样可以更好地利用HTTP方法来表达不同的操作意图。
- 不要使全部使用@RequestMapping来映射，原因：
  - 语义不清晰：@RequestMapping是一个通用的注解，可以用于映射任何HTTP方法，这可能会导致代码的可读性降低。使用特定的注解（如@GetMapping、@PostMapping等）可以更清晰地表达方法的意图和用途。
  - 错误风险：使用@RequestMapping时，如果忘记指定HTTP方法，可能会导致方法被错误地映射到多个HTTP方法上，增加了出错的风险。使用特定的注解可以避免这种情况，提高代码的健壮性。
  - 维护困难：当项目规模较大时，使用@RequestMapping可能会使得代码难以维护和理解，因为开发者需要额外的时间来确定每个方法处理的是哪个HTTP方法。使用特定的注解可以简化这一过程，提高开发效率。

## 环境隔离

- 用内存数据库快速验证程序正确性，可以写多个不同的配置文件，运行时激活不同的配置文件来切换数据库
- 运行时有命令行参数，可以使用参数来指定配置文件，开发和运行使用不同的文件

## Controller

- Service 层：处理核心业务逻辑，如用户注册、查询书籍等
- Dao 层：负责与数据库进行交互，执行SQL查询和更新操作
- Service 是一个接口，创建不了实例，找不到实现时会在整个工程中找这个Service的实现类.Spring根据注释来找到实现类，将对象的引用注入到Controller中，这个过程叫做依赖注入（Dependency Injection）。通过这种方式，Controller不需要关心Service的具体实现细节，只需要依赖于Service接口即可，这样可以提高代码的灵活性和可维护性。
- 如果有多个Service实现类，可以用 XXServiceImpl implements XXService 来命名实现类
- 代码需要分层，做接口和实现的分离，接口是稳定的
- Controller接到请求后发给Service，Service处理完业务逻辑后调用Dao层进行数据库操作，最后将结果返回给Controller，由Controller将结果返回给前端。这种分层设计使得代码结构清晰，职责分明，易于维护和扩展
- 传送数据方法：1.路径，2.问号，键值对，3.Body，不是明文，不会被看到

## Spring MVC

- 三种前后端传递参数的途径
  - 路径参数：/api/v1/book/{id}，通过@PathVariable注解获取路径中的参数值
  - 查询参数：/api/v1/books?author=xxx&title=yyy，通过@RequestParam注解获取查询参数的值
  - 请求体参数：通过@RequestBody注解获取请求体中的数据，通常用于POST或PUT请求，数据格式可以是JSON、XML等

## Spring Data JPA

## Entity & Repository

- Entity：数据库表的映射类，使用@Entity注解标记，定义表结构和字段
- Repository：数据访问层接口，继承JpaRepository，提供基本的CRUD操作，无需实现类，Spring Data JPA会自动生成实现类
- 通过定义Repository接口，Spring Data JPA会根据方法命名规则自动生成查询方法，例如findByUsername、findByEmail等，这些方法会根据方法名中的属性自动构建SQL查询语句
- Repository接口还支持自定义查询方法，可以使用@Query注解编写JPQL

## Spring Boot Actuator

# AI 重整理

## Web应用程序架构概览

在现代软件工程中，Web应用程序的开发基于经典的请求-响应（Request-Response）编程模型，其架构设计通常遵循两种主要范式：面向展现的应用程序（Presentation-oriented）与面向服务的应用程序（Service-oriented）。面向展现的Web应用程序主要职责是响应客户端的请求，动态生成包含各种标记语言（如HTML、XHTML、XML）以及动态交互内容的Web页面 。相反，面向服务的Web应用程序则致力于实现Web服务端点，作为后端数据处理核心，通过标准协议（通常返回JSON或XML格式的数据）为各类客户端提供服务 。在实际架构中，面向展现的应用程序往往作为面向服务的应用程序的直接客户端，两者协同构建出复杂的分布式系统 。

一个标准的Web应用程序是一个复合的工程实体，它由多个关键部分构成，包括执行核心业务逻辑的Web组件、用于构建用户界面的静态资源文件（如图像、级联样式表CSS、客户端脚本）以及各种辅助类和第三方类库 。这些组件无法独立运行，它们必须依赖于Web容器（Web Container）所提供的底层支持服务 。Web容器不仅提供了网络套接字的监听与协议解析，还为Web组件提供了生命周期管理、线程池调度、安全上下文以及并发控制等基础服务 。正因为应用程序必须与这些容器服务深度集成，开发和运行Web应用程序的流程与执行传统的独立Java类存在着本质的差异 。

Web应用程序的生命周期遵循一套严谨的规范流程。开发人员首先需要编写Web组件的源代码，并在必要时配置Web应用程序的部署描述符（Deployment Descriptor）。随后，编译器将组件及引用的辅助类编译为字节码，并打包成一个可部署的单元（通常为WAR格式的文件）。将该部署包部署至Web容器后，客户端即可通过统一资源定位符（URL）引用并访问该Web应用程序 。

## Java Servlet核心技术深度解析

在Java Web生态系统的底层，Servlet技术扮演着不可替代的基础性角色。Servlet是一个采用Java编程语言编写的类，其核心设计目的是扩展那些通过请求-响应模型访问应用程序的服务器的功能 。理论上，Servlet技术可以响应任何类型的网络请求，但在实际的工程实践中，它最常用于扩展由Web服务器托管的应用程序，专门用于处理基于超文本传输协议（HTTP）的网络流量 。Java Servlet技术为这一目的定义了专门针对HTTP的Servlet类和接口 。

### Servlet API与组件抽象

为了支持Servlet的开发，Java平台提供了专用的API包。在传统的Java EE规范中，开发Servlet所需的接口和类主要封装在`javax.servlet`和`javax.servlet.http`包中 。`Servlet`接口是整个Java Servlet API的中心抽象，规范要求所有的Servlet组件必须直接实现该接口，或者更常见地，继承一个已经实现了该接口的基础抽象类 。

API设计了两个主要的抽象类以应对不同的协议需求：

|**抽象类名称**|**协议依赖性**|**核心应用场景**|
|---|---|---|
|`GenericServlet`|协议无关|当开发人员需要实现通用的、不依赖于特定网络协议的后台服务时，继承此抽象类 。|
|`HttpServlet`|依赖HTTP协议|在大多数基于HTTP的Web开发场景中被广泛继承。它提供了专门的方法来处理HTTP规范中的不同请求动作 。|

在现代Web开发中，被注解定义为Servlet的类必须继承`javax.servlet.http.HttpServlet`类（或在最新规范中的`jakarta.servlet.http.HttpServlet`类）。

### Web容器的事件处理序列

Web容器作为Web服务器与Servlet代码之间的桥梁，负责高度协调的事件处理序列。一次典型的客户端与服务器的交互流程如下所述 ：

首先，客户端（如Web浏览器）向Web服务器发起HTTP请求。Web服务器接收到该网络请求后，将其移交给后端的Servlet容器 。值得注意的是，Servlet容器的部署拓扑非常灵活，它可以与宿主Web服务器运行在同一个操作系统进程中，也可以在同一台主机的不同进程中运行，甚至可以部署在完全不同的物理或虚拟主机上 。

容器接收到请求后，会根据其内部维护的路由配置表（URL映射规则）决定需要调用哪一个具体的Servlet组件。为了将网络数据传递给Java代码，容器会实例化两个至关重要的对象：一个代表客户端请求的请求对象，以及一个代表服务器响应的响应对象 。随后，容器调用目标Servlet，并将这两个对象作为参数传递给它 。

Servlet通过操作请求对象，可以提取出大量与请求相关的上下文细节，例如远程用户的身份认证信息、HTTP POST请求体中的参数以及其他协议元数据 。在提取信息后，Servlet将执行预先编写的业务逻辑算法，并生成需要返回给客户端的数据。这些数据被写入到响应对象中 。一旦Servlet的代码执行完毕并返回控制权，Servlet容器将确保响应缓冲区被正确刷新，随后将控制权交还给宿主Web服务器，最终由服务器将格式化后的HTTP响应报文发送回客户端 。

## 请求处理机制与生命周期控制

### Servlet的生命周期管理

Servlet的生命周期并不由开发人员在代码中显式控制，而是完全由部署该组件的Web容器接管。当一个网络请求被映射到某个特定的Servlet时，容器会执行一系列标准化的生命周期步骤 。

如果目标Servlet的实例尚未在内存中创建，容器将启动完整的初始化序列 ： 首先，容器使用类加载器将Servlet的字节码类加载至JVM内存中。接着，容器通过反射机制创建该Servlet类的一个新实例 。在实例创建完成但在处理任何客户端请求之前，容器会调用该实例的`init`方法 。`init`方法的调用标志着初始化阶段的开始，开发人员可以通过重写`Servlet`接口的`init`方法或利用注解属性来自定义这一过程 。该阶段主要用于让Servlet读取持久化的配置数据、建立数据库连接池、初始化必须的系统资源以及执行其他一次性的启动任务 。如果Servlet在此阶段无法完成其初始化流程（例如数据库连接失败），它必须抛出一个`UnavailableException`异常，以此通知容器该组件当前不可用，无法提供服务 。

一旦初始化成功完成，容器就会调用该Servlet的`service`方法，并将之前构建的请求和响应对象传递给它 。在Servlet的整个生命周期中，`service`方法可能会被多个并发线程多次调用，以处理不同的客户端请求。

当容器认为需要移除某个Servlet时（例如服务器准备关闭，或者应用程序被卸载），它会通过调用该Servlet的`destroy`方法来完成最终的清理工作 。这为Servlet提供了一个释放内存、关闭后台工作线程以及断开外部资源连接的安全窗口。

### HTTP特定请求的处理策略

`HttpServlet`类为处理基于HTTP的请求提供了一套专门的方法，这些方法直接对应于HTTP协议中定义的标准动作（Verbs）。默认情况下，`HttpServlet`的`service`方法会解析传入请求的HTTP方法类型，并自动将其分发给相应的专用处理方法 ：

|**方法名称**|**HTTP动作**|**处理语义与应用场景**|
|---|---|---|
|`doGet`|GET|处理HTTP GET请求。根据RESTful规范，此方法应当是幂等的，仅用于数据的获取与查询，不应产生服务器状态的变更 。|
|`doPost`|POST|处理HTTP POST请求。用于客户端向服务器提交需要被处理的数据，通常会导致服务器状态的改变或新资源的创建 。|
|`doPut`|PUT|处理HTTP PUT请求。主要用于更新或替换服务器上的现有资源 。|
|`doDelete`|DELETE|处理HTTP DELETE请求。用于指示服务器删除指定的资源 。|
|`doHead`|HEAD|处理HTTP HEAD请求。类似于GET，但服务器在响应中只返回HTTP头部信息，不返回响应主体，常用于验证资源是否存在或检查文件更新时间 。|
|`doOptions`|OPTIONS|处理HTTP OPTIONS请求。用于客户端询问服务器支持哪些HTTP通信选项和方法，常用于跨域资源共享（CORS）的预检请求 。|
|`doTrace`|TRACE|处理HTTP TRACE请求。这是一种诊断性的请求，服务器需在响应主体中将接收到的请求报文原样返回给客户端，用于网络链路测试 。|

在常规的基于HTTP的Servlet开发中，开发人员通常只需要关注并重写`doGet`和`doPost`方法，即可满足绝大部分的业务需求 。

### HTTP Trailer的流式处理

随着现代Web应用对协议的深入利用，Servlet技术规范也增加了对分块传输编码（Chunked Transfer Encoding）中HTTP Trailer（尾部头字段）的支持。在分块传输模式下，某些响应或请求的头部信息在消息体发送完毕之前是无法确定的（例如数字签名或内容校验和）。

当Servlet需要读取HTTP请求的Trailer字段时，必须首先调用`HttpServletRequest`接口中的`isTrailerFieldsReady()`方法来检查尾部字段是否已经准备好被读取 。如果该方法返回`true`，Servlet即可通过`getTrailerFields`方法获取这些字段；如果在尚未就绪时强行读取，方法将抛出`IllegalStateException`异常 。

同理，Servlet也可以向响应中写入Trailer字段。这要求开发人员向`HttpServletResponse`接口的`setTrailerFields()`方法提供一个供应器（Supplier）。需要严格遵守的是，某些特定的头部信息绝对不能包含在传递给`setTrailerFields()`的Map键集合中，包括`Transfer-Encoding`、`Content-Length`、`Host`、缓存控制头、认证头、`Content-Encoding`、`Content-Type`、`Content-Range`以及`Trailer`本身 。发送带有Trailer的响应时，必须在常规头部中包含一个名为`Trailer`的字段，其值为即将发送的尾部键的逗号分隔列表，以此告知客户端期望接收哪些尾部信息 。

## 高级组件：过滤器与监听器

在复杂的Web后端架构中，除了直接处理请求的Servlet外，还需要处理大量横切关注点（Cross-cutting Concerns），如安全审计、请求数据压缩、统一字符编码转换等。此外，监控应用程序级的状态变动也是必不可少的。为此，Servlet规范引入了过滤器（Filters）和监听器（Listeners）两种高级组件。

### Servlet过滤器（Filters）

Servlet过滤器是一种用于拦截客户端请求并进行预处理，以及拦截服务器响应并进行后处理的可插拔组件 。过滤器本身并不产生直接响应，而是依附于特定的请求路径，对流经的数据进行审查和修改 。

过滤器的核心功能包括 ：

- 在目标Servlet被调用之前拦截其调用过程。
    
- 在请求到达Servlet之前检查HTTP请求头（如进行身份认证令牌的校验）。
    
- 通过提供封装了原始请求的定制化请求包装器（Wrapper对象），修改请求的头部和数据体内容。
    
- 通过提供定制化的响应包装器，修改响应的头部和数据，实现例如响应体GZIP压缩或数据加密的功能。
    
- 在目标Servlet执行完毕后，拦截响应离开容器的过程。
    

实现一个过滤器必须实现`javax.servlet.Filter`接口，该接口定义了三个贯穿过滤器生命周期的方法 ：

1. `init(FilterConfig filterConfig)`：当容器实例化过滤器时，该方法被调用。它在过滤器的生命周期中仅执行一次，开发人员应当在此方法中初始化任何需要的持久化资源，并保存传递进来的配置对象 。
    
2. `doFilter(ServletRequest request, ServletResponse response, FilterChain chain)`：这是过滤器执行实际过滤工作的核心方法。每当容器判定需要将过滤器应用于某个请求时，便会调用此方法 。该方法内部的逻辑执行被`chain.doFilter()`切分为两个阶段。在调用`chain.doFilter()`之前编写的代码属于请求到达Servlet之前的预处理阶段；而紧跟在`chain.doFilter()`之后的代码则属于Servlet执行完毕后的后处理阶段 。`FilterChain`对象负责将请求传递给拦截链中的下一个过滤器，若当前过滤器已是链条中的最后一个，则传递给目标Servlet 。
    
3. `destroy()`：当容器决定将过滤器实例从服务中卸载时，会调用此方法，以便过滤器执行相关的资源销毁和内存回收逻辑 。
    

### 过滤器的代码实践与注解配置

现代Java Web开发摒弃了繁琐的XML配置，转而大量使用注解来声明和配置过滤器。Servlet 3.0规范引入了`@WebFilter`注解，允许开发者直接在实现类上定义过滤器的拦截规则 。

Java

```
import javax.servlet.*;
import javax.servlet.annotation.WebFilter;
import javax.servlet.annotation.WebInitParam;
import java.io.IOException;

// 使用@WebFilter注解配置过滤器，并通过initParams注入初始化参数
@WebFilter(filterName = "TimeOfDayFilter", urlPatterns = {"/*"}, initParams = {
    @WebInitParam(name = "mood", value = "awake")
})
public class TimeOfDayFilter implements Filter {
    
    private String defaultMood;

    @Override
    public void init(FilterConfig filterConfig) throws ServletException {
        // 读取注解中定义的初始化参数
        this.defaultMood = filterConfig.getInitParameter("mood");
        System.out.println("TimeOfDayFilter Initialized with mood: " + defaultMood);
    }

    @Override
    public void doFilter(ServletRequest request, ServletResponse response, FilterChain chain) 
            throws IOException, ServletException {
        // 预处理阶段：在请求到达Servlet之前执行
        System.out.println("Before filter - Preprocessing before servlet");
        
        // 可在此处加入认证逻辑或修改请求数据
        
        // 将请求沿责任链向下传递，交由下一个过滤器或最终的Servlet处理
        chain.doFilter(request, response);
        
        // 后处理阶段：在Servlet执行完毕后执行
        System.out.println("After servlet - Following code will execute after running the servlet - PostProcessing");
    }

    @Override
    public void destroy() {
        // 资源清理逻辑
    }
}
```

在上述代码中，`@WebFilter`注解指定了拦截模式`urlPatterns = {"/*"}`，这意味着该过滤器将拦截所有到达应用程序的请求 。`initParams`属性包含了一个`@WebInitParam`注解，用于为该过滤器设置特定的初始化参数 。需要强调的是，过滤器使用的初始化参数仅针对该过滤器实例可见，这与所有组件共享的上下文参数（Context Parameter）截然不同 。

### Servlet监听器（Listeners）

如果说过滤器是对数据流的干预，那么监听器则是对状态变动的观察。监听器类实现了特定的接口，用于在Web应用程序的作用域对象（如`ServletContext`、`HttpSession`、`ServletRequest`）发生创建、销毁或属性修改等生命周期事件时进行响应 。

例如，`ServletContextListener`用于监听整个Web应用程序上下文的启动和关闭事件，这使其成为初始化全局数据库连接池的理想场所。而`HttpSessionListener`则用于监控用户会话的创建与销毁，常被用于统计当前在线用户数或审计会话的存活时长 。

Java

```
import javax.servlet.ServletContextEvent;
import javax.servlet.ServletContextListener;
import javax.servlet.http.HttpSessionEvent;
import javax.servlet.http.HttpSessionListener;
import javax.servlet.annotation.WebListener;

@WebListener
public class SessionLifeCycleEventExample implements ServletContextListener, HttpSessionListener {

    public SessionLifeCycleEventExample() {
        // 监听器类必须包含一个无参构造函数
    }

    // ServletContextListener 接口方法
    public void contextInitialized(ServletContextEvent sce) {
        System.out.println("Application Context Initialized");
    }

    public void contextDestroyed(ServletContextEvent sce) {
        System.out.println("Application Context Destroyed");
    }

    // HttpSessionListener 接口方法
    public void sessionCreated(HttpSessionEvent hse) {
        String sessionId = hse.getSession().getId();
        System.out.println("CREATE, SessionID:" + sessionId);
    }

    public void sessionDestroyed(HttpSessionEvent hse) {
        long start = hse.getSession().getCreationTime();
        long end = hse.getSession().getLastAccessedTime();
        System.out.println("DESTROY, Session Duration:" + (end - start) + "ms");
    }
}
```

通过添加`@WebListener`注解，容器在启动时会自动扫描并注册该类，无需进行额外的XML配置 。

### 组件协同运作实例：Mood应用程序

为了清晰展示Servlet、过滤器与监听器如何协同工作，Java EE官方教程提供了一个名为“Mood”的综合示例应用程序 。该应用程序位于`jakartaee-examples/tutorial/web/servlet/mood/`目录下，旨在根据一天中的不同时间动态展示角色（Duke）的心情状态 。

该示例应用程序由三个核心组件构成 ：

1. **`mood.web.MoodServlet`**：作为应用程序的展现层，该类继承自`HttpServlet`，并使用`@WebServlet("/report")`指定了URL路由模式。它的主要任务是生成HTML页面，显示描述Duke心情的文本字符串和相关的插图说明 。
    
2. **`mood.web.TimeOfDayFilter`**：该过滤器拦截所有请求（`/*`）。在其`doFilter`方法内部包含一个`switch`控制语句，它根据当前服务器的时间条件动态设定Duke的心情，并通过初始化参数表明角色的初始清醒状态 。
    
3. **`mood.web.SimpleServletListener`**：该监听器在后台静默运行，负责将Servlet生命周期中发生的所有变动事件记录下来，这些日志条目最终会输出在应用服务器的系统日志控制台中 。
    

当用户在Web浏览器中访问指定的URL（例如`http://localhost:8080/mood/report`，其中包含应用程序上下文根路径和Servlet模式）时，浏览器会触发完整的处理链 。请求首先被`TimeOfDayFilter`拦截并处理，随后由`MoodServlet`生成带有特定标题（“Servlet MoodServlet at /mood”）的页面，同时监听器在后台记录下整个流程的事件轨迹 。

## 基于XML的部署描述符配置

尽管现代应用大量采用注解来声明Web组件，但在处理基于Servlet 2.5及更早版本规范的遗留系统，或是需要进行高度集中化的灵活配置时，使用`web.xml`部署描述符（Deployment Descriptor）仍然是标准的工程实践 。

`web.xml`文件定义了Web组件及其运行配置信息，并在XML模式（Schema）文档的约束下编写 。该文件必须严格放置在Web应用程序目录结构的`WEB-INF/`子目录下 。在这个文件内，开发人员可以配置URL路径与处理这些路径请求的Servlet之间的映射规则，定义哪些URL需要进行安全身份验证，以及声明其他诸多配置参数 。

一个典型的Servlet映射配置需要在`web.xml`中完成两个维度的声明：物理组件的注册与逻辑路由的绑定 。

首先，利用`<servlet>`元素定义Servlet实例。此元素必须包含`<servlet-name>`以分配一个应用内的唯一引用名称，同时通过`<servlet-class>`指明该Servlet对应的Java类的完整包路径 。

其次，利用`<servlet-mapping>`元素将前面定义的引用名称与具体的URL模式相连接。`<servlet-name>`子元素必须与前面定义的名字完全对应，而`<url-pattern>`子元素则描述了用于解析和匹配HTTP请求路径的模式 。当Web容器接收到请求时，它会截取请求URL中位于`http://host:port`和`ContextPath`之后的部分，并将其与配置的`<url-pattern>`进行精确匹配或模式匹配（例如使用通配符`/*`或扩展名匹配`*.foo`）。如果匹配成功，映射的Servlet便会被调用 。

XML

```
<web-app xmlns="http://xmlns.jcp.org/xml/ns/javaee" 
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
         xsi:schemaLocation="http://xmlns.jcp.org/xml/ns/javaee http://xmlns.jcp.org/xml/ns/javaee/web-app_3_1.xsd" 
         version="3.1">

    <servlet>
        <servlet-name>comingsoon</servlet-name>
        <servlet-class>mysite.server.ComingSoonServlet</servlet-class>
    </servlet>

    <servlet-mapping>
        <servlet-name>comingsoon</servlet-name>
        <url-pattern>/*</url-pattern>
    </servlet-mapping>

    <welcome-file-list>
        <welcome-file>index.jsp</welcome-file>
        <welcome-file>index.html</welcome-file>
    </welcome-file-list>
</web-app>
```

除了组件映射，`web.xml`还可以包含`<welcome-file-list>`元素，该元素定义了所谓的“欢迎文件列表” 。当客户端请求的URL指向一个目录层级而非具体的资源文件时，Web服务器会自动按序查找该列表中的文件（如`index.jsp`或`index.html`），以将其作为默认页面返回 。此外，描述符中还支持大量其他的全局配置标签，如用于定义应用级变量的`<context-param>`、定义错误处理页面的`<error-page>`、定义会话超时的`<session-config>`以及用于资源和环境条目引用的`<resource-env-ref>`和`<env-entry>`等 。部署描述符在应用程序的配置与部署阶段被服务器的核心功能组件读取，对其进行的修改可能需要在服务器组装工具中重新打包或重启容器才能生效 。

## Spring框架演进与现代编程模型

随着互联网业务复杂度的指数级增长，原生Servlet API虽然提供了底层控制能力，但暴露出了严重的开发效率瓶颈。开发人员被迫在每一个组件中编写大量重复的模板化代码（Boilerplate Code），以处理诸如数据库连接创建、事务边界划定、JSON序列化与反序列化以及复杂的异常捕获逻辑。此外，基于XML的配置文件也随着工程规模的扩大而变得难以维护。

为了解决这些痛点，Spring框架应运而生。Spring的设计宗旨是使Web应用程序的开发变得快速且无忧（Fast and hassle-free）。它引入了一种彻底现代化的编程模型，通过控制反转（IoC）和面向切面编程（AOP）机制，极大地消除了冗长的模板代码和繁重的显式配置要求 。这种架构简化了服务端HTML页面渲染应用、高并发RESTful API接口以及基于事件的双向通信系统的构建流程 。

不仅如此，Spring还围绕Web开发生态构建了多个核心模块。例如，Spring Security模块提供了久经沙场考验的应用程序安全防护机制，能够无缝支持包括SAML、OAuth和LDAP在内的工业级标准认证协议，保障Web应用程序的访问安全 。在数据访问层面，Spring极大地降低了数据持久化的操作门槛，通过高度抽象的接口，使得应用程序能够轻松连接至关系型数据库、非关系型（NoSQL）数据存储、Map-Reduce计算框架以及基于云架构的数据服务平台 。

## Spring Boot核心机制与依赖管理

尽管Spring框架大幅简化了代码层面的逻辑，但它依然需要依赖极其复杂的依赖库管理以及对外部应用服务器（如独立部署的Tomcat容器）的繁琐配置。为了扫除这最后一道障碍，Spring Boot技术横空出世。Spring Boot的根本目的是让开发人员能够以“最小的麻烦”（Minimum fuss）和极少的预先配置，快速创建出可以独立运行的、达到生产级质量标准的Spring驱动应用程序 。

### 构建工具支持与版本要求

在进行Spring Boot开发之前，开发环境必须满足严格的技术准入条件。系统环境内必须安装并正确配置了支持的Java版本，开发人员需在终端运行`$ java -version`以确认其可用性 。同时，项目管理需要依赖构建自动化工具。Spring Boot官方支持以下工具及版本 ：

- **Maven**：版本需为3.3或以上（通过`$ mvn -v`验证）。
    
- **Gradle**：版本需为6系列（6.3或更高版本）。虽然框架在底层仍然支持5.6.x版本，但这已经被官方标记为过时（Deprecated），不再推荐用于新项目。
    

### 依赖注入与项目对象模型（POM）机制

在基于Maven的Spring Boot项目中，所有的配置管理起点都是项目根目录下的`pom.xml`（Project Object Model）文件。Spring Boot创新性地引入了“Starter”（启动器）机制。Starter实际上是一组预先配置好的依赖描述符，它将特定功能场景下所需的所有第三方库打包在一个依赖引用中，从而避免了版本冲突并简化了配置。

为了搭建一个支持Web开发的后端工程，开发人员只需在`pom.xml`文件的依赖区块中，通常位于`<parent>`区块的下方，添加`spring-boot-starter-web`依赖项 。

XML

```
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-web</artifactId>
</dependency>
```

仅仅通过引入这一项依赖，Maven工具链就会在后台自动解析并下载构建REST API所需的所有核心模块，包括Spring MVC框架组件、处理JSON转换的Jackson库、数据验证框架，以及更为核心的——一个内嵌的应用程序容器 。

## 内嵌式Web容器选型与性能对比

在传统的Servlet部署模式中，Web应用程序被打包为WAR文件，并上传至远程的容器服务器中运行。Spring Boot彻底颠覆了这一模式，它的每个Web应用程序启动器默认都在应用程序包内包含了一个内嵌的Web服务器（Embedded Web Server）。这意味着应用程序本身就是一个可直接启动的独立进程。

对于Servlet技术栈的应用程序，`spring-boot-starter-web`模块通过传递依赖，默认引入了Apache Tomcat服务器 。然而，Spring Boot的架构高度解耦，允许开发人员轻松替换掉默认容器，转而使用其他具有不同性能特征的引擎，如Jetty或Undertow 。

官方支持的内嵌容器规格如下表所示 ：

|**内嵌容器引擎**|**容器支持版本**|**支持的Servlet规范版本**|**特性分析与应用场景**|
|---|---|---|---|
|**Tomcat**|9.0|4.0|作为业界标准，历史最悠久，运行最为稳定可靠。在需要极致的安全性和稳定性保障的企业级应用中是首选 。|
|**Jetty**|9.4|3.1|相对轻量级，启动速度快。由于其对Servlet 4.0标准的支持存在滞后，其主要活跃于要求快速响应和机器间（M2M）通信的微型服务场景中 。|
|**Undertow**|2.0|4.0|采用了基于非阻塞I/O的高性能架构设计。在面对极端高并发吞吐量需求的应用时，表现出极佳的处理性能 。|

在工程实践中，各大容器在常规业务负载下的表现差异通常并不显著。然而，在严格的基准测试环境中，它们的资源消耗和性能表现呈现出细微的区别 。例如，在内存利用率指标上（jvm.memory.used），Tomcat（168MB）与Undertow（164MB）相近，而Jetty（155MB）的占用相对更为精简 。在并发处理能力上，Undertow在每秒处理请求数（Requests per second）和平均单次请求耗时（ms）这两个核心吞吐量指标上，通常均优于Tomcat和Jetty 。尽管如此，在复杂的企业级架构和大规模（100+服务器）集群部署中，由于Servlet及Spring的抽象层屏蔽了绝大部分底层细节，容器的具体实现通常不会成为业务瓶颈 。

如果由于特定的架构规划需要将底层容器替换为Jetty，开发人员必须在`pom.xml`中对原有的`spring-boot-starter-web`依赖进行修改，利用`<exclusions>`标签显式排除掉Tomcat的启动器包，并引入Jetty的启动器包 。由于Jetty 9.4版本不支持Servlet 4.0，可能还需要在属性中覆盖Servlet API的版本 。

XML

```
<properties>
    <servlet-api.version>3.1.0</servlet-api.version>
</properties>

<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-web</artifactId>
    <exclusions>
        <exclusion>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-tomcat</artifactId>
        </exclusion>
    </exclusions>
</dependency>
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-jetty</artifactId>
</dependency>
```

## 基于Spring Data JPA的数据持久化架构

处理关系型数据库的持久化操作是Web后端的重中之重。Spring Boot通过提供`spring-boot-starter-data-jpa`依赖模块，极大地简化了基于Java持久化API（JPA）的数据库交互流程 。在底层实现中，Spring的控制反转（IoC）容器负责管理和注入`EntityManager` Bean对象，而具体的数据处理、实体变更跟踪以及与数据库之间的数据同步则通常由Hibernate框架这一具体的持久化提供商来负责执行 。

在构建基于REST API的数据交互系统时，业界通常遵循一套严谨的四层架构设计模式：控制器层（Controller）负责处理HTTP请求并组装响应、服务层（Service）封装核心业务逻辑、存储库层（Repository）管理与数据库的直接通信，实体层（Entity）则用于映射数据库的底层表结构 。

### 实体层（Entity Layer）设计

实体类是纯粹的Java对象（POJO），通过各类注解将其结构直接映射为关系型数据库中的表。

- `@Entity`：该核心注解向JPA声明当前的类是一个需要被框架进行生命周期管理的持久化实体类，可以被映射至数据库 。
    
- `@Table`：允许开发者指定表级别的元数据，例如通过`name`参数强制设定该实体对应的数据库表名 。
    
- `@Id`：指示类中被修饰的成员字段是当前实体的唯一标识符（即主键）。
    
- `@GeneratedValue(strategy = GenerationType.IDENTITY)`：声明该主键的生成策略，此处设定为由底层数据库自带的自动递增（Auto-increment）机制来生成主键值 。
    
- `@Column`：用于进一步详细指定数据库列的属性（如是否允许为空、长度限制等）。
    

Java

```
package com.example.demo.entity;

import jakarta.persistence.*;

@Entity
@Table(name = "users")
public class User {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    
    @Column(nullable = false)
    private String name;
    
    private String email;
    private int age;

    // 为了符合JPA规范，必须提供一个无参构造函数
    public User() {}

    public User(String name, String email, int age) {
        this.name = name;
        this.email = email;
        this.age = age;
    }

    // 省略属性的Getters和Setters方法...
}
```

### 存储库层（Repository Layer）设计

存储库层的设计是Spring Data JPA消除模板代码的精髓所在。开发人员无需编写复杂的JDBC查询或数据访问对象（DAO）实现类，只需声明一个接口即可自动获得完整的增删改查（CRUD）功能 。

通过继承`JpaRepository<T, ID>`或其父接口`CrudRepository<T, ID>`（其中泛型参数`T`代表实体类的类型，`ID`代表主键字段的类型），该接口将自动继承一系列预定义的数据库操作方法，如`save()`、`findById()`、`findAll()`和`deleteById()` 。通常在接口上方使用`@Repository`注解将其标识为Spring管理的组件 。Spring框架在应用程序启动时，利用动态代理技术自动为该接口生成具体的实现类。

Java

```
package com.example.demo.repository;

import com.example.demo.entity.User;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

// 继承JpaRepository，自动获得针对User实体以Long为主键的所有CRUD方法
@Repository
public interface UserRepository extends JpaRepository<User, Long> {
}
```

### 数据库连接与底层配置

所有组件间的协同工作依赖于准确的环境配置。开发人员需要在工程资源目录下的`application.properties`文件中，明确指定数据库的连接参数与Hibernate框架的行为策略 。

Properties

```
# 设定JDBC驱动的连接URL，指定连接本机的MySQL数据库实例
spring.datasource.url=jdbc:mysql://localhost:3306/userdb
# 数据库访问账户认证信息
spring.datasource.username=root
spring.datasource.password=yourpassword
# 指定Hibernate的DDL自动生成策略，update表示启动时根据实体类自动更新表结构
spring.jpa.hibernate.ddl-auto=update
# 开启在控制台中打印执行的底层SQL语句，用于调试分析
spring.jpa.show-sql=true
```

当控制器层接收到客户端的HTTP POST等请求时，通过依赖注入机制调用服务层的方法，服务层继而调用`UserRepository`接口。Spring框架负责在底层开启数据库事务，组装SQL语句，通过JDBC驱动提交至数据库执行，并将结果集映射回Java实体类返回，从而形成一个高度自动化、无缝衔接的处理闭环。

## Spring Boot 3与Jakarta EE命名空间迁移

随着Java企业级生态的深层次变革，Spring Boot 3版本的发布带来了一次革命性的架构升级。这一升级的背后，主要受到两大历史性技术更迭的驱动：基础库命名空间从`javax`全面向`jakarta`的强制性迁移，以及由GraalVM支持的原生映像预先编译（AOT）技术的深度集成 。

### Java EE至Jakarta EE的历史变迁

自甲骨文（Oracle）公司将Java平台企业版（Java EE）的管理权及技术资产移交给开源社区Eclipse基金会后，出于商标及版权合规性的要求，所有的遗留规范和核心库必须进行重命名 。这就导致了历史悠久的`javax.servlet`命名空间被全面废弃，现代生态被要求强制转向`jakarta.servlet`命名空间 。

Spring Boot 3彻底拥抱了这一变化，它的内核要求建立在Jakarta EE 9及其后续版本的基础之上 。对于所有计划升级或迁移到新栈的企业级代码库而言，这一变化直接引入了破坏性的包级不兼容问题 。

在迁移过程中，若开发人员仍然在源代码中使用旧版的导入路径，例如引入`import javax.servlet.http.HttpServletRequest;`，当应用在基于Spring Boot 3的环境中进行编译或运行时，系统将抛出极其严重的`ClassNotFoundException`异常或包不匹配错误（如对象不可赋值错误）。

### 深度迁移与重构策略

开发团队必须采用系统的重构策略以解决这一割裂。最基础的修复在于代码层面的全量替换： 所有涉及Servlet API的类库引入必须进行修正： `import javax.servlet.*;` 必须被严格重写为 `import jakarta.servlet.*;` 。

然而，真正的风险潜伏在复杂的依赖树之中。在企业级工程中，试图混用Java EE与Jakarta EE依赖库是完全不可行的 。例如，Spring MVC框架的核心控制器`DispatcherServlet`在Spring Framework 6版本中已全面依赖于Jakarta Servlet API。任何试图与遗留`javax.servlet`继续耦合的尝试都会导致系统崩溃 。

此外，如果项目中引入的第三方依赖包（如旧版的社交登录库、遗留的PDF生成组件等）未积极维护，依然在内部传递拉取`javax.servlet`依赖包，则会引发复杂的间接冲突 。开发人员必须使用诸如`mvn dependency:tree`的命令深入审查依赖树，将不兼容的库替换为兼容版本，或者对于无法修改的遗留二进制包（JAR或WAR），使用诸如Eclipse Transformer之类的字节码转换工具，在构建环节将其内部的命名空间自动转换重写为Jakarta标准 。同时，由于底层的API变迁，使用的内嵌式或外部Servlet容器也必须升级。为了支持Jakarta Servlet 5+及以上标准规范，容器版本必须硬性升级至Tomcat 10或Jetty 11之上，低于此版本的容器将无法正常解析和加载新的API接口 。

## 现代云原生运行态：JIT与GraalVM AOT编译模型

除了命名空间的断代升级，Spring Boot 3对于底层应用执行模型的优化也达到了前所未有的高度。传统上，所有的Java应用程序（包括早期的Spring Boot应用）都在Java虚拟机（JVM）内部运行，并重度依赖于即时编译器（Just-In-Time Compiler, JIT）进行字节码转换与优化 。

在传统的JIT架构下，开发者的Java源代码首先被编译为与平台底层解耦的中间字节码 。在应用程序启动时，JVM逐条解释这些字节码执行。随着系统运行，JIT编译器在后台不断收集运行时的执行频率数据、分支预测情况和方法调用路径 。当它识别出高频调用的“热点”代码（Hot paths）后，便会在系统运行时将其动态编译成高度优化的、特定于当前硬件环境的本地机器指令 。尽管这种动态分析模型能够在系统经历了一段预热期（Warm-up phase）后展现出极其强悍的峰值性能，但它在云原生和微服务架构下暴露出了致命缺陷：应用程序启动时间缓慢、需要大量内存去支撑JVM的运行环境以及保存JIT编译器所需的各类元数据 。

为解决这些弊端，Spring Boot 3引入了对基于GraalVM的预先编译技术（Ahead-Of-Time, AOT）的原生支持 。GraalVM是一个高性能的JDK分发版本，它不仅包含多语言支持，还提供了一个核心工具——Native Image构建器，这相当于传统HotSpot JIT编译器的一个颠覆性替代方案 。

与JIT在运行时动态转换代码不同，AOT编译采用了封闭世界假设（Closed-world assumption）。在项目的构建编译阶段，AOT编译器对Java源代码、框架的依赖项、各种外部类库以及JDK中的本地代码进行彻底的静态分析，并提前将它们全部编译并打包为一个极其精简的、可以直接在目标操作系统上执行的独立二进制可执行文件（Standalone Executable）。

这种预先将系统固化的策略在云环境部署中具有极高的收益，但也带来了明确的技术权衡：

|**架构特性**|**JIT编译架构（传统JVM运行时）**|**GraalVM AOT编译架构（Native Image）**|
|---|---|---|
|**应用启动耗时**|较慢。需等待JVM初始化进程启动、类加载机制激活，以及初始字节码的逐条解释执行 。|几乎瞬时完成（亚秒级）。因为运行的是纯粹的、预先优化好的底层本地机器码序列 。|
|**系统内存占用**|庞大。需要为JVM运行机制、庞大的类描述元数据以及JIT编译器的中间代码留存大量的内存空间 。|极其紧凑。二进制文件仅包含应用生命周期内被绝对调用和使用的必要逻辑，去除了大量冗余框架代码 。|
|**容器镜像大小**|巨大。部署镜像中必须强制打包完整的Java运行环境（JRE）以支撑JVM的运行 。|非常微小。最终的执行文件不需要依赖外部的JRE，极大降低了Docker等容器的存储和分发成本 。|
|**安全攻击面**|具有标准且更为宽泛的应用层攻击面积。|由于脱离了完整的虚拟机框架，攻击面显著减小，且本地编译后的文件对逆向工程（Reverse engineering）具有更高的抵抗力 。|
|**Java动态特性支持**|原生且完美地支持Java反射（Reflection）、动态类加载以及字节码生成机制。|与Java的动态特性产生冲突。任何针对类的反射行为和动态代理，都必须在编译期前被显式和详尽地人工配置 。|
|**运行时性能优化**|在预热完成并在JIT介入后，往往能根据实际硬件利用率进行动态修正，达到极高的极限吞吐能力 。|性能曲线扁平且静态。由于缺乏运行时的动态监控，一旦程序编译成型，便无法再进行深度的性能自我调节 。|

将庞大的Spring框架适配到GraalVM Native Image架构中面临着巨大的技术挑战，原因在于Spring框架的底层长期严重依赖反射机制和动态代理技术来进行Bean的实例化和依赖注入的编排 。由于AOT编译在分析代码时无法预测运行时动态反射所涉及的类，如果直接编译往往会导致系统在运行时出现严重的找不到对象错误。

为了攻克这一难题，Spring Framework 6在项目的构建生命周期中强制引入了一个额外且至关重要的AOT处理阶段（AOT Processing step）。在该阶段，Spring AOT引擎会在编译前全面接管并扫描项目的上下文环境，精准推断出哪些Bean将被需要并注入，并自动生成替代反射调用的底层硬编码桩和配置清单 。这一机制近乎完全消除了系统在运行时对反射的依赖，使得GraalVM编译器能够获得一棵清晰、可预测且易于分析的方法调用树，最终使得复杂的Spring Boot应用程序能够完美编译为轻量级且极速启动的微服务镜像 。不过，这一技术的广泛应用也伴随着其内在局限性：AOT编译过程对CPU计算资源的消耗极大且异常耗时，其能支持的垃圾收集器（Garbage Collectors）类型也大幅受限，且由于丢弃了JVM环境，针对原生镜像的诊断、监控与调试工作变得更具挑战性 。