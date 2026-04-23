import data from "./Data.json";

// =========================
// 前端内存数据仓库（data-router 版本）
// =========================
// 角色定位：
// - 这里是“业务数据的唯一写入入口”；
// - loader 从这里读快照，action 调这里改数据；
// - 页面组件本身不直接持久化全局业务状态。
//
// 设计原因：
// - 保留课堂项目“纯前端读 Data.json”的前提；
// - 同时让数据式路由完整接管读写流程（loader/action）。

// AUTH_USER_KEY：当前登录用户名（会话态）存储键。
const AUTH_USER_KEY = "ebook-auth-username";
// REMEMBER_USER_KEY：记住用户名（登录页默认值）存储键。
const REMEMBER_USER_KEY = "ebook-remember-username";
// USER_EMAIL_KEY / USER_SIGNATURE_KEY：用户资料字段持久化键。
const USER_EMAIL_KEY = "ebook-user-email";
const USER_SIGNATURE_KEY = "ebook-user-signature";

// 运行环境保护：仅在浏览器环境访问 localStorage。
const canUseStorage = typeof window !== "undefined" && typeof window.localStorage !== "undefined";

// 存储读写工具：统一封装，避免到处直接操作 window.localStorage。
const getStoredValue = (key) => {
  if (!canUseStorage) {
    return null;
  }
  return window.localStorage.getItem(key);
};

const setStoredValue = (key, value) => {
  if (!canUseStorage) {
    return;
  }
  window.localStorage.setItem(key, value);
};

const removeStoredValue = (key) => {
  if (!canUseStorage) {
    return;
  }
  window.localStorage.removeItem(key);
};

// 启动时读取“当前已登录用户名”，用于恢复会话。
const authUsername = getStoredValue(AUTH_USER_KEY);
const storedEmail = getStoredValue(USER_EMAIL_KEY);
const storedSignature = getStoredValue(USER_SIGNATURE_KEY);

const initialUser = {
  ...data.user,
  signature: data.user.signature || ""
};

// 内部可变状态对象：
// - books：书籍主数据（只读来源于 Data.json）；
// - user：当前展示的用户信息；
// - cartItems：购物车条目；
// - orders：订单条目；
// - searchByPage：按页面隔离的搜索词；
// - isLoggedIn：登录态。
//
// 注意：state 仅在本模块内部直接修改，对外必须通过导出函数访问。
const state = {
  books: data.books,
  user: {
    ...initialUser,
    username: authUsername || initialUser.username,
    email: storedEmail || initialUser.email,
    signature: storedSignature || initialUser.signature
  },
  cartItems: data.initialCart.map((item) => ({ ...item })),
  orders: data.initialOrders.map((item) => ({ ...item })),
  searchByPage: {
    books: "",
    detail: "",
    cart: "",
    orders: "",
    user: ""
  },
  isLoggedIn: Boolean(authUsername)
};

// getSnapshot：返回“防御性复制”的状态快照给 loader 使用。
// 复制目的：避免外部模块直接改写仓库内部引用，保证写入只能走 action 调用的仓库函数。
export function getSnapshot() {
  return {
    books: state.books,
    user: { ...state.user },
    cartItems: state.cartItems.map((item) => ({ ...item })),
    orders: state.orders.map((item) => ({ ...item })),
    searchByPage: { ...state.searchByPage },
    isLoggedIn: state.isLoggedIn
  };
}

// 返回“记住我”用户名，供登录页 loader 填充输入框默认值。
export function getRememberedUsername() {
  return getStoredValue(REMEMBER_USER_KEY) || "";
}

// 登录行为：
// 1) 打开登录态；
// 2) 更新当前用户名；
// 3) 写入会话用户名；
// 4) 按 remember 决定是否写入“记住我”用户名。
export function login(username, remember) {
  state.isLoggedIn = true;
  state.user = {
    ...state.user,
    username
  };
  setStoredValue(AUTH_USER_KEY, username);
  if (remember) {
    setStoredValue(REMEMBER_USER_KEY, username);
  }
}

// 退出行为：仅清理会话登录态，不清理“记住我”用户名。
export function logout() {
  state.isLoggedIn = false;
  removeStoredValue(AUTH_USER_KEY);
}

// 更新用户资料（用户名/邮箱/个性签名）。
// 注意：当用户名被修改时，需要同步更新会话存储里的用户名。
export function updateUserProfile({ username, email, signature }) {
  state.user = {
    ...state.user,
    username,
    email,
    signature
  };

  setStoredValue(USER_EMAIL_KEY, email);
  setStoredValue(USER_SIGNATURE_KEY, signature);

  if (state.isLoggedIn) {
    setStoredValue(AUTH_USER_KEY, username);
  }

  if (getStoredValue(REMEMBER_USER_KEY)) {
    setStoredValue(REMEMBER_USER_KEY, username);
  }
}

// 更新某个页面的搜索词（其余页面搜索词保持不变）。
export function setPageSearch(pageKey, value) {
  state.searchByPage = {
    ...state.searchByPage,
    [pageKey]: value
  };
}

// 加入购物车：
// - 已存在同书籍：数量 +1（上限 4），并设为选中；
// - 不存在：新增一条默认选中记录。
export function addToCart(bookId) {
  const found = state.cartItems.find((item) => item.bookId === bookId);
  if (found) {
    state.cartItems = state.cartItems.map((item) =>
      item.bookId === bookId
        ? { ...item, qty: Math.min(item.qty + 1, 4), selected: true }
        : item
    );
    return;
  }

  state.cartItems = [...state.cartItems, { bookId, qty: 1, selected: true }];
}

// 购物车全选/全不选。
export function toggleSelectAllCart(checked) {
  state.cartItems = state.cartItems.map((item) => ({ ...item, selected: checked }));
}

// 购物车单行勾选更新。
export function toggleCartItem(bookId, checked) {
  state.cartItems = state.cartItems.map((item) =>
    item.bookId === bookId ? { ...item, selected: checked } : item
  );
}

// 更新单行购买数量（上层 action 已做范围校验）。
export function updateCartQty(bookId, qty) {
  state.cartItems = state.cartItems.map((item) =>
    item.bookId === bookId ? { ...item, qty } : item
  );
}

// 从购物车移除指定 bookId。
export function removeCartItem(bookId) {
  state.cartItems = state.cartItems.filter((item) => item.bookId !== bookId);
}

// 结算逻辑：
// 1) 找出当前选中购物车条目；
// 2) 转换成订单结构（补齐价格，生成订单号）；
// 3) 新订单插入到列表前面；
// 4) 已结算条目从购物车移除。
export function checkoutSelected() {
  const selected = state.cartItems.filter((item) => item.selected);
  if (!selected.length) {
    return;
  }

  const newOrders = selected
    .map((item, index) => {
      const book = state.books.find((entry) => entry.id === item.bookId);
      if (!book) {
        return null;
      }

      return {
        id: `ORD-${Date.now()}-${String(index + 1).padStart(4, "0")}`,
        status: "pending",
        bookId: item.bookId,
        qty: item.qty,
        unitPrice: book.price
      };
    })
    .filter(Boolean);

  state.orders = [...newOrders, ...state.orders];
  state.cartItems = state.cartItems.filter((item) => !item.selected);
}

// 按订单号更新订单状态（pending/paid/cancelled）。
export function updateOrderStatus(orderId, status) {
  state.orders = state.orders.map((order) =>
    order.id === orderId ? { ...order, status } : order
  );
}

// 详情页辅助查询：通过 bookId 返回书籍对象，不存在则返回 null。
export function getBookById(bookId) {
  return state.books.find((item) => item.id === bookId) || null;
}
