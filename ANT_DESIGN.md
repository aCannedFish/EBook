# ANT_DESIGN.md

本文档说明本次迭代中 `react-ebook` 项目对 Ant Design（AntD）组件的使用方式、对应功能和代码落点。

## 1. 接入方式

### 1.1 依赖安装

在 `react-ebook/package.json` 中新增：

- `antd`

### 1.2 全局样式引入

在 `react-ebook/src/main.jsx` 中引入：

```jsx
import "antd/dist/reset.css";
```

用途：重置 AntD 默认样式基线，避免与项目原有 CSS 产生不可控冲突。

---

## 2. 总体设计原则

本次重构遵循两条原则：

1. **只替换视图层组件**  
   保留 Data Router 的 `loader/action` 数据流、`appStore` 状态读写规则不变。

2. **交互语义不变**  
   表单提交、页面跳转、购物车与订单操作仍使用原有 action 协议（`intent` 分派）。

---

## 3. 组件清单与具体用法

## 3.1 布局与导航（Dashboard）

文件：`react-ebook/src/components/DashboardLayout.jsx`

使用组件：

- `Layout`（`Layout.Sider / Header / Content`）
- `Menu`
- `Input`
- `Avatar`
- `Button`
- `Typography`
- `Space`
- 图标：`BookOutlined / ShoppingCartOutlined / SolutionOutlined / UserOutlined / LogoutOutlined / SearchOutlined`

用途与写法：

1. `Layout.Sider`：承载侧边导航与退出按钮  
2. `Menu`：根据当前路由高亮选中项，`onClick` 导航到目标页面  
3. `Input`：顶部搜索输入，`onChange` 继续调用原 `onSearchChange`，保持 action 更新搜索词  
4. `Avatar + Typography.Text`：展示当前用户名  
5. `Button`：退出登录触发原 `onLogout`

---

## 3.2 登录页

文件：`react-ebook/src/pages/LoginPage.jsx`

使用组件：

- `Card`
- `Input` / `Input.Password`
- `Checkbox`
- `Button`
- `Typography`
- `Space`

用途与写法：

1. `Card`：登录表单外层容器  
2. `Input / Input.Password`：用户名与密码输入  
3. `Checkbox`：Remember me 选项  
4. `Button`：登录和游客进入操作  
5. 保留 React Router `<Form>` 与 `useSubmit()`，确保登录逻辑仍由 `loginAction` 处理

---

## 3.3 书籍列表页 + 卡片

文件：

- `react-ebook/src/pages/BooksPage.jsx`
- `react-ebook/src/components/BookCard.jsx`

使用组件：

- `Row` / `Col`
- `Tag`
- `Typography`
- `Card`
- `Button`
- `Space`
- 图标：`ShoppingCartOutlined`

用途与写法：

1. `Row/Col`：替代原手写网格，提供响应式栅格布局  
2. `BookCard` 用 `Card` 渲染书籍信息  
3. `Button`：详情跳转、加入购物车  
4. `Tag`：库存状态显示（绿色/橙色）  
5. “加入购物车”仍通过 React Router `<Form method="post">` 提交 `intent=add-to-cart`

---

## 3.4 书籍详情页

文件：`react-ebook/src/pages/BookDetailPage.jsx`

使用组件：

- `Typography`
- `Tag`
- `Card`
- `Descriptions`
- `Button`
- `Space`

用途与写法：

1. `Typography`：标题、描述、段落文本  
2. `Tag`：库存状态标签  
3. `Descriptions`：结构化展示分类、状态、ISBN、发货方式  
4. `Button`：加入购物车、购买、返回操作  
5. 详情页 `Form` 仍提交到 `bookDetailAction`，数据更新链路不变

---

## 3.5 购物车页

文件：`react-ebook/src/pages/CartPage.jsx`

使用组件：

- `Table`
- `Card`
- `Checkbox`
- `Select`
- `Button`
- `Tag`
- `Typography`
- `Space`
- 图标：`DeleteOutlined`

用途与写法：

1. `Table`：展示购物车明细，替代原 HTML table  
2. `rowSelection`：与已有 `selected` 状态双向同步（单选/全选）  
3. `Select`：数量选择（1~4）并调用 `onUpdateQty`  
4. `Button`：移除商品、结算、继续选购  
5. `Card`：商品区与结算区分组

---

## 3.6 订单页

文件：`react-ebook/src/pages/OrdersPage.jsx`

使用组件：

- `Table`
- `Tag`
- `Button`
- `Typography`
- `Space`

用途与写法：

1. `Table`：订单列表展示  
2. `Tag`：订单状态（待付款/已付款/已取消）  
3. `Button`：取消、付款、再次购买等行操作  
4. 保持 `onUpdateOrderStatus`、`onBuyAgain` 原行为，仍走 action

---

## 3.7 用户信息页

文件：`react-ebook/src/pages/UserPage.jsx`

使用组件：

- `Card`
- `Input` / `Input.TextArea`
- `Button`
- `Tag`
- `Alert`
- `Typography`
- `Space`

用途与写法：

1. 使用 `Card + Input` 构建资料编辑表单  
2. 使用 `Alert` 显示提交结果（成功/错误）  
3. 使用 `Tag` 展示会员等级  
4. 仍使用 React Router `<Form method="post">` 提交 `intent=update-profile`

---

## 4. 与数据路由的配合方式

虽然 UI 替换为 AntD，但所有业务动作依旧是：

1. 组件交互（点击/输入）
2. 提交到 route action（`intent`）
3. action 调用 `appStore` 更新状态
4. loader 重新读取快照
5. 页面基于新数据渲染

这保证了“UI 重构”不会破坏既有路由与状态设计。

---

## 5. 样式适配

文件：`react-ebook/src/styles.css`

新增了 AntD 适配类（如 `.antd-shell__*`、`.book-antd-card*`、`.cart-antd-toolbar`），用于：

- 约束布局尺寸
- 对齐间距
- 保持与原项目页面结构一致

这些样式只做页面级适配，不改动业务逻辑。

---

## 6. 注意事项

1. 引入 AntD 后打包体积增加（构建会提示 chunk 偏大），属于预期现象。  
2. 当前仍可继续按页面分批优化（如按需拆分、路由级代码分割）来降低首屏包体积。  
3. 本次改造未推送仓库，仅完成本地迭代。
