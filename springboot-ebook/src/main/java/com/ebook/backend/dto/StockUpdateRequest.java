package com.ebook.backend.dto;

import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;

/** 库存部分更新请求；禁止负库存，不要求重复提交整本书的资料。 */
public record StockUpdateRequest(@NotNull @Min(0) Integer stockQty) {
}
