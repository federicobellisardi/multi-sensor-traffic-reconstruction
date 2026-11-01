/**
 * Complete workflow: browser -> real API -> real sim_engine -> real output files -> browser.
 * No mocks. Research outputs are hidden (ALPHA_SIM_RUNS points nowhere), so everything here, screenshots
 * included, comes from synthetic demand on the public network and can be committed.
 */
import { expect, test, type Page } from "@playwright/test";
import { spawn, execSync, type ChildProcess } from "node:child_process";
import { mkdtempSync, readFileSync, readdirSync, mkdirSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const BACKEND = join(import.meta.dirname, "../../backend");
const SHOTS = join(import.meta.dirname, "../../docs/screenshots");
const URL = "http://127.0.0.1:8799";
const state = mkdtempSync(join(process.env.ALPHA_E2E_TMP ?? tmpdir(), "alpha-e2e-"));
let server: ChildProcess;

async function startServer() {
  server = spawn(join(process.env.VENV!, "bin/uvicorn"), ["app.asgi:app", "--host", "127.0.0.1", "--port", "8799", "--timeout-graceful-shutdown", "5"], {
    cwd: BACKEND, stdio: "inherit",
    env: { ...process.env, ALPHA_STATE_DIR: state, ALPHA_SIM_RUNS: join(state, "no-research-runs"), ALPHA_RESEARCH_PYTHON: "/nonexistent", ALPHA_POLL_S: "0.3", ALPHA_MIN_AVAILABLE_MEMORY_GB: "1" },
  });
  for (let i = 0; i < 120; i++) {
    if (server.exitCode !== null) throw new Error("server exited at startup; is port 8799 in use?");
    try { if ((await fetch(`${URL}/api/health`)).ok) return; } catch { /* starting */ }
    await new Promise((r) => setTimeout(r, 500));
  }
  throw new Error("server did not start");
}

async function stopServer() {
  if (server.exitCode !== null) return;
  const done = new Promise((r) => server.once("exit", r));
  const force = setTimeout(() => server.kill("SIGKILL"), 15_000);
  server.kill("SIGTERM");
  await done;
  clearTimeout(force);
}

test.beforeAll(async () => { mkdirSync(SHOTS, { recursive: true }); await startServer(); });
test.afterAll(async () => { await stopServer(); });

async function scenarioFromBaseline(page: Page, name: string, hours: string, trips: string, factor = "1") {
  await page.goto("/#/scenarios");
  await page.getByRole("button", { name: "New scenario" }).click();
  const form = page.getByRole("form", { name: "Scenario form" });
  await form.getByLabel("Name").fill(name);
  await form.getByLabel("Hours from midnight").fill(hours);
  await form.getByLabel("Synthetic trips per day").fill(trips);
  await form.getByLabel("Demand multiplier").fill(factor);
  await form.getByLabel("Seed").fill("5");
  await form.getByRole("button", { name: "Save scenario" }).click();
  await expect(page.getByTestId(`scenario-${name}`)).toBeVisible();
}

async function launch(page: Page, name: string) {
  await page.getByTestId(`scenario-${name}`).getByRole("button", { name: "Launch" }).click();
  await expect(page.getByTestId("run-detail")).toBeVisible();
  return page.url().split("/").pop()!;
}

// the bracket keeps pgrep from matching the shell running it
const enginesOf = (id: string) => Number(execSync(`pgrep -fc "[s]im_engine ${state}/runs/${id}/sim.json" || true`).toString().trim());
const detailStatus = (page: Page) => page.getByTestId("run-detail").getByTestId("status");
const roadsRendered = (page: Page) => page.evaluate(() => (window as any).__alphaMap.queryRenderedFeatures({ layers: ["roads"] }).length as number);

test("network loads with an empty state before any run", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("note")).toContainText("not a validated predictive digital twin");
  await expect(page.getByTestId("map")).toHaveAttribute("data-ready", "true", { timeout: 60_000 });
  await page.waitForFunction(() => (window as any).__alphaMap.loaded());
  expect(await roadsRendered(page)).toBeGreaterThan(1000);
  await expect(page.getByText("No completed runs yet")).toBeVisible();
  await page.screenshot({ path: join(SHOTS, "01_empty_network.png") });
});

