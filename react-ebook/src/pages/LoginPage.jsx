import { useState } from "react";
import { Form, Link, useLoaderData, useSubmit } from "react-router-dom";

// 登录页：提供账号登录、记住用户名和游客直达书城三种交互路径。
function LoginPage() {
  // loaderData 由 /login 的 loader 返回（见 App.jsx -> loginLoader）。
  const loaderData = useLoaderData();
  // submit 用于命令式触发当前路由 action（等价于提交 Form）。
  const submit = useSubmit();
  // username 保存用户名输入框的实时内容。
  const [username, setUsername] = useState(loaderData?.defaultUsername || "");
  // password 保存密码输入框的实时内容，当前示例不做后端校验。
  const [password, setPassword] = useState("");
  // remember 控制“记住我”复选框状态，决定是否写入本地存储。
  const [remember, setRemember] = useState(false);

  // 提交表单：先阻止默认刷新，再做最基础的非空校验，最后通知上层更新登录态。
  const handleSubmit = (event) => {
    event.preventDefault();
    // trim 用来去掉前后空格，避免只输入空白字符被视为有效内容。
    if (!username.trim() || !password.trim()) {
      return;
    }

    // 这里不直接调用登录 API，而是提交到当前路由 action。
    // action 会根据 intent=login 执行登录逻辑并 redirect 到 /books。
    submit(
      {
        intent: "login",
        username: username.trim(),
        password: password.trim(),
        remember: remember ? "on" : ""
      },
      { method: "post" }
    );
  };

  // 游客模式：如果用户已经输入名字就沿用，否则给一个默认昵称。
  const handleGuest = () => {
    // || 是短路或：左侧为空字符串时，才使用默认值。
    const guestName = username.trim() || "同学A";
    // 游客登录同样走路由 action，保持“写操作统一在 action 中处理”的架构约束。
    submit(
      {
        intent: "guest",
        username: guestName
      },
      { method: "post" }
    );
  };

  // main 表示当前页面的主内容区域。
  return (
    <main className="auth">
      <section className="auth__panel card" aria-label="登录表单">
        <header className="brand">
          <figure className="brand__logo" aria-label="网站 Logo">
            <img src="/assets/logo.svg" alt="电子书城 Logo" width="42" height="42" />
          </figure>
          <div>
            <div className="brand__title"><span className="brand__welcome">欢迎登录</span> EBook电子书城</div>
          </div>
        </header>

        <section className="u-mt-18">
          <header>
            <h1>登录</h1>
          </header>

          {/* Form 默认提交到当前路由（/login）对应 action。 */}
          <Form method="post" onSubmit={handleSubmit}>
            <div className="field">
              <label className="field__label" htmlFor="username">用户名</label>
              <input
                className="input"
                id="username"
                type="text"
                placeholder="请输入用户名"
                autoComplete="username"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                required
              />
            </div>

            <div className="field u-mt-12">
              <label className="field__label" htmlFor="password">密码</label>
              <input
                className="input"
                id="password"
                type="password"
                placeholder="请输入密码"
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
              />
            </div>

            <div className="auth__actions">
              <label className="auth__checks" htmlFor="remember">
                <input
                  id="remember"
                  type="checkbox"
                  checked={remember}
                  onChange={(event) => setRemember(event.target.checked)}
                />
                Remember me
              </label>
              <Link className="link" to="/login" aria-label="忘记密码入口">忘记密码？</Link>
            </div>

            <div className="auth__cta">
              <button className="btn btn-primary" type="submit">登录</button>
              <button className="btn btn-secondary" type="button" onClick={handleGuest}>直接进入书城</button>
            </div>
          </Form>
        </section>
      </section>
    </main>
  );
}

export default LoginPage;
