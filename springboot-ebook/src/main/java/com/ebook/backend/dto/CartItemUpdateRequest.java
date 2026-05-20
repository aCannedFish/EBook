package com.ebook.backend.dto;

/**
 * 更新购物车单行 API 请求体（PATCH 部分更新语义）。
 * <p>
 * {@link #qty}、{@link #selected} 均为可选：仅非 null 字段会写入数据库，
 * 由 {@link com.ebook.backend.service.CartService#updateCartItem} 处理。
 * </p>
 */
public class CartItemUpdateRequest {

    /** 新数量；null 表示不修改；合法范围为 1～4。 */
    private Integer qty;

    /** 是否勾选结算；null 表示不修改。 */
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
