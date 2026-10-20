import { useEffect, useMemo, useRef, useState } from "react";
import { Alert, Button, Card, Collapse, Input, Space, Spin, Tag, Typography } from "antd";
import {
  ApiOutlined,
  BulbOutlined,
  DatabaseOutlined,
  RobotOutlined,
  SendOutlined,
  UserOutlined
} from "@ant-design/icons";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useLoaderData } from "react-router-dom";
import { fetchAssistantHealth, sendAssistantMessage } from "../api/assistantApi";
import { requireAuthSnapshot } from "../routes/authRouteHandlers";
import { handleSetSearchIntent } from "../routes/pageActions";
import "./AssistantPage.css";

// 示例问题覆盖合并后的四类工具：库存、比价、荐书、政策。
const EXAMPLE_QUESTIONS = [
  "帮我查一下 ISBN为978-3-00-000000-4 的书还有多少本，顺便看看别家卖多少钱",
  "我想买一本关于微服务的书，另外如果我买了不喜欢，拆了塑封还能退吗？",
  "退货运费谁承担？金卡会员有什么折扣？",
  "有没有讲 Rust 的书？"
];

export async function assistantLoader() {
  requireAuthSnapshot();
  const snapshot = requireAuthSnapshot();

  // 助手服务没启动不应让整个页面进错误边界，降级成一条提示即可。
  let health = null;
  let healthError = null;
  try {
    health = await fetchAssistantHealth();
  } catch (error) {
    healthError = error.message;
  }

  return { health, healthError, search: snapshot.searchByPage.assistant };
}

export async function assistantAction({ request }) {
  requireAuthSnapshot();
  const formData = await request.formData();
  handleSetSearchIntent(formData, "assistant");
  return null;
}

// 模型输出的 Markdown 由 react-markdown 渲染，remark-gfm 补上表格、删除线这些扩展语法。
// 默认不解析原始 HTML，外部链接统一加 target=_blank 与 noopener。
const MARKDOWN_COMPONENTS = {
  a: ({ node, ...props }) => <a {...props} target="_blank" rel="noopener noreferrer" />
};

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

/** 库存与售价：一行结论，数字用 Tag 标出来。 */
function InventoryResult({ result }) {
  return (
    <div className="assistant-facts">
      <span className="assistant-facts__title">《{result.title}》</span>
      <span className="assistant-facts__author">{result.author}</span>
      <Tag color={result.stockQty > 0 ? "green" : "red"}>
        {result.stockText} {result.stockQty} 本
      </Tag>
      <span>{result.price} 元</span>
    </div>
  );
}

/** 竞品报价：各平台价格与到货时间。 */
function PriceResult({ result }) {
  return (
    <ul className="assistant-quotes">
      {(result.quotes || []).map((quote) => (
        <li key={quote.platform} className="assistant-quotes__item">
          <span className="assistant-quotes__platform">{quote.platform}</span>
          <span>{quote.price} 元</span>
          <Tag color={quote.inStock ? "green" : "red"}>{quote.inStock ? "有货" : "缺货"}</Tag>
          <span className="assistant-quotes__delivery">{quote.deliveryDays} 天到</span>
        </li>
      ))}
      {result.lowestPrice ? (
        <li className="assistant-quotes__note">最低价 {result.lowestPrice} 元</li>
      ) : null}
    </ul>
  );
}

/** 书目检索：书名、价格、库存与相关度。 */
function BookResults({ result }) {
  return (
    <ul className="assistant-books">
      {(result.results || []).map((book) => (
        <li key={book.isbn} className="assistant-books__item">
          <div className="assistant-books__title">
            《{book.title}》<span className="assistant-books__author">{book.author}</span>
          </div>
          <div className="assistant-books__meta">
            <Tag color={book.inStock ? "green" : "red"}>
              {book.inStock ? `有货 ${book.stockQty} 本` : "缺货"}
            </Tag>
            <span>{book.price} 元</span>
            <span>{book.category}</span>
            <span className="assistant-books__score">相关度 {book.score}</span>
          </div>
        </li>
      ))}
      {result.outOfStockMatches?.length ? (
        <li className="assistant-books__note">
          另有匹配主题但缺货：{result.outOfStockMatches.map((title) => `《${title}》`).join("、")}
        </li>
      ) : null}
    </ul>
  );
}

/** 政策检索：条款号、相似度与原文，这是政策回答的依据。 */
function PolicyPassages({ result }) {
  return (
    <div className="assistant-passages">
      {(result.passages || []).map((passage) => (
        <div key={passage.id} className="assistant-passage">
          <div className="assistant-passage__head">
            <DatabaseOutlined />
            <span className="assistant-passage__heading">{passage.headingPath}</span>
            <Tag color="blue">{passage.score}</Tag>
            <span className="assistant-passage__id">{passage.id}</span>
          </div>
          <pre className="assistant-passage__text">{passage.text}</pre>
        </div>
      ))}
    </div>
  );
}

/** 一步执行：Thought → Action → Observation，观测按工具类型展开。
    hideThought 用于并行调用：同一轮里多个动作共享一句理由，只显示一次。 */
