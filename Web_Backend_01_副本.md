---
title: Web后端01：JSON 与 Fetch API
categories:
  - Note(Web)
tags:
  - JSON
  - Fetch API
abbrlink: 8001
date: 2026-05-14 17:20:00
cover: /img/background3.png
katex: true
---

# 回放速记

## JSON

### 前后端传递 JSON 纯文本文件

### 早期使用 XML

- 类似 html
- 可以用来描述数据
- 被抛弃：语法上较复杂，但是容易排查错误；承载信息能力弱，有效信息少，字节数过多
- 不容易解析

建一个 DOM 树：

```angular2html
user 
  |_ ID _ 101
  |_ name _ Alice
  |_ role _ Prof
  |_ dept _ CS
```
第一种方法（建 DOM 树）：
- 第一次在内存中建立 DOM 树速度很慢
- 一旦建立好查询速度很快（在内存中）
- 文件很大时 DOM 树巨大

第二种方法（文件当成流，SAX，直接访问）:
- 往前读标签，直到找到目标标签，找到后读值
- 不需要内存中建树，速度快，占用少
- 读速度很慢，流读取每次都要从头读
- 开销平摊到平时

性能较差，换成 JSON

现在还可以用，但是不首选

### JSON 套用 JS 标记法

- 键值对存储数据
- 和 XML 一样是纯文本
- 不需要开始结束标签，省空间，可读性强
- 信息密度高，更轻量

### JSON != JavaScript Object

- 键必须是字符串，必须小写
- 数字不同于 java 对象
- 不允许 inf， NaN，允许 null
- 可以是 bool
- 可以嵌套
- 可以是数组，数组内容可以不是同一种类型
- 字符串必须双引号，不允许单引号
- 只允许十进制
- 末尾对象后面没有逗号
- JS 对象允许函数成员，JSON 不允许
- JS 转 JSON 交给现有包处理，自己直接混用处理容易出错

### TEXT 和 BLOB 的区别

### 数据交互

JS obj 转 JSON（序列化）：
- 字符串化 `JSON.stringify(js_obj)`
- 可选参数 `replacer` 传递选择
- 第三个参数使用`2`：美化缩进
- 内存满了，对象还在用，将其写到 disk 中，这个过程也需要序列化，本质上就是变成一个 string
JSON 转 JS obj（反序列化）：
- 恢复成一个对象 `JSON.parse(json_str)`
- 第二个参数是一个函数：怎么转？
- Fetch API 时会抛错误，用`.catch`处理：没响应，转换出错

### 为何不使用 Ajax

- 使用 `await` `async`处理异步
- Ajax，fetch，Axios 发送异步信号 Asyn/Await
- 前端浏览器发送后端，从后台拿取状态
- 请求页面->刷新页面
- 请求数据->根据状态刷新页面的一部分，更新状态后刷新部分内容。实际上过程是异步的，从操作到响应这段时间可以挂起执行其他动作；这是一个非阻塞的等待

### Ajax 到 Fetch API

- 比 Ajax 更加简洁易读
- 以 Promise 为基础
- fetch 范式 `fetch(...).then(...).catch(...)`，必须要看 response 是否 ok
- POST 虚拟数据流。把一个数据 POST 到后端去；JSON 响应，转换 JS obj
- `then`堆叠风格相当于`promise` 堆叠，也可以使用 `Async/Await`，两个事对等的，后者可读性一般更好

### JSON Schema

- 格式更加严格
- 对应 XML 的 DTD 文档定义和 XML Schema，可以校验格式
- Schema 要求数据必须是什么样子？符不符合要求？
- 不是强制的，可以写代码时避免错误

### JSON 关系型数据库

- 作为文本字段写数据库不容易解析
- 嵌套对象摊平，但是嵌套的关系被抹掉了
- 可以为嵌套对象添加额外字段进行对应，加额外的表做外径关联，解决摊平嵌套信息丢失问题。关联操作非常费时，拼接的时候做笛卡尔积之后再挨个筛选。非常耗时
- 怎么权衡？折中——当成一个字段丢进数据库，但是存纯文本不容易做查找

### MongoDB & BSON

- MongoDB 直接存成一个文档
- 也是直接存字符串，但是可以在 JSON 上建立索引，性能较高

### JSON 性能

问题：
- 高负载情况下怎么处理？带宽和 CPU 的限制怎么应对？使用流式处理器处理？
- JSON 纯文本文件表达能力弱
- 不容易压缩
- Fetch 不必要的信息
- 数字表示：JSON 和 java 对象之间可能存在精度差。可以转换成字符串处理，保留高精度
- Schema 来约束长度和精度问题

题外话：压缩的本质：相同的内容避免存若干遍

- 用差分来对比语义
- 提取主干特征来恢复，理论上就是函数求逆

JSON 也可以压缩。

### JSON 安全

传来的 JSON 可能是恶意的，MySQL injection 注入攻击：
```json
{
    "usarname": {"$ne": null},
    "password": {"$ne": null}
}
```
这样的数据 get 值时随便输入一个值就能通过。

执行 SQL 语句时一次性发多条给后台，风险较大。

还有跨站脚本攻击，Cookie 劫持，传递的 JSON 需要做后台校验。

## Fetch API

### 同源策略

- 发请求的时候有一堵墙。
- Script 试图请求，请求的时候会携带访问源
- 不允许的情况下不同源不允许访问

### 源

怎么定义？

协议，主机，端口：

`PROTOCOL+HOST+PORT->The Origin`

- 不写默认 80 端口
- http https 协议不一致
- a.com b.com 主机不一样
- 用 8080 端口不对

什么时候能访问？

从浏览器发出请求 Origin 是localhost:3000 ?

