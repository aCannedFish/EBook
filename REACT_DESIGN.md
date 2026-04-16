# E-Book 项目 React 设计文档（扩展版）

本文档面向初学者，目标是把当前项目的 **实现细节** 讲清楚，尤其是 React Router 数据路由（Data Router）相关概念与落地方式。

---

## 0. 先读这段：项目在做什么

这是一个基于 React 18 + Vite 的电子书商城前端，包含登录、书籍浏览、详情、购物车、订单、用户信息等页面。  
项目采用 React Router 6.4+ 的**数据路由模式**，把“页面数据读取”和“用户操作写入”都交给路由层处理。

---

## 1. 初学者必备：Router 基本概念

在进入代码前，先理解 8 个关键词：

1. **Route（路由）**：URL 路径和页面逻辑的映射关系。  
2. **createBrowserRouter**：用“路由对象数组”定义整站路由。  
3. **RouterProvider**：把 router 注入 React 树，让路由生效。  
4. **loader（读）**：进入页面前先执行的数据读取函数。  
5. **action（写）**：处理提交动作（表单/按钮）的写入函数。  
6. **redirect**：在 loader/action 中做跳转（如未登录跳到 `/login`）。  
7. **useLoaderData**：页面读取 loader 返回的数据。  
8. **useSubmit / Form**：页面触发 action 写操作。

> 可以把数据路由理解成“页面控制器”：
> - loader 像查询接口；
> - action 像写入接口；
> - 页面组件只负责渲染和触发动作。

---

## 2. 项目结构与职责分层

```text
react-ebook/
├── public/                 # 静态资源（图片、SVG）
├── src/
│   ├── components/
│   │   ├── DashboardLayout.jsx   # 通用外壳（侧栏+顶栏+搜索+用户区）
│   │   └── BookCard.jsx          # 书籍卡片（详情入口+加购入口）
│   ├── data/
│   │   ├── Data.json             # 初始数据（书籍/用户/购物车/订单）
│   │   └── appStore.js           # 前端内存仓库（统一读写业务数据）
│   ├── pages/
│   │   ├── LoginPage.jsx
│   │   ├── BooksPage.jsx
│   │   ├── BookDetailPage.jsx
│   │   ├── CartPage.jsx
│   │   ├── OrdersPage.jsx
│   │   └── UserPage.jsx
│   ├── App.jsx              # 路由表 + 全部 loader/action + 路由桥接组件
│   ├── main.jsx             # React 挂载入口
│   └── styles.css           # 全局样式
└── ...
```

### 分层思路

- **路由层（App.jsx）**：定义 URL、鉴权、数据读写入口。  
- **数据层（appStore.js）**：维护业务状态和增删改查函数。  
- **页面层（pages）**：渲染 UI，接收数据与回调。  
- **组件层（components）**：可复用 UI 单元。  

---

## 3. 路由总览（当前代码）

| 路径 | loader | action | 页面 element | 说明 |
|---|---|---|---|---|
| `/` | `authRedirectLoader` | - | - | 按登录态分流到 `/books` 或 `/login` |
| `/login` | `loginLoader` | `loginAction` | `LoginPage` | 登录页（登录/直接进入） |
| `/logout` | - | `logoutAction` | - | 退出登录 |
| `/books` | `booksLoader` | `booksAction` | `BooksRoute` | 书籍列表 |
| `/books/:bookId` | `bookDetailLoader` | `bookDetailAction` | `BookDetailRoute` | 书籍详情 |
| `/cart` | `cartLoader` | `cartAction` | `CartRoute` | 购物车 |
| `/orders` | `ordersLoader` | `ordersAction` | `OrdersRoute` | 订单 |
| `/user` | `userLoader` | `userAction` | `UserRoute` | 用户信息 |
| `*` | `authRedirectLoader` | - | - | 兜底分流 |

---

## 4. 鉴权设计（登录与未登录的边界）

核心函数：`requireAuthSnapshot()`

```js
function requireAuthSnapshot() {
  const snapshot = getSnapshot();
  if (!snapshot.isLoggedIn) throw redirect("/login");
  return snapshot;
}
```

### 作用

- 所有业务页 loader/action 开头都调用它。  
- 未登录用户无法访问 `/books /cart /orders /user ...`。  
- 鉴权不分散在页面组件里，而是集中在路由层。

---

## 5. 登录页逻辑（当前实现细节）

登录页 action 有两个分支：

1. `intent="login"`：用户名密码非空即可调用 `login(username, remember)` 并跳到 `/books`。  
2. `intent="guest"`：点击“直接进入书城”，用输入用户名或默认 `"同学A"` 直接登录并跳到 `/books`。  

### 重要说明

当前版本属于教学演示实现：  
- **未做真实用户存在性和密码正确性校验**；  
- 只要表单内容满足基本非空，即可进入登录态。  

---

## 6. appStore 数据仓库详解

`src/data/appStore.js` 是项目数据“单一真相源”（Single Source of Truth）。

### 6.1 核心状态字段

- `books`：书籍列表（来自 `Data.json`）  
- `user`：当前登录用户展示信息  
- `cartItems`：购物车条目（`bookId/qty/selected`）  
- `orders`：订单列表  
- `searchByPage`：按页面隔离搜索词  
- `isLoggedIn`：登录状态

### 6.2 关键函数职责

