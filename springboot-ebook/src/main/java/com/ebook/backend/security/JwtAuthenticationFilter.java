package com.ebook.backend.security;

import com.ebook.backend.entity.User;
import com.ebook.backend.repository.UserRepository;
import com.ebook.backend.service.support.AdminGuard;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.jsonwebtoken.JwtException;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.List;
import java.util.Map;
import org.springframework.http.HttpHeaders;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

/** 每次请求独立验签；再读取现有用户记录，使禁用账号和角色变更立即生效。 */
@Component
public class JwtAuthenticationFilter extends OncePerRequestFilter {
    private final JwtTokenService tokens;
    private final UserRepository users;
    private final ObjectMapper mapper;

    public JwtAuthenticationFilter(JwtTokenService tokens, UserRepository users, ObjectMapper mapper) {
        this.tokens = tokens;
        this.users = users;
        this.mapper = mapper;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response,
                                    FilterChain chain) throws ServletException, IOException {
        String header = request.getHeader(HttpHeaders.AUTHORIZATION);
        if (header == null || header.isBlank()) {
            chain.doFilter(request, response);
            return;
        }
        try {
            if (!header.startsWith("Bearer ")) {
                throw new IllegalArgumentException("需要 Bearer Token");
            }
            Long id = Long.valueOf(tokens.verify(header.substring(7).trim()).getSubject());
            User user = users.findById(id).filter(u -> !Boolean.FALSE.equals(u.getEnabled()))
                    .orElseThrow(() -> new IllegalArgumentException("用户不存在或已禁用"));
            boolean admin = AdminGuard.isAdmin(user);
            BookstorePrincipal principal = new BookstorePrincipal(id, user.getUsername(), admin);
            var authentication = new UsernamePasswordAuthenticationToken(principal, null,
                    List.of(new SimpleGrantedAuthority(admin ? "ROLE_ADMIN" : "ROLE_USER")));
            SecurityContextHolder.getContext().setAuthentication(authentication);
        } catch (JwtException | IllegalArgumentException error) {
            SecurityContextHolder.clearContext();
            response.setStatus(401);
            response.setContentType("application/json;charset=UTF-8");
            response.setHeader(HttpHeaders.WWW_AUTHENTICATE, "Bearer error=\"invalid_token\"");
            mapper.writeValue(response.getOutputStream(), Map.of(
                    "status", 401, "message", "Token 无效、已过期或账号已禁用"));
            return;
        }
        chain.doFilter(request, response);
    }
}
