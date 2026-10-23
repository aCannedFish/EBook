import { setPageSearch } from "../data/appStore";

/** 处理顶栏搜索 intent；命中时返回 true，action 应 return null。 */
export function handleSetSearchIntent(formData, pageKey) {
  if (String(formData.get("intent") || "") !== "set-search") {
    return false;
  }
  setPageSearch(pageKey, String(formData.get("value") || ""));
  return true;
}
