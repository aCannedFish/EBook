import { useState } from "react";
import { Alert, Button, Card, Collapse, Empty, Input, Space, Spin, Tag, Typography } from "antd";
import { ApiOutlined, RobotOutlined, SendOutlined, UserOutlined } from "@ant-design/icons";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useLoaderData } from "react-router-dom";
import { fetchAssistantHealth, sendAssistantMessage } from "../api/assistantApi";
import { requireAuthSnapshot } from "../routes/authRouteHandlers";
import { handleSetSearchIntent } from "../routes/pageActions";
import "./AssistantPage.css";

// 作业里给出的那句提问，放在这里是方便演示：点一下就能跑通完整链路。
const EXAMPLE_QUESTIONS = [
  "帮我查一下 ISBN为978-3-00-000000-4 的书还有多少本，顺便看看别家卖多少钱",
  "ISBN为12345 的书还有多少本",
  "ISBN为978-7-00-000000-8 的书还有几本？另外帮我对比一下其他平台的价格",
  "《量子物理》还有货吗？"
];

export async function assistantLoader() {
  requireAuthSnapshot();
  const snapshot = requireAuthSnapshot();

  let health = null;
  let healthError = null;
  try {
    health = await fetchAssistantHealth();
  } catch (error) {
    // 助手服务没启动不应该让整个页面进错误边界，降级成一条提示即可。
    healthError = error.message;
  }

  return {
    health,
    healthError,
    search: snapshot.searchByPage.assistant
  };
}

export async function assistantAction({ request }) {
  requireAuthSnapshot();
  const formData = await request.formData();
  handleSetSearchIntent(formData, "assistant");
  return null;
}

// 模型输出的 Markdown 由 react-markdown 渲染，remark-gfm 补上表格、删除线、任务列表这些扩展语法
// （模型很爱用表格做价格对比）。默认不解析原始 HTML，所以模型输出里的 <script> 之类只会被当文本转义，
// 不存在注入风险；外部链接统一加 target=_blank 与 noopener。
const MARKDOWN_COMPONENTS = {
  a: ({ node, ...props }) => <a {...props} target="_blank" rel="noopener noreferrer" />
};

// 助手回复按 Markdown 渲染；用户自己敲的是纯文本，按段落显示即可，避免被当成语法误解析。
function MessageText({ content, markdown, isError }) {
  const className = `assistant-msg__text ${markdown ? "assistant-md" : ""} ${
    isError ? "assistant-msg__text--error" : ""
  }`;

  if (!markdown) {
    return (
      <div className={className}>
        {content.split("\n").map((line, index) => (
          <p key={index}>{line}</p>
        ))}
      </div>
    );
  }

  return (
    <div className={className}>
      <Markdown remarkPlugins={[remarkGfm]} components={MARKDOWN_COMPONENTS}>
        {content}
      </Markdown>
    </div>
  );
}

// 单次函数调用的展示卡片：函数名、参数、执行结果、耗时。
// 作业要求「打印需要调用的函数名及参数」，这里把它做成了界面的一部分。
function ToolCallCard({ call }) {
  const error = call.result?.error;
  const summary = error ? `${error.code}｜${error.message}` : `返回 ${Object.keys(call.result || {}).length} 个字段`;

  return (
    <div className={`assistant-tool ${call.ok ? "assistant-tool--ok" : "assistant-tool--failed"}`}>
      <div className="assistant-tool__head">
        <ApiOutlined className="assistant-tool__icon" />
        <Typography.Text code>{call.name}</Typography.Text>
        <Tag color={call.ok ? "green" : "red"}>{call.ok ? "调用成功" : "调用失败"}</Tag>
        <Typography.Text type="secondary">
          第 {call.round} 轮 · {call.durationMs} ms
        </Typography.Text>
      </div>

      <div className="assistant-tool__row">
        <span className="assistant-tool__label">参数</span>
        <code className="assistant-tool__code">
          {call.name}({JSON.stringify(call.arguments)})
        </code>
      </div>
      <div className="assistant-tool__row">
        <span className="assistant-tool__label">结果</span>
        <span className="assistant-tool__summary">{summary}</span>
      </div>

      <Collapse
        ghost
        size="small"
        items={[
          {
            key: "result",
            label: "查看完整返回",
            children: <pre className="assistant-tool__json">{JSON.stringify(call.result, null, 2)}</pre>
          }
        ]}
      />

      {error?.hint ? (
        <Alert
          banner
          type={error.retryable ? "warning" : "error"}
          message={`回传给模型的纠错提示：${error.hint}`}
          className="assistant-tool__hint"
        />
      ) : null}
    </div>
  );
}

