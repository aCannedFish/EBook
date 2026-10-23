import { pinyin } from "pinyin-pro";

/**
 * 把书名、作者、分类转成可搜索文本，同时带上全拼和首字母。
 *
 * 例如「算法导论」会得到 suanfadaolun 与 sfdl，用户输入中文、全拼或
 * 首字母都能命中；英文书名保持原样，因此英文关键词也照常匹配。
 */
export function buildBookEntry(book) {
  const source = [book.title, book.author, book.category].join(" ");
  const options = { toneType: "none", type: "array" };
  const full = pinyin(source, options).join("");
  const initials = pinyin(source, { ...options, pattern: "first" }).join("");
  // 去掉书名开头的引号、书名号等装饰，避免《xxx》被归到 # 组。
  const title = String(book.title).replace(/^[^\p{L}\p{N}]+/u, "");
  const titlePinyin = pinyin(title, options).join("");
  const first = (pinyin(title, { ...options, pattern: "first" })[0] || "")
    .trim()
    .charAt(0)
    .toUpperCase();
  const initial = /^[A-Z]$/.test(first) ? first : "#";
  return {
    text: normalize(`${source} ${full} ${initials}`),
    initial,
    // 数字或符号开头的书名排在字母之后，不打断 A-Z 顺序。
    sortKey: initial === "#" ? `zzz${normalize(titlePinyin)}` : normalize(titlePinyin)
  };
}

/** 去掉空白和常见分隔符，让「clean code」「clean-code」等价。 */
export function normalize(value) {
  return String(value || "")
    .toLowerCase()
    .replace(/[\s\-_/·.,:;'"()（）【】]+/g, "");
}
