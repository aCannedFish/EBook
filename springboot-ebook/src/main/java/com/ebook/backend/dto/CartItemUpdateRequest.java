package com.ebook.backend.dto;

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
