import { useMemo, useState } from "react";
import {
  Alert,
  Button,
  Card,
  Collapse,
  Empty,
  Input,
  Space,
  Spin,
  Switch,
  Tag,
  Tooltip,
  Typography
} from "antd";
import {
  ApiOutlined,
  BulbOutlined,
  DatabaseOutlined,
  ExperimentOutlined,
  SendOutlined,
  UserOutlined
} from "@ant-design/icons";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useLoaderData } from "react-router-dom";
import { fetchGuideHealth, sendGuideMessage } from "../api/guideApi";
import { requireAuthSnapshot } from "../routes/authRouteHandlers";
import { handleSetSearchIntent } from "../routes/pageActions";
import "./GuidePage.css";

// 例子都来自演示脚本：第一句就是作业要求的复杂交互 Case（找书 + 问政策）。
const EXAMPLE_QUESTIONS = [
  "我想买一本关于算法的书，另外如果我买了不喜欢，拆了塑封还能退吗？",
  "我想买一本 100 元以内的微服务书，最好有现货；另外我是金卡会员，拆了塑封还能退吗？",
  "退货运费谁承担？另外金卡会员有什么折扣？",
  "有没有讲 Rust 的书？"
];

const markdownComponents = {
  a: ({ node, ...props }) => <a {...props} target="_blank" rel="noopener noreferrer" />
};

export async function guideLoader() {
  requireAuthSnapshot();
  const snapshot = requireAuthSnapshot();

  // 助手服务没起不应该让页面进错误边界，降级成一条提示。
  let health = null;
  let healthError = null;
  try {
    health = await fetchGuideHealth();
  } catch (error) {
    healthError = error.message;
  }

  return { health, healthError, search: snapshot.searchByPage.guide };
}

export async function guideAction({ request }) {
  requireAuthSnapshot();
  const formData = await request.formData();
  handleSetSearchIntent(formData, "guide");
  return null;
}

/** 一行摘要：不展开细节时看这一行就够了。 */
function observationSummary(step) {
  const result = step.result || {};
  if (!step.ok) {
    const error = result.error || {};
    return `${error.code || "失败"}：${error.message || "工具调用失败"}`;
  }
  if (step.action === "query_store_policy") {
    return `命中 ${result.count} 条条款，最高相似度 ${result.topScore}`;
  }
  if (step.action === "search_book_catalog") {
    const titles = (result.results || []).map((book) => `《${book.title}》`).join("、");
    return `命中 ${result.count} 本：${titles}`;
  }
  return "已执行";
}

/** 书目检索的结构化观测：把书名、价格、库存摊开，不用去看 JSON。 */
function BookResults({ result }) {
  return (
    <ul className="guide-books">
      {(result.results || []).map((book) => (
        <li key={book.isbn} className="guide-books__item">
          <div className="guide-books__title">
            《{book.title}》<span className="guide-books__author">{book.author}</span>
          </div>
          <div className="guide-books__meta">
            <Tag color={book.inStock ? "green" : "red"}>
              {book.inStock ? `有货 ${book.stockQty} 本` : "缺货"}
            </Tag>
            <span>{book.price} 元</span>
            <span>{book.category}</span>
            <span className="guide-books__score">相关度 {book.score}</span>
          </div>
        </li>
      ))}
      {result.outOfStockMatches?.length ? (
        <li className="guide-books__note">
          另有匹配主题但缺货：{result.outOfStockMatches.map((title) => `《${title}》`).join("、")}
        </li>
      ) : null}
    </ul>
  );
}

