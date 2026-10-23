package com.ebook.backend.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

/**
 * 购物车行实体，映射表 {@code cart_items}。
 * <p>
 * 同一 {@link #userId} 与 {@link #bookId} 在表上有唯一约束，保证每用户每书仅一行；
 * {@link #selected} 表示结算时是否勾选。由 {@link com.ebook.backend.service.CartService} 读写。
 * </p>
 */
@Entity
@Table(name = "cart_items")
public class CartItem {

    /** 购物车行主键，自增。 */
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    /** 所属用户 id，外键逻辑关联 {@link User#getId()}。 */
    @Column(nullable = false)
    private Long userId;

    /** 书籍 id，外键逻辑关联 {@link Book#getId()}。 */
    @Column(nullable = false)
    private Long bookId;

    /** 购买数量，业务上限 4（在 Service 层 enforced）。 */
    @Column(nullable = false)
    private Integer qty;

    /** 是否参与结算；true 的行在 checkout 时转为订单。 */
    @Column(nullable = false)
    private Boolean selected;

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public Long getUserId() {
        return userId;
    }

    public void setUserId(Long userId) {
        this.userId = userId;
    }

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
