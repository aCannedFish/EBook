# HTML 交互设计说明

## 1. 实现目标

本版本为原生 HTML + CSS 静态页面实现，对应课程作业的前端展示需求：

- 登录页（`pages/login.html`）
- 书城列表页（`pages/books.html`）
- 书籍详情页（`pages/book-detail.html`）
- 购物车页（`pages/cart.html`）
- 订单页（`pages/orders.html`）
- 用户信息页（`pages/user.html`）

页面以 UI 展示和页面跳转为主，不包含真实后端接口。

## 2. 目录结构

```text
html-version/
  index.html
  pages/
  css/styles.css
  assets/
```

- `pages/`：页面级模板，按业务拆分。
- `css/styles.css`：统一样式入口。
- `assets/`：封面图、Logo、头像等静态资源。

## 3. 页面与交互设计

- 语义化结构：`header`、`main`、`section`、`nav`、`aside`、`table`。
- 侧栏导航与顶栏在业务页保持统一，保证一致体验。
- 交互通过链接与表单行为模拟：登录跳转、详情跳转、购物车与订单按钮展示。
- 当前不包含真实后端数据读写。

## 4. 样式与响应式

`css/styles.css` 采用“主题变量 + 组件类 + 工具类”的组织方式，核心布局使用 `flex` 与 `grid`，并通过多断点适配平板与手机。

## 5. 与 React 版本关系

HTML 版本是 React 版本的界面原型：

- 信息架构一致。
- 视觉风格一致。
- React 版本在此基础上增加路由与状态管理。

## 6. 运行方式

```bash
git checkout html-version
open pages/login.html
```

