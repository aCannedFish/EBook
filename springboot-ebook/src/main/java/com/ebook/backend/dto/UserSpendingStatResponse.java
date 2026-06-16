package com.ebook.backend.dto;

/**
 * 消费榜统计项：指定时间范围内某用户的累计购书金额。
 */
public class UserSpendingStatResponse {

    private Long userId;
    private String username;
    private Integer totalAmount;
    private Integer totalQty;

    public Long getUserId() {
        return userId;
    }

    public void setUserId(Long userId) {
        this.userId = userId;
    }

    public String getUsername() {
        return username;
    }

    public void setUsername(String username) {
        this.username = username;
    }

    public Integer getTotalAmount() {
        return totalAmount;
    }

    public void setTotalAmount(Integer totalAmount) {
        this.totalAmount = totalAmount;
    }

    public Integer getTotalQty() {
        return totalQty;
    }

    public void setTotalQty(Integer totalQty) {
        this.totalQty = totalQty;
    }
}
