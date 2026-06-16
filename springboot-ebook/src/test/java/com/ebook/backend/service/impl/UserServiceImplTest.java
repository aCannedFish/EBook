package com.ebook.backend.service.impl;

import com.ebook.backend.dto.UserLoginRequest;
import com.ebook.backend.entity.User;
import com.ebook.backend.repository.UserRepository;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.Mockito.when;

/**
 * 用户服务单元测试：覆盖禁用账号登录拦截。
 */
@ExtendWith(MockitoExtension.class)
class UserServiceImplTest {

    @Mock
    private UserRepository userRepository;

    @InjectMocks
    private UserServiceImpl userService;

    @Test
    void login_rejectsDisabledUser() {
        User user = new User();
        user.setUsername("DefaultUser");
        user.setPassword("123456");
        user.setEnabled(false);
        when(userRepository.findByUsername("DefaultUser")).thenReturn(Optional.of(user));

        UserLoginRequest request = new UserLoginRequest();
        request.setUsername("DefaultUser");
        request.setPassword("123456");

        IllegalArgumentException ex = assertThrows(IllegalArgumentException.class, () -> userService.login(request));
        assertEquals("您的账号已经被禁用", ex.getMessage());
    }
}
