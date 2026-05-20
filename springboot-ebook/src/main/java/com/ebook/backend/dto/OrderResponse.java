package com.ebook.backend.dto;

/**
 * 订单 API 响应体。
 * <p>
 * {@link #id} 在业务上对应库表 {@code orders.order_no}（非自增主键 id），便于前端展示与 PATCH 路径一致；
 * 由 {@link com.ebook.backend.service.OrderService} 组装。
 * </p>
 */
public class OrderResponse {

    private String id;
    private String status;
    private Long bookId;
    private Integer qty;
    private Integer unitPrice;

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

    public Long getBookId() {
        return bookId;
    }

    public void setBookId(Long bookId) {
        this.bookId = bookId;
    }

    public Integer getQty() {
        return qty;
    }

    public void setQty(Integer qty) {
        this.qty = qty;
    }

    public Integer getUnitPrice() {
        return unitPrice;
    }

    public void setUnitPrice(Integer unitPrice) {
        this.unitPrice = unitPrice;
    }
}
