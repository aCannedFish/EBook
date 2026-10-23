/** 金额格式化为两位小数。 */
export function formatPrice(value) {
  return `￥${Number(value || 0).toFixed(2)}`;
}

/** 将 ISO 日期字符串格式化为本地可读文本。 */
export function formatDateTime(value) {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString("zh-CN");
}
