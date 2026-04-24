# ACTION：当前项目的 Action 机制与跳转协同

本文档对应当前 `react-ebook` 代码，说明 Data Router 中 action 如何分派、如何与页面跳转协同。

---

## 1. Action 在项目中的职责

在本项目中：

1. `loader` 读数据（来自 `appStore` 快照）
2. `action` 写数据（调用 `appStore` 写函数）
3. 组件通过 `<Form>` 或 `useSubmit()` 提交动作

统一原则：**组件不直接改全局业务状态，所有写操作都走 action。**

---

## 2. 路由与 action 对应关系

| 路径 | action | 作用 |
|---|---|---|
| `/login` | `loginAction` | 登录、游客进入 |
| `/logout` | `logoutAction` | 退出登录 |
| `/books` | `booksAction` | 搜索、加购 |
| `/books/:bookId` | `bookDetailAction` | 搜索、加购 |
| `/cart` | `cartAction` | 勾选、改数量、移除、结算 |
| `/orders` | `ordersAction` | 搜索、更新状态、再次购买 |
| `/user` | `userAction` | 搜索、更新用户资料 |

---

## 3. 分派协议：`intent`

每个 action 的第一步都相同：

```js
const formData = await request.formData();
const intent = String(formData.get("intent") || "");
```

再根据 intent 分支执行实际动作。

优点：

1. 同一路由可承载多动作
2. 参数协议统一（隐藏字段 + formData）
3. 减少无意义子路由拆分

---

## 4. 触发方式

### 4.1 声明式（`<Form method="post">`）

典型场景：登录、加购、资料提交。

### 4.2 命令式（`useSubmit`）

典型场景：搜索输入、表格行操作、勾选/数量变更。

常见参数：

- `method: "post"`
- `action: "/cart" | "/orders" ...`
- `navigate: false`（只更新数据，不改 URL）

---

## 5. 各 action 现状摘要

## 5.1 `loginAction`

- `intent=login`：校验后 `login(username, remember)`，重定向 `/books`
- `intent=guest`：游客登录，重定向 `/books`

## 5.2 `booksAction`

- `set-search`：写 `searchByPage.books`
- `add-to-cart`：`addToCart(bookId)` 并跳 `/cart`（可 `redirectTo` 覆盖）

## 5.3 `bookDetailAction`

- `set-search`：写 `searchByPage.detail`
- `add-to-cart`：优先表单 `bookId`，回退 `params.bookId`

## 5.4 `cartAction`

- `set-search`
- `toggle-select-all`
- `toggle-item`
- `update-qty`
- `remove-item`
- `checkout`（结算后跳 `/orders`）

## 5.5 `ordersAction`

- `set-search`
- `update-status`
- `buy-again`（加购后跳 `/books`）

## 5.6 `userAction`

- `set-search`
- `update-profile`（更新 `username/email/signature`，并持久化相关字段）

## 5.7 `logoutAction`

- 清理登录态后跳 `/login`

---

## 6. Action 与跳转设计

项目中有三类跳转：

1. `Link/NavLink`：纯导航
2. `throw redirect(...)`：写操作完成后的流程跳转
3. loader 内 redirect：鉴权/分流跳转

语义边界：

- 局部交互：`navigate:false` + `return null`
- 流程推进：`throw redirect(...)`

---

## 7. 与展示层复用组件的关系

当前购物车与订单已经抽出：

- `ResourceTable`
- `StatusTag`
- `RowActions`

这些组件只处理表格与按钮渲染，不触碰业务状态；实际状态更新仍由 action 分支调用 `appStore` 完成。
