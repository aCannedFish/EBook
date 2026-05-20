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
 * </p>
 */
@Service
public class OrderService {

    /** 允许写入数据库的订单状态枚举值。 */
    private static final List<String> ALLOWED_STATUSES = List.of("pending", "paid", "cancelled");

    /** 订单表仓储。 */
    private final OrderRepository orderRepository;

    /** 校验用户存在。 */
    private final UserRepository userRepository;

    /** 创建订单时读取书名对应价格。 */
    private final BookRepository bookRepository;

    /**
     * @param orderRepository 订单仓储
     * @param userRepository  用户仓储
     * @param bookRepository  图书仓储
     */
    public OrderService(OrderRepository orderRepository,
                        UserRepository userRepository,
                        BookRepository bookRepository) {
        this.orderRepository = orderRepository;
        this.userRepository = userRepository;
        this.bookRepository = bookRepository;
    }

    /**
     * 查询用户全部订单，按 {@code created_at} 降序。
     *
     * @param userId 用户主键
     * @return 订单 DTO 列表
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
     *
     * @param userId  用户 id
     * @param orderNo 业务订单号
     * @param status  新状态
     * @return 更新后的订单 DTO
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
        return orderRepository.saveAll(orders)
                .stream()
                .map(this::toResponse)
                .toList();
    }

    /**
     * @param userId 用户 id
     */
    private void ensureUser(Long userId) {
        userRepository.findById(userId)
                .orElseThrow(() -> new ResourceNotFoundException("user not found: " + userId));
    }

    /**
     * 生成业务订单号。
     *
     * @param index 同一批次内的序号，从 1 递增
     * @return 形如 ORD-20260519120000-0001-4521 的字符串
     */
    private String generateOrderNo(int index) {
        String timestamp = DateTimeFormatter.ofPattern("yyyyMMddHHmmss")
                .format(LocalDateTime.now());
        int suffix = ThreadLocalRandom.current().nextInt(1000, 9999);
        return String.format("ORD-%s-%04d-%d", timestamp, index, suffix);
    }

    /**
     * @param order 订单实体
     * @return API 用 DTO，id 字段为 orderNo
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