机器 A 访问网页 C，在 C 做 get 请求去访问 B，get 请求的 origin 体现的是 A 而不是 C。请求是 A 的脚本发出的。
这一部分有点乱，听得不清楚，没看太懂。

什么情况下算跨域请求？

后端收到前端请求的时候检查授权头。怎么带允许信息？
- 前端先问能不能访问；
- 后端应答；
- 允许的话去做get之类的操作

代码里具体怎么处理跨域请求？(Node.js(Express)/Java(Spring Boot)/Python(Flask/Django))

### Spring Boot 的三种设置方法

接到请求去拿跨域信息。
- Fine-Grained 直接设置
- Global MVC
- Low-level Filter 要写专门的配置文件，更常见

### 前后端 Fetch 怎么设置

Fetch 主要处理异步和跨域请求

- fetch(url, init)
- 做 get 请求，前端跨域代码怎么写
- JWP 验证（好像是），Token 校验
- 跨域的时候要带 include，默认是不带的，允许跨域要加这个
- 后台要 Token，前台要给 token，没 token 加 include 证书（这一部分好乱）
- CorsConfig

到这里前端就结束了

# AI 重整理

## 现代Web异步通信架构演进

现代Web应用程序的演进在很大程度上取决于从静态的、同步的页面加载方式向动态的、异步的数据交换模式的转变。这一范式在历史上被称为异步JavaScript和XML（Asynchronous JavaScript and XML，简称AJAX），它代表了一种核心的Web开发技术。通过AJAX，Web应用程序可以在后台通过发出异步HTTP请求从服务器获取内容，并使用新内容动态更新文档对象模型（DOM）的相关部分，而无需进行破坏用户体验的完整页面刷新 。

异步编程技术使得主线程能够启动一个可能需要长时间运行的网络任务，并在该任务在后台执行的同时，保持对用户交互和其他事件的响应能力 。一旦HTTP事务结束，服务器返回的有效载荷（Payload）将被传递回应用层进行处理。虽然这项技术最初依赖XML作为主要的数据交换格式，但现代架构已经全面转向JavaScript对象简谱（JSON）。JSON凭借其轻量级的语法和与JavaScript运行时的原生集成优势，成为了目前Web后端开发中绝对的主流 。因此，深入理解数据格式、网络协议、请求接口以及服务器端处理机制的交叉点，是构建具有高弹性和高性能的现代Web架构的必经之路。

## 数据交换格式体系：结构范式与安全机制

在HTTP协议之上进行复杂数据结构的传输，必须首先将其序列化为基于文本的格式。Extensible Markup Language（XML）和JavaScript Object Notation（JSON）是两种最主要的数据序列化标准，它们在架构特征、处理开销以及安全性方面存在着显著的差异 。

### 体系结构与性能对比

XML是标准通用标记语言（SGML）的一个子集，依赖于基于标签的树状结构 。其设计初衷是提供高度的描述性，支持复杂的命名空间、严格的模式验证（如XSD和DTD），以及涵盖日期、图像等多样化的数据类型 。然而，这种描述能力是以极端的冗长性为代价的。繁琐的起始和结束标签导致网络有效载荷体积庞大，而且解析XML需要进行繁重的文档对象模型（DOM）操作，这会显著降低解析速度并消耗大量内存效率 。

相比之下，JSON是一种独立于编程语言的开放数据交换格式，其语法基于JavaScript对象语法的子集 。它采用简单的键值对结构，并支持数组和嵌套对象，完全省略了闭合标签的开销 。JSON结构的简洁性通常会带来更小的文件体积，从而实现网络层面上更快的传输速度，并在序列化和反序列化过程中显著降低CPU的利用率 。

|**架构特征**|**JavaScript Object Notation (JSON)**|**Extensible Markup Language (XML)**|
|---|---|---|
|**语法结构**|键值对映射，逗号分隔的数组|具有层级关系的起始/结束标签，节点属性|
|**数据类型支持**|字符串、数字、布尔值、数组、对象、null|支持JSON所有类型，外加日期、布尔值、图像及命名空间|
|**解析机制**|原生JavaScript内置函数直接解析|需要依赖专门的XML DOM解析器|
|**数据验证**|JSON Schema（可选的外部规范）|XSD / DTD（高度集成的强制性规范）|
|**性能与开销**|载荷轻量，网络传输快，原生解析速度极高|载荷冗长，DOM处理消耗大量内存与计算资源|

### JSON语法规范与原生处理方法

尽管JSON在视觉上与JavaScript对象字面量语法高度相似，但它遵循一套更为严格的语法规则，以确保跨不同编程环境下的解析确定性 。有效的JSON严格限制原始数据类型只能是双引号包裹的字符串字面量、十进制数字、布尔值（`true`/`false`）以及`null` 。它明确禁止使用JavaScript特有的构造，例如`undefined`、`NaN`、`Infinity`、函数方法、尾随逗号以及任何形式的内联注释 。对象属性的键名必须强制使用双引号包裹，且数字不能包含前导零 。

JavaScript全局的`JSON`命名空间对象提供了两个静态方法来与这种格式进行交互：`JSON.stringify()`和`JSON.parse()` 。序列化过程通过`JSON.stringify()`执行，它将原生的JavaScript对象转换为标准的JSON文本 。该方法接受可选的`replacer`函数或数组参数，用于选择性地包含属性或转换特定值。例如，在处理高精度大整数（`BigInt`）时，由于JSON原生不支持`BigInt`，开发者可以使用`replacer`函数将其转换为字符串以防止精度丢失；同样，也可以利用该参数对`Map`和`Set`等复杂数据结构进行自定义序列化，否则它们会被默认序列化为空对象 `{}` 。

