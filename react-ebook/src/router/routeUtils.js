import { redirect } from "react-router-dom";
import { getSnapshot } from "../data/appStore";

// 读取当前全局快照并做登录态校验。
// 未登录时在路由层直接重定向到 /login。
export function requireAuthSnapshot() {
  const snapshot = getSnapshot();
  if (!snapshot.isLoggedIn) {
    throw redirect("/login");
  }
  return snapshot;
}

// action 分派约定：通过 intent 区分同一路由下的多种操作。
export function readIntent(formData) {
  return String(formData.get("intent") || "");
}

// 可选跳转路径读取：没有 redirectTo 时退回 fallback。
export function readRedirectPath(formData, fallback) {
  return String(formData.get("redirectTo") || fallback);
}
