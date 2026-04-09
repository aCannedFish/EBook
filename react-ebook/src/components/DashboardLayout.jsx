import { NavLink } from "react-router-dom";

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
      <aside className="sidebar" aria-label="侧栏导航">
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

      <main className="main">
        <header className="topbar" aria-label="顶栏">
          <div className="topbar__left">
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
            <div className="avatar" aria-label="用户信息">
              <img className="avatar__img" src="/avatar.svg" alt="用户头像" width="30" height="30" />
              <div className="avatar__name">{username}</div>
            </div>
          </div>
        </header>

        {children}
      </main>
    </div>
  );
}

export default DashboardLayout;

