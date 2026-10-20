"use strict";

/** 只截取真实浏览器页面，不生成终端外观、不伪造 API 响应、不注入对话文本。 */
const { createRequire } = require("node:module");
const fs = require("node:fs/promises");
const path = require("node:path");
const crypto = require("node:crypto");
const requireRuntime = createRequire(process.env.CODEX_NODE_PACKAGES + "/package.json");
const { chromium } = requireRuntime("playwright-core");
const base = "http://127.0.0.1:5173";
const evidence = [];

async function capture(page, hw, name, options = {}) {
  const file = path.join(process.cwd(), `docs/assignments/hw${hw}/screenshots/${name}.png`);
  await page.screenshot({ path: file, ...options });
  const bytes = await fs.readFile(file);
  evidence.push({
    file: path.relative(process.cwd(), file), url: page.url(),
    capturedAt: new Date().toISOString(), sha256: crypto.createHash("sha256").update(bytes).digest("hex")
  });
  await fs.writeFile("docs/assignments/browser-captures.json", JSON.stringify({ captureMethod: "Playwright Chromium page.screenshot", processing: "none", screenshots: evidence }, null, 2));
  console.log("原始浏览器截图：", file);
}

async function captureSwagger(page, block, name) {
  await page.setViewportSize({ width: 1280, height: 1800 });
  await block.getByText("Response headers", { exact: true }).waitFor();
  await block.locator(".responses-inner").scrollIntoViewIfNeeded();
  await page.waitForTimeout(350);
  const start = await block.locator(".curl-command").boundingBox();
  const end = await block.locator(".live-responses-table").boundingBox();
  const height = end.y + end.height - start.y + 12;
  if (start.y < 0 || start.y + height > 1800) throw new Error("实际响应超出截图视口");
  await capture(page, 4, name, {
    clip: { x: start.x, y: start.y, width: start.width, height }
  });
}