test("the frozen profile is refused cleanly without private inputs and closures are not offered", async ({ page }) => {
  await page.goto("/#/scenarios");
  const frozen = page.getByTestId("scenario-Frozen model: Monday 10 Feb 2020");
  await expect(frozen.getByRole("button", { name: "Launch" })).toBeDisabled();
  await expect(frozen).toContainText("Cannot run here");
  await page.getByRole("button", { name: "New scenario" }).click();
  await expect(page.getByLabel("Road closure: not available")).toBeDisabled();
});

test("invalid parameters are rejected with a readable message", async ({ page }) => {
  await page.goto("/#/scenarios");
  await page.getByRole("button", { name: "New scenario" }).click();
  const form = page.getByRole("form", { name: "Scenario form" });
  await form.getByLabel("Name").fill("invalid");
  await form.getByLabel("Hours from midnight").fill("99");
  await form.getByRole("button", { name: "Save scenario" }).click();
  await expect(form.getByRole("alert")).toContainText("hours");
});

test("create, launch, monitor, inspect on map and chart, compare", async ({ page }) => {
  await scenarioFromBaseline(page, "e2e-a", "3", "60000");
  const a = await launch(page, "e2e-a");
  await page.screenshot({ path: join(SHOTS, "02_run_monitoring.png") });
  await expect(detailStatus(page)).toHaveText(/Completed/, { timeout: 8 * 60_000 });
  await expect(page.getByTestId("log")).toContainText("simulation done");
  await expect(page.getByTestId("run-detail")).toContainText("SYNTHETIC");
  await page.screenshot({ path: join(SHOTS, "03_run_completed.png") });

  // what the browser shows must be what the engine wrote
  await page.getByRole("link", { name: "View on map" }).click();
  await expect(page.getByTestId("map")).toHaveAttribute("data-ready", "true", { timeout: 60_000 });
  await expect(page.getByText("SYNTHETIC DEMAND. Not real traffic.")).toBeVisible();
  await expect(page.getByTestId("legend")).toBeVisible();

  const dir = join(state, "runs", a);
  const file = readdirSync(dir).find((f) => /^sim_uniq_.*\.csv$/.test(f))!;
  const rows = readFileSync(join(dir, file), "utf8").trim().split("\n").slice(1).map((l) => l.split(";"));
  const totals = new Map<number, number[]>();
  for (const r of rows) {
    const v = r.slice(3).map(Number);
    const cid = Number(r[1]);
    totals.set(cid, (totals.get(cid) ?? v.map(() => 0)).map((x, i) => x + v[i]));
  }
  const busiest = [...totals.entries()].sort((x, y) => y[1][2] - x[1][2])[0];
  expect(busiest[1][2]).toBeGreaterThan(0);

  await page.getByRole("slider", { name: "Hour" }).fill("2");
  await page.waitForFunction(({ cid, max }) => {
    const m = (window as any).__alphaMap;
    return m.getFeatureState({ source: "roads", id: cid }).v === 1 && max > 0;
  }, { cid: busiest[0], max: busiest[1][2] });

  // select the busiest road by a real click on the canvas
  const net = await (await fetch(`${URL}/api/network`)).json();
  const coords = net.features.find((f: any) => f.id === busiest[0]).geometry.coordinates;
  const middle = coords[Math.floor(coords.length / 2)];
  await page.evaluate((c) => { (window as any).__alphaMap.jumpTo({ center: c, zoom: 13 }); }, middle);
  await page.waitForFunction(() => (window as any).__alphaMap.loaded());
  const hit = await page.evaluate((c) => {
    const m = (window as any).__alphaMap;
    const canvas = m.getCanvas().getBoundingClientRect();
    const p = m.project(c);
    return { x: canvas.x + p.x, y: canvas.y + p.y };
  }, middle);
  await page.mouse.click(hit.x, hit.y);
  await expect(page.getByTestId("link-chart")).toBeVisible();
  const heading = await page.locator(".results h2").first().textContent();
  const cid = Number(heading!.replace("Road ", ""));
  await page.getByRole("button", { name: "Show table" }).click();
  await expect(page.locator("[data-testid=link-chart] tbody tr")).toHaveCount(3);
  const cells = await page.locator("[data-testid=link-chart] tbody tr").evaluateAll((trs) => trs.map((tr) => [...tr.querySelectorAll("td")].map((td) => td.textContent)));
  const ft = rows.find((r) => Number(r[1]) === cid && r[2] === "FT")!.slice(3).map(Number);
  const tf = rows.find((r) => Number(r[1]) === cid && r[2] === "TF")!.slice(3).map(Number);
  expect(cells.map((c) => Number(c[1]!.replace(/,/g, "")))).toEqual(ft);
  expect(cells.map((c) => Number(c[2]!.replace(/,/g, "")))).toEqual(tf);
  await page.getByRole("button", { name: "Show chart" }).click();
  await page.evaluate(() => { (window as any).__alphaMap.jumpTo({ center: [11.1, 44.55], zoom: 7.3 }); });
  await page.waitForTimeout(800);
  await page.screenshot({ path: join(SHOTS, "04_map_road_chart.png") });

  // road class filter acts on the rendered map
  await page.waitForFunction(() => (window as any).__alphaMap.loaded());
  const before = await roadsRendered(page);
  await page.getByRole("checkbox", { name: "secondary" }).uncheck();
  await page.waitForFunction(() => (window as any).__alphaMap.loaded());
  await page.waitForTimeout(300);
  expect(await roadsRendered(page)).toBeLessThan(before);
  await page.getByRole("checkbox", { name: "secondary" }).check();

  // demand perturbation, then comparison
  await scenarioFromBaseline(page, "e2e-b", "3", "60000", "2");
  const b = await launch(page, "e2e-b");
  await expect(detailStatus(page)).toHaveText(/Completed/, { timeout: 8 * 60_000 });
  await page.goto(`/#/map/${a}`);
  await expect(page.getByTestId("map")).toHaveAttribute("data-ready", "true", { timeout: 60_000 });
  await page.getByLabel("Compare with (B − A)").selectOption(b);
  await expect(page.getByTestId("total-change")).toHaveText(/%/);
  const change = parseFloat((await page.getByTestId("total-change").textContent())!);
  expect(change).toBeGreaterThan(30);  // twice the departures: more passages, not necessarily exactly double
  await page.waitForTimeout(800);
  await page.screenshot({ path: join(SHOTS, "05_compare.png") });
});

