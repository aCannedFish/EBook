package com.ebook.backend;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * Spring Boot 应用入口。
 * <p>
 * {@link SpringBootApplication} 触发组件扫描（本包及子包）、自动配置（数据源、JPA、内嵌 Tomcat 等），
 * 启动后对外提供 {@code /api/v1/**} REST 接口。
 * </p>
 */
@SpringBootApplication
public class EbookBackendApplication {

    public static void main(String[] args) {
        SpringApplication.run(EbookBackendApplication.class, args);
    }
}
