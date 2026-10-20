"use strict";

/**
 * 在合并后的单一 /assistant 页面采集作业2、作业3真实对话和截图。
 *
 * 浏览器直接请求本地书城和 Agent。截图不拼接、不重绘；落盘的 API 证据
 * 只包含用户已授权的课程演示书目、模拟竞品报价和课程虚构政策。
 */
const { createRequire } = require("node:module");
const crypto = require("node:crypto");
const fs = require("node:fs/promises");
const path = require("node:path");
const runtime = createRequire(process.env.CODEX_NODE_PACKAGES + "/package.json");
const { chromium } = runtime("playwright-core");

const root = process.cwd();
const front = "http://127.0.0.1:5173";
const ai = "http://127.0.0.1:8000";

async function saveCapture(page, homework, filename) {
  const relativePath = `docs/assignments/hw${homework}/screenshots/${filename}.png`;
  const absolutePath = path.join(root, relativePath);
  await page.screenshot({ path: absolutePath, fullPage: true });

  const bytes = await fs.readFile(absolutePath);
  const manifestPath = path.join(root, "docs/assignments/browser-captures.json");
  const manifest = JSON.parse(await fs.readFile(manifestPath, "utf8"));
  manifest.captureMethod = "Playwright Chromium page.screenshot";
  manifest.processing = "none";
  manifest.screenshots = manifest.screenshots.filter((item) => item.file !== relativePath);
  manifest.screenshots.push({
    file: relativePath,
    url: page.url(),
    capturedAt: new Date().toISOString(),
    sha256: crypto.createHash("sha256").update(bytes).digest("hex")
  });
  await fs.writeFile(manifestPath, JSON.stringify(manifest, null, 2));
  console.log("真实页面截图：", relativePath);
}

function saveResponse(homework, filename, response, body) {
  const evidence = {
    method: response.request().method(),
    path: new URL(response.url()).pathname,
    authorizationPresent: true,
    status: response.status(),
    body
  };
  const target = path.join(root, `docs/assignments/hw${homework}/${filename}.json`);
  return fs.writeFile(target, JSON.stringify(evidence, null, 2));
}

function writeReactTrace(steps) {
  const trace = [];
  for (const step of steps) {
    trace.push(
      `Thought: ${step.thought}`,
      `Action: ${step.action}`,
      `Action Input: ${JSON.stringify(step.arguments)}`,
      `Observation: ${JSON.stringify(step.result, null, 2)}`,
      ""
    );
  }
  return fs.writeFile(
    path.join(root, "docs/assignments/hw3/logs/react-trace.txt"),
    trace.join("\n"),
    "utf8"
  );
}

async function writeAssistantLog(requestId) {
  const logPath = path.join(root, ".logs/ai-server.log");
  const runtimeLog = (await fs.readFile(logPath, "utf8"))
    .split("\n")
    .filter((line) => line.includes(`[${requestId}]`))
    .join("\n");
  if (!runtimeLog.includes("最终答复")) {
    throw new Error("统一 Agent 尚未写入该请求的完整服务端运行日志");
  }
  return fs.writeFile(path.join(root, "docs/assignments/hw3/logs/ai-runtime.log"),
                      runtimeLog + "\n", "utf8");
}

async function ask(page, question) {
  const composer = page.locator(".assistant__composer textarea");
  await composer.fill(question);
  const responsePromise = page.waitForResponse((response) =>
    response.url().endsWith("/api/assistant/chat") && response.request().method() === "POST",
    { timeout: 180000 });
  await composer.press("Enter");
  const response = await responsePromise;
  if (response.status() !== 200) {
    throw new Error(`统一助手返回 HTTP ${response.status()}`);
  }
  const body = await response.json();
  await page.waitForFunction(() => !document.querySelector(".assistant__pending"));
  return { response, body };
}

