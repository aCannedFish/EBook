package com.ebook.backend.dto;

/**
 * 顾客个人购书统计明细行。
 */
public class MyPurchaseStatItemResponse {

    private Long bookId;
    private String title;
    private Integer qty;
    private Integer amount;

    public Long getBookId() {
        return bookId;
    }

    public void setBookId(Long bookId) {
        this.bookId = bookId;
    }

    public String getTitle() {
        return title;
    }

    public void setTitle(String title) {
        this.title = title;
    }

    public Integer getQty() {
        return qty;
    }

    public void setQty(Integer qty) {
        this.qty = qty;
    }

    public Integer getAmount() {
        return amount;
    }

    public void setAmount(Integer amount) {
        this.amount = amount;
    }
}
