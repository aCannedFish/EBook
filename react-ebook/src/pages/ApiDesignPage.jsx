import { useEffect, useState } from "react";
import { Alert, Button, Card, Collapse, Input, Space, Tag, Typography } from "antd";
import { requireAdminSnapshot } from "../routes/authRouteHandlers";
import { authHeaders, notifyUnauthorized } from "../api/auth";

/** 在原书城展示实际模型 API 对话与生成的契约，截图直接来自正在运行的页面。 */
export function apiDesignLoader() {
  requireAdminSnapshot();
  return null;
}

async function designRequest(path, options = {}) {
  const response = await fetch(`/assistant-api/api/design/${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...authHeaders() }
  });
  if (response.status === 401) {
    notifyUnauthorized();
  }
  const body = await response.json();
  if (!response.ok) {
    throw new Error(body.detail || "接口文档生成失败");
  }
  return body;
}

export default function ApiDesignPage() {
  const [record, setRecord] = useState({ messages: [] });
  const [input, setInput] = useState("请根据现有书城接口，生成完整的 OpenAPI 3.0.3 JSON 契约。");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    designRequest("conversation").then(setRecord).catch((failure) => setError(failure.message));
  }, []);

  async function send() {
    if (!input.trim()) {
      return;
    }
    setPending(true);
    setError("");
    try {
      await designRequest("chat", {
        method: "POST",
        body: JSON.stringify({
          message: input.trim(),
          history: record.messages.filter((message) => message.role !== "system")
        })
      });
      setRecord(await designRequest("conversation"));
      setInput("");
    } catch (failure) {
      setError(failure.message);
    } finally {
      setPending(false);
    }
  }

  const system = record.messages.find((message) => message.role === "system");
  return (
    <Card title="接口设计对话">
      <Space wrap style={{ marginBottom: 16 }}>
        <Tag color="blue">{record.model || "真实模型 API"}</Tag>
        {record.generatedAt ? <Typography.Text>实际生成时间：{record.generatedAt}</Typography.Text> : null}
        {record.validation?.valid ? <Tag color="green">契约校验通过</Tag> : null}
      </Space>
      <Collapse items={[{
        key: "system", label: "完整 System Prompt",
        children: <pre style={{ whiteSpace: "pre-wrap" }}>{system?.content || "正在读取"}</pre>
      }]} />
      <Space direction="vertical" style={{ width: "100%", margin: "16px 0" }}>
        {record.messages.filter((message) => message.role !== "system").map((message, index) => (
          <Card key={index} size="small" title={message.role === "user" ? "User Prompt" : "模型 API 回复"}>
            {message.role === "user" ? <Typography.Paragraph>{message.content}</Typography.Paragraph> : (
              <>
                <Typography.Paragraph>已生成 OpenAPI 3.0.3 JSON，覆盖书目列表、图书详情、新增图书和库存更新。</Typography.Paragraph>
                <Collapse items={[{
                  key: "json", label: "查看完整 JSON",
                  children: <pre style={{ overflow: "auto", maxHeight: 420 }}>{message.content}</pre>
                }]} />
              </>
            )}
          </Card>
        ))}
      </Space>
      {error ? <Alert type="error" message={error} showIcon /> : null}
      <Input.TextArea aria-label="接口设计问题" value={input} onChange={(event) => setInput(event.target.value)} rows={3} />
      <Space style={{ marginTop: 12 }}>
        <Button type="primary" loading={pending} onClick={send}>发送到模型</Button>
        <Button onClick={() => setInput("请再次核对 page 默认 0、size 默认 20 且最大 100、category 过滤、401/403/404 响应和库存 PATCH。保持路径、operationId 和 Schema 不变，输出修订后的完整 JSON。")}>
          核对接口约束
        </Button>
      </Space>
    </Card>
  );
}
