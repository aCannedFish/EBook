#!/usr/bin/env python3
"""对电子书城前端的客服助手页面做真实截图。

不是把对话记录画成图片，而是真的把前端跑起来、真的点「示例问题」按钮、
真的让后端的 Function Calling 跑一遍，然后把浏览器里的画面截下来。
所以这些截图本身就是「前端确实接通了」的证据。

前置条件（脚本会自己检查）：
    - 助手后端：cd python-assistant && ./run-local.sh    （127.0.0.1:8000）
    - 前端开发服务器：cd react-ebook && npm run dev       （localhost:5173）
    - 本机装有 Chrome 或 Edge

用法：
    python3 scripts/capture_ui.py
"""

from __future__ import annotations

import base64
import json
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

import websocket  # 来自 websocket-client

ROOT = Path(__file__).resolve().parent.parent
SHOTS = ROOT / "docs" / "screenshots"

# Vite 默认只监听 localhost，在 macOS 上可能只绑到 IPv6 的 ::1；
# 这里两个都试，谁的地址能通就用谁，免得非要多带一个 --host 参数才能跑本脚本。
FRONTEND_CANDIDATES = ("http://127.0.0.1:5173", "http://[::1]:5173")
ASSISTANT_URL = "http://127.0.0.1:8000"
DEBUG_PORT = 9333

BROWSERS = [
    Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
    Path("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"),
]

#: 要截取的场景：(文件名, 描述, 示例问题按钮的序号，从 0 开始)
SCENARIOS = [
    ("ui-01-normal.png", "正常链路：库存 + 比价", 0),
    ("ui-02-self-correction.png", "非法 ISBN：模型改为向用户确认", 1),
    ("ui-03-retry.png", "上游超时：重试后成功", 2),
    ("ui-04-no-isbn.png", "信息不足：先索要 ISBN", 3),
]

VIEWPORT = {"width": 1440, "height": 1100}
DEVICE_SCALE = 2


def find_browser() -> Path:
    for candidate in BROWSERS:
        if candidate.exists():
            return candidate
    found = shutil.which("google-chrome") or shutil.which("chromium")
    if found:
        return Path(found)
    raise SystemExit("找不到 Chrome / Edge，无法截图")


#: urllib 在 macOS 上会读取系统代理设置，本机开发端口不该走代理，
#: 否则连 http://127.0.0.1:5173 都会被丢给代理，拿到 502。
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def probe(url: str, timeout: float = 3.0):
    """访问本机地址，返回 True/False，不抛异常。"""
    try:
        with OPENER.open(url, timeout=timeout) as response:
            response.read(1)
        return True
    except Exception:  # noqa: BLE001 - 探测失败一律视为「没起来」
        return False


def require(url: str, hint: str) -> None:
    if not probe(url):
        raise SystemExit(f"无法访问 {url}：{hint}")


def resolve_frontend_url() -> str:
    for candidate in FRONTEND_CANDIDATES:
        if probe(candidate):
            return candidate
    raise SystemExit(
        "无法访问前端开发服务器（已尝试 127.0.0.1:5173 与 [::1]:5173）："
        "请先在 react-ebook 目录运行 npm run dev"
    )


class DevTools:
    """极简 CDP 客户端。"""

    def __init__(self, ws_url: str) -> None:
        self._ws = websocket.create_connection(ws_url, timeout=30)
        self._next_id = 0

    def send(self, method: str, **params):
        self._next_id += 1
        message_id = self._next_id
        self._ws.send(json.dumps({"id": message_id, "method": method, "params": params}))
        while True:
            payload = json.loads(self._ws.recv())
            if payload.get("id") == message_id:
                if "error" in payload:
                    raise RuntimeError(f"{method} 失败：{payload['error']}")
                return payload.get("result", {})

    def eval(self, expression: str):
        result = self.send(
            "Runtime.evaluate", expression=expression, returnByValue=True, awaitPromise=True
        )
        return result.get("result", {}).get("value")

    def wait_for(self, expression: str, timeout: float = 20.0, interval: float = 0.2) -> None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.eval(expression):
                return
            time.sleep(interval)
        raise TimeoutError(f"等待超时：{expression}")

    def close(self) -> None:
        self._ws.close()


