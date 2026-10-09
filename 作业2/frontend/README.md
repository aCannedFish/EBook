# 前端：客服助手对话界面

这三个文件来自电子书城前端工程 `react-ebook/`，由 `scripts/export_sources.sh` 自动导出，
与主仓库里的版本保持一致。

| 文件 | 对应工程路径 | 说明 |
|---|---|---|
| `AssistantPage.jsx` | `react-ebook/src/pages/AssistantPage.jsx` | 对话界面，含函数调用卡片 |
| `assistantApi.js` | `react-ebook/src/api/assistantApi.js` | 助手后端请求封装 |
| `AssistantPage.css` | `react-ebook/src/pages/AssistantPage.css` | 界面样式 |
| `integration.patch` | — | 对 `App.jsx` / `DashboardLayout.jsx` / `appStore.js` / `vite.config.js` / `package.json` 的改动 |

## 接入方式

```bash
cd react-ebook
cp ../作业2/frontend/AssistantPage.jsx  src/pages/
cp ../作业2/frontend/AssistantPage.css  src/pages/
cp ../作业2/frontend/assistantApi.js    src/api/
git apply ../作业2/frontend/integration.patch
```

补丁包含五处改动：

1. `App.jsx`：注册 `/assistant` 路由，带 `loader`（读助手服务状态）与 `handle.searchPlaceholder`
   （复用站内顶栏搜索，用于过滤对话内容）。
2. `DashboardLayout.jsx`：顾客与管理员菜单各加一项「客服助手」。
3. `appStore.js`：`searchByPage` 增加 `assistant` 槽位。
4. `vite.config.js`：加 `/assistant-api` 代理，把请求转发到助手后端 `127.0.0.1:8000`。
   开发时前端发的是同源请求，不必依赖助手服务的 CORS 配置。
5. `package.json`：新增 `react-markdown` 与 `remark-gfm` 两个依赖，用于渲染模型输出的 Markdown。

## 界面行为

- 开发时助手后端地址默认走 Vite 代理的同源路径 `/assistant-api`；
  生产构建下默认 `http://localhost:8000`，都可用 `VITE_ASSISTANT_API_BASE_URL` 覆盖。
- 每次问答把之前的用户与助手文本作为 `history` 一并提交，服务端据此维持多轮上下文。
- 模型返回的每一次 `tool_calls` 都渲染成一张卡片：函数名、参数、成功/失败、耗时、
  可展开的完整返回值；失败时额外显示回传给模型的纠错提示。
- **助手回复按 Markdown 渲染**（`react-markdown` + `remark-gfm`）：标题、列表、加粗、
  行内代码、代码块、引用、表格都正常显示；表格在气泡内横向滚动，不会撑破布局。
  用户自己输入的是纯文本，按段落显示，不被当成 Markdown 语法解析。
- 渲染不启用 `rehype-raw`，原始 HTML 只会被转义成文本 —— 模型输出里的
  `<script>`、`<img onerror>` 不会变成真实节点。外链统一加 `target="_blank"` 与 `rel="noopener noreferrer"`。
- 助手服务未启动时页面降级为一条提示，不会把整个路由打进错误边界。
