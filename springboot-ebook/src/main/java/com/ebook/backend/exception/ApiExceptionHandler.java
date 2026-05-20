package com.ebook.backend.exception;

import java.util.HashMap;
import java.util.Map;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

/**
 * 全局 REST 异常处理器（Spring MVC {@link RestControllerAdvice}）。
 * <p>
 * 将 Controller/Service 抛出的异常统一转换为 JSON {@code {"message": "..."}}，
 * 避免各接口自行 try-catch，并与前端 {@code backendApi.js} 的错误解析约定一致。
 * </p>
 */
@RestControllerAdvice
public class ApiExceptionHandler {

    /** 业务参数或规则错误（如密码错误、qty 超范围）→ 400 */
    @ExceptionHandler(IllegalArgumentException.class)
    public ResponseEntity<Map<String, Object>> handleIllegalArgument(IllegalArgumentException ex) {
        Map<String, Object> body = new HashMap<>();
        body.put("message", ex.getMessage());
        return ResponseEntity.badRequest().body(body);
    }

    /** 资源不存在（书/用户/购物车行/订单）→ 404 */
    @ExceptionHandler(ResourceNotFoundException.class)
    public ResponseEntity<Map<String, Object>> handleNotFound(ResourceNotFoundException ex) {
        Map<String, Object> body = new HashMap<>();
        body.put("message", ex.getMessage());
        return ResponseEntity.status(HttpStatus.NOT_FOUND).body(body);
    }

    /**
     * {@code @Valid} 请求体校验失败（Jakarta Bean Validation）→ 400。
     * 取第一个字段错误信息作为 message。
     */
    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<Map<String, Object>> handleValidation(MethodArgumentNotValidException ex) {
        Map<String, Object> body = new HashMap<>();
        body.put("message", ex.getBindingResult().getFieldError() != null
                ? ex.getBindingResult().getFieldError().getDefaultMessage()
                : "validation failed");
        return ResponseEntity.badRequest().body(body);
    }
}
