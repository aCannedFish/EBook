import { Link, redirect, useLoaderData, useSubmit } from "react-router-dom";
import DashboardLayout from "../components/DashboardLayout";
import {
  checkoutSelected,
  removeCartItem,
  setPageSearch,
  toggleCartItem,
  toggleSelectAllCart,
  updateCartQty
} from "../data/appStore";
import { readIntent, requireAuthSnapshot } from "../router/routeUtils";

export async function cartLoader() {
  const snapshot = requireAuthSnapshot();
  return {
    books: snapshot.books,
    cartItems: snapshot.cartItems,
    username: snapshot.user.username,
    search: snapshot.searchByPage.cart
  };
}

export async function cartAction({ request }) {
  requireAuthSnapshot();
  const formData = await request.formData();
  const intent = readIntent(formData);

  if (intent === "set-search") {
    setPageSearch("cart", String(formData.get("value") || ""));
    return null;
  }

  if (intent === "toggle-select-all") {
    toggleSelectAllCart(formData.get("checked") === "true");
    return null;
  }

  if (intent === "toggle-item") {
    const bookId = String(formData.get("bookId") || "");
    const checked = formData.get("checked") === "true";
    if (bookId) {
      toggleCartItem(bookId, checked);
    }
    return null;
  }

  if (intent === "update-qty") {
    const bookId = String(formData.get("bookId") || "");
    const qty = Number(formData.get("qty"));
    if (bookId && Number.isInteger(qty) && qty >= 1 && qty <= 4) {
      updateCartQty(bookId, qty);
    }
    return null;
  }

  if (intent === "remove-item") {
    const bookId = String(formData.get("bookId") || "");
    if (bookId) {
      removeCartItem(bookId);
    }
    return null;
  }

  if (intent === "checkout") {
    checkoutSelected();
    throw redirect("/orders");
  }

  return null;
}

