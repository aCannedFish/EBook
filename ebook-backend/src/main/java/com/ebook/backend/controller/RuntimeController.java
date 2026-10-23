package com.ebook.backend.controller;

import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

/** 从真实 Web 请求中读取 JDK 和线程信息，供健康检查与作业截图验证。 */
@RestController
public class RuntimeController {
    @GetMapping("/api/v1/runtime")
    public Map<String, Object> runtime() {
        return Map.of("application", "ebook-backend", "javaVersion", System.getProperty("java.version"),
                "requestThreadVirtual", Thread.currentThread().isVirtual(),
                "requestThreadName", Thread.currentThread().getName());
    }
}
