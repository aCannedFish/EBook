import BookCard from "../components/BookCard";
import DashboardLayout from "../components/DashboardLayout";

// 书城主页：按关键词筛选书籍并以卡片网格展示。
function BooksPage({
  books,
  username,
  search,
  onSearchChange,
  onAddToCart,
  onLogout
}) {
  const keyword = search.trim().toLowerCase();
  // 支持书名、作者、分类的本地模糊筛选。
  const filteredBooks = books.filter((book) => {
    if (!keyword) {
      return true;
    }

    return [book.title, book.author, book.category]
      .join(" ")
      .toLowerCase()
      .includes(keyword);
  });

  return (
    <DashboardLayout
      username={username}
      onLogout={onLogout}
      searchPlaceholder="搜索书名 / 作者 / 分类"
      searchValue={search}
      onSearchChange={onSearchChange}
    >
      <section className="page card" aria-label="书籍列表页面">
        <header className="page__header">
          <div>
            <h1 className="page__title">书籍列表</h1>
            <p className="page__desc">展示封面、书名、作者与价格。</p>
          </div>
          <div className="pill pill--pay" aria-label="提示">共 {filteredBooks.length} 本</div>
        </header>

        <section className="grid grid--books" aria-label="书籍卡片列表">
          {filteredBooks.map((book) => (
            <BookCard
              key={book.id}
              book={book}
              onAddToCart={onAddToCart}
            />
          ))}
        </section>
      </section>
    </DashboardLayout>
  );
}

export default BooksPage;
