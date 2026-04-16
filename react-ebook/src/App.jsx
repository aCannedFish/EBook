import { createContext, useContext, useMemo, useState } from "react";
import {
  Navigate,
  RouterProvider,
  createBrowserRouter,
  useParams
} from "react-router-dom";
import data from "./data/Data.json";
import ProtectedRoute from "./components/ProtectedRoute";
import LoginPage from "./pages/LoginPage";
import BooksPage from "./pages/BooksPage";
import BookDetailPage from "./pages/BookDetailPage";
import CartPage from "./pages/CartPage";
import OrdersPage from "./pages/OrdersPage";
import UserPage from "./pages/UserPage";

// AppStateContext：集中承载“跨路由共享”的应用级状态与业务动作。
// 设计目的：
// 1) 避免把同一批 props 在路由包装组件中层层透传；
// 2) 让数据式路由的每个 route element 都能直接读取最新状态；
// 3) 保持状态源头唯一（App 根组件）。
const AppStateContext = createContext(null);

// useAppState：自定义 Hook，统一封装 context 读取逻辑。
// 如果组件未被 Provider 包裹，立即抛出错误，避免“默默拿到 null”导致排查困难。
function useAppState() {
  const context = useContext(AppStateContext);
  if (!context) {
    throw new Error("useAppState must be used within AppStateContext.Provider");
  }
  return context;
}

// RedirectByAuth：统一登录态分流逻辑，供 "/" 与 "*" 复用，避免重复组件。
// replace=true 的含义：替换历史记录，避免用户点浏览器“后退”又回到中间重定向页。
function RedirectByAuth() {
  const { isLoggedIn } = useAppState();
  return <Navigate to={isLoggedIn ? "/books" : "/login"} replace />;
}

// LoginRoute：登录路由包装层。
// 只向登录页注入其真正需要的能力（onLogin），页面本身不感知全局状态细节。
function LoginRoute() {
  const { handleLogin } = useAppState();
  return <LoginPage onLogin={handleLogin} />;
}

// ProtectedRouteLayout：受保护路由的公共父层。
// 所有 children 页面都会先经过这里做登录校验。
function ProtectedRouteLayout() {
  const { isLoggedIn } = useAppState();
  return <ProtectedRoute isLoggedIn={isLoggedIn} />;
}

// BooksRoute：书城页路由包装层。
// 职责是“状态映射”而不是业务计算：把 App 的共享状态与动作映射为页面 props。
function BooksRoute() {
  const { books, user, searchByPage, handlePageSearch, addToCart, handleLogout } = useAppState();

  return (
    <BooksPage
      books={books}
      username={user.username}
      search={searchByPage.books}
      onSearchChange={(value) => handlePageSearch("books", value)}
      onAddToCart={addToCart}
      onLogout={handleLogout}
    />
  );
}

// BookDetailRoute：详情页路由包装层。
// 这里先用 URL 参数 bookId 在共享 books 中预取 detailBook，并通过 prop 传入详情页。
function BookDetailRoute() {
  const { bookId } = useParams();
  const { books, user, searchByPage, handlePageSearch, addToCart, handleLogout } = useAppState();
  const detailBook = books.find((item) => item.id === bookId);

  return (
    <BookDetailPage
      detailBook={detailBook}
      username={user.username}
      search={searchByPage.detail}
      onSearchChange={(value) => handlePageSearch("detail", value)}
      onAddToCart={addToCart}
      onLogout={handleLogout}
    />
  );
}

// CartRoute：购物车页路由包装层，向页面注入购物车相关所有动作。
function CartRoute() {
  const {
    books,
    cartItems,
    user,
    searchByPage,
    handlePageSearch,
    toggleSelectAllCart,
    toggleCartItem,
    updateCartQty,
    removeCartItem,
    checkoutSelected,
    handleLogout
  } = useAppState();

  return (
    <CartPage
      books={books}
      cartItems={cartItems}
      username={user.username}
      search={searchByPage.cart}
      onSearchChange={(value) => handlePageSearch("cart", value)}
      onToggleSelectAll={toggleSelectAllCart}
      onToggleItem={toggleCartItem}
      onUpdateQty={updateCartQty}
      onRemoveItem={removeCartItem}
      onCheckout={checkoutSelected}
      onLogout={handleLogout}
    />
  );
}

