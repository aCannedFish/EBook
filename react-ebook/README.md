# react-ebook

作业 3 的 React + React Router 版本电子书城，功能覆盖：登录、书城、详情、购物车、订单、用户信息。

## 快速开始

```bash
npm install
npm run dev
```

默认访问开发地址（通常是 `http://localhost:5173`）。

## 路由

- `/login`
- `/books`
- `/books/:bookId`
- `/cart`
- `/orders`
- `/user`

## 可验证点

1. 登录后才能进入业务页。
2. 书城点击“查看详情”会进入对应 `bookId` 的详情页。
3. 列表和详情页都可以“加入购物车”。
4. 购物车支持全选、数量修改、移除、结算。
5. 订单页支持取消/付款/再次购买。
6. 用户页展示基本资料与快捷入口。

## 代码结构

- `src/pages`：页面组件
- `src/components`：复用组件
- `src/data/Data.json`：前端演示数据
- `src/App.jsx`：路由与全局状态
