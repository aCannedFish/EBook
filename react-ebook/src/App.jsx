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

  // Routes 负责声明应用内所有页面的地址映射。
  return (
    <Routes>
      {/* 根路径根据登录状态自动跳转到登录页或书城页。 */}
      <Route
        path="/"
        element={<Navigate to={isLoggedIn ? "/books" : "/login"} replace />}
      />
      {/* 登录页对未登录用户开放。 */}
      <Route path="/login" element={<LoginPage onLogin={handleLogin} />} />

      {/* 受保护路由：下面这些页面都要求先登录。 */}
      <Route element={<ProtectedRoute isLoggedIn={isLoggedIn} />}>
        {/* 书城首页：展示所有书籍并允许加入购物车。 */}
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
        {/* 详情页：根据 bookId 展示单本书完整信息。 */}
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
        {/* 购物车页：支持勾选、改数量和结算。 */}
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
        {/* 订单页：可以查看订单状态并执行付款/取消/再次购买。 */}
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
        {/* 用户中心页：展示账户信息和快捷入口。 */}
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

      {/* 兜底路由：任何未知地址都会被重定向回合适的首页。 */}
      <Route path="*" element={<Navigate to={isLoggedIn ? "/books" : "/login"} replace />} />
    </Routes>
  );
}

export default App;