JavaScript

```
// 处理高精度数字及复杂对象的序列化示例
const data = { 
    id: 12345678901234567890n, 
    registry: new Map([[1, "active"]]) 
};

const jsonString = JSON.stringify(data, (key, value) => {
    if (typeof value === 'bigint') {
        return value.toString(); // 防止BigInt序列化报错
    }
    if (value instanceof Map) {
        return Array.from(value.entries()); // 转换Map为二维数组
    }
    return value;
});
```

反序列化则由`JSON.parse()`负责，它将JSON格式的字符串还原为功能完整的JavaScript对象 。与序列化类似，`JSON.parse()`支持一个`reviver`参数。该参数是一个遍历生成对象的函数，允许应用程序在将最终对象返回给执行上下文之前，拦截并转换特定值，例如将ISO格式的日期字符串直接还原为原生的`Date`对象，或者将大数字符串重新解析为`BigInt`实例 。

### 反序列化的安全隐患：eval与JSON.parse的区别

在历史早期的Web开发中，由于JSON在结构上是JavaScript的子集，一些实现方式曾依赖原生的`eval()`函数将JSON文本编译为JavaScript结构 。`eval()`函数是一个全局机制，它将传入的字符串作为可执行的JavaScript表达式或语句进行计算 。

将`eval()`用于解析外部数据的做法引入了灾难性的安全漏洞 。由于`eval()`无法区分静态数据和可执行代码，JSON有效载荷中嵌入的任何恶意指令（例如精心构造的脚本或DOM操作函数）都会以应用程序全局上下文的完整权限被执行 。这为跨站脚本攻击（XSS）和数据篡改打开了巨大的攻击面，攻击者可以通过注入恶意脚本来窃取用户会话Cookie、篡改界面或代表用户发起未经授权的API调用 。

与之形成鲜明对比的是，`JSON.parse()`充当了一道坚固的密码学和逻辑边界。它依赖于严格定义的实现契约，根据极其死板的JSON语法规则对传入的参数进行词法分析 。如果字符串中包含可执行函数、数学表达式或格式错误的标签，`JSON.parse()`会立即中止操作并抛出`SyntaxError`异常，从而物理阻断了任意脚本的执行 。因此，现代后端和前端交互架构标准强制要求独占使用`JSON.parse()`进行数据解析，彻底将`eval()`从数据交换任务中淘汰 。

## 传统异步请求核心：XMLHttpRequest (XHR) API

十多年来，执行异步HTTP请求的核心接口一直是`XMLHttpRequest`（XHR）API 。尽管其命名中包含了“XML”这一历史遗留词汇（源于XML曾是主导数据格式的时代），但XHR对象不仅限于检索XML文档，它能够获取和传输任何类型的数据格式，包括纯文本、JSON以及底层的二进制数据流 。

### 初始化与连接生命周期

一次完整的XHR事务生命周期始于实例化一个新的`XMLHttpRequest`对象，并调用其`open()`方法 。`open()`方法用于初始化请求，它需要指定使用的HTTP动词（例如`GET`或`POST`）、目标URL，以及一个可选的布尔值标志，用于决定该请求是否应以异步模式执行 。

尽管异步标志的默认值为`true`，但开发者在历史上曾可以选择强制执行同步请求 。然而，在主线程上执行同步的XMLHttpRequest目前已被所有主流现代浏览器正式弃用，因为其对终端用户体验具有毁灭性的影响 。同步网络请求会阻塞JavaScript的事件循环，冻结整个DOM结构直至服务器返回响应。在此期间，应用程序会呈现假死状态，UI渲染和用户交互被彻底挂起，这在现代应用开发中是不可接受的 。

在请求初始化之后，开发者可以使用`setRequestHeader()`方法附加应用程序特定的HTTP请求头，如认证令牌或内容类型声明。值得注意的是，`setRequestHeader()`必须在`open()`调用之后、`send()`调用之前执行 。最后，通过调用`send()`方法将请求正式分发到服务器，对于`POST`和`PUT`等操作，`send()`方法可以接受一个可选的主体有效载荷（Body Payload）参数 。

### readyState 状态机过渡架构

在整个请求的生命周期中，XHR对象通过一个内部状态机进行转换，该状态由`readyState`属性跟踪，其返回值为0到4之间的整数 。

|**readyState 值**|**状态名称**|**语义描述与应用上下文**|
|---|---|---|
|**0**|`UNSENT`|客户端XMLHttpRequest对象已成功创建，但尚未调用`open()`方法初始化 。|
|**1**|`OPENED`|`open()`方法已被调用。底层网络连接已建立，客户端已准备好接受`setRequestHeader()`配置，并可以随时调用`send()`方法发起传输 。|
|**2**|`HEADERS_RECEIVED`|`send()`方法已被执行，所有网络重定向（若有）已被透明处理，服务器的初始HTTP响应头和状态码已接收完毕，可供客户端代码检查 。|
|**3**|`LOADING`|响应的实体主体（Entity Body）正在持续下载中。如果响应类型是文本流，此时的`responseText`属性将持有一部分不完整的片段数据 。|
|**4**|`DONE`|整个网络操作已彻底完成。这表示数据传输已成功结束，或者因为网络错误、跨域拦截等原因导致连接彻底失败 。|

为了跟踪这些细微的状态转换，开发者传统上会将回调函数绑定到`onreadystatechange`事件处理器上。每当底层内部状态发生递增时，该事件就会被触发 。在此回调逻辑中，必须显式验证`readyState === 4`，并进一步检查HTTP的`status`代码（如200），然后才能安全地处理返回的有效载荷 。

### 事件处理范式：onreadystatechange 与 onload 的抉择

