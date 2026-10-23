package com.ebook.backend.dto;

import java.util.List;

/** 书目列表的稳定分页契约；页码从零开始，集合字段统一为 items。 */
public record BookPageResponse(List<BookResponse> items, int page, int size,
                               long totalElements, int totalPages) {
}
