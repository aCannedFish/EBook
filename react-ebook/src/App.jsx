import {
  RouterProvider,
  createBrowserRouter,
  redirect,
  useLoaderData,
  useRouteError,
  useSubmit,
  isRouteErrorResponse
} from "react-router-dom";
import LoginPage from "./pages/LoginPage";
import BooksPage from "./pages/BooksPage";
import BookDetailPage from "./pages/BookDetailPage";
import CartPage from "./pages/CartPage";
import OrdersPage from "./pages/OrdersPage";
import UserPage from "./pages/UserPage";
import {
  addToCart,
  checkoutSelected,
  getBookById,
  getRememberedUsername,
  getSnapshot,
  login,
  logout,
  removeCartItem,
  setPageSearch,
  toggleCartItem,
  toggleSelectAllCart,
  updateCartQty,
  updateOrderStatus
} from "./data/appStore";

// =========================
// 数据路由架构说明（核心）
// =========================
// 本文件是整站“数据式 Router”入口，负责三件事：
// 1) 路由定义：通过 createBrowserRouter 声明 URL -> 页面映射；
// 2) 数据读取：每个页面对应 loader，返回页面渲染所需数据；
// 3) 业务写入：每个页面对应 action，处理表单/按钮触发的数据变更。
//
// 与传统“App useState + props 层层下发”不同：
// - 页面不直接依赖全局 React State 容器；
// - 页面通过 useLoaderData 获取数据快照；
// - 交互通过 submit/Form 触发 action 修改数据并自动驱动路由更新。

// requireAuthSnapshot：统一鉴权入口。
// 任何业务页 loader/action 都可先调用它，确保未登录用户被路由层重定向到 /login。
function requireAuthSnapshot() {
  const snapshot = getSnapshot();
  if (!snapshot.isLoggedIn) {
    throw redirect("/login");
  }
  return snapshot;
}

// readIntent：从 formData 中读取业务意图字段 intent。
// 约定：所有 action 都通过 intent 区分“同一路由下的不同动作分支”。
function readIntent(formData) {
  return String(formData.get("intent") || "");
}

// readRedirectPath：读取表单里可选的 redirectTo，若不存在则使用 fallback。
// 用于“提交动作后跳转到指定页面”的场景（如加入购物车后跳到 /cart）。
function readRedirectPath(formData, fallback) {
  return String(formData.get("redirectTo") || fallback);
}

// "/" 与 "*" 的公共分流逻辑：根据登录态跳去 /books 或 /login。
async function authRedirectLoader() {
  const snapshot = getSnapshot();
  throw redirect(snapshot.isLoggedIn ? "/books" : "/login");
}

// 登录页 loader：
// - 已登录用户不应再次进入登录页，直接跳 /books；
// - 未登录时返回“记住的用户名”用于输入框默认值。
async function loginLoader() {
  const snapshot = getSnapshot();
  if (snapshot.isLoggedIn) {
    throw redirect("/books");
  }
  return {
    defaultUsername: getRememberedUsername()
  };
}

// 登录页 action：
// - intent=login：账号登录（含 remember）；
// - intent=guest：游客登录（默认昵称兜底）。
// 成功后使用 redirect 让路由完成页面跳转与数据刷新。
async function loginAction({ request }) {
  const formData = await request.formData();
  const intent = readIntent(formData);

  if (intent === "login") {
    const username = String(formData.get("username") || "").trim();
    const password = String(formData.get("password") || "").trim();
    const remember = formData.get("remember") === "on";
    if (!username || !password) {
      return null;
    }
    login(username, remember);
    throw redirect("/books");
  }

  if (intent === "guest") {
    const username = String(formData.get("username") || "").trim() || "同学A";
    login(username, false);
    throw redirect("/books");
  }

  return null;
}

// 退出 action：清理登录态并回到登录页。
async function logoutAction() {
  logout();
  throw redirect("/login");
}

// 书城页 loader：提供书籍列表、用户名、该页搜索词。
async function booksLoader() {
  const snapshot = requireAuthSnapshot();
  return {
    books: snapshot.books,
    username: snapshot.user.username,
    search: snapshot.searchByPage.books
  };
}

// 书城页 action：
// - set-search：更新该页搜索词（不跳转）；
// - add-to-cart：加入购物车后按 redirectTo（默认 /cart）跳转。
async function booksAction({ request }) {
  requireAuthSnapshot();
  const formData = await request.formData();
  const intent = readIntent(formData);

  if (intent === "set-search") {
    setPageSearch("books", String(formData.get("value") || ""));
    return null;
  }

  if (intent === "add-to-cart") {
    const bookId = String(formData.get("bookId") || "");
    if (bookId) {
      addToCart(bookId);
    }
    throw redirect(readRedirectPath(formData, "/cart"));
  }

  return null;
}

// 详情页 loader：返回当前书籍对象（detailBook）+ 当前用户与搜索词。
// detailBook 可能为 null（无效 bookId），页面会渲染“未找到”分支。
async function bookDetailLoader({ params }) {
  const snapshot = requireAuthSnapshot();
  return {
    detailBook: getBookById(params.bookId),
    username: snapshot.user.username,
    search: snapshot.searchByPage.detail
  };
}

