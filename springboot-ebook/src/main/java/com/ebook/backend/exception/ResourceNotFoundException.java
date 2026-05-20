package com.ebook.backend.exception;

/**
 * 业务资源不存在时抛出的运行时异常。
 * <p>
 * 由 {@link ApiExceptionHandler} 捕获并映射为 HTTP 404；
 * Service 层在 {@code Optional.orElseThrow} 或查无数据时使用。
 * </p>
 */
public class ResourceNotFoundException extends RuntimeException {

    public ResourceNotFoundException(String message) {
        super(message);
    }
}
