package com.ebook.backend.dto;

/**
 * 图书 API 响应体（Java → JSON）。
 * <p>
 * 由 {@link com.ebook.backend.service.BookService} 从 {@link com.ebook.backend.entity.Book} 转换而来，
 * 对外屏蔽 JPA 实体细节，便于后续切换异构数据源时保持 API 契约不变。
 * </p>
 */
public class BookResponse {

    /** 图书主键。 */
    private Long id;

    /** 书名。 */
    private String title;

    /** 作者。 */
    private String author;

    /** 售价（整数，单位：元）。 */
    private Integer price;

    /** 分类。 */
    private String category;

    /** 出版社。 */
    private String publisher;

    /** 国际标准书号。 */
    private String isbn;

    /** 售卖形式文案。 */
    private String format;

    /** 库存状态类型：ok / warn 等。 */
    private String stockType;

    /** 库存状态展示文案。 */
    private String stockText;

    /** 内容简介。 */
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

    public String getDescription() {
        return description;
    }

    public void setDescription(String description) {
        this.description = description;
    }
}