// 购物车页：把购物车状态和图书信息合并后，再提供勾选、改数量和结算操作。
function CartPage({
  books,
  cartItems,
  username,
  search,
  onSearchChange,
  onToggleSelectAll,
  onToggleItem,
  onUpdateQty,
  onRemoveItem,
  onCheckout,
  onLogout
}) {
  // 将搜索词标准化，方便对书名做不区分大小写的过滤。
  const keyword = search.trim().toLowerCase();
  // rows 是“视图层数据”：把购物车条目与书籍元信息拼成适合渲染的结构。
  const rows = cartItems
    .map((item) => {
      // 先根据 bookId 找到完整书籍对象，如果找不到就跳过该条目。
      const book = books.find((entry) => entry.id === item.bookId);
      if (!book) {
        return null;
      }

      // subtotal 是当前行金额 = 单价 × 数量。
      return {
        ...item,
        book,
        subtotal: book.price * item.qty
      };
    })
    // filter(Boolean) 去掉 map 中返回的 null。
    .filter(Boolean)
    // 如果有关键词，就只保留书名包含关键词的商品行。
    .filter((row) => !keyword || row.book.title.toLowerCase().includes(keyword));

  // selectedRows 表示当前被勾选、准备结算的商品行。
  const selectedRows = rows.filter((row) => row.selected);
  // 是否“全选”：只有当前有行且每一行都被选中时才算全选。
  const allSelected = rows.length > 0 && selectedRows.length === rows.length;
  // 结算金额只统计已勾选项，确保汇总值和结算动作一致。
  const subtotal = selectedRows.reduce((sum, row) => sum + row.subtotal, 0);

  return (
    <DashboardLayout
      username={username}
      onLogout={onLogout}
      searchPlaceholder="搜索购物车中的书籍"
      searchValue={search}
      onSearchChange={onSearchChange}
    >
      <section className="page card" aria-label="购物车页面">
        <header className="page__header">
          <div>
            <h1 className="page__title">我的购物车</h1>
          </div>
          <div className="pill">共 {rows.length} 件</div>
        </header>

        <section className="cart" aria-label="购物车内容区">
          <section className="panel" aria-label="商品列表">
            <header className="panel__header">
              <h2 className="panel__title">商品</h2>
              <label className="auth__checks" htmlFor="selectAll">
                <input
                  id="selectAll"
                  type="checkbox"
                  checked={allSelected}
                  onChange={(event) => onToggleSelectAll(event.target.checked)}
                />
                全选
              </label>
            </header>
            <div className="panel__body">
              <table className="table" aria-label="购物车表格">
                <thead>
                  <tr>
                    <th scope="col">选择</th>
                    <th scope="col">书名</th>
                    <th scope="col">作者</th>
                    <th scope="col">单价</th>
                    <th scope="col">数量</th>
                    <th scope="col" className="u-right">小计</th>
                    <th scope="col" className="u-right">操作</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => (
                    <tr className="table__row" key={row.bookId}>
                      <td>
                        <input
                          type="checkbox"
                          checked={row.selected}
                          onChange={(event) => onToggleItem(row.bookId, event.target.checked)}
                          aria-label={`选择商品 ${row.book.title}`}
                        />
                      </td>
                      <td>
                        {/* 从购物车进入详情时，除路径参数外额外传递当前行的完整书籍对象。
                            这样详情页能优先使用 state.book，减少一次查找并保持页面间数据关联。 */}
                        <Link className="link" to={`/books/${row.bookId}`} state={{ book: row.book }}>{row.book.title}</Link>
                      </td>
                      <td>{row.book.author}</td>
                      <td>￥{row.book.price.toFixed(2)}</td>
                      <td>
                        <div className="qty" aria-label="数量选择">
                          <label className="u-sr-only" htmlFor={`qty-${row.bookId}`}>数量</label>
                          <select
                            id={`qty-${row.bookId}`}
                            value={row.qty}
                            onChange={(event) => onUpdateQty(row.bookId, Number(event.target.value))}
                          >
                            <option value={1}>1</option>
                            <option value={2}>2</option>
                            <option value={3}>3</option>
                            <option value={4}>4</option>
                          </select>
                        </div>
                      </td>
                      <td className="u-right"><strong>￥{row.subtotal.toFixed(2)}</strong></td>
                      <td className="u-right">
                        <button className="btn btn-danger cart-remove-btn" type="button" onClick={() => onRemoveItem(row.bookId)}>移除</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <aside className="panel" aria-label="结算信息">
            <header className="panel__header">
              <h2 className="panel__title">结算</h2>
              <span className="tag tag--pending">待结算</span>
            </header>
            <div className="panel__body">
              <div className="summary" aria-label="价格汇总">
                <div className="summary__row">
                  <span>商品金额</span>
                  <strong>￥{subtotal.toFixed(2)}</strong>
                </div>
                <div className="summary__row">
                  <span>优惠</span>
                  <strong>￥0.00</strong>
                </div>
                <div className="summary__row summary__total">
                  <span>合计</span>
                  <strong>￥{subtotal.toFixed(2)}</strong>
                </div>
              </div>

              <div className="summary__actions">
                <Link className="btn btn-secondary" to="/books">继续选购</Link>
                <button className="btn btn-primary" type="button" onClick={onCheckout}>结算</button>
              </div>
            </div>
          </aside>
        </section>
      </section>
    </DashboardLayout>
  );
}

export function CartRoute() {
  const data = useLoaderData();
  const submit = useSubmit();

  return (
    <CartPage
      books={data.books}
      cartItems={data.cartItems}
      username={data.username}
      search={data.search}
      onSearchChange={(value) => submit({ intent: "set-search", value }, { method: "post", action: "/cart", navigate: false })}
      onToggleSelectAll={(checked) =>
        submit({ intent: "toggle-select-all", checked: String(checked) }, { method: "post", action: "/cart", navigate: false })
      }
      onToggleItem={(bookId, checked) =>
        submit({ intent: "toggle-item", bookId, checked: String(checked) }, { method: "post", action: "/cart", navigate: false })
      }
      onUpdateQty={(bookId, qty) =>
        submit({ intent: "update-qty", bookId, qty: String(qty) }, { method: "post", action: "/cart", navigate: false })
      }
      onRemoveItem={(bookId) => submit({ intent: "remove-item", bookId }, { method: "post", action: "/cart", navigate: false })}
      onCheckout={() => submit({ intent: "checkout" }, { method: "post", action: "/cart" })}
      onLogout={() => submit(null, { method: "post", action: "/logout" })}
    />
  );
}

export default CartPage;
