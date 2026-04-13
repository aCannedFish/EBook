import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

// 登录页：提供账号登录、记住用户名和游客直达书城三种交互路径。
function LoginPage({ onLogin }) {
  // useNavigate 用于登录成功后跳转到书城页。
  const navigate = useNavigate();
  // username 保存用户名输入框的实时内容。
  const [username, setUsername] = useState("");
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

    // onLogin 由父组件提供，用于写入全局登录状态和用户名。
    onLogin(username.trim(), remember);
    // 登录成功后跳转到书城首页。
    navigate("/books");
  };

  // 游客模式：如果用户已经输入名字就沿用，否则给一个默认昵称。
  const handleGuest = () => {
    // || 是短路或：左侧为空字符串时，才使用默认值。
    const guestName = username.trim() || "同学A";
    onLogin(guestName, false);
    navigate("/books");
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

          <form onSubmit={handleSubmit}>
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
          </form>
        </section>
      </section>
    </main>
  );
}

export default LoginPage;

