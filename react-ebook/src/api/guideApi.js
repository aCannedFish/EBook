import { authHeaders, notifyUnauthorized } from "./auth";

// 导购与库存客服共用 python-assistant，通过当前顾客的 JWT 读取原书城目录。
const GUIDE_BASE_URL =
  import.meta.env.VITE_GUIDE_API_BASE_URL ??
  (import.meta.env.DEV ? "/guide-api" : "http://localhost:8000");

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`${GUIDE_BASE_URL}${path}`, {
      headers: {
        "Content-Type": "application/json",
        ...authHeaders(),
        ...(options.headers || {})
      },
      ...options
    });
  } catch {
    throw new Error(
      `无法连接导购助手服务（${GUIDE_BASE_URL}）。请启动项目的 python-assistant 服务，` +
        "或在仓库根目录执行 ./run-all.sh --guide。"
    );
  }

  if (response.status === 401) {
    notifyUnauthorized();
  }
  if (!response.ok) {
    let message = `导购助手服务返回 ${response.status}`;
    try {
      const body = await response.json();
      if (body?.detail) {
        message = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
      }
    } catch {
      // 非 JSON 错误体，保留默认文案
    }
    throw new Error(message);
  }

  return response.json();
}

/** 一次 ReAct 问答。返回 reply 与完整的 steps（Thought / Action / Observation）。 */
export function sendGuideMessage(message, useRemoteModel = false) {
  return request("/api/guide/chat", {
    method: "POST",
    body: JSON.stringify({ message, useRemoteModel })
  });
}

/** 服务状态：RAG 索引是否就绪、用的是哪个向量化实现、书目规模。 */
export function fetchGuideHealth() {
  return request("/api/guide/health");
}

/** 工具 Schema，界面上展示「Agent 手上有哪两个工具」。 */
export function fetchGuideTools() {
  return request("/api/guide/tools");
}
