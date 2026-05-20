package com.ebook.backend.service;

import com.ebook.backend.dto.OrderResponse;
import com.ebook.backend.entity.Book;
import com.ebook.backend.entity.CartItem;
import com.ebook.backend.entity.OrderEntity;
import com.ebook.backend.exception.ResourceNotFoundException;
import com.ebook.backend.repository.BookRepository;
import com.ebook.backend.repository.OrderRepository;
import com.ebook.backend.repository.UserRepository;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ThreadLocalRandom;
import org.springframework.stereotype.Service;

/**
 * 订单业务服务。
 * <p>
 * 被 {@link com.ebook.backend.controller.OrderController} 与 {@link CartService#checkout} 调用；
 * 通过 {@link OrderRepository} 持久化 {@link OrderEntity}。
 * 每条购物车结算行生成一条订单（一书一单），单价取自下单瞬间的 {@link Book#getPrice()}。
 * </p>
 */
@Service
public class OrderService {

    private static final List<String> ALLOWED_STATUSES = List.of("pending", "paid", "cancelled");

    private final OrderRepository orderRepository;
    private final UserRepository userRepository;
    private final BookRepository bookRepository;

    public OrderService(OrderRepository orderRepository,
                        UserRepository userRepository,
                        BookRepository bookRepository) {
        this.orderRepository = orderRepository;
        this.userRepository = userRepository;
        this.bookRepository = bookRepository;
    }

    /**
     * 查询用户全部订单，按 {@code created_at} 降序（Repository 方法名推导排序）。
     */
    public List<OrderResponse> getOrders(Long userId) {
        ensureUser(userId);
        return orderRepository.findByUserIdOrderByCreatedAtDesc(userId)
                .stream()
                .map(this::toResponse)
                .toList();
    }

    /**
     * 更新订单状态；订单必须属于该 userId。
     */
    public OrderResponse updateStatus(Long userId, String orderNo, String status) {
        ensureUser(userId);
        if (!ALLOWED_STATUSES.contains(status)) {
            throw new IllegalArgumentException("invalid status");
        }
        OrderEntity order = orderRepository.findByOrderNoAndUserId(orderNo, userId)
                .orElseThrow(() -> new ResourceNotFoundException("order not found: " + orderNo));
        order.setStatus(status);
        return toResponse(orderRepository.save(order));
    }

    /**
     * 根据购物车已选行批量创建订单（供结算调用）。
     * <p>
     * 每个 {@link CartItem} 对应一条 {@link OrderEntity}；
     * {@link OrderEntity#setUnitPrice} 为价格快照，避免日后改书价影响历史订单。
     * </p>
     *
     * @param userId 下单用户
     * @param items  已勾选的购物车行，非空
     * @return 已持久化的订单 DTO 列表
     */
    public List<OrderResponse> createOrders(Long userId, List<CartItem> items) {
        ensureUser(userId);
        if (items == null || items.isEmpty()) {
            return List.of();
        }

        List<OrderEntity> orders = new ArrayList<>();
        int index = 1;
        for (CartItem item : items) {
            Book book = bookRepository.findById(item.getBookId())
                    .orElseThrow(() -> new ResourceNotFoundException("book not found: " + item.getBookId()));
            OrderEntity order = new OrderEntity();
            order.setOrderNo(generateOrderNo(index));
            order.setUserId(userId);
            order.setBookId(book.getId());
            order.setQty(item.getQty());
            order.setUnitPrice(book.getPrice());
            order.setStatus("pending");
            orders.add(order);
            index += 1;
        }
        // saveAll：Spring Data JPA 批量 INSERT，返回带生成 id 的实体列表
        return orderRepository.saveAll(orders)
                .stream()
                .map(this::toResponse)
                .toList();
    }

    private void ensureUser(Long userId) {
        userRepository.findById(userId)
                .orElseThrow(() -> new ResourceNotFoundException("user not found: " + userId));
    }

    /**
     * 生成业务订单号：时间戳 + 批次内序号 + 随机后缀，降低同秒冲突概率。
     * 格式示例：{@code ORD-20260519120000-0001-4521}
     */
    private String generateOrderNo(int index) {
        String timestamp = DateTimeFormatter.ofPattern("yyyyMMddHHmmss")
                .format(LocalDateTime.now());
        int suffix = ThreadLocalRandom.current().nextInt(1000, 9999);
        return String.format("ORD-%s-%04d-%d", timestamp, index, suffix);
    }

    /**
     * 将 {@link OrderEntity} 转为 API DTO；对外 {@code id} 使用 {@link OrderEntity#getOrderNo()}。
     */
    private OrderResponse toResponse(OrderEntity order) {
        OrderResponse response = new OrderResponse();
        response.setId(order.getOrderNo());
        response.setStatus(order.getStatus());
        response.setBookId(order.getBookId());
        response.setQty(order.getQty());
        response.setUnitPrice(order.getUnitPrice());
        return response;
    }
}
