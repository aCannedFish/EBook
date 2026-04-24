import { Alert, Button, Card, Input, Space, Tag, Typography } from "antd";
import { Form as RouterForm, useActionData, useLoaderData } from "react-router-dom";
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
            <Button type="default" htmlType="submit" form="profile-form">提交</Button>
          </header>
          <div className="panel__body">
            <RouterForm id="profile-form" method="post" className="profile-form">
              <input type="hidden" name="intent" value="update-profile" />
              <Card size="small" bordered={false}>
                <Space direction="vertical" size={16} className="profile-form__stack">
                  <div className="profile-form__field">
                    <Typography.Text type="secondary">用户名</Typography.Text>
                    <Input name="username" defaultValue={username} required />
                  </div>
                  <div className="profile-form__field">
                    <Typography.Text type="secondary">邮箱</Typography.Text>
                    <Input name="email" type="email" defaultValue={user.email} required />
                  </div>
                  <div className="profile-form__field">
                    <Typography.Text type="secondary">个性签名</Typography.Text>
                    <Input.TextArea
                      name="signature"
                      defaultValue={user.signature || ""}
                      placeholder="介绍一下自己吧"
                      autoSize={{ minRows: 3, maxRows: 6 }}
                    />
                  </div>
                  <div className="profile-form__field">
                    <Typography.Text type="secondary">会员等级</Typography.Text>
                    <div><Tag color="green">{user.level}</Tag></div>
                  </div>
                </Space>
              </Card>
              {actionData?.message && (
                <Alert
                  type={actionData.status === "error" ? "error" : "success"}
                  message={actionData.message}
                  showIcon
                />
              )}
            </RouterForm>
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
