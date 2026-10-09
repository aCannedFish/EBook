# 作业1 · E-BookStore 图书管理 OpenAPI 3.0 接口文档

用 System Prompt + 多轮 User Prompt 驱动大模型产出符合 OpenAPI (Swagger) 规范的 JSON 接口文档。

## 提交物

| 文件 | 说明 |
|---|---|
| `524031910113-作业1.zip` | **提交压缩包**：作业文档 + 最终 JSON 规范文件 |
| `524031910113-作业1.docx` | 主提交文档，正文写在课程作业模版里：完整 Prompt 与多轮对话、最终 OpenAPI 3.0 规范 |
| `openapi.json` | 最终生成的 OpenAPI 3.0.3 规范文件 |
| `template.docx` | 课程下发的作业模版，生成文档时作为版式基准 |
| `prompts.md` | Prompt 与多轮对话全文（由 `dialog/turns.json` 生成，便于复制粘贴） |
| `dialog/turns.json` | 多轮对话记录，文档正文的唯一数据源 |
| `scripts/` | 规范校验、Prompt 导出、文档生成脚本 |

## 覆核方式

```bash
cd 作业1

# 1. 校验规范：结构 + $ref 解析 + 28 处示例与 schema 一致性 + 输出确定性
python3 scripts/validate_openapi.py

# 2. 导出 Prompt 全文到 prompts.md
python3 scripts/build_prompts.py

# 3. 生成提交文档与压缩包
python3 scripts/build_docx.py
```

`build_docx.py` 先用 `pandoc --reference-doc=template.docx` 把正文套进课程模板的样式，
再把模板自带的表头（日期 / 课程名 — 作业X / 学号 姓名 得分 / 本次作业回答如下：）填好插到最前面，
最后打成 `524031910113-作业1.zip`（文档 + `openapi.json`）。

文档正文全部由 `dialog/turns.json` 与 `openapi.json` 现场生成，不存在文档与产物脱节的可能。

## 接口一览

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/books` | 书目列表：page、size、category、keyword、sort、order |
| POST | `/api/v1/books` | 添加新书，管理员通过 `operatorId` 查询参数鉴权 |
| GET | `/api/v1/books/{bookId}` | 单本书详情 |
| PATCH | `/api/v1/books/{bookId}/stock` | 更新库存，支持 SET / INCREASE / DECREASE |

12 处非 2xx 响应统一引用 `components.schemas.ApiError`（`code` / `message` / `path` / `timestamp` / `details`）。

## 依赖

- `pandoc`（Markdown → docx）
- `python3` + `jsonschema`
