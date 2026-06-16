package com.ebook.backend.service;

import com.ebook.backend.dto.UserLoginRequest;
import com.ebook.backend.dto.UserProfileUpdateRequest;
import com.ebook.backend.dto.UserRegisterRequest;
import com.ebook.backend.dto.UserResponse;
import java.util.List;

/**
 * 用户业务服务接口。
 */
public interface UserService {

    UserResponse register(UserRegisterRequest request);

    UserResponse login(UserLoginRequest request);

    UserResponse getById(Long id);

    UserResponse updateProfile(Long id, UserProfileUpdateRequest request);

    List<UserResponse> listAllForAdmin(Long operatorId);

    UserResponse setEnabled(Long operatorId, Long userId, boolean enabled);
}
