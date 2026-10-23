package com.ebook.backend.repository;

import com.ebook.backend.entity.User;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

/**
 * 用户数据访问接口（Spring Data JPA）。
 */
public interface UserRepository extends JpaRepository<User, Long> {

    /**
     * 按登录名查询，用于登录与注册唯一性校验。
     *
     * @param username 用户名
     * @return 匹配的用户，无则 empty
     */
    Optional<User> findByUsername(String username);

    /**
     * 按邮箱查询，用于注册/改资料时的唯一性校验。
     *
     * @param email 邮箱
     * @return 匹配的用户，无则 empty
     */
    Optional<User> findByEmail(String email);
}
