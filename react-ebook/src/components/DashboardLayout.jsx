import {
  BookOutlined,
  LogoutOutlined,
  SearchOutlined,
  ShoppingCartOutlined,
  SolutionOutlined,
  UserOutlined
} from "@ant-design/icons";
import { Avatar, Button, Input, Layout, Menu, Space, Typography } from "antd";
import { useLocation, useNavigate } from "react-router-dom";

// 后台主框架：把通用壳布局抽出来复用，页面只需要关注自己的业务内容。
// 这里统一管理侧边导航、顶部搜索、用户头像与退出按钮，children 用来承载各页面主体。
function DashboardLayout({
  children,
  username,
  onLogout,
  searchPlaceholder,
  searchValue,
  onSearchChange
}) {
  const location = useLocation();
  const navigate = useNavigate();

  // 使用 Ant Design Menu 统一侧边导航交互和激活态。
  const menuItems = [
    { key: "/books", icon: <BookOutlined />, label: "书城" },
    { key: "/cart", icon: <ShoppingCartOutlined />, label: "购物车" },
    { key: "/orders", icon: <SolutionOutlined />, label: "订单" },
    { key: "/user", icon: <UserOutlined />, label: "用户信息" }
  ];

  const selectedKey = menuItems.find((item) => location.pathname.startsWith(item.key))?.key || "/books";

  return (
    // 使用 Ant Design Layout 构建统一后台壳层，保留原有“侧栏+顶部+内容”布局语义。
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
          {/* 使用 Ant Design Input + Icon 承担全局搜索输入，仍保持原 onChange 触发 action 的数据流。 */}
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
