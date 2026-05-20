package com.ebook.backend.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.LocalDateTime;

/**
 * 订单实体，映射表 {@code orders}（类名避免与 SQL 关键字及模块歧义）。
 * <p>
 * {@link #orderNo} 为业务订单号，对外 API 的 {@link com.ebook.backend.dto.OrderResponse#getId()} 即此字段；
 * {@link #unitPrice} 为下单时从 {@link Book#getPrice()} 复制的快照；
 * {@link #createdAt} 由数据库默认时间戳填充（insertable/updatable=false）。
 * </p>
 */
@Entity
@Table(name = "orders")
public class OrderEntity {

    /** 表主键，自增；对外业务标识使用 {@link #orderNo}。 */
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    /** 业务订单号，唯一，如 ORD-20260519120000-0001-4521。 */
    @Column(name = "order_no", nullable = false, unique = true, length = 40)
    private String orderNo;

    /** 下单用户 id。 */
    @Column(nullable = false)
    private Long userId;

    /** 所购书籍 id。 */
    @Column(nullable = false)
    private Long bookId;

    /** 购买数量。 */
    @Column(nullable = false)
    private Integer qty;

    /** 下单时单价快照（分/元与 books.price 一致）。 */
    @Column(nullable = false)
    private Integer unitPrice;

    /** 订单状态：pending / paid / cancelled。 */
    @Column(nullable = false, length = 20)
    private String status;

    /** 创建时间，仅读，由数据库 DEFAULT CURRENT_TIMESTAMP 写入。 */
    @Column(name = "created_at", insertable = false, updatable = false)
    private LocalDateTime createdAt;

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getOrderNo() {
        return orderNo;
    }

    public void setOrderNo(String orderNo) {
        this.orderNo = orderNo;
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

    public Integer getUnitPrice() {
        return unitPrice;
    }

    public void setUnitPrice(Integer unitPrice) {
        this.unitPrice = unitPrice;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }
}
