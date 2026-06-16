package com.ebook.backend.service;

import com.ebook.backend.dto.BookResponse;
import com.ebook.backend.dto.BookUpsertRequest;
import com.ebook.backend.entity.Book;
import java.util.List;

/**
 * 图书业务服务接口。
 */
public interface BookService {

    List<BookResponse> listAll();

    BookResponse getById(Long id);

    Book findEntityById(Long id);

    BookResponse create(Long operatorId, BookUpsertRequest request);

    BookResponse update(Long operatorId, Long id, BookUpsertRequest request);

    void delete(Long operatorId, Long id);
}
