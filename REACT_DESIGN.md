# EBook React 项目设计文档

本文档面向课程作业与代码阅读场景，完整说明当前 `react-ebook` 的实现结构、交互逻辑、路由设计与数据交互方式。  
项目核心目标是：在单页应用（SPA）中使用 **React Router Data Router** 完成页面切换与数据读写统一管理。

---

## 1. 文件结构与运行方法

### 1.1 项目结构（核心目录）

```text
react-ebook/
├── public/
│   └── assets/                       # 静态资源（logo、头像、封面）
├── src/
│   ├── App.jsx                       # 路由装配入口（createBrowserRouter）
│   ├── main.jsx                      # React 挂载入口
│   ├── styles.css                    # 全局样式
│   ├── components/
│   │   ├── DashboardLayout.jsx       # 受保护页面共享壳层（侧栏+顶栏）
│   │   └── BookCard.jsx              # 书籍卡片组件（详情+加购）
│   ├── pages/
│   │   ├── LoginPage.jsx             # 登录页（含 loginLoader/loginAction）
│   │   ├── BooksPage.jsx             # 书城页（booksLoader/booksAction）
│   │   ├── BookDetailPage.jsx        # 详情页（bookDetailLoader/bookDetailAction）
│   │   ├── CartPage.jsx              # 购物车页（cartLoader/cartAction）
│   │   ├── OrdersPage.jsx            # 订单页（ordersLoader/ordersAction）
│   │   └── UserPage.jsx              # 用户页（userLoader/userAction）
│   ├── routes/
│   │   ├── Root.jsx                  # RootRoute / ProtectedRootRoute（共享布局）
│   │   ├── authRouteHandlers.js      # 认证相关 loader/action
│   │   └── RouteErrorBoundary.jsx    # 路由级错误边界
│   ├── router/
│   │   └── routeUtils.js             # 通用路由辅助函数（intent/auth/redirectTo）
│   └── data/
│       ├── Data.json                 # 前端演示数据源（书籍/用户/初始购物车/初始订单）
│       └── appStore.js               # 前端内存数据仓库（统一读写）
├── package.json
└── vite.config.js
```

### 1.2 启动与构建

在 `react-ebook/` 目录执行：

```bash
npm install
npm run dev
```

默认开发地址通常为：

```text
http://localhost:5173
```

生产构建：

```bash
npm run build
npm run preview
```

---

## 2. 界面交互设计

### 2.1 全局交互框架

受保护页面（书城/详情/购物车/订单/用户）共享 `DashboardLayout`，包含：

1. 左侧导航：书城、购物车、订单、用户信息、退出。
2. 顶部搜索框：根据当前路由动态显示不同 placeholder。
3. 顶部用户区：显示当前用户名和头像。

共享布局由 `ProtectedRootRoute` 提供，不再由各页面重复包裹。

### 2.2 登录页交互（`LoginPage`）

登录页有两种进入业务区方式：

1. **登录按钮**
    - 校验用户名/密码非空；
    - 提交 `intent=login` 到 `loginAction`；
    - 登录成功后跳转 `/books`。

2. **直接进入书城按钮**
    - 提交 `intent=guest`；
    - 用户名为空时使用默认值 `"同学A"`；
    - 跳转 `/books`。

附加交互：

- `Remember me` 对应 `remember` 字段，控制是否保存记住用户名。
- “忘记密码？”当前是占位入口（链接到 `/login`）。

### 2.3 书城页交互（`BooksPage` + `BookCard`）

1. 顶部搜索会实时过滤书名/作者/分类（前端模糊匹配）。
2. 每张书卡有两个主要动作：
    - `查看详情`：跳转 `/books/:bookId`，并通过 `state.book` 传递当前书对象。
    - `加入购物车`：通过 `<Form method="post">` 提交 `intent=add-to-cart`。

### 2.4 详情页交互（`BookDetailPage`）

详情页的数据解析优先级：

1. `location.state.book`（从列表/购物车/订单带来的上下文数据）；
2. `loader` 根据 `bookId` 查到的 `detailBook`（兼容地址栏直达）。

主要操作：

- `加入购物车`（`intent=add-to-cart`）；
- `立即购买`（跳到订单页）；
- `继续逛书城`（跳回 `/books`）。

若书籍不存在，显示“未找到对应书籍”页内提示。

### 2.5 购物车页交互（`CartPage`）

1. 支持全选/单选；
2. 支持数量调整（1~4）；
3. 支持移除单条；
4. 结算只统计已选中条目；
5. `结算` 会把已选条目转为订单并跳到 `/orders`。

