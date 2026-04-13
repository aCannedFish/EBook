import { Navigate, Outlet } from "react-router-dom";

// 路由守卫组件：在进入受保护页面之前先检查登录状态。
// 这里不直接渲染页面内容，而是根据条件决定返回登录页还是嵌套路由出口。
function ProtectedRoute({ isLoggedIn }) {
  // 如果当前没有登录，就立刻重定向到 /login，并使用 replace 避免污染浏览历史。
  if (!isLoggedIn) {
    return <Navigate to="/login" replace />;
  }

  // 已登录时渲染 <Outlet />，让父级路由下的子页面继续正常显示。
  return <Outlet />;
}

export default ProtectedRoute;

