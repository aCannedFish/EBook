package com.ebook.backend.service.support;

import com.ebook.backend.entity.Book;

/**
 * 根据库存数量同步 stockType/stockText 展示字段。
 */
public final class StockHelper {

    private StockHelper() {
    }

    public static void syncStockDisplay(Book book) {
        int qty = book.getStockQty() == null ? 0 : book.getStockQty();
        if (qty <= 0) {
            book.setStockType("out");
            book.setStockText("缺货");
        } else if (qty <= 5) {
            book.setStockType("warn");
            book.setStockText("库存紧张");
        } else {
            book.setStockType("ok");
            book.setStockText("有货");
        }
    }
}
