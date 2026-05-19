package com.ebook.backend.controller;

import com.ebook.backend.dto.OrderResponse;
import com.ebook.backend.dto.OrderStatusRequest;
import com.ebook.backend.service.OrderService;
import jakarta.validation.Valid;
import java.util.List;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/orders")
public class OrderController {

    private final OrderService orderService;

    public OrderController(OrderService orderService) {
        this.orderService = orderService;
    }

    @GetMapping("/{userId}")
    public List<OrderResponse> getOrders(@PathVariable Long userId) {
        return orderService.getOrders(userId);
    }

    @PatchMapping("/{userId}/{orderNo}")
    public OrderResponse updateStatus(@PathVariable Long userId,
                                      @PathVariable String orderNo,
                                      @Valid @RequestBody OrderStatusRequest request) {
        return orderService.updateStatus(userId, orderNo, request.getStatus());
    }
}
