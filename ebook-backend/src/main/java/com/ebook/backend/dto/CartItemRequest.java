package com.ebook.backend.dto;

import jakarta.validation.constraints.NotNull;

/**
 * 加入购物车 API 请求体。
 * <p>
 * {@link #bookId} 对应 {@link com.ebook.backend.entity.Book#getId()}；
 * {@link #qty} 可选，缺省视为 1，在 {@link com.ebook.backend.service.CartService#addToCart} 中与已有数量累加。
 * </p>
 */
public class CartItemRequest {

    /** 要加入购物车的书籍主键，必填。 */
    @NotNull(message = "bookId is required")
    private Long bookId;

    /** 本次增加的数量；null 时按 1 处理。 */
    private Integer qty;

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
}
