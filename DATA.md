# DATA.md

本文结合当前 `react-ebook` 代码，说明网页如何与 `Data.json` 交互，以及运行时数据状态如何创建、维护和交互。

## 1. 数据源与总体架构

### 1.1 静态数据源

项目的数据初始来源是：

- `react-ebook/src/data/Data.json`

其中包含四类初始数据：

1. `books`：书籍列表（封面、价格、作者、分类等）
2. `user`：用户基础信息（`username/email/level/signature`）
3. `initialCart`：初始购物车条目
4. `initialOrders`：初始订单条目

### 1.2 运行时数据中枢

项目把“运行时可变数据”统一放在：

- `react-ebook/src/data/appStore.js`

该文件是数据路由模式下的**唯一业务写入入口**：

- **loader** 从 `appStore` 读取快照（`getSnapshot()`）
- **action** 调用 `appStore` 的写函数更新状态
- 页面组件只做展示与触发提交，不直接改全局状态

这使数据流清晰为：`组件事件 -> action -> appStore -> loader 重新取数 -> 组件刷新`。

---

## 2. 网页启动时：状态如何创建

启动时在 `appStore.js` 完成 `state` 初始化：

1. 读取 `Data.json`：`import data from "./Data.json"`
2. 读取 localStorage（若在浏览器环境）：
   - `ebook-auth-username`（登录用户名）
   - `ebook-remember-username`（登录页默认用户名）
   - `ebook-user-email`（用户邮箱持久化）
   - `ebook-user-signature`（用户签名持久化）
3. 生成内存状态 `state`：
   - `books`：直接来自 `data.books`
   - `user`：以 `data.user` 为基准，再叠加持久化字段
   - `cartItems`：从 `data.initialCart` 拷贝
   - `orders`：从 `data.initialOrders` 拷贝
   - `searchByPage`：各页面独立搜索词（`books/detail/cart/orders/user`）
   - `isLoggedIn`：由是否存在 `ebook-auth-username` 决定

> 结论：`Data.json` 是初始化基线，localStorage 是跨刷新补丁，`state` 是当前运行会话的真实数据。

---

## 3. 路由层如何读取与写入数据（Data Router）

路由装配在 `react-ebook/src/App.jsx`，采用 `createBrowserRouter`。

### 3.1 读取（loader）

每个页面 loader 都先做鉴权（受保护页）再返回页面所需数据：

- `booksLoader`：`books + searchByPage.books`
- `bookDetailLoader`：`detailBook + searchByPage.detail`
- `cartLoader`：`books + cartItems + searchByPage.cart`
- `ordersLoader`：`books + orders + searchByPage.orders`
- `userLoader`：`user + username + searchByPage.user`

这些 loader 的数据由 `useLoaderData()` 进入页面组件。

### 3.2 写入（action）

所有写操作通过 `<Form method="post">` 或 `useSubmit()` 进入 action。  
每个 action 用 `intent` 分派动作（`String(formData.get("intent") || "")`）：

- `booksAction`
  - `set-search`
  - `add-to-cart`
- `bookDetailAction`
  - `set-search`
  - `add-to-cart`
- `cartAction`
  - `set-search`
  - `toggle-select-all`
  - `toggle-item`
  - `update-qty`
  - `remove-item`
  - `checkout`
- `ordersAction`
  - `set-search`
  - `update-status`
  - `buy-again`
- `userAction`
  - `set-search`
  - `update-profile`
- `loginAction`
  - `login`
  - `guest`
- `logoutAction`
  - 退出并重定向登录页

action 内部真正改状态的都是 `appStore` 导出函数（例如 `addToCart/updateCartQty/updateOrderStatus/updateUserProfile`）。

说明：购物车与订单页面虽已抽出 `ResourceTable/StatusTag/RowActions` 复用组件，但这些组件只负责 UI 渲染，数据写入依旧通过 action -> appStore。

---

## 4. 运行中：状态如何维护

