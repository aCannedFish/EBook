package com.ebook.backend.dto;

/**
 * 用户 API 响应体（Java → JSON）。
 * <p>
 * 由 {@link com.ebook.backend.service.UserService} 从 {@link com.ebook.backend.entity.User} 转换而来，
 *  有意不包含 password，供登录/注册/资料接口返回给前端。
 * </p>
 */
public class UserResponse {

    private Long id;
    private String username;
    private String email;
    private String signature;
    private String level;

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

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

    public String getLevel() {
        return level;
    }

    public void setLevel(String level) {
        this.level = level;
    }
}
