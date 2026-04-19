# SEARCH：Dashboard 复用下的搜索与筛选数据流详解

本文基于当前代码实现，解释在 **`DashboardLayout` 被父路由统一复用** 的前提下，页面搜索框输入如何传递到各页面，以及筛选如何在页面内落地。

---

## 1. 总体架构：搜索框在壳层，搜索数据在子路由

当前项目把后台壳层统一上移到受保护父路由：

- `App.jsx` 中受保护父路由 `element: <ProtectedRootRoute />`，子路由是 `books/cart/orders/user/books/:bookId`（`react-ebook/src/App.jsx`）
- `ProtectedRootRoute` 里只渲染一次 `<DashboardLayout />`，子页面走 `<Outlet />`（`react-ebook/src/routes/Root.jsx`）

这带来一个核心问题：  
**一个共享搜索输入框，如何对不同子页面使用不同搜索值/提示词/筛选逻辑？**

项目采用的答案是：

1. 各子路由在 `handle.searchPlaceholder` 声明占位词（`App.jsx`）
2. 各子路由 `loader` 返回统一字段 `search`
3. 父路由 `ProtectedRootRoute` 用 `useMatches()` 找到“当前激活且可搜索”的子路由
4. 父路由把该子路由的 `search` 和 `placeholder` 注入 `DashboardLayout`
5. 输入变化时，父路由用 `submit(..., { action: activeSearchRoute.pathname, navigate: false })` 提交到当前页 action
6. 当前页 action 收到 `intent=set-search` 后调用 `setPageSearch(pageKey, value)` 写入仓库
7. loader 重取数据，页面使用 `search` 在本地做筛选

---

## 2. 路由层如何声明“每页可搜索能力”

在 `react-ebook/src/App.jsx` 里，受保护子路由都声明了 `handle.searchPlaceholder`：

- `/books` -> `"搜索书名 / 作者 / 分类"`
- `/books/:bookId` -> `"搜索其他书籍"`
- `/cart` -> `"搜索购物车中的书籍"`
- `/orders` -> `"搜索订单号或书名"`
- `/user` -> `"搜索用户相关设置"`

这一步只定义“元信息”，真正生效在 `ProtectedRootRoute` 的 `useMatches` 解析中。

---

## 3. 父路由如何识别当前激活的可搜索页面

`react-ebook/src/routes/Root.jsx`：

```jsx
function getActiveSearchRoute(matches) {
  return [...matches]
    .reverse()
    .find(
      (match) =>
        match?.handle?.searchPlaceholder
        && match?.data
        && typeof match.data === "object"
        && "search" in match.data
    );
}
```

关键点：

1. `matches.reverse().find(...)`：从最深层匹配开始找，优先命中当前叶子页面
2. 必须有 `handle.searchPlaceholder`：说明该路由声明了搜索 UI 元信息
3. 必须有 `data.search`：说明该路由 loader 返回了搜索值

因此，登录页等无搜索语义的路由不会被误选中。

---

## 4. DashboardLayout 搜索框的受控数据来源

`ProtectedRootRoute` 对 `DashboardLayout` 传参（`react-ebook/src/routes/Root.jsx`）：

```jsx
<DashboardLayout
  searchPlaceholder={activeSearchRoute?.handle?.searchPlaceholder || "搜索"}
  searchValue={activeSearchRoute?.data?.search || ""}
  onSearchChange={(value) =>
    submit(
      { intent: "set-search", value },
      { method: "post", action: activeSearchRoute?.pathname || "/books", navigate: false }
    )
  }
>
```

`DashboardLayout` 内部输入框是标准受控组件（`react-ebook/src/components/DashboardLayout.jsx`）：

```jsx
<input
  type="search"
  placeholder={searchPlaceholder}
  value={searchValue}
  onChange={(event) => onSearchChange(event.target.value)}
/>
```

所以输入框自身不持久化状态，值完全来自“当前激活子路由 loader 的 `search`”。

---

## 5. 搜索提交是如何命中“当前页面 action”的

仍在 `ProtectedRootRoute`：

- `submit({ intent: "set-search", value }, { action: activeSearchRoute.pathname, navigate: false })`

这意味着：

1. action 目标是当前子路由路径（例如 `/orders`、`/cart`）
2. `navigate: false` 不切换 URL，只触发当前路由数据写入与刷新
3. 顶部搜索框复用一套提交逻辑，但实际由每个页面自己的 action 接收与解释

---

## 6. Action 如何把搜索词写入“按页面隔离”的仓库

所有可搜索页面 action 都支持 `intent === "set-search"` 并调用：

```js
setPageSearch(pageKey, value)
```

`react-ebook/src/data/appStore.js`：

```js
searchByPage: {
  books: "",
  detail: "",
  cart: "",
  orders: "",
  user: ""
}
```

```js
export function setPageSearch(pageKey, value) {
  state.searchByPage = {
    ...state.searchByPage,
    [pageKey]: value
  };
}
```