虽然`onreadystatechange`在各种旧有代码库中根深蒂固，但现代XHR实现和最佳实践更倾向于使用`onload`事件监听器 。这两者在架构上的主要区别在于：`onreadystatechange`会在请求的各个中间状态（1、2、3和4）期间被多次重复触发，而`onload`则极其精确，它只在请求成功完成、且所有数据已完全缓冲到内存中时触发唯一的一次 。

此外，依赖`onreadystatechange`进行错误处理会引入复杂的边界情况。在遇到严重的网络连通性问题或跨域资源共享（CORS）拦截时，请求的`readyState`依然会推进到4（表示操作结束），但其`status`属性将被重置为0 。在这些异常失败的场景中，XHR对象还会触发专门的`onerror`事件处理器。如果混用这两种机制，可能会导致竞态条件，使得状态改变回调和错误回调被同时意外触发 。独占使用`onload`可以确保成功的回调逻辑仅在有效的HTTP事务圆满解决时才被调用，从而将网络层面的崩溃和底层异常严格隔离到`onerror`处理器中，这使得代码逻辑更为清晰和健壮 。

### 响应解析层：responseText 与 responseXML

当网络请求在State 4成功解析后，开发人员可以通过特定的响应属性来访问服务器返回的有效载荷 。`responseText`属性返回一个原始字符串，代表响应实体主体的字面文本数据 。在现代Web后端交互中，如果服务器返回的是JSON数据格式，应用程序不能直接使用该字符串，必须通过`JSON.parse()`将其反序列化为对象后才能以编程方式进行交互 。

相对而言，`responseXML`属性则试图将传入的文本数据原生解析为结构化的文档对象模型（DOM）树 。尽管名称中带有XML，但`responseXML`实际上具备解析XML和标准HTML文档的双重能力 。如果服务器在响应头中正确声明了`Content-Type`为`text/xml`或`text/html`，该属性将直接产出一个可利用DOM API查询的Document对象 。然而，如果后端接口配置不当，未能指定正确的MIME类型，浏览器解析器将拒绝填充`responseXML`，返回`null`。为了绕过这种限制，开发人员可以在调用`send()`之前使用`overrideMimeType()`方法，强制浏览器将传入流视为特定的数据格式。这种技术在历史版本中也常被用于通过指定用户定义的字符集（charset）来强制XHR对象下载和处理原始的二进制数据流 。

JavaScript

```
// 现代 XMLHttpRequest 封装示例
function makeAjaxRequest(url, method = 'GET', payload = null) {
    const xhr = new XMLHttpRequest();
    xhr.open(method, url, true);
    
    // 强制设定响应格式为JSON
    xhr.responseType = 'json';
    xhr.setRequestHeader('Content-Type', 'application/json');

    xhr.onload = function() {
        if (xhr.status >= 200 && xhr.status < 300) {
            // responseType 为 'json' 时，xhr.response 已自动转换为对象
            console.log("请求成功：", xhr.response);
        } else {
            console.error("HTTP 错误，状态码：", xhr.status);
        }
    };

    xhr.onerror = function() {
        console.error("网络连接失败或跨域被拦截");
    };

    xhr.send(payload? JSON.stringify(payload) : null);
}
```

## 现代异步请求标准：Fetch API 的声明式与Promise驱动

虽然`XMLHttpRequest`依然具备完整的功能并在旧设备上提供广泛的兼容性，但由于其严重依赖回调函数的架构、晦涩难懂的状态机管理，以及将请求头、配置信息和请求体混合在同一对象中的混乱设计，它已经不再适应现代软件工程的设计模式 。为了解决这些痛点，W3C引入了Fetch API，这是一种功能更强大、灵活性更高且语法在本质上更为清晰的替代方案，目前已被深度集成到所有现代浏览器以及Node.js运行环境中 。

### 基于 Promise 的架构设计

Fetch API 与 XHR 之间最核心的区别在于其底层的 Promise 架构 。调用全局的 `fetch()` 方法并不会像 XHR 那样需要开发者自行挂载回调函数，而是立即返回一个 JavaScript Promise 对象。一旦服务器返回了初始的 HTTP 响应头，这个 Promise 就会立即 resolve 为一个 `Response` 对象 。这种设计从根本上消除了所谓的“回调地狱”（Callback Hell），允许开发者利用优雅的 Promise 链式调用（`.then().catch()`）或现代的 `async/await` 语法特性，以编写同步代码的思维习惯来组织复杂的异步数据流 。

不同于 XHR 采用的宏大单一对象配置模式，Fetch API 在规范层面明确解耦并定义了独立的 `Request`（请求）、`Response`（响应）和 `Headers`（请求/响应头）接口对象，从而提供了一种高度模块化和可深度重用的网络拓扑抽象 。不仅如此，Fetch 还在底层天然集成了对 Service Workers、Cache API 缓存管理以及原生 Readable Streams（可读流）的支持。这使得现代 Web 应用能够以流的方式逐块增量处理高达数 GB 的巨型数据载荷，而无需将其一次性完全加载至内存中，从而实现极致的性能优化 。

### Fetch API 核心接口拆解

#### Request 与 Headers 对象

`fetch()` 方法在调用时接受一个强制的 URL 字符串参数，以及一个可选的 `RequestInit` 配置对象。该配置对象可以包含 `method`（HTTP 动词）、`mode`（跨域模式）、`credentials`（凭证策略）、`headers`（请求头集合）以及 `body`（请求负载）等属性 。在更复杂的场景下，开发者也可以使用 `Request()` 构造函数实例化一个独立的 `Request` 对象，并在多个 `fetch()` 调用中复用或传递它 。

