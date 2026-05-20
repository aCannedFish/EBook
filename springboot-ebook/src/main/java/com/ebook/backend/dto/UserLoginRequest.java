package com.ebook.backend.dto;

import jakarta.validation.constraints.NotBlank;

/**
 * 登录 API 请求体（JSON → Java）。
 * <p>
 * 由 {@link com.ebook.backend.controller.UserController#login} 接收；
 * {@code @Valid} 触发 Jakarta Bean Validation，失败时由 {@link com.ebook.backend.exception.ApiExceptionHandler} 返回 400。
 * </p>
 */
public class UserLoginRequest {

    @NotBlank(message = "username is required")
    private String username;

    @NotBlank(message = "password is required")
    private String password;

    public String getUsername() {
        return username;
    }

    public void setUsername(String username) {
        this.username = username;
    }

    public String getPassword() {
        return password;
    }

    public void setPassword(String password) {
        this.password = password;
    }
}
