# EBook 电子书城项目：React 架构与语法深度拆解手册

> **前言**：本手册基于当前最新代码重写，重点解释项目如何从声明式路由迁移到**数据式路由**，并保持 UI、功能、数据行为不变。

---

## 第一层：宏观架构 —— 项目是怎么“跑”起来的？

### 1. 入口文件：`main.jsx`（点火系统）

当前入口职责非常纯粹：

- **`createRoot`**：在 `#root` 挂载 React 应用。
- **`<StrictMode>`**：开发期额外检查。
- **`<App />`**：路由能力不再由 `main.jsx` 提供，而由 `App.jsx` 内部的 `RouterProvider` 提供。

> 关键变化：不再在入口层使用 `<BrowserRouter>`。

### 2. 根组件：`App.jsx`（中央控制塔）

`App.jsx` 现在同时承担四个角色：

1. **状态中心**：维护 `isLoggedIn/user/cartItems/orders/searchByPage`。
2. **动作分发器**：维护 `handleLogin/addToCart/checkoutSelected/...`。
3. **路由编排器**：使用 `createBrowserRouter` 声明路由对象。
4. **上下文提供者**：通过 `AppStateContext.Provider` 向路由包装组件提供共享状态与动作。

---

## 第二层：模块化设计 —— 为什么要这样分文件？

### 1. 布局抽象：`DashboardLayout.jsx`

- 通过 `children` 插槽承载各页面主体内容。
- 统一侧栏、顶栏、搜索框、用户信息区。
- 减少页面重复壳层代码。

### 2. 权限隔离：`ProtectedRoute.jsx`

- 接收 `isLoggedIn`。
- 未登录：`<Navigate to="/login" replace />`。
- 已登录：`<Outlet />`。

### 3. 展示单元：`BookCard.jsx`

- 只消费 `book` 与 `onAddToCart`。
- 详情跳转使用 `Link state={{ book }}`，把当前书籍对象随跳转一并传递。

---

## 第三层：函数逻辑 —— 交互是如何流动的？

项目遵循：**数据下行（Props Down），事件上行（Events Up）**。

### 1. “列表跳详情”交互全追踪

1. 用户在 `BookCard` 点击“查看详情”。
2. `Link` 跳到 `/books/:bookId`，并附带 `state.book`。
3. `BookDetailPage` 同时读取：
   - `location.state?.book`（首选）
   - `initialBook`（由路由包装组件基于 `bookId` 传入）
   - `books.find(...)`（最终兜底）
4. 页面展示与用户点击书籍保持一致。

### 2. “加购”交互全追踪

1. 子组件触发 `onAddToCart(book.id)`。
2. 事件上抛至 `App.jsx`。
3. `addToCart` 使用不可变更新修改 `cartItems`。
4. 购物车与相关页面自动重渲染。

---

## 第四层：语法百科全书 —— 这些代码背后是什么？

### 1. 数据式路由核心 API

- **`createBrowserRouter(routeObjects)`**：以对象数组定义整套路由。
- **`RouterProvider`**：将 router 注入 React 树。
- **`children` 路由**：用于受保护页面分组。

### 2. `useContext` + `createContext`

`App.jsx` 中定义 `AppStateContext`，路由包装组件通过 `useAppState()` 读取共享状态，避免层层手动传参。

### 3. `useState` 函数式更新

例如：

```js
setCartItems((prev) => prev.map(...))
```

保证基于最新快照更新，避免并发交互下的旧值问题。

### 4. `useMemo`

```js
const books = useMemo(() => data.books, []);
```

保持书籍数组引用稳定，减少无意义重算。

### 5. 路由参数与跳转状态

- **`useParams`**：读取 `:bookId`。
- **`useLocation`**：读取 `Link state` 传递对象。

这两个能力组合实现了“参数驱动 + 状态直传 + 数据兜底”。

---

## 第五层：设计亮点与避坑建议

### 1. 为什么详情页要三层定位？

因为真实访问路径有三种：列表点击、购物车点击、地址栏直达。三层策略可覆盖全部场景并避免空白页。

### 2. 为什么 `searchByPage` 设计为对象？

避免页面间搜索词串扰：书城搜索不应影响购物车和订单页。

### 3. 为什么仍然强调不可变更新？

React 依赖引用变化判断重渲染。直接改原对象会导致 UI 不更新或状态错乱。

---

## 总结：当前项目的 React 思维模型

1. **用状态描述界面，不直接操纵 DOM**。
2. **用数据式路由描述页面关系，不写命令式页面切换**。
3. **用组件与上下文组织协作，用单向数据流保证可预测性**。
