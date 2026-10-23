package com.ebook.backend.service.impl;

import com.ebook.backend.dto.OrderResponse;
import com.ebook.backend.entity.Book;
import com.ebook.backend.entity.CartItem;
import com.ebook.backend.entity.OrderEntity;
import com.ebook.backend.entity.User;
import com.ebook.backend.repository.BookRepository;
import com.ebook.backend.repository.OrderRepository;
import com.ebook.backend.repository.UserRepository;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * 订单服务单元测试：覆盖结算扣减库存。
 */
@ExtendWith(MockitoExtension.class)
class OrderServiceImplTest {

    @Mock
    private OrderRepository orderRepository;

    @Mock
    private UserRepository userRepository;

    @Mock
    private BookRepository bookRepository;

    @InjectMocks
    private OrderServiceImpl orderService;

    @Test
    void createOrders_deductsStock() {
        Long userId = 2L;
        User user = new User();
        user.setId(userId);
        when(userRepository.findById(userId)).thenReturn(Optional.of(user));

        Book book = new Book();
        book.setId(1L);
        book.setTitle("Test Book");
        book.setPrice(59);
        book.setStockQty(10);
        book.setStockType("ok");
        book.setStockText("有货");
        when(bookRepository.findById(1L)).thenReturn(Optional.of(book));
        when(bookRepository.save(any(Book.class))).thenAnswer(invocation -> invocation.getArgument(0));

        CartItem cartItem = new CartItem();
        cartItem.setUserId(userId);
        cartItem.setBookId(1L);
        cartItem.setQty(2);
        cartItem.setSelected(true);

        when(orderRepository.save(any(OrderEntity.class))).thenAnswer(invocation -> {
            OrderEntity order = invocation.getArgument(0);
            order.setId(100L);
            return order;
        });

        List<OrderResponse> orders = orderService.createOrders(userId, List.of(cartItem));

        assertEquals(1, orders.size());
        assertEquals(8, book.getStockQty());

        ArgumentCaptor<Book> bookCaptor = ArgumentCaptor.forClass(Book.class);
        verify(bookRepository).save(bookCaptor.capture());
        assertEquals(8, bookCaptor.getValue().getStockQty());
    }

    @Test
    void createOrders_rejectsInsufficientStock() {
        Long userId = 2L;
        User user = new User();
        user.setId(userId);
        when(userRepository.findById(userId)).thenReturn(Optional.of(user));

        Book book = new Book();
        book.setId(1L);
        book.setTitle("Test Book");
        book.setPrice(59);
        book.setStockQty(1);
        when(bookRepository.findById(1L)).thenReturn(Optional.of(book));

        CartItem cartItem = new CartItem();
        cartItem.setUserId(userId);
        cartItem.setBookId(1L);
        cartItem.setQty(3);
        cartItem.setSelected(true);

        IllegalArgumentException ex = assertThrows(
                IllegalArgumentException.class,
                () -> orderService.createOrders(userId, List.of(cartItem))
        );
        assertEquals("《Test Book》库存不足：当前仅剩 1 本，您需要 3 本。", ex.getMessage());
    }
}
