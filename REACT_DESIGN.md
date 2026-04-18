# E-Book 项目 React 设计文档（更新版）

本文档面向初学者，解释当前 `react-version` 分支中 React 项目的真实实现结构。  
重点是：项目已经重构为**标准数据路由（Data Router）+ Root 嵌套路由**风格，并且 `App.jsx` 仅承担路由装配职责。

---

## 0. 项目目标与约束

这是一个电子书商城单页应用（SPA），核心页面包括：

1. 登录页
2. 书籍列表页
3. 书籍详情页
4. 购物车页
5. 订单页
6. 用户信息页

实现约束：

- 不改变原有 UI 风格与交互体验；
- 数据仍由前端文件（`Data.json`）读取并在前端内存仓库中维护；
- 页面之间保持数据关联（例如列表点“三体”，详情展示“三体”）；
- 路由层全面采用数据路由能力（`loader/action/redirect`）。

---

## 1. 先理解：什么是数据路由

React Router 6.4+ 的数据路由模式，把“页面跳转”和“数据读写”绑定到路由上：

1. `loader`：路由进入前读取数据（读）
2. `action`：路由提交时处理写操作（写）
3. `redirect`：在路由逻辑中完成跳转
4. `useLoaderData`：页面读取当前路由 loader 返回的数据
5. `Form/useSubmit`：页面触发 action

可以把它理解为“前端路由控制器”：

- 页面组件尽量只负责渲染；
- 数据来源和写入路径统一在路由模块里管理。

---

## 2. 最新目录结构与职责

```text
react-ebook/
├── public/
│   └── assets/                         # 静态资源（logo、封面等）
├── src/
│   ├── components/
│   │   ├── DashboardLayout.jsx         # 后台通用外壳
│   │   └── BookCard.jsx                # 书籍卡片
│   ├── data/
│   │   ├── Data.json                   # 初始数据
│   │   └── appStore.js                 # 前端内存数据仓库
│   ├── pages/
│   │   ├── LoginPage.jsx               # 登录模块（含 loginLoader/loginAction）
│   │   ├── BooksPage.jsx               # 书城模块（含 booksLoader/booksAction/BooksRoute）
│   │   ├── BookDetailPage.jsx          # 详情模块（含 detail loader/action/route）
│   │   ├── CartPage.jsx                # 购物车模块（含 cart loader/action/route）
│   │   ├── OrdersPage.jsx              # 订单模块（含 orders loader/action/route）
│   │   └── UserPage.jsx                # 用户模块（含 user loader/action/route）
│   ├── routes/
│   │   ├── Root.jsx                    # RootRoute / ProtectedRootRoute
│   │   ├── authRouteHandlers.js        # authRedirectLoader / requireAuthLoader / logoutAction
│   │   └── RouteErrorBoundary.jsx      # 路由错误边界
│   ├── App.jsx                         # 只做 router 装配与 App 壳
│   ├── main.jsx                        # React 挂载入口
│   └── styles.css
└── ...
```

### 分层总结

