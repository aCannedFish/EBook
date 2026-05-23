package com.ebook.backend.entity;

import jakarta.persistence.CascadeType;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.OneToMany;
import jakarta.persistence.Table;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

/**
 * 订单头实体，映射表 {@code orders}（类名避免与 SQL 关键字及模块歧义）。
 * <p>
 * {@link #orderNo} 为业务订单号，对外 API 的 {@link com.ebook.backend.dto.OrderResponse#getId()} 即此字段；
 * 一次结算批次对应一条订单头，多本书明细在 {@link #items} 中；
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

    /** 业务订单号，唯一，如 ORD-20260519120000-4521。 */
    @Column(name = "order_no", nullable = false, unique = true, length = 40)
    private String orderNo;

    /** 下单用户 id。 */
    @Column(nullable = false)
    private Long userId;

    /** 订单状态：pending / paid / cancelled。 */
    @Column(nullable = false, length = 20)
    private String status;

    /** 创建时间，仅读，由数据库 DEFAULT CURRENT_TIMESTAMP 写入。 */
    @Column(name = "created_at", insertable = false, updatable = false)
    private LocalDateTime createdAt;

    /** 本批次下的书籍明细；级联持久化，不单独使用 OrderItemRepository。 */
    @OneToMany(mappedBy = "order", cascade = CascadeType.ALL, orphanRemoval = true)
    private List<OrderItem> items = new ArrayList<>();

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

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }

    public List<OrderItem> getItems() {
        return items;
    }

    public void setItems(List<OrderItem> items) {
        this.items = items;
    }

    /**
     * 向本订单追加一行明细并维护双向关联。
     *
     * @param item 订单明细
     */
    public void addItem(OrderItem item) {
        items.add(item);
        item.setOrder(this);
    }
}