async function main() {
  const browser = await chromium.launch({ executablePath: process.env.BOOKSTORE_CHROMIUM, headless: true, chromiumSandbox: true });
  try {
    const context = await browser.newContext();
    const page = await context.newPage();
    page.on("pageerror", (error) => console.log("PAGE_ERROR", error.message));
    await page.goto(base + "/login", { waitUntil: "domcontentloaded" });
    await page.locator("#username").fill("admin");
    await page.locator("#password").fill("admin123");
    await page.locator("button[type='submit']").first().click();
    await page.waitForURL("**/books");
    await page.getByText("微服务设计", { exact: false }).first().waitFor();
    await capture(page, 4, "integrated-bookstore", { fullPage: true });

    // 页面读取真实模型 API 已保存的两轮对话，截图保留模型、时间和每轮输入。
    await page.goto(base + "/contract", { waitUntil: "domcontentloaded" });
    await page.getByText("契约校验通过", { exact: true }).waitFor();
    await page.getByText("User Prompt", { exact: true }).first().waitFor();
    await capture(page, 1, "contract-conversation", { fullPage: true });

    const login = await context.request.post("http://127.0.0.1:8080/api/v1/users/login", { data: { username: "admin", password: "admin123" } });
    const jwt = (await login.json()).accessToken;
    const auth = { Authorization: "Bearer " + jwt };
    const originalResponse = await context.request.get("http://127.0.0.1:8080/api/v1/books/4", { headers: auth });
    const original = (await originalResponse.json()).stockQty;
    try {
      await context.request.patch("http://127.0.0.1:8080/api/v1/books/4/stock", { headers: auth, data: { stockQty: 37 } });
      await page.goto(base + "/assistant", { waitUntil: "domcontentloaded" });
      await page.locator(".assistant__composer textarea").fill("帮我查一下 ISBN为978-3-00-000000-4 的书还有多少本，顺便看看别家卖多少钱。");
      const responsePromise = page.waitForResponse((response) => response.url().includes("/api/assistant/chat") && response.request().method() === "POST", { timeout: 150000 });
      await page.locator(".assistant__composer textarea").press("Enter");
      const response = await responsePromise;
      const result = await response.json();
      if (response.status() !== 200 || !result.toolCalls.some((call) => call.name === "check_inventory" && call.result.stockQty === 37)) {
        throw new Error("前端库存对话未读取实际库存37");
      }
      await page.getByText("check_inventory", { exact: true }).first().waitFor();
      await capture(page, 2, "inventory-function-calling", { fullPage: true });
      await page.locator(".assistant-msg__text").last().scrollIntoViewIfNeeded();
      await capture(page, 2, "inventory-reply", { fullPage: true });
    } finally {
      await context.request.patch("http://127.0.0.1:8080/api/v1/books/4/stock", { headers: auth, data: { stockQty: original } });
    }
    // 同一前端页面继续验证超时后的模型自纠错。
    await page.locator(".assistant__composer textarea").fill("ISBN为978-7-00-000000-8 的书还有几本？比较一下其他平台价格，如果超时请按提示重试。");
    const correctionPromise = page.waitForResponse((response) => response.url().includes("/api/assistant/chat") && response.request().method() === "POST", { timeout: 150000 });
    await page.locator(".assistant__composer textarea").press("Enter");
    const correction = await (await correctionPromise).json();
    if (!correction.toolCalls.some((call) => call.result.error?.code === "UPSTREAM_TIMEOUT")) {
      throw new Error("本次未触发指定的课程模拟超时");
    }
    await page.getByText(/UPSTREAM_TIMEOUT/).first().waitFor();
    await page.getByText(/UPSTREAM_TIMEOUT/).first().scrollIntoViewIfNeeded();
    await capture(page, 2, "timeout-self-correction", { fullPage: true });

    await page.goto(base + "/guide", { waitUntil: "domcontentloaded" });
    await page.locator(".guide__composer textarea").fill("我想买一本关于微服务的书，另外如果我买了不喜欢，拆了塑封还能退吗？");
    const guidePromise = page.waitForResponse((response) => response.url().includes("/api/guide/chat") && response.request().method() === "POST", { timeout: 150000 });
    await page.locator(".guide__composer textarea").press("Enter");
    const guide = await (await guidePromise).json();
    if (guide.stoppedReason !== "completed" || guide.steps[0].action !== "search_book_catalog") {
      throw new Error("导购前端未完成指定 ReAct 链路");
    }
    await page.getByText("query_store_policy", { exact: true }).first().waitFor();
    await capture(page, 3, "react-bookstore", { fullPage: true });
    await page.getByText("query_store_policy", { exact: true }).first().scrollIntoViewIfNeeded();
    await capture(page, 3, "react-policy", { fullPage: true });
    await page.locator(".guide-msg__text").last().scrollIntoViewIfNeeded();
    await capture(page, 3, "react-reply", { fullPage: true });

    const swagger = await context.newPage();
    await swagger.goto("http://127.0.0.1:8080/swagger-ui/index.html", { waitUntil: "domcontentloaded" });
    const detail = swagger.locator(".opblock-get").filter({ has: swagger.getByRole("link", { name: "/api/v1/books/{id}", exact: true }) });
    await detail.locator(".opblock-summary").click();
    await detail.getByRole("button", { name: "Try it out", exact: true }).click();
    await detail.locator("input").first().fill("1");
    await detail.getByRole("button", { name: "Execute", exact: true }).click();
    await detail.locator(".live-responses-table .response-col_status").filter({ hasText: "401" }).waitFor();
    await captureSwagger(swagger, detail, "jwt-401");
    await swagger.getByRole("button", { name: "Authorize", exact: true }).click();
    await swagger.locator("#auth-bearer-value").fill(jwt);
    await swagger.getByRole("button", { name: "Apply credentials", exact: true }).click();
    await swagger.getByRole("button", { name: "Close", exact: true }).click();
    await detail.getByRole("button", { name: "Execute", exact: true }).click();
    await detail.locator(".live-responses-table .response-col_status").filter({ hasText: "200" }).waitFor();
    await captureSwagger(swagger, detail, "jwt-200");
    const runtime = swagger.locator(".opblock-get").filter({ has: swagger.getByRole("link", { name: "/api/v1/runtime", exact: true }) });
    await runtime.locator(".opblock-summary").click();
    await runtime.getByRole("button", { name: "Try it out", exact: true }).click();
    await runtime.getByRole("button", { name: "Execute", exact: true }).click();
    await runtime.locator(".live-responses-table").filter({ hasText: "requestThreadVirtual" }).waitFor();
    await captureSwagger(swagger, runtime, "virtual-thread-runtime");
    await fs.writeFile("docs/assignments/browser-captures.json", JSON.stringify({ captureMethod: "Playwright Chromium page.screenshot", processing: "none", screenshots: evidence }, null, 2));
    console.log("真实页面测试与全部原始截图已完成。");
  } finally {
    await browser.close();
  }
}
main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
