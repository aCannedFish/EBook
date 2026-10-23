package com.ebook.backend.service.support;

import com.ebook.backend.entity.User;
import com.ebook.backend.exception.ResourceNotFoundException;
import com.ebook.backend.repository.UserRepository;

/**
 * 管理员权限校验工具，供 Admin/Stats 等服务复用。
 */
public final class AdminGuard {

    public static final String ADMIN_LEVEL = "管理员";

    private AdminGuard() {
    }

    /**
     * 校验操作者存在且为管理员。
     */
    public static User ensureAdmin(UserRepository userRepository, Long operatorId) {
        User operator = userRepository.findById(operatorId)
                .orElseThrow(() -> new ResourceNotFoundException("user not found: " + operatorId));
        if (!isAdmin(operator)) {
            throw new IllegalArgumentException("admin permission required");
        }
        return operator;
    }

    public static boolean isAdmin(User user) {
        return user != null && ADMIN_LEVEL.equals(user.getLevel());
    }
}
