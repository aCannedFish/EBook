package com.ebook.backend.security;

import org.springframework.security.access.AccessDeniedException;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;

/** 将原有 URL 中的 userId/operatorId 与已认证身份绑定，防止客户端伪造用户编号。 */
@Component
public class CurrentUser {
    public BookstorePrincipal principal() {
        return (BookstorePrincipal) SecurityContextHolder.getContext().getAuthentication().getPrincipal();
    }

    /** 普通用户只能访问自己的资料、购物车、订单和统计；管理员可管理这些资源。 */
    public void requireSelf(Long id) {
        BookstorePrincipal user = principal();
        if (!user.admin() && !user.id().equals(id)) {
            throw new AccessDeniedException("不能访问其他用户的数据");
        }
    }

    /** 原有服务层保留 operatorId 参数，但实际值必须由当前登录管理员决定。 */
    public Long adminId(Long supplied) {
        BookstorePrincipal user = principal();
        if (!user.admin() || (supplied != null && !supplied.equals(user.id()))) {
            throw new AccessDeniedException("需要当前登录管理员身份");
        }
        return user.id();
    }
}