function MessageBubble({ message }) {
  const isUser = message.role === "user";

  return (
    <div className={`assistant-msg ${isUser ? "assistant-msg--user" : "assistant-msg--bot"}`}>
      <div className="assistant-msg__avatar">{isUser ? <UserOutlined /> : <RobotOutlined />}</div>
      <div className="assistant-msg__body">
        <div className="assistant-msg__meta">
          <span>{isUser ? "我" : "客服助手"}</span>
          {message.modelMode ? <Tag color="blue">{message.modelMode}</Tag> : null}
          {message.stoppedReason && message.stoppedReason !== "completed" ? (
            <Tag color="orange">{message.stoppedReason}</Tag>
          ) : null}
        </div>

        {message.toolCalls?.length ? (
          <div className="assistant-msg__tools">
            <Typography.Text type="secondary" className="assistant-msg__tools-title">
              模型请求调用 {message.toolCalls.length} 个函数，已拦截并本地执行：
            </Typography.Text>
            {message.toolCalls.map((call, index) => (
              <ToolCallCard key={`${call.name}-${call.round}-${index}`} call={call} />
            ))}
          </div>
        ) : null}

        {message.content ? (
          <MessageText
            content={message.content}
            markdown={!isUser}
            isError={Boolean(message.error)}
          />
        ) : null}
      </div>
    </div>
  );
}

function AssistantPage({ health, healthError, search }) {
  const [messages, setMessages] = useState([]);
  const [draft, setDraft] = useState("");
  const [pending, setPending] = useState(false);

  const keyword = search.trim().toLowerCase();
  const visibleMessages = keyword
    ? messages.filter((message) => {
        const haystack = [
          message.content,
          ...(message.toolCalls || []).map(
            (call) => `${call.name} ${JSON.stringify(call.arguments)} ${JSON.stringify(call.result)}`
          )
        ]
          .join(" ")
          .toLowerCase();
        return haystack.includes(keyword);
      })
    : messages;

  async function ask(question) {
    const trimmed = question.trim();
    if (!trimmed || pending) {
      return;
    }

    // 本地历史只保留角色与文本：服务端已经有完整的 tool 消息轨迹，
    // 前端只负责把多轮上下文带过去，不重复实现一遍消息拼接。
    const history = messages
      .filter((message) => message.content && !message.error)
      .map((message) => ({ role: message.role, content: message.content }));

    setMessages((previous) => [...previous, { role: "user", content: trimmed }]);
    setDraft("");
    setPending(true);

    try {
      const result = await sendAssistantMessage(trimmed, history);
      setMessages((previous) => [
        ...previous,
        {
          role: "assistant",
          content: result.reply,
          toolCalls: result.toolCalls,
          modelMode: result.modelMode,
          stoppedReason: result.stoppedReason
        }
      ]);
    } catch (error) {
      setMessages((previous) => [
        ...previous,
        { role: "assistant", content: error.message, error: true }
      ]);
    } finally {
      setPending(false);
    }
  }

  return (
    <section className="assistant">
      <Card
        className="assistant__panel"
        title={
          <Space>
            <RobotOutlined />
            <span>客服助手</span>
            {health ? <Tag color="blue">{health.modelMode}</Tag> : null}
          </Space>
        }
        extra={
          <Button size="small" onClick={() => setMessages([])} disabled={!messages.length}>
            清空对话
          </Button>
        }
      >
        {healthError ? (
          <Alert
            type="warning"
            showIcon
            message="没有连上助手服务"
            description={healthError}
            className="assistant__alert"
          />
        ) : null}

        <div className="assistant__thread">
          {visibleMessages.length ? (
            visibleMessages.map((message, index) => (
              <MessageBubble key={index} message={message} />
            ))
          ) : (
            <Empty
              className="assistant__empty"
              description={
                messages.length
                  ? "没有匹配的对话内容"
                  : "问我某本书还有多少本、本店卖多少钱，或者别家卖多少钱"
              }
            />
          )}
          {pending ? (
            <div className="assistant__pending">
              <Spin size="small" />
              <span>助手正在调用函数查询……</span>
            </div>
          ) : null}
        </div>

        <div className="assistant__examples">
          <Typography.Text type="secondary">示例问题：</Typography.Text>
          <Space wrap>
            {EXAMPLE_QUESTIONS.map((question) => (
              <Button
                key={question}
                size="small"
                disabled={pending}
                onClick={() => ask(question)}
              >
                {question.length > 28 ? `${question.slice(0, 28)}…` : question}
              </Button>
            ))}
          </Space>
        </div>

        <div className="assistant__composer">
          <Input.TextArea
            value={draft}
            autoSize={{ minRows: 1, maxRows: 4 }}
            placeholder="例如：帮我查一下 ISBN为978-3-00-000000-4 的书还有多少本，顺便看看别家卖多少钱"
            onChange={(event) => setDraft(event.target.value)}
            onPressEnter={(event) => {
              if (!event.shiftKey) {
                event.preventDefault();
                ask(draft);
              }
            }}
          />
          <Button type="primary" icon={<SendOutlined />} loading={pending} onClick={() => ask(draft)}>
            发送
          </Button>
        </div>
      </Card>
    </section>
  );
}

export function AssistantRoute() {
  const { health, healthError, search } = useLoaderData();
  return <AssistantPage health={health} healthError={healthError} search={search} />;
}

export default AssistantPage;
