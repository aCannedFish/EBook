# EBook 项目 GRAM（全面版）

> 使用范围：课程答辩复习手册。覆盖 `react-ebook` 中 `HTML + CSS + React` 核心语法、设计哲学、代码映射、易踩坑与规避策略。

---

## 0. 使用方法（答辩前 5 分钟速览）

1. 先看第 1、2 章，讲清“项目怎么跑起来、结构怎么分层”。
2. 再看第 3、4、5 章，回答“你具体用了哪些 HTML/CSS/React 语法”。
3. 最后看第 7、8 章，回答“为什么这样设计、常见坑怎么避免”。

---

## 1. 项目技术全景与设计目标

### 1.1 技术栈

- 构建：Vite（由 `index.html` 的 `type="module"` 脚本入口触发）
- 前端框架：React 18（`ReactDOM.createRoot`）
- 路由：`react-router-dom`
- 样式：单文件全局样式 `src/styles.css` + 语义化类名
- 数据：本地 JSON（`src/data/Data.json`）

### 1.2 业务目标

- 完成登录、书城、详情、购物车、订单、用户中心 6 个页面。
- 保证“列表 -> 详情 -> 加购 -> 结算 -> 订单流转”的闭环。
- 实现统一布局和统一状态管理，支持页面间协作。

### 1.3 React 设计哲学（本项目落地版）

- **单向数据流**：`App.jsx` 下发数据，子组件上抛事件。
- **状态上提**：跨页面共享状态集中在 `App.jsx`。
- **声明式 UI**：UI = State 的函数，不手动操纵 DOM。
- **关注点分离**：路由守卫、布局壳层、业务页面各司其职。

---

## 2. 文件结构与分层思路（工程观）

```text
react-ebook/
  index.html
  src/
	main.jsx
	App.jsx
	styles.css
	components/
	  DashboardLayout.jsx
	  Layout.jsx
	  BookCard.jsx
	  ProtectedRoute.jsx
	pages/
	  LoginPage.jsx
	  BooksPage.jsx
	  BookDetailPage.jsx
	  CartPage.jsx
	  OrdersPage.jsx
	  UserPage.jsx
	data/
	  Data.json
```

分层解释：

- **入口层**：`main.jsx`，负责挂载应用与注入路由环境。
- **编排层**：`App.jsx`，负责路由声明、全局状态、业务动作。
- **页面层**：`pages/*`，负责页面级派生数据和具体渲染。
- **构件层**：`components/*`，负责可复用 UI 与守卫逻辑。
- **资源层**：`styles.css` + `public/assets`，负责视觉与静态资源。

答辩关键词：**容器组件 + 展示组件**、**状态集中 + 行为下发**。

---

## 3. HTML 基础语法在项目中的体现

### 3.1 入口 HTML（`react-ebook/index.html`）

- `<!doctype html>`：声明标准模式。
- `<html lang="zh-CN">`：语言声明，利于可访问性与 SEO。
- `<meta charset="UTF-8">`：字符编码。
- `<meta name="viewport" ...>`：移动端适配基础。
- `<div id="root"></div>`：React 根挂载点。
- `<script type="module" src="/src/main.jsx"></script>`：Vite 模块化入口。

### 3.2 语义化标签（JSX 渲染后的 HTML 结构）

项目广泛使用：

- 结构：`main`、`section`、`article`、`aside`、`header`、`nav`、`figure`
- 表格：`table`、`thead`、`tbody`、`tr`、`th`、`td`
- 表单：`form`、`label`、`input`、`select`、`button`

设计价值：可读性更高，答辩中可说明“不是只用 `div` 堆页面”。

### 3.3 可访问性（A11y）实践

- `aria-label`：为非文本控件提供语义描述。
- `htmlFor`：绑定 `label` 与表单元素。
- `scope="col" / scope="row"`：提升表格可读性。
- 图片 `alt` 文案：封面、头像、logo 都有替代文本。

常见坑：

- 只写视觉不写语义，屏幕阅读器体验差。
- `label` 未绑定输入框，键盘与读屏可用性降低。

---

## 4. CSS 语法与样式体系（`react-ebook/src/styles.css`）

### 4.1 CSS 变量与主题化

在 `:root` 中定义：颜色、圆角、阴影、字体、焦点阴影等，例如：

- `--bg`、`--panel`、`--brand`、`--danger`
- `--radius`、`--shadow`、`--font`

设计思想：**设计令牌（Design Tokens）**，便于统一视觉与后续换肤。

### 4.2 全局重置与基础规则

- `* { box-sizing: border-box; }`
- `html, body { height: 100%; }`
- 控件字体继承：`button, input, select { font: inherit; }`

答辩可讲：这保证跨页面尺寸计算一致、字体一致。

### 4.3 工具类策略

通用工具类：`.u-hidden`、`.u-right`、`.u-sr-only`、`.u-mt-*`。

意义：

