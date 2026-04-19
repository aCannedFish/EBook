# ACTION：本项目中 Action 的处理机制与页面跳转设计

本文解释两件事：

1. 代码里“Action”如何定义、分派、执行
2. 页面跳转（导航）如何与 Action 协同设计

---

## 1. Action 在本项目里的角色

本项目使用 React Router Data Router。  
在该模式下：

- `loader` 负责读数据
- `action` 负责写数据/处理用户操作
- 组件层通过 `<Form>` 或 `useSubmit` 提交到 action

对应装配位置：`react-ebook/src/App.jsx`（每个路由绑定自己的 `loader/action`）。

---

## 2. 路由装配：哪个路径对应哪个 action

`react-ebook/src/App.jsx` 中，核心 action 映射如下：

| 路径 | action | 用途 |
| --- | --- | --- |
| `/login` | `loginAction` | 登录、游客进入 |
| `/logout` | `logoutAction` | 退出登录 |
| `/books` | `booksAction` | 搜索、加入购物车 |
| `/books/:bookId` | `bookDetailAction` | 详情页搜索、加入购物车 |
| `/cart` | `cartAction` | 勾选、改数量、移除、结算 |
| `/orders` | `ordersAction` | 搜索、更新状态、再次购买 |
| `/user` | `userAction` | 用户页搜索状态写入 |

说明：`/logout` 是“只有 action 没有页面 element”的动作路由。

---

## 3. Action 分派协议：`intent` 字段

项目通过一个统一协议在同一路由里承载多个动作：

```js
// react-ebook/src/router/routeUtils.js
export function readIntent(formData) {
  return String(formData.get("intent") || "");
}
```

每个 action 都先：

1. `const formData = await request.formData()`
2. `const intent = readIntent(formData)`
3. `if (intent === "...") { ... }`

这样避免为每个小操作拆成多个子路由，且逻辑集中。

---

## 4. Action 的触发入口：Form 与 useSubmit

### 4.1 `<Form method="post">`

示例：`BookCard.jsx` 的“加入购物车”按钮：

```jsx
<Form method="post">
  <input type="hidden" name="intent" value="add-to-cart" />
  <input type="hidden" name="bookId" value={book.id} />
  <input type="hidden" name="redirectTo" value="/cart" />
</Form>
```

默认提交到当前路由 action（在书城页即 `/books`）。

---

### 4.2 `useSubmit` 命令式提交

示例：`OrdersRoute`：

```jsx
submit(
  { intent: "update-status", orderId, status },
  { method: "post", action: "/orders", navigate: false }
)
```

适用于按钮点击、受控输入、非表单交互。

---

## 5. 各 action 具体处理逻辑（逐页面）

## 5.1 `loginAction`（`react-ebook/src/pages/LoginPage.jsx`）

- `intent === "login"`：
  - 读取用户名/密码/remember
  - 校验非空
  - `login(username, remember)`
  - `throw redirect("/books")`
- `intent === "guest"`：
  - 使用输入用户名或默认 `"同学A"`
  - `login(username, false)`
  - `throw redirect("/books")`

配合 `loginLoader`：已登录访问 `/login` 会直接重定向到 `/books`。

---

## 5.2 `booksAction`（`react-ebook/src/pages/BooksPage.jsx`）

- `set-search`：`setPageSearch("books", value)`，返回 `null`
- `add-to-cart`：
  - 读取 `bookId`
  - `addToCart(bookId)`
  - `throw redirect(readRedirectPath(formData, "/cart"))`

即书城页加入购物车后默认跳到购物车，也可通过 `redirectTo` 覆盖。

---

## 5.3 `bookDetailAction`（`react-ebook/src/pages/BookDetailPage.jsx`）

- `set-search`：`setPageSearch("detail", value)`
- `add-to-cart`：
  - `bookId` 优先取表单，否则回退 `params.bookId`
  - `addToCart(bookId)`
  - `throw redirect(readRedirectPath(formData, "/cart"))`

说明：详情页提交时兼容“表单未携带 bookId”的场景。

---

## 5.4 `cartAction`（`react-ebook/src/pages/CartPage.jsx`）

支持 6 类 intent：

1. `set-search` -> `setPageSearch("cart", value)`
2. `toggle-select-all` -> `toggleSelectAllCart(checked)`
3. `toggle-item` -> `toggleCartItem(bookId, checked)`
4. `update-qty` -> `updateCartQty(bookId, qty)`（1~4）
5. `remove-item` -> `removeCartItem(bookId)`
6. `checkout` -> `checkoutSelected(); throw redirect("/orders")`

