import { Link, useParams } from "react-router-dom";
import DashboardLayout from "../components/DashboardLayout";

function BookDetailPage({
  books,
  username,
  search,
  onSearchChange,
  onAddToCart,
  onLogout
}) {
  const handleImageError = (event) => {
    const image = event.currentTarget;
    if (image.dataset.fallbackApplied === "true") {
      return;
    }

    image.dataset.fallbackApplied = "true";
    image.src = "/logo.svg";
  };

  const { bookId } = useParams();
  const book = books.find((item) => item.id === bookId);

  if (!book) {
    return (
      <DashboardLayout
        username={username}
        onLogout={onLogout}
        searchPlaceholder="搜索其他书籍"
        searchValue={search}
        onSearchChange={onSearchChange}
      >
        <section className="page card" aria-label="书籍详情内容">
          <header className="page__header">
            <div>
              <h1 className="page__title">未找到对应书籍</h1>
              <p className="page__desc">可能是链接无效，或该书籍尚未配置。</p>
            </div>
          </header>
          <section className="detail">
            <section className="detail__content">
              <div className="detail__cta">
                <Link className="btn btn-secondary" to="/books">返回书城</Link>
              </div>
            </section>
          </section>
        </section>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout
      username={username}
      onLogout={onLogout}
      searchPlaceholder="搜索其他书籍"
      searchValue={search}
      onSearchChange={onSearchChange}
    >
      <article className="page card" aria-label="书籍详情内容">
        <header className="page__header">
          <div>
            <h1 className="page__title">{book.title}</h1>
            <p className="page__desc">分类：{book.category} · 作者：{book.author}</p>
          </div>
          <div className={`pill ${book.stockType === "warn" ? "pill--warn" : "pill--ok"}`} aria-label="库存状态">
            {book.stockType === "warn" ? "库存紧张" : "库存充足"}
          </div>
        </header>

        <section className="detail" aria-label="详情布局">
          <figure className="detail__media" aria-label="书籍封面">
            <img src={book.cover} alt={`${book.title} 封面`} onError={handleImageError} />
          </figure>

          <section className="detail__content" aria-label="书籍信息">
            <h1 className="u-hidden">{book.title}</h1>
            <p className="detail__sub">
              价格：<span className="price">￥{book.price.toFixed(2)}</span>
            </p>

            <section className="kv" aria-label="关键信息">
              <div className="kv__item">
                <div className="kv__k">分类</div>
                <div className="kv__v">{book.category}</div>
              </div>
              <div className="kv__item">
                <div className="kv__k">状态</div>
                <div className="kv__v">在售 · 可加入购物车</div>
              </div>
              <div className="kv__item">
                <div className="kv__k">ISBN</div>
                <div className="kv__v">{book.isbn}</div>
              </div>
              <div className="kv__item">
                <div className="kv__k">发货方式</div>
                <div className="kv__v">{book.format}</div>
              </div>
            </section>

            <section className="detail__desc" aria-label="作品简介">
              <h2>作品简介</h2>
              <p>{book.description}</p>
            </section>

            <section className="detail__cta" aria-label="操作入口">
              <Link className="btn btn-primary" to="/cart" onClick={() => onAddToCart(book.id)}>加入购物车</Link>
              <Link className="btn btn-secondary" to="/orders">立即购买</Link>
              <Link className="btn btn-secondary" to="/books">继续逛书城</Link>
            </section>
          </section>
        </section>
      </article>
    </DashboardLayout>
  );
}

export default BookDetailPage;
