# ANT_DESIGN：组件使用与 props 说明（当前实现）

本文档对应当前 `react-ebook` 代码，逐项说明 Ant Design 组件在项目中的作用、调用位置，以及关键 props 的意义。

---

## 1. 接入

1. 依赖：`antd`
2. 入口样式：`src/main.jsx`

```jsx
import "antd/dist/reset.css";
```

用途：重置 AntD 样式基线，减少与项目自定义 CSS 冲突。

---

## 2. DashboardLayout（`src/components/DashboardLayout.jsx`）

## 2.1 `Layout` / `Layout.Sider` / `Layout.Header` / `Layout.Content`

用途：统一后台壳层（侧栏+顶栏+内容区）。

关键 props：

| 组件 | props | 含义/用途 |
|---|---|---|
| `Layout.Sider` | `width={230}` | 固定侧栏宽度，确保菜单区域稳定 |
| `Layout.Header` | `className="antd-shell__header"` | 结合样式层控制顶栏高度与边框 |
| `Layout.Content` | `className="antd-shell__content"` | 统一内容区内边距 |

## 2.2 `Menu`

用途：侧边导航。

关键 props：

| props | 含义/用途 |
|---|---|
| `mode="inline"` | 纵向菜单样式 |
| `selectedKeys={[selectedKey]}` | 根据当前路由高亮对应菜单 |
| `items={menuItems}` | 菜单项配置（key/icon/label） |
| `onClick={({ key }) => navigate(key)}` | 点击后跳转路由 |

## 2.3 `Input`（顶栏搜索）

用途：共享搜索输入框。

关键 props：

| props | 含义/用途 |
|---|---|
| `allowClear` | 显示清空按钮 |
| `prefix={<SearchOutlined />}` | 搜索图标前缀 |
| `placeholder={searchPlaceholder}` | 由当前激活子路由动态决定提示词 |
| `value={searchValue}` | 受控输入值，来源于当前子路由 loader |
| `onChange={(e) => onSearchChange(e.target.value)}` | 触发 Data Router action 写入搜索词 |

## 2.4 `Avatar` / `Typography.Text` / `Button`

- `Avatar size={30} icon={<UserOutlined />}`：显示用户图标
- `Typography.Text`：显示当前用户名
- 退出按钮：`Button icon={<LogoutOutlined />} onClick={onLogout}`

---

## 3. LoginPage（`src/pages/LoginPage.jsx`）

## 3.1 `Card`

- `className="auth__panel card"`：作为登录区容器

## 3.2 `Input` / `Input.Password`

| 组件 | props | 含义/用途 |
|---|---|---|
| `Input` | `value/onChange` | 用户名受控输入 |
| `Input` | `autoComplete="username"` | 浏览器自动填充优化 |
| `Input.Password` | `value/onChange` | 密码受控输入 |
| `Input.Password` | `autoComplete="current-password"` | 密码自动填充优化 |

## 3.3 `Checkbox`

- `checked={remember}`
- `onChange={(e) => setRemember(e.target.checked)}`

用途：控制 remember me 状态并传入 action。

## 3.4 `Button`

- 登录：`type="primary" htmlType="submit"`
- 游客进入：`onClick={handleGuest}`

---

## 4. BooksPage + BookCard

## 4.1 BooksPage（`src/pages/BooksPage.jsx`）

| 组件 | props | 含义/用途 |
|---|---|---|
| `Typography.Title` | `level={3}` | 页面主标题层级 |
| `Tag` | `color="blue"` | 列表数量提示 |
| `Row` | `gutter={[16,16]}` | 卡片栅格行间距和列间距 |
| `Col` | `xs/sm/lg/xl` | 响应式列宽 |

## 4.2 BookCard（`src/components/BookCard.jsx`）

| 组件 | props | 含义/用途 |
|---|---|---|
| `Card` | `className="book-antd-card"` | 书籍卡片容器 |
| `Card` | `cover={<img .../>}` | 封面区域 |
| `Typography.Title` | `level={5}` | 卡片标题 |
| `Tag` | `color={warn? "orange":"green"}` | 库存状态 |
| `Button` | `block` | 按钮同宽铺满卡片内容宽度 |
| `Button` | `type="primary"` | 主操作（加入购物车）视觉强调 |
| `Button` | `icon={<ShoppingCartOutlined />}` | 加购语义图标 |
| `Button` | `htmlType="submit"` | 交给 Router `<Form>` 提交 action |

---

## 5. BookDetailPage（`src/pages/BookDetailPage.jsx`）

