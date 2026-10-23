import { authHeaders, notifyUnauthorized, saveToken } from "./auth";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ??
  (import.meta.env.DEV ? "" : "http://localhost:8080");

async function request(path, options = {}) {
  // 登录与注册使用账号凭证，不附带上一次会话的 Token。
  const { authenticated = true, ...fetchOptions } = options;
  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...fetchOptions,
      headers: {
        "Content-Type": "application/json",
        ...(authenticated ? authHeaders() : {}),
        ...(fetchOptions.headers || {})
      }
    });
  } catch {
    throw new Error(
      "无法连接后端。请确认 ebook-backend 已在 8080 启动；若 5173 端口被占用请先关闭旧的前端进程。"
    );
  }

  if (!response.ok) {
    let message = `request failed: ${response.status}`;
    if (response.status === 401 && !path.includes("/users/login")) {
      notifyUnauthorized();
      message = "登录已过期，请重新登录。";
    }
    if (response.status === 403) {
      message = "当前账号没有访问该资源的权限。";
    }
    try {
      const body = await response.json();
      if (body?.message && response.status !== 403) {
        message = String(body.message);
      }
    } catch {
      // ignore non-json error body
    }
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

function buildQuery(params) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      search.set(key, String(value));
    }
  });
  const query = search.toString();
  return query ? `?${query}` : "";
}

/** 保留页面现有的数组接口，在此适配服务端统一的分页响应。 */
export async function fetchBooks() {
  const first = await request("/api/v1/books?page=0&size=100");
  const items = [...first.items];
  for (let page = 1; page < first.totalPages; page += 1) {
    const next = await request(`/api/v1/books?page=${page}&size=100`);
    items.push(...next.items);
  }
  return items;
}

export function fetchBookById(id) {
  return request(`/api/v1/books/${encodeURIComponent(id)}`);
}

export function createBook(payload) {
  return request("/api/v1/books", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function updateBook(id, payload) {
  return request(`/api/v1/books/${encodeURIComponent(id)}`, {
    method: "PUT",
    body: JSON.stringify(payload)
  });
}

export function deleteBook(id) {
  return request(`/api/v1/books/${encodeURIComponent(id)}`, {
    method: "DELETE"
  });
}

export function registerUser(payload) {
  return request("/api/v1/users/register", {
    authenticated: false,
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function loginUser(payload) {
  const result = await request("/api/v1/users/login", {
    authenticated: false,
    method: "POST",
    body: JSON.stringify(payload)
  });
  saveToken(result.accessToken);
  return result.user;
}

export function fetchUserById(id) {
  return request(`/api/v1/users/${encodeURIComponent(id)}`);
}

export function updateUserProfile(id, payload) {
  return request(`/api/v1/users/${encodeURIComponent(id)}`, {
    method: "PUT",
    body: JSON.stringify(payload)
  });
}

export function fetchAllUsers(operatorId) {
  return request(`/api/v1/users/admin/all${buildQuery({ operatorId })}`);
}

export function setUserEnabled(operatorId, userId, enabled) {
  return request(`/api/v1/users/admin/${encodeURIComponent(userId)}/enabled${buildQuery({ operatorId })}`, {
    method: "PUT",
    body: JSON.stringify({ enabled })
  });
}

export function fetchCartItems(userId) {
  return request(`/api/v1/cart/${encodeURIComponent(userId)}`);
}

export function addCartItem(userId, payload) {
  return request(`/api/v1/cart/${encodeURIComponent(userId)}/items`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function updateCartItem(userId, bookId, payload) {
  return request(`/api/v1/cart/${encodeURIComponent(userId)}/items/${encodeURIComponent(bookId)}`, {
    method: "PATCH",
    body: JSON.stringify(payload)
  });
}

export function removeCartItem(userId, bookId) {
  return request(`/api/v1/cart/${encodeURIComponent(userId)}/items/${encodeURIComponent(bookId)}`, {
    method: "DELETE"
  });
}

export function checkoutCart(userId) {
  return request(`/api/v1/cart/${encodeURIComponent(userId)}/checkout`, {
    method: "POST"
  });
}

export function fetchOrders(userId, filters = {}) {
  return request(`/api/v1/orders/${encodeURIComponent(userId)}${buildQuery(filters)}`);
}

export function fetchAllOrders(operatorId, filters = {}) {
  return request(`/api/v1/orders/admin/all${buildQuery({ operatorId, ...filters })}`);
}

export function updateOrderStatus(userId, orderId, payload) {
  return request(`/api/v1/orders/${encodeURIComponent(userId)}/${encodeURIComponent(orderId)}`, {
    method: "PATCH",
    body: JSON.stringify(payload)
  });
}

export function fetchBookSalesStats(operatorId, filters = {}) {
  return request(`/api/v1/stats/admin/book-sales${buildQuery({ operatorId, ...filters })}`);
}

export function fetchUserSpendingStats(operatorId, filters = {}) {
  return request(`/api/v1/stats/admin/user-spending${buildQuery({ operatorId, ...filters })}`);
}

export function fetchMyPurchaseStats(userId, filters = {}) {
  return request(`/api/v1/stats/my/${encodeURIComponent(userId)}${buildQuery(filters)}`);
}
