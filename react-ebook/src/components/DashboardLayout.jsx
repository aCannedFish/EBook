import {
  BarChartOutlined,
  BookOutlined,
  LogoutOutlined,
  SearchOutlined,
  ShoppingCartOutlined,
  SolutionOutlined,
  TeamOutlined,
  UserOutlined
} from "@ant-design/icons";
import { Avatar, Button, Input, Layout, Menu, Space, Tag, Typography } from "antd";
import { useLocation, useNavigate } from "react-router-dom";

function DashboardLayout({
  children,
  username,
  isAdmin,
  level,
  onLogout,
  searchPlaceholder,
  searchValue,
  onSearchChange
}) {
  const location = useLocation();
  const navigate = useNavigate();

  const customerItems = [
    { key: "/books", icon: <BookOutlined />, label: "书城" },
    { key: "/cart", icon: <ShoppingCartOutlined />, label: "购物车" },
    { key: "/orders", icon: <SolutionOutlined />, label: "我的订单" },
    { key: "/stats", icon: <BarChartOutlined />, label: "购书统计" },
    { key: "/user", icon: <UserOutlined />, label: "用户信息" }
  ];

  const adminItems = [
    { key: "/books", icon: <BookOutlined />, label: "书城浏览" },
    { key: "/admin/books", icon: <BookOutlined />, label: "书籍管理" },
    { key: "/admin/users", icon: <TeamOutlined />, label: "用户管理" },
    { key: "/orders", icon: <SolutionOutlined />, label: "我的订单" },
    { key: "/admin/orders", icon: <SolutionOutlined />, label: "全部订单" },
    { key: "/stats", icon: <BarChartOutlined />, label: "数据统计" },
    { key: "/user", icon: <UserOutlined />, label: "用户信息" }
  ];

  const menuItems = isAdmin ? adminItems : customerItems;
  const selectedKey = menuItems.find((item) => location.pathname.startsWith(item.key))?.key || "/books";

  return (
    <Layout className="antd-shell">
      <Layout.Sider width={230} className="antd-shell__sider">
        <div className="antd-shell__brand" role="button" tabIndex={0} onClick={() => navigate("/books")} onKeyDown={(event) => event.key === "Enter" && navigate("/books")}>
          <img src="/assets/logo.svg" alt="电子书城 Logo" width="34" height="34" />
        </div>
        <Menu
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
        <Button className="antd-shell__logout" icon={<LogoutOutlined />} onClick={onLogout}>
          退出（返回登录）
        </Button>
      </Layout.Sider>
      <Layout>
        <Layout.Header className="antd-shell__header">
          <Input
            allowClear
            className="antd-shell__search"
            prefix={<SearchOutlined />}
            placeholder={searchPlaceholder}
            value={searchValue}
            onChange={(event) => onSearchChange(event.target.value)}
          />
          <Space>
            <Avatar size={30} icon={<UserOutlined />} />
            <Typography.Text>{username}</Typography.Text>
            {isAdmin ? <Tag color="gold">管理员</Tag> : <Tag color="blue">{level || "顾客"}</Tag>}
          </Space>
        </Layout.Header>
        <Layout.Content className="antd-shell__content">
          {children}
        </Layout.Content>
      </Layout>
    </Layout>
  );
}

export default DashboardLayout;
