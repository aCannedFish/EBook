package com.ebook.backend.service;

import com.ebook.backend.dto.OrderResponse;
import com.ebook.backend.entity.CartItem;
import java.time.LocalDateTime;
import java.util.List;

/**
 * 订单业务服务接口。
 */
public interface OrderService {

    List<OrderResponse> getOrders(Long userId, LocalDateTime from, LocalDateTime to, String bookTitle);

    List<OrderResponse> getAllOrdersForAdmin(Long operatorId, LocalDateTime from, LocalDateTime to, String bookTitle);

    OrderResponse updateStatus(Long userId, String orderNo, String status);

    List<OrderResponse> createOrders(Long userId, List<CartItem> items);
}
