package com.ebook.backend.config;

import org.springframework.boot.web.embedded.tomcat.TomcatProtocolHandlerCustomizer;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.HandlerInterceptor;
import org.springframework.web.servlet.config.annotation.InterceptorRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.util.concurrent.Executors;

/** 在原书城 Tomcat 中为每个 Web 请求分配虚拟线程，并输出实际线程类型。 */
@Configuration
public class VirtualThreadConfig implements WebMvcConfigurer {
    @Bean
    public TomcatProtocolHandlerCustomizer<?> virtualRequests() {
        return handler -> handler.setExecutor(Executors.newVirtualThreadPerTaskExecutor());
    }

    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        registry.addInterceptor(new HandlerInterceptor() {
            @Override
            public boolean preHandle(HttpServletRequest request, HttpServletResponse response,
                                     Object handler) {
                response.setHeader("X-Runtime-Thread",
                        Thread.currentThread().isVirtual() ? "virtual-thread" : "platform-thread");
                return true;
            }
        }).addPathPatterns("/api/**");
    }
}
