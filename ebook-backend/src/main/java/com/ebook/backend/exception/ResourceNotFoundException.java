package com.ebook.backend.exception;

/**
 * 业务资源不存在时抛出的运行时异常。
 */
public class ResourceNotFoundException extends RuntimeException {

    /**
     * @param message 错误说明，会写入 API 响应的 message 字段
     */
    public ResourceNotFoundException(String message) {
        super(message);
    }
}
