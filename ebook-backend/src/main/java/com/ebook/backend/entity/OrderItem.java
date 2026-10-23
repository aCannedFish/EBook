package com.ebook.backend.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;

/**
 * 订单明细行，映射表 {@code order_items}。
 * <p>
 * 同一 {@link OrderEntity} 下可有多条明细，表示一次结算批次中的多本书；
 * 持久化通过 {@link OrderEntity} 的级联保存，不单独配置 Repository。
 * </p>
 */
@Entity
@Table(name = "order_items")
public class OrderItem {

    /** 明细主键。 */
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    /** 所属订单头。 */
    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "order_id", nullable = false)
    private OrderEntity order;

    /** 所购书籍 id。 */
    @Column(name = "book_id", nullable = false)
    private Long bookId;

    /** 购买数量。 */
    @Column(nullable = false)
    private Integer qty;

    /** 下单时单价快照。 */
    @Column(name = "unit_price", nullable = false)
    private Integer unitPrice;

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public OrderEntity getOrder() {
        return order;
    }

    public void setOrder(OrderEntity order) {
        this.order = order;
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

    public Integer getUnitPrice() {
        return unitPrice;
    }

    public void setUnitPrice(Integer unitPrice) {
        this.unitPrice = unitPrice;
    }
}
