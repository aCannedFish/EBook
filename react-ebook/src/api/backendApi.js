const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8080";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {})
    },
    ...options
  });

  if (!response.ok) {
    let message = `request failed: ${response.status}`;
    try {
      const body = await response.json();
      if (body?.message) {
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

export function fetchBooks() {
  return request("/api/v1/books");
}

export function fetchBookById(id) {
  return request(`/api/v1/book/${encodeURIComponent(id)}`);
}

export function createBook(operatorId, payload) {
  return request(`/api/v1/books${buildQuery({ operatorId })}`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function updateBook(operatorId, id, payload) {
  return request(`/api/v1/books/${encodeURIComponent(id)}${buildQuery({ operatorId })}`, {
    method: "PUT",
    body: JSON.stringify(payload)
  });
}

export function deleteBook(operatorId, id) {
  return request(`/api/v1/books/${encodeURIComponent(id)}${buildQuery({ operatorId })}`, {
    method: "DELETE"
  });
}

export function registerUser(payload) {
  return request("/api/v1/users/register", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function loginUser(payload) {
  return request("/api/v1/users/login", {
    method: "POST",
    body: JSON.stringify(payload)
  });
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