其中 1~5 大多 `navigate: false` 原地更新，`checkout` 发生页面跳转。

---

## 5.5 `ordersAction`（`react-ebook/src/pages/OrdersPage.jsx`）

- `set-search` -> `setPageSearch("orders", value)`
- `update-status`：
  - 校验 `status` 在 `pending/paid/cancelled`
  - `updateOrderStatus(orderId, status)`
- `buy-again`：
  - `addToCart(bookId)`
  - `throw redirect(readRedirectPath(formData, "/books"))`

---

## 5.6 `userAction`（`react-ebook/src/pages/UserPage.jsx`）

- 目前只处理 `set-search` -> `setPageSearch("user", value)`
- 返回 `null`

---

## 5.7 `logoutAction`（`react-ebook/src/routes/authRouteHandlers.js`）

- 执行 `logout()`
- `throw redirect("/login")`

这是一个纯动作路由，不渲染页面组件。

---

## 6. 页面跳转设计：三条主路径

## 6.1 声明式跳转：`<Link>` / `<NavLink>`

典型位置：

- 侧边栏导航（`DashboardLayout.jsx`）
- 页面内跳转（例如“继续选购”“返回书城”）

`NavLink` 自动提供激活态样式，用于主导航。

---

## 6.2 Action 驱动跳转：`throw redirect(...)`

这类跳转绑定在“写操作完成后”：

- 登录成功 -> `/books`
- 退出登录 -> `/login`
- 加入购物车后 -> `/cart`
- 结算后 -> `/orders`
- 再次购买后 -> `/books`（可覆盖）

优点：导航与数据写入保持事务语义（先写后跳）。

---

## 6.3 路由守卫式跳转：loader 内 redirect

典型在 `authRouteHandlers.js` 与 `routeUtils.js`：

- 未登录访问受保护页 -> `/login`
- 访问 `/` 或 `*` -> 按登录态分流到 `/books` 或 `/login`
- 已登录访问 `/login` -> `/books`

即“路由入口处”先决策，不让页面进入非法状态。

---

## 7. `navigate: false` 的设计意图

大量 submit 使用：

```js
{ method: "post", action: "/xxx", navigate: false }
```

效果：

- 不改变当前 URL
- 仍触发 action 与数据刷新
- 适合搜索、勾选、改数量、状态更新这类“局部交互”

因此项目把“是否跳页”作为 action 语义的一部分：

- 局部更新：`navigate: false` + `return null`
- 流程推进：`throw redirect(...)`

---

## 8. Action 与数据仓库的边界

`react-ebook/src/data/appStore.js` 是唯一写入入口，action 只调用仓库 API，不直接改组件状态。  
例如：

- `addToCart / checkoutSelected / updateOrderStatus`
- `setPageSearch`
- `login / logout`

这样形成稳定分层：

1. 组件：只发意图（intent + 参数）
2. action：解析意图、校验参数、调用仓库
3. 仓库：实际改状态
4. loader：把新快照返回给页面

---

## 9. 页面间跳转时的数据传递策略

## 9.1 URL 参数承载可分享定位

详情页使用 `/books/:bookId`，保障链接可直达。

## 9.2 Link state 承载上下文对象

在书城/购物车/订单点进详情时都传 `state={{ book }}`（`BookCard.jsx`、`CartPage.jsx`、`OrdersPage.jsx`）。  
详情页优先使用 `location.state.book`（且校验 id 匹配），否则回退 loader 的 `detailBook`（`BookDetailPage.jsx`）。

这使“页面内跳转体验”与“地址栏直达”同时成立。

---

## 10. 关键代码索引

- 路由装配：`react-ebook/src/App.jsx`
- 鉴权与分流跳转：`react-ebook/src/routes/authRouteHandlers.js`
- 根/受保护布局与搜索提交：`react-ebook/src/routes/Root.jsx`
- action 协议工具：`react-ebook/src/router/routeUtils.js`
- 数据仓库：`react-ebook/src/data/appStore.js`
- 页面 action：
  - `react-ebook/src/pages/LoginPage.jsx`
  - `react-ebook/src/pages/BooksPage.jsx`
  - `react-ebook/src/pages/BookDetailPage.jsx`
  - `react-ebook/src/pages/CartPage.jsx`
  - `react-ebook/src/pages/OrdersPage.jsx`
  - `react-ebook/src/pages/UserPage.jsx`
- 触发 action 的组件：
  - `react-ebook/src/components/BookCard.jsx`
  - `react-ebook/src/components/DashboardLayout.jsx`

