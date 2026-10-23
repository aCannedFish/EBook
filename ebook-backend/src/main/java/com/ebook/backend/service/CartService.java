package com.ebook.backend.service;

import com.ebook.backend.dto.CartItemRequest;
import com.ebook.backend.dto.CartItemResponse;
import com.ebook.backend.dto.CartItemUpdateRequest;
import com.ebook.backend.dto.OrderResponse;
import java.util.List;

/**
 * 购物车业务服务接口。
 */
public interface CartService {

    List<CartItemResponse> getCartItems(Long userId);

    List<CartItemResponse> addToCart(Long userId, CartItemRequest request);

    List<CartItemResponse> updateCartItem(Long userId, Long bookId, CartItemUpdateRequest request);

    List<CartItemResponse> removeCartItem(Long userId, Long bookId);

    List<OrderResponse> checkout(Long userId);
}