// OrdersRoute：订单页路由包装层，注入订单状态更新与“再次购买”动作。
function OrdersRoute() {
  const {
    books,
    orders,
    user,
    searchByPage,
    handlePageSearch,
    updateOrderStatus,
    addToCart,
    handleLogout
  } = useAppState();

  return (
    <OrdersPage
      books={books}
      orders={orders}
      username={user.username}
      search={searchByPage.orders}
      onSearchChange={(value) => handlePageSearch("orders", value)}
      onUpdateOrderStatus={updateOrderStatus}
      onBuyAgain={addToCart}
      onLogout={handleLogout}
    />
  );
}

// UserRoute：用户页路由包装层，注入用户信息与局部搜索动作。
function UserRoute() {
  const { user, searchByPage, handlePageSearch, handleLogout } = useAppState();

  return (
    <UserPage
      user={user}
      username={user.username}
      search={searchByPage.user}
      onSearchChange={(value) => handlePageSearch("user", value)}
      onLogout={handleLogout}
    />
  );
}

// 数据式路由配置：以“路由对象数组”描述整站页面结构。
// 与声明式 <Routes><Route> 不同，此处是静态配置+运行时渲染，便于集中管理与扩展。
const router = createBrowserRouter([
  {
    path: "/",
    element: <RedirectByAuth />
  },
  {
    path: "/login",
    element: <LoginRoute />
  },
  {
    element: <ProtectedRouteLayout />,
    children: [
      {
        path: "/books",
        element: <BooksRoute />
      },
      {
        path: "/books/:bookId",
        element: <BookDetailRoute />
      },
      {
        path: "/cart",
        element: <CartRoute />
      },
      {
        path: "/orders",
        element: <OrdersRoute />
      },
      {
        path: "/user",
        element: <UserRoute />
      }
    ]
  },
  {
    path: "*",
    element: <RedirectByAuth />
  }
]);

