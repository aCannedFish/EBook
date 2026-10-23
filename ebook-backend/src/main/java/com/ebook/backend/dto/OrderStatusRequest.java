package com.ebook.backend.dto;

import jakarta.validation.constraints.NotBlank;

/**
 * 更新订单状态 API 请求体。
 * <p>
 * {@link #status} 合法取值在 {@link com.ebook.backend.service.OrderService#updateStatus} 中校验：
 * {@code pending}、{@code paid}、{@code cancelled}。
 * </p>
 */
public class OrderStatusRequest {

    /** 目标状态，不能为空。 */
    @NotBlank(message = "status is required")
    private String status;

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }
}
