import { isRouteErrorResponse, useRouteError } from "react-router-dom";

// RouteErrorBoundary：路由级错误边界。
// 统一接收当前路由树抛出的异常，避免页面直接崩溃到白屏。
export default function RouteErrorBoundary() {
  // useRouteError 会返回当前路由上下文抛出的错误对象。
  const error = useRouteError();
  // 响应型错误（如 loader/action 抛出的 Response）可读取状态码与状态文案。
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

  // 其它运行时异常（非 Response）统一展示兜底提示。
  return (
    <main className="auth">
      <section className="auth__panel card">
        <h1>页面发生异常</h1>
        <p>请刷新后重试。</p>
      </section>
    </main>
  );
}
