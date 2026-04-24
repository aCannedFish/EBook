import { Button, Space, Table, Tag, Typography } from "antd";
import { Link, redirect, useLoaderData, useSubmit } from "react-router-dom";
import { addToCart, setPageSearch, updateOrderStatus } from "../data/appStore";
import { requireAuthSnapshot } from "../routes/authRouteHandlers";

export async function ordersLoader() {
  const snapshot = requireAuthSnapshot();
  return {
    books: snapshot.books,
    orders: snapshot.orders,
    search: snapshot.searchByPage.orders
  };
}

export async function ordersAction({ request }) {
  requireAuthSnapshot();
  const formData = await request.formData();
  const intent = String(formData.get("intent") || "");

  if (intent === "set-search") {
    setPageSearch("orders", String(formData.get("value") || ""));
    return null;
  }

  if (intent === "update-status") {
    const orderId = String(formData.get("orderId") || "");
    const status = String(formData.get("status") || "");
    if (orderId && ["pending", "paid", "cancelled"].includes(status)) {
      updateOrderStatus(orderId, status);
    }
    return null;
  }

  if (intent === "buy-again") {
    const bookId = String(formData.get("bookId") || "");
    if (bookId) {
      addToCart(bookId);
    }
    throw redirect(String(formData.get("redirectTo") || "/books"));
  }

  return null;
}

// 订单状态映射表：把内部状态值和展示文案、样式类集中管理，避免 JSX 中到处写条件分支。
const statusMeta = {
  pending: { label: "待付款", color: "orange" },
  paid: { label: "已付款", color: "green" },
  cancelled: { label: "已取消", color: "red" }
};

// 订单页：基于订单列表和图书列表拼装展示数据，并提供状态操作入口。
function OrdersPage({
  books,
  orders,
  search,
  onUpdateOrderStatus,
  onBuyAgain
}) {
  // 统一处理搜索词，便于进行大小写不敏感匹配。
  const keyword = search.trim().toLowerCase();
  // rows 是用于渲染的增强版订单数据：补齐书籍对象并计算总价。
  const rows = orders
    .map((order) => {
      // 先把订单中的 bookId 映射回完整书籍信息。
      const book = books.find((item) => item.id === order.bookId);
      if (!book) {
        return null;
      }

      // total = 数量 × 单价，表示这笔订单的金额。
      return {
        ...order,
        book,
        total: order.qty * order.unitPrice
      };
    })
    // 去掉找不到书籍的异常订单行。
    .filter(Boolean)
    // 仅保留订单号或书名命中的行。
    .filter((row) => {
      if (!keyword) {
        return true;
      }

      return `${row.id} ${row.book.title}`.toLowerCase().includes(keyword);
    });

  // 使用 Ant Design Table 统一订单列表渲染、状态标签与行操作按钮。
  const columns = [
    {
      title: "订单号",
      dataIndex: "id",
      render: (value) => <span className="order-id">{value}</span>
    },
    {
      title: "状态",
      dataIndex: "status",
      render: (status) => <Tag color={statusMeta[status].color}>{statusMeta[status].label}</Tag>
    },
    {
      title: "书名",
      dataIndex: "book",
      render: (_, row) => (
        <Link className="link" to={`/books/${row.bookId}`} state={{ book: row.book }}>
          {row.book.title}
        </Link>
      )
    },
    {
      title: "数量",
      dataIndex: "qty"
    },
    {
      title: "单价",
      dataIndex: "unitPrice",
      render: (value) => `￥${Number(value).toFixed(2)}`
    },
    {
      title: "总价",
      dataIndex: "total",
      align: "right",
      render: (value) => <strong>￥{Number(value).toFixed(2)}</strong>
    },
    {
      title: "操作",
      dataIndex: "action",
      align: "right",
      render: (_, row) => (
        <Space>
          {row.status === "pending" && (
            <>
              <Button danger size="small" onClick={() => onUpdateOrderStatus(row.id, "cancelled")}>取消</Button>
              <Button type="primary" size="small" onClick={() => onUpdateOrderStatus(row.id, "paid")}>付款</Button>
            </>
          )}
          {row.status === "paid" && (
            <Button size="small">查看</Button>
          )}
          {row.status === "cancelled" && (
            <Button size="small" onClick={() => onBuyAgain(row.bookId)}>再次购买</Button>
          )}
        </Space>
      )
    }
  ];

  return (
    <section className="page card" aria-label="订单页面">
      <header className="page__header">
        <Typography.Title level={3} className="page__title">我的订单</Typography.Title>
        <Tag>共 {rows.length} 单</Tag>
      </header>

      <section className="orders" aria-label="订单列表">
        <Table rowKey="id" dataSource={rows} columns={columns} pagination={false} />
      </section>
    </section>
  );
}

export function OrdersRoute() {
  const data = useLoaderData();
  const submit = useSubmit();

  return (
    <OrdersPage
      books={data.books}
      orders={data.orders}
      search={data.search}
      onUpdateOrderStatus={(orderId, status) =>
        submit({ intent: "update-status", orderId, status }, { method: "post", action: "/orders", navigate: false })
      }
      onBuyAgain={(bookId) => submit({ intent: "buy-again", bookId, redirectTo: "/books" }, { method: "post", action: "/orders" })}
    />
  );
}

export default OrdersPage;
