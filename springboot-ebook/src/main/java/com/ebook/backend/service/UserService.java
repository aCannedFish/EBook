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

@Service
public class UserService {

    private final UserRepository userRepository;

    public UserService(UserRepository userRepository) {
        this.userRepository = userRepository;
    }

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

    public UserResponse login(UserLoginRequest request) {
        User user = userRepository.findByUsername(request.getUsername())
                .orElseThrow(() -> new IllegalArgumentException("invalid username or password"));
        if (!user.getPassword().equals(request.getPassword())) {
            throw new IllegalArgumentException("invalid username or password");
        }
        return toResponse(user);
    }

    public UserResponse getById(Long id) {
        User user = userRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("user not found: " + id));
        return toResponse(user);
    }

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