- **App.jsx**：纯装配层（路由树 + `RouterProvider`）
- **pages/**：按业务模块下沉 loader/action/route bridge
- **routes/**：跨页面复用的根路由、鉴权与错误边界
- **data/appStore.js**：统一业务数据读写

---

## 3. 路由树（Root + children）

当前采用嵌套路由结构：

| 层级 | 路径 | loader | action | element | 说明 |
|---|---|---|---|---|---|
| Root | `/` | - | - | `RootRoute` | 顶层容器，挂统一错误边界 |
| Root child | `index` | `authRedirectLoader` | - | - | 访问 `/` 时按登录态分流 |
| Root child | `login` | `loginLoader` | `loginAction` | `LoginPage` | 登录页 |
| Root child | `logout` | - | `logoutAction` | - | 退出动作 |
| Protected parent | （无 path） | `requireAuthLoader` | - | `ProtectedRootRoute` | 受保护父路由 |
| Protected child | `books` | `booksLoader` | `booksAction` | `BooksRoute` | 书籍列表 |
| Protected child | `books/:bookId` | `bookDetailLoader` | `bookDetailAction` | `BookDetailRoute` | 详情 |
| Protected child | `cart` | `cartLoader` | `cartAction` | `CartRoute` | 购物车 |
| Protected child | `orders` | `ordersLoader` | `ordersAction` | `OrdersRoute` | 订单 |
| Protected child | `user` | `userLoader` | `userAction` | `UserRoute` | 用户页 |
| Root child | `*` | `authRedirectLoader` | - | - | 兜底分流 |

---

## 4. 为什么现在更“标准”

本次重构后，项目符合数据路由推荐形态：

1. **Root 嵌套路由**：不是扁平路径堆叠，而是根路由承载 children。
2. **模块归属清晰**：每个页面把本页面 `loader/action` 放在同文件。
3. **App 纯装配**：`App.jsx` 不再维护业务 loader/action，只做路由拼装。
4. **复用路由能力**：鉴权分流、错误边界抽到 `routes/` 目录复用。
5. **共享布局上移**：`DashboardLayout` 统一放在 `ProtectedRootRoute`，子页面不再重复包壳。

---

## 5. 鉴权与分流逻辑

### 5.1 `requireAuthLoader`

位置：`src/routes/authRouteHandlers.js`

- 用于受保护父路由；
- 未登录时直接 `redirect("/login")`；
- 已登录允许进入子路由（books/cart/orders/user）。

### 5.2 `authRedirectLoader`

- 用于 `/` 和 `*`；
- 已登录跳 `/books`；
- 未登录跳 `/login`。

### 5.3 `logoutAction`

- 清理登录态（调用 `appStore.logout()`）；
- 重定向回登录页。

### 5.4 `ProtectedRootRoute`（共享 Dashboard）

- 在父路由统一渲染 `DashboardLayout + Outlet`；
- 从当前激活子路由 loader 数据中读取 `username/search`；
- 统一处理顶部搜索与退出动作（提交到当前子路由 action 或 `/logout`）。

---

## 6. 页面模块的统一模式

除了登录页，其余业务页面都遵循类似结构：

1. `xxxLoader`：读取该页需要的数据
2. `xxxAction`：处理该页动作分支（通过 `intent`）
3. `XxxRoute`：桥接组件（`useLoaderData`，按需再用 `useSubmit`）
4. `XxxPage`：纯渲染组件

另外，通用壳层（侧栏/顶栏/搜索/头像）由 `ProtectedRootRoute` 统一提供，页面仅保留业务内容区。

---

## 7. 数据流（以书城与购物车为例）

### 7.1 书城搜索（不跳转）

1. 顶部共享搜索框变化（在 `ProtectedRootRoute` 中）  
2. 提交 `intent=set-search` 到当前子路由 action（`navigate: false`）
3. 更新 `appStore.searchByPage.books`
4. 当前路由数据刷新，地址不变

### 7.2 加入购物车（跳转）

1. 卡片提交 `intent="add-to-cart"`
2. `booksAction` 调用 `addToCart(bookId)`
3. `redirect("/cart")`
4. `cartLoader` 返回最新购物车数据

---

## 8. appStore 的角色

`src/data/appStore.js` 是前端演示仓库（内存态）：

- `getSnapshot()` 提供给 loader 安全读取；
- `addToCart / updateCartQty / removeCartItem / checkoutSelected` 处理购物车；
- `updateOrderStatus` 处理订单状态；
- `login / logout` 处理登录态与本地存储。

注意：这是教学项目中的前端数据层，不是后端数据库。

---

## 9. 页面间数据关联（列表 -> 详情）

项目保留了“Prop + State 关联”的关键要求：

1. 列表、购物车、订单页进入详情时使用 `Link state={{ book }}`
2. 详情页优先使用 `location.state?.book`
3. 若没有 state（如地址栏直达），再使用 `loader` 的 `detailBook`

这样既保证“点哪本看哪本”，又兼容刷新和直达链接。

---

## 10. 错误处理

`src/routes/RouteErrorBoundary.jsx` 作为路由错误边界：

- 对 `isRouteErrorResponse(error)` 显示状态码信息；
- 其他异常显示通用兜底提示；
- 避免局部异常导致整页白屏。

---

## 11. 当前实现边界

为了课堂演示，当前登录仍是简化逻辑：

- 登录输入做基本非空判断；
- 支持“直接进入书城（guest）”流程；
- 不接真实后端鉴权接口。

这部分可在后续接入真实账号体系时替换，但不会影响当前路由架构。

---

## 12. 结论

当前 `react-version` 已完成从“集中式路由逻辑”向“Root 嵌套 + 模块下沉”的重构：

1. 路由结构更标准（Data Router 官方推荐思路）
2. 代码职责更清晰（App 装配、模块自治）
3. 功能与样式保持原有行为不变
4. 对初学者更友好（读写链路固定、排查路径更明确）
