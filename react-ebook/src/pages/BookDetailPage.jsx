import { Form, Link, redirect, useLoaderData, useLocation, useParams, useSubmit } from "react-router-dom";
import DashboardLayout from "../components/DashboardLayout";
import { addToCart, getBookById, setPageSearch } from "../data/appStore";
import { readIntent, readRedirectPath, requireAuthSnapshot } from "../router/routeUtils";

export async function bookDetailLoader({ params }) {
  const snapshot = requireAuthSnapshot();
  return {
    detailBook: getBookById(params.bookId),
    username: snapshot.user.username,
    search: snapshot.searchByPage.detail
  };
}

export async function bookDetailAction({ request, params }) {
  requireAuthSnapshot();
  const formData = await request.formData();
  const intent = readIntent(formData);

  if (intent === "set-search") {
    setPageSearch("detail", String(formData.get("value") || ""));
    return null;
  }

  if (intent === "add-to-cart") {
    const bookId = String(formData.get("bookId") || params.bookId || "");
    if (bookId) {
      addToCart(bookId);
    }
    throw redirect(readRedirectPath(formData, "/cart"));
  }

  return null;
}

// 书籍详情页：通过 URL 参数定位单本书，并展示完整的商品信息与操作入口。
function BookDetailPage({
  detailBook,
  username,
  search,
  onSearchChange,
  onLogout
}) {
  // 封面错误处理：图片加载失败时回退到站点 Logo，避免空白占位破坏布局。
  const handleImageError = (event) => {
    // currentTarget 是当前这个 img 元素本身。
    const image = event.currentTarget;
    // 通过 data 标记防止兜底图片再次失败时进入死循环。
    if (image.dataset.fallbackApplied === "true") {
      return;
    }

    // 先设置标记，再替换图片地址。
    image.dataset.fallbackApplied = "true";
    image.src = "/assets/logo.svg";
  };

  // useParams 读取路由中的 :bookId，对应当前详情页要展示哪一本书。
  const { bookId } = useParams();
  // useLocation 读取上一页面通过 Link state 传入的数据，保持页面间数据关联。
  const location = useLocation();
  // bookFromState：从导航 state 中拿到的“上一页面已选书籍对象”。
  // 常见来源：书城列表、购物车、订单页点击书名跳转详情。
  const bookFromState = location.state?.book;
  // book 解析策略（按优先级）：
  // 1) state.book 且 id 与 URL 参数一致：优先使用，确保“点哪本看哪本”；
  // 2) detailBook（来自路由包装层基于 bookId 的预查找结果，覆盖地址栏直达场景）。
  const book = (bookFromState && bookFromState.id === bookId ? bookFromState : null)
    || detailBook;

  // 如果参数无效或数据缺失，就进入“未找到”分支，给用户明确反馈。
  if (!book) {
    // 仍然使用同一个 Layout，保持页面壳一致。
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

  // 正常详情分支：展示封面、元信息、简介和按钮组。
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
              {/* 与列表页一致：详情页加入购物车也走当前路由 action（bookDetailAction），
                  确保所有写操作都在数据路由层集中处理。 */}
              <Form method="post">
                <input type="hidden" name="intent" value="add-to-cart" />
                <input type="hidden" name="bookId" value={book.id} />
                <input type="hidden" name="redirectTo" value="/cart" />
                <button className="btn btn-primary" type="submit">加入购物车</button>
              </Form>
              <Link className="btn btn-secondary" to="/orders">立即购买</Link>
              <Link className="btn btn-secondary" to="/books">继续逛书城</Link>
            </section>
          </section>
        </section>
      </article>
    </DashboardLayout>
  );
}

export function BookDetailRoute() {
  const data = useLoaderData();
  const submit = useSubmit();

  return (
    <BookDetailPage
      detailBook={data.detailBook}
      username={data.username}
      search={data.search}
      onSearchChange={(value) => submit({ intent: "set-search", value }, { method: "post", navigate: false })}
      onLogout={() => submit(null, { method: "post", action: "/logout" })}
    />
  );
}

export default BookDetailPage;
