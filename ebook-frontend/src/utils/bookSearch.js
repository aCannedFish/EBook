import { pinyin } from "pinyin-pro";

/**
 * 把书名、作者、分类转成可搜索文本，同时带上全拼和首字母。
 *
 * 例如「算法导论」会得到 suanfadaolun 与 sfdl，用户输入中文、全拼或
 * 首字母都能命中；英文书名保持原样，因此英文关键词也照常匹配。
 */
export function buildBookSearchText(book) {
  const source = [book.title, book.author, book.category].join(" ");
  const options = { toneType: "none", type: "array" };
  const full = pinyin(source, options).join("");
  const initials = pinyin(source, { ...options, pattern: "first" }).join("");
  return normalize(`${source} ${full} ${initials}`);
}

/** 去掉空白和常见分隔符，让「clean code」「clean-code」等价。 */
export function normalize(value) {
  return String(value || "")
    .toLowerCase()
    .replace(/[\s\-_/·.,:;'"()（）【】]+/g, "");
}
