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

@Service
public class CartService {

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

    public List<CartItemResponse> getCartItems(Long userId) {
        ensureUser(userId);
        return cartItemRepository.findByUserId(userId)
                .stream()
                .map(this::toResponse)
                .toList();
    }

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
        int nextQty = Math.min(item.getQty() + increment, 4);
        item.setQty(nextQty);
        cartItemRepository.save(item);
        return getCartItems(userId);
    }

    public List<CartItemResponse> updateCartItem(Long userId, Long bookId, CartItemUpdateRequest request) {
        ensureUser(userId);
        CartItem item = cartItemRepository.findByUserIdAndBookId(userId, bookId)
                .orElseThrow(() -> new ResourceNotFoundException("cart item not found"));

        if (request.getQty() != null) {
            int qty = request.getQty();
            if (qty < 1 || qty > 4) {
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

    public List<CartItemResponse> removeCartItem(Long userId, Long bookId) {
        ensureUser(userId);
        cartItemRepository.deleteByUserIdAndBookId(userId, bookId);
        return getCartItems(userId);
    }

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
