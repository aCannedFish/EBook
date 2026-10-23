package com.ebook.backend.repository;

import com.ebook.backend.entity.OrderEntity;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.EntityGraph;
import org.springframework.data.jpa.repository.JpaRepository;

/**
 * 订单数据访问接口（Spring Data JPA）。
 */
public interface OrderRepository extends JpaRepository<OrderEntity, Long> {

    /**
     * 按用户查询订单（含明细），创建时间从新到旧。
     *
     * @param userId 用户主键
     * @return 订单列表
     */
    @EntityGraph(attributePaths = "items")
    List<OrderEntity> findByUserIdOrderByCreatedAtDesc(Long userId);

    /**
     * 按业务订单号与用户 id 定位订单（防止跨用户修改）。
     *
     * @param orderNo 业务订单号
     * @param userId  用户 id
     * @return 订单或 empty
     */
    @EntityGraph(attributePaths = "items")
    Optional<OrderEntity> findByOrderNoAndUserId(String orderNo, Long userId);

    /**
     * 管理员查询全部订单（含明细），创建时间从新到旧。
     */
    @EntityGraph(attributePaths = "items")
    List<OrderEntity> findAllByOrderByCreatedAtDesc();
}