/** RAG 检索的结构化观测：条款号、相似度与引用原文，这是政策回答的依据。 */
function PolicyPassages({ result }) {
  return (
    <div className="guide-passages">
      <Typography.Text type="secondary" className="guide-passages__hint">
        检索用词：{result.question} · 相似度闸门以上共 {result.count} 条
      </Typography.Text>
      {(result.passages || []).map((passage) => (
        <div key={passage.id} className="guide-passage">
          <div className="guide-passage__head">
            <DatabaseOutlined />
            <span className="guide-passage__heading">{passage.headingPath}</span>
            <Tag color="blue">{passage.score}</Tag>
            <span className="guide-passage__id">{passage.id}</span>
          </div>
          <pre className="guide-passage__text">{passage.text}</pre>
        </div>
      ))}
    </div>
  );
}

/** 一步 ReAct：Thought → Action → Observation。 */
function StepCard({ step }) {
  const error = step.result?.error;

  return (
    <div className={`guide-step ${step.ok ? "guide-step--ok" : "guide-step--failed"}`}>
      <div className="guide-step__head">
        <span className="guide-step__index">步骤 {step.index}</span>
        <Tag color={step.ok ? "green" : "red"}>{step.ok ? "执行成功" : "执行失败"}</Tag>
        <span className="guide-step__duration">{step.durationMs} ms</span>
      </div>

      <div className="guide-step__section">
        <span className="guide-step__label guide-step__label--thought">
          <BulbOutlined /> Thought
        </span>
        <p className="guide-step__thought">{step.thought || "（模型未给出推理）"}</p>
      </div>

      <div className="guide-step__section">
        <span className="guide-step__label guide-step__label--action">
          <ApiOutlined /> Action
        </span>
        <div className="guide-step__action">
          <code className="guide-step__name">{step.action}</code>
          <code className="guide-step__args">{JSON.stringify(step.arguments)}</code>
          {step.parseError ? <Tag color="orange">参数解析失败</Tag> : null}
        </div>
      </div>

      <div className="guide-step__section">
        <span className="guide-step__label guide-step__label--observation">Observation</span>
        <div className="guide-step__observation">{observationSummary(step)}</div>
        {step.ok && step.action === "search_book_catalog" ? (
          <BookResults result={step.result} />
        ) : null}
        {step.ok && step.action === "query_store_policy" ? (
          <PolicyPassages result={step.result} />
        ) : null}
        {error?.hint ? (
          <Alert
            banner
            type={error.retryable ? "warning" : "error"}
            message={`回传给模型的纠错提示：${error.hint}`}
            className="guide-step__hint"
          />
        ) : null}
      </div>

      <Collapse
        ghost
        size="small"
        items={[
          {
            key: "raw",
            label: "查看完整观测（回填给模型的内容）",
            children: <pre className="guide-step__json">{JSON.stringify(step.result, null, 2)}</pre>
          }
        ]}
      />
    </div>
  );
}

function MessageBubble({ message }) {
  const isUser = message.role === "user";

  return (
    <div className={`guide-msg ${isUser ? "guide-msg--user" : "guide-msg--bot"}`}>
      <div className="guide-msg__avatar">{isUser ? <UserOutlined /> : <ExperimentOutlined />}</div>
      <div className="guide-msg__body">
        <div className="guide-msg__meta">
          <span>{isUser ? "我" : "导购助手"}</span>
          {message.modelMode ? <Tag color="blue">{message.modelMode}</Tag> : null}
          {message.rounds ? <span>{message.rounds} 轮</span> : null}
          {message.stoppedReason && message.stoppedReason !== "completed" ? (
            <Tag color="orange">{message.stoppedReason}</Tag>
          ) : null}
        </div>

        {message.steps?.length ? (
          <div className="guide-msg__steps">
            <Typography.Text type="secondary" className="guide-msg__steps-title">
              Agent 的推理与工具调用过程（Thought → Action → Observation）：
            </Typography.Text>
            {message.steps.map((step) => (
              <StepCard key={step.index} step={step} />
            ))}
          </div>
        ) : null}

        {message.content ? (
          <div className={`guide-msg__text ${message.error ? "guide-msg__text--error" : ""}`}>
            {isUser ? (
              message.content.split("\n").map((line, index) => <p key={index}>{line}</p>)
            ) : (
              <Markdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                {message.content}
              </Markdown>
            )}
          </div>
        ) : null}
      </div>
    </div>
  );
}

