package com.ebook.backend.dto;

import java.util.ArrayList;
import java.util.List;

/**
 * 顾客个人购书统计：指定时间范围内的明细与汇总。
 */
public class MyPurchaseStatResponse {

    private Integer totalQty;
    private Integer totalAmount;
    private List<MyPurchaseStatItemResponse> items = new ArrayList<>();

    public Integer getTotalQty() {
        return totalQty;
    }

    public void setTotalQty(Integer totalQty) {
        this.totalQty = totalQty;
    }

    public Integer getTotalAmount() {
        return totalAmount;
    }

    public void setTotalAmount(Integer totalAmount) {
        this.totalAmount = totalAmount;
    }

    public List<MyPurchaseStatItemResponse> getItems() {
        return items;
    }

    public void setItems(List<MyPurchaseStatItemResponse> items) {
        this.items = items;
    }
}
