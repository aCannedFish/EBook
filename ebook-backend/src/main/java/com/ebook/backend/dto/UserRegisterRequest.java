package com.ebook.backend.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/**
 * 用户注册 API 请求体。
 * <p>
 * 校验通过后由 {@link com.ebook.backend.service.UserService#register} 转为 {@link com.ebook.backend.entity.User} 持久化。
 * </p>
 */
public class UserRegisterRequest {

    /** 新用户名，最长 60，库表唯一。 */
    @NotBlank(message = "username is required")
    @Size(max = 60)
    private String username;

    /** 密码，长度 6～128。 */
    @NotBlank(message = "password is required")
    @Size(min = 6, max = 128)
    private String password;

    /** 邮箱，须符合邮箱格式且唯一。 */
    @Email(message = "email format invalid")
    @NotBlank(message = "email is required")
    @Size(max = 120)
    private String email;

    /** 个性签名，可选。 */
    @Size(max = 200)
    private String signature;

    /** 用户等级，可选；缺省时 Service 设为「普通用户」。 */
    @Size(max = 30)
    private String level;

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
