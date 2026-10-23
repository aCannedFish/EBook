import { Input, Space, Tag, Typography } from "antd";
import { Link, redirect, useLoaderData, useSubmit } from "react-router-dom";
import ResourceTable from "../components/ResourceTable";
import RowActions from "../components/RowActions";
import StatusTag from "../components/StatusTag";
import {
  addToCart,
  ensureBooksLoaded,
  ensureOrdersLoaded,
  setOrderFilters,
  setPageSearch,
  updateOrderStatus
} from "../data/appStore";
import { requireAdminSnapshot, requireAuthSnapshot } from "../routes/authRouteHandlers";
import { formatDateTime } from "../utils/format";

export async function ordersLoader() {
  requireAuthSnapshot();
  await ensureBooksLoaded();
  await ensureOrdersLoaded(true, { adminView: false });
  const snapshot = requireAuthSnapshot();
  return {
    books: snapshot.books,
    orders: snapshot.orders,
    search: snapshot.searchByPage.orders,
    filters: snapshot.orderFilters,
    adminView: false
  };
}

export async function adminOrdersLoader() {
  requireAdminSnapshot();
  await ensureBooksLoaded();
  await ensureOrdersLoaded(true, { adminView: true });
  const snapshot = requireAdminSnapshot();
  return {
    books: snapshot.books,
    orders: snapshot.orders,
    search: snapshot.searchByPage.adminOrders,
    filters: snapshot.orderFilters,
    adminView: true
  };
}

async function handleOrdersAction(request, pageKey) {
  requireAuthSnapshot();
  const formData = await request.formData();
  const intent = String(formData.get("intent") || "");

  if (intent === "set-search") {
    setPageSearch(pageKey, String(formData.get("value") || ""));
    return null;
  }

  if (intent === "set-filters") {
    setOrderFilters({
      from: String(formData.get("from") || ""),
      to: String(formData.get("to") || ""),
      bookTitle: String(formData.get("bookTitle") || "")
    });
    await ensureOrdersLoaded(true, { adminView: pageKey === "adminOrders" });
    return null;
  }

  if (intent === "update-status") {
    const orderId = String(formData.get("orderId") || "");
    const userId = Number(formData.get("userId") || formData.get("ownerId") || 0);
    const status = String(formData.get("status") || "");
    const snapshot = requireAuthSnapshot();
    const targetUserId = userId || snapshot.user.id;
    if (orderId && ["pending", "paid", "cancelled"].includes(status)) {
      await updateOrderStatus(orderId, status, targetUserId);
    }
    return null;
  }

  if (intent === "buy-again") {
    const bookId = String(formData.get("bookId") || "");
    if (bookId) {
      await addToCart(bookId);
    }
    throw redirect(String(formData.get("redirectTo") || "/books"));
  }

  return null;
}

export async function ordersAction({ request }) {
  return handleOrdersAction(request, "orders");
}

export async function adminOrdersAction({ request }) {
  return handleOrdersAction(request, "adminOrders");
}

// 订单状态映射表：把内部状态值和展示文案、样式类集中管理，避免 JSX 中到处写条件分支。
const statusMeta = {
  pending: { label: "待付款", color: "orange" },
  paid: { label: "已付款", color: "green" },
  cancelled: { label: "已取消", color: "red" }
};

