import { Col, Row, Space, Tag, Typography, Alert } from "antd";
import { useEffect, useMemo, useState } from "react";
import BookCard from "../components/BookCard";
import { redirect, useActionData, useLoaderData } from "react-router-dom";
import { addToCart, ensureBooksLoaded, setPageSearch } from "../data/appStore";
import { requireAuthSnapshot } from "../routes/authRouteHandlers";
import { getApiErrorMessage } from "../utils/apiError";
import { buildBookEntry, normalize } from "../utils/bookSearch";

export async function booksLoader() {
  const snapshot = requireAuthSnapshot();
  await ensureBooksLoaded();
  const latestSnapshot = requireAuthSnapshot();
  return {
    books: latestSnapshot.books,
    search: snapshot.searchByPage.books
  };
}

export async function booksAction({ request }) {
  requireAuthSnapshot();
  const formData = await request.formData();
  const intent = String(formData.get("intent") || "");

  if (intent === "set-search") {
    setPageSearch("books", String(formData.get("value") || ""));
    return null;
  }

  if (intent === "add-to-cart") {
    const bookId = String(formData.get("bookId") || "");
    if (bookId) {
      try {
        await addToCart(bookId);
      } catch (error) {
        await ensureBooksLoaded(true);
        return {
          status: "error",
          message: getApiErrorMessage(error, "加入购物车失败，请检查库存。")
        };
      }
    }
    throw redirect(String(formData.get("redirectTo") || "/cart"));
  }

  return null;
}

const ALPHABET = [..."ABCDEFGHIJKLMNOPQRSTUVWXYZ", "#"];

// 书城主页：关键词、分类和拼音首字母三种筛选可以叠加。
function BooksPage({
  books,
  search,
  actionError
}) {
  const [category, setCategory] = useState("");

  // 分类集合完全由当前书目生成：管理员新增一个分类后，这里会自动多一个标签。
  const categories = useMemo(() => {
    const seen = new Set(books.map((book) => book.category).filter(Boolean));
    return [...seen].sort((left, right) => left.localeCompare(right, "zh-Hans-CN"));
  }, [books]);

  // 预先算好拼音全文、首字母和排序键，避免每次输入都重复转换。
  const entries = useMemo(
    () => books.map((book) => ({ book, ...buildBookEntry(book) })),
    [books]
  );

  const keyword = normalize(search);
  const filteredByText = useMemo(
    () => entries.filter(({ book, text }) => {
      if (category && book.category !== category) {
        return false;
      }
      return !keyword || text.includes(keyword);
    }),
    [entries, category, keyword]
  );

  // 右侧字母表只统计当前分类与搜索条件下有书的字母，空字母置灰。
  const letterCounts = useMemo(
    () => filteredByText.reduce((counts, entry) => {
      counts[entry.initial] = (counts[entry.initial] || 0) + 1;
      return counts;
    }, {}),
    [filteredByText]
  );

  const [letter, setLetter] = useState("");

  // 切换分类后原来选中的字母可能已经没有书，自动回到全部。
  useEffect(() => {
    if (letter && !letterCounts[letter]) {
      setLetter("");
    }
  }, [letter, letterCounts]);

  const filteredBooks = filteredByText
    .filter((entry) => !letter || entry.initial === letter)
    .sort((left, right) => left.sortKey.localeCompare(right.sortKey))
    .map((entry) => entry.book);

  // 共享壳层（DashboardLayout）已经上移到受保护父路由，
  // 当前页面只保留内容主体。
  return (
    <section className="page card" aria-label="书籍列表页面">
      <header className="page__header">
        <div>
          {/* 使用 Ant Design Typography 统一标题层级语义。 */}
          <Typography.Title level={3} className="page__title">书籍列表</Typography.Title>
        </div>
        {/* 使用 Ant Design Tag 展示数量摘要，替代手写状态徽标。 */}
        <Tag color="blue" aria-label="提示">共 {filteredBooks.length} 本</Tag>
      </header>

      {actionError ? (
        <div className="page__toolbar">
          <Alert type="error" showIcon message={actionError} />
        </div>
      ) : null}

      <div className="page__toolbar book-filter">
        <span className="book-filter__label">分类</span>
        <Space size={[8, 8]} wrap>
          <Tag.CheckableTag checked={!category} onChange={() => setCategory("")}>
            全部
          </Tag.CheckableTag>
          {categories.map((item) => (
            <Tag.CheckableTag
              key={item}
              checked={category === item}
              onChange={() => setCategory(category === item ? "" : item)}
            >
              {item}
            </Tag.CheckableTag>
          ))}
        </Space>
      </div>

      <div className="book-layout">
        {/* 使用 Ant Design Row/Col 统一响应式栅格，保持原卡片网格布局。 */}
        <Row gutter={[16, 16]} aria-label="书籍卡片列表" className="book-antd-grid">
          {filteredBooks.map((book) => (
            <Col key={book.id} xs={24} sm={12} lg={8} xl={6} className="book-antd-col">
              <BookCard book={book} />
            </Col>
          ))}
        </Row>
        <nav className="book-alphabet" aria-label="按拼音首字母筛选">
          {ALPHABET.map((item) => {
            const count = letterCounts[item] || 0;
            const active = letter === item;
            return (
              <button
                key={item}
                type="button"
                className={`book-alphabet__letter${active ? " book-alphabet__letter--active" : ""}`}
                disabled={count === 0}
                aria-pressed={active}
                aria-label={active ? `取消 ${item} 筛选` : `筛选以 ${item} 开头的书`}
                onClick={() => setLetter(active ? "" : item)}
              >
                {item}
              </button>
            );
          })}
        </nav>
      </div>
    </section>
  );
}

export function BooksRoute() {
  const data = useLoaderData();
  const actionData = useActionData();
  const actionError = actionData?.status === "error" ? actionData.message : null;

  return (
    <BooksPage
      books={data.books}
      search={data.search}
      actionError={actionError}
    />
  );
}

export default BooksPage;
