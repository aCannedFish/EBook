package com.ebook.backend.controller;

import com.ebook.backend.dto.BookResponse;
import com.ebook.backend.dto.BookPageResponse;
import com.ebook.backend.dto.BookUpsertRequest;
import com.ebook.backend.dto.StockUpdateRequest;
import com.ebook.backend.security.CurrentUser;
import com.ebook.backend.service.BookService;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import java.net.URI;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/** 原书城的图书资源接口：同一接口承担页面读写、AI 库存读取和 OpenAPI 契约验证。 */
@RestController
@RequestMapping("/api/v1/books")
@Validated
public class BookController {
    private final BookService books;
    private final CurrentUser currentUser;

    public BookController(BookService books, CurrentUser currentUser) {
        this.books = books;
        this.currentUser = currentUser;
    }

    @GetMapping
    public BookPageResponse list(@RequestParam(defaultValue = "0") @Min(0) int page,
                                 @RequestParam(defaultValue = "20") @Min(1) @Max(100) int size,
                                 @RequestParam(required = false) String category,
                                 @RequestParam(required = false) String keyword,
                                 @RequestParam(required = false) String isbn) {
        return books.search(page, size, category, keyword, isbn);
    }

    @GetMapping("/{id}")
    public BookResponse detail(@PathVariable Long id) {
        return books.getById(id);
    }

    @PostMapping
    public ResponseEntity<BookResponse> create(@Valid @RequestBody BookUpsertRequest request) {
        BookResponse created = books.create(currentUser.adminId(null), request);
        return ResponseEntity.created(URI.create("/api/v1/books/" + created.getId())).body(created);
    }

    @PutMapping("/{id}")
    public BookResponse update(@PathVariable Long id, @Valid @RequestBody BookUpsertRequest request) {
        return books.update(currentUser.adminId(null), id, request);
    }

    @PatchMapping("/{id}/stock")
    public BookResponse stock(@PathVariable Long id, @Valid @RequestBody StockUpdateRequest request) {
        return books.updateStock(currentUser.adminId(null), id, request.stockQty());
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> delete(@PathVariable Long id) {
        books.delete(currentUser.adminId(null), id);
        return ResponseEntity.noContent().build();
    }
}