HTTP 头部信息的管理通过专用的 `Headers` 接口实现。该接口提供了一套标准化的 API 用于对请求/响应头进行严格的清洗、查询和追加操作 。开发者可以直接向 `fetch` 传递一个简单的字面量对象，或者传入一个正式实例化的 `Headers` 对象来明确声明内容类型（Content-Type）或注入 OAuth 授权令牌（Authorization tokens） 。 需要特别注意的是，与 XHR 默认且强制地将当前域的浏览器会话 Cookie 附加到所有请求的行为不同，Fetch API 在设计上更为注重隐私保护和安全性，默认情况下它拒绝发送任何 Cookie。如果开发者需要向后端传输身份凭证，必须在配置对象中显式声明 `credentials` 属性为 `same-origin`（仅向同源目标发送）或 `include`（在跨域请求中也发送凭证） 。

#### Response 对象与 Body 数据流提取

由 `fetch()` 触发的 Promise 会 resolve 为一个 `Response` 对象，该对象内部封装了 HTTP 状态码（`Response.status`）、指示请求是否成功的布尔标志（`Response.ok`），以及一个类似 Map 结构的 Headers 集合 。

考虑到响应的有效载荷在理论上可能是一个体积庞大的媒体文件，`Response.body` 在底层被直接暴露为一个底层的 `ReadableStream` 流对象 。为了方便开发者从流中提取和解码数据，Fetch API 提供了多种基于 Promise 的异步实例方法 ：

- **`.json()`**：读取并消费整个数据流直至结束，随后将提取出的原始文本传入内置的 JSON 解析器进行反序列化，最终返回一个标准的 JavaScript 对象 。
    
- **`.text()`**：将整个响应体作为未经任何处理的原始 UTF-8 字符串返回 。
    
- **`.blob()`**：以二进制大型对象（Binary Large Object, Blob）的形式提取响应数据。Blob 包含了不可变的原始二进制数据，并附带了对应的 MIME 类型信息。这种方法在处理图片等二进制资产时极其高效，开发者可以将返回的 Blob 传入 `URL.createObjectURL()` 转换为内存对象 URL，并直接绑定到 `<img src>` 标签上进行渲染 。
    
- **`.arrayBuffer()`**：返回一个更底层的、长度固定的连续内存序列引用（`ArrayBuffer`）。它主要用于性能敏感的重型二进制数据处理、密码学运算、或 WebGL 图形渲染等高级场景 。
    
- **`.formData()`**：专门用于拦截并自动解析服务器返回的 `multipart/form-data` 格式响应，将其转换为一个可查询的、键值对形式的 `FormData` 接口对象 。
    

一个关键的架构约束是：由于上述方法都会彻底消费（Consume）底层的 `ReadableStream`，因此响应体（Body）只能被读取一次 。如果一个应用程序在同一逻辑流中既需要获取响应的原始文本进行日志记录，又需要解析其 JSON 结构以驱动业务逻辑，开发者必须在调用读取方法前，先使用 `Response.clone()` 方法对整个响应流进行复制 。

### 构造网络请求：GET 与 POST 的最佳实践

`GET` 请求旨在从服务器检索资源表现形式，严格遵循 HTTP 的幂等性，不应修改服务器的状态。由于标准规范禁止 `GET` 请求携带 `body` 负载，因此任何动态的查询参数都必须编码并附加到 URL 的查询字符串（Query String）中，现代开发通常推荐使用原生的 `URLSearchParams` 构造函数来完成参数的安全编码与拼接 。

相反，`POST` 请求主要用于向服务器推送数据，通常会导致后端状态的改变或新资源的创建 。当使用 JSON 格式构造 `POST` 请求时，开发者必须在 `fetch` 选项中显式且精确地配置三个核心参数 ：

1. **Method（请求方法）：** 将 `method` 属性显式赋值为 `"POST"` 。
    
2. **Headers（请求头）：** 必须手动将 `Content-Type` 标头设定为 `application/json;charset=utf-8` 。如果遗漏此项配置，浏览器对于字符串类型的 Body 会默认退化为 `text/plain`。这会导致基于 Express.js 或 Spring Boot 等现代后端框架内置的 JSON 解析中间件由于无法识别媒体类型而拒收请求或解析失败 。
    
3. **Body（负载主体）：** 必须利用 `JSON.stringify()` 将前端的 JavaScript 业务对象安全地序列化为 JSON 格式的文本字符串，然后再将其赋给 `body` 属性 。
    

以下代码片段展示了一个结合现代异步语法（async/await）并严格遵循上述配置范式的健壮实现：

JavaScript

```
async function submitJsonData(endpoint, dataPayload) {
  const requestOptions = {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    // 将对象序列化为标准JSON字符串
    body: JSON.stringify(dataPayload)
  };

  try {
    // 阶段一：等待服务器响应头部信息
    const response = await fetch(endpoint, requestOptions);
    
    // 最佳实践：在提取数据前，验证HTTP状态码是否在成功范围(200-299)
    if (!response.ok) {
      throw new Error(`业务或服务器异常，HTTP状态码：${response.status}`);
    }
    
    // 阶段二：异步提取并反序列化响应流中的JSON主体
    const jsonResponse = await response.json();
    console.log("事务处理成功：", jsonResponse);
    return jsonResponse;
    
  } catch (error) {
    // 捕获网络断开、跨域阻断或主动抛出的HTTP异常
    console.error("网络请求终止或解析彻底失败：", error.message);
  }
}
```

### 异常处理的细微差别与两段式验证

