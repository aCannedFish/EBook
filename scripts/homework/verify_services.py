"""真实启停回归：清理残留端口、单独重启、释放端口并验证数据库数据保留。

此脚本会重启本项目的 5173/8080/8000 服务，最后保持完整书城运行；
只请求本机健康检查和书目接口，不调用模型、不修改书目。
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
PORTS = (8080, 8000, 5173)
CHECKS = []


def command(*args: str) -> None:
    subprocess.run(list(args), cwd=ROOT, check=True)


def listening(port: int) -> bool:
    result = subprocess.run(["lsof", "-tiTCP:" + str(port), "-sTCP:LISTEN"], capture_output=True)
    return bool(result.stdout.strip())


def request(path: str, body=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    call = urllib.request.Request("http://127.0.0.1:8080" + path,
                                  data=json.dumps(body).encode() if body is not None else None,
                                  headers=headers)
    with urllib.request.urlopen(call, timeout=10) as response:
        return json.load(response)


def catalog():
    """仅比较书目数据，不把登录 Token 写入证据。"""
    token = request("/api/v1/users/login", {"username": "DefaultUser", "password": "123456"})["accessToken"]
    return request("/api/v1/books?size=100", token=token)["items"]


def check_running() -> None:
    assert all(listening(port) for port in PORTS)
    assert request("/api/v1/runtime")["requestThreadVirtual"] is True
    with urllib.request.urlopen("http://127.0.0.1:8000/api/assistant/health", timeout=5) as response:
        tools = json.load(response)["tools"]
        assert tools == ["check_inventory", "get_competitor_price",
                         "search_book_catalog", "query_store_policy"]
    with urllib.request.urlopen("http://127.0.0.1:5173", timeout=5) as response:
        assert response.status == 200


def check_stopped() -> None:
    assert not any(listening(port) for port in PORTS)
    for name in ("backend", "agent", "frontend"):
        assert not (ROOT / ".logs" / f"{name}.json").exists()
    result = subprocess.run(["docker", "inspect", "-f", "{{.State.Running}}", "ebook-mysql-integrated"],
                            text=True, capture_output=True, check=True)
    assert result.stdout.strip() == "false"


def main() -> None:
    """每一步验证外部可见行为，不使用服务管理器内部函数作为测试结论。"""
    before = catalog()
    command("./stop-all.sh")
    check_stopped()
    CHECKS.append({"case": "完整停止释放三个端口并停止本项目MySQL", "passed": True})
    residuals = []
    try:
        for port in PORTS:
            residuals.append(subprocess.Popen([sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"],
                                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                             start_new_session=True))
        time.sleep(0.5)
        assert all(listening(port) for port in PORTS)
        command("./run-all.sh")
        check_running()
        assert all(process.poll() is not None for process in residuals)
        assert catalog() == before
        CHECKS.append({"case": "启动清理三个残留进程并保留数据库书目", "passed": True})
    finally:
        for process in residuals:
            if process.poll() is None:
                process.terminate()
    backend = (ROOT / ".logs/backend.json").read_text()
    agent = (ROOT / ".logs/agent.json").read_text()
    command("./ebook-frontend/run-local.sh")
    check_running()
    assert (ROOT / ".logs/backend.json").read_text() == backend
    assert (ROOT / ".logs/agent.json").read_text() == agent
    CHECKS.append({"case": "组件入口单独重启前端，后端和Agent继续运行", "passed": True})
    command("./ebook-frontend/stop-local.sh")
    assert not listening(5173) and listening(8080) and listening(8000)
    CHECKS.append({"case": "组件停止入口仅释放前端端口", "passed": True})
    command("./stop-all.sh")
    command("./stop-all.sh")
    check_stopped()
    CHECKS.append({"case": "重复完整停止仍正确释放端口", "passed": True})
    command("./run-all.sh")
    check_running()
    assert catalog() == before
    CHECKS.append({"case": "最终完整启动且书目和库存保持不变", "passed": True})
    output = ROOT / "docs/assignments/service-lifecycle.json"
    output.write_text(json.dumps({"checkedAt": datetime.now(timezone.utc).isoformat(),
                                  "checks": CHECKS, "ports": list(PORTS), "finalState": "running"},
                                 ensure_ascii=False, indent=2))
    print("启停回归全部通过，最后保持三个服务运行。", flush=True)


if __name__ == "__main__":
    main()
