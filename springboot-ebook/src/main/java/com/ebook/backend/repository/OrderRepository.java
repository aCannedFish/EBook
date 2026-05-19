package com.ebook.backend.repository;

import com.ebook.backend.entity.OrderEntity;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface OrderRepository extends JpaRepository<OrderEntity, Long> {
    List<OrderEntity> findByUserIdOrderByCreatedAtDesc(Long userId);
    Optional<OrderEntity> findByOrderNoAndUserId(String orderNo, Long userId);
}
