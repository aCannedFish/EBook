/** 本地静态封面文件名（与 public/assets 下文件一致）。 */
const COVER_FILENAME_BY_ISBN = {
  "978-0-00-000000-1": "Digital Fundamentals（Thomas.L.Floyd）.png",
  "978-1-00-000000-2": "Fundamentals of Computer Graphics（Steve Marschner）.png",
  "978-2-00-000000-3": "Intorduction to Computing Systems（Yale.N.Patt）.png",
  "978-3-00-000000-4": "Introduction To Algorithms（Thomas.H.Cormen）.png",
  "978-4-00-000000-5": "Qt 6 C++开发指南（王维波）.png",
  "978-5-00-000000-6": "应用随机过程（熊德文）.png",
  "978-6-00-000000-7": "深入理解计算机系统（兰德尔.E.布莱恩特，大卫.R.奥哈拉伦）.png",
  "978-7-00-000000-8": "量子物理（吕智国）.png"
};

/**
 * 解析图书封面 URL。
 * 优先按 ISBN 映射到 public/assets 中的真实文件名，避免 C++ 等含 + 号路径被浏览器误解析。
 */
export function resolveBookCover(rawBook) {
  const filename = COVER_FILENAME_BY_ISBN[rawBook?.isbn];
  if (filename) {
    return `/assets/${encodeURI(filename)}`;
  }

  const candidate = rawBook?.coverUrl || rawBook?.cover;
  if (!candidate) {
    return "/assets/logo.svg";
  }

  return normalizeCoverPath(candidate);
}

function normalizeCoverPath(path) {
  if (!path.startsWith("/assets/")) {
    return path;
  }

  const encodedName = path.slice("/assets/".length);
  try {
    const decoded = decodeURIComponent(encodedName.replace(/\+/g, "%2B"));
    return `/assets/${encodeURI(decoded)}`;
  } catch {
    return `/assets/${encodedName.replace(/\+/g, "%2B")}`;
  }
}
