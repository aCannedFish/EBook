import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./styles.css";

// 应用启动入口：负责把 React 树挂载到 HTML 的 root 节点，并为整站提供路由能力。
// ReactDOM.createRoot 会创建 React 18 的并发根节点，后续 render 都会在这个容器上完成。
ReactDOM.createRoot(document.getElementById("root")).render(
  // StrictMode 只在开发环境触发额外检查，用来帮助发现副作用、废弃 API 和潜在问题。
  <React.StrictMode>
    {/* BrowserRouter 通过浏览器 History API 管理前端路由，使 /books、/cart 等地址可直接访问。 */}
    <BrowserRouter>
      {/* App 是整个电子书商城的根组件，内部统一管理登录态、购物车和订单状态。 */}
      <App />
    </BrowserRouter>
  </React.StrictMode>
);

