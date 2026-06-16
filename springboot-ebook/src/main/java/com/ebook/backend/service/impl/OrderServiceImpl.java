package com.ebook.backend.service.impl;

import com.ebook.backend.dto.OrderItemResponse;
import com.ebook.backend.dto.OrderResponse;
import com.ebook.backend.entity.Book;
import com.ebook.backend.entity.CartItem;
import com.ebook.backend.entity.OrderEntity;
import com.ebook.backend.entity.OrderItem;
import com.ebook.backend.entity.User;
import com.ebook.backend.exception.ResourceNotFoundException;
import com.ebook.backend.repository.BookRepository;
import com.ebook.backend.repository.OrderRepository;
import com.ebook.backend.repository.UserRepository;
import com.ebook.backend.service.OrderService;
import com.ebook.backend.service.support.AdminGuard;
import com.ebook.backend.service.support.StockHelper;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ThreadLocalRandom;
import java.util.stream.Collectors;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * {@link OrderService} 的 Spring 实现。
 */
@Service
public class OrderServiceImpl implements OrderService {

    private static final List<String> ALLOWED_STATUSES = List.of("pending", "paid", "cancelled");
    private static final DateTimeFormatter ISO_FORMATTER = DateTimeFormatter.ISO_LOCAL_DATE_TIME;

    private final OrderRepository orderRepository;
    private final UserRepository userRepository;
    private final BookRepository bookRepository;

    public OrderServiceImpl(OrderRepository orderRepository,
                            UserRepository userRepository,
                            BookRepository bookRepository) {
        this.orderRepository = orderRepository;
        this.userRepository = userRepository;
        this.bookRepository = bookRepository;
    }

    @Override
    public List<OrderResponse> getOrders(Long userId, LocalDateTime from, LocalDateTime to, String bookTitle) {
        ensureUser(userId);
        List<OrderEntity> orders = orderRepository.findByUserIdOrderByCreatedAtDesc(userId);
        return filterAndMapOrders(orders, from, to, bookTitle, false);
    }

    @Override
    public List<OrderResponse> getAllOrdersForAdmin(Long operatorId,
                                                    LocalDateTime from,
                                                    LocalDateTime to,
                                                    String bookTitle) {
        AdminGuard.ensureAdmin(userRepository, operatorId);
        List<OrderEntity> orders = orderRepository.findAllByOrderByCreatedAtDesc();
        Map<Long, String> usernames = userRepository.findAll().stream()
                .collect(Collectors.toMap(User::getId, User::getUsername));
        return filterAndMapOrders(orders, from, to, bookTitle, true).stream()
                .peek(order -> order.setUsername(usernames.get(order.getUserId())))
                .toList();
    }

    @Override
    public OrderResponse updateStatus(Long userId, String orderNo, String status) {
        ensureUser(userId);
        if (!ALLOWED_STATUSES.contains(status)) {
            throw new IllegalArgumentException("invalid status");
        }
        OrderEntity order = orderRepository.findByOrderNoAndUserId(orderNo, userId)
                .orElseThrow(() -> new ResourceNotFoundException("order not found: " + orderNo));
        order.setStatus(status);
        return toResponse(orderRepository.save(order), false);
    }

    @Override
    @Transactional
    public List<OrderResponse> createOrders(Long userId, List<CartItem> items) {
        ensureUser(userId);
        if (items == null || items.isEmpty()) {
            return List.of();
        }

        for (CartItem item : items) {
            Book book = bookRepository.findById(item.getBookId())
                    .orElseThrow(() -> new ResourceNotFoundException("book not found: " + item.getBookId()));
            if (book.getStockQty() == null || book.getStockQty() < item.getQty()) {
                throw new IllegalArgumentException("insufficient stock for: " + book.getTitle());
            }
        }

        OrderEntity order = new OrderEntity();
        order.setOrderNo(generateOrderNo());
        order.setUserId(userId);
        order.setStatus("pending");

        for (CartItem item : items) {
            Book book = bookRepository.findById(item.getBookId())
                    .orElseThrow(() -> new ResourceNotFoundException("book not found: " + item.getBookId()));
            book.setStockQty(book.getStockQty() - item.getQty());
            StockHelper.syncStockDisplay(book);
            bookRepository.save(book);

            OrderItem line = new OrderItem();
            line.setBookId(book.getId());
            line.setQty(item.getQty());
            line.setUnitPrice(book.getPrice());
            order.addItem(line);
        }

        OrderEntity saved = orderRepository.save(order);
        return List.of(toResponse(saved, false));
    }

    private List<OrderResponse> filterAndMapOrders(List<OrderEntity> orders,
                                                   LocalDateTime from,
                                                   LocalDateTime to,
                                                   String bookTitle,
                                                   boolean includeUserId) {
        String titleKeyword = bookTitle == null ? "" : bookTitle.trim().toLowerCase();
        return orders.stream()
                .filter(order -> matchesDateRange(order, from, to))
                .map(order -> toResponse(order, includeUserId))
                .filter(order -> matchesBookTitle(order, titleKeyword))
                .sorted(Comparator.comparing(OrderResponse::getCreatedAt,
                        Comparator.nullsLast(Comparator.reverseOrder())))
                .toList();
    }

    private boolean matchesDateRange(OrderEntity order, LocalDateTime from, LocalDateTime to) {
        LocalDateTime createdAt = order.getCreatedAt();
        if (createdAt == null) {
            return true;
        }
        if (from != null && createdAt.isBefore(from)) {
            return false;
        }
        if (to != null && createdAt.isAfter(to)) {
            return false;
        }
        return true;
    }

    private boolean matchesBookTitle(OrderResponse order, String titleKeyword) {
        if (titleKeyword.isEmpty()) {
            return true;
        }
        return order.getItems().stream().anyMatch(item -> {
            Book book = bookRepository.findById(item.getBookId()).orElse(null);
            return book != null && book.getTitle().toLowerCase().contains(titleKeyword);
        });
    }

    private void ensureUser(Long userId) {
        userRepository.findById(userId)
                .orElseThrow(() -> new ResourceNotFoundException("user not found: " + userId));
    }

    private String generateOrderNo() {
        String timestamp = DateTimeFormatter.ofPattern("yyyyMMddHHmmss")
                .format(LocalDateTime.now());
        int suffix = ThreadLocalRandom.current().nextInt(1000, 9999);
        return String.format("ORD-%s-%d", timestamp, suffix);
    }

    private OrderResponse toResponse(OrderEntity order, boolean includeUserId) {
        OrderResponse response = new OrderResponse();
        response.setId(order.getOrderNo());
        response.setStatus(order.getStatus());
        if (includeUserId) {
            response.setUserId(order.getUserId());
        }
        if (order.getCreatedAt() != null) {
            response.setCreatedAt(ISO_FORMATTER.format(order.getCreatedAt()));
        }
        List<OrderItemResponse> itemResponses = order.getItems().stream()
                .map(this::toItemResponse)
                .toList();
        response.setItems(itemResponses);
        response.setTotalPrice(itemResponses.stream()
                .mapToInt(item -> item.getQty() * item.getUnitPrice())
                .sum());
        return response;
    }

    private OrderItemResponse toItemResponse(OrderItem item) {
        OrderItemResponse response = new OrderItemResponse();
        response.setBookId(item.getBookId());
        response.setQty(item.getQty());
        response.setUnitPrice(item.getUnitPrice());
        return response;
    }
}
