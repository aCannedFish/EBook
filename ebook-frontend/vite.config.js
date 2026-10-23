import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8080",
        changeOrigin: true
      },
      // 客服助手由 Python Agent 提供。开发时走这里的代理转发，
      // 前端就用同源请求，不必依赖后端的 CORS 配置。
      "/assistant-api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/assistant-api/, "")
      }
    }
  }
});

