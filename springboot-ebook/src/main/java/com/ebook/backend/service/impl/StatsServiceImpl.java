package com.ebook.backend.service.impl;

import com.ebook.backend.dto.BookSalesStatResponse;
import com.ebook.backend.dto.MyPurchaseStatItemResponse;
import com.ebook.backend.dto.MyPurchaseStatResponse;
import com.ebook.backend.dto.UserSpendingStatResponse;
import com.ebook.backend.entity.Book;
import com.ebook.backend.entity.OrderEntity;
import com.ebook.backend.entity.OrderItem;
import com.ebook.backend.entity.User;
import com.ebook.backend.exception.ResourceNotFoundException;
import com.ebook.backend.repository.BookRepository;
import com.ebook.backend.repository.OrderRepository;
import com.ebook.backend.repository.UserRepository;
import com.ebook.backend.service.StatsService;
import com.ebook.backend.service.support.AdminGuard;
import java.time.LocalDateTime;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import org.springframework.stereotype.Service;

/**
 * {@link StatsService} 的 Spring 实现。
 */
@Service
public class StatsServiceImpl implements StatsService {

    private final OrderRepository orderRepository;
    private final UserRepository userRepository;
    private final BookRepository bookRepository;

    public StatsServiceImpl(OrderRepository orderRepository,
                            UserRepository userRepository,
                            BookRepository bookRepository) {
        this.orderRepository = orderRepository;
        this.userRepository = userRepository;
        this.bookRepository = bookRepository;
    }

    @Override
    public List<BookSalesStatResponse> bookSalesRanking(Long operatorId,
                                                      LocalDateTime from,
                                                      LocalDateTime to) {
        AdminGuard.ensureAdmin(userRepository, operatorId);
        Map<Long, BookSalesStatResponse> stats = new HashMap<>();
        for (OrderEntity order : eligibleOrders(from, to, null)) {
            for (OrderItem item : order.getItems()) {
                BookSalesStatResponse row = stats.computeIfAbsent(item.getBookId(), bookId -> {
                    BookSalesStatResponse created = new BookSalesStatResponse();
                    created.setBookId(bookId);
                    Book book = bookRepository.findById(bookId).orElse(null);
                    created.setTitle(book == null ? "未知书籍" : book.getTitle());
                    created.setTotalQty(0);
                    created.setTotalAmount(0);
                    return created;
                });
                row.setTotalQty(row.getTotalQty() + item.getQty());
                row.setTotalAmount(row.getTotalAmount() + item.getQty() * item.getUnitPrice());
            }
        }
        return stats.values().stream()
                .sorted(Comparator.comparing(BookSalesStatResponse::getTotalQty).reversed())
                .toList();
    }

    @Override
    public List<UserSpendingStatResponse> userSpendingRanking(Long operatorId,
                                                              LocalDateTime from,
                                                              LocalDateTime to) {
        AdminGuard.ensureAdmin(userRepository, operatorId);
        Map<Long, UserSpendingStatResponse> stats = new HashMap<>();
        Map<Long, String> usernames = userRepository.findAll().stream()
                .collect(java.util.stream.Collectors.toMap(User::getId, User::getUsername));

        for (OrderEntity order : eligibleOrders(from, to, null)) {
            UserSpendingStatResponse row = stats.computeIfAbsent(order.getUserId(), userId -> {
                UserSpendingStatResponse created = new UserSpendingStatResponse();
                created.setUserId(userId);
                created.setUsername(usernames.getOrDefault(userId, "未知用户"));
                created.setTotalQty(0);
                created.setTotalAmount(0);
                return created;
            });
            for (OrderItem item : order.getItems()) {
                row.setTotalQty(row.getTotalQty() + item.getQty());
                row.setTotalAmount(row.getTotalAmount() + item.getQty() * item.getUnitPrice());
            }
        }
        return stats.values().stream()
                .sorted(Comparator.comparing(UserSpendingStatResponse::getTotalAmount).reversed())
                .toList();
    }

    @Override
    public MyPurchaseStatResponse myPurchaseStats(Long userId, LocalDateTime from, LocalDateTime to) {
        userRepository.findById(userId)
                .orElseThrow(() -> new ResourceNotFoundException("user not found: " + userId));

        Map<Long, MyPurchaseStatItemResponse> stats = new HashMap<>();
        for (OrderEntity order : eligibleOrders(from, to, userId)) {
            for (OrderItem item : order.getItems()) {
                MyPurchaseStatItemResponse row = stats.computeIfAbsent(item.getBookId(), bookId -> {
                    MyPurchaseStatItemResponse created = new MyPurchaseStatItemResponse();
                    created.setBookId(bookId);
                    Book book = bookRepository.findById(bookId).orElse(null);
                    created.setTitle(book == null ? "未知书籍" : book.getTitle());
                    created.setQty(0);
                    created.setAmount(0);
                    return created;
                });
                row.setQty(row.getQty() + item.getQty());
                row.setAmount(row.getAmount() + item.getQty() * item.getUnitPrice());
            }
        }

        MyPurchaseStatResponse response = new MyPurchaseStatResponse();
        response.setItems(stats.values().stream()
                .sorted(Comparator.comparing(MyPurchaseStatItemResponse::getQty).reversed())
                .toList());
        response.setTotalQty(response.getItems().stream().mapToInt(MyPurchaseStatItemResponse::getQty).sum());
        response.setTotalAmount(response.getItems().stream().mapToInt(MyPurchaseStatItemResponse::getAmount).sum());
        return response;
    }

    private List<OrderEntity> eligibleOrders(LocalDateTime from, LocalDateTime to, Long userId) {
        List<OrderEntity> orders = userId == null
                ? orderRepository.findAllByOrderByCreatedAtDesc()
                : orderRepository.findByUserIdOrderByCreatedAtDesc(userId);
        return orders.stream()
                .filter(order -> !"cancelled".equals(order.getStatus()))
                .filter(order -> matchesDateRange(order, from, to))
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
}
