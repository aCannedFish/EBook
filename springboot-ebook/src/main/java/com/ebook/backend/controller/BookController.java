package com.ebook.backend.controller;

import com.ebook.backend.entity.Book;
import com.ebook.backend.service.BookService;
import java.util.List;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 图书 REST 接口（Spring Web MVC {@link RestController}）。
 * <p>
 * 路径前缀 {@code /api/v1}；直接返回 {@link Book} 实体列表/详情（Jackson 序列化为 JSON），
 * 由 {@link BookService} 访问 {@link com.ebook.backend.repository.BookRepository}。
 * </p>
 */
@RestController
@RequestMapping("/api/v1")
public class BookController {

    private final BookService bookService;

    public BookController(BookService bookService) {
        this.bookService = bookService;
    }

    /**
     * 获取全部图书，对应前端书城列表页。
     *
     * @return 库中所有 {@link Book}，JSON 数组
     */
    @GetMapping("/books")
    public List<Book> getAllBooks() {
        return bookService.findAll();
    }

    /**
     * 按主键获取单本书详情。
     *
     * @param id 路径中的图书 id（Long，与库表一致）
     * @return 图书实体；不存在时 Service 抛 {@link com.ebook.backend.exception.ResourceNotFoundException} → 404
     */
    @GetMapping("/book/{id}")
    public Book getBookById(@PathVariable Long id) {
        return bookService.findById(id);
    }
}
