# 作业2 · 电子书城客服 AI 助手（Function Calling）

客服助手通过大模型的 Function Calling 调用两个本地 Skill，回答顾客关于库存与竞品价格的问题：

| Skill | 作用 |
|---|---|
| `check_inventory(isbn)` | 查询书店实时库存与售价 |
| `get_competitor_price(isbn)` | 查询竞品（模拟）价格 |

完整链路：用户提问 → 模型返回 `tool_calls` → **拦截并打印函数名与参数** → 本地模拟执行 →
结果以 `role: "tool"` 回填上下文 → 模型生成自然语言回复 → 前端展示。

## 目录

```text
作业2/
├── backend/                  # Python 服务（从主仓库 python-assistant/backend 导出）
│   ├── tools.py              # 两个 Skill 的 Schema、实现与统一派发
│   ├── catalog.py            # 库存数据源（内置模拟目录 / 真实后端）
│   ├── llm.py                # 模型客户端 + 离线替身模型
│   ├── agent.py              # Function Calling 循环与异常处理
│   ├── server.py             # FastAPI 接口
│   ├── cli.py                # 命令行入口与五个演示场景
│   ├── config.py             # 环境变量配置
│   └── tests/                # 62 个单元测试
├── frontend/                 # 接入电子书城前端的助手界面
│   ├── AssistantPage.jsx
│   ├── assistantApi.js
│   ├── AssistantPage.css
│   └── integration.patch     # 对 App.jsx / DashboardLayout.jsx / appStore.js 的改动
├── scripts/                  # 源码导出、截图与日志采集
└── docs/                     # 截图、日志、演示链路、文档中间稿
```

本作业的代码已经并入主仓库，日常开发在主仓库里跑：

| 内容 | 主仓库位置 |
|---|---|
| 助手后端 | `python-assistant/backend/` |
| 前端助手界面 | `react-ebook/src/pages/AssistantPage.jsx` 等 |

`作业2/backend/` 与 `作业2/frontend/` 是由 `scripts/export_sources.sh` 从主仓库导出的副本，
只为了让本作业的压缩包自包含、可独立运行。改代码请改主仓库，然后重跑导出脚本。

按要求没有打包整个工程：`frontend/integration.patch` 只包含接入所必需的改动，
第三方依赖（Jar 包 / node_modules）一律不在提交范围内。

## 启动

依赖已在主仓库里配好，三个进程各开一个终端。**只演示客服助手的话，第 3 个不是必需的**：
助手页面自己用 localStorage 判断登录态，库存来自助手后端的模拟目录，
不读 MySQL 也不调 Spring Boot。

主仓库根目录有一键脚本，会同时起两个后端：

```bash
./run-all.sh --with-frontend   # 书城后端 + 客服助手 + 前端
./stop-all.sh --with-frontend  # 停止
```

分开手动启动：

```bash
# 1. 助手后端 —— 127.0.0.1:8000
cd python-assistant && ./run-local.sh
```

```bash
# 2. 前端 —— localhost:5173
cd react-ebook && npm install && npm run dev
```

```bash
# 3.（可选）书城业务后端 —— 8080 + Docker MySQL 3307
cd springboot-ebook && ./run-local.sh
```

浏览器打开 http://localhost:5173 ，登录（`DefaultUser` / `123456`）后点左侧「客服助手」。

前端通过 Vite 代理的同源路径 `/assistant-api` 访问助手服务（见 `react-ebook/vite.config.js`），
所以开发时不涉及跨域。要直连别的地址就设 `VITE_ASSISTANT_API_BASE_URL`。

> 走代理就没有跨域问题。若绕过代理直连 `http://localhost:8000`，服务端也配了白名单：
> `localhost` / `127.0.0.1` / `[::1]` × `5173` / `4173` 六种来源都放行
> （Vite 只监听 `localhost` 时在 macOS 上可能只绑到 IPv6 的 `::1`，浏览器发的
> `Origin` 就是 `http://[::1]:5173`，漏掉它会拿到 400）。

### 只想命令行看效果

