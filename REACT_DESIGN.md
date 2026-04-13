# React 设计说明

## 1. 实现目标

本次将作业 1 的静态页面重构为 React + React Router 工程，并保持原有功能范围一致：

- 登录页（`/login`）
- 书城列表页（`/books`）
- 书籍详情页（`/books/:bookId`）
- 购物车页（`/cart`）
- 订单页（`/orders`）
- 用户信息页（`/user`）

同时满足：

1. 列表页与详情页可跳转。
2. 点击哪本书就展示哪本详情（Prop + State + 路由参数）。
3. 统一从前端数据文件读取数据。
4. 使用函数组件进行构件化封装。

---

## 2. 工程结构

```text
react-ebook/
  index.html
  package.json
  src/
    App.jsx
    main.jsx
    styles.css
    data/
      Data.json
    components/
      DashboardLayout.jsx
      BookCard.jsx
      ProtectedRoute.jsx
    pages/
      LoginPage.jsx
      BooksPage.jsx
      BookDetailPage.jsx
      CartPage.jsx
      OrdersPage.jsx
      UserPage.jsx
  public/
    assets/
      logo.svg
      avatar.svg
```

组织原则：

- `pages/` 负责页面级功能。
- `components/` 负责复用构件。
- `data/Data.json` 负责演示数据。
- `App.jsx` 负责路由、状态提升、页面协作。

---

## 3. 路由设计

`App.jsx` 中采用 React Router 配置：

- `/`：按登录状态重定向到 `/login` 或 `/books`
- `/login`：登录页
- `/books`：书籍列表页
- `/books/:bookId`：详情页
- `/cart`：购物车页
- `/orders`：订单页
- `/user`：用户页
- `*`：兜底重定向

并使用 `ProtectedRoute` 保护业务页，未登录访问业务路由会跳回登录页。

---

## 4. 数据与状态设计（Prop + State）

### 4.1 数据文件

`Data.json` 中集中维护：

- `books`（8 本书，含价格、分类、ISBN、描述等）
- `user`（用户信息）
- `initialCart`（默认购物车）
- `initialOrders`（默认订单）

### 4.2 状态提升

在 `App.jsx` 管理全局状态：

- `isLoggedIn`
- `user`
- `selectedBookId`
- `cartItems`
- `orders`
- `searchByPage`

### 4.3 Prop 传递示例

- `App.jsx -> BooksPage -> BookCard`：书籍列表与点击行为。
- `App.jsx -> BookDetailPage`：通过 `selectedBookId` 与 `bookId` 参数关联详情。
- `App.jsx -> CartPage/OrdersPage/UserPage`：传入数据和操作函数（增删改查）。

这保证了“页面跳转时数据保持关联”的作业要求。

---

## 5. 构件化设计体现

### 5.1 页面构件

- `LoginPage`
- `BooksPage`
- `BookDetailPage`
- `CartPage`
- `OrdersPage`
- `UserPage`

### 5.2 复用构件

- `DashboardLayout`：复用侧栏 + 顶栏 + 头像 + 搜索框。
- `BookCard`：复用书籍卡片。
- `ProtectedRoute`：路由权限保护。

### 5.3 单向数据流

页面不直接改全局数据，统一由 `App.jsx` 的操作函数修改，保证逻辑集中、可维护。

---

## 6. 与原 HTML 页面一致性说明

React 版本对齐了原页面功能：

1. 侧栏导航结构一致（书城/购物车/订单/用户/退出）。
2. 顶栏搜索与头像展示一致。
3. 列表页可“查看详情 / 加入购物车”。
4. 详情页展示分类、价格、ISBN、简介及购买入口。
5. 购物车支持全选、数量修改、小计与结算。
6. 订单页展示状态标签，并支持取消/付款/再次购买操作。
7. 用户页展示基本资料与快捷入口。

---

## 7. 运行方式

在 `react-ebook` 目录下执行：

```bash
npm install
npm run dev
```

验证建议：

1. `/login` 登录后进入 `/books`。
2. 在 `/books` 点击“查看详情”，检查详情是否匹配。
3. 在详情页/列表页加入购物车，检查 `/cart` 数量与金额变化。
4. 在 `/cart` 结算后检查 `/orders` 新增待付款订单。
5. 在 `/user` 查看用户信息与快捷入口。

---

## 8. 迭代 1 可扩展方向

本工程已作为迭代 1 的基础：

- 可以接入后端 API 替换 `Data.json`。
- 可以引入 Context/Redux 管理更复杂状态。
- 可以补充订单详情、支付流程、用户编辑等业务功能。
