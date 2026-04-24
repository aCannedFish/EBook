# EBook React 版本设计说明（当前实现）

本文档对应当前 `react-ebook` 代码，重点覆盖：路由组织、数据流、Ant Design 组件化改造、复用组件设计。

---

## 1. 项目结构（核心）

```text
react-ebook/
├── src/
│   ├── App.jsx                         # 路由装配层
│   ├── main.jsx                        # 应用入口（含 antd reset）
│   ├── styles.css                      # 全局样式 + AntD 适配层
│   ├── data/
│   │   ├── Data.json                   # 初始演示数据
│   │   └── appStore.js                 # 运行时内存仓库（统一读写）
│   ├── routes/
│   │   ├── Root.jsx                    # ProtectedRootRoute（共享壳层）
│   │   ├── authRouteHandlers.js        # 鉴权/分流/退出 action
│   │   └── RouteErrorBoundary.jsx      # 路由错误边界
│   ├── pages/
│   │   ├── LoginPage.jsx               # login loader/action
│   │   ├── BooksPage.jsx               # books loader/action
│   │   ├── BookDetailPage.jsx          # detail loader/action
│   │   ├── CartPage.jsx                # cart loader/action
│   │   ├── OrdersPage.jsx              # orders loader/action
│   │   └── UserPage.jsx                # user loader/action
│   └── components/
│       ├── DashboardLayout.jsx         # 侧栏+顶栏共享布局（AntD Layout）
│       ├── BookCard.jsx                # 书卡组件（封面/标题/加购）
│       ├── ResourceTable.jsx           # 复用表格壳
│       ├── StatusTag.jsx               # 复用状态标签
│       └── RowActions.jsx              # 复用行操作按钮组
└── public/assets/                      # 封面、头像、logo
```

---

## 2. 路由架构（Data Router）

### 2.1 总体策略

1. `App.jsx` 只做路由声明与拼装（`createBrowserRouter`）。
2. 每个页面的 `loader/action` 下沉到对应页面模块。
3. 受保护业务区由父路由统一鉴权与共享布局。

### 2.2 路由树

| 路径 | loader | action | element |
|---|---|---|---|
| `/`(index) | `authRedirectLoader` | - | - |
| `/login` | `loginLoader` | `loginAction` | `LoginPage` |
| `/logout` | - | `logoutAction` | - |
| 受保护父路由 | `requireAuthLoader` | - | `ProtectedRootRoute` |
| `/books` | `booksLoader` | `booksAction` | `BooksRoute` |
| `/books/:bookId` | `bookDetailLoader` | `bookDetailAction` | `BookDetailRoute` |
| `/cart` | `cartLoader` | `cartAction` | `CartRoute` |
| `/orders` | `ordersLoader` | `ordersAction` | `OrdersRoute` |
| `/user` | `userLoader` | `userAction` | `UserRoute` |
| `*` | `authRedirectLoader` | - | - |

### 2.3 共享布局与搜索

`ProtectedRootRoute` 通过 `useMatches()` 找到当前激活子路由，并读取：

- `handle.searchPlaceholder`
- `loader` 返回的 `data.search`

然后把搜索输入统一提交到当前子路由 action（`intent=set-search`，`navigate:false`）。

---

## 3. 数据层设计

### 3.1 单一读写入口

`appStore.js` 是业务数据唯一写入口：

- `loader`：`getSnapshot()` 读快照
- `action`：调用仓库函数写数据

### 3.2 状态字段

- `books`
- `user`
- `cartItems`
- `orders`
- `searchByPage`（books/detail/cart/orders/user）
- `isLoggedIn`

### 3.3 持久化

通过 localStorage 持久化：

- 登录用户名
- remember 用户名
- 用户邮箱
- 用户签名

---

## 4. 页面交互设计（现状）

### 4.1 登录

- 用户名/密码登录
- 游客直达
- remember me

### 4.2 书城

- 顶部关键词筛选（书名/作者/分类）
- 书卡支持查看详情、加入购物车

### 4.3 详情

- 优先使用 `state.book`，回退到 `loader` 查询结果
- 加购、购买、返回

### 4.4 购物车

- 全选/单选
- 数量调整（1~4）
- 移除、结算

### 4.5 订单

- 状态更新（pending/paid/cancelled）
- 再次购买

### 4.6 用户中心

- 编辑用户名/邮箱/签名
- 提交后 action 写入 `appStore` 并持久化

---

## 5. 组件化与复用

### 5.1 布局复用

- `DashboardLayout` 统一侧栏、顶栏、搜索与用户区

### 5.2 业务复用

- `BookCard`：书籍卡片展示与操作

### 5.3 列表层复用（新）

1. `ResourceTable`：封装 AntD `Table` 共有配置（无分页等）
2. `StatusTag`：统一状态颜色/文案映射
3. `RowActions`：统一行操作按钮组渲染

这三者让 `CartPage/OrdersPage` 列定义与操作逻辑明显减重复。

---

## 6. Ant Design 改造结果

项目已在主要页面采用 AntD 组件（布局、表单、表格、按钮、标签、描述列表等），但保持：

1. 路由结构不变
2. action/loader 协议不变
3. `appStore` 数据写入边界不变

即：**只替换视图层，不改变数据链路。**

---

## 7. 关键说明

1. 当前为课程作业工程，后端接口未接入。
2. 引入 AntD 后包体积上升属预期，可后续做路由级代码拆分。
3. 若继续优化，可沿用“展示层抽复用 + data router 保持稳定”的方向迭代。
