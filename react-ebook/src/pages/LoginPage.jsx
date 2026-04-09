import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

function LoginPage({ onLogin }) {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(false);

  const handleSubmit = (event) => {
    event.preventDefault();
    if (!username.trim() || !password.trim()) {
      return;
    }

    onLogin(username.trim(), remember);
    navigate("/books");
  };

  const handleGuest = () => {
    const guestName = username.trim() || "同学A";
    onLogin(guestName, false);
    navigate("/books");
  };

  return (
    <main className="auth">
      <section className="auth__panel card" aria-label="登录表单">
        <header className="brand">
          <figure className="brand__logo" aria-label="网站 Logo">
            <img src="/logo.svg" alt="电子书城 Logo" width="42" height="42" />
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

