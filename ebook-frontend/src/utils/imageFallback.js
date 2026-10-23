const FALLBACK_SRC = "/assets/logo.svg";

/** 封面加载失败时回退到站点 Logo，避免重复触发 onError。 */
export function handleCoverImageError(event) {
  const image = event.currentTarget;
  if (image.dataset.fallbackApplied === "true") {
    return;
  }
  image.dataset.fallbackApplied = "true";
  image.src = FALLBACK_SRC;
}
