package com.ebook.backend.service;

import com.ebook.backend.entity.Book;
import com.ebook.backend.exception.ResourceNotFoundException;
import com.ebook.backend.repository.BookRepository;
import java.util.List;
import org.springframework.stereotype.Service;

/**
 * 图书业务服务（Spring {@link Service} Bean）。
 * <p>
 * 被 {@link com.ebook.backend.controller.BookController} 调用；
 * 亦被 {@link CartService}、{@link OrderService} 用于校验书是否存在及读取价格。
 * </p>
 */
@Service
public class BookService {

    /** 图书数据访问接口（Spring Data JPA 代理实现）。 */
    private final BookRepository bookRepository;

    /**
     * @param bookRepository 由 Spring 注入的 {@link BookRepository}
     */
    public BookService(BookRepository bookRepository) {
        this.bookRepository = bookRepository;
    }

    /**
     * 返回书目表中全部记录（无分页）。
     *
     * @return 所有 {@link Book} 实体
     */
    public List<Book> findAll() {
        return bookRepository.findAll();
    }

    /**
     * 按主键查书；不存在则抛 {@link ResourceNotFoundException}。
     *
     * @param id 图书主键
     * @return 图书记录
     */
    public Book findById(Long id) {
        return bookRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("book not found: " + id));
    }
}
