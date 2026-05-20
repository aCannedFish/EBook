package com.ebook.backend.service;

import com.ebook.backend.dto.UserLoginRequest;
import com.ebook.backend.dto.UserProfileUpdateRequest;
import com.ebook.backend.dto.UserRegisterRequest;
import com.ebook.backend.dto.UserResponse;
import com.ebook.backend.entity.User;
import com.ebook.backend.exception.ResourceNotFoundException;
import com.ebook.backend.repository.UserRepository;
import java.util.Optional;
import org.springframework.stereotype.Service;

/**
 * 用户业务服务：注册、登录、资料查询与更新。
 * <p>
 * 与 {@link com.ebook.backend.controller.UserController} 配合；
 * 持久化通过 {@link UserRepository}（Spring Data JPA）。
 * 密码为演示级明文存储与比对，生产环境应使用 {@code PasswordEncoder}。
 * </p>
 */
@Service
public class UserService {

    private final UserRepository userRepository;

    public UserService(UserRepository userRepository) {
        this.userRepository = userRepository;
    }

    /**
     * 注册：校验用户名、邮箱唯一后插入 {@link User}。
     *
     * @throws IllegalArgumentException 用户名或邮箱已存在（→ 400）
     */
    public UserResponse register(UserRegisterRequest request) {
        userRepository.findByUsername(request.getUsername()).ifPresent(user -> {
            throw new IllegalArgumentException("username already exists");
        });
        userRepository.findByEmail(request.getEmail()).ifPresent(user -> {
            throw new IllegalArgumentException("email already exists");
        });

        User user = new User();
        user.setUsername(request.getUsername());
        user.setPassword(request.getPassword());
        user.setEmail(request.getEmail());
        user.setSignature(request.getSignature() == null ? "" : request.getSignature());
        user.setLevel(request.getLevel() == null || request.getLevel().isBlank()
                ? "普通用户"
                : request.getLevel());

        User saved = userRepository.save(user);
        return toResponse(saved);
    }

    /**
     * 登录：按用户名查库并比对密码；失败统一文案，避免泄露「用户是否存在」。
     *
     * @throws IllegalArgumentException 用户不存在或密码错误（→ 400）
     */
    public UserResponse login(UserLoginRequest request) {
        User user = userRepository.findByUsername(request.getUsername())
                .orElseThrow(() -> new IllegalArgumentException("invalid username or password"));
        if (!user.getPassword().equals(request.getPassword())) {
            throw new IllegalArgumentException("invalid username or password");
        }
        return toResponse(user);
    }

    /**
     * 按 id 获取用户公开信息。
     */
    public UserResponse getById(Long id) {
        User user = userRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("user not found: " + id));
        return toResponse(user);
    }

    /**
     * 更新资料：允许改用户名/邮箱，但不得与其他用户冲突。
     */
    public UserResponse updateProfile(Long id, UserProfileUpdateRequest request) {
        User user = userRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("user not found: " + id));

        Optional<User> byUsername = userRepository.findByUsername(request.getUsername());
        if (byUsername.isPresent() && !byUsername.get().getId().equals(id)) {
            throw new IllegalArgumentException("username already exists");
        }

        Optional<User> byEmail = userRepository.findByEmail(request.getEmail());
        if (byEmail.isPresent() && !byEmail.get().getId().equals(id)) {
            throw new IllegalArgumentException("email already exists");
        }

        user.setUsername(request.getUsername());
        user.setEmail(request.getEmail());
        user.setSignature(request.getSignature() == null ? "" : request.getSignature());

        User saved = userRepository.save(user);
        return toResponse(saved);
    }

    /**
     * Entity → 对外 DTO，显式排除 password。
     */
    private UserResponse toResponse(User user) {
        UserResponse response = new UserResponse();
        response.setId(user.getId());
        response.setUsername(user.getUsername());
        response.setEmail(user.getEmail());
        response.setSignature(user.getSignature());
        response.setLevel(user.getLevel());
        return response;
    }
}