Fetch API 与传统 XHR 之间一个非常核心，且极易导致新手开发者产生误解的差异在于其错误传播机制 。由 `fetch()` 返回的 Promise **仅在**遭遇灾难性的底层网络故障时才会执行 reject（拒绝）操作——例如 DNS 解析失败、设备网络接口离线、或遇到了严厉的跨域资源共享（CORS）策略拦截 。

至关重要的一点是：如果服务器成功接收到了请求，但由于某些原因返回了一个明确指示错误的 HTTP 状态码（例如表示资源未找到的 `404 Not Found`，或表示后端服务崩溃的 `500 Internal Server Error`），在 Fetch 的机制中，由于 HTTP 通信协议层面的往返（Round-trip）在技术上已经顺利完成，因此 `fetch()` 产生的 Promise 依然会成功 resolve 。

正因如此，构建容错性强的网络架构要求开发者实施严格的两段式验证逻辑： 首先，必须使用 `try...catch` 代码块来拦截底层的网络崩溃异常；其次，在 `try` 块内部，必须主动探查 `response.ok` 属性（当 HTTP 状态码介于 200 至 299 之间时，该属性值为 `true`）。如果该属性为 `false`，则表明发生了 HTTP 语义级别的失败，此时开发者需要根据具体的状态码手动抛出（`throw`）应用层面的错误或执行降级策略，以防止后续的代码试图解析一个可能包含错误堆栈信息的意外响应体 。

## 异步请求方案横向对比

在不同的历史时期和项目需求下，前端工程界涌现了多种异步请求工具。通过以下表格可以清晰对比主流方案的技术特性：

|**特性 / 库**|**XMLHttpRequest (XHR)**|**jQuery.ajax**|**Fetch API**|**Axios**|
|---|---|---|---|---|
|**底层实现**|浏览器原生核心API|封装自 XMLHttpRequest|浏览器原生标准API|封装自 XMLHttpRequest (Node中封装 http)|
|**编程模型**|回调函数 (Event Callbacks)|Promises (后期版本)|纯原生 Promises|Promises|
|**语法简洁度**|极其冗长，需手动设置状态监听|简单，适合老式项目|现代、声明式、链式调用|极简，且提供大量语法糖|
|**错误处理**|需混用 onreadystatechange/onerror|jQuery自动处理|需手动校验 `response.ok`|自动根据 HTTP 状态码抛出异常|
|**数据流 (Stream)**|不支持，必须完全缓冲到内存|不支持|原生支持流式处理大型响应体|有限支持 (通过适配器)|
|**拦截器与取消**|支持 `abort()`|支持取消，无强大拦截器|支持 `AbortController` 取消|原生提供强大的请求/响应拦截器|

通过对比可知，对于无需引入第三方依赖的现代轻量级 Web 应用，原生 Fetch API 是最佳选择；而对于需要复杂请求拦截、全局错误处理和自动 JSON 转换的大型企业级应用，Axios 因其丰富的功能特性仍占据主导地位 。

## 跨域资源共享 (CORS) 与安全防御体系

Web 安全的基石在很大程度上依赖于同源策略（Same-Origin Policy）。这是一项由浏览器层面强制执行的绝对安全规则，它严厉禁止客户端脚本未经授权直接读取来自不同域名、协议或端口的敏感数据 。然而，现代面向服务（SOA）或微服务架构要求前端界面必须持续地与第三方 API 或分离的后端集群进行高频交互。跨域资源共享（CORS）正是在这一背景下诞生的一种标准化的 HTTP 标头协商机制，它允许目标服务器安全地放宽同源策略的限制，并选择性地“放行”跨域流量 。

### Preflight（预检）请求验证机制

为了防止部署在现代 Web 环境中的恶意前端脚本，对那些在设计时并未考虑 CORS 规范的传统遗留服务器发起具有破坏性的跨域操作，浏览器在底层静默实现了一种称为“预检请求”（Preflight Request）的保护屏障 。

在真正调度开发者配置的异步请求之前，浏览器会自动拦截并静态分析该请求的参数。如果请求符合所谓的“简单请求”（Simple Request）标准——即使用的 HTTP 方法被严格限制在 `GET`、`HEAD` 或 `POST` 之内，且附加的头部信息仅限于 `Accept`、`Accept-Language` 等安全标头，同时如果包含 `Content-Type`，其值必须为 `text/plain`、`application/x-www-form-urlencoded` 或 `multipart/form-data` 中的一种——那么浏览器会认为该请求风险可控，并立即将其直接发出 。

但是，一旦应用程序试图使用具有潜在破坏性的方法（如 `PUT`、`DELETE`），或尝试注入自定义的认证标头（如 `Authorization`、`x-api-key`），亦或是将 `Content-Type` 设置为被广泛使用的 `application/json`，该请求将立即触发预检机制 。

预检机制在网络层表现为一个自动生成的 `OPTIONS` HTTP 请求，它被优先分发至目标资源服务器 。`OPTIONS` 方法本质上是一个不携带任何数据主体的探测包，它通过几个特定的头部信息向服务器“征询”权限 ：

- `Origin`：准确声明试图发起跨域调用的前端页面的协议和域名 。
    
- `Access-Control-Request-Method`：告知服务器，后续真正发出的请求将使用哪种 HTTP 动词（例如 `POST` 或 `DELETE`） 。
    
- `Access-Control-Request-Headers`：列出前端应用程序计划在真实请求中注入的所有自定义头部信息 。
    

### 服务器端的跨域标头断言与性能考量

服务器在接收到 `OPTIONS` 探测请求后，其内置的 CORS 中间件会验证发出请求的 Origin 是否在允许的白名单内，以及请求的方法和标头是否受到支持 。如果服务器批准了这次事务，它必须返回一个不含主体的 HTTP 200 或 204 响应，并附带以下确认性质的头部指令 ：

