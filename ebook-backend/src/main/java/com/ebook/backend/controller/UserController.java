package com.ebook.backend.controller;

import com.ebook.backend.security.CurrentUser;
import com.ebook.backend.security.JwtTokenService;
import com.ebook.backend.dto.LoginResponse;

import com.ebook.backend.dto.UserEnabledRequest;
import com.ebook.backend.dto.UserLoginRequest;
import com.ebook.backend.dto.UserProfileUpdateRequest;
import com.ebook.backend.dto.UserRegisterRequest;
import com.ebook.backend.dto.UserResponse;
import com.ebook.backend.service.UserService;
import jakarta.validation.Valid;
import java.util.List;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * 用户 REST 接口。
 */
@RestController
@RequestMapping("/api/v1/users")
public class UserController {

    private final UserService userService;
    private final CurrentUser currentUser;
    private final JwtTokenService tokens;

    public UserController(UserService userService, CurrentUser currentUser, JwtTokenService tokens) {
        this.userService = userService;
        this.currentUser = currentUser;
        this.tokens = tokens;
    }

    @PostMapping("/register")
    public ResponseEntity<UserResponse> register(@Valid @RequestBody UserRegisterRequest request) {
        return ResponseEntity.status(HttpStatus.CREATED).body(userService.register(request));
    }

    @PostMapping("/login")
    public ResponseEntity<LoginResponse> login(@Valid @RequestBody UserLoginRequest request) {
        UserResponse user = userService.login(request);
        return ResponseEntity.ok(new LoginResponse(user, tokens.issue(user), "Bearer", tokens.ttlSeconds()));
    }

    /** AI 服务用当前 JWT 验证书城身份，无需相信客户端提供的用户编号。 */
    @GetMapping("/me")
    public UserResponse current() {
        return userService.getById(currentUser.principal().id());
    }

    @GetMapping("/{id}")
    public ResponseEntity<UserResponse> getUser(@PathVariable Long id) {
        currentUser.requireSelf(id);
        return ResponseEntity.ok(userService.getById(id));
    }

    @PutMapping("/{id}")
    public ResponseEntity<UserResponse> updateProfile(@PathVariable Long id,
                                                      @Valid @RequestBody UserProfileUpdateRequest request) {
        currentUser.requireSelf(id);
        return ResponseEntity.ok(userService.updateProfile(id, request));
    }

    @GetMapping("/admin/all")
    public List<UserResponse> listAllForAdmin(@RequestParam Long operatorId) {
        return userService.listAllForAdmin(currentUser.adminId(operatorId));
    }

    @PutMapping("/admin/{userId}/enabled")
    public UserResponse setEnabled(@RequestParam Long operatorId,
                                   @PathVariable Long userId,
                                   @Valid @RequestBody UserEnabledRequest request) {
        return userService.setEnabled(currentUser.adminId(operatorId), userId, request.getEnabled());
    }
}
