import { redirect } from "react-router-dom";
import { getSnapshot, logout } from "../data/appStore";

// requireAuthLoader：受保护路由的统一鉴权入口。
// 读取当前快照，未登录则在路由层直接重定向到 /login。
// 返回 null 表示本 loader 只做守卫，不负责提供页面渲染数据。
export async function requireAuthLoader() {
  const snapshot = getSnapshot();
  if (!snapshot.isLoggedIn) {
    throw redirect("/login");
  }
  return null;
}

// authRedirectLoader：根路径和兜底路径的分流逻辑。
// 已登录跳 /books；未登录跳 /login，避免出现“空白首页”。
export async function authRedirectLoader() {
  const snapshot = getSnapshot();
  throw redirect(snapshot.isLoggedIn ? "/books" : "/login");
}

// logoutAction：统一退出动作。
// 先清理登录态，再重定向回登录页，确保受保护页面不能继续访问。
export async function logoutAction() {
  logout();
  throw redirect("/login");
}
