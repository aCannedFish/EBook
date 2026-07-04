package com.ebook.backend.service.impl;

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
import com.ebook.backend.service.CartService;
import com.ebook.backend.service.OrderService;
import com.ebook.backend.service.support.StockHelper;
import java.util.List;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * {@link CartService} 的 Spring 实现。
 */
@Service
public class CartServiceImpl implements CartService {

    private final CartItemRepository cartItemRepository;
    private final UserRepository userRepository;
    private final BookRepository bookRepository;
    private final OrderService orderService;

    public CartServiceImpl(CartItemRepository cartItemRepository,
                           UserRepository userRepository,
                           BookRepository bookRepository,
                           OrderService orderService) {
        this.cartItemRepository = cartItemRepository;
        this.userRepository = userRepository;
        this.bookRepository = bookRepository;
        this.orderService = orderService;
    }

    @Override
    public List<CartItemResponse> getCartItems(Long userId) {
        ensureUser(userId);
        return cartItemRepository.findByUserId(userId)
                .stream()
                .map(this::toResponse)
                .toList();
    }

    @Override
    public List<CartItemResponse> addToCart(Long userId, CartItemRequest request) {
        ensureUser(userId);
        Book book = bookRepository.findById(request.getBookId())
                .orElseThrow(() -> new ResourceNotFoundException("book not found: " + request.getBookId()));
        int increment = request.getQty() == null ? 1 : request.getQty();
        if (increment < 1) {
            throw new IllegalArgumentException("购买数量至少为 1 本。");
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
        StockHelper.ensureCanAddToCart(book, item.getQty(), increment);
        int nextQty = Math.min(item.getQty() + increment, StockHelper.MAX_QTY_PER_BOOK);
        item.setQty(nextQty);
        cartItemRepository.save(item);
        return getCartItems(userId);
    }

    @Override
    public List<CartItemResponse> updateCartItem(Long userId, Long bookId, CartItemUpdateRequest request) {
        ensureUser(userId);
        CartItem item = cartItemRepository.findByUserIdAndBookId(userId, bookId)
                .orElseThrow(() -> new ResourceNotFoundException("cart item not found"));
        Book book = bookRepository.findById(bookId)
                .orElseThrow(() -> new ResourceNotFoundException("book not found: " + bookId));

        if (request.getQty() != null) {
            int qty = request.getQty();
            if (qty < 1 || qty > StockHelper.MAX_QTY_PER_BOOK) {
                throw new IllegalArgumentException("每本书购物车数量需在 1～" + StockHelper.MAX_QTY_PER_BOOK + " 本之间。");
            }
            StockHelper.ensureSufficient(book, qty);
            item.setQty(qty);
        }

        if (request.getSelected() != null) {
            item.setSelected(request.getSelected());
        }

        cartItemRepository.save(item);
        return getCartItems(userId);
    }

    @Override
    public List<CartItemResponse> removeCartItem(Long userId, Long bookId) {
        ensureUser(userId);
        cartItemRepository.deleteByUserIdAndBookId(userId, bookId);
        return getCartItems(userId);
    }

    @Override
    @Transactional
    public List<OrderResponse> checkout(Long userId) {
        ensureUser(userId);
        List<CartItem> selectedItems = cartItemRepository.findByUserId(userId)
                .stream()
                .filter(CartItem::getSelected)
                .toList();
        if (selectedItems.isEmpty()) {
            throw new IllegalArgumentException("请先勾选要结算的商品。");
        }
        List<OrderResponse> createdOrders = orderService.createOrders(userId, selectedItems);
        cartItemRepository.deleteByUserId(userId);
        return createdOrders;
    }

    private void ensureUser(Long userId) {
        userRepository.findById(userId)
                .orElseThrow(() -> new ResourceNotFoundException("user not found: " + userId));
    }

    private CartItemResponse toResponse(CartItem item) {
        CartItemResponse response = new CartItemResponse();
        response.setBookId(item.getBookId());
        response.setQty(item.getQty());
        response.setSelected(item.getSelected());
        return response;
    }
}
