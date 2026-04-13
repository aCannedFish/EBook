import { Link } from "react-router-dom";

// 列表页复用卡片：把单本书的展示信息和操作按钮封装起来，便于在书城页循环渲染。
function BookCard({ book, onAddToCart }) {
  // 图片错误处理：封面加载失败时只替换一次，避免 onError 因替换后再次失败而循环触发。
  const handleImageError = (event) => {
    // currentTarget 指向当前 <img>，而不是触发事件的子元素。
    const image = event.currentTarget;
    // dataset 用来记录是否已经切换过兜底图，防止重复执行。
    if (image.dataset.fallbackApplied === "true") {
      return;
    }

    // 先标记再切图，避免 logo 自身再触发错误时进入死循环。
    image.dataset.fallbackApplied = "true";
    image.src = "/assets/logo.svg";
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
