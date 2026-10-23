import { Tag } from "antd";

// StatusTag：复用状态标签渲染，统一颜色与文案映射。
function StatusTag({ status, metaMap }) {
  const meta = metaMap[status];
  if (!meta) {
    return <Tag>{status}</Tag>;
  }
  return <Tag color={meta.color}>{meta.label}</Tag>;
}

export default StatusTag;
