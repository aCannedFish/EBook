package com.ebook.backend.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

/**
 * 跨域（CORS）配置，供前后端分离联调使用。
 */
@Configuration
public class CorsConfig {

    /**
     * 注册 CORS 规则的 {@link WebMvcConfigurer} Bean。
     * <p>
     * 匿名内部类重写 {@link WebMvcConfigurer#addCorsMappings}，仅放行 {@code /api/**} 与前端开发源。
     * </p>
     *
     * @return Spring MVC 配置扩展 Bean
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
