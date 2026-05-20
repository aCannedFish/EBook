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

/**
 * 订单 REST 接口。
 * <p>
 * 列表与状态更新均按 {@code userId} 隔离；订单业务主键为路径中的 {@code orderNo}（非表自增 id）。
 * 由 {@link OrderService} 访问 {@link com.ebook.backend.repository.OrderRepository}。
 * </p>
 */
@RestController
@RequestMapping("/api/v1/orders")
public class OrderController {

    /** 订单业务服务。 */
    private final OrderService orderService;

    /**
     * @param orderService 由 Spring 注入的 {@link OrderService}
     */
    public OrderController(OrderService orderService) {
        this.orderService = orderService;
    }

    /**
     * 查询用户订单，按创建时间倒序。
     *
     * @param userId 用户主键
     * @return 订单 DTO 列表
     */
    @GetMapping("/{userId}")
    public List<OrderResponse> getOrders(@PathVariable Long userId) {
        return orderService.getOrders(userId);
    }

    /**
     * 更新订单状态（pending / paid / cancelled）。
     *
     * @param userId  订单所属用户（用于校验归属）
     * @param orderNo 业务订单号，与 {@link OrderResponse#getId()} 一致
     * @param request 含新 status
     * @return 更新后的订单 DTO
     */
    @PatchMapping("/{userId}/{orderNo}")
    public OrderResponse updateStatus(@PathVariable Long userId,
                                      @PathVariable String orderNo,
                                      @Valid @RequestBody OrderStatusRequest request) {
        return orderService.updateStatus(userId, orderNo, request.getStatus());
    }
}
