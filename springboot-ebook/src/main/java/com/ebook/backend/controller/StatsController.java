package com.ebook.backend.controller;

import com.ebook.backend.dto.BookSalesStatResponse;
import com.ebook.backend.dto.MyPurchaseStatResponse;
import com.ebook.backend.dto.UserSpendingStatResponse;
import com.ebook.backend.service.StatsService;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.LocalTime;
import java.util.List;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * 统计 REST 接口。
 */
@RestController
@RequestMapping("/api/v1/stats")
public class StatsController {

    private final StatsService statsService;

    public StatsController(StatsService statsService) {
        this.statsService = statsService;
    }

    @GetMapping("/admin/book-sales")
    public List<BookSalesStatResponse> bookSalesRanking(@RequestParam Long operatorId,
                                                        @RequestParam(required = false)
                                                        @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate from,
                                                        @RequestParam(required = false)
                                                        @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate to) {
        return statsService.bookSalesRanking(operatorId, toStart(from), toEnd(to));
    }

    @GetMapping("/admin/user-spending")
    public List<UserSpendingStatResponse> userSpendingRanking(@RequestParam Long operatorId,
                                                              @RequestParam(required = false)
                                                              @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate from,
                                                              @RequestParam(required = false)
                                                              @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate to) {
        return statsService.userSpendingRanking(operatorId, toStart(from), toEnd(to));
    }

    @GetMapping("/my/{userId}")
    public MyPurchaseStatResponse myPurchaseStats(@PathVariable Long userId,
                                                  @RequestParam(required = false)
                                                  @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate from,
                                                  @RequestParam(required = false)
                                                  @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate to) {
        return statsService.myPurchaseStats(userId, toStart(from), toEnd(to));
    }

    private LocalDateTime toStart(LocalDate date) {
        return date == null ? null : date.atStartOfDay();
    }

    private LocalDateTime toEnd(LocalDate date) {
        return date == null ? null : date.atTime(LocalTime.MAX);
    }
}
