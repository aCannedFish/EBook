package com.ebook.backend.service;

import com.ebook.backend.dto.BookSalesStatResponse;
import com.ebook.backend.dto.MyPurchaseStatResponse;
import com.ebook.backend.dto.UserSpendingStatResponse;
import java.time.LocalDateTime;
import java.util.List;

/**
 * 统计业务服务接口。
 */
public interface StatsService {

    List<BookSalesStatResponse> bookSalesRanking(Long operatorId, LocalDateTime from, LocalDateTime to);

    List<UserSpendingStatResponse> userSpendingRanking(Long operatorId, LocalDateTime from, LocalDateTime to);

    MyPurchaseStatResponse myPurchaseStats(Long userId, LocalDateTime from, LocalDateTime to);
}