def wait_for_page(port: int, timeout: float = 20.0) -> str:
    """等浏览器起来并返回第一个 page target 的 WebSocket 地址。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/json", timeout=2) as response:
                targets = json.loads(response.read().decode("utf-8"))
            for target in targets:
                if target.get("type") == "page" and target.get("webSocketDebuggerUrl"):
                    return target["webSocketDebuggerUrl"]
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            pass
        time.sleep(0.3)
    raise SystemExit("等待浏览器调试端口超时")


def capture_panel(devtools: DevTools, out_path: Path) -> None:
    """截取助手面板本身，2 倍像素密度，避免嵌进文档后糊掉。

    对话区平时是固定高度内滚动的，截图前临时放开高度限制，
    让整轮问答一次成像；截完还原，不影响页面本身的行为。
    """
    devtools.eval(
        """(() => {
             const thread = document.querySelector('.assistant__thread');
             thread.dataset.prevMaxHeight = thread.style.maxHeight;
             thread.style.maxHeight = 'none';
             return true;
           })()"""
    )
    rect = devtools.eval(
        """(() => {
             const el = document.querySelector('.assistant__panel');
             const r = el.getBoundingClientRect();
             return {x: r.x, y: r.y, width: r.width, height: r.height};
           })()"""
    )
    result = devtools.send(
        "Page.captureScreenshot",
        format="png",
        captureBeyondViewport=True,
        clip={
            "x": max(rect["x"] - 8, 0),
            "y": max(rect["y"] - 8, 0),
            "width": rect["width"] + 16,
            "height": rect["height"] + 16,
            "scale": 1,
        },
    )
    out_path.write_bytes(base64.b64decode(result["data"]))
    devtools.eval(
        """(() => {
             const thread = document.querySelector('.assistant__thread');
             thread.style.maxHeight = thread.dataset.prevMaxHeight || '';
             return true;
           })()"""
    )


def main() -> int:
    require(
        f"{ASSISTANT_URL}/api/assistant/health",
        "请先在 python-assistant 目录运行 ./run-local.sh 启动助手后端",
    )
    frontend_url = resolve_frontend_url()

    browser = find_browser()
    SHOTS.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as profile:
        process = subprocess.Popen(
            [
                str(browser),
                "--headless=new",
                "--disable-gpu",
                "--hide-scrollbars",
                f"--remote-debugging-port={DEBUG_PORT}",
                # 新版 Chromium 默认拒绝带 Origin 头的 WebSocket 连接，CDP 客户端必须显式放行。
                "--remote-allow-origins=*",
                f"--user-data-dir={profile}",
                "about:blank",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            devtools = DevTools(wait_for_page(DEBUG_PORT))
            devtools.send("Page.enable")
            devtools.send("Runtime.enable")
            devtools.send(
                "Emulation.setDeviceMetricsOverride",
                width=VIEWPORT["width"],
                height=VIEWPORT["height"],
                deviceScaleFactor=DEVICE_SCALE,
                mobile=False,
            )

            # 直接写登录态，跳过登录页 —— 助手页面本身不依赖书城业务后端。
            devtools.send("Page.navigate", url=f"{frontend_url}/login")
            devtools.wait_for("document.readyState === 'complete'")
            devtools.eval(
                """(() => {
                     localStorage.setItem('ebook-auth-username', 'DefaultUser');
                     localStorage.setItem('ebook-auth-user-id', '2');
                     localStorage.setItem('ebook-user-email', 'student@example.com');
                     return true;
                   })()"""
            )
            devtools.send("Page.navigate", url=f"{frontend_url}/assistant")
            devtools.wait_for("!!document.querySelector('.assistant__examples')")
            devtools.wait_for(
                "document.querySelector('.assistant__panel .ant-tag')?.textContent.includes('rule-based')"
            )

            for filename, title, index in SCENARIOS:
                # 每次先清空，保证截图里只有这一个场景。
                devtools.eval(
                    """(() => {
                         const clear = document.querySelector('.assistant__panel .ant-card-extra button');
                         if (!clear.disabled) clear.click();
                         return true;
                       })()"""
                )
                devtools.wait_for("!document.querySelector('.assistant-msg')")

                devtools.eval(
                    f"""(() => {{
                          const buttons = document.querySelectorAll('.assistant__examples .ant-space-item button');
                          buttons[{index}].click();
                          return true;
                        }})()"""
                )
                devtools.wait_for("!document.querySelector('.assistant__pending')", timeout=30)
                devtools.wait_for("!!document.querySelector('.assistant-msg--bot')")

                out_path = SHOTS / filename
                capture_panel(devtools, out_path)
                with out_path.open("rb") as handle:
                    size = len(handle.read())
                print(f"{filename}  {title}  ({size / 1024:.0f} KB)")

            devtools.close()
        finally:
            process.terminate()
            process.wait(timeout=10)

    print(f"\n截图目录：{SHOTS}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
