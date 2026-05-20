package com.ebook.backend.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

/**
 * 跨域（CORS）配置，供前后端分离联调使用。
 * <p>
 * 前端 Vite 默认 {@code http://localhost:5173}，后端 {@code :8080}，浏览器同源策略会拦截跨域 fetch；
 * 本配置通过 Spring MVC 的 {@link WebMvcConfigurer#addCorsMappings} 声明允许的来源与方法。
 * </p>
 */
@Configuration
public class CorsConfig {

    /**
     * 注册全局 CORS 规则：仅作用于 {@code /api/**} 路径。
     */
    @Bean
    public WebMvcConfigurer webMvcConfigurer() {
        return new WebMvcConfigurer() {
            @Override
            public void addCorsMappings(CorsRegistry registry) {
                registry.addMapping("/api/**")
                        .allowedOrigins("http://localhost:5173")
                        .allowedMethods("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS")
                        .allowedHeaders("*");
            }
        };
    }
}