这不是全局单一关键词，而是 **页面隔离的搜索状态**。

---

## 7. Loader 如何把对应页面搜索词回流给 Dashboard

每个页面 loader 都返回 `search` 字段，来源是 `searchByPage.<pageKey>`：

- `booksLoader` -> `searchByPage.books`（`BooksPage.jsx`）
- `bookDetailLoader` -> `searchByPage.detail`（`BookDetailPage.jsx`）
- `cartLoader` -> `searchByPage.cart`（`CartPage.jsx`）
- `ordersLoader` -> `searchByPage.orders`（`OrdersPage.jsx`）
- `userLoader` -> `searchByPage.user`（`UserPage.jsx`）

于是 `ProtectedRootRoute` 在 `useMatches()` 里读到 `match.data.search`，再绑定回顶部输入框。  
形成闭环：**输入 -> action -> store -> loader -> matches.data -> 输入值回填**。

---

## 8. 各页面“筛选”具体怎么做（代码级）

### 8.1 书城页 `/books`

`react-ebook/src/pages/BooksPage.jsx`：

1. `const keyword = search.trim().toLowerCase()`
2. `books.filter(...)`
3. 匹配字段：`title + author + category` 拼接后 `includes(keyword)`

即：支持对书名、作者、分类做不区分大小写模糊匹配。

---

### 8.2 购物车页 `/cart`

`react-ebook/src/pages/CartPage.jsx`：

1. 先把 `cartItems` 与 `books` 关联，得到 `rows`
2. 再按 `row.book.title.toLowerCase().includes(keyword)` 过滤

注意顺序：先“业务拼装”（数量、小计、选中状态），后“显示筛选”。

---

### 8.3 订单页 `/orders`

`react-ebook/src/pages/OrdersPage.jsx`：

1. 先把订单与书籍关联成 `rows`
2. 过滤条件：`${row.id} ${row.book.title}` 包含关键词

即支持按订单号和书名查询。

---

### 8.4 详情页 `/books/:bookId` 与用户页 `/user`

二者也接入 `set-search` + `searchByPage`，但当前页面主体没有列表筛选逻辑。  
含义是：它们共享顶部搜索框状态与占位词，但不在页面主体做过滤计算（现阶段）。

---

## 9. 为什么 Dashboard 复用后仍能做到“每页搜索语义不同”

因为项目把“搜索”的职责拆成三层：

1. **共享壳层（DashboardLayout）**：只负责输入 UI
2. **父路由协调层（ProtectedRootRoute）**：负责把输入动态路由到当前页 action
3. **页面数据层（各 page loader/action）**：负责本页搜索状态存储和本页筛选规则

这种拆分使得：

- 搜索框只渲染一次，但行为按当前页面动态切换
- 页面切换后可保留各自搜索词（`searchByPage`）
- 新增页面时只需补 `handle.searchPlaceholder + loader.search + action(set-search)` 即可接入

---

## 10. 搜索链路时序（从键盘输入到列表变化）

以 `/orders` 为例：

1. 用户在 Dashboard 顶栏输入内容（`DashboardLayout`）
2. `onSearchChange` 调用父路由 `submit`
3. POST 到 `/orders`，formData：`intent=set-search`、`value=<输入值>`
4. `ordersAction` 命中 `if (intent === "set-search")`
5. `setPageSearch("orders", value)` 写入仓库
6. 路由数据刷新，`ordersLoader` 返回 `search: snapshot.searchByPage.orders`
7. `OrdersPage` 拿到新 `search`，重新计算 `rows.filter(...)`
8. `ProtectedRootRoute` 同时把新 `search` 回灌给 `DashboardLayout` 的 `searchValue`

结果：顶栏输入值与页面筛选结果保持一致，并且 URL 不变化。

---

## 11. 搜索与跳转的边界关系

当前搜索方案 **不写入 URL 查询参数**，完全存于内存仓库 `appStore`。  
因此表现为：

- 同一次应用会话内，页面间切换可保留各页面搜索词
- 刷新页面后搜索词会重置（`searchByPage` 初始为空）
- 与登录态存储策略不同（登录态存在 localStorage，搜索词不持久化）

---

## 12. 关键代码索引

- 路由搜索元信息：`react-ebook/src/App.jsx`
- 父路由搜索协调：`react-ebook/src/routes/Root.jsx`
- 共享输入框实现：`react-ebook/src/components/DashboardLayout.jsx`
- 页面搜索写入（action）：
  - `react-ebook/src/pages/BooksPage.jsx`
  - `react-ebook/src/pages/BookDetailPage.jsx`
  - `react-ebook/src/pages/CartPage.jsx`
  - `react-ebook/src/pages/OrdersPage.jsx`
  - `react-ebook/src/pages/UserPage.jsx`
- 页面搜索状态仓库：`react-ebook/src/data/appStore.js`

