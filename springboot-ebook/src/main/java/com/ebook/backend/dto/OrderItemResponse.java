package com.ebook.backend.dto;

/**
 * 订单明细 API 响应体。
 * <p>
 * 由 {@link com.ebook.backend.service.OrderService} 从 {@link com.ebook.backend.entity.OrderItem} 组装。
 * </p>
 */
public class OrderItemResponse {

    /** 所购书籍 id。 */
    private Long bookId;

    /** 购买数量。 */
    private Integer qty;

    /** 下单时单价快照。 */
    private Integer unitPrice;

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
