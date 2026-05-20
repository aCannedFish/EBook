package com.ebook.backend.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/**
 * 更新用户资料 API 请求体（不含密码）。
 * <p>
 * 对应 {@link com.ebook.backend.controller.UserController#updateProfile}。
 * </p>
 */
public class UserProfileUpdateRequest {

    @NotBlank(message = "username is required")
    @Size(max = 60)
    private String username;

    @NotBlank(message = "email is required")
    @Email(message = "email format invalid")
    @Size(max = 120)
    private String email;

    @Size(max = 200)
    private String signature;

    public String getUsername() {
        return username;
    }

    public void setUsername(String username) {
        this.username = username;
    }

    public String getEmail() {
        return email;
    }

    public void setEmail(String email) {
        this.email = email;
    }

    public String getSignature() {
        return signature;
    }

    public void setSignature(String signature) {
        this.signature = signature;
    }
}
