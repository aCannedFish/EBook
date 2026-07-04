import { Alert, Button, Card, Descriptions, Space, Tag, Typography } from "antd";
import { Form, redirect, useActionData, useLoaderData, useLocation, useNavigate, useParams } from "react-router-dom";
import { addToCart, ensureBooksLoaded, fetchAndStoreBookById, getBookById, setPageSearch } from "../data/appStore";
import { requireAuthSnapshot } from "../routes/authRouteHandlers";
import { getApiErrorMessage } from "../utils/apiError";
import { isOutOfStock } from "../utils/stock";

export async function bookDetailLoader({ params }) {
  requireAuthSnapshot();
  await ensureBooksLoaded();
  const snapshot = requireAuthSnapshot();
  let detailBook = getBookById(params.bookId);
  try {
    detailBook = await fetchAndStoreBookById(params.bookId);
  } catch (error) {
    if (error?.status !== 404) {
      throw error;
    }
  }
  return {
    detailBook,
    search: snapshot.searchByPage.detail
  };
}

export async function bookDetailAction({ request, params }) {
  requireAuthSnapshot();
  const formData = await request.formData();
  const intent = String(formData.get("intent") || "");

  if (intent === "set-search") {
    setPageSearch("detail", String(formData.get("value") || ""));
    return null;
  }

  if (intent === "add-to-cart") {
    const bookId = String(formData.get("bookId") || params.bookId || "");
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

// 书籍详情页：通过 URL 参数定位单本书，并展示完整的商品信息与操作入口。
function BookDetailPage({
  detailBook,
  actionError
}) {
  const navigate = useNavigate();
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
    return (
      <section className="page card" aria-label="书籍详情内容">
        <header className="page__header">
          <div>
            <Typography.Title level={3} className="page__title">未找到对应书籍</Typography.Title>
            <Typography.Paragraph className="page__desc">可能是链接无效，或该书籍尚未配置。</Typography.Paragraph>
          </div>
        </header>
        <section className="detail">
          <section className="detail__content">
            <div className="detail__cta">
              <Button onClick={() => navigate("/books")}>返回书城</Button>
            </div>
          </section>
        </section>
      </section>
    );
  }

  // 正常详情分支：展示封面、元信息、简介和按钮组。
  return (
    <article className="page card" aria-label="书籍详情内容">
      <header className="page__header">
        <div>
          {/* 使用 Ant Design Typography 输出详情页标题和副标题。 */}
          <Typography.Title level={3} className="page__title">{book.title}</Typography.Title>
          <Typography.Paragraph className="page__desc">分类：{book.category} · 作者：{book.author}</Typography.Paragraph>
        </div>
        <Tag color={book.stockType === "warn" ? "orange" : book.stockType === "out" ? "red" : "green"} aria-label="库存状态">
          {book.stockType === "out" ? "缺货" : book.stockType === "warn" ? "库存紧张" : "库存充足"}
        </Tag>
      </header>

      {actionError ? (
        <div className="page__toolbar">
          <Alert type="error" showIcon message={actionError} />
        </div>
      ) : null}

      <section className="detail" aria-label="详情布局">
        <figure className="detail__media" aria-label="书籍封面">
          <img src={book.cover} alt={`${book.title} 封面`} onError={handleImageError} />
        </figure>

        <section className="detail__content" aria-label="书籍信息">
          <Typography.Paragraph className="detail__sub">
            价格：<span className="price">￥{book.price.toFixed(2)}</span>
          </Typography.Paragraph>

          {/* 使用 Ant Design Descriptions 展示结构化书籍元数据。 */}
          <Card size="small">
            <Descriptions column={1} size="small">
              <Descriptions.Item label="分类">{book.category}</Descriptions.Item>
              <Descriptions.Item label="出版社">{book.publisher}</Descriptions.Item>
              <Descriptions.Item label="库存">
                {book.stockText} · 库存 {book.stockQty ?? 0} 本
              </Descriptions.Item>
              <Descriptions.Item label="ISBN">{book.isbn}</Descriptions.Item>
              <Descriptions.Item label="发货方式">{book.format}</Descriptions.Item>
            </Descriptions>
          </Card>

          <section className="detail__desc" aria-label="作品简介">
            <Typography.Title level={4}>作品简介</Typography.Title>
            <Typography.Paragraph>{book.description}</Typography.Paragraph>
          </section>

          <section className="detail__cta" aria-label="操作入口">
            {/* 与列表页一致：详情页加入购物车也走当前路由 action（bookDetailAction），
                确保所有写操作都在数据路由层集中处理。 */}
            <Form method="post">
              <input type="hidden" name="intent" value="add-to-cart" />
              <input type="hidden" name="bookId" value={book.id} />
              <input type="hidden" name="redirectTo" value="/cart" />
              <Button type="primary" htmlType="submit" disabled={isOutOfStock(book)}>
                {isOutOfStock(book) ? "已缺货" : "加入购物车"}
              </Button>
            </Form>
            <Space wrap>
              <Button onClick={() => navigate("/orders")}>立即购买</Button>
              <Button onClick={() => navigate("/books")}>继续逛书城</Button>
            </Space>
          </section>
        </section>
      </section>
    </article>
  );
}

export function BookDetailRoute() {
  const data = useLoaderData();
  const actionData = useActionData();
  const actionError = actionData?.status === "error" ? actionData.message : null;

  return (
    <BookDetailPage
      detailBook={data.detailBook}
      actionError={actionError}
    />
  );
}

export default BookDetailPage;
