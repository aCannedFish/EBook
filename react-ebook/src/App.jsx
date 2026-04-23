import { RouterProvider, createBrowserRouter } from "react-router-dom";
import LoginPage, { loginAction, loginLoader } from "./pages/LoginPage";
import { BooksRoute, booksAction, booksLoader } from "./pages/BooksPage";
import { BookDetailRoute, bookDetailAction, bookDetailLoader } from "./pages/BookDetailPage";
import { CartRoute, cartAction, cartLoader } from "./pages/CartPage";
import { OrdersRoute, ordersAction, ordersLoader } from "./pages/OrdersPage";
import { UserRoute, userAction, userLoader } from "./pages/UserPage";
import { ProtectedRootRoute } from "./routes/Root";
import { authRedirectLoader, logoutAction, requireAuthLoader } from "./routes/authRouteHandlers";
import RouteErrorBoundary from "./routes/RouteErrorBoundary";

// =========================
// 路由装配层（App 入口）
// =========================
// 本文件只承担两项职责：
// 1) 定义并装配整站路由树（createBrowserRouter）；
// 2) 在 App 组件中挂载 RouterProvider。
//
// 业务数据读取与写入（loader/action）已下沉到各模块文件，
// 这里仅做“路由关系与模块拼装”。
const router = createBrowserRouter([
  {
    // 顶层 Root：承载全站 children，并统一挂错误边界。
    path: "/",
    errorElement: <RouteErrorBoundary />,
    children: [
      {
        // 访问 "/" 时按登录态分流到 /books 或 /login。
        index: true,
        loader: authRedirectLoader
      },
      {
        // 登录页路由：loader/action 归属于 LoginPage 模块。
        path: "login",
        loader: loginLoader,
        action: loginAction,
        element: <LoginPage />
      },
      {
        // 退出动作路由：仅 action，无页面 element。
        path: "logout",
        action: logoutAction
      },
      {
        // 受保护父路由：通过 requireAuthLoader 统一做登录校验。
        loader: requireAuthLoader,
        element: <ProtectedRootRoute />,
        children: [
          {
            path: "books",
            loader: booksLoader,
            action: booksAction,
            handle: {
              searchPlaceholder: "搜索书名 / 作者 / 分类"
            },
            element: <BooksRoute />
          },
          {
            path: "books/:bookId",
            loader: bookDetailLoader,
            action: bookDetailAction,
            handle: {
              searchPlaceholder: "搜索其他书籍"
            },
            element: <BookDetailRoute />
          },
          {
            path: "cart",
            loader: cartLoader,
            action: cartAction,
            handle: {
              searchPlaceholder: "搜索购物车中的书籍"
            },
            element: <CartRoute />
          },
          {
            path: "orders",
            loader: ordersLoader,
            action: ordersAction,
            handle: {
              searchPlaceholder: "搜索订单号或书名"
            },
            element: <OrdersRoute />
          },
          {
            path: "user",
            loader: userLoader,
            action: userAction,
            handle: {
              searchPlaceholder: "搜索用户相关设置"
            },
            element: <UserRoute />
          }
        ]
      },
      {
        // 未匹配路径兜底：同样走登录态分流逻辑。
        path: "*",
        loader: authRedirectLoader
      }
    ]
  }
]);

// App 仅作为路由提供者壳，不承载业务状态。
function App() {
  return <RouterProvider router={router} />;
}

export default App;
