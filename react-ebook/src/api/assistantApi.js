import { authHeaders, notifyUnauthorized } from "./auth";

// 客服助手后端（python-assistant/ 的 FastAPI 服务）的请求封装。
// 与 backendApi.js 分开，是因为它指向另一个进程：默认 http://localhost:8000，
// 而书城业务后端是 http://localhost:8080。
//
// 开发时默认走 Vite 代理的同源路径 /assistant-api（见 vite.config.js），
// 这样前端是普通同源请求，不依赖助手服务的 CORS 配置。
const ASSISTANT_BASE_URL =
  import.meta.env.VITE_ASSISTANT_API_BASE_URL ??
  (import.meta.env.DEV ? "/assistant-api" : "http://localhost:8000");

async function fetchResponse(path, options = {}) {
  let response;
  try {
    response = await fetch(`${ASSISTANT_BASE_URL}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...authHeaders(),
        ...(options.headers || {})
      }
    });
  } catch (error) {
    if (options.signal?.aborted) {
      throw error;
    }
    throw new Error(
      "无法连接客服助手服务。请在 python-assistant 目录执行 ./run-local.sh 启动助手后端（默认 127.0.0.1:8000）。"
    );
  }

  if (response.status === 401) {
    notifyUnauthorized();
  }
  if (!response.ok) {
    let message = `助手服务返回 ${response.status}`;
    try {
      const body = await response.json();
      if (body?.detail) {
        message = String(body.detail);
      }
    } catch {
      // 非 JSON 错误体，保留默认文案
    }
    throw new Error(message);
  }

  return response;
}

async function request(path, options = {}) {
  return (await fetchResponse(path, options)).json();
}

/** 一次问答。history 传 OpenAI 消息格式，用于多轮上下文。 */
export function sendAssistantMessage(message, history = []) {
  return request("/api/assistant/chat", {
    method: "POST",
    body: JSON.stringify({ message, history })
  });
}

/** 助手服务状态：用来在界面上标明当前是真实模型还是离线替身模型。 */
export function fetchAssistantHealth() {
  return request("/api/assistant/health");
}

/** 历史会话及消息由服务端按当前 JWT 对应的用户保存。 */
export function fetchAssistantSessions(signal) {
  return request("/api/assistant/sessions", { signal });
}

export function createAssistantSession() {
  return request("/api/assistant/sessions", { method: "POST" });
}

export function fetchAssistantSession(sessionId, signal) {
  return request(`/api/assistant/sessions/${encodeURIComponent(sessionId)}`, { signal });
}

export function sendSessionMessage(sessionId, message) {
  return request(`/api/assistant/sessions/${encodeURIComponent(sessionId)}/messages`, {
    method: "POST",
    body: JSON.stringify({ message })
  });
}

/**
 * 用 Fetch 读取 SSE，允许携带书城 Bearer Token；UTF-8 解码器跨网络分片保留状态。
 * 帧可能被拆开或合并，只有读到空行才解析事件。游标供断线后继续订阅。
 */
export async function watchAssistantSession(sessionId, after, onMessage, signal) {
  const response = await fetchResponse(
    `/api/assistant/sessions/${encodeURIComponent(sessionId)}/events?after=${after}`,
    { signal, headers: { Accept: "text/event-stream" } }
  );
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { value, done } = await reader.read();
      buffer += decoder.decode(value, { stream: !done });
      buffer = buffer.replace(/\r\n/g, "\n");
      let boundary;
      while ((boundary = buffer.indexOf("\n\n")) !== -1) {
        const frame = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2);
        const lines = frame.split("\n");
        const event = lines.find((line) => line.startsWith("event:"))?.slice(6).trim();
        const id = Number(lines.find((line) => line.startsWith("id:"))?.slice(3).trim());
        const data = lines.filter((line) => line.startsWith("data:"))
          .map((line) => line.slice(5).trimStart()).join("\n");
        if (event === "done") {
          return;
        }
        if (event === "message" && data && Number.isFinite(id)) {
          onMessage(JSON.parse(data), id);
        }
      }
      if (done) {
        throw new Error("进度连接已断开");
      }
    }
  } finally {
    await reader.cancel().catch(() => {});
    reader.releaseLock();
  }
}
