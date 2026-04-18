import BookCard from "../components/BookCard";
import { redirect, useLoaderData } from "react-router-dom";
import { addToCart, setPageSearch } from "../data/appStore";
import { readIntent, readRedirectPath, requireAuthSnapshot } from "../router/routeUtils";

export async function booksLoader() {
  const snapshot = requireAuthSnapshot();
  return {
    books: snapshot.books,
    username: snapshot.user.username,
    search: snapshot.searchByPage.books
  };
}

export async function booksAction({ request }) {
  requireAuthSnapshot();
  const formData = await request.formData();
  const intent = readIntent(formData);

  if (intent === "set-search") {
    setPageSearch("books", String(formData.get("value") || ""));
    return null;
  }

  if (intent === "add-to-cart") {
    const bookId = String(formData.get("bookId") || "");
    if (bookId) {
      addToCart(bookId);
    }
    throw redirect(readRedirectPath(formData, "/cart"));
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
          <h1 className="page__title">书籍列表</h1>
        </div>
        <div className="pill pill--pay" aria-label="提示">共 {filteredBooks.length} 本</div>
      </header>

      <section className="grid grid--books" aria-label="书籍卡片列表">
        {filteredBooks.map((book) => (
          <BookCard
            key={book.id}
            book={book}
          />
        ))}
      </section>
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