- 减少重复声明
- 提高开发效率
- `u-sr-only` 兼顾无障碍隐藏文本场景

### 4.4 组件化样式命名

项目采用近似 BEM 的命名：

- 块：`.book`、`.page`、`.panel`、`.topbar`
- 元素：`.book__title`、`.panel__header`
- 修饰：`.pill--warn`、`.tag--paid`

设计思想：**结构清晰、冲突可控、维护成本低**。

### 4.5 布局与响应式

- 大框架：`.app { display: grid; grid-template-columns: 203px 1fr; }`
- 列表网格：`.grid--books` 在不同断点切换 4/3/2/1 列。
- 媒体查询：`@media (max-width: 1040px / 820px / 520px)`。

常见坑：

- 只做桌面不做响应式，移动端布局崩溃。
- 宽度写死导致溢出，项目通过 `min(...)` 和弹性布局规避。

### 4.6 交互细节

- 按钮过渡与按压反馈：`transition` + `:active`。
- 输入框焦点可视化：`box-shadow: var(--focus)`。
- 表格行 hover 态：提升数据可读性。

---

## 5. React 语法总表（结合当前代码）

### 5.1 组件与 JSX

- 函数组件：`function Comp() { return (...) }`
- JSX 表达式：`{variable}`、`{condition ? A : B}`
- 组件嵌套：页面组件嵌入 `DashboardLayout`
- `children` 插槽：布局与内容分离

### 5.2 Props 与事件回调

- 父传子：`books`、`user`、`orders`、`search`
- 子传父（事件上抛）：`onAddToCart`、`onCheckout`、`onUpdateOrderStatus`

核心原则：**数据下行，事件上行**。

### 5.3 Hooks 使用

- `useState`：本地状态与全局状态
- `useMemo`：缓存 `books` 引用
- `useParams`：读取路由参数 `bookId`
- `useNavigate`：登录后跳转

### 5.4 路由语法

- `<Routes>` + `<Route>` 声明页面映射
- `<Navigate replace>` 做重定向
- `<Outlet>` 承载受保护子路由
- `<Link>` 和 `<NavLink>` 做导航

### 5.5 列表与条件渲染

- `array.map()` 渲染列表，必须稳定 `key`
- `if (...) return ...` 做早返回分支
- `&&` 和三元表达式做局部渲染

### 5.6 表单与受控组件

- 输入框：`value + onChange`
- 复选框：`checked + onChange`
- 下拉：`value + onChange(Number(...))`
- 表单提交：`event.preventDefault()`

### 5.7 不可变数据更新

- 数组：`map/filter` 更新
- 对象：`{ ...prev, key: value }`
- 函数式更新：`setState((prev) => next)`

---

## 6. React 设计模式在项目中的落地

### 6.1 根组件编排模式（`react-ebook/src/App.jsx`）

- 集中管理：`isLoggedIn`、`user`、`cartItems`、`orders`、`searchByPage`
- 集中动作：登录、登出、加购、结算、改状态
- 集中路由：公开路由 + 受保护路由 + 兜底

优点：业务入口单一，状态变化路径可追踪。

### 6.2 路由守卫模式（`react-ebook/src/components/ProtectedRoute.jsx`）

- 未登录自动跳回 `/login`
- 登录后通过 `<Outlet />` 放行子页面

优点：权限逻辑复用，不污染页面组件。

### 6.3 布局复用模式（`react-ebook/src/components/DashboardLayout.jsx`）

- 侧栏/顶栏/用户区统一管理
- 页面只关注自己的业务内容

优点：视觉一致，减少重复代码。

### 6.4 派生数据模式（`BooksPage`/`CartPage`/`OrdersPage`）

- 不把 `filteredBooks`、`subtotal`、`selectedRows` 再存一份 state
- 每次渲染按当前状态计算

优点：降低状态同步 Bug。

### 6.5 兼容层模式（`react-ebook/src/components/Layout.jsx`）

- `export { default } from "./DashboardLayout"`

优点：重构时不强制全量改引用，风险可控。

---

## 7. 按文件覆盖：语法点 + 设计点 + 易踩坑

### `react-ebook/src/main.jsx`

- 语法点：`createRoot`、`StrictMode`、`BrowserRouter`
- 设计点：入口最小化，只做启动与环境注入
- 易踩坑：忘记包 `BrowserRouter` 会导致路由 Hook 报错

### `react-ebook/src/App.jsx`

- 语法点：多 `useState`、`useMemo`、函数式更新
- 设计点：单一状态源、统一动作分发
- 易踩坑：
  - 直接修改 `prev` 对象会造成状态不可预测
  - 搜索词不隔离会导致跨页输入串扰

### `react-ebook/src/components/BookCard.jsx`

- 语法点：`Link`、事件处理、动态类名
- 设计点：展示组件最小化，回调交给父级
- 易踩坑：图片 `onError` 不做标记会触发无限回退循环

