package com.ebook.backend.security;

import com.ebook.backend.dto.UserResponse;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.io.Decoders;
import io.jsonwebtoken.security.Keys;
import java.time.Instant;
import java.util.Date;
import java.util.UUID;
import javax.crypto.SecretKey;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

/** 签发并验证书城 JWT。Token 自包含，不写 Session 或服务端 Token 表。 */
@Service
public class JwtTokenService {
    private final SecretKey key;
    private final long ttlSeconds;

    public JwtTokenService(@Value("${app.jwt.secret}") String secret,
                           @Value("${app.jwt.ttl-seconds:3600}") long ttlSeconds) {
        this.key = Keys.hmacShaKeyFor(Decoders.BASE64.decode(secret));
        if (ttlSeconds <= 0) {
            throw new IllegalArgumentException("JWT 有效期必须大于零");
        }
        this.ttlSeconds = ttlSeconds;
    }

    /** 以用户主键绑定身份，避免用户名修改后影响订单、购物车的所有权校验。 */
    public String issue(UserResponse user) {
        Instant now = Instant.now();
        return Jwts.builder()
                .subject(user.getId().toString())
                .issuer("ebook-bookstore")
                .id(UUID.randomUUID().toString())
                .claim("username", user.getUsername())
                .claim("role", Boolean.TRUE.equals(user.getAdmin()) ? "ADMIN" : "USER")
                .issuedAt(Date.from(now))
                .expiration(Date.from(now.plusSeconds(ttlSeconds)))
                .signWith(key, Jwts.SIG.HS256)
                .compact();
    }

    /** 同时校验签名、有效期和签发方，非法 Token 交给过滤器返回 401。 */
    public Claims verify(String token) {
        return Jwts.parser().verifyWith(key).requireIssuer("ebook-bookstore")
                .build().parseSignedClaims(token).getPayload();
    }

    public long ttlSeconds() {
        return ttlSeconds;
    }
}
