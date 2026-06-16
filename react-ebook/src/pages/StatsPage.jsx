import { Input, Space, Table, Tabs, Tag, Typography } from "antd";
import { useLoaderData, useSubmit } from "react-router-dom";
import { loadStats, setPageSearch, setStatsFilters } from "../data/appStore";
import { requireAuthSnapshot } from "../routes/authRouteHandlers";
import { formatPrice } from "../utils/format";
import { isAdmin } from "../utils/role";

export async function statsLoader() {
  const snapshot = requireAuthSnapshot();
  const stats = await loadStats(true);
  return {
    ...stats,
    user: snapshot.user,
    search: snapshot.searchByPage.stats,
    filters: snapshot.statsFilters
  };
}

export async function statsAction({ request }) {
  requireAuthSnapshot();
  const formData = await request.formData();
  const intent = String(formData.get("intent") || "");

  if (intent === "set-search") {
    setPageSearch("stats", String(formData.get("value") || ""));
    return null;
  }

  if (intent === "set-filters") {
    setStatsFilters({
      from: String(formData.get("from") || ""),
      to: String(formData.get("to") || "")
    });
    await loadStats(true);
    return null;
  }

  return null;
}

function StatsPage({ user, bookSalesStats, userSpendingStats, myPurchaseStats, filters, onFilterChange }) {
  const admin = isAdmin(user);

  const bookColumns = [
    { title: "书名", dataIndex: "title" },
    { title: "销量（本）", dataIndex: "totalQty", sorter: (a, b) => a.totalQty - b.totalQty },
    {
      title: "销售额",
      dataIndex: "totalAmount",
      render: (value) => formatPrice(value),
      sorter: (a, b) => a.totalAmount - b.totalAmount
    }
  ];

  const spendingColumns = [
    { title: "用户名", dataIndex: "username" },
    { title: "购书总本数", dataIndex: "totalQty" },
    {
      title: "累计消费",
      dataIndex: "totalAmount",
      render: (value) => formatPrice(value)
    }
  ];

  const myColumns = [
    { title: "书名", dataIndex: "title" },
    { title: "购买数量", dataIndex: "qty" },
    { title: "金额", dataIndex: "amount", render: (value) => formatPrice(value) }
  ];

  const filterBar = (
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
        <Tag color="blue">不含已取消订单</Tag>
      </Space>
    </div>
  );

  if (admin) {
    return (
      <section className="page card" aria-label="统计页面">
        <header className="page__header">
          <Typography.Title level={3} className="page__title">数据统计</Typography.Title>
        </header>
        {filterBar}
        <div className="page__section">
          <Tabs
            items={[
              {
                key: "sales",
                label: "热销榜",
                children: <Table rowKey="bookId" columns={bookColumns} dataSource={bookSalesStats} pagination={false} />
              },
              {
                key: "spending",
                label: "消费榜",
                children: <Table rowKey="userId" columns={spendingColumns} dataSource={userSpendingStats} pagination={false} />
              }
            ]}
          />
        </div>
      </section>
    );
  }

  return (
    <section className="page card" aria-label="我的购书统计">
      <header className="page__header">
        <Typography.Title level={3} className="page__title">我的购书统计</Typography.Title>
        <Space>
          <Tag color="blue">总本数：{myPurchaseStats?.totalQty || 0}</Tag>
          <Tag color="green">总金额：{formatPrice(myPurchaseStats?.totalAmount || 0)}</Tag>
        </Space>
      </header>
      {filterBar}
      <div className="page__section">
        <Table rowKey="bookId" columns={myColumns} dataSource={myPurchaseStats?.items || []} pagination={false} />
      </div>
    </section>
  );
}

export function StatsRoute() {
  const data = useLoaderData();
  const submit = useSubmit();

  return (
    <StatsPage
      {...data}
      onFilterChange={(partial) =>
        submit(
          {
            intent: "set-filters",
            from: partial.from ?? data.filters.from,
            to: partial.to ?? data.filters.to
          },
          { method: "post", navigate: false }
        )
      }
    />
  );
}

export default StatsPage;
