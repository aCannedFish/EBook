package com.ebook.backend.controller;

import com.ebook.backend.dto.UserLoginRequest;
import com.ebook.backend.dto.UserProfileUpdateRequest;
import com.ebook.backend.dto.UserRegisterRequest;
import com.ebook.backend.dto.UserResponse;
import com.ebook.backend.service.UserService;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 用户 REST 接口：注册、登录、查询与更新资料。
 * <p>
 * 入参使用 DTO + {@code @Valid}（Jakarta Validation）；出参统一为 {@link UserResponse}（不含密码）。
 * 业务逻辑在 {@link UserService}，持久化经 {@link com.ebook.backend.repository.UserRepository}。
 * </p>
 */
@RestController
@RequestMapping("/api/v1/users")
public class UserController {

    /** 用户业务服务。 */
    private final UserService userService;

    /**
     * @param userService 由 Spring 注入的 {@link UserService}
     */
    public UserController(UserService userService) {
        this.userService = userService;
    }

    /**
     * 注册新用户；成功返回 201 Created。
     *
     * @param request 注册表单 JSON，经 {@code @Valid} 校验
     * @return 新用户信息（不含密码）
     */
    @PostMapping("/register")
    public ResponseEntity<UserResponse> register(@Valid @RequestBody UserRegisterRequest request) {
        return ResponseEntity.status(HttpStatus.CREATED).body(userService.register(request));
    }

    /**
     * 登录：校验库中用户名与密码（演示项目为明文比对）。
     *
     * @param request 用户名与密码
     * @return 用户信息，前端保存 {@link UserResponse#getId()}
     */
    @PostMapping("/login")
    public ResponseEntity<UserResponse> login(@Valid @RequestBody UserLoginRequest request) {
        return ResponseEntity.ok(userService.login(request));
    }

    /**
     * 按 id 查询用户公开资料。
     *
     * @param id 用户主键
     * @return 用户 DTO
     */
    @GetMapping("/{id}")
    public ResponseEntity<UserResponse> getUser(@PathVariable Long id) {
        return ResponseEntity.ok(userService.getById(id));
    }

    /**
     * 更新用户名、邮箱、个性签名（不可改密码）。
     *
     * @param id      要更新的用户 id，须与 body 中业务一致（当前未做 Token 校验）
     * @param request 新资料
     * @return 更新后的用户 DTO
     */
    @PutMapping("/{id}")
    public ResponseEntity<UserResponse> updateProfile(@PathVariable Long id,
                                                      @Valid @RequestBody UserProfileUpdateRequest request) {
        return ResponseEntity.ok(userService.updateProfile(id, request));
    }
}
