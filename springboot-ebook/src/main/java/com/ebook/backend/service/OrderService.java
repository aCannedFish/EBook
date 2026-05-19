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

@Service
public class OrderService {

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

    public List<OrderResponse> getOrders(Long userId) {
        ensureUser(userId);
        return orderRepository.findByUserIdOrderByCreatedAtDesc(userId)
                .stream()
                .map(this::toResponse)
                .toList();
    }

    public OrderResponse updateStatus(Long userId, String orderNo, String status) {
        ensureUser(userId);
        if (!List.of("pending", "paid", "cancelled").contains(status)) {
            throw new IllegalArgumentException("invalid status");
        }
        OrderEntity order = orderRepository.findByOrderNoAndUserId(orderNo, userId)
                .orElseThrow(() -> new ResourceNotFoundException("order not found: " + orderNo));
        order.setStatus(status);
        return toResponse(orderRepository.save(order));
    }

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

    private void ensureUser(Long userId) {
        userRepository.findById(userId)
                .orElseThrow(() -> new ResourceNotFoundException("user not found: " + userId));
    }

    private String generateOrderNo(int index) {
        String timestamp = DateTimeFormatter.ofPattern("yyyyMMddHHmmss")
                .format(LocalDateTime.now());
        int suffix = ThreadLocalRandom.current().nextInt(1000, 9999);
        return String.format("ORD-%s-%04d-%d", timestamp, index, suffix);
    }

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