// 详情页 action：
// - set-search：更新详情页搜索词；
// - add-to-cart：将当前书籍加入购物车并跳转。
async function bookDetailAction({ request, params }) {
  requireAuthSnapshot();
  const formData = await request.formData();
  const intent = readIntent(formData);

  if (intent === "set-search") {
    setPageSearch("detail", String(formData.get("value") || ""));
    return null;
  }

  if (intent === "add-to-cart") {
    const bookId = String(formData.get("bookId") || params.bookId || "");
    if (bookId) {
      addToCart(bookId);
    }
    throw redirect(readRedirectPath(formData, "/cart"));
  }

  return null;
}

// 购物车页 loader：返回渲染购物车所需全部数据。
async function cartLoader() {
  const snapshot = requireAuthSnapshot();
  return {
    books: snapshot.books,
    cartItems: snapshot.cartItems,
    username: snapshot.user.username,
    search: snapshot.searchByPage.cart
  };
}

// 购物车页 action（多分支）：
// - set-search：更新购物车搜索词；
// - toggle-select-all：全选/取消全选；
// - toggle-item：单行勾选；
// - update-qty：更新商品数量（带范围校验 1~4）；
// - remove-item：移除单行；
// - checkout：把已选行转成订单并跳转 /orders。
async function cartAction({ request }) {
  requireAuthSnapshot();
  const formData = await request.formData();
  const intent = readIntent(formData);

  if (intent === "set-search") {
    setPageSearch("cart", String(formData.get("value") || ""));
    return null;
  }

  if (intent === "toggle-select-all") {
    toggleSelectAllCart(formData.get("checked") === "true");
    return null;
  }

  if (intent === "toggle-item") {
    const bookId = String(formData.get("bookId") || "");
    const checked = formData.get("checked") === "true";
    if (bookId) {
      toggleCartItem(bookId, checked);
    }
    return null;
  }

  if (intent === "update-qty") {
    const bookId = String(formData.get("bookId") || "");
    const qty = Number(formData.get("qty"));
    if (bookId && Number.isInteger(qty) && qty >= 1 && qty <= 4) {
      updateCartQty(bookId, qty);
    }
    return null;
  }

  if (intent === "remove-item") {
    const bookId = String(formData.get("bookId") || "");
    if (bookId) {
      removeCartItem(bookId);
    }
    return null;
  }

  if (intent === "checkout") {
    checkoutSelected();
    throw redirect("/orders");
  }

  return null;
}

// 订单页 loader：返回订单表格所需数据。
async function ordersLoader() {
  const snapshot = requireAuthSnapshot();
  return {
    books: snapshot.books,
    orders: snapshot.orders,
    username: snapshot.user.username,
    search: snapshot.searchByPage.orders
  };
}

// 订单页 action：
// - set-search：更新订单搜索；
// - update-status：更新订单状态（限制在允许值集合）；
// - buy-again：再次购买（实质是 addToCart）后跳转。
async function ordersAction({ request }) {
  requireAuthSnapshot();
  const formData = await request.formData();
  const intent = readIntent(formData);

  if (intent === "set-search") {
    setPageSearch("orders", String(formData.get("value") || ""));
    return null;
  }

  if (intent === "update-status") {
    const orderId = String(formData.get("orderId") || "");
    const status = String(formData.get("status") || "");
    if (orderId && ["pending", "paid", "cancelled"].includes(status)) {
      updateOrderStatus(orderId, status);
    }
    return null;
  }

  if (intent === "buy-again") {
    const bookId = String(formData.get("bookId") || "");
    if (bookId) {
      addToCart(bookId);
    }
    throw redirect(readRedirectPath(formData, "/books"));
  }

  return null;
}

// 用户页 loader：返回用户信息与该页搜索词。
async function userLoader() {
  const snapshot = requireAuthSnapshot();
  return {
    user: snapshot.user,
    username: snapshot.user.username,
    search: snapshot.searchByPage.user
  };
}

// 用户页 action：当前只处理搜索词同步。
async function userAction({ request }) {
  requireAuthSnapshot();
  const formData = await request.formData();
  const intent = readIntent(formData);
  if (intent === "set-search") {
    setPageSearch("user", String(formData.get("value") || ""));
  }
  return null;
}

// ===== 路由组件层（loader 数据 -> 页面 props）=====
// 这些组件不保存业务状态，只做“桥接”：
// 1) 用 useLoaderData 读取该路由 loader 返回的数据；
// 2) 用 useSubmit 把页面事件转换为 action 提交请求。

function BooksRoute() {
  const data = useLoaderData();
  const submit = useSubmit();
  return (
    <BooksPage
      books={data.books}
      username={data.username}
      search={data.search}
      // navigate:false 表示仅提交 action 并刷新当前数据，不改变地址栏路径。
      onSearchChange={(value) => submit({ intent: "set-search", value }, { method: "post", action: "/books", navigate: false })}
      onLogout={() => submit(null, { method: "post", action: "/logout" })}
    />
  );
}

