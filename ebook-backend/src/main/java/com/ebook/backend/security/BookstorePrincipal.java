package com.ebook.backend.security;

/** JWT 验证后的书城身份；用户编号来自已验签的 sub，权限来自当前用户记录。 */
public record BookstorePrincipal(Long id, String username, boolean admin) {
}