### 2.6 订单页交互（`OrdersPage`）

订单状态：

- `pending`：可取消、可付款；
- `paid`：可查看（按钮占位）；
- `cancelled`：可再次购买（会重新加购）。

页面支持按订单号/书名搜索。

### 2.7 用户页交互（`UserPage`）

展示用户基本信息（用户名、邮箱、会员等级）。  
“编辑”按钮为当前版本占位交互。

---

## 3. 路由设计

### 3.1 路由总体思路

项目使用数据路由：

- 路由在 `App.jsx` 中通过 `createBrowserRouter` 声明；
- 页面数据读取走 `loader`；
- 页面写操作走 `action`；
- 跳转在 `loader/action` 中通过 `redirect` 完成；
- 受保护区使用父路由统一鉴权与共享布局。

### 3.2 路由树与职责

| 路径层级 | 路径 | loader | action | element | handle |
|---|---|---|---|---|---|
| Root | `/` | - | - | `RootRoute` | - |
| Root child | `index` | `authRedirectLoader` | - | - | - |
| Root child | `login` | `loginLoader` | `loginAction` | `LoginPage` | - |
| Root child | `logout` | - | `logoutAction` | - | - |
| Protected parent | (无 path) | `requireAuthLoader` | - | `ProtectedRootRoute` | - |
| Protected child | `books` | `booksLoader` | `booksAction` | `BooksRoute` | `searchPlaceholder` |
| Protected child | `books/:bookId` | `bookDetailLoader` | `bookDetailAction` | `BookDetailRoute` | `searchPlaceholder` |
| Protected child | `cart` | `cartLoader` | `cartAction` | `CartRoute` | `searchPlaceholder` |
| Protected child | `orders` | `ordersLoader` | `ordersAction` | `OrdersRoute` | `searchPlaceholder` |
| Protected child | `user` | `userLoader` | `userAction` | `UserRoute` | `searchPlaceholder` |
| Root child | `*` | `authRedirectLoader` | - | - | - |

### 3.3 关键路由函数详解

#### 3.3.1 `authRedirectLoader`（`/` 与 `*`）

- 未登录：`redirect("/login")`
- 已登录：`redirect("/books")`

用途：统一首页分流与兜底路径分流。

#### 3.3.2 `requireAuthLoader`（受保护父路由）

1. 校验登录态；
2. 未登录重定向 `/login`；
3. 返回 `{ username }` 供共享壳层显示。

#### 3.3.3 `logoutAction`

1. 清理登录态（`appStore.logout()`）；
2. 跳转 `/login`。

### 3.4 各业务路由 loader/action 详细说明

#### 3.4.1 `/login`

**loader: `loginLoader`**

- 已登录直接跳 `/books`；
- 未登录返回默认用户名（记住我场景）。

**action: `loginAction`**

- `intent=login`：非空校验后调用 `login(username, remember)`；
- `intent=guest`：游客登录；
- 成功后统一 `redirect("/books")`。

#### 3.4.2 `/books`

**loader: `booksLoader`**

- 返回 `books`、`search`。

**action: `booksAction`**

- `intent=set-search`：更新书城搜索词；
- `intent=add-to-cart`：加购并按 `redirectTo` 跳转（默认 `/cart`）。

#### 3.4.3 `/books/:bookId`

**loader: `bookDetailLoader`**

- 根据参数返回 `detailBook`；
- 返回 `search`（供共享顶栏搜索框）。

**action: `bookDetailAction`**

- `intent=set-search`：更新详情页搜索词；
- `intent=add-to-cart`：按 `bookId` 加购并跳转。

#### 3.4.4 `/cart`

**loader: `cartLoader`**

- 返回 `books`、`cartItems`、`search`。

**action: `cartAction`**

- `intent=set-search`：更新购物车搜索词；
- `intent=toggle-select-all`：全选/取消全选；
- `intent=toggle-item`：单行勾选；
- `intent=update-qty`：更新数量（1~4）；
- `intent=remove-item`：移除商品；
- `intent=checkout`：结算并跳转 `/orders`。

#### 3.4.5 `/orders`

**loader: `ordersLoader`**

- 返回 `books`、`orders`、`search`。

**action: `ordersAction`**

- `intent=set-search`：更新订单搜索词；
- `intent=update-status`：更新订单状态（pending/paid/cancelled）；
- `intent=buy-again`：再次购买并按 `redirectTo` 跳转（默认 `/books`）。

#### 3.4.6 `/user`

**loader: `userLoader`**

- 返回 `user`、`username`、`search`。

**action: `userAction`**