| 组件 | props | 含义/用途 |
|---|---|---|
| `Typography.Title` | `level={3/4}` | 主标题与“作品简介”分级 |
| `Typography.Paragraph` | - | 副标题和正文段落 |
| `Tag` | `color` | 库存状态视觉反馈 |
| `Card` | `size="small"` | 关键信息容器 |
| `Descriptions` | `column={1}` | 单列信息展示 |
| `Descriptions` | `size="small"` | 紧凑信息行 |
| `Button` | `htmlType="submit"` | 加购提交 |
| `Space` | `wrap` | 操作按钮自动换行 |

---

## 6. CartPage（`src/pages/CartPage.jsx`）

## 6.1 页面级组件

| 组件 | props | 含义/用途 |
|---|---|---|
| `Card` | `title="商品"` | 商品区分组 |
| `Card` | `title="结算"` / `extra={<Tag .../>}` | 结算区分组及状态角标 |
| `Checkbox` | `checked/onChange` | 全选控制 |
| `Select` | `size="small"` | 紧凑数量选择器 |
| `Select` | `value/options/onChange` | 数量值绑定与更新 |
| `Button` | `type="primary"` | 结算主操作 |

## 6.2 复用组件：`ResourceTable`

调用：

```jsx
<ResourceTable
  rowKey="bookId"
  dataSource={rows}
  columns={columns}
  rowSelection={...}
/>
```

props 说明：

| props | 含义/用途 |
|---|---|
| `rowKey="bookId"` | 行唯一键，保证选择状态稳定 |
| `dataSource={rows}` | 购物车行数据 |
| `columns={columns}` | 列定义（书名/作者/数量/小计/操作） |
| `rowSelection` | 与 `selected` 状态联动，实现单选/全选 |

## 6.3 复用组件：`RowActions`

调用（移除按钮）：

```jsx
<RowActions actions={[{ key, label, danger, icon, onClick }]} />
```

props 说明：

| props | 含义/用途 |
|---|---|
| `actions` | 动作配置数组，驱动按钮渲染 |
| `key` | 按钮稳定键 |
| `label` | 按钮文案 |
| `danger` | 危险操作视觉样式 |
| `icon` | 操作图标 |
| `onClick` | 对应业务动作（如移除） |

---

## 7. OrdersPage（`src/pages/OrdersPage.jsx`）

## 7.1 页面级组件

| 组件 | props | 含义/用途 |
|---|---|---|
| `Typography.Title` | `level={3}` | 页面标题 |
| `Tag` | - | 订单数量提示 |

## 7.2 复用组件：`StatusTag`

调用：

```jsx
<StatusTag status={status} metaMap={statusMeta} />
```

props 说明：

| props | 含义/用途 |
|---|---|
| `status` | 当前状态值（pending/paid/cancelled） |
| `metaMap` | 状态映射表（`label/color`） |

## 7.3 复用组件：`RowActions`

调用为多动作数组（取消/付款/查看/再次购买）。

额外 props：

| props | 含义/用途 |
|---|---|
| `type` | 按钮类型（主按钮等） |
| `hidden` | 条件渲染开关（按状态显示对应动作） |

## 7.4 复用组件：`ResourceTable`

调用：

```jsx
<ResourceTable rowKey="id" dataSource={rows} columns={columns} />
```

用途：统一订单列表表格壳配置。

---

## 8. UserPage（`src/pages/UserPage.jsx`）

| 组件 | props | 含义/用途 |
|---|---|---|
| `Card` | `size="small"` / `bordered={false}` | 表单信息区容器 |
| `Input` | `name/defaultValue/required` | 用户名/邮箱字段提交与回填 |
| `Input.TextArea` | `autoSize={{minRows,maxRows}}` | 签名自适应高度 |
| `Tag` | `color="green"` | 会员等级展示 |
| `Alert` | `type/message/showIcon` | 提交结果反馈 |
| `Button` | `htmlType="submit" form="profile-form"` | 顶部按钮触发表单提交 |
| `Typography.Text` | `type="secondary"` | 字段标签弱化样式 |
| `Space` | `direction="vertical"` | 纵向字段分组 |

---

## 9. 适配样式层（`src/styles.css`）

项目通过 `.antd-shell__*`、`.book-antd-card*`、`.book-antd-grid` 等类对 AntD 组件做页面级约束，目的：

1. 保持课程项目既有布局结构
2. 统一卡片、网格、间距与响应式表现
3. 不改变数据流和 action 行为

---

## 10. 结论

当前 AntD 改造已经覆盖主要页面。所有组件调用都保持“展示层替换、数据层不动”的策略：  
`UI 交互 -> action(intent) -> appStore -> loader -> UI`
