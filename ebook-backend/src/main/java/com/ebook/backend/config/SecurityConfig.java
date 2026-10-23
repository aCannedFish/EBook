package com.ebook.backend.config;

import com.ebook.backend.security.JwtAuthenticationFilter;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.swagger.v3.oas.models.Components;
import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Info;
import io.swagger.v3.oas.models.security.SecurityRequirement;
import io.swagger.v3.oas.models.security.SecurityScheme;
import java.util.Map;
import org.springframework.boot.web.servlet.FilterRegistrationBean;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;

/** 沿用课程示例的 SecurityFilterChain，在原书城中接入 JWT 和无状态会话策略。 */
@Configuration
public class SecurityConfig {
    @Bean
    public SecurityFilterChain bookstoreSecurity(HttpSecurity http, JwtAuthenticationFilter jwt,
                                                  ObjectMapper mapper) throws Exception {
        http.csrf(csrf -> csrf.disable())
                .cors(cors -> {})
                .formLogin(form -> form.disable())
                .httpBasic(basic -> basic.disable())
                .logout(logout -> logout.disable())
                .requestCache(cache -> cache.disable())
                .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .authorizeHttpRequests(auth -> auth
                        .requestMatchers(HttpMethod.OPTIONS, "/**").permitAll()
                        .requestMatchers("/api/v1/users/login", "/api/v1/users/register",
                                "/api/v1/runtime", "/v3/api-docs/**", "/swagger-ui/**",
                                "/swagger-ui.html", "/error").permitAll()
                        .requestMatchers("/api/**").authenticated()
                        .anyRequest().permitAll())
                .exceptionHandling(errors -> errors
                        .authenticationEntryPoint((request, response, error) -> {
                            response.setStatus(401);
                            response.setContentType("application/json;charset=UTF-8");
                            response.setHeader(HttpHeaders.WWW_AUTHENTICATE, "Bearer");
                            mapper.writeValue(response.getOutputStream(), Map.of(
                                    "status", 401, "message", "请携带有效的 Authorization Bearer Token"));
                        })
                        .accessDeniedHandler((request, response, error) -> {
                            response.setStatus(403);
                            response.setContentType("application/json;charset=UTF-8");
                            mapper.writeValue(response.getOutputStream(), Map.of(
                                    "status", 403, "message", "没有访问该资源的权限"));
                        }))
                .addFilterBefore(jwt, UsernamePasswordAuthenticationFilter.class);
        return http.build();
    }

    /** Filter 只在 Security 链执行，避免又被 Servlet 容器重复注册。 */
    @Bean
    public FilterRegistrationBean<JwtAuthenticationFilter> jwtRegistration(JwtAuthenticationFilter jwt) {
        var registration = new FilterRegistrationBean<>(jwt);
        registration.setEnabled(false);
        return registration;
    }

    @Bean
    public OpenAPI bookstoreOpenApi() {
        return new OpenAPI().info(new Info().title("EBook 书城 API").version("1.0.0"))
                .components(new Components().addSecuritySchemes("bearerAuth", new SecurityScheme()
                        .type(SecurityScheme.Type.HTTP).scheme("bearer").bearerFormat("JWT")))
                .addSecurityItem(new SecurityRequirement().addList("bearerAuth"));
    }
}