async function main() {
  const browser = await chromium.launch({
    executablePath: process.env.BOOKSTORE_CHROMIUM,
    headless: true,
    chromiumSandbox: true
  });

  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1100 } });
    page.on("pageerror", (error) => console.error("PAGE_ERROR", error.message));
    await page.goto(front + "/login", { waitUntil: "domcontentloaded" });
    await page.locator("#username").fill("DefaultUser");
    await page.locator("#password").fill("123456");
    await page.locator("button[type='submit']").first().click();
    await page.waitForURL("**/books");
    await page.goto(front + "/assistant", { waitUntil: "domcontentloaded" });
    await page.getByText("客服助手", { exact: true }).first().waitFor();

    const inventory = await ask(
      page,
      "帮我查一下 ISBN为978-3-00-000000-4 的书还有多少本，顺便看看别家卖多少钱。"
    );
    const inventoryNames = inventory.body.steps.map((step) => step.action);
    if (!inventoryNames.includes("check_inventory") || !inventoryNames.includes("get_competitor_price")) {
      throw new Error("统一助手未完成库存和模拟竞品两个 Function Calling 动作");
    }
    await saveResponse(2, "inventory-live", inventory.response, inventory.body);
    await page.getByText("get_competitor_price", { exact: true }).waitFor();
    await saveCapture(page, 2, "inventory-function-calling");
    await page.locator(".assistant-msg__text").last().scrollIntoViewIfNeeded();
    await saveCapture(page, 2, "inventory-reply");

    await page.getByRole("button", { name: "清空对话", exact: true }).click();
    const correction = await ask(
      page,
      "ISBN为978-7-00-000000-8 的书还有几本？比较一下其他平台价格，如果超时请按工具提示重试。"
    );
    const priceSteps = correction.body.steps.filter((step) => step.action === "get_competitor_price");
    if (priceSteps.length < 2 || priceSteps[0].ok || !priceSteps.at(-1).ok) {
      throw new Error("统一助手未展示模拟竞品超时后的 Tool Call 重试");
    }
    await saveResponse(2, "self-correction", correction.response, correction.body);
    await page.locator(".assistant-step--failed").waitFor();
    await saveCapture(page, 2, "timeout-self-correction");

    await page.getByRole("button", { name: "清空对话", exact: true }).click();
    const invalid = await ask(page, "ISBN为12345的书还有多少本？");
    if (!invalid.body.steps.some((step) => step.result?.error?.code === "INVALID_ISBN_FORMAT")) {
      throw new Error("统一助手未将错误 ISBN 交给库存工具并返回格式错误");
    }
    await saveResponse(2, "invalid-isbn", invalid.response, invalid.body);

    await page.getByRole("button", { name: "清空对话", exact: true }).click();
    const guide = await ask(
      page,
      "我想买一本关于微服务的书，另外如果我买了不喜欢，拆了塑封还能退吗？"
    );
    const actions = guide.body.steps.map((step) => step.action);
    const catalogIndex = actions.indexOf("search_book_catalog");
    const policyIndex = actions.indexOf("query_store_policy");
    if (catalogIndex < 0 || policyIndex <= catalogIndex) {
      throw new Error("统一助手未先检索书目、再检索退换货政策");
    }
    await saveResponse(3, "react-case", guide.response, guide.body);
    await writeReactTrace(guide.body.steps);
    await writeAssistantLog(guide.body.requestId);
    await page.locator(".assistant-step__name").filter({ hasText: "search_book_catalog" }).waitFor();
    await saveCapture(page, 3, "react-bookstore");
    await page.locator(".assistant-step__name").filter({ hasText: "query_store_policy" }).scrollIntoViewIfNeeded();
    await saveCapture(page, 3, "react-policy");
    await page.locator(".assistant-msg__text").last().scrollIntoViewIfNeeded();
    await saveCapture(page, 3, "react-reply");

    console.log("单一 /assistant 页面已采集真实 Function Calling 与 Thought → Action → Observation 记录。");
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
