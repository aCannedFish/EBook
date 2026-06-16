package com.ebook.backend.dto;

import java.util.ArrayList;
import java.util.List;

/**
 * 订单 API 响应体。
 * <p>
 * {@link #id} 在业务上对应库表 {@code orders.order_no}（非自增主键 id），便于前端展示与 PATCH 路径一致；
 * {@link #items} 为同一结算批次下的书籍明细；{@link #totalPrice} 为明细行金额之和。
 * 由 {@link com.ebook.backend.service.OrderService} 组装。
 * </p>
 */
public class OrderResponse {

    /** 业务订单号，对应 {@link com.ebook.backend.entity.OrderEntity#getOrderNo()}。 */
    private String id;

    /** 订单状态：pending / paid / cancelled。 */
    private String status;

    /** 本单合计金额（各明细 qty × unitPrice 之和）。 */
    private Integer totalPrice;

    /** 同一批次下的书籍明细。 */
    private List<OrderItemResponse> items = new ArrayList<>();

    /** 下单用户 id（管理员查看全部订单时使用）。 */
    private Long userId;

    /** 下单用户名（管理员查看全部订单时使用）。 */
    private String username;

    /** 创建时间 ISO 字符串。 */
    private String createdAt;

    public String getId() {
        return id;
    }

    public void setId(String id) {
        this.id = id;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public Integer getTotalPrice() {
        return totalPrice;
    }

    public void setTotalPrice(Integer totalPrice) {
        this.totalPrice = totalPrice;
    }

    public List<OrderItemResponse> getItems() {
        return items;
    }

    public void setItems(List<OrderItemResponse> items) {
        this.items = items;
    }

    public Long getUserId() {
        return userId;
    }

    public void setUserId(Long userId) {
        this.userId = userId;
    }

    public String getUsername() {
        return username;
    }

    public void setUsername(String username) {
        this.username = username;
    }

    public String getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(String createdAt) {
        this.createdAt = createdAt;
    }
}
