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
import org.springframework.stereotype.Service;

/**
 * {@link BookService} 的 Spring 实现。
 */
@Service
public class BookServiceImpl implements BookService {

    private final BookRepository bookRepository;
    private final UserRepository userRepository;

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

    @Override
    public BookResponse getById(Long id) {
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
