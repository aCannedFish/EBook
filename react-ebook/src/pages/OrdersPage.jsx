import { Link } from "react-router-dom";
import DashboardLayout from "../components/DashboardLayout";

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
  username,
  search,
  onSearchChange,
  onUpdateOrderStatus,
  onBuyAgain,
  onLogout
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
    <DashboardLayout
      username={username}
      onLogout={onLogout}
      searchPlaceholder="搜索订单号或书名"
      searchValue={search}
      onSearchChange={onSearchChange}
    >
      <section className="page card" aria-label="订单页面">
        <header className="page__header">
          <div>
            <h1 className="page__title">我的订单</h1>
            <p className="page__desc">查看订单号、状态、商品与金额等信息。</p>
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
                      <Link className="btn btn-secondary" to="/books" onClick={() => onBuyAgain(row.bookId)}>再次购买</Link>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </section>
    </DashboardLayout>
  );
}

export default OrdersPage;
