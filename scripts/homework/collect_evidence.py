"""采集合并后单一客服助手的真实 API 证据，只使用课程模拟书目与政策。"""

from __future__ import annotations

import json
from pathlib import Path
import urllib.error
import urllib.request
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs/assignments"
SEED_ISBNS = {
    "9780000000001", "9781000000002", "9782000000003", "9783000000004",
    "9784000000005", "9785000000006", "9786000000007", "9787000000008",
    "9787111600001", "9787115400002",
}


def request(method: str, base: str, path: str, body=None, token: str | None = None):
    """保留实际响应，证据仅标明是否携带身份，不持久化 JWT。"""
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    call = urllib.request.Request(
        base + quote(path, safe="/?=&:%"), data=None if body is None else json.dumps(body).encode(),
        headers=headers, method=method,
    )
    try:
        response = urllib.request.urlopen(call, timeout=240)
    except urllib.error.HTTPError as error:
        response = error
    raw = response.read().decode("utf-8")
    result = {
        "method": method, "path": path, "authorizationPresent": bool(token),
        "status": response.code, "headers": dict(response.headers),
        "body": json.loads(raw) if raw else None,
    }
    print(f"{method} {path}: {response.code}", flush=True)
    return result


def save(hw: int, name: str, payload) -> None:
    path = DOCS / f"hw{hw}" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    """先核对演示数据边界，再联调库存、超时纠错和语义政策检索。"""
    store, ai = "http://127.0.0.1:8080", "http://127.0.0.1:8000"
    admin_login = request("POST", store, "/api/v1/users/login", {"username": "admin", "password": "admin123"})
    user_login = request("POST", store, "/api/v1/users/login", {"username": "DefaultUser", "password": "123456"})
    assert admin_login["status"] == user_login["status"] == 200
    admin, reader = admin_login["body"]["accessToken"], user_login["body"]["accessToken"]
    books = request("GET", store, "/api/v1/books?size=100", token=reader)["body"]["items"]
    # 允许原始演示书目以及项目中已登记的新增课程书目，仍拒绝未登记的数据。
    imported = json.loads((ROOT / "scripts/book_import/books.json").read_text(encoding="utf-8"))
    course_isbns = SEED_ISBNS | {book["isbn"].replace("-", "") for book in imported}
    current_isbns = {book["isbn"].replace("-", "") for book in books}
    assert SEED_ISBNS <= current_isbns <= course_isbns
    assert "虚构" in (ROOT / "python-assistant/data/policy.txt").read_text()
    auth = [request("GET", store, "/api/v1/books/1"),
            request("GET", store, "/api/v1/books/1", token="bad-token"),
            request("GET", store, "/api/v1/books/1", token=reader),
            request("GET", store, "/api/v1/cart/1", token=reader),
            request("GET", store, "/api/v1/runtime")]
    assert [item["status"] for item in auth] == [401, 401, 200, 403, 200]
    assert auth[-1]["body"]["requestThreadVirtual"]
    assert auth[-1]["body"]["javaVersion"].startswith("21.")
    assert not any(key.lower() == "set-cookie" for key in admin_login["headers"])
    save(4, "http-evidence.json", auth)
    catalog = [request("GET", store, "/api/v1/books?page=0&size=2", token=reader),
               request("GET", store, "/api/v1/books?category=算法", token=reader)]
    assert len(catalog[0]["body"]["items"]) == 2
    assert len(catalog[1]["body"]["items"]) == 1
    save(1, "runtime-evidence.json", catalog)

    original = request("GET", store, "/api/v1/books/4", token=reader)["body"]["stockQty"]
    try:
        assert request("PATCH", store, "/api/v1/books/4/stock", {"stockQty": 37}, admin)["status"] == 200
        stock = request("POST", ai, "/api/assistant/chat", {
            "message": "帮我查一下 ISBN为978-3-00-000000-4 的书还有多少本，顺便看看别家卖多少钱。"
        }, reader)
        assert stock["status"] == 200, stock
        assert stock["body"]["modelMode"].startswith("remote:")
        steps = stock["body"]["steps"]
        assert {step["action"] for step in steps} >= {"check_inventory", "get_competitor_price"}
        inventory = next(step for step in steps if step["action"] == "check_inventory" and step["ok"])
        assert inventory["result"]["stockQty"] == 37
        save(2, "inventory-live.json", stock)
    finally:
        request("PATCH", store, "/api/v1/books/4/stock", {"stockQty": original}, admin)
    correction = request("POST", ai, "/api/assistant/chat", {
        "message": "ISBN为978-7-00-000000-8 的书还有几本？请比较其他平台价格，如果查询超时，请按工具提示重试一次。"
    }, reader)
    assert correction["status"] == 200, correction
    price_steps = [step for step in correction["body"]["steps"] if step["action"] == "get_competitor_price"]
    assert len(price_steps) >= 2 and not price_steps[0]["ok"] and price_steps[-1]["ok"]
    save(2, "self-correction.json", correction)
    invalid = request("POST", ai, "/api/assistant/chat", {"message": "ISBN为12345的书还有多少本"}, reader)
    assert invalid["status"] == 200, invalid
    assert any(
        step["result"].get("error", {}).get("code") == "INVALID_ISBN_FORMAT"
        for step in invalid["body"]["steps"]
    ), invalid
    save(2, "invalid-isbn.json", invalid)
    schemas = request("GET", ai, "/api/assistant/tools", token=reader)
    names = [item["function"]["name"] for item in schemas["body"]["tools"]]
    assert names == ["check_inventory", "get_competitor_price", "search_book_catalog", "query_store_policy"]
    save(2, "tool-schemas.json", schemas)
    assistant = request("POST", ai, "/api/assistant/chat", {
        "message": "我想买一本关于微服务的书，另外如果我买了不喜欢，拆了塑封还能退吗？"
    }, reader)
    assert assistant["status"] == 200, assistant
    assert assistant["body"]["stoppedReason"] == "completed"
    steps = assistant["body"]["steps"]
    assert steps[0]["action"] == "search_book_catalog"
    assert steps[0]["result"]["source"] == "bookstore-api"
    assert any(step["action"] == "query_store_policy" and step["ok"] for step in steps)
    assert all(step["thought"] and step["observation"] for step in steps)
    save(3, "react-case.json", assistant)
    print("同一客服助手中的 Function Calling、政策 RAG 和 Thought → Action → Observation 过程已采集。", flush=True)


if __name__ == "__main__":
    main()
