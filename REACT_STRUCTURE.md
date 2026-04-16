# EBook 项目 React 架构与语法深度拆解手册

> **说明**：本文档按当前代码重写。HTML/CSS 做简明总结，重点拆解 React 的数据式路由、状态管理与组件协作。

---

## 第一部分：HTML 与 CSS 基础（简明指南）

### 1. HTML：语义化与可访问性

- 页面结构使用 `main/section/header/article/nav/aside` 等语义标签。
- 表单与交互控件通过 `label + htmlFor`、`aria-label` 提升可访问性。
- 图片统一配置 `alt` 文本，保证语义完整。

### 2. CSS：统一样式与组件化命名

- 样式集中于 `src/styles.css`，使用 `:root` 变量统一主题色、边框、阴影与字体。
- 使用 `.block__element--modifier` 风格命名（如 `book__cover`、`pill--warn`）。
- 使用 Grid/Flex 与媒体查询实现响应式布局。

---

## 第二部分：React 核心架构（深度拆解）

### 1. 入口与挂载：`main.jsx`

- 仅负责 `createRoot(...).render(<StrictMode><App /></StrictMode>)`。
- 路由容器不再在入口层创建，避免入口与路由耦合。

### 2. 路由编排：`App.jsx`

当前改为数据式路由：

- `createBrowserRouter([...])` 定义路由树。
- `RouterProvider router={router}` 注入路由能力。
- 路由层使用包装组件（如 `BooksRoute`、`BookDetailRoute`）将全局状态映射为页面 `props`。

### 3. 访问控制：`ProtectedRoute.jsx`

- 统一处理业务页鉴权：
  - 未登录：重定向 `/login`
  - 已登录：渲染子路由 `<Outlet />`

---

## 第三部分：状态与数据流（核心机制）

### 1. 单一数据源

演示数据统一来自 `src/data/Data.json`：

- `books`
- `user`
- `initialCart`
- `initialOrders`

### 2. 全局状态中心（App 层）

`App.jsx` 统一维护：

- `isLoggedIn`
- `user`
- `cartItems`
- `orders`
- `searchByPage`

并通过 `AppStateContext` 暴露给路由包装组件。

### 3. 单向数据流

- 状态与动作由 `App` 下发到页面。
- 页面通过回调上抛事件。
- `setState` 使用不可变更新，保证渲染可预测。

---

## 第四部分：页面与组件协作（行为拆解）

### 1. `BooksPage` + `BookCard`

- `BooksPage` 负责筛选与列表渲染。
- `BookCard` 负责单卡展示与操作按钮。
- “查看详情”使用 `Link state={{ book }}`，携带当前书籍对象。

### 2. `BookDetailPage`

- 读取 `useParams().bookId`。
- 读取 `useLocation().state?.book`。
- 接收路由包装层注入的 `initialBook` prop。
- 最终按优先级匹配详情数据，确保“点哪本看哪本”。

### 3. `CartPage`

- 将 `cartItems` 与 `books` 合并为 `rows`。
- 计算 `selectedRows/allSelected/subtotal` 等派生值。
- 支持全选、单选、改数量、移除、结算。

### 4. `OrdersPage`

- 通过 `statusMeta` 统一状态文案与样式。
- 根据状态渲染不同操作（取消/付款/查看/再次购买）。

### 5. `UserPage`

- 展示用户信息与快捷入口。
- 复用 `DashboardLayout` 保持界面一致。

---

## 第五部分：关键 React 语法点（答辩高频）

1. `useState`：本地状态与函数式更新。
2. `useMemo`：缓存稳定引用（如 `books`）。
3. `createContext/useContext`：跨层读取全局状态。
4. `createBrowserRouter/RouterProvider`：数据式路由核心。
5. `useParams/useLocation`：参数路由与跳转状态读取。
6. `map/filter/reduce`：不可变数据变换与派生计算。

---

## 结语

本项目当前代码结构体现了标准 React 工程化思路：以数据式路由组织页面，以全局状态统一业务动作，以组件复用保证 UI 一致性，以单向数据流保障行为可预测。
