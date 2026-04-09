import { Link } from "react-router-dom";

function BookCard({ book, onAddToCart }) {
  const handleImageError = (event) => {
    const image = event.currentTarget;
    if (image.dataset.fallbackApplied === "true") {
      return;
    }

    image.dataset.fallbackApplied = "true";
    image.src = "/logo.svg";
  };


  return (
    <article className="book" aria-label={`书籍卡片 ${book.title}`}>
      <figure className="book__cover" aria-label={`${book.title} 封面`}>
        <img src={book.cover} alt={`${book.title} 封面`} loading="lazy" onError={handleImageError} />
      </figure>
      <div className="book__body">
        <h2 className="book__title">{book.title}</h2>
        <p className="book__author">作者：{book.author}</p>
        <div className="book__meta">
          <span className="price">￥{book.price.toFixed(2)}</span>
          <span className={`pill ${book.stockType === "warn" ? "pill--warn" : "pill--ok"}`}>
            {book.stockText}
          </span>
        </div>
        <div className="book__actions">
          <Link className="btn btn-secondary" to={`/books/${book.id}`}>
            查看详情
          </Link>
          <Link
            className="btn btn-primary"
            to="/cart"
            onClick={() => onAddToCart(book.id)}
          >
            加入购物车
          </Link>
        </div>
      </div>
    </article>
  );
}

export default BookCard;
