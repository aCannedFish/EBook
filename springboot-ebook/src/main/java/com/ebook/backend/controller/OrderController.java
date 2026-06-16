package com.ebook.backend.controller;

import com.ebook.backend.dto.OrderResponse;
import com.ebook.backend.dto.OrderStatusRequest;
import com.ebook.backend.service.OrderService;
import jakarta.validation.Valid;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.LocalTime;
import java.util.List;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * 订单 REST 接口。
 */
@RestController
@RequestMapping("/api/v1/orders")
public class OrderController {

    private final OrderService orderService;

    public OrderController(OrderService orderService) {
        this.orderService = orderService;
    }

    @GetMapping("/{userId}")
    public List<OrderResponse> getOrders(@PathVariable Long userId,
                                         @RequestParam(required = false)
                                         @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate from,
                                         @RequestParam(required = false)
                                         @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate to,
                                         @RequestParam(required = false) String bookTitle) {
        return orderService.getOrders(userId, toStart(from), toEnd(to), bookTitle);
    }

    @GetMapping("/admin/all")
    public List<OrderResponse> getAllOrdersForAdmin(@RequestParam Long operatorId,
                                                    @RequestParam(required = false)
                                                    @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate from,
                                                    @RequestParam(required = false)
                                                    @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate to,
                                                    @RequestParam(required = false) String bookTitle) {
        return orderService.getAllOrdersForAdmin(operatorId, toStart(from), toEnd(to), bookTitle);
    }

    @PatchMapping("/{userId}/{orderNo}")
    public OrderResponse updateStatus(@PathVariable Long userId,
                                      @PathVariable String orderNo,
                                      @Valid @RequestBody OrderStatusRequest request) {
        return orderService.updateStatus(userId, orderNo, request.getStatus());
    }

    private LocalDateTime toStart(LocalDate date) {
        return date == null ? null : date.atStartOfDay();
    }

    private LocalDateTime toEnd(LocalDate date) {
        return date == null ? null : date.atTime(LocalTime.MAX);
    }
}
