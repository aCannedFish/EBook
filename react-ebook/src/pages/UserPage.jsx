import DashboardLayout from "../components/DashboardLayout";

// 用户中心页：展示当前登录账户的基本资料。
function UserPage({ user, username, search, onSearchChange, onLogout }) {
  // 继续复用后台布局，保证用户中心与其他页面拥有统一外壳。
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
        </section>
      </section>
    </DashboardLayout>
  );
}

export default UserPage;
