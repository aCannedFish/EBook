"use strict";

/** 仅请求本机：更新实际模型记录页面，以及 Swagger 实际 401/200 与虚拟线程截图。 */
const { createRequire } = require("node:module");
const fs = require("node:fs/promises");
const crypto = require("node:crypto");
const runtime = createRequire(process.env.CODEX_NODE_PACKAGES + "/package.json");
const { chromium } = runtime("playwright-core");

async function save(page, locator, file, options) {
  if (options) await page.screenshot({ path: file, ...options });
  else await locator.screenshot({ path: file });
  const manifest = JSON.parse(await fs.readFile("docs/assignments/browser-captures.json", "utf8"));
  manifest.captureMethod = "Playwright Chromium page.screenshot / locator.screenshot";
  manifest.screenshots = manifest.screenshots.filter((item) => item.file !== file);
  manifest.screenshots.push({ file, url: page.url(), capturedAt: new Date().toISOString(), sha256: crypto.createHash("sha256").update(await fs.readFile(file)).digest("hex") });
  await fs.writeFile("docs/assignments/browser-captures.json", JSON.stringify(manifest, null, 2));
  console.log("已保存真实页面截图：", file);
}

async function saveSwagger(page, block, file) {
  await block.locator(".responses-inner").scrollIntoViewIfNeeded();
  await page.waitForTimeout(350);
  const start = await block.locator(".curl-command").boundingBox();
  const end = await block.locator(".live-responses-table").boundingBox();
  const width = (await block.locator(".responses-inner").boundingBox()).width;
  const height = end.y + end.height - start.y + 12;
  if (start.y < 0 || start.y + height > 1800) throw new Error("实际响应超出截图视口");
  await save(page, null, file, { clip: { x: start.x, y: start.y, width: Math.min(start.width, width), height } });
}

async function main() {
  const browser = await chromium.launch({ executablePath: process.env.BOOKSTORE_CHROMIUM, headless: true, chromiumSandbox: true });
  try {
    const context = await browser.newContext();
    const page = await context.newPage();
    await page.goto("http://127.0.0.1:5173/login", { waitUntil: "domcontentloaded" });
    await page.locator("#username").fill("admin");
    await page.locator("#password").fill("admin123");
    await page.locator("button[type='submit']").first().click();
    await page.waitForURL("**/books");
    await page.goto("http://127.0.0.1:5173/contract", { waitUntil: "domcontentloaded" });
    await page.getByText("契约校验通过", { exact: true }).waitFor();
    await save(page, page.locator(".antd-shell"), "docs/assignments/hw1/screenshots/contract-conversation.png");
    await page.getByText("查看完整 JSON", { exact: true }).last().click();
    await page.locator("pre").last().waitFor({ state: "visible" });
    await page.waitForTimeout(700);
    await save(page, page.locator(".ant-card-small").last(), "docs/assignments/hw1/screenshots/contract-json.png");

    const login = await context.request.post("http://127.0.0.1:8080/api/v1/users/login", { data: { username: "DefaultUser", password: "123456" } });
    const jwt = (await login.json()).accessToken;
    const swagger = await context.newPage();
    await swagger.setViewportSize({ width: 1280, height: 1800 });
    await swagger.goto("http://127.0.0.1:8080/swagger-ui/index.html", { waitUntil: "domcontentloaded" });
    const detail = swagger.locator(".opblock-get").filter({ has: swagger.getByRole("link", { name: "/api/v1/books/{id}", exact: true }) });
    await detail.locator(".opblock-summary").click();
    await detail.getByRole("button", { name: "Try it out", exact: true }).click();
    await detail.locator("input").first().fill("1");
    await detail.getByRole("button", { name: "Execute", exact: true }).click();
    await detail.locator(".live-responses-table .response-col_status").filter({ hasText: "401" }).waitFor();
    await detail.getByText("Response headers", { exact: true }).waitFor();
    await saveSwagger(swagger, detail, "docs/assignments/hw4/screenshots/jwt-401.png");
    await swagger.getByRole("button", { name: "Authorize", exact: true }).click();
    await swagger.locator("#auth-bearer-value").fill(jwt);
    await swagger.getByRole("button", { name: "Apply credentials", exact: true }).click();
    await swagger.getByRole("button", { name: "Close", exact: true }).click();
    await detail.getByRole("button", { name: "Execute", exact: true }).click();
    await detail.locator(".live-responses-table .response-col_status").filter({ hasText: "200" }).waitFor();
    await saveSwagger(swagger, detail, "docs/assignments/hw4/screenshots/jwt-200.png");
    const runtimeBlock = swagger.locator(".opblock-get").filter({ has: swagger.getByRole("link", { name: "/api/v1/runtime", exact: true }) });
    await runtimeBlock.locator(".opblock-summary").click();
    await runtimeBlock.getByRole("button", { name: "Try it out", exact: true }).click();
    await runtimeBlock.getByRole("button", { name: "Execute", exact: true }).click();
    await runtimeBlock.locator(".live-responses-table").filter({ hasText: "requestThreadVirtual" }).waitFor();
    await saveSwagger(swagger, runtimeBlock, "docs/assignments/hw4/screenshots/virtual-thread-runtime.png");
  } finally {
    await browser.close();
  }
}
main().catch((error) => { console.error(error); process.exitCode = 1; });
