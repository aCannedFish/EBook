import { Col, Row, Tag, Typography } from "antd";
import BookCard from "../components/BookCard";
import { redirect, useLoaderData } from "react-router-dom";
import { addToCart, ensureBooksLoaded, setPageSearch } from "../data/appStore";
import { requireAuthSnapshot } from "../routes/authRouteHandlers";

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
      await addToCart(bookId);
    }
    throw redirect(String(formData.get("redirectTo") || "/cart"));
  }

  return null;
}

// 书城主页：先做本地关键词过滤，再把结果交给卡片网格展示。
function BooksPage({
  books,
  search
}) {
  // 将搜索词统一转成小写并去掉空格，便于做大小写不敏感的模糊匹配。
  const keyword = search.trim().toLowerCase();
  // filter 会遍历全部图书，逐本判断是否命中关键词。
  const filteredBooks = books.filter((book) => {
    // 空搜索词时直接返回全部数据。
    if (!keyword) {
      return true;
    }

    // 把标题、作者、分类拼成一个字符串，再统一转小写后做 includes 搜索。
    return [book.title, book.author, book.category]
      .join(" ")
      .toLowerCase()
      .includes(keyword);
  });

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

      {/* 使用 Ant Design Row/Col 统一响应式栅格，保持原卡片网格布局。 */}
      <Row gutter={[16, 16]} aria-label="书籍卡片列表" className="book-antd-grid">
        {filteredBooks.map((book) => (
          <Col key={book.id} xs={24} sm={12} lg={8} xl={6} className="book-antd-col">
            <BookCard book={book} />
          </Col>
        ))}
      </Row>
    </section>
  );
}

export function BooksRoute() {
  const data = useLoaderData();

  return (
    <BooksPage
      books={data.books}
      search={data.search}
    />
  );
}

export default BooksPage;
