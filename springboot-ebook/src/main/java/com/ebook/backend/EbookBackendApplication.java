package com.ebook.backend;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * Spring Boot 应用入口。
 */
@SpringBootApplication
public class EbookBackendApplication {

    /**
     * 启动 Spring 容器与内嵌 Tomcat。
     *
     * @param args 命令行参数，可覆盖 spring 配置（如 --server.port）
     */
    public static void main(String[] args) {
        SpringApplication.run(EbookBackendApplication.class, args);
    }
}
