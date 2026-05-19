package com.ebook.backend.controller;

import com.ebook.backend.dto.CartItemRequest;
import com.ebook.backend.dto.CartItemResponse;
import com.ebook.backend.dto.CartItemUpdateRequest;
import com.ebook.backend.dto.OrderResponse;
import com.ebook.backend.service.CartService;
import jakarta.validation.Valid;
import java.util.List;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/cart")
public class CartController {

    private final CartService cartService;

    public CartController(CartService cartService) {
        this.cartService = cartService;
    }

    @GetMapping("/{userId}")
    public List<CartItemResponse> getCart(@PathVariable Long userId) {
        return cartService.getCartItems(userId);
    }

    @PostMapping("/{userId}/items")
    public List<CartItemResponse> addItem(@PathVariable Long userId,
                                          @Valid @RequestBody CartItemRequest request) {
        return cartService.addToCart(userId, request);
    }

    @PatchMapping("/{userId}/items/{bookId}")
    public List<CartItemResponse> updateItem(@PathVariable Long userId,
                                             @PathVariable Long bookId,
                                             @RequestBody CartItemUpdateRequest request) {
        return cartService.updateCartItem(userId, bookId, request);
    }

    @DeleteMapping("/{userId}/items/{bookId}")
    public List<CartItemResponse> removeItem(@PathVariable Long userId,
                                             @PathVariable Long bookId) {
        return cartService.removeCartItem(userId, bookId);
    }

    @PostMapping("/{userId}/checkout")
    public List<OrderResponse> checkout(@PathVariable Long userId) {
        return cartService.checkout(userId);
    }
}
