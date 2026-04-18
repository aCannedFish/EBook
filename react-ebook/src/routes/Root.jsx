import { Outlet, useLocation, useMatches, useSubmit } from "react-router-dom";
import DashboardLayout from "../components/DashboardLayout";

// RootRoute：全站根布局路由。
// 当前版本不渲染额外 UI，仅作为 children 的承载容器。
// 后续若需要全局壳（如主题容器、全局提示等），可优先在这里扩展。
export function RootRoute() {
  return <Outlet />;
}

// 按当前路径返回顶部搜索框占位文案。
// 这样可以把“页面级搜索提示语”从各页面组件统一收敛到共享布局层。
function getSearchPlaceholder(pathname) {
  if (pathname === "/books") {
    return "搜索书名 / 作者 / 分类";
  }
  if (pathname.startsWith("/books/")) {
    return "搜索其他书籍";
  }
  if (pathname.startsWith("/cart")) {
    return "搜索购物车中的书籍";
  }
  if (pathname.startsWith("/orders")) {
    return "搜索订单号或书名";
  }
  if (pathname.startsWith("/user")) {
    return "搜索用户相关设置";
  }
  return "搜索";
}

// 从当前匹配链中，取最深层业务页 loader 的通用数据（username/search）。
// 业务页 loader 都返回这两个字段，因此这里可以统一提取供共享布局使用。
function readDashboardData(matches) {
  const activeMatch = [...matches]
    .reverse()
    .find((match) => match?.data && typeof match.data === "object" && "username" in match.data && "search" in match.data);
  return {
    username: activeMatch?.data?.username || "",
    search: activeMatch?.data?.search || ""
  };
}

// ProtectedRootRoute：受保护业务区的共享布局路由。
// 与之前“每个页面自己包 DashboardLayout”不同，这里在父路由统一渲染一次 DashboardLayout，
// 子页面只渲染内容主体（通过 Outlet 插槽注入）。
export function ProtectedRootRoute() {
  const submit = useSubmit();
  const location = useLocation();
  const matches = useMatches();
  const dashboardData = readDashboardData(matches);

  return (
    <DashboardLayout
      username={dashboardData.username}
      onLogout={() => submit(null, { method: "post", action: "/logout" })}
      searchPlaceholder={getSearchPlaceholder(location.pathname)}
      searchValue={dashboardData.search}
      onSearchChange={(value) =>
        submit({ intent: "set-search", value }, { method: "post", action: location.pathname, navigate: false })
      }
    >
      <Outlet />
    </DashboardLayout>
  );
}
