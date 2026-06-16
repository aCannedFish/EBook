package com.ebook.backend.controller;

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

    public UserController(UserService userService) {
        this.userService = userService;
    }

    @PostMapping("/register")
    public ResponseEntity<UserResponse> register(@Valid @RequestBody UserRegisterRequest request) {
        return ResponseEntity.status(HttpStatus.CREATED).body(userService.register(request));
    }

    @PostMapping("/login")
    public ResponseEntity<UserResponse> login(@Valid @RequestBody UserLoginRequest request) {
        return ResponseEntity.ok(userService.login(request));
    }

    @GetMapping("/{id}")
    public ResponseEntity<UserResponse> getUser(@PathVariable Long id) {
        return ResponseEntity.ok(userService.getById(id));
    }

    @PutMapping("/{id}")
    public ResponseEntity<UserResponse> updateProfile(@PathVariable Long id,
                                                      @Valid @RequestBody UserProfileUpdateRequest request) {
        return ResponseEntity.ok(userService.updateProfile(id, request));
    }

    @GetMapping("/admin/all")
    public List<UserResponse> listAllForAdmin(@RequestParam Long operatorId) {
        return userService.listAllForAdmin(operatorId);
    }

    @PutMapping("/admin/{userId}/enabled")
    public UserResponse setEnabled(@RequestParam Long operatorId,
                                   @PathVariable Long userId,
                                   @Valid @RequestBody UserEnabledRequest request) {
        return userService.setEnabled(operatorId, userId, request.getEnabled());
    }
}