// 订单页：按结算批次展示订单，同一单内多本书合并为一行并汇总总价。
function OrdersPage({
  books,
  orders,
  search,
  filters,
  adminView,
  onUpdateOrderStatus,
  onBuyAgain,
  onFilterChange
}) {
  const keyword = search.trim().toLowerCase();
  const rows = orders
    .map((order) => {
      const items = (order.items || [])
        .map((item) => {
          const book = books.find((entry) => entry.id === item.bookId);
          if (!book) {
            return null;
          }
          return {
            ...item,
            book,
            lineTotal: item.qty * item.unitPrice
          };
        })
        .filter(Boolean);

      if (items.length === 0) {
        return null;
      }

      return {
        ...order,
        items,
        total: order.totalPrice || items.reduce((sum, item) => sum + item.lineTotal, 0)
      };
    })
    .filter(Boolean)
    .filter((row) => {
      if (!keyword) {
        return true;
      }

      const bookTitles = row.items.map((item) => item.book.title).join(" ");
      return `${row.id} ${bookTitles}`.toLowerCase().includes(keyword);
    });

  const columns = [
    {
      title: "订单号",
      dataIndex: "id",
      render: (value) => <span className="order-id">{value}</span>
    },
    ...(adminView
      ? [{
          title: "用户",
          dataIndex: "username",
          render: (value, row) => value || `用户#${row.userId}`
        }]
      : []),
    {
      title: "下单时间",
      dataIndex: "createdAt",
      render: (value) => formatDateTime(value)
    },
    {
      title: "状态",
      dataIndex: "status",
      render: (status) => <StatusTag status={status} metaMap={statusMeta} />
    },
    {
      title: "商品明细",
      dataIndex: "items",
      render: (items) => (
        <div className="order-items">
          {items.map((item) => (
            <div key={`${item.bookId}-${item.qty}`} className="order-items__line">
              <Link className="link" to={`/books/${item.bookId}`} state={{ book: item.book }}>
                {item.book.title}
              </Link>
              <span className="order-items__meta">
                ×{item.qty} · ￥{Number(item.unitPrice).toFixed(2)}
              </span>
            </div>
          ))}
        </div>
      )
    },
    {
      title: "订单总价",
      dataIndex: "total",
      align: "right",
      render: (value) => <strong>￥{Number(value).toFixed(2)}</strong>
    },
    {
      title: "操作",
      dataIndex: "action",
      align: "right",
      render: (_, row) => {
        const actions = [
          {
            key: `cancel-${row.id}`,
            label: "取消",
            danger: true,
            hidden: row.status !== "pending",
            onClick: () => onUpdateOrderStatus(row.id, "cancelled", row.userId)
          },
          {
            key: `pay-${row.id}`,
            label: "付款",
            type: "primary",
            hidden: row.status !== "pending",
            onClick: () => onUpdateOrderStatus(row.id, "paid", row.userId)
          },
          {
            key: `view-${row.id}`,
            label: "查看",
            hidden: row.status !== "paid"
          }
        ];

        if (row.status === "cancelled") {
          row.items.forEach((item) => {
            actions.push({
              key: `again-${row.id}-${item.bookId}`,
              label: `再次购买：${item.book.title}`,
              onClick: () => onBuyAgain(item.bookId)
            });
          });
        }

        return <RowActions actions={actions} />;
      }
    }
  ];

  return (
    <section className="page card" aria-label="订单页面">
      <header className="page__header">
        <Typography.Title level={3} className="page__title">
          {adminView ? "全部订单" : "我的订单"}
        </Typography.Title>
        <Tag>共 {rows.length} 单</Tag>
      </header>

      <div className="page__toolbar">
        <Space wrap>
          <Input
            type="date"
            value={filters.from || ""}
            onChange={(event) => onFilterChange({ from: event.target.value })}
          />
          <Input
            type="date"
            value={filters.to || ""}
            onChange={(event) => onFilterChange({ to: event.target.value })}
          />
          <Input
            placeholder="按书名过滤"
            value={filters.bookTitle || ""}
            onChange={(event) => onFilterChange({ bookTitle: event.target.value })}
            style={{ width: 220 }}
          />
        </Space>
      </div>

      <section className="page__section orders" aria-label="订单列表">
        <ResourceTable rowKey="id" dataSource={rows} columns={columns} />
      </section>
    </section>
  );
}

export function OrdersRoute() {
  const data = useLoaderData();
  const submit = useSubmit();

  return (
    <OrdersPage
      {...data}
      onUpdateOrderStatus={(orderId, status, ownerId) =>
        submit({ intent: "update-status", orderId, status, ownerId }, { method: "post", action: "/orders", navigate: false })
      }
      onBuyAgain={(bookId) => submit({ intent: "buy-again", bookId, redirectTo: "/books" }, { method: "post", action: "/orders" })}
      onFilterChange={(partial) =>
        submit(
          {
            intent: "set-filters",
            from: partial.from ?? data.filters.from,
            to: partial.to ?? data.filters.to,
            bookTitle: partial.bookTitle ?? data.filters.bookTitle
          },
          { method: "post", navigate: false }
        )
      }
    />
  );
}

export function AdminOrdersRoute() {
  const data = useLoaderData();
  const submit = useSubmit();

  return (
    <OrdersPage
      {...data}
      onUpdateOrderStatus={(orderId, status, ownerId) =>
        submit({ intent: "update-status", orderId, status, ownerId }, { method: "post", action: "/admin/orders", navigate: false })
      }
      onBuyAgain={(bookId) => submit({ intent: "buy-again", bookId, redirectTo: "/books" }, { method: "post", action: "/admin/orders" })}
      onFilterChange={(partial) =>
        submit(
          {
            intent: "set-filters",
            from: partial.from ?? data.filters.from,
            to: partial.to ?? data.filters.to,
            bookTitle: partial.bookTitle ?? data.filters.bookTitle
          },
          { method: "post", navigate: false }
        )
      }
    />
  );
}

export default OrdersPage;
