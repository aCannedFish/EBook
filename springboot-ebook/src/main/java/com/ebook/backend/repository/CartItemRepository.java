package com.ebook.backend.repository;

import com.ebook.backend.entity.CartItem;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

/**
 * 购物车行数据访问接口（Spring Data JPA）。
 */
public interface CartItemRepository extends JpaRepository<CartItem, Long> {

    /**
     * 查询某用户的全部购物车行。
     *
     * @param userId 用户主键
     * @return 购物车实体列表
     */
    List<CartItem> findByUserId(Long userId);

    /**
     * 查询某用户下指定书籍的购物车行（加购 UPSERT 用）。
     *
     * @param userId 用户 id
     * @param bookId 书籍 id
     * @return 唯一一行或 empty
     */
    Optional<CartItem> findByUserIdAndBookId(Long userId, Long bookId);

    /**
     * 删除某用户下指定书籍的购物车行。
     *
     * @param userId 用户 id
     * @param bookId 书籍 id
     */
    void deleteByUserIdAndBookId(Long userId, Long bookId);
}
