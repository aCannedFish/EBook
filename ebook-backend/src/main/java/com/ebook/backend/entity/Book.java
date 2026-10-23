package com.ebook.backend.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

/**
 * 图书实体，映射表 {@code books}。
 * <p>
 * 可由 {@link com.ebook.backend.dto.BookResponse} 对外序列化为 JSON（无敏感字段）；
 * 封面路径不在库中，由前端按 {@link #isbn} 映射静态资源。
 * </p>
 */
@Entity
@Table(name = "books")
public class Book {

    /** 主键，自增；购物车、订单通过 bookId 引用。 */
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    /** 书名。 */
    @Column(nullable = false, length = 150)
    private String title;

    /** 作者。 */
    @Column(nullable = false, length = 100)
    private String author;

    /** 售价（整数，单位：元，与订单 unit_price 一致）。 */
    @Column(nullable = false)
    private Integer price;

    /** 分类标签，用于列表筛选展示。 */
    @Column(nullable = false, length = 120)
    private String category;

    /** 出版社名称。 */
    @Column(nullable = false, length = 120)
    private String publisher;

    /** 国际标准书号，唯一；前端用于匹配封面图。 */
    @Column(nullable = false, unique = true, length = 30)
    private String isbn;

    /** 售卖形式文案，如「电子书 · 立即阅读」。 */
    @Column(nullable = false, length = 60)
    private String format;

    /** 库存状态类型：如 ok / warn，供前端 Tag 颜色。 */
    @Column(nullable = false, length = 50)
    private String stockType;

    /** 库存状态展示文案：如「有货」「库存紧张」。 */
    @Column(nullable = false, length = 50)
    private String stockText;

    /** 库存数量，结算时扣减。 */
    @Column(name = "stock_qty", nullable = false)
    private Integer stockQty = 0;

    /** 封面 URL，可为空（前端可回退 ISBN 映射）。 */
    @Column(name = "cover_url", length = 512)
    private String coverUrl;

    /** 内容简介。 */
    @Column(nullable = false, columnDefinition = "TEXT")
    private String description;

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getTitle() {
        return title;
    }

    public void setTitle(String title) {
        this.title = title;
    }

    public String getAuthor() {
        return author;
    }

    public void setAuthor(String author) {
        this.author = author;
    }

    public Integer getPrice() {
        return price;
    }

    public void setPrice(Integer price) {
        this.price = price;
    }

    public String getCategory() {
        return category;
    }

    public void setCategory(String category) {
        this.category = category;
    }

    public String getPublisher() {
        return publisher;
    }

    public void setPublisher(String publisher) {
        this.publisher = publisher;
    }

    public String getIsbn() {
        return isbn;
    }

    public void setIsbn(String isbn) {
        this.isbn = isbn;
    }

    public String getFormat() {
        return format;
    }

    public void setFormat(String format) {
        this.format = format;
    }

    public String getStockType() {
        return stockType;
    }

    public void setStockType(String stockType) {
        this.stockType = stockType;
    }

    public String getStockText() {
        return stockText;
    }

    public void setStockText(String stockText) {
        this.stockText = stockText;
    }

    public Integer getStockQty() {
        return stockQty;
    }

    public void setStockQty(Integer stockQty) {
        this.stockQty = stockQty;
    }

    public String getCoverUrl() {
        return coverUrl;
    }

    public void setCoverUrl(String coverUrl) {
        this.coverUrl = coverUrl;
    }

    public String getDescription() {
        return description;
    }

    public void setDescription(String description) {
        this.description = description;
    }
}
