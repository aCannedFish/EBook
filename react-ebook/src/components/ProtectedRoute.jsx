import { Navigate, Outlet } from "react-router-dom";

// 路由守卫：未登录时统一跳回登录页，已登录则渲染子路由。
function ProtectedRoute({ isLoggedIn }) {
  if (!isLoggedIn) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}

export default ProtectedRoute;

