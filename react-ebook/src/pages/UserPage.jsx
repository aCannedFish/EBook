import { Link } from "react-router-dom";
import DashboardLayout from "../components/DashboardLayout";

function UserPage({ user, username, search, onSearchChange, onLogout }) {
  return (
    <DashboardLayout
      username={username}
      onLogout={onLogout}
      searchPlaceholder="搜索用户相关设置"
      searchValue={search}
      onSearchChange={onSearchChange}
    >
      <section className="page card" aria-label="用户信息页面">
        <header className="page__header">
          <div>
            <h1 className="page__title">个人资料</h1>
            <p className="page__desc">查看当前登录用户的基本信息。</p>
          </div>
          <div className="pill pill--ok">已登录</div>
        </header>

        <section className="grid" aria-label="用户信息内容">
          <section className="panel" aria-label="基本信息">
            <header className="panel__header">
              <h2 className="panel__title">基本信息</h2>
              <button className="btn btn-secondary" type="button">编辑</button>
            </header>
            <div className="panel__body">
              <table className="table" aria-label="用户信息表格">
                <tbody>
                  <tr className="table__row">
                    <th scope="row">用户名</th>
                    <td>{username}</td>
                  </tr>
                  <tr className="table__row">
                    <th scope="row">邮箱</th>
                    <td>{user.email}</td>
                  </tr>
                  <tr className="table__row">
                    <th scope="row">会员等级</th>
                    <td><span className="pill">{user.level}</span></td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          <section className="panel" aria-label="快捷入口">
            <header className="panel__header">
              <h2 className="panel__title">快捷入口</h2>
              <span className="tag tag--paid">UI 展示</span>
            </header>
            <div className="panel__body">
              <div className="summary__actions">
                <Link className="btn btn-secondary" to="/cart">我的购物车</Link>
                <Link className="btn btn-primary" to="/orders">我的订单</Link>
              </div>
            </div>
          </section>
        </section>
      </section>
    </DashboardLayout>
  );
}

export default UserPage;

