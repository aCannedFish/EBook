package com.ebook.backend.dto;

/**
 * 更新购物车单行 API 请求体（PATCH 部分更新语义）。
 * <p>
 * {@link #qty}、{@link #selected} 均为可选：仅非 null 字段会写入数据库，
 * 由 {@link com.ebook.backend.service.CartService#updateCartItem} 处理。
 * </p>
 */
public class CartItemUpdateRequest {

    private Integer qty;

    private Boolean selected;

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
