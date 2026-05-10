package com.ebook.backend.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public class UserRegisterRequest {

    @NotBlank(message = "username is required")
    @Size(max = 60)
    private String username;

    @NotBlank(message = "password is required")
    @Size(min = 6, max = 128)
    private String password;

    @Email(message = "email format invalid")
    @NotBlank(message = "email is required")
    @Size(max = 120)
    private String email;

    @Size(max = 200)
    private String signature;

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