function BookDetailRoute() {
  const data = useLoaderData();
  const submit = useSubmit();
  return (
    <BookDetailPage
      detailBook={data.detailBook}
      username={data.username}
      search={data.search}
      // 详情页提交到“当前路由 action”（不显式写 action），由 bookDetailAction 处理。
      onSearchChange={(value) => submit({ intent: "set-search", value }, { method: "post", navigate: false })}
      onLogout={() => submit(null, { method: "post", action: "/logout" })}
    />
  );
}

function CartRoute() {
  const data = useLoaderData();
  const submit = useSubmit();
  return (
    <CartPage
      books={data.books}
      cartItems={data.cartItems}
      username={data.username}
      search={data.search}
      onSearchChange={(value) => submit({ intent: "set-search", value }, { method: "post", action: "/cart", navigate: false })}
      onToggleSelectAll={(checked) => submit({ intent: "toggle-select-all", checked: String(checked) }, { method: "post", action: "/cart", navigate: false })}
      onToggleItem={(bookId, checked) => submit({ intent: "toggle-item", bookId, checked: String(checked) }, { method: "post", action: "/cart", navigate: false })}
      onUpdateQty={(bookId, qty) => submit({ intent: "update-qty", bookId, qty: String(qty) }, { method: "post", action: "/cart", navigate: false })}
      onRemoveItem={(bookId) => submit({ intent: "remove-item", bookId }, { method: "post", action: "/cart", navigate: false })}
      // checkout 需要跳到订单页，因此不使用 navigate:false。
      onCheckout={() => submit({ intent: "checkout" }, { method: "post", action: "/cart" })}
      onLogout={() => submit(null, { method: "post", action: "/logout" })}
    />
  );
}

function OrdersRoute() {
  const data = useLoaderData();
  const submit = useSubmit();
  return (
    <OrdersPage
      books={data.books}
      orders={data.orders}
      username={data.username}
      search={data.search}
      onSearchChange={(value) => submit({ intent: "set-search", value }, { method: "post", action: "/orders", navigate: false })}
      onUpdateOrderStatus={(orderId, status) => submit({ intent: "update-status", orderId, status }, { method: "post", action: "/orders", navigate: false })}
      // 再次购买后由 action 控制跳转目标，保持动作逻辑集中在路由层。
      onBuyAgain={(bookId) => submit({ intent: "buy-again", bookId, redirectTo: "/books" }, { method: "post", action: "/orders" })}
      onLogout={() => submit(null, { method: "post", action: "/logout" })}
    />
  );
}

function UserRoute() {
  const data = useLoaderData();
  const submit = useSubmit();
  return (
    <UserPage
      user={data.user}
      username={data.username}
      search={data.search}
      onSearchChange={(value) => submit({ intent: "set-search", value }, { method: "post", action: "/user", navigate: false })}
      onLogout={() => submit(null, { method: "post", action: "/logout" })}
    />
  );
}

// 通用路由错误边界：
// - 响应型错误（throw redirect/Response）显示状态码信息；
// - 其他运行时异常显示通用错误文案。
function RouteErrorBoundary() {
  const error = useRouteError();
  if (isRouteErrorResponse(error)) {
    return (
      <main className="auth">
        <section className="auth__panel card">
          <h1>页面加载失败</h1>
          <p>{error.status} {error.statusText}</p>
        </section>
      </main>
    );
  }

  return (
    <main className="auth">
      <section className="auth__panel card">
        <h1>页面发生异常</h1>
        <p>请刷新后重试。</p>
      </section>
    </main>
  );
}

// 路由表：每个业务页面都具备“loader + action + element + errorElement”四元能力。
// 这让页面的数据读取、写入与异常处理都在路由层集中表达。
const router = createBrowserRouter([
  {
    path: "/",
    loader: authRedirectLoader,
    errorElement: <RouteErrorBoundary />
  },
  {
    path: "/login",
    loader: loginLoader,
    action: loginAction,
    element: <LoginPage />,
    errorElement: <RouteErrorBoundary />
  },
  {
    path: "/logout",
    action: logoutAction
  },
  {
    path: "/books",
    loader: booksLoader,
    action: booksAction,
    element: <BooksRoute />,
    errorElement: <RouteErrorBoundary />
  },
  {
    path: "/books/:bookId",
    loader: bookDetailLoader,
    action: bookDetailAction,
    element: <BookDetailRoute />,
    errorElement: <RouteErrorBoundary />
  },
  {
    path: "/cart",
    loader: cartLoader,
    action: cartAction,
    element: <CartRoute />,
    errorElement: <RouteErrorBoundary />
  },
  {
    path: "/orders",
    loader: ordersLoader,
    action: ordersAction,
    element: <OrdersRoute />,
    errorElement: <RouteErrorBoundary />
  },
  {
    path: "/user",
    loader: userLoader,
    action: userAction,
    element: <UserRoute />,
    errorElement: <RouteErrorBoundary />
  },
  {
    path: "*",
    loader: authRedirectLoader
  }
]);

// App 变为纯路由壳：不再维护业务 useState，
// 所有页面数据来自 loader，交互提交到 action。
function App() {
  return <RouterProvider router={router} />;
}

export default App;