### `react-ebook/src/components/DashboardLayout.jsx`

- 语法点：`children`、`NavLink` 动态 class、受控搜索框
- 设计点：壳层复用
- 易踩坑：把页面业务逻辑塞进布局会导致布局“变重”

### `react-ebook/src/components/ProtectedRoute.jsx`

- 语法点：`Navigate`、`Outlet`
- 设计点：权限边界前置到路由层
- 易踩坑：重定向不加 `replace` 可能污染浏览器回退栈

### `react-ebook/src/pages/LoginPage.jsx`

- 语法点：受控表单、`useNavigate`
- 设计点：局部状态自管，全局登录上抛
- 易踩坑：未 `trim` 可能把纯空格视为合法输入

### `react-ebook/src/pages/BooksPage.jsx`

- 语法点：`filter` + `map` 链式处理
- 设计点：派生列表，不冗余存储
- 易踩坑：`key` 不稳定会导致渲染异常或状态错位

### `react-ebook/src/pages/BookDetailPage.jsx`

- 语法点：`useParams` + `find`
- 设计点：无效参数兜底分支
- 易踩坑：假设 `book` 一定存在会引发运行时报错

### `react-ebook/src/pages/CartPage.jsx`

- 语法点：`map/find/filter/reduce` 综合应用
- 设计点：原始购物车数据 + 视图拼装数据分离
- 易踩坑：
  - 结算金额和结算条目不一致（通过 `selectedRows` 统一来源规避）
  - 数量字符串不转数值会造成计算异常

### `react-ebook/src/pages/OrdersPage.jsx`

- 语法点：状态映射常量、条件渲染分支
- 设计点：展示状态与业务状态分离（`statusMeta`）
- 易踩坑：在 JSX 里散写状态文案，后续维护易漏改

### `react-ebook/src/pages/UserPage.jsx`

- 语法点：表格语义结构、链接导航
- 设计点：轻页面 + 快捷入口
- 易踩坑：用户信息展示字段和 `user` 数据结构不一致时要做兜底

---

## 8. 课程答辩高频问题与标准答法

### Q1：为什么把状态都放在 `App.jsx`？

答：因为 `cart/orders/user/login` 是多页面共享数据，放在根组件可避免兄弟组件互相同步，符合状态上提和单向数据流。

### Q2：为什么 `CartPage` 不再开一个 `subtotal` state？

答：`subtotal` 是可由 `selectedRows` 计算得到的派生值，直接 `reduce` 计算更可靠，避免双份状态不一致。

### Q3：为什么用 `ProtectedRoute` 而不是每页都判断登录？

答：权限逻辑是横切关注点，应该统一在路由层复用，实现集中管理和降低重复。

### Q4：CSS 为什么用全局文件而不是每页内联？

答：全局样式能统一设计令牌、命名规范和响应式策略，避免样式碎片化；也符合作业“禁止内联样式”的规范。

### Q5：这个项目体现了哪些 React 风格？

答：函数组件、Hooks、声明式路由、状态上提、不可变更新、派生数据、组件复用、可访问性意识。

---

## 9. 易踩坑清单（写代码前先看）

1. **直接改 state 引用**：必须用不可变更新。
2. **列表 key 用索引**：应使用业务唯一键（如 `book.id`、`order.id`）。
3. **受控/非受控混用**：输入组件要么受控要么非受控，不要来回切。
4. **忘记类型转换**：`select` 取值默认字符串，数量/金额计算前需 `Number(...)`。
5. **路由参数未兜底**：`find` 失败必须有“未找到”分支。
6. **图片回退死循环**：`onError` 回退要带一次性标记。
7. **多页面共用同一个搜索 state**：会导致切页串值，应按页面隔离。
8. **权限逻辑分散在页面**：应放到 `ProtectedRoute`。
9. **响应式未覆盖**：至少验证 1040/820/520 三个断点。
10. **只做视觉不做语义**：保证 `aria-label`、`label`、`scope`、`alt` 完整。

---

## 10. 项目复习检查表（自测）

- [ ] 我能画出 `main.jsx -> App.jsx -> pages/components` 的数据流。
- [ ] 我能解释为什么 `App.jsx` 是状态中心。
- [ ] 我能讲清 `ProtectedRoute` 的 `Navigate + Outlet`。
- [ ] 我能写出一个受控表单（`value + onChange + preventDefault`）。
- [ ] 我能解释 `map/filter/reduce` 在购物车和订单中的作用。
- [ ] 我能说出 `styles.css` 的变量体系、命名规范和响应式断点。
- [ ] 我能举例至少 5 个“易踩坑 + 规避方式”。

---

## 11. 一句话结论（答辩收尾）

这个项目的核心不是“把页面搬到 React”，而是通过 **状态上提 + 路由守卫 + 布局复用 + 派生数据 + 规范化 CSS**，把页面升级为一个结构清晰、可维护、可扩展的前端应用。

