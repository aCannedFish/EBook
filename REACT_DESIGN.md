# React 交互设计说明

## 1. 目标与设计定位

本项目将静态电商页面升级为 `React + React Router` 单页应用，在保持原业务范围不变的前提下，引入可维护的组件化与状态管理结构。

覆盖页面：

- 登录页：`/login`
- 书城页：`/books`
- 详情页：`/books/:bookId`
- 购物车页：`/cart`
- 订单页：`/orders`
- 用户页：`/user`

设计目标：

1. 页面跳转由路由统一管理，地址可直达。
2. 业务状态集中在根组件，页面通过 `props` 和回调协作。
3. 列表、详情、购物车、订单等页面共享同一份数据源。
4. 复用布局与构件，避免重复实现侧栏、顶栏和卡片 UI。

> 设计注释：该项目采用“教学型工程”风格，逻辑尽量显式，注释解释每一步数据变化，便于学习和二次迭代。

---

## 2. 工程结构与职责分层（详细）

```text
react-ebook/
  index.html                    # Vite 挂载容器
  package.json                  # 依赖与脚本
  src/
    main.jsx                    # 应用入口：挂载根组件 + BrowserRouter
    App.jsx                     # 应用编排层：路由、全局状态、业务动作
    styles.css                  # 全局样式
    data/
      Data.json                 # 演示数据源（书籍、用户、购物车、订单）
    components/
      DashboardLayout.jsx       # 后台壳层布局（侧栏+顶栏+用户区）
      Layout.jsx                # 兼容转发层（导出 DashboardLayout）
      BookCard.jsx              # 书籍卡片复用构件
      ProtectedRoute.jsx        # 路由守卫构件
    pages/
      LoginPage.jsx             # 登录与游客进入
      BooksPage.jsx             # 书籍列表与筛选
      BookDetailPage.jsx        # 单书详情展示
      CartPage.jsx              # 购物车选择、数量、结算
      OrdersPage.jsx            # 订单查询与状态流转
      UserPage.jsx              # 用户资料与快捷入口
  public/
    assets/                     # 静态资源（logo、头像、封面）
```

分层原则：

- **`App.jsx` = 容器层（Container）**：维护共享状态和跨页面行为。
- **`pages/*` = 页面层（Page）**：组织页面业务和派生数据，不持有全局状态。
- **`components/*` = 展示/复用层（Presentational）**：提供可复用 UI 外壳与局部交互。
- **`data/Data.json` = 本地数据源**：演示阶段替代后端 API。

> 设计注释：该分层符合 React 常见“容器-展示分离”思想，便于后续将 `Data.json` 替换为接口调用。

---

## 3. 路由与访问控制设计

路由由 `App.jsx` 统一声明：

- `/`：根据 `isLoggedIn` 重定向到 `/books` 或 `/login`
- `/login`：公开访问
- `/books`、`/books/:bookId`、`/cart`、`/orders`、`/user`：受保护访问
- `*`：兜底重定向

`ProtectedRoute.jsx` 设计：

- 接收 `isLoggedIn`。
- 未登录：返回 `<Navigate to="/login" replace />`。
- 已登录：返回 `<Outlet />`，继续渲染嵌套路由。

React 风格体现：

- **声明式路由**：页面结构由 `<Routes>/<Route>` 描述，而非命令式切换。
- **守卫可复用**：权限判断不散落在每个页面，集中在单一构件。

---

## 4. 数据模型与状态管理设计

### 4.1 数据来源

`src/data/Data.json` 提供四类初始数据：

- `books`：图书元信息（价格、分类、ISBN、库存文案等）
- `user`：用户基本信息
- `initialCart`：初始购物车条目
- `initialOrders`：初始订单列表

### 4.2 全局状态（`App.jsx`）

当前实现中的共享状态：

- `isLoggedIn`：登录态
- `user`：当前用户
- `cartItems`：购物车条目（`bookId/qty/selected`）
- `orders`：订单列表
- `searchByPage`：分页面搜索词（`books/detail/cart/orders/user`）

> 设计注释：本实现使用“按页面隔离搜索词”的策略，避免切换页面时输入互相覆盖，提升交互连贯性。

### 4.3 关键业务动作（由 `App.jsx` 下发）

- `handleLogin / handleLogout`：登录态切换与用户名更新
- `addToCart`：同书籍合并数量，数量上限控制
- `toggleSelectAllCart / toggleCartItem`：购物车选择态管理
- `updateCartQty / removeCartItem`：购物车编辑
- `checkoutSelected`：将勾选购物车条目转换为订单并移出购物车
- `updateOrderStatus`：订单状态流转（待付款/已付款/已取消）

React 风格体现：

- **状态上提（State Lifting）**：共享状态集中管理。
- **单向数据流（Top-Down Data Flow）**：状态下发，事件上抛。
- **不可变更新（Immutability）**：通过 `map/filter/reduce` 和扩展运算符更新状态。

