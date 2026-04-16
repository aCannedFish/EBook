import { Form, Link } from "react-router-dom";

// 列表页复用卡片：把单本书的展示信息和操作按钮封装起来，便于在书城页循环渲染。
function BookCard({ book }) {
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
          {/* 详情入口：同时传递路径参数和 state.book。
              - 路径参数 book.id 用于地址可分享/可直达；
              - state.book 用于从列表跳详情时直接携带已选中的书籍对象，减少详情页二次查找。 */}
          <Link className="btn btn-secondary" to={`/books/${book.id}`} state={{ book }}>
            查看详情
          </Link>
          {/* 该 Form 提交到当前路由 action（/books -> booksAction）。
              hidden 字段即 action 协议参数：
              - intent: 动作类型；
              - bookId: 目标书籍；
              - redirectTo: 写入成功后跳转目的地。 */}
          <Form className="book__action-form" method="post">
            <input type="hidden" name="intent" value="add-to-cart" />
            <input type="hidden" name="bookId" value={book.id} />
            <input type="hidden" name="redirectTo" value="/cart" />
            <button className="btn btn-primary" type="submit">加入购物车</button>
          </Form>
        </div>
      </div>
    </article>
  );
}

export default BookCard;
