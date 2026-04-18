import { Link, redirect, useLoaderData, useSubmit } from "react-router-dom";
import { addToCart, setPageSearch, updateOrderStatus } from "../data/appStore";
import { readIntent, readRedirectPath, requireAuthSnapshot } from "../router/routeUtils";

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
  const intent = readIntent(formData);

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
    throw redirect(readRedirectPath(formData, "/books"));
  }

  return null;
}

// 订单状态映射表：把内部状态值和展示文案、样式类集中管理，避免 JSX 中到处写条件分支。
const statusMeta = {
  pending: { label: "待付款", className: "tag tag--pending" },
  paid: { label: "已付款", className: "tag tag--paid" },
  cancelled: { label: "已取消", className: "tag tag--cancelled" }
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

  return (
    <section className="page card" aria-label="订单页面">
      <header className="page__header">
        <div>
          <h1 className="page__title">我的订单</h1>
        </div>
        <div className="pill">共 {rows.length} 单</div>
      </header>

      <section className="orders" aria-label="订单列表">
        <table className="table" aria-label="订单表格">
          <thead>
            <tr>
              <th scope="col">订单号</th>
              <th scope="col">状态</th>
              <th scope="col">书名</th>
              <th scope="col">数量</th>
              <th scope="col">单价</th>
              <th scope="col" className="u-right">总价</th>
              <th scope="col" className="u-right">操作</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr className="table__row" key={row.id}>
                <td className="order-id">{row.id}</td>
                <td><span className={statusMeta[row.status].className}>{statusMeta[row.status].label}</span></td>
                <td>
                  {/* 从订单页跳详情时传递 row.book，避免详情页仅依赖 URL 再次检索。 */}
                  <Link className="link" to={`/books/${row.bookId}`} state={{ book: row.book }}>{row.book.title}</Link>
                </td>
                <td>{row.qty}</td>
                <td>￥{row.unitPrice.toFixed(2)}</td>
                <td className="u-right"><strong>￥{row.total.toFixed(2)}</strong></td>
                <td className="u-right">
                  {row.status === "pending" && (
                    <span className="order-actions">
                      <button className="btn btn-danger" type="button" onClick={() => onUpdateOrderStatus(row.id, "cancelled")}>取消</button>
                      <button className="btn btn-primary" type="button" onClick={() => onUpdateOrderStatus(row.id, "paid")}>付款</button>
                    </span>
                  )}
                  {row.status === "paid" && (
                    <button className="btn btn-secondary" type="button">查看</button>
                  )}
                  {row.status === "cancelled" && (
                    <button className="btn btn-secondary" type="button" onClick={() => onBuyAgain(row.bookId)}>再次购买</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
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
