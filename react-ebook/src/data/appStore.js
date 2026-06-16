import data from "./Data.json";
import { resolveBookCover } from "../utils/cover";
import {
  addCartItem,
  checkoutCart,
  createBook as createBookApi,
  deleteBook as deleteBookApi,
  fetchAllOrders,
  fetchAllUsers,
  fetchBookById,
  fetchBookSalesStats,
  fetchBooks,
  fetchCartItems,
  fetchMyPurchaseStats,
  fetchOrders,
  fetchUserSpendingStats,
  removeCartItem as removeCartItemApi,
  setUserEnabled,
  updateBook as updateBookApi,
  updateCartItem,
  updateOrderStatus as updateOrderStatusApi,
  updateUserProfile as updateUserProfileApi
} from "../api/backendApi";

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
const AUTH_USER_ID_KEY = "ebook-auth-user-id";
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
const storedUserIdRaw = getStoredValue(AUTH_USER_ID_KEY);
const storedUserId = storedUserIdRaw ? Number(storedUserIdRaw) : null;
const storedEmail = getStoredValue(USER_EMAIL_KEY);
const storedSignature = getStoredValue(USER_SIGNATURE_KEY);

const initialUser = {
  ...data.user,
  signature: data.user.signature || ""
};

const fallbackCoverByIsbn = new Map(
  data.books.map((book) => [book.isbn, resolveBookCover(book)])
);

function normalizeBook(rawBook) {
  return {
    ...rawBook,
    id: String(rawBook.id),
    price: Number(rawBook.price) || 0,
    stockQty: Number(rawBook.stockQty ?? rawBook.stock_qty ?? 0),
    cover: resolveBookCover(rawBook) || fallbackCoverByIsbn.get(rawBook.isbn) || "/assets/logo.svg"
  };
}

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
  books: [],
  user: {
    ...initialUser,
    id: Number.isFinite(storedUserId) ? storedUserId : null,
    username: authUsername || initialUser.username,
    email: storedEmail || initialUser.email,
    signature: storedSignature || initialUser.signature
  },
  cartItems: [],
  orders: [],
  adminUsers: [],
  orderFilters: {
    from: "",
    to: "",
    bookTitle: ""
  },
  statsFilters: {
    from: "",
    to: ""
  },
  bookSalesStats: [],
  userSpendingStats: [],
  myPurchaseStats: null,
  searchByPage: {
    books: "",
    detail: "",
    cart: "",
    orders: "",
    user: "",
    adminBooks: "",
    adminUsers: "",
    adminOrders: "",
    stats: ""
  },
  isLoggedIn: Boolean(authUsername && Number.isFinite(storedUserId))
};

let booksLoaded = false;
let cartLoaded = false;
let ordersLoaded = false;

// getSnapshot：返回“防御性复制”的状态快照给 loader 使用。
// 复制目的：避免外部模块直接改写仓库内部引用，保证写入只能走 action 调用的仓库函数。
export function getSnapshot() {
  return {
    books: state.books,
    user: { ...state.user },
    cartItems: state.cartItems.map((item) => ({ ...item })),
    orders: state.orders.map((item) => ({ ...item })),
    adminUsers: state.adminUsers.map((item) => ({ ...item })),
    orderFilters: { ...state.orderFilters },
    statsFilters: { ...state.statsFilters },
    bookSalesStats: state.bookSalesStats,
    userSpendingStats: state.userSpendingStats,
    myPurchaseStats: state.myPurchaseStats,
    searchByPage: { ...state.searchByPage },
    isLoggedIn: state.isLoggedIn
  };
}

function pruneItemsWithoutBooks() {
  const bookIdSet = new Set(state.books.map((book) => String(book.id)));
  state.cartItems = state.cartItems
    .map((item) => ({ ...item, bookId: String(item.bookId) }))
    .filter((item) => bookIdSet.has(item.bookId));
  state.orders = state.orders
    .map((order) => ({
      ...order,
      items: (order.items || [])
        .map((line) => ({ ...line, bookId: String(line.bookId) }))
        .filter((line) => bookIdSet.has(line.bookId))
    }))
    .filter((order) => order.items.length > 0);
}

export async function ensureBooksLoaded(force = false) {
  if (booksLoaded && !force) {
    return state.books;
  }

  const books = await fetchBooks();
  state.books = books.map(normalizeBook);
  booksLoaded = true;
  pruneItemsWithoutBooks();
  return state.books;
}

