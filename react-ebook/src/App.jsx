import { Navigate, Route, Routes } from "react-router-dom";
import { useMemo, useState } from "react";
import data from "./data/Data.json";
import ProtectedRoute from "./components/ProtectedRoute";
import LoginPage from "./pages/LoginPage";
import BooksPage from "./pages/BooksPage";
import BookDetailPage from "./pages/BookDetailPage";
import CartPage from "./pages/CartPage";
import OrdersPage from "./pages/OrdersPage";
import UserPage from "./pages/UserPage";

// 应用根组件：集中维护登录态、购物车、订单与各页面搜索状态。
function App() {
  const books = useMemo(() => data.books, []);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [user, setUser] = useState(data.user);
  const [cartItems, setCartItems] = useState(data.initialCart);
  const [orders, setOrders] = useState(data.initialOrders);
  // 按页面保存搜索词，切页时可保留当前页面输入。
  const [searchByPage, setSearchByPage] = useState({
    books: "",
    detail: "",
    cart: "",
    orders: "",
    user: ""
  });

  const handlePageSearch = (pageKey, value) => {
    setSearchByPage((prev) => ({ ...prev, [pageKey]: value }));
  };

  // 登录后更新展示用户名；勾选记住时写入本地存储。
  const handleLogin = (username, remember) => {
    setIsLoggedIn(true);
    setUser((prev) => ({
      ...prev,
      username
    }));

    if (remember) {
      localStorage.setItem("ebook-remember-username", username);
    }
  };

  const handleLogout = () => {
    setIsLoggedIn(false);
  };

  // 购物车同书籍按 id 合并数量，且最大数量限制为 4。
  const addToCart = (bookId) => {
    setCartItems((prev) => {
      const found = prev.find((item) => item.bookId === bookId);
      if (found) {
        return prev.map((item) =>
          item.bookId === bookId
            ? { ...item, qty: Math.min(item.qty + 1, 4), selected: true }
            : item
        );
      }

      return [...prev, { bookId, qty: 1, selected: true }];
    });
  };

  const toggleSelectAllCart = (checked) => {
    setCartItems((prev) => prev.map((item) => ({ ...item, selected: checked })));
  };

  const toggleCartItem = (bookId, checked) => {
    setCartItems((prev) =>
      prev.map((item) =>
        item.bookId === bookId ? { ...item, selected: checked } : item
      )
    );
  };

  const updateCartQty = (bookId, qty) => {
    setCartItems((prev) =>
      prev.map((item) =>
        item.bookId === bookId ? { ...item, qty } : item
      )
    );
  };

  const removeCartItem = (bookId) => {
    setCartItems((prev) => prev.filter((item) => item.bookId !== bookId));
  };

  const checkoutSelected = (selectedRows) => {
    if (!selectedRows.length) {
      return;
    }

    // 生成简易订单号并把已勾选商品从购物车移除。
    const newOrders = selectedRows.map((row, index) => ({
      id: `ORD-${Date.now()}-${String(index + 1).padStart(4, "0")}`,
      status: "pending",
      bookId: row.bookId,
      qty: row.qty,
      unitPrice: row.book.price
    }));

    setOrders((prev) => [...newOrders, ...prev]);
    setCartItems((prev) => prev.filter((item) => !item.selected));
  };

  const updateOrderStatus = (orderId, status) => {
    setOrders((prev) =>
      prev.map((order) => (order.id === orderId ? { ...order, status } : order))
    );
  };

  return (
    // 路由结构与原静态页面对应：登录、书城、详情、购物车、订单、用户中心。
    <Routes>
      <Route
        path="/"
        element={<Navigate to={isLoggedIn ? "/books" : "/login"} replace />}
      />
      <Route path="/login" element={<LoginPage onLogin={handleLogin} />} />

      <Route element={<ProtectedRoute isLoggedIn={isLoggedIn} />}>
        <Route
          path="/books"
          element={
            <BooksPage
              books={books}
              username={user.username}
              search={searchByPage.books}
              onSearchChange={(value) => handlePageSearch("books", value)}
              onAddToCart={addToCart}
              onLogout={handleLogout}
            />
          }
        />
        <Route
          path="/books/:bookId"
          element={
            <BookDetailPage
              books={books}
              username={user.username}
              search={searchByPage.detail}
              onSearchChange={(value) => handlePageSearch("detail", value)}
              onAddToCart={addToCart}
              onLogout={handleLogout}
            />
          }
        />
        <Route
          path="/cart"
          element={
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
          }
        />
        <Route
          path="/orders"
          element={
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
          }
        />
        <Route
          path="/user"
          element={
            <UserPage
              user={user}
              username={user.username}
              search={searchByPage.user}
              onSearchChange={(value) => handlePageSearch("user", value)}
              onLogout={handleLogout}
            />
          }
        />
      </Route>

      <Route path="*" element={<Navigate to={isLoggedIn ? "/books" : "/login"} replace />} />
    </Routes>
  );
}

export default App;