```bash
cd python-assistant      # 或 cd 作业2，导出的副本同样能跑
python -m backend.cli --offline --demo      # 五个场景，不联网
python -m backend.cli "ISBN为978-3-00-000000-4 的书还有多少本？"
```

## 接入真实模型

配置写在 `python-assistant/.env`（主仓库）或本目录的 `.env`（导出的副本同样会读）：

```bash
cp .env.example .env     # 填 LLM_BASE_URL / LLM_MODEL / LLM_API_KEY
```

任何 OpenAI 兼容接口都能用，`.env.example` 里给了 OpenAI / DeepSeek / 通义千问三家的现成写法。
环境变量优先于 `.env`，临时换模型不必改文件：

```bash
LLM_MODEL=deepseek-chat python -m backend.cli   # 或 ./run-local.sh 起 HTTP 服务
```

不设 `LLM_API_KEY` 时自动使用内置的离线替身模型 `LocalRuleBasedLLM`。

## 测试

```bash
cd 作业2
python -m pytest backend/tests -q
```

## 设计要点

**为什么要有离线替身模型。** 真实模型的调用结果不可复现，测试也不能依赖网络。
`LocalRuleBasedLLM` 用固定规则模拟一次真实的 Function Calling 决策（判断该调哪些函数、
遇到可重试错误就重试、信息够了就总结），因此整条链路在没有 API Key 的环境下也能演示和被测试覆盖。
它只替换「模型」这一层，工具执行、上下文回填、异常处理走的都是正式代码路径。

**为什么工具层不抛异常。** 异常栈对模型没有意义，`error.hint` 才有。
`ToolRegistry.dispatch` 把所有失败收敛成 `{"ok": false, "error": {code, message, retryable, hint}}`，
模型据此决定「原样重试」还是「换策略 / 如实告知用户」——这就是 Self-Correction 的全部输入。

**为什么加刹车。** 模型的工具调用可能陷入循环。连续失败上限（默认 3 次）与往返轮次上限（默认 6 轮）
保证最坏情况下也只会返回一句可解释的话，而不是让请求挂死。

## 环境变量

| 变量 | 默认值 | 说明 |
|---|---|---|
| `LLM_BASE_URL` | `https://api.openai.com/v1` | 任意 OpenAI 兼容接口 |
| `LLM_API_KEY` | 空 | 留空则使用离线替身模型 |
| `LLM_MODEL` | `gpt-4o-mini` | 模型名 |
| `LLM_TIMEOUT_SECONDS` | `30` | 模型请求超时 |
| `BOOKSTORE_API_BASE` | 空 | 设置后 `check_inventory` 改读电子书城真实后端 `GET /api/v1/books` |
| `COMPETITOR_LATENCY_SECONDS` | `0.4` | 模拟比价接口耗时 |
| `COMPETITOR_TIMEOUT_SECONDS` | `1.0` | 比价接口超时阈值 |
| `AGENT_MAX_TOOL_ROUNDS` | `6` | 单轮提问内最大往返次数 |
| `AGENT_MAX_TOOL_ERRORS` | `3` | 连续工具失败上限 |
| `ASSISTANT_ALLOWED_ORIGINS` | 见上「关于跨域」 | 覆盖 CORS 白名单，逗号分隔 |

## 重新生成提交物

```bash
bash scripts/collect_logs.sh        # 采集真实的测试 / 演示 / 服务端日志
python3 scripts/capture_terminal.py # 渲染终端截图
python3 scripts/capture_ui.py       # 驱动浏览器截取真实界面（需前后端都在运行）
bash scripts/export_sources.sh      # 从主仓库导出后端与前端源码
python3 scripts/build_docx.py       # 生成 524031910113-作业2.docx 与 524031910113-作业2.zip
```

`build_docx.py` 先用 `pandoc --reference-doc=template.docx` 把正文套进课程模板的样式，
再把模板自带的表头（日期 / 课程名 — 作业X / 学号 姓名 得分 / 本次作业回答如下：）填好插到最前面。
压缩包只收自己编写的源码、脚本和文档：`backend/`、`frontend/`、`scripts/`、`docs/`、
`README.md`、`requirements.txt`，外加课程模板；不含整个工程，不含第三方依赖，也不含 Jar 包。
