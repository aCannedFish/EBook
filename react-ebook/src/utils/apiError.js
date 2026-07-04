/** 从 fetch/action 抛出的 Error 中提取可展示的中文提示。 */
export function getApiErrorMessage(error, fallback = "操作失败，请稍后重试。") {
  const message = error?.message;
  if (!message || message.startsWith("request failed:")) {
    return fallback;
  }
  return String(message);
}