function GuidePage({ health, healthError, search }) {
  const [messages, setMessages] = useState([]);
  const [draft, setDraft] = useState("");
  const [pending, setPending] = useState(false);
  const [useRemote, setUseRemote] = useState(false);

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

  const ragStats = health?.ragStats || {};

  async function ask(question) {
    const trimmed = question.trim();
    if (!trimmed || pending) {
      return;
    }

    setMessages((previous) => [...previous, { role: "user", content: trimmed }]);
    setDraft("");
    setPending(true);

    try {
      const result = await sendGuideMessage(trimmed, useRemote);
      setMessages((previous) => [
        ...previous,
        {
          role: "assistant",
          content: result.reply,
          steps: result.steps,
          modelMode: result.modelMode,
          rounds: result.rounds,
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
    <section className="guide">
      <Card
        className="guide__panel"
        title={
          <Space wrap>
            <ExperimentOutlined />
            <span>导购助手</span>
            <Tag color="purple">RAG + ReAct</Tag>
            {health ? (
              <>
                <Tag color={health.rag === "ready" ? "green" : "red"}>
                  政策库 {health.rag === "ready" ? `就绪 ${ragStats.count} 块` : "不可用"}
                </Tag>
                <Tooltip title={`向量化：${ragStats.embedderNote || "未知"}`}>
                  <Tag>{ragStats.dimensions} 维向量</Tag>
                </Tooltip>
                <Tag>{health.catalogSize} 本在售</Tag>
              </>
            ) : null}
          </Space>
        }
        extra={
          <Space>
            <Tooltip title="用配好的真实模型替代内置的离线替身模型；未配置密钥时不可用">
              <Space size={4}>
                <Switch
                  size="small"
                  checked={useRemote}
                  disabled={!health?.llmConfigured}
                  onChange={setUseRemote}
                />
                <Typography.Text type="secondary">真实模型</Typography.Text>
              </Space>
            </Tooltip>
            <Button size="small" onClick={() => setMessages([])} disabled={!messages.length}>
              清空对话
            </Button>
          </Space>
        }
      >
        {healthError ? (
          <Alert
            type="warning"
            showIcon
            message="没有连上导购助手服务"
            description={healthError}
            className="guide__alert"
          />
        ) : null}

        <div className="guide__thread">
          {visibleMessages.length ? (
            visibleMessages.map((message, index) => <MessageBubble key={index} message={message} />)
          ) : (
            <Empty
              className="guide__empty"
              description={
                messages.length
                  ? "没有匹配的对话或调用"
                  : "问我某类主题有什么书，或者退换货与会员政策怎么规定"
              }
            />
          )}
          {pending ? (
            <div className="guide__pending">
              <Spin size="small" />
              <span>Agent 正在推理并调用工具（Thought → Action → Observation）……</span>
            </div>
          ) : null}
        </div>

        <div className="guide__examples">
          <Typography.Text type="secondary">示例问题：</Typography.Text>
          <Space wrap>
            {EXAMPLE_QUESTIONS.map((question) => (
              <Button key={question} size="small" disabled={pending} onClick={() => ask(question)}>
                {question.length > 30 ? `${question.slice(0, 30)}…` : question}
              </Button>
            ))}
          </Space>
        </div>

        <div className="guide__composer">
          <Input.TextArea
            value={draft}
            autoSize={{ minRows: 1, maxRows: 4 }}
            placeholder="例如：我想买一本关于算法的书，另外如果我买了不喜欢，拆了塑封还能退吗？"
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

export function GuideRoute() {
  const { health, healthError, search } = useLoaderData();
  return <GuidePage health={health} healthError={healthError} search={search} />;
}

export default GuidePage;
