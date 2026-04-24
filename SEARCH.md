# SEARCH：共享布局下的搜索数据流（当前实现）

本文档描述当前代码中“一个顶栏搜索框，驱动多个页面筛选”的实现方式。

---

## 1. 基本思路

1. 搜索框只渲染在共享壳层 `DashboardLayout`
2. 搜索状态按页面隔离存储在 `searchByPage`
3. 当前活跃子路由决定：
   - 输入框 placeholder
   - 当前显示值
   - action 提交目标路径

---

## 2. 路由层声明（`App.jsx`）

受保护子路由在 `handle.searchPlaceholder` 声明页面搜索提示词：

- `/books`
- `/books/:bookId`
- `/cart`
- `/orders`
- `/user`

---

## 3. 父路由协调（`routes/Root.jsx`）

`ProtectedRootRoute`：

1. `useMatches()` 找到当前“可搜索且 loader 返回 search”的匹配项
2. 向 `DashboardLayout` 传：
   - `searchPlaceholder`
   - `searchValue`
   - `onSearchChange`
3. `onSearchChange` 内部 `submit({ intent: "set-search", value }, { action: activePath, navigate:false })`

即输入变化不会跳页，只更新当前路由对应搜索词。

---

## 4. 搜索输入 UI（`components/DashboardLayout.jsx`）

当前顶栏使用 Ant Design `Input`：

- `value={searchValue}`
- `placeholder={searchPlaceholder}`
- `onChange` 触发 `onSearchChange`
- `prefix={<SearchOutlined />}`
- `allowClear`

这保证搜索框是受控组件，值来源于当前子路由 loader 数据。

---

## 5. action 写入（各页面）

页面 action 统一处理：

```js
if (intent === "set-search") {
  setPageSearch("<pageKey>", String(formData.get("value") || ""));
  return null;
}
```

对应关系：

- books -> `searchByPage.books`
- detail -> `searchByPage.detail`
- cart -> `searchByPage.cart`
- orders -> `searchByPage.orders`
- user -> `searchByPage.user`

---

## 6. loader 回流

各 loader 返回 `search` 字段，父路由再把该值注入共享顶栏，实现：

输入 -> action -> appStore -> loader -> 顶栏回填

---

## 7. 页面筛选规则

- `BooksPage`：筛 `title/author/category`
- `CartPage`：筛购物车行的书名
- `OrdersPage`：筛订单号 + 书名
- `BookDetailPage/UserPage`：接入搜索状态但不做列表筛选（当前版本）

---

## 8. 关键特性

1. **每页搜索词隔离**：切换页面不互相污染
2. **共享输入框复用**：只渲染一次，行为按路由动态切换
3. **URL 不变化**：使用 `navigate:false` 保持当前地址