## 4.1 全局状态对象（appStore）

`state` 字段职责如下：

- `books`：书籍主数据（当前版本只读）
- `user`：当前用户资料（可编辑用户名/邮箱/签名）
- `cartItems`：购物车项（`bookId/qty/selected`）
- `orders`：订单项（`id/status/bookId/qty/unitPrice`）
- `searchByPage`：分页面搜索状态
- `isLoggedIn`：登录态

## 4.2 防御性快照

`getSnapshot()` 返回对象拷贝，而不是暴露 `state` 原引用。  
这样外部模块不能绕过 action 直接改仓库，避免数据竞争和隐式副作用。

## 4.3 页面间共享搜索状态

`searchByPage` 由 `setPageSearch(pageKey, value)` 更新。  
在 `ProtectedRootRoute` 中通过 `useMatches()` 找当前激活路由，再把顶栏搜索提交到对应页面 action（`intent=set-search`）。  
因此每个页面保留自己的搜索词，切页后互不覆盖。

---

## 5. 刷新后的持久化与恢复

当前持久化策略是“部分业务状态持久化”：

1. **登录相关**
   - `login()` 写入 `ebook-auth-username`
   - `logout()` 清理 `ebook-auth-username`
   - `remember me` 写入 `ebook-remember-username`
2. **用户资料**
   - `updateUserProfile()` 写入：
     - `ebook-user-email`
     - `ebook-user-signature`
   - 若已登录，也同步更新 `ebook-auth-username`
   - 若已存在记住用户名，也同步更新 `ebook-remember-username`

因此刷新后可恢复：

- 登录用户名
- 邮箱
- 个性签名

而购物车与订单当前是内存态（刷新后回到 `Data.json` 初始值）。

---

## 6. 页面之间的数据关联怎么实现

## 6.1 列表页 -> 详情页

通过两条链路保证“点哪本看哪本”：

1. URL 参数：`/books/:bookId`
2. Link state：`state={{ book }}`

详情页优先使用 `location.state.book`（且校验 id 匹配），否则回退到 loader 的 `detailBook`。  
这样既支持页面间携带对象，又支持地址栏直达刷新。

## 6.2 购物车/订单 -> 详情页

购物车和订单中的书名链接也携带 `state.book`，详情页使用同一套优先级解析逻辑，保证跨页面跳转时数据一致。

---

## 7. 关键交互流程（代码级）

### 7.1 加入购物车

1. 用户在列表或详情点击“加入购物车”
2. `<Form>` 提交 `intent=add-to-cart`
3. 对应 action 调 `addToCart(bookId)`
4. action `redirect("/cart")`
5. `cartLoader` 用最新快照渲染购物车

### 7.2 购物车结算

1. 点击“结算”提交 `intent=checkout`
2. `checkoutSelected()` 将已选条目转为订单并从购物车移除
3. `redirect("/orders")`
4. `ordersLoader` 读取新订单列表渲染

### 7.3 订单状态变更

1. 点击“付款/取消”提交 `intent=update-status`
2. `updateOrderStatus(orderId, status)` 更新订单状态
3. action 返回 `null`（不跳转），当前页按新快照刷新

### 7.4 用户资料更新

1. 用户页表单提交 `intent=update-profile`
2. `userAction` 读取并校验 `username/email/signature`
3. `updateUserProfile()` 更新 `state.user` 并写入 localStorage
4. action 返回成功消息，页面显示“个人信息已更新”
5. 刷新后初始化阶段从 localStorage 恢复资料

---

## 8. 总结

当前项目的数据交互模型可以概括为：

- **Data.json 提供初始数据**
- **appStore 承担运行时状态与写入规则**
- **loader/action 构成页面与状态之间的标准数据路由通道**
- **localStorage 负责登录与用户资料的跨刷新恢复**

这套设计保证了：页面逻辑清晰、写操作集中、路由驱动数据刷新、跨页面数据关联可追踪。
