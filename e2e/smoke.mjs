import assert from "node:assert/strict";
import { chromium } from "playwright";

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
const calls = [];

await page.route("http://127.0.0.1:8000/v1/**", async (route) => {
  const request = route.request();
  const url = new URL(request.url());
  const path = url.pathname;
  const method = request.method();
  calls.push({ path, method });

  const json = (body, status = 200) =>
    route.fulfill({
      status,
      contentType: "application/json",
      body: JSON.stringify(body),
    });

  if (path === "/v1/skills") {
    return json({ skills: [
      { id: "assistant.general", name: "General Assistant", description: "General help", enabled: true, risk: "low" },
      { id: "workflow.plan", name: "Workflow Planner", description: "Plan work", enabled: true, risk: "low" },
    ] });
  }
  if (path === "/v1/tools") {
    return json({ tools: [
      { id: "memory.search", name: "Search Memory", description: "Search current memory", risk: "low", enabled: true, requires_approval: false },
      { id: "automations.list", name: "List Automations", description: "List saved jobs", risk: "low", enabled: true, requires_approval: false },
      { id: "email.send", name: "Send Email", description: "Disabled write action", risk: "high", enabled: false, requires_approval: true },
    ] });
  }
  if (path === "/v1/integrations/status") {
    return json({ integrations: [
      { id: "openrouter", name: "OpenRouter", configured: true, mode: "model", note: "Configured" },
      { id: "email", name: "Email", configured: false, mode: "oauth", note: "Not connected" },
    ] });
  }
  if (path === "/v1/automations" && method === "GET") {
    return json({ automations: [], worker_enabled: false, scheduler: "disabled" });
  }
  if (path === "/v1/automations" && method === "POST") {
    return json({ id: "auto-1", name: "Test", enabled: false });
  }
  if (path === "/v1/system/stats") {
    return json({ model_configured: true, retrieval_mode: "fts5", automation_count: 0 });
  }
  if (path === "/v1/agent/run") {
    return json({ answer: "تم تنفيذ المهمة التجريبية بنجاح.", model: "mock-model", sources: [] });
  }
  if (path === "/v1/tools/automations.list/execute") {
    return json({ status: "completed", result: [{ id: "auto-1", name: "Daily report" }] });
  }
  if (path === "/v1/designer/estimate") {
    return json({ approval_id: "approval-token-12345678901234567890", estimated_cost_usd: 0.04, model: "mock-image-model", size: "1024x1024" });
  }
  if (path === "/v1/designer/generate") {
    return json({ id: "image-1", artifact_url: "/v1/designer/artifacts/image-1", estimated_cost_usd: 0.04 });
  }
  if (path === "/v1/designer/artifacts/image-1") {
    return route.fulfill({
      status: 200,
      contentType: "image/png",
      body: Buffer.from([137, 80, 78, 71, 13, 10, 26, 10, 1, 2, 3]),
    });
  }
  if (path === "/v1/voice/status") {
    return json({ whisper: { configured: false, reachable: false }, kokoro: { configured: false, reachable: false } });
  }
  if (path === "/v1/tools/audit") {
    return json({ executions: [] });
  }
  return json({ detail: "Unhandled mocked endpoint: " + path }, 404);
});

try {
  await page.goto("http://127.0.0.1:5173", { waitUntil: "networkidle" });
  assert.match(await page.title(), /Ahmed Maaroof Agent OS/);

  await page.getByPlaceholder("AGENT_API_KEY").first().fill("e2e-test-key");
  await page.getByText("النظام متصل").waitFor();

  await page.getByRole("button", { name: /المساعد المركزي/ }).first().click();
  await page.getByPlaceholder("اكتب المهمة أو السؤال هنا...").fill("نفذ اختبار الواجهة");
  await page.getByPlaceholder("اكتب المهمة أو السؤال هنا...").press("Enter");
  await page.getByText("تم تنفيذ المهمة التجريبية بنجاح.").waitFor();

  await page.getByRole("button", { name: /مكتبة المهارات/ }).first().click();
  const automationTool = page.locator(".tool-row").filter({ hasText: "List Automations" });
  await automationTool.getByRole("button", { name: "تنفيذ" }).click();
  await page.getByText("Daily report").waitFor();

  await page.getByRole("button", { name: /استوديو التصميم/ }).first().click();
  await page.getByPlaceholder("اكتب وصفاً دقيقاً للصورة المطلوبة...").fill("Minimal geometric poster in blue and ivory");
  await page.getByRole("button", { name: "تقدير التكلفة" }).click();
  await page.getByText("0.0400 USD").waitFor();
  await page.getByRole("button", { name: "موافقة وتوليد" }).click();
  await page.getByAltText("Generated design result").waitFor();

  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("button", { name: "فتح القائمة" }).waitFor();

  assert(calls.some((call) => call.path === "/v1/agent/run"));
  assert(calls.some((call) => call.path === "/v1/tools/automations.list/execute"));
  assert(calls.some((call) => call.path === "/v1/designer/generate"));
  process.stdout.write("Playwright smoke E2E passed: connect, chat, tools, Designer approval, responsive navigation.\n");
} finally {
  await browser.close();
}
