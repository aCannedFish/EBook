// 导购助手后端（作业3 的 RAG + ReAct 服务，作业3/backend/server.py）的请求封装。
//
// 它与客服助手是两个进程，所以端口也不同：
//   客服助手（python-assistant，Function Calling）  8000
//   导购助手（作业3，RAG + ReAct）                  8010
// 两个服务可以同时跑，页面上也就能同时演示两种 Agent 形态。
//
// 开发时走 Vite 代理的同源路径 /guide-api（见 vite.config.js）；
// 生产构建默认直连本机 8010，部署到别的地址时用 VITE_GUIDE_API_BASE_URL 覆盖。
const GUIDE_BASE_URL =
  import.meta.env.VITE_GUIDE_API_BASE_URL ??
  (import.meta.env.DEV ? "/guide-api" : "http://localhost:8010");

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`${GUIDE_BASE_URL}${path}`, {
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {})
      },
      ...options
    });
  } catch {
    throw new Error(
      `无法连接导购助手服务（${GUIDE_BASE_URL}）。请在作业3 目录用 PORT=8010 ./run-local.sh 启动，` +
        "或在仓库根目录执行 ./run-all.sh --guide。"
    );
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
