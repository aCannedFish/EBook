package com.ebook.backend.service.impl;

import com.ebook.backend.dto.OrderResponse;
import com.ebook.backend.entity.CartItem;
import com.ebook.backend.entity.User;
import com.ebook.backend.repository.BookRepository;
import com.ebook.backend.repository.CartItemRepository;
import com.ebook.backend.repository.UserRepository;
import com.ebook.backend.service.OrderService;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * 购物车服务单元测试：覆盖结算后清空整辆购物车。
 */
@ExtendWith(MockitoExtension.class)
class CartServiceImplTest {

    @Mock
    private CartItemRepository cartItemRepository;

    @Mock
    private UserRepository userRepository;

    @Mock
    private BookRepository bookRepository;

    @Mock
    private OrderService orderService;

    @InjectMocks
    private CartServiceImpl cartService;

    @Test
    void checkout_clearsEntireCartAfterOrder() {
        Long userId = 2L;
        User user = new User();
        user.setId(userId);
        when(userRepository.findById(userId)).thenReturn(Optional.of(user));

        CartItem selected = new CartItem();
        selected.setUserId(userId);
        selected.setBookId(1L);
        selected.setQty(1);
        selected.setSelected(true);

        CartItem unselected = new CartItem();
        unselected.setUserId(userId);
        unselected.setBookId(2L);
        unselected.setQty(1);
        unselected.setSelected(false);

        when(cartItemRepository.findByUserId(userId)).thenReturn(List.of(selected, unselected));

        OrderResponse order = new OrderResponse();
        order.setId("ORD-test-0001");
        when(orderService.createOrders(userId, List.of(selected))).thenReturn(List.of(order));

        List<OrderResponse> created = cartService.checkout(userId);

        assertEquals(1, created.size());
        verify(orderService).createOrders(userId, List.of(selected));
        verify(cartItemRepository).deleteByUserId(eq(userId));
    }
}
