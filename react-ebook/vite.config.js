import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8080",
        changeOrigin: true
      },
      // 客服助手是独立的 Python 服务。开发时走这里的代理转发，
      // 前端就用同源请求，不必依赖后端的 CORS 配置。
      "/assistant-api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/assistant-api/, "")
      },
      // 导购助手（作业3，RAG + ReAct）是另一个 Python 服务，默认在 8010，
      // 这样两个助手可以同时启动、同页演示。
      "/guide-api": {
        target: "http://localhost:8010",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/guide-api/, "")
      }
    }
  }
});

