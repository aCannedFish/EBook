package com.ebook.backend.repository;

import com.ebook.backend.entity.Book;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.JpaSpecificationExecutor;

/**
 * 图书数据访问接口（Spring Data JPA）。
 * <p>
 * 继承 {@link JpaRepository} 即具备 {@code findAll}、{@code findById}、{@code save} 等；
 * 实现由框架在启动时动态生成。
 * </p>
 */
public interface BookRepository extends JpaRepository<Book, Long>, JpaSpecificationExecutor<Book> {

    Optional<Book> findByIsbn(String isbn);
}
