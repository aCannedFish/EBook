package com.ebook.backend.dto;

/**
 * 热销榜统计项：指定时间范围内某书的销量与销售额。
 */
public class BookSalesStatResponse {

    private Long bookId;
    private String title;
    private Integer totalQty;
    private Integer totalAmount;

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
}