// 应用根组件：集中管理登录态、用户资料、购物车、订单以及各页面独立搜索词。
function App() {
  // useMemo 缓存书籍数组引用，避免每次渲染都重新创建同一份数据对象。
  const books = useMemo(() => data.books, []);
  // 登录状态决定路由跳转和受保护页面是否可见。
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  // user 保存当前展示中的用户资料，如用户名、邮箱和等级。
  const [user, setUser] = useState(data.user);
  // cartItems 保存购物车条目，每项包含 bookId、qty 与 selected。
  const [cartItems, setCartItems] = useState(data.initialCart);
  // orders 保存订单列表，页面会根据它渲染订单表格。
  const [orders, setOrders] = useState(data.initialOrders);
  // 按页面分别保存搜索词，切换路由时不互相覆盖输入内容。
  const [searchByPage, setSearchByPage] = useState({
    books: "",
    detail: "",
    cart: "",
    orders: "",
    user: ""
  });

  // 根据页面 key 更新对应的搜索词，采用函数式写法避免覆盖其他页面状态。
  const handlePageSearch = (pageKey, value) => {
    setSearchByPage((prev) => ({ ...prev, [pageKey]: value }));
  };

  // 登录成功后：设置登录态、更新用户名；如果勾选记住，则写入 localStorage。
  const handleLogin = (username, remember) => {
    setIsLoggedIn(true);
    setUser((prev) => ({
      ...prev,
      username
    }));

    // localStorage 用于跨刷新记住用户名，这里仅演示持久化存储的写入动作。
    if (remember) {
      localStorage.setItem("ebook-remember-username", username);
    }
  };

  // 退出登录：这里只修改登录态，页面会自动回到登录路由。
  const handleLogout = () => {
    setIsLoggedIn(false);
  };

  // 加入购物车：若已有相同 bookId，则合并数量；否则新增一条购物车记录。
  const addToCart = (bookId) => {
    setCartItems((prev) => {
      // find 用来判断购物车中是否已经存在该书。
      const found = prev.find((item) => item.bookId === bookId);
      if (found) {
        // map 遍历每一项，只修改命中的那一行。
        return prev.map((item) =>
          item.bookId === bookId
            // Math.min 限制最大数量为 4，同时把该项重新设为选中状态。
            ? { ...item, qty: Math.min(item.qty + 1, 4), selected: true }
            : item
        );
      }

      // 如果购物车中还没有这本书，就新建一条并默认选中。
      return [...prev, { bookId, qty: 1, selected: true }];
    });
  };

  // 全选/取消全选：批量修改购物车条目的 selected 字段。
  const toggleSelectAllCart = (checked) => {
    setCartItems((prev) => prev.map((item) => ({ ...item, selected: checked })));
  };

  // 单行勾选：只更新指定 bookId 的 selected 状态。
  const toggleCartItem = (bookId, checked) => {
    setCartItems((prev) =>
      prev.map((item) =>
        item.bookId === bookId ? { ...item, selected: checked } : item
      )
    );
  };

  // 修改数量：通过下拉框把用户选中的 qty 写回对应购物车行。
  const updateCartQty = (bookId, qty) => {
    setCartItems((prev) =>
      prev.map((item) =>
        item.bookId === bookId ? { ...item, qty } : item
      )
    );
  };

  // 从购物车中删除一条记录。
  const removeCartItem = (bookId) => {
    setCartItems((prev) => prev.filter((item) => item.bookId !== bookId));
  };

  // 结算选中项：把选择的购物车行转成订单，并从购物车中移除已结算商品。
  const checkoutSelected = (selectedRows) => {
    // 没有选择任何商品时直接返回，避免生成空订单。
    if (!selectedRows.length) {
      return;
    }

    // map 把选中行转换成订单对象，订单号用时间戳 + 序号生成。
    const newOrders = selectedRows.map((row, index) => ({
      id: `ORD-${Date.now()}-${String(index + 1).padStart(4, "0")}`,
      status: "pending",
      bookId: row.bookId,
      qty: row.qty,
      unitPrice: row.book.price
    }));

    // 新订单放到列表前面，让最新订单优先展示。
    setOrders((prev) => [...newOrders, ...prev]);
    // filter 删除购物车中已勾选的项目，模拟“已结算移出购物车”的行为。
    setCartItems((prev) => prev.filter((item) => !item.selected));
  };

  // 更新订单状态：根据订单 id 替换对应状态字段。
  const updateOrderStatus = (orderId, status) => {
    setOrders((prev) =>
      prev.map((order) => (order.id === orderId ? { ...order, status } : order))
    );
  };

  // appState：统一打包给 Context Provider 的值对象。
  // 包含“状态快照 + 业务动作”，供所有路由包装组件按需解构使用。
  const appState = {
    books,
    isLoggedIn,
    user,
    cartItems,
    orders,
    searchByPage,
    handlePageSearch,
    handleLogin,
    handleLogout,
    addToCart,
    toggleSelectAllCart,
    toggleCartItem,
    updateCartQty,
    removeCartItem,
    checkoutSelected,
    updateOrderStatus
  };

  return (
    // Provider 作为全局状态入口，保证 RouterProvider 渲染的任意路由组件都可读取共享状态。
    <AppStateContext.Provider value={appState}>
      {/* RouterProvider 负责根据当前 URL 选择并渲染 router 中匹配的 route element。 */}
      <RouterProvider router={router} />
    </AppStateContext.Provider>
  );
}

export default App;
