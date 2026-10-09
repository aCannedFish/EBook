// 客服助手后端（python-assistant/ 的 FastAPI 服务）的请求封装。
// 与 backendApi.js 分开，是因为它指向另一个进程：默认 http://localhost:8000，
// 而书城业务后端是 http://localhost:8080。
//
// 开发时默认走 Vite 代理的同源路径 /assistant-api（见 vite.config.js），
// 这样前端是普通同源请求，不依赖助手服务的 CORS 配置。
const ASSISTANT_BASE_URL =
  import.meta.env.VITE_ASSISTANT_API_BASE_URL ??
  (import.meta.env.DEV ? "/assistant-api" : "http://localhost:8000");

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`${ASSISTANT_BASE_URL}${path}`, {
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {})
      },
      ...options
    });
  } catch {
    throw new Error(
      "无法连接客服助手服务。请在 python-assistant 目录执行 ./run-local.sh 启动助手后端（默认 127.0.0.1:8000）。"
    );
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

  return response.json();
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
