import { Link } from "react-router-dom";
import DashboardLayout from "../components/DashboardLayout";

const statusMeta = {
  pending: { label: "待付款", className: "tag tag--pending" },
  paid: { label: "已付款", className: "tag tag--paid" },
  cancelled: { label: "已取消", className: "tag tag--cancelled" }
};

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
  const keyword = search.trim().toLowerCase();
  const rows = orders
    .map((order) => {
      const book = books.find((item) => item.id === order.bookId);
      if (!book) {
        return null;
      }

      return {
        ...order,
        book,
        total: order.qty * order.unitPrice
      };
    })
    .filter(Boolean)
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
                  <td><Link className="link" to={`/books/${row.bookId}`}>{row.book.title}</Link></td>
                  <td>{row.qty}</td>
                  <td>￥{row.unitPrice.toFixed(2)}</td>
                  <td className="u-right"><strong>￥{row.total.toFixed(2)}</strong></td>
                  <td className="u-right">
                    {row.status === "pending" && (
                      <>
                        <button className="btn btn-danger" type="button" onClick={() => onUpdateOrderStatus(row.id, "cancelled")}>取消</button>
                        <button className="btn btn-primary" type="button" onClick={() => onUpdateOrderStatus(row.id, "paid")}>付款</button>
                      </>
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

