# python-assistant · 电子书城客服助手后端

电子书城前端的「客服助手」页面所依赖的 Python 服务。通过大模型的 Function Calling 调用两个本地 Skill：

| Skill | 作用 |
|---|---|
| `check_inventory(isbn)` | 查询书店实时库存与售价 |
| `get_competitor_price(isbn)` | 查询竞品（模拟）价格 |

完整链路：用户提问 → 模型返回 `tool_calls` → 拦截并打印函数名与参数 → 本地执行 →
结果以 `role: "tool"` 回填上下文 → 模型生成自然语言回复。

## 启动

```bash
cd python-assistant
chmod +x run-local.sh stop-local.sh
./run-local.sh
```

首次运行会建 `.venv` 并安装依赖。默认监听 `127.0.0.1:8000`，换端口用 `PORT=8001 ./run-local.sh`。

停止：

```bash
./stop-local.sh
```

**不配置模型 API 也能跑通全流程**：未设置 `LLM_API_KEY` 时使用内置的离线替身模型
`LocalRuleBasedLLM`，它按固定规则模拟一次真实的 Function Calling 决策
（判断该调哪些函数、遇到可重试错误就重试、信息够了就总结）。

## 配置模型 API

配置写在 `python-assistant/.env` 里：

```bash
cd python-assistant
cp .env.example .env
```

打开 `.env` 填三项即可（文件里给了 OpenAI / DeepSeek / 通义千问 / 上海交大模型服务的现成写法，取消注释就行）：

```bash
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
LLM_API_KEY=sk-xxxx
```

**`LLM_BASE_URL` 填到 `/v1` 为止，不要带 `/chat/completions`。** 客户端会自己拼这一段，
多写了会请求到 `.../chat/completions/chat/completions` 而返回 404 NotFoundError。
程序会把误写的后缀自动去掉，但填对更省事。同理，`LLM_MODEL` 必须是该服务商
模型列表里的名字——把 `gpt-4o-mini` 配到只提供 `deepseek-chat` 的地址上同样是 404。

任何 OpenAI 兼容接口都能用，换供应商只改这三行。改完重启 `./run-local.sh`。

进程环境变量优先于 `.env`，所以临时试别的模型不必改文件：

```bash
LLM_MODEL=gpt-4o ./run-local.sh
```

配置项读在 `backend/config.py`，`.env` 的查找位置是 `python-assistant/.env` 与当前工作目录。
完整变量表见文末。

### 报错怎么读

模型接口出错时，回复里会带上排查方向，而不是只有一句 error 类名：

| 状态码 | 常见原因 |
|---|---|
| 404 | `LLM_BASE_URL` 多写了 `/chat/completions`，或 `LLM_MODEL` 不在该服务商的模型列表里 |
| 401 / 403 | `LLM_API_KEY` 无效，或密钥与模型不属于同一个服务商 |
| 429 | 触发限流，稍后重试或换模型 |
| 5xx | 服务商侧故障，不是本地配置问题 |

服务端日志（`.logs/assistant.log`）里会打印完整请求地址。确认配置是否生效可以直接看：

```bash
curl -s http://127.0.0.1:8000/api/assistant/health
# {"status":"ok","modelMode":"remote:deepseek-chat","llmBaseUrl":"https://api.deepseek.com/v1"}
```

`modelMode` 是 `offline:rule-based` 就说明密钥没读到，仍在用离线替身模型。

## 接口

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/assistant/chat` | 一次问答，返回回复与本次触发的全部函数调用 |
| GET | `/api/assistant/tools` | 当前交给大模型的 Tool 列表（排查用） |
| GET | `/api/assistant/health` | 健康检查与当前模型模式 |

前端通过 Vite 代理的同源路径 `/assistant-api` 访问（见 `react-ebook/vite.config.js`），
开发时不依赖 CORS；服务本身也配了回环地址白名单，直连同样可用。

## 命令行

```bash
python -m backend.cli --offline --demo      # 五个场景，不联网
python -m backend.cli "ISBN为978-3-00-000000-4 的书还有多少本？"
python -m backend.cli                       # 交互式对话
```

## 测试

```bash
python -m pytest backend/tests -q
```

## 配置

变量可以写在 `.env` 里，也可以用环境变量给（环境变量优先）。

| 变量 | 默认值 | 说明 |
|---|---|---|
| `LLM_BASE_URL` | `https://api.openai.com/v1` | 任意 OpenAI 兼容接口 |
| `LLM_API_KEY` | 空 | 留空则使用离线替身模型 |
| `LLM_MODEL` | `gpt-4o-mini` | 模型名 |
| `LLM_TIMEOUT_SECONDS` | `30` | 模型请求超时 |
| `LLM_TEMPERATURE` | `0.2` | 采样温度 |
| `BOOKSTORE_API_BASE` | 空 | 设置后 `check_inventory` 改读电子书城真实后端 `GET /api/v1/books`；留空则用内置模拟目录 |
| `COMPETITOR_LATENCY_SECONDS` | `0.4` | 模拟比价接口耗时 |
| `COMPETITOR_TIMEOUT_SECONDS` | `1.0` | 比价接口超时阈值 |
| `AGENT_MAX_TOOL_ROUNDS` | `6` | 单轮提问内最大往返次数 |
| `AGENT_MAX_TOOL_ERRORS` | `3` | 连续工具失败上限 |
| `ASSISTANT_ALLOWED_ORIGINS` | 回环地址 × 5173/4173 | 覆盖 CORS 白名单，逗号分隔 |

## 目录

```text
python-assistant/
├── backend/
│   ├── tools.py      # 两个 Skill 的 Schema、实现与统一派发
│   ├── catalog.py    # 库存数据源（内置模拟目录 / 电子书城真实后端）
│   ├── llm.py        # 模型客户端 + 离线替身模型
│   ├── agent.py      # Function Calling 循环与异常处理
│   ├── server.py     # FastAPI 接口
│   ├── cli.py        # 命令行入口与五个演示场景
│   ├── config.py     # 配置读取（环境变量 + .env）
│   └── tests/        # 单元测试
├── .env.example      # 配置模板，复制成 .env 后填写
├── requirements.txt
├── run-local.sh
└── stop-local.sh
```

设计说明与演示链路的完整记录见 `作业2/README.md`。
