package com.ebook.backend.dto;

import jakarta.validation.constraints.NotBlank;

public class OrderStatusRequest {

    @NotBlank(message = "status is required")
    private String status;

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }
}
