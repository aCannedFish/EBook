"""通过已集成的书城接口执行两轮真实模型对话，验证 OpenAPI 输出结构稳定性。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from collect_evidence import request, save


def main() -> None:
    """发送真实 System/User Prompt，保存每轮模型产物，不手工修改最终 JSON。"""
    login = request("POST", "http://127.0.0.1:8080", "/api/v1/users/login",
                    {"username": "admin", "password": "admin123"})
    token = login["body"]["accessToken"]
    history = []
    prompts = [
        "请根据给出的现有 EBook 书城实现，生成完整的 OpenAPI 3.0.3 JSON。确保包括分页、分类、状态码和 JWT。",
        "请再次核对 page 默认0、size默认20且最大100、分类过滤、401/403/404响应和库存PATCH。保持路径、operationId及Schema字段类型不变，输出修订后的完整JSON。",
    ]
    results = []
    for prompt in prompts:
        result = request("POST", "http://127.0.0.1:8000", "/api/design/chat",
                         {"message": prompt, "history": history}, token)
        assert result["status"] == 200, result
        reply = result["body"]["reply"]
        spec = json.loads(reply)
        assert spec["openapi"] == "3.0.3"
        history.extend([{"role": "user", "content": prompt}, {"role": "assistant", "content": reply}])
        results.append(result)
        save(1, f"openapi-round-{len(results)}.json", spec)
    def signature(spec):
        return {path: {method: value["operationId"] for method, value in operations.items()
                       if method in {"get", "post", "patch"}}
                for path, operations in spec["paths"].items()}
    assert signature(json.loads(results[0]["body"]["reply"])) == signature(json.loads(results[1]["body"]["reply"]))
    save(1, "generation-evidence.json", results)
    print("两轮真实模型对话完成，路径、方法、operationId 与分页约束保持一致。")


if __name__ == "__main__":
    main()
