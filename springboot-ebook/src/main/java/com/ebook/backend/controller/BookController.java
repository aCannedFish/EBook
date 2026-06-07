package com.ebook.backend.controller;

import com.ebook.backend.dto.BookResponse;
import com.ebook.backend.service.BookService;
import java.util.List;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 图书 REST 接口（Spring Web MVC {@link RestController}）。
 * <p>
 * 路径前缀 {@code /api/v1}；返回 {@link BookResponse} DTO（由 Service 从 Entity 转换），
 * 不直接暴露 {@link com.ebook.backend.entity.Book} 实体。
 * </p>
 */
@RestController
@RequestMapping("/api/v1")
public class BookController {

    /** 图书业务服务，构造器注入。 */
    private final BookService bookService;

    /**
     * @param bookService 由 Spring 容器注入的 {@link BookService} Bean
     */
    public BookController(BookService bookService) {
        this.bookService = bookService;
    }

    /**
     * 获取全部图书，对应前端书城列表页。
     *
     * @return 库中所有图书 DTO，JSON 数组
     */
    @GetMapping("/books")
    public List<BookResponse> getAllBooks() {
        return bookService.listAll();
    }

    /**
     * 按主键获取单本书详情。
     *
     * @param id 路径中的图书 id（Long，与库表一致）
     * @return 图书 DTO；不存在时 Service 抛 {@link com.ebook.backend.exception.ResourceNotFoundException} → 404
     */
    @GetMapping("/book/{id}")
    public BookResponse getBookById(@PathVariable Long id) {
        return bookService.getById(id);
    }
}