test("cancelling a run stops the engine process", async ({ page }) => {
  await scenarioFromBaseline(page, "e2e-cancel", "24", "200000");
  const id = await launch(page, "e2e-cancel");
  await expect.poll(() => enginesOf(id), { timeout: 30_000, intervals: [100] }).toBe(1);
  await page.getByRole("button", { name: "Cancel run" }).click();
  await expect(detailStatus(page)).toHaveText(/Cancelled/, { timeout: 60_000 });
  await expect.poll(() => enginesOf(id), { timeout: 15_000 }).toBe(0);
  await expect(page.getByRole("link", { name: "View on map" })).toHaveCount(0);
});

test("an engine crash is shown as a failure with its log", async ({ page }) => {
  await scenarioFromBaseline(page, "e2e-crash", "24", "200000");
  const id = await launch(page, "e2e-crash");
  await expect.poll(() => enginesOf(id), { timeout: 30_000, intervals: [100] }).toBe(1);
  execSync(`pkill -9 -f "[s]im_engine ${state}/runs/${id}/sim.json"`);
  await expect(detailStatus(page)).toHaveText(/Failed/, { timeout: 30_000 });
  await expect(page.getByTestId("run-detail").getByRole("alert")).toContainText("no flow output");
  await page.screenshot({ path: join(SHOTS, "06_run_failed.png") });
});

test("previous runs survive a server restart", async ({ page }) => {
  const before = await (await fetch(`${URL}/api/runs?status=completed`)).json();
  expect(before.length).toBeGreaterThanOrEqual(2);
  await stopServer();
  await startServer();
  await page.goto(`/#/runs/${before[0].id}`);
  await expect(detailStatus(page)).toHaveText(/Completed/);
  await page.getByRole("link", { name: "View on map" }).click();
  await expect(page.getByTestId("legend")).toBeVisible({ timeout: 60_000 });
});

test("the layout works at phone width", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 800 });
  for (const h of ["#/map", "#/runs", "#/scenarios"]) {
    await page.goto(`/${h}`);
    await page.waitForTimeout(800);
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(overflow, h).toBeLessThanOrEqual(0);
  }
  await page.goto("/#/map");
  await page.waitForTimeout(1500);
  await page.screenshot({ path: join(SHOTS, "07_phone.png") });
});
