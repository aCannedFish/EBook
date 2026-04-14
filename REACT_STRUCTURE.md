# EBook 电子书城项目：React 架构与语法深度拆解手册

> **前言**：本手册旨在通过“剥洋葱”的方式，从文件结构到代码行，逐层剖析本项目是如何利用 React 构建一个动态、可交互的 Web 应用的。

---

## 第一层：宏观架构 —— 项目是怎么“跑”起来的？

### 1. 入口文件：`main.jsx`（点火系统）
这是 React 世界的起点。
- **`createRoot`**：React 18 的新 API。它在 HTML 的 `id="root"` 节点上创建了一个“画布”。
- **`<BrowserRouter>`**：路由的“基站”。它利用 HTML5 History API 监听 URL 的变化，让组件能够感知当前在哪个页面。
- **`<StrictMode>`**：开发环境的“纠错员”。它会故意执行两次渲染，帮我们发现不规范的代码（比如副作用没清理）。

### 2. 根组件：`App.jsx`（中央控制塔）
这是整个项目的核心，它承担了三个最重要的角色：
- **状态中心 (State Center)**：管理 `isLoggedIn`、`cartItems`、`orders` 等所有全局数据。
- **逻辑分发器 (Action Dispatcher)**：定义了所有的业务函数（如 `addToCart`、`checkoutSelected`）。
- **路由声明 (Route Declaration)**：决定了哪个 URL 对应哪个页面。

---

## 第二层：模块化设计 —— 为什么要这样分文件？

我们采用了 **“容器组件 (Container) + 展示组件 (Presentational)”** 的模式。

### 1. 布局抽象：`DashboardLayout.jsx`
- **设计意图**：实现“一次编写，到处复用”。
- **核心语法：`children` 插槽**
    - 在组件标签中间写的内容，都会被 React 自动收集到 `props.children` 里。
    - **作用**：让侧栏、顶栏这种重复的 UI 逻辑与具体页面内容解耦。

### 2. 权限隔离：`ProtectedRoute.jsx`
- **高阶组件 (HOC) 思想**：它不展示具体业务，只负责逻辑拦截。
- **核心语法：`<Outlet />` 和 `<Navigate />`**
    - `Outlet`：占位符，如果验证通过，子路由的内容就会渲染在这里。
    - `Navigate`：自动跳转，类似于 `window.location.href` 但不会引起页面刷新。

### 3. 展示单元：`BookCard.jsx`
- **单一职责**：它只负责把传进来的 `book` 对象画出来，不关心数据是怎么来的。这样即使以后书城变成“推荐书单”，这个卡片依然能用。

---

## 第三层：函数逻辑 —— 交互是如何流动的？

在本项目中，交互遵循 **“数据下行 (Props Down)，行为上行 (Events Up)”** 的闭环逻辑。

### 1. “加购”交互全追踪
1.  **子组件触发**：用户在 `BookCard` 点“加入购物车”。
2.  **回调冒泡**：`BookCard` 调用 `onAddToCart(id)`。这个函数是通过 Props 从 `App.jsx` 一路传下来的。
3.  **状态更新**：`App.jsx` 中的 `addToCart` 函数执行。
    - 它使用 **不可变更新**：`setCartItems(prev => [...prev, newItem])`。
4.  **UI 响应**：由于 `cartItems` 变了，React 自动通知所有用到这个数据的组件（如购物车页面、导航栏角标）重新画图。

### 2. 派生数据 (Derived State) 的妙用 —— `CartPage.jsx`
**初学者的错**：在 `CartPage` 再开一个 `total` 的 State。
**本项目的方案**：直接在渲染函数里算。
```javascript
const subtotal = selectedRows.reduce((sum, row) => sum + row.subtotal, 0);
```
- **逻辑分析**：`subtotal` 是依赖于 `cartItems` 的。只要 `cartItems` 变了，React 重新执行渲染函数，`subtotal` 就会自动重算。这样保证了金额永远是准确的，不会出现“数据不同步”的 Bug。

---

## 第四层：语法百科全书 —— 这些代码背后是什么？

### 1. `useState`：不仅仅是变量
- **语法**：`const [state, setState] = useState(initialValue)`
- **深度理解**：`state` 是只读的镜像，`setState` 是请求更新的指令。
- **本项目技巧**：**函数式更新**。
    - `setOrders(prev => [...newOrders, ...prev])`
    - **为什么？**：如果多次连续点击，`prev` 能保证你拿到的是内存里那一刻最新的值，而不是旧的快照。

### 2. `useMemo`：缓存的智慧
- **语法**：`useMemo(() => computeValue, [dependencies])`
- **在本项目中**：我们用它包裹 `Data.json` 的导入。
- **意义**：防止每次组件刷新都去重新解析 JSON。只有当依赖项（这里是空数组 `[]`）变化时才重算，极大地节省了 CPU。

### 3. `useParams`：URL 里的秘密
- **语法**：从 `react-router-dom` 导入。
- **在本项目中**：`/books/:bookId`。
- **逻辑**：当用户访问 `/books/1` 时，`useParams()` 会返回 `{ bookId: "1" }`。我们据此在数组里 `find` 出对应的书。

### 4. `NavLink`：聪明的链接
- **区别**：比普通的 `Link` 多了一个“感知”功能。
- **语法**：`className={({ isActive }) => ... }`
- **逻辑**：它会自动对比当前的浏览器地址和自己的 `to` 属性，如果匹配，就自动给你传一个 `isActive: true`，让你能给侧栏加上高亮颜色。

### 5. JSX 中的逻辑判断
- **短路评价 (`&&`)**：`{ orders.length === 0 && <p>暂无订单</p> }`。
    - 底层：如果左边为假，右边就不执行。
- **三元运算符 (`? :`)**：`{ isLoggedIn ? <Home /> : <Login /> }`。
    - 底层：React 根据条件直接选择挂载哪棵 DOM 树。

---

## 第五层：设计亮点与避坑建议

### 1. 为什么用 `key={book.id}` 而不是 `key={index}`？
- **深度解析**：React 内部有一张“虚拟 DOM 表”。如果用索引，你删掉第一项，后面所有项的索引都会变，React 会以为所有项都变了，导致昂贵的重绘甚至表单输入丢失。用 `id` 就像用身份证号，即便顺序乱了，React 也能一眼认出“它还是它”。

### 2. 为什么搜索词 `searchByPage` 是个对象？
- **设计亮点**：我们在 `App.jsx` 定义了 `{ books: "", cart: "", ... }`。
- **初学者的坑**：如果只定义一个 `search` 字符串，你在书城搜了“React”，切换到购物车时，购物车也会被过滤，这不符合逻辑。
- **解决方案**：按页面键值对隔离存储，互不干扰。

### 3. 严格模式下的“双重渲染”
- **现象**：你会发现 `console.log` 打印了两次。
- **解释**：这是 React 在帮你检查函数的“纯度”。如果你的函数有副作用（比如直接修改全局变量），两次运行的结果会不一致，从而提醒你代码有问题。

---

## 总结：React 的思维模型

在本项目中，我们不是在“操纵网页元素”，而是在 **“描述状态”**。
1.  **定义数据 (State)**：用户是谁？购物车里有什么？
2.  **编写模板 (JSX)**：数据长什么样时，页面应该长什么样？
3.  **处理交互 (Event)**：点击后，数据该怎么变？

**剩下的事，全部交给 React 去完成。**
