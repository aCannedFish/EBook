package com.ebook.backend.repository;

import com.ebook.backend.entity.User;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

/**
 * 用户数据访问接口（Spring Data JPA）。
 * <p>
 * 自定义方法由方法名解析生成查询（如 {@code findByUsername} → {@code WHERE username = ?}）。
 * 供 {@link com.ebook.backend.service.UserService} 及购物车/订单中的用户存在性校验使用。
 * </p>
 */
public interface UserRepository extends JpaRepository<User, Long> {

    Optional<User> findByUsername(String username);

    Optional<User> findByEmail(String email);
}
