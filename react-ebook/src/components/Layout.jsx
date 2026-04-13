// 兼容层：保留旧的 `Layout` 引用路径，避免外部代码因重构而失效。
// 该文件本身不包含 UI，只是把默认导出转发到新的 `DashboardLayout`。
export { default } from "./DashboardLayout";

