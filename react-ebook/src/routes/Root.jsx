import { Outlet } from "react-router-dom";

// RootRoute：全站根布局路由。
// 当前版本不渲染额外 UI，仅作为 children 的承载容器。
// 后续若需要全局壳（如主题容器、全局提示等），可优先在这里扩展。
export function RootRoute() {
  return <Outlet />;
}

// ProtectedRootRoute：受保护业务区的父路由容器。
// 本身只负责承载子路由，鉴权逻辑由它在路由表里的 loader 统一处理。
export function ProtectedRootRoute() {
  return <Outlet />;
}
