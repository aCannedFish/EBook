package com.ebook.backend.service.impl;

import com.ebook.backend.dto.BookResponse;
import com.ebook.backend.dto.BookUpsertRequest;
import com.ebook.backend.entity.Book;
import com.ebook.backend.exception.ResourceNotFoundException;
import com.ebook.backend.repository.BookRepository;
import com.ebook.backend.repository.UserRepository;
import com.ebook.backend.service.BookService;
import com.ebook.backend.service.support.AdminGuard;
import com.ebook.backend.service.support.StockHelper;
import java.util.List;
import java.util.Locale;
import com.ebook.backend.dto.BookPageResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.data.jpa.domain.Specification;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.stereotype.Service;

/**
 * {@link BookService} 的 Spring 实现。
 */
@Service
public class BookServiceImpl implements BookService {

    private final BookRepository bookRepository;
    private final UserRepository userRepository;

    @Value("${app.books.query-delay-ms:0}")
    private long queryDelayMillis;

    public BookServiceImpl(BookRepository bookRepository, UserRepository userRepository) {
        this.bookRepository = bookRepository;
        this.userRepository = userRepository;
    }

    @Override
    public List<BookResponse> listAll() {
        return bookRepository.findAll()
                .stream()
                .map(this::toResponse)
                .toList();
    }

    /** 将分页和过滤交给数据库，前端、库存 Skill 与导购共用同一数据源。 */
    @Override
    public BookPageResponse search(int page, int size, String category, String keyword, String isbn) {
        simulateSlowQuery();
        Specification<Book> filters = (book, query, cb) -> cb.conjunction();
        if (category != null && !category.isBlank()) {
            filters = filters.and((book, query, cb) -> cb.equal(book.get("category"), category));
        }
        if (keyword != null && !keyword.isBlank()) {
            String pattern = "%" + keyword.trim().toLowerCase(Locale.ROOT) + "%";
            filters = filters.and((book, query, cb) -> cb.or(
                    cb.like(cb.lower(book.get("title")), pattern),
                    cb.like(cb.lower(book.get("author")), pattern),
                    cb.like(cb.lower(book.get("category")), pattern)));
        }
        if (isbn != null && !isbn.isBlank()) {
            String normalized = isbn.replace("-", "").replace(" ", "");
            filters = filters.and((book, query, cb) -> cb.equal(
                    cb.function("replace", String.class, book.get("isbn"), cb.literal("-"), cb.literal("")),
                    normalized));
        }
        var results = bookRepository.findAll(filters, PageRequest.of(page, size, Sort.by("id")));
        return new BookPageResponse(results.getContent().stream().map(this::toResponse).toList(),
                page, size, results.getTotalElements(), results.getTotalPages());
    }

    /** 在真实书城库存记录上执行部分更新，随后库存查询工具立即读取到新值。 */
    @Override
    @Transactional
    public BookResponse updateStock(Long operatorId, Long id, int stockQty) {
        AdminGuard.ensureAdmin(userRepository, operatorId);
        Book book = findEntityById(id);
        book.setStockQty(stockQty);
        StockHelper.syncStockDisplay(book);
        return toResponse(bookRepository.save(book));
    }

    /** 仅模拟可配置的数据库等待，不持有 synchronized 锁阻塞虚拟线程载体。 */
    private void simulateSlowQuery() {
        if (queryDelayMillis <= 0) {
            return;
        }
        try {
            Thread.sleep(queryDelayMillis);
        } catch (InterruptedException error) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("查询被中断", error);
        }
    }

    @Override
    public BookResponse getById(Long id) {
        simulateSlowQuery();
        return toResponse(findEntityById(id));
    }

    @Override
    public Book findEntityById(Long id) {
        return bookRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("book not found: " + id));
    }

    @Override
    public BookResponse create(Long operatorId, BookUpsertRequest request) {
        AdminGuard.ensureAdmin(userRepository, operatorId);
        bookRepository.findByIsbn(request.getIsbn()).ifPresent(book -> {
            throw new IllegalArgumentException("isbn already exists");
        });
        Book book = new Book();
        applyUpsert(book, request);
        return toResponse(bookRepository.save(book));
    }

    @Override
    public BookResponse update(Long operatorId, Long id, BookUpsertRequest request) {
        AdminGuard.ensureAdmin(userRepository, operatorId);
        Book book = findEntityById(id);
        bookRepository.findByIsbn(request.getIsbn()).ifPresent(existing -> {
            if (!existing.getId().equals(id)) {
                throw new IllegalArgumentException("isbn already exists");
            }
        });
        applyUpsert(book, request);
        return toResponse(bookRepository.save(book));
    }

    @Override
    public void delete(Long operatorId, Long id) {
        AdminGuard.ensureAdmin(userRepository, operatorId);
        Book book = findEntityById(id);
        bookRepository.delete(book);
    }

    private void applyUpsert(Book book, BookUpsertRequest request) {
        book.setTitle(request.getTitle());
        book.setAuthor(request.getAuthor());
        book.setPrice(request.getPrice());
        book.setCategory(request.getCategory());
        book.setPublisher(request.getPublisher());
        book.setIsbn(request.getIsbn());
        book.setFormat(request.getFormat());
        book.setStockQty(request.getStockQty());
        book.setCoverUrl(request.getCoverUrl());
        book.setDescription(request.getDescription());
        StockHelper.syncStockDisplay(book);
    }

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
        response.setStockQty(book.getStockQty());
        response.setCoverUrl(book.getCoverUrl());
        response.setDescription(book.getDescription());
        return response;
    }
}