- `intent=set-search`：更新用户页搜索词。

### 3.5 共享布局如何与路由协作（重点）

`ProtectedRootRoute` 使用：

1. `useLoaderData()` 获取父路由返回的 `username`；
2. `useMatches()` 找到当前激活子路由：
    - 读取该路由 `handle.searchPlaceholder`；
    - 读取该路由 `data.search`；
3. 顶部搜索提交 `intent=set-search` 到当前激活子路由 action（`navigate:false`）。

这保证了：

- 壳层统一；
- 搜索行为仍由各页面 action 处理；
- 页面逻辑归页面、壳层逻辑归父路由。

---

## 4. 数据交互设计

### 4.1 数据来源与仓库职责

数据来源：`src/data/Data.json`。  
运行时数据仓库：`src/data/appStore.js`。

`appStore` 是本项目的前端数据单一读写入口：

- `loader` 从这里读取快照（`getSnapshot`）；
- `action` 调这里的函数写数据（如 `addToCart`、`checkoutSelected`）。

### 4.2 仓库状态结构

核心字段：

1. `books`
2. `user`
3. `cartItems`
4. `orders`
5. `searchByPage`
6. `isLoggedIn`

### 4.3 关键数据操作函数

#### 认证相关

- `login(username, remember)`
- `logout()`
- `getRememberedUsername()`

#### 搜索相关

- `setPageSearch(pageKey, value)`

#### 购物车相关

- `addToCart(bookId)`
- `toggleSelectAllCart(checked)`
- `toggleCartItem(bookId, checked)`
- `updateCartQty(bookId, qty)`
- `removeCartItem(bookId)`
- `checkoutSelected()`

#### 订单相关

- `updateOrderStatus(orderId, status)`

#### 详情查询

- `getBookById(bookId)`

### 4.4 路由与数据仓库的交互协议

`action` 分支统一使用 `intent`：

- 读取函数：`readIntent(formData)`；
- 可选跳转路径：`readRedirectPath(formData, fallback)`；
- 鉴权快照：`requireAuthSnapshot()`。

这种协议让每个 action 可以在单一入口中处理多种操作，避免创建过多分散接口。

### 4.5 典型数据流（端到端）

#### A. 登录进入书城

1. `/login` -> `loginLoader` 返回默认用户名；
2. 提交 `intent=login`；
3. `loginAction` 调 `appStore.login`；
4. 跳转 `/books`；
5. `booksLoader` 输出页面数据。

#### B. 书城加购 -> 购物车

1. `BookCard` 提交 `intent=add-to-cart`；
2. `booksAction` 调 `addToCart`；
3. `redirect("/cart")`；
4. `cartLoader` 返回最新购物车。

#### C. 购物车结算 -> 订单

1. 提交 `intent=checkout`；
2. `cartAction` 调 `checkoutSelected`；
3. 新增订单并移除已结算购物车项；
4. `redirect("/orders")`。

#### D. 订单取消后再次购买

1. `/orders` 提交 `intent=buy-again`；
2. `ordersAction` 调 `addToCart(bookId)`；
3. 跳转 `/books`。

---

## 5. 组件复用

### 5.1 `DashboardLayout`（布局复用）

复用范围：所有受保护页面。  
复用内容：

1. 左侧导航；
2. 顶部搜索；
3. 用户信息展示；
4. 统一内容插槽（`children`）。

收益：

- 统一视觉结构；
- 页面不重复维护侧栏和顶栏；
- 搜索与退出逻辑集中。

### 5.2 `BookCard`（业务卡片复用）

复用范围：书城书籍网格。  
复用内容：

1. 封面、标题、作者、价格、库存状态展示；
2. 查看详情入口；
3. 加购表单提交协议。

### 5.3 页面 Route Bridge 组件复用模式

每个页面模块都导出 `XxxRoute`，承担“路由数据到页面 props”的桥接：

1. `useLoaderData()` 取数据；
2. 需要写操作时用 `useSubmit()`；
3. 页面组件保持展示导向，降低耦合。

### 5.4 路由元信息复用（`handle.searchPlaceholder`）

各受保护子路由统一在 `handle` 声明搜索占位文案。  
共享布局统一读取，不再在布局组件里硬编码路径判断。

---

## 补充说明

1. 本项目是课程作业范式，数据层为前端内存仓库，不包含真实后端接口。
2. 当前登录逻辑是教学简化版（含游客直达），重在展示数据路由的组织方式。
3. 代码已实现“路由装配层（App）/路由逻辑层（pages+routes）/数据层（appStore）/复用组件层（components）”分离。

