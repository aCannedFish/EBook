package com.ebook.backend.controller;

import com.ebook.backend.security.CurrentUser;

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

/**
 * 购物车 REST 接口。
 * <p>
 * 路径中的 {@code userId} 必须与 JWT 身份一致，或由管理员访问。
 * 写操作后多数接口返回**该用户完整购物车列表**（{@link CartItemResponse}），便于前端一次刷新 UI。
 * 结算委托 {@link CartService#checkout}，内部再调用 {@link com.ebook.backend.service.OrderService}。
 * </p>
 */
@RestController
@RequestMapping("/api/v1/cart")
public class CartController {

    /** 购物车业务服务。 */
    private final CartService cartService;
    private final CurrentUser currentUser;

    /**
     * @param cartService 由 Spring 注入的 {@link CartService}
     */
    public CartController(CartService cartService, CurrentUser currentUser) {
        this.cartService = cartService;
        this.currentUser = currentUser;
    }

    /**
     * 查询指定用户的全部购物车行。
     *
     * @param userId 用户主键
     * @return 购物车 DTO 列表
     */
    @GetMapping("/{userId}")
    public List<CartItemResponse> getCart(@PathVariable Long userId) {
        currentUser.requireSelf(userId);
        return cartService.getCartItems(userId);
    }

    /**
     * 加购：body 含 bookId、可选 qty；同书累加数量，上限 4。
     *
     * @param userId  购物车所属用户
     * @param request 含 bookId、qty
     * @return 更新后的完整购物车列表
     */
    @PostMapping("/{userId}/items")
    public List<CartItemResponse> addItem(@PathVariable Long userId,
                                          @Valid @RequestBody CartItemRequest request) {
        currentUser.requireSelf(userId);
        return cartService.addToCart(userId, request);
    }

    /**
     * 部分更新数量或勾选状态（PATCH 语义）。
     *
     * @param userId  用户 id
     * @param bookId  要更新的书籍 id
     * @param request 仅非 null 字段生效
     * @return 更新后的完整购物车列表
     */
    @PatchMapping("/{userId}/items/{bookId}")
    public List<CartItemResponse> updateItem(@PathVariable Long userId,
                                             @PathVariable Long bookId,
                                             @RequestBody CartItemUpdateRequest request) {
        currentUser.requireSelf(userId);
        return cartService.updateCartItem(userId, bookId, request);
    }

    /**
     * 删除购物车中某本书对应的一行。
     *
     * @param userId 用户 id
     * @param bookId 书籍 id
     * @return 删除后的完整购物车列表
     */
    @DeleteMapping("/{userId}/items/{bookId}")
    public List<CartItemResponse> removeItem(@PathVariable Long userId,
                                             @PathVariable Long bookId) {
        currentUser.requireSelf(userId);
        return cartService.removeCartItem(userId, bookId);
    }

    /**
     * 结算：将 selected=true 的行转为订单并删除这些购物车行。
     *
     * @param userId 下单用户
     * @return 本次创建的订单列表（可能为空，若无勾选行）
     */
    @PostMapping("/{userId}/checkout")
    public List<OrderResponse> checkout(@PathVariable Long userId) {
        currentUser.requireSelf(userId);
        return cartService.checkout(userId);
    }
}
