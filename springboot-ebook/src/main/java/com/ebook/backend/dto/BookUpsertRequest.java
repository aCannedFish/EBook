package com.ebook.backend.dto;

import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

/**
 * 管理员创建/更新图书请求体。
 */
public class BookUpsertRequest {

    @NotBlank(message = "title is required")
    @Size(max = 150)
    private String title;

    @NotBlank(message = "author is required")
    @Size(max = 100)
    private String author;

    @NotNull(message = "price is required")
    @Min(value = 0, message = "price must be >= 0")
    private Integer price;

    @NotBlank(message = "category is required")
    @Size(max = 120)
    private String category;

    @NotBlank(message = "publisher is required")
    @Size(max = 120)
    private String publisher;

    @NotBlank(message = "isbn is required")
    @Size(max = 30)
    private String isbn;

    @NotBlank(message = "format is required")
    @Size(max = 60)
    private String format;

    @NotNull(message = "stockQty is required")
    @Min(value = 0, message = "stockQty must be >= 0")
    private Integer stockQty;

    @Size(max = 512)
    private String coverUrl;

    @NotBlank(message = "description is required")
    private String description;

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
