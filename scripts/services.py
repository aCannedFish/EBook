#!/usr/bin/env python3
"""管理同一书城的三个服务，清理指定端口并等待真实 HTTP 就绪。

PID 的启动时间用于防止误用过期记录；新进程单独建立进程组，使 npm/Maven
的子进程也能一起退出。端口清理仅作用于调用者明确选择的服务端口。
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent.parent
LOGS = ROOT / ".logs"
SERVICES = {
    "backend": ("书城后端", 8080, "/api/v1/runtime", "ebook-backend/run-local.sh", "bookstore"),
    "agent": ("Agent 服务", 8000, "/api/assistant/health", "ebook-agent/run-local.sh", "ai"),
    "frontend": ("React 前端", 5173, "/", "ebook-frontend/run-local.sh", "frontend"),
}


def run_output(command: list[str]) -> str:
    """读取本机进程信息；不存在的进程或空端口统一返回空字符串。"""
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else ""


def identity(pid: int) -> str:
    return run_output(["ps", "-p", str(pid), "-o", "lstart="])


def listeners(port: int) -> set[int]:
    output = run_output(["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-t"])
    return {int(value) for value in output.split() if value.isdigit()}


def signal_process(pid: int, started: str, sig: signal.Signals, group: bool = False) -> None:
    """只给仍对应同一次启动的进程发信号，忽略正常退出竞态。"""
    if pid <= 1 or pid == os.getpid() or not started or identity(pid) != started:
        return
    try:
        if group and os.getpgid(pid) == pid:
            os.killpg(pid, sig)
        else:
            os.kill(pid, sig)
    except ProcessLookupError:
        pass


def stop_service(name: str) -> None:
    """先退出已记录的整组进程，再清理该服务端口上的旧实例。"""
    label, port, _, _, legacy = SERVICES[name]
    record_path = LOGS / f"{name}.json"
    targets: dict[int, tuple[str, bool]] = {}
    if record_path.exists():
        record = json.loads(record_path.read_text())
        targets[record["pid"]] = (record["started"], True)
    # 兼容本次整合前的 PID 文件，只有工作目录仍属于当前项目才接受记录。
    legacy_path = LOGS / f"integrated-{legacy}.pid"
    if legacy_path.exists():
        pid_text = legacy_path.read_text().strip()
        if pid_text.isdigit():
            pid = int(pid_text)
            cwd = run_output(["lsof", "-a", "-p", str(pid), "-d", "cwd", "-Fn"])
            if any(line.startswith("n" + str(ROOT) + "/") for line in cwd.splitlines()):
                targets.setdefault(pid, (identity(pid), False))
    for pid in listeners(port):
        targets.setdefault(pid, (identity(pid), False))
    for pid, (started, group) in targets.items():
        signal_process(pid, started, signal.SIGTERM, group)
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        if not listeners(port) and all(identity(pid) != item[0] for pid, item in targets.items()):
            break
        time.sleep(0.2)
    for pid, (started, group) in targets.items():
        signal_process(pid, started, signal.SIGKILL, group)
    # 某些旧启动器会在父进程退出期间留下监听子进程，按同一端口再检查一次。
    for pid in listeners(port):
        signal_process(pid, identity(pid), signal.SIGKILL)
    time.sleep(0.1)
    if listeners(port):
        raise RuntimeError(f"{label}端口 {port} 仍被占用，请查看进程权限。")
    record_path.unlink(missing_ok=True)
    legacy_path.unlink(missing_ok=True)
    print(f"{label}已停止，端口 {port} 已释放。", flush=True)


def stop_database() -> None:
    """停止本项目启动的开发数据库，保留容器和持久化数据卷。"""
    marker = LOGS / "mysql-managed.json"
    if not marker.exists() or not shutil.which("docker"):
        return
    record = json.loads(marker.read_text())
    if record == {"project": str(ROOT), "container": "ebook-mysql-integrated"}:
        result = subprocess.run(["docker", "stop", "-t", "10", record["container"]],
                                capture_output=True, text=True, check=False)
        if result.returncode:
            raise RuntimeError("开发数据库未能停止：" + result.stderr.strip())
        print("MySQL 已停止，127.0.0.1:3307；数据卷已保留。", flush=True)


def start_service(name: str) -> None:
    """启动后检查 HTTP 和进程存活，失败时关闭刚启动的实例。"""
    label, port, health, script, legacy = SERVICES[name]
    log_path = LOGS / f"{legacy if name != 'agent' else 'ai'}-server.log"
    with log_path.open("ab") as log:
        log.write(f"\n--- {time.strftime('%Y-%m-%d %H:%M:%S')} 启动 {label} ---\n".encode())
        process = subprocess.Popen(["bash", str(ROOT / script)], cwd=ROOT,
                                   stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                                   start_new_session=True,
                                   env={**os.environ, "EBOOK_SERVICE_CHILD": "1"})
    started = identity(process.pid)
    (LOGS / f"{name}.json").write_text(json.dumps({"pid": process.pid, "started": started}))
    url = f"http://127.0.0.1:{port}"
    deadline = time.monotonic() + 300
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"{label}启动失败，请查看 {log_path}")
        try:
            with urlopen(url + health, timeout=2) as response:
                if response.status == 200:
                    print(f"{label}已就绪：{url}（端口 {port}）", flush=True)
                    return
        except (URLError, TimeoutError):
            pass
        time.sleep(0.5)
    raise RuntimeError(f"{label}等待就绪超时，请查看 {log_path}")


def main() -> int:
    """串行管理生命周期，启动失败时回收此次启动的服务。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["start", "stop", "status"])
    parser.add_argument("services", nargs="*", choices=list(SERVICES))
    args = parser.parse_args()
    selected = [name for name in SERVICES if name in (args.services or SERVICES)]
    LOGS.mkdir(exist_ok=True)
    if not shutil.which("lsof"):
        parser.error("需要 lsof（macOS 自带；Linux 请先安装 lsof）。")
    with (LOGS / "services.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if args.action == "status":
            for name in selected:
                label, port, _, _, _ = SERVICES[name]
                pids = listeners(port)
                print(f"{label}：{'运行中' if pids else '已停止'} http://127.0.0.1:{port}")
            return 0
        if args.action == "stop":
            for name in reversed(selected):
                stop_service(name)
            if "backend" in selected:
                stop_database()
            return 0
        # 开始启动前清理所有选定端口，避免把旧实例的 HTTP 当成新服务已就绪。
        for name in reversed(selected):
            stop_service(name)
        launched = []
        try:
            for name in selected:
                launched.append(name)
                start_service(name)
        except (KeyboardInterrupt, Exception):
            for name in reversed(launched):
                stop_service(name)
            if "backend" in launched:
                stop_database()
            raise
    print("接口文档：http://127.0.0.1:8080/swagger-ui/index.html", flush=True)
    print("日志目录：" + str(LOGS), flush=True)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (RuntimeError, PermissionError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
