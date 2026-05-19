import { Button, Card, Checkbox, Input, Space, Typography } from "antd";
import { useState } from "react";
import { Form, Link, redirect, useActionData, useLoaderData, useSubmit } from "react-router-dom";
import { loginUser, registerUser } from "../api/backendApi";
import { getRememberedUsername, getSnapshot, setAuthenticatedUser } from "../data/appStore";

export async function loginLoader() {
  const snapshot = getSnapshot();
  if (snapshot.isLoggedIn) {
    throw redirect("/books");
  }
  return {
    defaultUsername: getRememberedUsername()
  };
}

export async function loginAction({ request }) {
  const formData = await request.formData();
  const intent = String(formData.get("intent") || "");

  if (intent === "login") {
    const username = String(formData.get("username") || "").trim();
    const password = String(formData.get("password") || "").trim();
    const remember = formData.get("remember") === "on";
    if (!username || !password) {
      return {
        status: "error",
        message: "请输入用户名和密码。"
      };
    }
    try {
      const user = await loginUser({ username, password });
      setAuthenticatedUser(user, remember);
      throw redirect("/books");
    } catch (error) {
      return {
        status: "error",
        message: error?.message || "登录失败，请检查账号和密码。"
      };
    }
  }

  if (intent === "guest") {
    try {
      const user = await loginUser({ username: "同学A", password: "123456" });
      setAuthenticatedUser(user, false);
      throw redirect("/books");
    } catch (error) {
      return {
        status: "error",
        message: error?.message || "体验账号不可用，请使用注册登录。"
      };
    }
  }

  if (intent === "register") {
    const username = String(formData.get("username") || "").trim();
    const password = String(formData.get("password") || "").trim();
    const email = String(formData.get("email") || "").trim();
    const remember = formData.get("remember") === "on";
    if (!username || !password || !email) {
      return {
        status: "error",
        message: "用户名、密码和邮箱不能为空。"
      };
    }

    try {
      const user = await registerUser({
        username,
        password,
        email,
        signature: "",
        level: "普通用户"
      });
      setAuthenticatedUser(user, remember);
      throw redirect("/books");
    } catch (error) {
      return {
        status: "error",
        message: error?.message || "注册失败，请稍后重试。"
      };
    }
  }

  return null;
}

// 登录页：提供账号登录、记住用户名和游客直达书城三种交互路径。
function LoginPage() {
  // loaderData 由 /login 的 loader 返回（见 App.jsx -> loginLoader）。
  const loaderData = useLoaderData();
  const actionData = useActionData();
  // submit 用于命令式触发当前路由 action（等价于提交 Form）。
  const submit = useSubmit();
  // username 保存用户名输入框的实时内容。
  const [username, setUsername] = useState(loaderData?.defaultUsername || "");
  // password 保存密码输入框的实时内容，当前示例不做后端校验。
  const [password, setPassword] = useState("");
  // remember 控制“记住我”复选框状态，决定是否写入本地存储。
  const [remember, setRemember] = useState(false);
  const [email, setEmail] = useState("");

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
      {/* 使用 Ant Design Card 作为登录容器，统一表单视觉结构。 */}
      <Card className="auth__panel card" aria-label="登录表单">
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
            <Typography.Title level={4}>登录</Typography.Title>
          </header>

          {/* Form 默认提交到当前路由（/login）对应 action。 */}
          <Form method="post" onSubmit={handleSubmit}>
            <Space direction="vertical" size={12} className="auth-antd-form">
              <div className="field">
                <label className="field__label" htmlFor="username">用户名</label>
                {/* 使用 Ant Design Input 提升输入框一致性和可维护性。 */}
                <Input
                  id="username"
                  placeholder="请输入用户名"
                  autoComplete="username"
                  value={username}
                  onChange={(event) => setUsername(event.target.value)}
                  required
                />
              </div>

              <div className="field">
                <label className="field__label" htmlFor="password">密码</label>
                {/* 使用 Ant Design Password 输入框内置可见性切换与反馈样式。 */}
                <Input.Password
                  id="password"
                  placeholder="请输入密码"
                  autoComplete="current-password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  required
                />
              </div>

              <div className="field">
                <label className="field__label" htmlFor="email">邮箱（用于注册）</label>
                <Input
                  id="email"
                  type="email"
                  placeholder="请输入邮箱"
                  autoComplete="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                />
              </div>

              <div className="auth__actions">
                <Checkbox
                  id="remember"
                  checked={remember}
                  onChange={(event) => setRemember(event.target.checked)}
                >
                  Remember me
                </Checkbox>
                <Link className="link" to="/login" aria-label="忘记密码入口">忘记密码？</Link>
              </div>

              <div className="auth__cta">
                <Button type="primary" htmlType="submit">登录</Button>
                <Button onClick={handleGuest}>直接进入书城</Button>
                <Button
                  onClick={() =>
                    submit(
                      {
                        intent: "register",
                        username: username.trim(),
                        password: password.trim(),
                        email: email.trim(),
                        remember: remember ? "on" : ""
                      },
                      { method: "post" }
                    )
                  }
                >
                  注册并登录
                </Button>
              </div>
              {actionData?.status === "error" ? (
                <Typography.Text type="danger">{actionData.message}</Typography.Text>
              ) : null}
            </Space>
          </Form>
        </section>
      </Card>
    </main>
  );
}

export default LoginPage;
