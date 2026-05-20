package com.ebook.backend.repository;

import com.ebook.backend.entity.Book;
import org.springframework.data.jpa.repository.JpaRepository;

/**
 * 图书数据访问接口（Spring Data JPA）。
 * <p>
 * 继承 {@link JpaRepository} 即具备 {@code findAll}、{@code findById}、{@code save} 等；
 * 实现由框架在启动时动态生成。供 {@link com.ebook.backend.service.BookService}、
 * {@link com.ebook.backend.service.CartService}、{@link com.ebook.backend.service.OrderService} 使用。
 * </p>
 */
public interface BookRepository extends JpaRepository<Book, Long> {
}
