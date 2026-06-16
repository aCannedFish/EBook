import { ShoppingCartOutlined } from "@ant-design/icons";
import { Button, Card, Space, Tag, Typography } from "antd";
import { Form, useNavigate } from "react-router-dom";

// 列表页复用卡片：把单本书的展示信息和操作按钮封装起来，便于在书城页循环渲染。
function BookCard({ book }) {
  const navigate = useNavigate();
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
    // 使用 Ant Design Card 封装单本书籍展示，统一卡片信息密度与按钮布局。
    <Card
      className="book-antd-card"
      cover={<img src={book.cover} alt={`${book.title} 封面`} loading="lazy" onError={handleImageError} />}
    >
      <Space direction="vertical" size={10} className="book-antd-card__stack">
        <Typography.Title level={5} className="book-antd-card__title">
          {book.title}
        </Typography.Title>
        <Typography.Text type="secondary" className="book-antd-card__author">
          作者：{book.author}
        </Typography.Text>
        <Space className="book-antd-card__meta">
          <Typography.Text strong className="book-antd-card__price">
            ￥{book.price.toFixed(2)}
          </Typography.Text>
          <Tag color={book.stockType === "warn" ? "orange" : book.stockType === "out" ? "red" : "green"}>
            {book.stockText} · 库存 {book.stockQty ?? 0}
          </Tag>
        </Space>
        <Space direction="vertical" size={8} className="book-antd-card__actions">
          {/* 使用 Ant Design Button 提供详情跳转操作，保持原有 state.book 传递。 */}
          <Button block onClick={() => navigate(`/books/${book.id}`, { state: { book } })}>
            查看详情
          </Button>
          {/* 继续走 React Router Form 提交 action，Button 只负责 UI 呈现。 */}
          <Form className="book__action-form" method="post">
            <input type="hidden" name="intent" value="add-to-cart" />
            <input type="hidden" name="bookId" value={book.id} />
            <input type="hidden" name="redirectTo" value="/cart" />
            <Button block type="primary" icon={<ShoppingCartOutlined />} htmlType="submit">
              加入购物车
            </Button>
          </Form>
        </Space>
      </Space>
    </Card>
  );
}

export default BookCard;
