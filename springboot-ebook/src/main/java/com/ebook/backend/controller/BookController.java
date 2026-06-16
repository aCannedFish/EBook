package com.ebook.backend.controller;

import com.ebook.backend.dto.BookResponse;
import com.ebook.backend.dto.BookUpsertRequest;
import com.ebook.backend.service.BookService;
import jakarta.validation.Valid;
import java.util.List;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * 图书 REST 接口。
 */
@RestController
@RequestMapping("/api/v1")
public class BookController {

    private final BookService bookService;

    public BookController(BookService bookService) {
        this.bookService = bookService;
    }

    @GetMapping("/books")
    public List<BookResponse> getAllBooks() {
        return bookService.listAll();
    }

    @GetMapping("/book/{id}")
    public BookResponse getBookById(@PathVariable Long id) {
        return bookService.getById(id);
    }

    @PostMapping("/books")
    public ResponseEntity<BookResponse> createBook(@RequestParam Long operatorId,
                                                   @Valid @RequestBody BookUpsertRequest request) {
        return ResponseEntity.status(HttpStatus.CREATED).body(bookService.create(operatorId, request));
    }

    @PutMapping("/books/{id}")
    public BookResponse updateBook(@RequestParam Long operatorId,
                                   @PathVariable Long id,
                                   @Valid @RequestBody BookUpsertRequest request) {
        return bookService.update(operatorId, id, request);
    }

    @DeleteMapping("/books/{id}")
    public ResponseEntity<Void> deleteBook(@RequestParam Long operatorId, @PathVariable Long id) {
        bookService.delete(operatorId, id);
        return ResponseEntity.noContent().build();
    }
}
