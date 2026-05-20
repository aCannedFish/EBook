package com.ebook.backend.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

/**
 * 用户实体，映射表 {@code users}（JPA/Hibernate）。
 * <p>
 * 持久化层使用；对外 API 通过 {@link com.ebook.backend.dto.UserResponse} 暴露，避免泄露 {@link #password}。
 * 与 {@link CartItem}、{@link OrderEntity} 通过 {@code userId} 逻辑关联（未使用 JPA 关联注解）。
 * </p>
 */
@Entity
@Table(name = "users")
public class User {

    /** 主键，自增；登录成功后前端保存此 id 用于后续 API 路径。 */
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    /** 登录名，唯一，最长 60 字符。 */
    @Column(nullable = false, unique = true, length = 60)
    private String username;

    /** 登录密码（演示环境明文存储，不通过 API 返回）。 */
    @Column(nullable = false, length = 128)
    private String password;

    /** 邮箱，唯一，用于注册校验与资料展示。 */
    @Column(nullable = false, unique = true, length = 120)
    private String email;

    /** 个性签名，可为空字符串。 */
    @Column(length = 200)
    private String signature;

    /** 用户等级展示文案，如「普通用户」。 */
    @Column(nullable = false, length = 30)
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