- `getSnapshot()`：返回防御性复制快照，供 loader 使用。  
- `login/logout()`：维护登录态和 localStorage。  
- `setPageSearch()`：更新某页面搜索词。  
- `addToCart()`：加购（同书叠加，上限 4）。  
- `toggleSelectAllCart / toggleCartItem / updateCartQty / removeCartItem`：购物车编辑。  
- `checkoutSelected()`：把选中购物车行转成订单并移除。  
- `updateOrderStatus()`：订单状态更新。  
- `getBookById()`：详情页按 id 查书籍。

### 6.3 为什么用 `getSnapshot()` 克隆

防止页面拿到可变引用后直接改仓库内部对象，保证写入必须经过 action + store 函数路径。

---

## 7. Intent 协议（action 分支开关）

项目采用 `intent` 字段做 action 分派，统一规则：

- 先 `readIntent(formData)` 取动作类型；
- 再根据 `if (intent === "...")` 进入对应业务分支。

常见 intent：

- `login` / `guest`
- `set-search`
- `add-to-cart`
- `toggle-select-all`
- `toggle-item`
- `update-qty`
- `remove-item`
- `checkout`
- `update-status`
- `buy-again`

这让每个路由只需一个 action，也能支持多种交互操作。

---

## 8. 页面实现细节（逐页）

### 8.1 LoginPage

- 用 `useLoaderData()` 读取默认用户名。  
- 用 `useSubmit()` 命令式提交 intent。  
- `<Form method="post">` 默认提交到当前路由 action（`/login`）。  

### 8.2 BooksPage + BookCard

- `BooksPage` 按搜索词过滤 `books`。  
- `BookCard`：
  - `Link to="/books/:id"` 进入详情（附带 `state.book`）；
  - `Form` 提交 `add-to-cart` 到 `/books` action。

### 8.3 BookDetailPage

- URL 参数 `bookId` + `location.state?.book` 双来源。  
- 优先使用 `state.book`（点击来源数据），否则用 loader 提供的 `detailBook`。  
- “加入购物车”通过当前详情路由 action 处理。  

### 8.4 CartPage

- 把 `cartItems` 与 `books` 合并成 `rows`（渲染友好结构）。  
- 派生值：
  - `selectedRows`
  - `allSelected`
  - `subtotal`  
- 所有编辑动作通过 `onXxx` -> `submit` -> `cartAction`。

### 8.5 OrdersPage

- 把 `orders` 与 `books` 关联，生成带 `book/total` 的渲染行。  
- `pending` 可取消/付款，`cancelled` 可再次购买。  
- 状态按钮触发 `update-status` 或 `buy-again`。

### 8.6 UserPage

- 展示用户名、邮箱、会员等级。  
- 目前“编辑”按钮为演示位（无写入逻辑）。  

---

## 9. 典型业务链路（端到端）

### 9.1 登录进入书城

1. 打开 `/login`  
2. `loginLoader` 返回默认用户名  
3. 提交 `intent=login`  
4. `loginAction -> appStore.login -> redirect("/books")`  
5. `/books` loader 拉取最新快照并渲染

### 9.2 书城加购

1. `BookCard` 提交 `intent=add-to-cart`  
2. `booksAction` 调 `addToCart(bookId)`  
3. 重定向 `/cart`  
4. `cartLoader` 返回更新后的购物车数据

### 9.3 购物车结算

1. 点击“结算”提交 `intent=checkout`  
2. `cartAction -> checkoutSelected()`  
3. 购物车选中项转订单，购物车删除对应项  
4. 跳转 `/orders`

---

## 10. `navigate: false` 为什么重要

在 `useSubmit` 里设置 `navigate: false`，表示：

- 执行 action；
- 刷新当前路由数据；
- **不改变地址栏路径**。

适用于“页内微交互”，如搜索、勾选、改数量、移除等。

---

## 11. 错误边界（errorElement）

项目为主要路由配置了 `errorElement: <RouteErrorBoundary />`：

- `isRouteErrorResponse(error)`：显示状态码和状态文案；  
- 其他错误：显示通用“页面发生异常”。  

好处：局部路由报错时不会整站白屏。

---

## 12. 与传统写法对比（帮助理解）

### 传统模式
- 页面 `useEffect` 拉数据  
- 页面里 `useState` 管全局逻辑  
- 组件层层传状态和回调

### 当前数据路由模式
- loader 统一读  
- action 统一写  
- 页面组件只渲染 + 触发动作  

结论：更容易维护，业务流更可追踪。

---

## 13. 当前实现的边界与可扩展方向

### 当前边界（有意简化）

- 登录是教学版，不做严格账号体系校验。  
- 数据仓库为前端内存对象，适合课堂演示，不是生产后端数据库。  

### 后续可扩展

1. 把 `appStore` 替换为真实 API。  
2. 为登录引入密码校验和用户注册体系。  
3. 给用户页“编辑”按钮补 action。  
4. 增加 loader/action 的单元测试。  

---

## 14. 关键术语小词典

- **SPA**：单页应用，页面切换不整页刷新。  
- **Data Router**：路由层同时管理页面渲染与数据读写。  
- **Loader**：路由进入前读数据。  
- **Action**：路由提交后写数据。  
- **Redirect**：在路由逻辑中跳转。  
- **Snapshot**：某一时刻的数据副本。  
- **Intent**：动作意图字段，用于 action 分支判断。  



