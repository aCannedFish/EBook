import { NavLink } from "react-router-dom";

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
  return (
    <div className="app">
      {/* 左侧栏：承载品牌入口、主导航和退出操作。 */}
      <aside className="sidebar" aria-label="侧栏导航">
        {/* 品牌区：点击 Logo 可以回到书城首页。 */}
        <div className="sidebar__brand">
          <NavLink className="brand" to="/books" aria-label="返回书城首页">
            <figure className="brand__logo">
              <img src="/logo.svg" alt="电子书城 Logo" width="42" height="42" />
            </figure>
            <div>
              <div className="brand__title">EBook电子书城</div>
            </div>
          </NavLink>
        </div>

        {/* 主导航：NavLink 会自动根据当前路由添加激活样式。 */}
        <nav className="nav" aria-label="页面导航">
          <NavLink to="/books" className={({ isActive }) => `nav__item${isActive ? " is-active" : ""}`}>
            <span className="nav__dot" aria-hidden="true"></span>
            <span>书城</span>
          </NavLink>
          <NavLink to="/cart" className={({ isActive }) => `nav__item${isActive ? " is-active" : ""}`}>
            <span className="nav__dot" aria-hidden="true"></span>
            <span>购物车</span>
          </NavLink>
          <NavLink to="/orders" className={({ isActive }) => `nav__item${isActive ? " is-active" : ""}`}>
            <span className="nav__dot" aria-hidden="true"></span>
            <span>订单</span>
          </NavLink>
          <NavLink to="/user" className={({ isActive }) => `nav__item${isActive ? " is-active" : ""}`}>
            <span className="nav__dot" aria-hidden="true"></span>
            <span>用户信息</span>
          </NavLink>
          <button type="button" className="nav__item nav__button" onClick={onLogout}>
            <span className="nav__dot" aria-hidden="true"></span>
            <span>退出（返回登录）</span>
          </button>
        </nav>
      </aside>

      {/* 主区域：顶部工具栏 + 页面内容容器。 */}
      <main className="main">
        {/* 顶栏：包含本地搜索和当前登录用户信息。 */}
        <header className="topbar" aria-label="顶栏">
          <div className="topbar__left">
            {/* 顶部搜索只是前端筛选，不会提交表单，所以 onSubmit 里直接 preventDefault。 */}
            <form className="search" onSubmit={(event) => event.preventDefault()} aria-label="搜索">
              <span className="u-muted-2" aria-hidden="true">⌕</span>
              <label className="u-sr-only" htmlFor="global-q">搜索</label>
              <input
                id="global-q"
                type="search"
                placeholder={searchPlaceholder}
                value={searchValue}
                onChange={(event) => onSearchChange(event.target.value)}
              />
            </form>
          </div>
          <div className="topbar__right">
            {/* 用户区：展示头像与用户名，帮助区分当前登录身份。 */}
            <div className="avatar" aria-label="用户信息">
              <img className="avatar__img" src="/avatar.svg" alt="用户头像" width="30" height="30" />
              <div className="avatar__name">{username}</div>
            </div>
          </div>
        </header>

        {/* children 是插槽式内容：不同页面把自己的主体内容放进来。 */}
        {children}
      </main>
    </div>
  );
}

export default DashboardLayout;

