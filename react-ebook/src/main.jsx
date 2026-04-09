import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./styles.css";

// 应用启动入口：注入路由上下文并挂载到 index.html 的 #root。
ReactDOM.createRoot(document.getElementById("root")).render(
  // StrictMode 仅在开发环境帮助发现潜在副作用，不影响生产功能。
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
);

