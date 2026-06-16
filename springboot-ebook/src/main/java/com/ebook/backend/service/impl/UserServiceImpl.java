package com.ebook.backend.service.impl;

import com.ebook.backend.dto.UserLoginRequest;
import com.ebook.backend.dto.UserProfileUpdateRequest;
import com.ebook.backend.dto.UserRegisterRequest;
import com.ebook.backend.dto.UserResponse;
import com.ebook.backend.entity.User;
import com.ebook.backend.exception.ResourceNotFoundException;
import com.ebook.backend.repository.UserRepository;
import com.ebook.backend.service.UserService;
import com.ebook.backend.service.support.AdminGuard;
import java.util.List;
import java.util.Optional;
import org.springframework.stereotype.Service;

/**
 * {@link UserService} 的 Spring 实现。
 */
@Service
public class UserServiceImpl implements UserService {

    private final UserRepository userRepository;

    public UserServiceImpl(UserRepository userRepository) {
        this.userRepository = userRepository;
    }

    @Override
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
        user.setEnabled(true);

        return toResponse(userRepository.save(user));
    }

    @Override
    public UserResponse login(UserLoginRequest request) {
        User user = userRepository.findByUsername(request.getUsername())
                .orElseThrow(() -> new IllegalArgumentException("invalid username or password"));
        if (Boolean.FALSE.equals(user.getEnabled())) {
            throw new IllegalArgumentException("您的账号已经被禁用");
        }
        if (!user.getPassword().equals(request.getPassword())) {
            throw new IllegalArgumentException("invalid username or password");
        }
        return toResponse(user);
    }

    @Override
    public UserResponse getById(Long id) {
        User user = userRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("user not found: " + id));
        return toResponse(user);
    }

    @Override
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

        return toResponse(userRepository.save(user));
    }

    @Override
    public List<UserResponse> listAllForAdmin(Long operatorId) {
        AdminGuard.ensureAdmin(userRepository, operatorId);
        return userRepository.findAll()
                .stream()
                .map(this::toResponse)
                .toList();
    }

    @Override
    public UserResponse setEnabled(Long operatorId, Long userId, boolean enabled) {
        AdminGuard.ensureAdmin(userRepository, operatorId);
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new ResourceNotFoundException("user not found: " + userId));
        if (AdminGuard.isAdmin(user) && !enabled) {
            throw new IllegalArgumentException("cannot disable admin account");
        }
        user.setEnabled(enabled);
        return toResponse(userRepository.save(user));
    }

    private UserResponse toResponse(User user) {
        UserResponse response = new UserResponse();
        response.setId(user.getId());
        response.setUsername(user.getUsername());
        response.setEmail(user.getEmail());
        response.setSignature(user.getSignature());
        response.setLevel(user.getLevel());
        response.setEnabled(user.getEnabled());
        response.setAdmin(AdminGuard.isAdmin(user));
        return response;
    }
}
