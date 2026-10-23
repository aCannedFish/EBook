import { Button, Space } from "antd";

// RowActions：复用行操作按钮组，按配置渲染按钮。
function RowActions({ actions }) {
  return (
    <Space>
      {actions
        .filter((action) => !action.hidden)
        .map((action) => (
          <Button
            key={action.key}
            type={action.type}
            size={action.size || "small"}
            danger={action.danger}
            icon={action.icon}
            onClick={action.onClick}
            disabled={action.disabled}
          >
            {action.label}
          </Button>
        ))}
    </Space>
  );
}

export default RowActions;
