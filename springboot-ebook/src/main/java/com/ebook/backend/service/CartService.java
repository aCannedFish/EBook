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

    /** 单本书在购物车中的最大购买数量 */
    private static final int MAX_QTY_PER_BOOK = 4;

    private final CartItemRepository cartItemRepository;
    private final UserRepository userRepository;
    private final BookRepository bookRepository;
    private final OrderService orderService;

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
     * <p>
     * 逻辑说明：
     * <ol>
     *   <li>{@code orElseGet}：无行时创建 transient {@link CartItem}，qty 先置 0 再参与累加；</li>
     *   <li>{@code save}：JPA 对无 id 行 INSERT，有 id 行 UPDATE；</li>
     *   <li>返回全量列表，供前端刷新整张购物车表。</li>
     * </ol>
     * </p>
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
     */
    public List<CartItemResponse> removeCartItem(Long userId, Long bookId) {
        ensureUser(userId);
        cartItemRepository.deleteByUserIdAndBookId(userId, bookId);
        return getCartItems(userId);
    }

    /**
     * 结算：将已勾选行转为订单并删除对应购物车行。
     * <p>
     * 跨服务调用 {@link OrderService#createOrders}；当前未使用 {@code @Transactional}，
     * 极端情况下可能出现订单已建但购物车未删，生产环境建议在方法上加事务注解。
     * </p>
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
     */
    private void ensureUser(Long userId) {
        userRepository.findById(userId)
                .orElseThrow(() -> new ResourceNotFoundException("user not found: " + userId));
    }

    /**
     * 持久化实体 → API 响应 DTO（不含书名等，由前端 join books 数据）。
     */
    private CartItemResponse toResponse(CartItem item) {
        CartItemResponse response = new CartItemResponse();
        response.setBookId(item.getBookId());
        response.setQty(item.getQty());
        response.setSelected(item.getSelected());
        return response;
    }
}
