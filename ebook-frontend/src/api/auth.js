/** JWT 的浏览器持久化入口。用户资料只用于展示，服务端身份由 Token 决定。 */
const TOKEN_KEY = "ebook-access-token";

export function getToken() {
  return typeof window === "undefined" ? null : window.localStorage.getItem(TOKEN_KEY);
}

export function saveToken(token) {
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  if (typeof window !== "undefined") {
    window.localStorage.removeItem(TOKEN_KEY);
  }
}

export function authHeaders() {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/** 此处仅决定页面是否需要重新登录；签名与权限始终由书城后端校验。 */
export function hasValidToken() {
  try {
    const payload = getToken().split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    return JSON.parse(window.atob(payload)).exp * 1000 > Date.now();
  } catch {
    return false;
  }
}

export function notifyUnauthorized() {
  clearToken();
  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event("ebook:unauthorized"));
  }
}

/** 刷新页面时恢复菜单角色；接口权限仍由服务端依据当前用户记录判断。 */
export function tokenIsAdmin() {
  try {
    const payload = getToken().split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    return JSON.parse(window.atob(payload)).role === "ADMIN";
  } catch {
    return false;
  }
}