function StepCard({ step, hideThought }) {
  const error = step.result?.error;

  return (
    <div className={`assistant-step ${step.ok ? "assistant-step--ok" : "assistant-step--failed"}`}>
      <div className="assistant-step__head">
        <span className="assistant-step__index">步骤 {step.index}</span>
        <Tag color={step.ok ? "green" : "red"}>{step.ok ? "执行成功" : "执行失败"}</Tag>
        <span className="assistant-step__duration">{step.durationMs} ms</span>
      </div>

      {step.thought && !hideThought ? (
        <div className="assistant-step__section">
          <span className="assistant-step__label assistant-step__label--thought">
            <BulbOutlined /> Thought
          </span>
          <p className="assistant-step__thought">{step.thought}</p>
        </div>
      ) : null}

      <div className="assistant-step__section">
        <span className="assistant-step__label assistant-step__label--action">
          <ApiOutlined /> Action
        </span>
        <div className="assistant-step__action">
          <code className="assistant-step__name">{step.action}</code>
          <code className="assistant-step__args">{JSON.stringify(step.arguments)}</code>
          {step.parseError ? <Tag color="orange">参数解析失败</Tag> : null}
        </div>
      </div>

      <div className="assistant-step__section">
        <span className="assistant-step__label assistant-step__label--observation">Observation</span>
        {step.ok && step.action === "check_inventory" ? (
          <InventoryResult result={step.result} />
        ) : null}
        {step.ok && step.action === "get_competitor_price" ? (
          <PriceResult result={step.result} />
        ) : null}
        {step.ok && step.action === "search_book_catalog" ? (
          <BookResults result={step.result} />
        ) : null}
        {step.ok && step.action === "query_store_policy" ? (
          <PolicyPassages result={step.result} />
        ) : null}
        {!step.ok && error ? (
          <Alert
            type={error.retryable ? "warning" : "error"}
            showIcon
            message={error.message}
            description={error.hint}
            className="assistant-step__hint"
          />
        ) : null}
      </div>

      <Collapse
        ghost
        size="small"
        items={[
          {
            key: "raw",
            label: "完整返回",
            children: <pre className="assistant-step__json">{JSON.stringify(step.result, null, 2)}</pre>
          }
        ]}
      />
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
          {message.stoppedReason && message.stoppedReason !== "completed" ? (
            <Tag color="orange">{message.stoppedReason}</Tag>
          ) : null}
        </div>

        {message.steps?.length ? (
          <div className="assistant-msg__steps">
            {message.steps.map((step, index) => (
              <StepCard
                key={step.index}
                step={step}
                hideThought={index > 0 && step.thought === message.steps[index - 1].thought}
              />
            ))}
          </div>
        ) : null}

        {message.content ? (
          <MessageText content={message.content} markdown={!isUser} isError={Boolean(message.error)} />
        ) : null}
      </div>
    </div>
  );
}

function AssistantPage({ health, healthError, search }) {
  const [messages, setMessages] = useState([]);
  const [draft, setDraft] = useState("");
  const [pending, setPending] = useState(false);
  const threadRef = useRef(null);

  // 等待时滚到底部看进度；回答到达后停在最新一条助手消息的开头，
  // 让执行步骤先进入视野，需要时再往下读答复。
  useEffect(() => {
    const thread = threadRef.current;
    if (!thread) {
      return;
    }
    if (pending) {
      thread.scrollTop = thread.scrollHeight;
      return;
    }
    const replies = thread.querySelectorAll(".assistant-msg--bot");
    const latest = replies[replies.length - 1];
    if (!latest) {
      return;
    }
    const offset = latest.getBoundingClientRect().top - thread.getBoundingClientRect().top;
    thread.scrollTop = Math.max(0, thread.scrollTop + offset - 8);
  }, [messages, pending]);

  const keyword = search.trim().toLowerCase();
  const visibleMessages = useMemo(() => {
    if (!keyword) {
      return messages;
    }
    return messages.filter((message) =>
      [
        message.content,
        ...(message.steps || []).map(
          (step) => `${step.thought} ${step.action} ${JSON.stringify(step.arguments)}`
        )
      ]
        .join(" ")
        .toLowerCase()
        .includes(keyword)
    );
  }, [messages, keyword]);

  async function ask(question) {
    const trimmed = question.trim();
    if (!trimmed || pending) {
      return;
    }

    // 只带角色与文本：每次请求的工具轨迹由服务端重新执行，不把旧轨迹塞回上下文。
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
          steps: result.steps,
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

        <div className="assistant__thread" ref={threadRef}>
          {visibleMessages.map((message, index) => (
            <MessageBubble key={index} message={message} />
          ))}
          {pending ? (
            <div className="assistant__pending">
              <Spin size="small" />
              <span>正在查询…</span>
            </div>
          ) : null}
        </div>

        <div className="assistant__examples">
          <Space wrap>
            {EXAMPLE_QUESTIONS.map((question) => (
              <Button key={question} size="small" disabled={pending} onClick={() => ask(question)}>
                {question.length > 30 ? `${question.slice(0, 30)}…` : question}
              </Button>
            ))}
          </Space>
        </div>

        <div className="assistant__composer">
          <Input.TextArea
            value={draft}
            autoSize={{ minRows: 1, maxRows: 4 }}
            placeholder="问库存、比价、找书，或退换货与会员政策"
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