export async function ensureCartLoaded(force = false) {
  if (cartLoaded && !force) {
    return state.cartItems;
  }
  if (!state.isLoggedIn || !state.user.id) {
    state.cartItems = [];
    cartLoaded = true;
    return state.cartItems;
  }
  const items = await fetchCartItems(state.user.id);
  state.cartItems = items.map((item) => ({
    ...item,
    bookId: String(item.bookId),
    qty: Number(item.qty) || 1,
    selected: Boolean(item.selected)
  }));
  cartLoaded = true;
  return state.cartItems;
}

export async function ensureOrdersLoaded(force = false, { adminView = false, filters = state.orderFilters } = {}) {
  if (ordersLoaded && !force) {
    return state.orders;
  }
  if (!state.isLoggedIn || !state.user.id) {
    state.orders = [];
    ordersLoaded = true;
    return state.orders;
  }
  const query = {
    from: filters.from || undefined,
    to: filters.to || undefined,
    bookTitle: filters.bookTitle || undefined
  };
  const items = adminView && state.user.admin
    ? await fetchAllOrders(state.user.id, query)
    : await fetchOrders(state.user.id, query);
  state.orders = items.map((item) => ({
    ...item,
    id: String(item.id),
    status: item.status,
    totalPrice: Number(item.totalPrice) || 0,
    userId: item.userId,
    username: item.username,
    createdAt: item.createdAt,
    items: (item.items || []).map((line) => ({
      bookId: String(line.bookId),
      qty: Number(line.qty) || 1,
      unitPrice: Number(line.unitPrice) || 0
    }))
  }));
  ordersLoaded = true;
  return state.orders;
}

export function setOrderFilters(filters) {
  state.orderFilters = { ...state.orderFilters, ...filters };
  ordersLoaded = false;
}

export function setStatsFilters(filters) {
  state.statsFilters = { ...state.statsFilters, ...filters };
}

export async function ensureAdminUsersLoaded(force = false) {
  if (!state.user.admin || !state.user.id) {
    state.adminUsers = [];
    return state.adminUsers;
  }
  if (state.adminUsers.length && !force) {
    return state.adminUsers;
  }
  state.adminUsers = await fetchAllUsers(state.user.id);
  return state.adminUsers;
}

export async function toggleUserEnabled(userId, enabled) {
  if (!state.user.admin || !state.user.id) {
    return;
  }
  await setUserEnabled(state.user.id, userId, enabled);
  await ensureAdminUsersLoaded(true);
}

export async function saveBook(bookPayload, bookId) {
  if (!state.user.admin || !state.user.id) {
    return;
  }
  if (bookId) {
    await updateBookApi(state.user.id, bookId, bookPayload);
  } else {
    await createBookApi(state.user.id, bookPayload);
  }
  await ensureBooksLoaded(true);
}

export async function removeBook(bookId) {
  if (!state.user.admin || !state.user.id) {
    return;
  }
  await deleteBookApi(state.user.id, bookId);
  await ensureBooksLoaded(true);
}

export async function loadStats(force = false) {
  if (!state.isLoggedIn || !state.user.id) {
    return;
  }
  const query = {
    from: state.statsFilters.from || undefined,
    to: state.statsFilters.to || undefined
  };
  if (state.user.admin) {
    state.bookSalesStats = await fetchBookSalesStats(state.user.id, query);
    state.userSpendingStats = await fetchUserSpendingStats(state.user.id, query);
    state.myPurchaseStats = null;
  } else {
    state.myPurchaseStats = await fetchMyPurchaseStats(state.user.id, query);
    state.bookSalesStats = [];
    state.userSpendingStats = [];
  }
  return {
    bookSalesStats: state.bookSalesStats,
    userSpendingStats: state.userSpendingStats,
    myPurchaseStats: state.myPurchaseStats
  };
}

