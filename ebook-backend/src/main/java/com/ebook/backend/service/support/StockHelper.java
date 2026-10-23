package com.ebook.backend.service.support;

import com.ebook.backend.entity.Book;

/**
 * 根据库存数量同步 stockType/stockText 展示字段，并提供库存校验错误信息。
 */
public final class StockHelper {

    public static final int MAX_QTY_PER_BOOK = 4;

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

    public static int availableQty(Book book) {
        return book.getStockQty() == null ? 0 : book.getStockQty();
    }

    /**
     * 校验请求数量是否可被当前库存满足；不满足时抛出带中文说明的 IllegalArgumentException。
     */
    public static void ensureSufficient(Book book, int requestedQty) {
        String title = book.getTitle() == null ? "该书籍" : book.getTitle();
        int stock = availableQty(book);
        if (stock <= 0) {
            throw new IllegalArgumentException("《" + title + "》已缺货，无法购买。");
        }
        if (requestedQty < 1) {
            throw new IllegalArgumentException("购买数量至少为 1 本。");
        }
        if (requestedQty > stock) {
            throw new IllegalArgumentException(
                    "《" + title + "》库存不足：当前仅剩 " + stock + " 本，您需要 " + requestedQty + " 本。");
        }
    }

    public static void ensureCanAddToCart(Book book, int currentCartQty, int increment) {
        int nextQty = Math.min(currentCartQty + increment, MAX_QTY_PER_BOOK);
        ensureSufficient(book, nextQty);
    }
}
