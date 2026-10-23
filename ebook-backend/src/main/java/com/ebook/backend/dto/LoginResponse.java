package com.ebook.backend.dto;

/** 现有书城登录接口的响应：前端使用 user 展示资料，使用 accessToken 认证后续请求。 */
public record LoginResponse(UserResponse user, String accessToken, String tokenType, long expiresIn) {
}
