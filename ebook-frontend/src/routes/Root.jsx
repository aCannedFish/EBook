import { Outlet, useLoaderData, useMatches, useSubmit } from "react-router-dom";
import DashboardLayout from "../components/DashboardLayout";

// 从当前匹配链中获取“可搜索页面”的活跃子路由。
// 约定：可搜索路由在 route.handle 上声明 searchPlaceholder。
function getActiveSearchRoute(matches) {
  return [...matches]
    .reverse()
    .find(
      (match) =>
        match?.handle?.searchPlaceholder
        && match?.data
        && typeof match.data === "object"
        && "search" in match.data
    );
}

// ProtectedRootRoute：受保护业务区的共享布局路由。
// 与之前“每个页面自己包 DashboardLayout”不同，这里在父路由统一渲染一次 DashboardLayout，
// 子页面只渲染内容主体（通过 Outlet 插槽注入）。
export function ProtectedRootRoute() {
  const loaderData = useLoaderData();
  const submit = useSubmit();
  const matches = useMatches();
  const activeSearchRoute = getActiveSearchRoute(matches);

  return (
    <DashboardLayout
      username={loaderData?.username || ""}
      isAdmin={Boolean(loaderData?.isAdmin)}
      level={loaderData?.level || ""}
      onLogout={() => submit(null, { method: "post", action: "/logout" })}
      searchPlaceholder={activeSearchRoute?.handle?.searchPlaceholder || "搜索"}
      searchValue={activeSearchRoute?.data?.search || ""}
      onSearchChange={(value) =>
        submit(
          { intent: "set-search", value },
          { method: "post", action: activeSearchRoute?.pathname || "/books", navigate: false }
        )
      }
    >
      <Outlet />
    </DashboardLayout>
  );
}
