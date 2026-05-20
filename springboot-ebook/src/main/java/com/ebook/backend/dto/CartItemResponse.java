package com.ebook.backend.dto;

/**
 * 购物车单行 API 响应体。
 * <p>
 * 仅含前端拼表所需字段；书名、价格由前端用 {@link #bookId} 关联已加载的书目列表。
 * 由 {@link com.ebook.backend.service.CartService} 从 {@link com.ebook.backend.entity.CartItem} 转换。
 * </p>
 */
public class CartItemResponse {

    /** 书籍主键，用于 join 书目信息。 */
    private Long bookId;

    /** 该行购买数量。 */
    private Integer qty;

    /** 是否勾选参与结算。 */
    private Boolean selected;

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

    public Boolean getSelected() {
        return selected;
    }

    public void setSelected(Boolean selected) {
        this.selected = selected;
    }
}
