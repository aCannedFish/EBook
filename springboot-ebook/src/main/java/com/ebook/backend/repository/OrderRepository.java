package com.ebook.backend.repository;

import com.ebook.backend.entity.OrderEntity;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

/**
 * 订单数据访问接口（Spring Data JPA）。
 * <p>
 * 供 {@link com.ebook.backend.service.OrderService} 查询列表、按订单号更新状态及批量保存新订单。
 * </p>
 */
public interface OrderRepository extends JpaRepository<OrderEntity, Long> {

    /** 按用户查询，创建时间倒序（最新在前）。 */
    List<OrderEntity> findByUserIdOrderByCreatedAtDesc(Long userId);

    /** 按业务订单号 + 用户定位，防止跨用户误改。 */
    Optional<OrderEntity> findByOrderNoAndUserId(String orderNo, Long userId);
}
