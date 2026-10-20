"use strict";

/** 用真实浏览器验证管理员新增、编辑、删除图书及顾客原有页面，测试记录最终移除。 */
const { createRequire } = require("node:module");
const fs = require("node:fs/promises");
const runtime = createRequire(process.env.CODEX_NODE_PACKAGES + "/package.json");
const { chromium } = runtime("playwright-core");

async function login(page, username, password) {
  await page.goto("http://127.0.0.1:5173/login", { waitUntil: "domcontentloaded" });
  await page.locator("#username").fill(username);
  await page.locator("#password").fill(password);
  await page.locator("button[type='submit']").first().click();
  await page.waitForURL("**/books");
}

async function main() {
  const browser = await chromium.launch({ executablePath: process.env.BOOKSTORE_CHROMIUM, headless: true, chromiumSandbox: true });
  const checks = [];
  let createdId;
  let adminToken;
  try {
    const page = await browser.newPage();
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    await login(page, "admin", "admin123");
    const loginResponse = await page.request.post("http://127.0.0.1:8080/api/v1/users/login", { data: { username: "admin", password: "admin123" } });
    adminToken = (await loginResponse.json()).accessToken;
    await page.goto("http://127.0.0.1:5173/admin/books", { waitUntil: "domcontentloaded" });
    await page.getByRole("button", { name: "新增图书", exact: true }).click();
    const fields = { title: "浏览器集成测试图书", author: "课程测试", price: "68", stockQty: "6", isbn: "9787300000026", category: "测试", publisher: "课程", format: "纸质书", description: "本条记录仅用于浏览器真实新增编辑删除验证，完成后移除。" };
    for (const [name, value] of Object.entries(fields)) {
      await page.locator(".ant-modal #" + name).fill(value);
    }
    const createdPromise = page.waitForResponse((response) => response.url().endsWith("/api/v1/books") && response.request().method() === "POST");
    await page.locator(".ant-modal-footer .ant-btn-primary").click();
    const created = await createdPromise;
    if (created.status() !== 201) throw new Error("新增图书响应：" + created.status());
    createdId = (await created.json()).id;
    checks.push({ case: "管理员界面新增图书", status: 201, id: createdId });
    let row = page.locator("tr").filter({ hasText: fields.title });
    await row.getByRole("button", { name: /编\s*辑/ }).click();
    await page.locator(".ant-modal #title").fill("浏览器集成测试图书已编辑");
    await page.locator(".ant-modal #stockQty").fill("9");
    const updatePromise = page.waitForResponse((response) => response.url().endsWith("/api/v1/books/" + createdId) && response.request().method() === "PUT");
    await page.locator(".ant-modal-footer .ant-btn-primary").click();
    const updated = await updatePromise;
    const updateBody = await updated.json();
    if (updated.status() !== 200 || updateBody.stockQty !== 9) throw new Error("编辑库存未生效");
    checks.push({ case: "管理员界面编辑图书与库存", status: 200, stockQty: updateBody.stockQty });
    row = page.locator("tr").filter({ hasText: "浏览器集成测试图书已编辑" });
    const deletePromise = page.waitForResponse((response) => response.url().endsWith("/api/v1/books/" + createdId) && response.request().method() === "DELETE");
    await row.getByRole("button", { name: /删\s*除/ }).click();
    const removed = await deletePromise;
    if (removed.status() !== 204) throw new Error("删除图书未返回204");
    await row.waitFor({ state: "detached" });
    checks.push({ case: "管理员界面删除临时图书", status: 204 });
    createdId = undefined;
    for (const route of ["/admin/users", "/admin/orders", "/contract"]) {
      await page.goto("http://127.0.0.1:5173" + route, { waitUntil: "domcontentloaded" });
      await page.locator(".antd-shell__content").waitFor();
      if (page.url().endsWith("/login")) throw new Error("管理员刷新登录失效");
      checks.push({ case: "管理员刷新访问" + route, passed: true });
    }
    const customer = await browser.newPage();
    await login(customer, "DefaultUser", "123456");
    for (const route of ["/books", "/cart", "/orders", "/stats", "/user", "/assistant", "/guide"]) {
      await customer.goto("http://127.0.0.1:5173" + route, { waitUntil: "domcontentloaded" });
      await customer.locator(".antd-shell__content").waitFor();
      if (customer.url().endsWith("/login")) throw new Error("顾客刷新登录失效");
      checks.push({ case: "顾客刷新访问" + route, passed: true });
    }
    if (errors.length) throw new Error(errors.join("\n"));
    await fs.writeFile("docs/assignments/browser-regression.json", JSON.stringify({ checkedAt: new Date().toISOString(), browser: "Chromium", checks, pageErrors: errors }, null, 2));
    console.log("真实浏览器新增201、编辑200、删除204及10个业务页面检查全部通过。");
  } finally {
    if (createdId && adminToken) {
      await browser.contexts()[0].request.delete("http://127.0.0.1:8080/api/v1/books/" + createdId, { headers: { Authorization: "Bearer " + adminToken } });
    }
    await browser.close();
  }
}
main().catch((error) => { console.error(error); process.exitCode = 1; });
