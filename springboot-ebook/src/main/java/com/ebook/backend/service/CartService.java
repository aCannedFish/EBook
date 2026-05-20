package com.ebook.backend.service;

import com.ebook.backend.dto.CartItemRequest;
import com.ebook.backend.dto.CartItemResponse;
import com.ebook.backend.dto.CartItemUpdateRequest;
import com.ebook.backend.dto.OrderResponse;
import com.ebook.backend.entity.Book;
import com.ebook.backend.entity.CartItem;
import com.ebook.backend.exception.ResourceNotFoundException;
import com.ebook.backend.repository.BookRepository;
import com.ebook.backend.repository.CartItemRepository;
import com.ebook.backend.repository.UserRepository;
import java.util.List;
import org.springframework.stereotype.Service;

/**
 * 购物车业务服务。
 * <p>
 * 被 {@link com.ebook.backend.controller.CartController} 调用；
 * 依赖 {@link CartItemRepository}、{@link BookRepository}、{@link UserRepository}；
 * 结算时编排 {@link OrderService#createOrders} 并删除已下单的购物车行。
 * </p>
 * <p>
 * 业务规则：每用户每书一行（表唯一键）；单书数量上限 4；仅 {@code selected=true} 的行参与结算。
 * </p>
 */
@Service
public class CartService {

    /** 单本书在购物车中的最大购买数量。 */
    private static final int MAX_QTY_PER_BOOK = 4;

    /** 购物车行持久化。 */
    private final CartItemRepository cartItemRepository;

    /** 用于 ensureUser 校验用户存在。 */
    private final UserRepository userRepository;

    /** 加购、结算时校验书籍存在并读取 id。 */
    private final BookRepository bookRepository;

    /** 结算时创建订单。 */
    private final OrderService orderService;

    /**
     * @param cartItemRepository 购物车表仓储
     * @param userRepository     用户表仓储
     * @param bookRepository     图书表仓储
     * @param orderService       订单服务（结算编排）
     */
    public CartService(CartItemRepository cartItemRepository,
                       UserRepository userRepository,
                       BookRepository bookRepository,
                       OrderService orderService) {
        this.cartItemRepository = cartItemRepository;
        this.userRepository = userRepository;
        this.bookRepository = bookRepository;
        this.orderService = orderService;
    }

    /**
     * 查询用户购物车并转为 {@link CartItemResponse} 列表。
     *
     * @param userId 用户主键
     * @return 购物车 DTO 列表
     */
    public List<CartItemResponse> getCartItems(Long userId) {
        ensureUser(userId);
        return cartItemRepository.findByUserId(userId)
                .stream()
                .map(this::toResponse)
                .toList();
    }

    /**
     * 加购：存在则累加数量，不存在则新建行；数量不超过 {@link #MAX_QTY_PER_BOOK}。
     *
     * @param userId  购物车所属用户
     * @param request 含 bookId、可选 qty
     * @return 更新后的完整购物车列表
     */
    public List<CartItemResponse> addToCart(Long userId, CartItemRequest request) {
        ensureUser(userId);
        Book book = bookRepository.findById(request.getBookId())
                .orElseThrow(() -> new ResourceNotFoundException("book not found: " + request.getBookId()));
        int increment = request.getQty() == null ? 1 : request.getQty();
        if (increment < 1) {
            throw new IllegalArgumentException("qty must be >= 1");
        }

        CartItem item = cartItemRepository.findByUserIdAndBookId(userId, book.getId())
                .orElseGet(() -> {
                    CartItem created = new CartItem();
                    created.setUserId(userId);
                    created.setBookId(book.getId());
                    created.setQty(0);
                    created.setSelected(true);
                    return created;
                });
        int nextQty = Math.min(item.getQty() + increment, MAX_QTY_PER_BOOK);
        item.setQty(nextQty);
        cartItemRepository.save(item);
        return getCartItems(userId);
    }

    /**
     * PATCH 式更新：仅当 request 中字段非 null 时才写入实体。
     *
     * @param userId  用户 id
     * @param bookId  书籍 id
     * @param request 部分更新字段
     * @return 更新后的完整购物车列表
     */
    public List<CartItemResponse> updateCartItem(Long userId, Long bookId, CartItemUpdateRequest request) {
        ensureUser(userId);
        CartItem item = cartItemRepository.findByUserIdAndBookId(userId, bookId)
                .orElseThrow(() -> new ResourceNotFoundException("cart item not found"));

        if (request.getQty() != null) {
            int qty = request.getQty();
            if (qty < 1 || qty > MAX_QTY_PER_BOOK) {
                throw new IllegalArgumentException("qty must be between 1 and 4");
            }
            item.setQty(qty);
        }

        if (request.getSelected() != null) {
            item.setSelected(request.getSelected());
        }

        cartItemRepository.save(item);
        return getCartItems(userId);
    }

    /**
     * 按用户与书 id 删除一行购物车记录。
     *
     * @param userId 用户 id
     * @param bookId 书籍 id
     * @return 删除后的完整购物车列表
     */
    public List<CartItemResponse> removeCartItem(Long userId, Long bookId) {
        ensureUser(userId);
        cartItemRepository.deleteByUserIdAndBookId(userId, bookId);
        return getCartItems(userId);
    }

    /**
     * 结算：将已勾选行转为订单并删除对应购物车行。
     *
     * @param userId 下单用户
     * @return 本次创建的订单列表；无勾选行时返回空列表
     */
    public List<OrderResponse> checkout(Long userId) {
        ensureUser(userId);
        List<CartItem> selectedItems = cartItemRepository.findByUserId(userId)
                .stream()
                .filter(CartItem::getSelected)
                .toList();
        if (selectedItems.isEmpty()) {
            return List.of();
        }
        List<OrderResponse> createdOrders = orderService.createOrders(userId, selectedItems);
        cartItemRepository.deleteAll(selectedItems);
        return createdOrders;
    }

    /**
     * 校验用户存在，供本类各方法复用。
     *
     * @param userId 待校验的用户 id
     */
    private void ensureUser(Long userId) {
        userRepository.findById(userId)
                .orElseThrow(() -> new ResourceNotFoundException("user not found: " + userId));
    }

    /**
     * 持久化实体 → API 响应 DTO。
     *
     * @param item 购物车行实体
     * @return 对外 DTO
     */
    private CartItemResponse toResponse(CartItem item) {
        CartItemResponse response = new CartItemResponse();
        response.setBookId(item.getBookId());
        response.setQty(item.getQty());
        response.setSelected(item.getSelected());
        return response;
    }
}
