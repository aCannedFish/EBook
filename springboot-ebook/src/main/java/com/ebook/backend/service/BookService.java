package com.ebook.backend.service;

import com.ebook.backend.dto.BookResponse;
import com.ebook.backend.entity.Book;
import com.ebook.backend.exception.ResourceNotFoundException;
import com.ebook.backend.repository.BookRepository;
import java.util.List;
import org.springframework.stereotype.Service;

/**
 * 图书业务服务（Spring {@link Service} Bean）。
 * <p>
 * 被 {@link com.ebook.backend.controller.BookController} 调用，对外返回 {@link BookResponse}；
 * 亦被 {@link CartService}、{@link OrderService} 通过 {@link #findEntityById} 读取实体。
 * 持久化经 {@link BookRepository}（Spring Data JPA）。
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
     * 返回全部书目 DTO 列表（供 REST API 使用）。
     *
     * @return 所有图书的 API 响应对象
     */
    public List<BookResponse> listAll() {
        return bookRepository.findAll()
                .stream()
                .map(this::toResponse)
                .toList();
    }

    /**
     * 按主键查书并转为 DTO；不存在则抛 {@link ResourceNotFoundException}。
     *
     * @param id 图书主键
     * @return 图书 DTO
     */
    public BookResponse getById(Long id) {
        return toResponse(findEntityById(id));
    }

    /**
     * 按主键查书实体；供本模块内其他 Service 读取价格等字段。
     *
     * @param id 图书主键
     * @return 图书记录
     */
    public Book findEntityById(Long id) {
        return bookRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("book not found: " + id));
    }

    /**
     * @param book JPA 实体
     * @return 对外 API DTO
     */
    private BookResponse toResponse(Book book) {
        BookResponse response = new BookResponse();
        response.setId(book.getId());
        response.setTitle(book.getTitle());
        response.setAuthor(book.getAuthor());
        response.setPrice(book.getPrice());
        response.setCategory(book.getCategory());
        response.setPublisher(book.getPublisher());
        response.setIsbn(book.getIsbn());
        response.setFormat(book.getFormat());
        response.setStockType(book.getStockType());
        response.setStockText(book.getStockText());
        response.setDescription(book.getDescription());
        return response;
    }
}
