import { Table } from "antd";

// ResourceTable：购物车/订单等复用的表格壳，窄屏下支持横向滚动。
function ResourceTable({ rowKey, dataSource, columns, rowSelection, scrollX = "max-content" }) {
  return (
    <div className="resource-table-wrapper">
      <Table
        rowKey={rowKey}
        dataSource={dataSource}
        columns={columns}
        pagination={false}
        rowSelection={rowSelection}
        scroll={{ x: scrollX }}
        tableLayout="auto"
      />
    </div>
  );
}

export default ResourceTable;
