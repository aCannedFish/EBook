export const MAX_QTY_PER_BOOK = 4;

export function isOutOfStock(book) {
  return Number(book?.stockQty ?? 0) <= 0;
}

/** 单本书在购物车中允许的最大数量（受库存与业务上限约束）。 */
export function maxPurchasableQty(book) {
  const stock = Number(book?.stockQty ?? 0);
  if (stock <= 0) {
    return 0;
  }
  return Math.min(MAX_QTY_PER_BOOK, stock);
}

/** 结算前客户端预检：返回第一条库存问题说明，无问题则返回 null。 */
export function validateCheckoutSelection(selectedRows) {
  if (!selectedRows.length) {
    return "请先勾选要结算的商品。";
  }
  for (const row of selectedRows) {
    const book = row.book;
    const qty = Number(row.qty) || 0;
    const stock = Number(book?.stockQty ?? 0);
    const title = book?.title || "该书籍";
    if (stock <= 0) {
      return `「${title}」已缺货，请移除后再结算。`;
    }
    if (qty > stock) {
      return `「${title}」库存不足：当前仅剩 ${stock} 本，购物车中为 ${qty} 本。请调整数量。`;
    }
  }
  return null;
}
