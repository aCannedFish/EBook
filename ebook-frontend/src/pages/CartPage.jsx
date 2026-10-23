import { DeleteOutlined } from "@ant-design/icons";
import { Alert, Button, Card, Checkbox, Select, Space, Tag, Typography } from "antd";
import { Link, redirect, useActionData, useLoaderData, useNavigate, useSubmit } from "react-router-dom";
import ResourceTable from "../components/ResourceTable";
import RowActions from "../components/RowActions";
import {
  checkoutSelected,
  ensureCartLoaded,
  ensureBooksLoaded,
  removeCartItem,
  setPageSearch,
  toggleCartItem,
  toggleSelectAllCart,
  updateCartQty
} from "../data/appStore";
import { requireAuthSnapshot } from "../routes/authRouteHandlers";
import { getApiErrorMessage } from "../utils/apiError";
import { maxPurchasableQty, validateCheckoutSelection } from "../utils/stock";

export async function cartLoader() {
  requireAuthSnapshot();
  await ensureBooksLoaded();
  await ensureCartLoaded();
  const snapshot = requireAuthSnapshot();
  return {
    books: snapshot.books,
    cartItems: snapshot.cartItems,
    search: snapshot.searchByPage.cart
  };
}

export async function cartAction({ request }) {
  requireAuthSnapshot();
  const formData = await request.formData();
  const intent = String(formData.get("intent") || "");

  if (intent === "set-search") {
    setPageSearch("cart", String(formData.get("value") || ""));
    return null;
  }

  if (intent === "toggle-select-all") {
    await toggleSelectAllCart(formData.get("checked") === "true");
    return null;
  }

  if (intent === "toggle-item") {
    const bookId = String(formData.get("bookId") || "");
    const checked = formData.get("checked") === "true";
    if (bookId) {
      await toggleCartItem(bookId, checked);
    }
    return null;
  }

  if (intent === "update-qty") {
    const bookId = String(formData.get("bookId") || "");
    const qty = Number(formData.get("qty"));
    if (bookId && Number.isInteger(qty) && qty >= 1 && qty <= 4) {
      try {
        await updateCartQty(bookId, qty);
      } catch (error) {
        await ensureBooksLoaded(true);
        await ensureCartLoaded(true);
        return { status: "error", message: getApiErrorMessage(error, "更新数量失败。") };
      }
    }
    return null;
  }

  if (intent === "remove-item") {
    const bookId = String(formData.get("bookId") || "");
    if (bookId) {
      await removeCartItem(bookId);
    }
    return null;
  }

  if (intent === "checkout") {
    try {
      await checkoutSelected();
    } catch (error) {
      await ensureBooksLoaded(true);
      await ensureCartLoaded(true);
      return {
        status: "error",
        message: getApiErrorMessage(error, "结算失败，请检查库存后重试。")
      };
    }
    throw redirect("/orders");
  }

  return null;
}

// 购物车页：把购物车状态和图书信息合并后，再提供勾选、改数量和结算操作。
function CartPage({
  books,
  cartItems,
  search,
  actionError,
  onToggleSelectAll,
  onToggleItem,
  onUpdateQty,
  onRemoveItem,
  onCheckout
}) {
  const navigate = useNavigate();
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
  const checkoutBlockedMessage = validateCheckoutSelection(selectedRows);
  const allSelected = rows.length > 0 && selectedRows.length === rows.length;
  const subtotal = selectedRows.reduce((sum, row) => sum + row.subtotal, 0);

  const qtyOptionsForRow = (row) => {
    const maxQty = maxPurchasableQty(row.book);
    return Array.from({ length: maxQty }, (_, index) => {
      const value = index + 1;
      return { value, label: String(value) };
    });
  };

  // 使用 Ant Design Table 定义购物车列，统一表格渲染与交互控件。
  const columns = [
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
      title: "作者",
      dataIndex: "author",
      render: (_, row) => row.book.author
    },
    {
      title: "单价",
      dataIndex: "unitPrice",
      render: (_, row) => `￥${row.book.price.toFixed(2)}`
    },
    {
      title: "数量",
      dataIndex: "qty",
      render: (_, row) => (
        <Select
          size="small"
          value={Math.min(row.qty, maxPurchasableQty(row.book) || row.qty)}
          options={qtyOptionsForRow(row)}
          disabled={maxPurchasableQty(row.book) === 0}
          onChange={(value) => onUpdateQty(row.bookId, Number(value))}
        />
      )
    },
    {
      title: "小计",
      dataIndex: "subtotal",
      align: "right",
      render: (_, row) => <strong>￥{row.subtotal.toFixed(2)}</strong>
    },
    {
      title: "操作",
      dataIndex: "action",
      align: "right",
      render: (_, row) => (
        <RowActions
          actions={[
            {
              key: `remove-${row.bookId}`,
              label: "移除",
              danger: true,
              icon: <DeleteOutlined />,
              onClick: () => onRemoveItem(row.bookId)
            }
          ]}
        />
      )
    }
  ];

  const selectedRowKeys = rows.filter((row) => row.selected).map((row) => row.bookId);

  return (
    <section className="page card" aria-label="购物车页面">
      <header className="page__header">
        <Typography.Title level={3} className="page__title">我的购物车</Typography.Title>
        <Tag>共 {rows.length} 件</Tag>
      </header>

      {actionError ? (
        <div className="page__toolbar">
          <Alert type="error" showIcon message={actionError} />
        </div>
      ) : null}
      {checkoutBlockedMessage && selectedRows.length > 0 ? (
        <div className="page__toolbar">
          <Alert type="warning" showIcon message={checkoutBlockedMessage} />
        </div>
      ) : null}

      <section className="cart" aria-label="购物车内容区">
        <Card className="panel" title="商品">
          <Space className="cart-antd-toolbar">
            {/* 使用 Ant Design Checkbox 管理全选操作，仍然提交到原 action。 */}
            <Checkbox checked={allSelected} onChange={(event) => onToggleSelectAll(event.target.checked)}>
              全选
            </Checkbox>
          </Space>
          <ResourceTable
            rowKey="bookId"
            dataSource={rows}
            columns={columns}
            rowSelection={{
              selectedRowKeys,
              onSelect: (record, selected) => onToggleItem(record.bookId, selected),
              onSelectAll: (selected) => onToggleSelectAll(selected)
            }}
          />
        </Card>

        <Card
          className="panel"
          title="结算"
          extra={<Tag color="orange">待结算</Tag>}
        >
          {/* 使用 Ant Design Typography + Button 构建结算摘要与操作区。 */}
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

          <Space className="summary__actions">
            <Button onClick={() => navigate("/books")}>继续选购</Button>
            <Button
              type="primary"
              disabled={selectedRows.length === 0 || Boolean(checkoutBlockedMessage)}
              onClick={onCheckout}
            >
              结算
            </Button>
          </Space>
        </Card>
      </section>
    </section>
  );
}

export function CartRoute() {
  const data = useLoaderData();
  const actionData = useActionData();
  const submit = useSubmit();
  const actionError = actionData?.status === "error" ? actionData.message : null;

  return (
    <CartPage
      books={data.books}
      cartItems={data.cartItems}
      search={data.search}
      actionError={actionError}
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
    />
  );
}

export default CartPage;
