# React 交互设计说明

## 1. 目标与设计定位

本项目在不改变既有 UI、数据与功能的前提下，采用 **React Router 数据式路由** 重构为单页应用，确保教学演示体验保持一致，同时提升架构可维护性。

覆盖页面：

- 登录页：`/login`
- 书城页：`/books`
- 详情页：`/books/:bookId`
- 购物车页：`/cart`
- 订单页：`/orders`
- 用户页：`/user`

设计目标：

1. 路由由路由对象统一声明，地址可直达与可回退。
2. 全局业务状态集中在根组件，通过 `props + 回调` 单向流转。
3. 页面数据统一来源于 `src/data/Data.json`。
4. 列表到详情保持数据关联：`Link state` 传递对象，URL 参数兜底定位。

> 设计注释：保持“教学型工程”风格，逻辑显式、注释可读、行为可追踪。

---

## 2. 工程结构与职责分层（详细）

```text
react-ebook/
  src/
    main.jsx                    # 应用入口：仅挂载 App
    App.jsx                     # 应用编排层：数据路由 + 全局状态 + 业务动作
    styles.css                  # 全局样式
    data/
      Data.json                 # 本地数据源（书籍、用户、购物车、订单）
    components/
      DashboardLayout.jsx       # 业务页面统一壳层
      BookCard.jsx              # 书籍卡片复用构件
      ProtectedRoute.jsx        # 路由守卫
    pages/
      LoginPage.jsx             # 登录与游客进入
      BooksPage.jsx             # 书籍列表与筛选
      BookDetailPage.jsx        # 书籍详情展示
      CartPage.jsx              # 购物车编辑与结算
      OrdersPage.jsx            # 订单查看与状态更新
      UserPage.jsx              # 用户资料与快捷入口
```

分层原则：

- **`App.jsx` = 容器层**：状态中心、动作中心、路由编排中心。
- **`pages/*` = 页面层**：消费状态、组织视图、计算派生数据。
- **`components/*` = 复用层**：壳层、卡片、守卫等高复用构件。
- **`data/Data.json` = 数据层**：前端直接读取的演示数据文件。

---

## 3. 路由与访问控制设计（数据式）

当前项目采用 `createBrowserRouter` 配置路由，并通过 `RouterProvider` 挂载。

路由结构：

- `/`：按 `isLoggedIn` 重定向到 `/books` 或 `/login`
- `/login`：公开页面
- `/books`、`/books/:bookId`、`/cart`、`/orders`、`/user`：受保护页面（`ProtectedRoute`）
- `*`：兜底重定向

关键点：

1. **数据式路由**：路由声明以对象数组表达，而非 `<Routes><Route>`。
2. **守卫复用**：`ProtectedRoute` 仍统一处理未登录重定向逻辑。
3. **路由包装组件**：`BooksRoute/BookDetailRoute/...` 在路由层将全局状态映射为页面 `props`。

---

## 4. 数据模型与状态管理设计

### 4.1 数据来源

`src/data/Data.json` 提供：

- `books`
- `user`
- `initialCart`
- `initialOrders`

### 4.2 全局状态（`App.jsx`）

- `isLoggedIn`
- `user`
- `cartItems`
- `orders`
- `searchByPage`（`books/detail/cart/orders/user`）

### 4.3 全局业务动作（`App.jsx`）

- 登录：`handleLogin`、`handleLogout`
- 购物车：`addToCart`、`toggleSelectAllCart`、`toggleCartItem`、`updateCartQty`、`removeCartItem`
- 订单：`checkoutSelected`、`updateOrderStatus`
- 搜索：`handlePageSearch`

React 风格体现：

- 状态上提（共享状态统一托管）
- 单向数据流（状态下发，事件上抛）
- 不可变更新（`map/filter/reduce`）

---

## 5. 页面设计思路（逐页）

### 5.1 `LoginPage.jsx`

- 受控表单管理输入
- 调用上层 `onLogin` 完成登录态写入
- `useNavigate` 跳转书城

### 5.2 `BooksPage.jsx`

- 本地关键词筛选（标题/作者/分类）
- 使用 `BookCard` 渲染网格
- 列表页仅负责展示与触发行为

### 5.3 `BookDetailPage.jsx`

- `useParams` 获取 `bookId`
- `useLocation` 读取 `Link state` 传来的 `book`
- 同时接收 `initialBook` prop（由路由包装组件提供）
- 三层定位策略：`state.book -> initialBook -> books.find(...)`
- 无效 ID 提供“未找到”分支

### 5.4 `CartPage.jsx`

- `cartItems + books` 拼装 `rows`
- 派生 `selectedRows/allSelected/subtotal`
- 支持勾选、改数量、移除、结算

### 5.5 `OrdersPage.jsx`

- 订单映射补齐书籍信息
- `statusMeta` 统一状态文案与样式
- 按状态展示对应操作按钮

### 5.6 `UserPage.jsx`

- 展示用户基础信息
- 提供购物车/订单快捷入口

---

## 6. 构件设计思路（components）

### 6.1 `DashboardLayout.jsx`

- 统一侧栏 + 顶栏 + 搜索 + 用户区
- 通过 `children` 承载页面内容

### 6.2 `BookCard.jsx`

- 单本书展示与入口操作
- 详情跳转使用 `to + state={{ book }}`

### 6.3 `ProtectedRoute.jsx`

- 统一登录态校验
- 未登录重定向 `/login`，已登录渲染 `<Outlet />`

### 6.4 `Layout.jsx`

- 保留兼容导出，避免旧引用失效

---

## 7. 项目采用的 React 风格总结

1. 函数组件 + Hooks。
2. 数据式路由（`createBrowserRouter`）。
3. `Context` 仅用于在路由包装组件中读取根状态（`AppStateContext`）。
4. 页面间数据关联同时使用 `prop` 与 `location.state`。
5. 派生数据优先，避免冗余状态。
6. 复用壳层与复用构件，保证页面一致性。

---

## 8. 与当前代码行为对齐

当前实现保持并满足：

1. 登录后进入书城，未登录无法访问业务页。
2. 列表页可跳详情页，详情数据与点击书籍保持一致。
3. 数据全部来自前端 `Data.json`。
4. 购物车、订单、用户页功能行为不变。
5. 页面 UI 样式与交互布局不变。
