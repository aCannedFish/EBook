import { Button, Space, Switch, Tag, Typography } from "antd";
import { useLoaderData, useSubmit } from "react-router-dom";
import ResourceTable from "../components/ResourceTable";
import { ensureAdminUsersLoaded, setPageSearch, toggleUserEnabled } from "../data/appStore";
import { requireAdminSnapshot } from "../routes/authRouteHandlers";

export async function adminUsersLoader() {
  requireAdminSnapshot();
  const users = await ensureAdminUsersLoaded(true);
  const snapshot = requireAdminSnapshot();
  return {
    users,
    search: snapshot.searchByPage.adminUsers
  };
}

export async function adminUsersAction({ request }) {
  requireAdminSnapshot();
  const formData = await request.formData();
  const intent = String(formData.get("intent") || "");

  if (intent === "set-search") {
    setPageSearch("adminUsers", String(formData.get("value") || ""));
    return null;
  }

  if (intent === "toggle-enabled") {
    const userId = Number(formData.get("userId"));
    const enabled = formData.get("enabled") === "true";
    if (userId) {
      await toggleUserEnabled(userId, enabled);
    }
    return null;
  }

  return null;
}

function AdminUsersPage({ users, search, onToggleEnabled }) {
  const keyword = search.trim().toLowerCase();
  const rows = users.filter((user) => {
    if (!keyword) {
      return true;
    }
    return `${user.username} ${user.email} ${user.level}`.toLowerCase().includes(keyword);
  });

  const columns = [
    { title: "用户名", dataIndex: "username" },
    { title: "邮箱", dataIndex: "email" },
    {
      title: "角色",
      dataIndex: "level",
      render: (level) => <Tag color={level === "管理员" ? "gold" : "blue"}>{level}</Tag>
    },
    {
      title: "状态",
      dataIndex: "enabled",
      render: (enabled) => (
        <Tag color={enabled ? "green" : "red"}>{enabled ? "正常" : "已禁用"}</Tag>
      )
    },
    {
      title: "操作",
      render: (_, row) => (
        <Switch
          checked={row.enabled}
          disabled={row.admin}
          checkedChildren="启用"
          unCheckedChildren="禁用"
          onChange={(checked) => onToggleEnabled(row.id, checked)}
        />
      )
    }
  ];

  return (
    <section className="page card" aria-label="用户管理页面">
      <header className="page__header">
        <Typography.Title level={3} className="page__title">用户管理</Typography.Title>
        <Tag>共 {rows.length} 人</Tag>
      </header>
      <ResourceTable rowKey="id" dataSource={rows} columns={columns} />
    </section>
  );
}

export function AdminUsersRoute() {
  const data = useLoaderData();
  const submit = useSubmit();

  return (
    <AdminUsersPage
      users={data.users}
      search={data.search}
      onToggleEnabled={(userId, enabled) =>
        submit({ intent: "toggle-enabled", userId, enabled }, { method: "post", navigate: false })
      }
    />
  );
}

export default AdminUsersPage;
