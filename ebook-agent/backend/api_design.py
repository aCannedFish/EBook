"""用真实模型为现有书城生成接口契约，并记录可复核的多轮 Prompt 与响应。"""

from __future__ import annotations

import json
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .config import LLM

OUTPUT = Path(__file__).resolve().parents[2] / "docs/assignments/hw1"
SYSTEM_PROMPT = """你是 E-BookStore 项目的后端 API 架构师，为已经存在的 Spring Boot 书城生成接口契约。
严格输出一个 OpenAPI 3.0.3 JSON 对象。禁止 Markdown 围栏、注释、解释文字、YAML、OpenAPI 3.1。
servers 必须且只能是 [{"url":"http://127.0.0.1:8080"}]，这是正在运行的原书城，禁止使用示例域名。
paths 只包含以下三个资源路径和四种操作，不创建另一个演示项目或虚构接口：
1. GET /api/v1/books：page 为从 0 开始的整数，默认 0，最小 0；size 为整数，默认 20，范围 1~100；
   category 为精确分类过滤；keyword 模糊匹配书名/作者/分类；isbn 可去除连字符后匹配。
   200 返回 {items: Book[], page: integer, size: integer, totalElements: integer, totalPages: integer}。
2. GET /api/v1/books/{id}：id 是 int64 路径参数；200 返回 Book，404 返回 Error。
3. POST /api/v1/books：仅管理员，创建成功返回 201 和 Location 响应头，响应体为 Book。
   请求必填 title/author/publisher/isbn/category/format/description（string）、price（非负 integer，元）、stockQty（非负 integer）；coverUrl 为可选 string。
4. PATCH /api/v1/books/{id}/stock：仅管理员，JSON 请求体 {stockQty: nonnegative integer}，200 返回更新后的 Book。
Book 是现有书城 DTO，字段为 id(int64)、title、author、publisher、isbn、category、format、description、coverUrl(可为空)、
price(integer)、stockQty(integer)、stockType(string)、stockText(string)。不要换成 name/count 或其它字段。
Error 至少包含 message:string；401 表示缺失/无效/过期 Bearer Token，403 表示权限不足，400 表示参数错误，404 表示资源不存在。
在 components.securitySchemes 定义 bearerAuth(type=http,scheme=bearer,bearerFormat=JWT)，全局 security 使用它。
统一用 components.schemas 与 $ref 复用 Book、BookPage、BookInput、StockInput、Error。
operationId 固定为 listBooks、getBook、createBook、updateStock。不能输出 operatorId 参数，管理员身份由 JWT 决定。
Few-Shot 约束示例：若收到 {\"stockQty\":37}，更新库存接口必须将它定义为 integer 且 minimum=0，不能要求重复提交整本书。
稳定性要求：后续修订必须保持这些路径、方法、operationId、字段类型、页码默认值及 $ref 名称不变。"""


def validate_contract(spec: dict) -> dict:
    """验证模型产物是否对应真实实现；失败时保留明确错误，不手工伪造模型输出。"""
    from openapi_spec_validator import validate_spec
    validate_spec(spec)
    assert spec.get("openapi") == "3.0.3", "必须使用 OpenAPI 3.0.3"
    operations = {"/api/v1/books": {"get", "post"}, "/api/v1/books/{id}": {"get"},
                  "/api/v1/books/{id}/stock": {"patch"}}
    assert set(spec["paths"]) == set(operations), "资源路径与书城实现不一致"
    assert spec.get("servers") == [{"url": "http://127.0.0.1:8080"}], "服务器地址必须对应当前书城"
    http_methods = {"get", "post", "put", "patch", "delete", "head", "options", "trace"}
    for path, methods in operations.items():
        assert methods == set(spec["paths"][path]) & http_methods, f"操作与要求不一致：{path}"
        for method in methods:
            assert not any(parameter["name"] == "operatorId"
                           for parameter in spec["paths"][path][method].get("parameters", []))
    parameters = {item["name"]: item for item in spec["paths"]["/api/v1/books"]["get"]["parameters"]}
    assert {"page", "size", "category"} <= set(parameters), "缺少分页或分类参数"
    assert parameters["page"]["schema"]["default"] == 0
    assert parameters["size"]["schema"]["maximum"] == 100
    assert parameters["size"]["schema"]["default"] == 20
    assert spec["components"]["securitySchemes"]["bearerAuth"]["scheme"] == "bearer"
    assert spec["security"], "缺少 Bearer 鉴权声明"
    for path, methods in operations.items():
        for method in methods:
            response = spec["paths"][path][method]["responses"]
            assert "401" in response
            assert ("201" if method == "post" else "200") in response
    schemas = spec["components"]["schemas"]
    assert {"Book", "BookPage", "BookInput", "StockInput", "Error"} <= set(schemas)
    assert schemas["StockInput"]["properties"]["stockQty"]["minimum"] == 0
    assert {"items", "page", "size", "totalElements", "totalPages"} <= set(schemas["BookPage"]["properties"])
    assert schemas["Book"]["properties"]["price"]["type"] == "integer"
    assert "Location" in spec["paths"]["/api/v1/books"]["post"]["responses"]["201"].get("headers", {})
    return {"valid": True, "paths": 3, "operations": 4, "pagination": "page=0,size=20,max=100"}


def generate(message: str, history: list[dict]) -> dict:
    """通过当前项目配置的模型 API 执行真实对话，并保存完整输入和 JSON 输出。"""
    if not LLM.configured:
        raise RuntimeError("作业1接口契约必须使用真实模型，请配置 LLM_API_KEY")
    safe_history = [entry for entry in history[-8:]
                    if entry.get("role") in {"user", "assistant"} and isinstance(entry.get("content"), str)]
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, *safe_history,
                {"role": "user", "content": message}]
    body = {"model": LLM.model, "messages": messages, "temperature": 0,
            "response_format": {"type": "json_object"}}
    request = urllib.request.Request(LLM.endpoint, data=json.dumps(body).encode(),
                                    headers={"Content-Type": "application/json",
                                             "Authorization": f"Bearer {LLM.api_key}"})
    with urllib.request.urlopen(request, timeout=120) as response:
        result = json.loads(response.read())
    content = result["choices"][0]["message"]["content"]
    spec = json.loads(content)
    validation = validate_contract(spec)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    conversation = {"model": LLM.model, "generatedAt": datetime.now(timezone(timedelta(hours=8))).isoformat(),
                    "messages": [*messages, {"role": "assistant", "content": content}],
                    "validation": validation}
    (OUTPUT / "conversation.json").write_text(json.dumps(conversation, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT / "openapi.json").write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"reply": content, "validation": validation, "modelMode": f"remote:{LLM.model}",
            "generatedAt": conversation["generatedAt"], "systemPrompt": SYSTEM_PROMPT}
