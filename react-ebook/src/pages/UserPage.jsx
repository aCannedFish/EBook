import { Form, useActionData, useLoaderData } from "react-router-dom";
import { setPageSearch, updateUserProfile } from "../data/appStore";
import { requireAuthSnapshot } from "../routes/authRouteHandlers";

export async function userLoader() {
  const snapshot = requireAuthSnapshot();
  return {
    user: snapshot.user,
    username: snapshot.user.username,
    search: snapshot.searchByPage.user
  };
}

export async function userAction({ request }) {
  requireAuthSnapshot();
  const formData = await request.formData();
  const intent = String(formData.get("intent") || "");
  if (intent === "set-search") {
    setPageSearch("user", String(formData.get("value") || ""));
    return null;
  }

  if (intent === "update-profile") {
    const username = String(formData.get("username") || "").trim();
    const email = String(formData.get("email") || "").trim();
    const signature = String(formData.get("signature") || "").trim();

    if (!username || !email) {
      return {
        status: "error",
        message: "用户名和邮箱不能为空。"
      };
    }

    updateUserProfile({ username, email, signature });
    return {
      status: "success",
      message: "个人信息已更新。"
    };
  }

  return null;
}

// 用户中心页：展示并允许编辑当前登录账户的基本资料。
function UserPage({ user, username, actionData }) {
  return (
    <section className="page card" aria-label="用户信息页面">
      <header className="page__header">
        <div>
          <h1 className="page__title">个人资料</h1>
        </div>
        <div className="pill pill--ok">已登录</div>
      </header>

      <section className="grid" aria-label="用户信息内容">
        <section className="panel" aria-label="基本信息">
          <header className="panel__header">
            <h2 className="panel__title">基本信息</h2>
            <button className="btn btn-secondary" type="submit" form="profile-form">提交</button>
          </header>
          <div className="panel__body">
            <Form id="profile-form" method="post" className="profile-form">
              <input type="hidden" name="intent" value="update-profile" />
              <table className="table" aria-label="用户信息表格">
                <tbody>
                  <tr className="table__row">
                    <th scope="row">用户名</th>
                    <td>
                      <input className="input" name="username" defaultValue={username} required />
                    </td>
                  </tr>
                  <tr className="table__row">
                    <th scope="row">邮箱</th>
                    <td>
                      <input className="input" name="email" type="email" defaultValue={user.email} required />
                    </td>
                  </tr>
                  <tr className="table__row">
                    <th scope="row">个性签名</th>
                    <td>
                      <textarea
                        className="input profile-form__textarea"
                        name="signature"
                        defaultValue={user.signature || ""}
                        placeholder="介绍一下自己吧"
                      />
                    </td>
                  </tr>
                  <tr className="table__row">
                    <th scope="row">会员等级</th>
                    <td><span className="pill">{user.level}</span></td>
                  </tr>
                </tbody>
              </table>
              {actionData?.message && (
                <p className={`profile-form__hint ${actionData.status === "error" ? "profile-form__hint--error" : "profile-form__hint--ok"}`}>
                  {actionData.message}
                </p>
              )}
            </Form>
          </div>
        </section>
      </section>
    </section>
  );
}

export function UserRoute() {
  const data = useLoaderData();
  const actionData = useActionData();

  return (
    <UserPage
      user={data.user}
      username={data.username}
      actionData={actionData}
    />
  );
}

export default UserPage;
