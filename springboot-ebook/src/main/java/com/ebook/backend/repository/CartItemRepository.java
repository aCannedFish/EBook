package com.ebook.backend.repository;

import com.ebook.backend.entity.CartItem;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

/**
 * 购物车行数据访问接口（Spring Data JPA）。
 * <p>
 * 与表 {@code cart_items} 及唯一键 {@code (user_id, book_id)} 对应；
 * 供 {@link com.ebook.backend.service.CartService} 完成加购、更新、删除与结算前查询。
 * </p>
 */
public interface CartItemRepository extends JpaRepository<CartItem, Long> {

    List<CartItem> findByUserId(Long userId);

    Optional<CartItem> findByUserIdAndBookId(Long userId, Long bookId);

    void deleteByUserIdAndBookId(Long userId, Long bookId);
}