- `Access-Control-Allow-Origin`：显式回显被允许访问资源的源域名（对于公共、无需凭证的开放 API，可返回通配符 `*`） 。
    
- `Access-Control-Allow-Methods`：以逗号分隔的列表形式，告知客户端当前资源支持的所有 HTTP 动词 。
    
- `Access-Control-Allow-Headers`：明确许可在真实请求中可以使用的自定义 HTTP 标头 。
    
- `Access-Control-Max-Age`：这是一个至关重要的缓存控制指令。它指示浏览器在指定的秒数内，将此次预检批准的结果缓存起来。在此期间，对于发往同一资源的类似跨域请求，浏览器可直接跳过预检阶段，直接发送真实请求 。
    

CORS 机制引入的整体网络延迟在数学上可以抽象表示为：$T_{total} = T_{handshake} + T_{preflight} + T_{request} + T_{response}$。其中预检往返时间 ($T_{preflight}$) 占据了显著比例。这突显了通过配置 `Access-Control-Max-Age` 标头来利用客户端预检缓存，对于优化高频次调用的 API 性能而言是何等关键。

如果服务器配置失误，未能返回与客户端源相匹配的 `Access-Control-Allow-Origin` 标头，浏览器将执行极其强硬的阻断措施。浏览器不仅会终止事务，更会从内核级别阻断底层的 JavaScript 执行上下文读取响应体中的任何数据片段，并在开发者控制台中抛出经典的 CORS 阻断异常 。必须澄清的一个技术细节是：CORS 策略的执行主体完全是客户端浏览器。在许多拦截案例中，服务器实际上已经接收并正常处理了跨域请求（甚至可能已经修改了数据库），但正是浏览器在最后关头拦截了服务器的响应，以保护本地运行环境免受非法数据的污染 。

### 异步请求的安全与局限性 (AJAX Issues)

尽管异步请求极大地增强了应用的可用性，但其底层机制也暴露出特定的安全漏洞与工程缺陷 ：

1. **跨站脚本攻击 (XSS) 与 跨站请求伪造 (CSRF)**：由于异步通信经常需要操作 DOM，如果没有严格实施输入校验和利用 `JSON.parse` 等安全解析手段，极易成为注入攻击的目标 。同时，由于请求可携带认证凭据，CSRF 攻击者可诱导用户在已登录状态下不知情地触发危险的异步操作 。
    
2. **搜索引擎优化 (SEO) 挑战**：传统的网络爬虫在抓取页面时并不执行 JavaScript。这意味着严重依赖 AJAX 加载核心内容的单页应用（SPA）在默认情况下对搜索引擎是不可见的，从而导致网页在搜索引擎结果中的排名极低，通常需要借助服务端渲染（SSR）技术来弥补这一缺陷 。
    
3. **调试复杂性增加**：由于请求是异步发生在后台的，页面不再通过整页重载提供明显的错误反馈，这显著增加了前端代码的维护和故障排查难度 。
    

## HTTP状态码与错误诊断工程

客户端与服务器之间通信闭环的最终达成，是通过 HTTP 状态码来确认的。这是一种包含三位数字的标准响应机制，用于精确传达操作的语义结果 。前端工程的稳健性要求开发者准确捕获和解析这些代码，以便驱动界面状态的流转、触发指数退避的重试算法，或向用户展示具备高度可理解性的错误提示 。

协议规范将状态码划分为五个具有特定指代意义的类别 ：

|**状态类别**|**数字区间**|**核心语义意义**|**典型业务场景与状态码解析**|
|---|---|---|---|
|**信息性响应**|100 - 199|请求已初步收到，服务器正在继续后续处理步骤。|**100 Continue**：指示客户端应继续发送带有大型 Payload 的请求体 。<br><br>  <br><br>**101 Switching Protocols**：常见于握手阶段，服务器同意将 HTTP 协议升级为 WebSocket 长连接 。|
|**成功响应**|200 - 299|客户端的意图已被服务器成功接收、理解并最终接受。|**200 OK**：最普遍的成功代码，用于标准的 `GET` 检索或成功的表单 `POST` 。<br><br>  <br><br>**201 Created**：专门用于回应导致数据库中新实体资源被创建的 `POST` 请求 。<br><br>  <br><br>**204 No Content**：通常用于成功的 `DELETE` 操作，告知客户端操作成功但无实体内容返回 。|
|**重定向指令**|300 - 399|客户端必须执行特定的额外操作（通常是发起新的请求）才能完成业务逻辑。|**301 Moved Permanently**：资源的 URI 已永久变更，有利于 SEO 权重的转移 。<br><br>  <br><br>**304 Not Modified**：客户端 HTTP 缓存有效，服务器告知无需重新下载资源，极大地节省了带宽资源 。|
|**客户端错误**|400 - 499|错误源于客户端，可能因为请求格式异常、凭据缺失或访问权限不足。|**400 Bad Request**：前端提交了格式错误的 JSON 载荷，或未通过后端的字段校验机制 。<br><br>  <br><br>**401 Unauthorized**：请求缺失合法的身份认证令牌（如 JWT token 过期或未携带） 。<br><br>  <br><br>**403 Forbidden**：用户已成功认证身份，但根据 RBAC/ABAC 模型，当前角色无权访问该接口 。<br><br>  <br><br>**404 Not Found**：请求的路由端点或特定资源实体在服务器上不存在 。|
|**服务器端错误**|500 - 599|服务器在处理一个表面上完全合法的请求时，由于内部故障而崩溃。|**500 Internal Server Error**：捕获到未处理的后端异常、数据库连接超时或底层语法崩溃 。|

