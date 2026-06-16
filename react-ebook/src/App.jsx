import { RouterProvider, createBrowserRouter } from "react-router-dom";
import LoginPage, { loginAction, loginLoader } from "./pages/LoginPage";
import { BooksRoute, booksAction, booksLoader } from "./pages/BooksPage";
import { BookDetailRoute, bookDetailAction, bookDetailLoader } from "./pages/BookDetailPage";
import { CartRoute, cartAction, cartLoader } from "./pages/CartPage";
import {
  AdminOrdersRoute,
  OrdersRoute,
  adminOrdersAction,
  adminOrdersLoader,
  ordersAction,
  ordersLoader
} from "./pages/OrdersPage";
import { UserRoute, userAction, userLoader } from "./pages/UserPage";
import { AdminUsersRoute, adminUsersAction, adminUsersLoader } from "./pages/AdminUsersPage";
import { AdminBooksRoute, adminBooksAction, adminBooksLoader } from "./pages/AdminBooksPage";
import { StatsRoute, statsAction, statsLoader } from "./pages/StatsPage";
import { ProtectedRootRoute } from "./routes/Root";
import { authRedirectLoader, logoutAction, requireAuthLoader } from "./routes/authRouteHandlers";
import RouteErrorBoundary from "./routes/RouteErrorBoundary";

const router = createBrowserRouter([
  {
    path: "/",
    errorElement: <RouteErrorBoundary />,
    children: [
      {
        index: true,
        loader: authRedirectLoader
      },
      {
        path: "login",
        loader: loginLoader,
        action: loginAction,
        element: <LoginPage />
      },
      {
        path: "logout",
        action: logoutAction
      },
      {
        loader: requireAuthLoader,
        element: <ProtectedRootRoute />,
        children: [
          {
            path: "books",
            loader: booksLoader,
            action: booksAction,
            handle: { searchPlaceholder: "搜索书名 / 作者 / 分类" },
            element: <BooksRoute />
          },
          {
            path: "books/:bookId",
            loader: bookDetailLoader,
            action: bookDetailAction,
            handle: { searchPlaceholder: "搜索其他书籍" },
            element: <BookDetailRoute />
          },
          {
            path: "cart",
            loader: cartLoader,
            action: cartAction,
            handle: { searchPlaceholder: "搜索购物车中的书籍" },
            element: <CartRoute />
          },
          {
            path: "orders",
            loader: ordersLoader,
            action: ordersAction,
            handle: { searchPlaceholder: "搜索订单号或书名" },
            element: <OrdersRoute />
          },
          {
            path: "admin/orders",
            loader: adminOrdersLoader,
            action: adminOrdersAction,
            handle: { searchPlaceholder: "搜索全部订单" },
            element: <AdminOrdersRoute />
          },
          {
            path: "admin/users",
            loader: adminUsersLoader,
            action: adminUsersAction,
            handle: { searchPlaceholder: "搜索用户名或邮箱" },
            element: <AdminUsersRoute />
          },
          {
            path: "admin/books",
            loader: adminBooksLoader,
            action: adminBooksAction,
            handle: { searchPlaceholder: "按书名搜索图书" },
            element: <AdminBooksRoute />
          },
          {
            path: "stats",
            loader: statsLoader,
            action: statsAction,
            handle: { searchPlaceholder: "搜索统计结果" },
            element: <StatsRoute />
          },
          {
            path: "user",
            loader: userLoader,
            action: userAction,
            handle: { searchPlaceholder: "搜索用户相关设置" },
            element: <UserRoute />
          }
        ]
      },
      {
        path: "*",
        loader: authRedirectLoader
      }
    ]
  }
]);

function App() {
  return <RouterProvider router={router} />;
}

export default App;
