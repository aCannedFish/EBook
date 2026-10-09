"""采集本次运行的测试、语义 RAG、ReAct 和独立 HTTP 服务证据。

每条日志来自实际命令输出。服务使用临时端口，不读取其他作业的服务日志；
任一必需验证失败会使脚本退出，避免打包成功掩盖演示失败。
"""

from __future__ import annotations

import json
import math
import os
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
LOGS = DOCS / "logs"
QUESTION = "我想买一本关于微服务的书，另外如果我买了不喜欢，拆了塑封还能退吗？"
sys.path.insert(0, str(ROOT))


def run_command(
    arguments: list[str], log_name: str, environment: dict[str, str]
) -> None:
    """执行命令并保存完整输出；退出码失败时停止采集。"""
    with (LOGS / log_name).open("w", encoding="utf-8") as output:
        subprocess.run(
            [sys.executable, *arguments],
            cwd=ROOT,
            env=environment,
            stdout=output,
            stderr=subprocess.STDOUT,
            check=True,
        )
    print(f"已采集：docs/logs/{log_name}", flush=True)


def collect_http(environment: dict[str, str]) -> None:
    """在独立临时端口启动服务，记录响应与完整执行日志。"""
    import httpx

    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    url = f"http://127.0.0.1:{port}"
    with (LOGS / "server.log").open("w", encoding="utf-8") as output:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "backend.server:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            cwd=ROOT,
            env=environment,
            stdout=output,
            stderr=subprocess.STDOUT,
        )
        try:
            with httpx.Client(base_url=url, timeout=5.0) as client:
                for _ in range(40):
                    if process.poll() is not None:
                        raise RuntimeError(
                            "临时服务启动失败，详见 docs/logs/server.log"
                        )
                    try:
                        health = client.get("/api/guide/health")
                        if health.status_code == 200:
                            break
                    except httpx.RequestError:
                        pass
                    time.sleep(0.25)
                else:
                    raise RuntimeError("临时服务健康检查超时")
                response = client.post(
                    "/api/guide/chat", json={"message": QUESTION}, timeout=120
                )
                response.raise_for_status()
                trace = response.json()
                assert trace["stoppedReason"] == "completed"
                assert [step["action"] for step in trace["steps"]] == [
                    "search_book_catalog",
                    "query_store_policy",
                ]
                search = client.post(
                    "/api/guide/policy/search", json={"question": "拆了塑封还能退吗"}
                )
                search.raise_for_status()
                assert search.json()["passages"][0]["clause"].startswith("第六条")
                (DOCS / "http-evidence.json").write_text(
                    json.dumps(
                        {
                            "health": health.json(),
                            "chat": trace,
                            "policySearch": search.json(),
                        },
                        ensure_ascii=False,
                        indent=2,
                    ),
                    encoding="utf-8",
                )
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
    text = (LOGS / "server.log").read_text(encoding="utf-8")
    assert all(marker in text for marker in ("Thought:", "Action:", "Observation:"))
    print("已采集：HTTP 响应与完整服务日志", flush=True)


def collect_rag() -> None:
    """导出政策分块及实际语义向量，验证向量有效性和关键条款召回。"""
    from backend.rag import RagPipeline

    index = RagPipeline().build(force=True)
    assert index.embedder.name.startswith("sentence-transformers:")
    vectors = index.store.to_dict()["vectors"]
    assert len(vectors) == len(index.chunks)
    assert all(len(vector) == 512 for vector in vectors)
    assert all(all(math.isfinite(value) for value in vector) for vector in vectors)
    assert all(
        abs(sum(value * value for value in vector) - 1) < 0.001 for vector in vectors
    )
    queries = (
        ("拆了塑封还能退吗", "第六条"),
        ("会员已拆封退货权益", "第二十条"),
        ("退货运费谁承担", "第十二条"),
        ("金卡会员有什么折扣", "第十七条"),
    )
    retrievals = []
    for question, expected in queries:
        hits = index.retrieve(question)
        assert hits and any(
            hit.chunk.clause.startswith(expected) for hit in hits
        ), question
        retrievals.append(
            {
                "question": question,
                "expectedClause": expected,
                "passages": [hit.to_dict() for hit in hits],
            }
        )
    (DOCS / "rag-evidence.json").write_text(
        json.dumps(
            {"stats": index.stats(), "retrievals": retrievals},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (DOCS / "policy-vectors.json").write_text(
        json.dumps(index.to_cache(), ensure_ascii=False),
        encoding="utf-8",
    )
    print(
        f"已验证：{len(index.chunks)} 个分块，{index.store.dimensions} 维语义向量",
        flush=True,
    )


def main() -> None:
    """依次生成当前源码的全部提交证据，并记录采集时间与模型模式。"""
    LOGS.mkdir(parents=True, exist_ok=True)
    environment = dict(os.environ)
    environment["EMBEDDING_MODE"] = "local"
    environment["RAG_MIN_SCORE"] = "0.55"
    os.environ.update(environment)
    run_command(["-m", "pytest", "backend/tests", "-q"], "tests.txt", environment)
    collect_rag()
    run_command(
        ["-m", "backend.cli", "--offline", "--demo", "--json", "docs/demo-trace.json"],
        "demo.txt",
        environment,
    )
    run_command(
        ["-m", "backend.cli", "--offline", "--stats"], "rag-stats.txt", environment
    )
    traces = json.loads((DOCS / "demo-trace.json").read_text(encoding="utf-8"))
    assert all(trace["stoppedReason"] == "completed" for trace in traces)
    assert [step["action"] for step in traces[0]["steps"]] == [
        "search_book_catalog",
        "query_store_policy",
    ]
    collect_http(environment)
    remote_path = DOCS / "remote-trace.json"
    remote_path.unlink(missing_ok=True)
    run_command(["scripts/run_remote_demo.py"], "demo-remote.txt", environment)
    status = {
        "collectedAt": datetime.now(timezone(timedelta(hours=8))).isoformat(),
        "embeddingMode": "local-semantic",
        "remoteModelVerified": remote_path.exists(),
        "offlineScenarios": len(traces),
    }
    (DOCS / "evidence-status.json").write_text(
        json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("证据采集完成。", flush=True)


if __name__ == "__main__":
    main()
