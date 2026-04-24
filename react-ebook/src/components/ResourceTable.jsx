import { Table } from "antd";

// ResourceTable：购物车/订单复用的表格壳，统一基础配置。
function ResourceTable({ rowKey, dataSource, columns, rowSelection }) {
  return (
    <Table
      rowKey={rowKey}
      dataSource={dataSource}
      columns={columns}
      pagination={false}
      rowSelection={rowSelection}
    />
  );
}

export default ResourceTable;
