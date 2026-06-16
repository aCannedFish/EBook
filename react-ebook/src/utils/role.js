/** 判断当前用户是否为管理员。 */
export function isAdmin(user) {
  return Boolean(user?.admin) || user?.level === "管理员";
}

/** 根据角色返回侧栏菜单项 key 列表。 */
export function getMenuKeysForRole(admin) {
  const common = ["/books", "/cart", "/orders", "/stats", "/user"];
  if (admin) {
    return ["/books", "/admin/books", "/admin/users", "/orders", "/admin/orders", "/stats", "/user"];
  }
  return common;
}