---

## 5. 页面设计思路（逐页）

### 5.1 `LoginPage.jsx`

设计要点：

- 采用受控表单（`username/password/remember` 均由 `useState` 管理）。
- 提交时 `preventDefault`，先做最小校验再调用 `onLogin`。
- 使用 `useNavigate` 进行登录后跳转。
- 提供游客入口（默认昵称兜底），降低试用门槛。

React 风格：局部临时状态放页面内部，全局登录状态交给父层处理。

### 5.2 `BooksPage.jsx`

设计要点：

- 根据搜索词做本地过滤（标题/作者/分类）。
- 通过 `BookCard` 渲染列表，避免列表项 UI 重复。
- 页面只负责“筛选+渲染”，加购动作委托给 `onAddToCart`。

React 风格：派生数据优先，不额外存储 `filteredBooks` 到 state。

### 5.3 `BookDetailPage.jsx`

设计要点：

- `useParams` 获取 `bookId`，在 `books` 中查找目标书。
- 设计“未找到”分支，确保无效链接也有可理解反馈。
- 展示完整元信息并提供多条操作路径（加购/去订单/回书城）。
- 图片加载失败时使用兜底图，且用 `dataset` 防止错误循环。

React 风格：根据路由参数驱动 UI，避免额外“当前书籍”全局状态。

### 5.4 `CartPage.jsx`

设计要点：

- 将 `cartItems` 与 `books` 合并为渲染行 `rows`。
- 派生 `selectedRows`、`allSelected`、`subtotal` 作为视图计算值。
- 支持全选、单选、数量变更、移除、结算。
- 结算时传递当前选中行给上层，保证金额计算和提交数据一致。

React 风格：复杂列表页采用“原始状态 + 计算视图”模式，可维护性更高。

### 5.5 `OrdersPage.jsx`

设计要点：

- 通过 `statusMeta` 将状态值与样式/文案集中映射。
- 订单行补齐书籍信息并计算总价后再渲染。
- 根据状态进行操作分支（取消/付款/查看/再次购买）。

React 风格：以常量配置替代散落条件，降低 JSX 复杂度。

### 5.6 `UserPage.jsx`

设计要点：

- 聚焦用户信息展示与快捷业务入口。
- 延续统一 `DashboardLayout`，保证页面体验一致。

React 风格：轻页面、强复用，避免重复搭建壳层结构。

---

## 6. 构件设计思路（components）

### 6.1 `DashboardLayout.jsx`

- 角色：全站业务页壳层。
- 职责：侧栏导航、顶栏搜索、用户区、退出按钮。
- 设计：通过 `children` 插槽承载各页面主体。
- 风格：布局与业务解耦，提高复用率与一致性。

### 6.2 `BookCard.jsx`

- 角色：书籍列表最小展示单元。
- 职责：展示封面/标题/作者/价格/库存状态，提供详情和加购入口。
- 设计：无全局状态，事件由父组件注入回调。
- 风格：小而纯的展示构件，便于测试与复用。

### 6.3 `ProtectedRoute.jsx`

- 角色：访问控制边界。
- 职责：统一判定登录态，决定渲染子路由或重定向。
- 风格：把“权限规则”从页面中抽离，实现路由层关注点分离。

### 6.4 `Layout.jsx`

- 角色：兼容层。
- 职责：转发导出 `DashboardLayout`，避免旧引用失效。
- 风格：重构期保守演进，降低改名带来的联动风险。

---

## 7. 项目采用的 React 风格总结

1. **函数组件优先**：全部页面和构件都使用函数组件。
2. **Hooks 驱动状态与路由**：`useState/useMemo/useParams/useNavigate`。
3. **声明式 UI**：页面随状态变化自动重渲染。
4. **状态上提 + 回调下传**：保证数据单向流动。
5. **派生数据而非冗余存储**：筛选结果、金额统计由计算得到。
6. **不可变更新**：避免直接修改原数组/对象。
7. **构件化与壳层复用**：业务页共享同一布局与导航体验。
8. **可访问性意识**：大量使用 `aria-label`、`htmlFor`、`scope`、`alt`。

---

## 8. 与原静态页面的功能对齐

已实现与原页面一致的核心体验：

1. 统一侧栏导航与顶栏结构。
2. 列表页可跳详情，详情可继续操作。
3. 加购后在购物车可见且可编辑。
4. 购物车结算生成订单，订单可执行状态操作。
5. 用户页展示基础资料并提供业务跳转。

---

## 9. 可扩展方向（迭代建议）

- 用真实 API 替换 `Data.json`，并加入请求态/错误态。
- 将登录态与用户信息持久化（如 `localStorage` + 初始化恢复）。
- 引入 Context 或 Redux Toolkit 管理更复杂跨页面状态。
- 为购物车与订单增加单元测试和交互测试。
- 拆分 `App.jsx` 的业务动作为自定义 Hook，降低根组件体积。