export async function fetchAndStoreBookById(bookId) {
  const book = normalizeBook(await fetchBookById(bookId));
  const existingIndex = state.books.findIndex((item) => item.id === book.id);
  if (existingIndex >= 0) {
    state.books = state.books.map((item) => (item.id === book.id ? book : item));
  } else {
    state.books = [...state.books, book];
  }
  booksLoaded = true;
  return book;
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
export function setAuthenticatedUser(user, remember) {
  state.isLoggedIn = true;
  state.user = {
    ...state.user,
    id: user.id,
    username: user.username,
    email: user.email,
    signature: user.signature || "",
    level: user.level || state.user.level,
    admin: Boolean(user.admin),
    enabled: user.enabled !== false
  };
  setStoredValue(AUTH_USER_KEY, user.username);
  setStoredValue(AUTH_USER_ID_KEY, String(user.id));
  setStoredValue(USER_EMAIL_KEY, user.email || "");
  setStoredValue(USER_SIGNATURE_KEY, user.signature || "");
  if (remember) {
    setStoredValue(REMEMBER_USER_KEY, user.username);
  }
  cartLoaded = false;
  ordersLoaded = false;
}

// 退出行为：仅清理会话登录态，不清理“记住我”用户名。
export function logout() {
  state.isLoggedIn = false;
  state.user = {
    ...initialUser,
    id: null,
    username: initialUser.username,
    email: getStoredValue(USER_EMAIL_KEY) || initialUser.email,
    signature: getStoredValue(USER_SIGNATURE_KEY) || initialUser.signature
  };
  removeStoredValue(AUTH_USER_KEY);
  removeStoredValue(AUTH_USER_ID_KEY);
  state.cartItems = [];
  state.orders = [];
  cartLoaded = false;
  ordersLoaded = false;
}

// 更新用户资料（用户名/邮箱/个性签名）。
// 注意：当用户名被修改时，需要同步更新会话存储里的用户名。
export async function updateUserProfile({ username, email, signature }) {
  if (!state.user.id) {
    return;
  }
  const updated = await updateUserProfileApi(state.user.id, { username, email, signature });
  state.user = {
    ...state.user,
    username: updated.username,
    email: updated.email,
    signature: updated.signature || "",
    level: updated.level || state.user.level
  };
  setStoredValue(USER_EMAIL_KEY, updated.email || "");
  setStoredValue(USER_SIGNATURE_KEY, updated.signature || "");
  setStoredValue(AUTH_USER_KEY, updated.username);
  if (getStoredValue(REMEMBER_USER_KEY)) {
    setStoredValue(REMEMBER_USER_KEY, updated.username);
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
export async function addToCart(bookId) {
  if (!state.user.id) {
    return;
  }
  const items = await addCartItem(state.user.id, { bookId: Number(bookId), qty: 1 });
  state.cartItems = items.map((item) => ({
    ...item,
    bookId: String(item.bookId),
    qty: Number(item.qty) || 1,
    selected: Boolean(item.selected)
  }));
  cartLoaded = true;
}

// 购物车全选/全不选。
export async function toggleSelectAllCart(checked) {
  if (!state.user.id) {
    return;
  }
  const tasks = state.cartItems
    .filter((item) => item.selected !== checked)
    .map((item) => updateCartItem(state.user.id, item.bookId, { selected: checked }));
  if (tasks.length) {
    await Promise.all(tasks);
  }
  await ensureCartLoaded(true);
}

// 购物车单行勾选更新。
export async function toggleCartItem(bookId, checked) {
  if (!state.user.id) {
    return;
  }
  const items = await updateCartItem(state.user.id, bookId, { selected: checked });
  state.cartItems = items.map((item) => ({
    ...item,
    bookId: String(item.bookId),
    qty: Number(item.qty) || 1,
    selected: Boolean(item.selected)
  }));
  cartLoaded = true;
}

// 更新单行购买数量（上层 action 已做范围校验）。
export async function updateCartQty(bookId, qty) {
  if (!state.user.id) {
    return;
  }
  const items = await updateCartItem(state.user.id, bookId, { qty });
  state.cartItems = items.map((item) => ({
    ...item,
    bookId: String(item.bookId),
    qty: Number(item.qty) || 1,
    selected: Boolean(item.selected)
  }));
  cartLoaded = true;
}

// 从购物车移除指定 bookId。
export async function removeCartItem(bookId) {
  if (!state.user.id) {
    return;
  }
  const items = await removeCartItemApi(state.user.id, bookId);
  state.cartItems = items.map((item) => ({
    ...item,
    bookId: String(item.bookId),
    qty: Number(item.qty) || 1,
    selected: Boolean(item.selected)
  }));
  cartLoaded = true;
}

// 结算逻辑：
// 1) 找出当前选中购物车条目；
// 2) 转换成订单结构（补齐价格，生成订单号）；
// 3) 新订单插入到列表前面；
// 4) 已结算条目从购物车移除。
export async function checkoutSelected() {
  if (!state.user.id) {
    return;
  }
  await checkoutCart(state.user.id);
  await ensureCartLoaded(true);
  await ensureOrdersLoaded(true);
}

// 按订单号更新订单状态（pending/paid/cancelled）。
export async function updateOrderStatus(orderId, status, userId = state.user.id) {
  if (!userId) {
    return;
  }
  const updated = await updateOrderStatusApi(userId, orderId, { status });
  state.orders = state.orders.map((order) =>
    order.id === updated.id ? { ...order, status: updated.status } : order
  );
  ordersLoaded = true;
}

// 详情页辅助查询：通过 bookId 返回书籍对象，不存在则返回 null。
export function getBookById(bookId) {
  const normalizedBookId = String(bookId);
  return state.books.find((item) => String(item.id) === normalizedBookId) || null;
}
