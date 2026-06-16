package com.ebook.backend.dto;

import jakarta.validation.constraints.NotNull;

/**
 * 管理员禁用/解禁用户请求体。
 */
public class UserEnabledRequest {

    @NotNull(message = "enabled is required")
    private Boolean enabled;

    public Boolean getEnabled() {
        return enabled;
    }

    public void setEnabled(Boolean enabled) {
        this.enabled = enabled;
    }
}
