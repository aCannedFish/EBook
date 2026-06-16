import { Button, Card, Checkbox, Input, Space, Tabs, Typography } from "antd";
import { useState } from "react";
import { Form, Link, redirect, useActionData, useLoaderData, useSubmit } from "react-router-dom";
import { loginUser, registerUser } from "../api/backendApi";
import { getRememberedUsername, getSnapshot, setAuthenticatedUser } from "../data/appStore";
import { validateLoginForm, validateRegisterForm } from "../utils/validation";

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
    const message = validateLoginForm({ username, password });
    if (message) {
      return { status: "error", message };
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
      const user = await loginUser({ username: "DefaultUser", password: "123456" });
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
    const confirmPassword = String(formData.get("confirmPassword") || "").trim();
    const email = String(formData.get("email") || "").trim();
    const remember = formData.get("remember") === "on";
    const message = validateRegisterForm({ username, password, confirmPassword, email });
    if (message) {
      return { status: "error", message };
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
        message: error?.message === "username already exists"
          ? "用户名已存在，请更换用户名。"
          : error?.message === "email already exists"
            ? "邮箱已被注册。"
            : error?.message || "注册失败，请稍后重试。"
      };
    }
  }

  return null;
}

function LoginPage() {
  const loaderData = useLoaderData();
  const actionData = useActionData();
  const submit = useSubmit();
  const [username, setUsername] = useState(loaderData?.defaultUsername || "");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [email, setEmail] = useState("");
  const [remember, setRemember] = useState(false);

  const handleLogin = (event) => {
    event.preventDefault();
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

  const handleRegister = (event) => {
    event.preventDefault();
    submit(
      {
        intent: "register",
        username: username.trim(),
        password: password.trim(),
        confirmPassword: confirmPassword.trim(),
        email: email.trim(),
        remember: remember ? "on" : ""
      },
      { method: "post" }
    );
  };

  const handleGuest = () => {
    submit({ intent: "guest" }, { method: "post" });
  };

  const errorText = actionData?.status === "error" ? actionData.message : null;

  return (
    <main className="auth">
      <Card className="auth__panel card" aria-label="登录表单">
        <header className="brand">
          <figure className="brand__logo" aria-label="网站 Logo">
            <img src="/assets/logo.svg" alt="电子书城 Logo" width="42" height="42" />
          </figure>
          <div>
            <div className="brand__title"><span className="brand__welcome">欢迎登录</span> EBook电子书城</div>
          </div>
        </header>

        <Tabs
          className="u-mt-18"
          items={[
            {
              key: "login",
              label: "登录",
              children: (
                <Form method="post" onSubmit={handleLogin}>
                  <Space direction="vertical" size={12} className="auth-antd-form">
                    <div className="field">
                      <label className="field__label" htmlFor="username">用户名</label>
                      <Input
                        id="username"
                        placeholder="请输入用户名"
                        autoComplete="username"
                        value={username}
                        onChange={(event) => setUsername(event.target.value)}
                      />
                    </div>
                    <div className="field">
                      <label className="field__label" htmlFor="password">密码</label>
                      <Input.Password
                        id="password"
                        placeholder="请输入密码"
                        autoComplete="current-password"
                        value={password}
                        onChange={(event) => setPassword(event.target.value)}
                      />
                    </div>
                    <div className="auth__actions">
                      <Checkbox checked={remember} onChange={(event) => setRemember(event.target.checked)}>
                        Remember me
                      </Checkbox>
                      <Link className="link" to="/login">忘记密码？</Link>
                    </div>
                    <div className="auth__cta">
                      <Button type="primary" htmlType="submit">登录</Button>
                      <Button onClick={handleGuest}>体验账号（DefaultUser）</Button>
                    </div>
                    {errorText ? <Typography.Text type="danger">{errorText}</Typography.Text> : null}
                  </Space>
                </Form>
              )
            },
            {
              key: "register",
              label: "注册",
              children: (
                <Form method="post" onSubmit={handleRegister}>
                  <Space direction="vertical" size={12} className="auth-antd-form">
                    <div className="field">
                      <label className="field__label" htmlFor="reg-username">用户名</label>
                      <Input
                        id="reg-username"
                        placeholder="请输入用户名"
                        value={username}
                        onChange={(event) => setUsername(event.target.value)}
                      />
                    </div>
                    <div className="field">
                      <label className="field__label" htmlFor="reg-password">密码</label>
                      <Input.Password
                        id="reg-password"
                        placeholder="请输入密码"
                        value={password}
                        onChange={(event) => setPassword(event.target.value)}
                      />
                    </div>
                    <div className="field">
                      <label className="field__label" htmlFor="confirm-password">重复密码</label>
                      <Input.Password
                        id="confirm-password"
                        placeholder="请再次输入密码"
                        value={confirmPassword}
                        onChange={(event) => setConfirmPassword(event.target.value)}
                      />
                    </div>
                    <div className="field">
                      <label className="field__label" htmlFor="reg-email">邮箱</label>
                      <Input
                        id="reg-email"
                        type="email"
                        placeholder="请输入邮箱"
                        value={email}
                        onChange={(event) => setEmail(event.target.value)}
                      />
                    </div>
                    <div className="auth__cta">
                      <Button type="primary" htmlType="submit">注册并登录</Button>
                    </div>
                    {errorText ? <Typography.Text type="danger">{errorText}</Typography.Text> : null}
                  </Space>
                </Form>
              )
            }
          ]}
        />
      </Card>
    </main>
  );
}

export default LoginPage;