高内聚低耦合的 Web 架构能够利用这些标准代码，将网络环境的波动状态与前端应用的核心业务状态进行完美的隔离。例如，当前端侦测到 API 响应的 `status` 为 `401 Unauthorized` 时，系统应当自动触发刷新 Token 的子例程，或者将用户的视图层强行路由至登录页面；而当遭遇到 `500` 或 `503` 状态时，应当立即切断可能导致雪崩效应的持续重试机制，向用户展示优雅的降级失败界面，并通过遥测系统向后端的日志收集模块自动发送报警信号 。

## 后端请求处理与并发架构范式

异步 Web 通信系统的整体效率不仅仅取决于前端技术的优化，更受到后端服务器在处理海量高并发 HTTP 连接时的底层架构限制。在当前的工业界中，处理从前端传入的复杂 JSON 请求主要存在两种被广泛应用的企业级架构范式：以 Node.js (Express.js) 为代表的事件驱动异步非阻塞架构，以及以 Java (Spring Boot) 为代表的多线程同步架构 。

Node.js 构建在高性能的 Chrome V8 引擎之上，其核心优势在于独特的单线程、事件驱动和非阻塞 I/O 模型 。当一个基于 Express.js 的服务端节点在同一瞬间接收到数以千计的高并发 JSON `POST` 请求时，它绝不会为每一个传入的连接分配或派生新的系统级线程。相反，主线程会将所有耗时的 I/O 操作（如发起数据库查询、读取文件系统或向第三方网关转发 API 调用）委托给操作系统底层的异步后台线程池，主线程自身则立即被释放，继续受理源源不断的下一个传入请求 。这种范式在处理属于 I/O 密集型（I/O-bound）的微服务时，能够展现出无与伦比的极高吞吐量表现 。

在需要并发处理的场景中，例如一个复合型的 Express 路由终点必须同时查询并更新三个不同的下游微服务，开发者可以利用 JavaScript 原生的 `Promise.all()` 特性，将三次独立的网络通信完全并行化发出，这可以指数级地缩短聚合响应的总时间 ：

JavaScript

```
// Express.js 异步非阻塞处理 JSON 负载并分发多个外部请求
const express = require('express');
const axios = require('axios');
const app = express();

// 挂载中间件，将请求的原始主体自动反序列化为 JSON
app.use(express.json());

app.post('/api/orchestrate', async (req, res) => {
  try {
    const payload = req.body;
    
    // 性能优化：并发向三个不同的下游服务分发异步HTTP请求
    const = await Promise.all([
      axios.post('http://internal.auth.svc/verify', payload),
      axios.post('http://internal.data.svc/update', payload),
      axios.post('http://internal.logger.svc/append', payload)
    ]);

    // 组装最终响应
    res.status(200).json({
      status: 'SUCCESS',
      details: {
        auth: authRes.data,
        updated: dataRes.data
      }
    });
  } catch (error) {
    // 捕获并发链中的任何异常，返回标准的 500 状态码
    res.status(500).json({ error: "微服务编排期间发生内部服务器错误" });
  }
});
```

与此形成对比的是，庞大且严谨的 Spring Boot 生态系统在传统上采用的是每请求一线程（Thread-per-request）的同步处理模型 。在这一模型下，每当一个新的 HTTP 请求抵达服务器网关，内置的 Tomcat 容器就会从预先初始化的线程池中专门划拨一个物理线程来全程负责该请求的完整生命周期：包括接收 JSON 请求体、执行安全校验、贯穿复杂的业务逻辑运算，最后执行并等待关系型数据库的事务提交 。

虽然在面对极端流量尖峰时，这种模型存在线程池被迅速耗尽（Thread Starvation）的固有风险，但该架构在处理 CPU 密集型（CPU-bound）任务时却具有不可替代的霸主地位 。对于诸如高强度密码学哈希运算、海量内存数据的复杂数学聚合、或是深度嵌套且巨大的 JSON 对象的深度反序列化及对象关系映射（ORM）等繁重计算任务，采用单线程模型的 Node.js 极易发生致命的事件循环阻塞。而 Java 则凭借其强大的多线程并行计算能力和成熟的并发调度机制，能够将复杂运算均匀分配至多核 CPU 上，确保整个系统的高可用性与计算吞吐极限 。

## 结论

现代 Web 后端与前端交互架构的核心构建，依托于一套高度精密、层层解耦的底层协议栈、数据格式规范以及异步编程接口。从历史上极其冗长晦涩的 XML 数据格式和高度依赖回调地狱、状态机机制混杂的 `XMLHttpRequest` 传统 API，全面演进至拥有极其轻量化解析特性的 JSON 标准和基于 Promise 链式驱动的 Fetch API，这一技术跃迁生动地揭示了整个软件工业界向声明式编程、非阻塞 I/O 处理以及流式数据操作架构的不可逆转移。

为了在生产环境中安全且健壮地实施这些复杂的架构系统，工程师们必须建立深厚的技术认知底蕴。这不仅包括严格甄别静态数据与可执行代码的边界，强行废除一切带有潜在漏洞的 `eval()` 求值函数并采用具备契约级严谨性的内置解析方法；还要求开发者在架构设计初期就严谨且周密地编排跨域资源共享（CORS）的准入逻辑，利用协商缓存等手段极致地压榨预检网络请求所带来的不必要性能损耗。此外，还需构建具有高度健壮性的双层错误捕获捕获网络层与协议层异常，通过精确解析语义化的 HTTP 状态码来进行故障的智能分级和重试调度。最终，只有熟练掌握前后端异步调度的全链路细节，方能打造出在延迟波动下具备高度韧性、在安全层面无懈可击，并且能够与底层高并发后端服务实现无缝、高吞吐整合的现代化企业级 Web 应用程序。

