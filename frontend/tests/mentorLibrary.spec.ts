import { test, expect, type Page } from "@playwright/test";

/**
 * v0.7 Feature 49 (Phase 3) — the Foundational Mentor Program. Same
 * real-app testing approach as dailyObjectives.spec.ts — exercises the
 * live Vite + FastAPI stack, no mocking.
 */

async function clickContinueOnTitleScreen(page: Page): Promise<void> {
  const canvas = page.locator("canvas");
  await expect(canvas).toBeVisible();
  await page.waitForTimeout(800);
  for (let attempt = 0; attempt < 5; attempt++) {
    const box = await canvas.boundingBox();
    if (!box) throw new Error("canvas has no bounding box");
    await page.mouse.click(box.x + box.width / 2, box.y + box.height * 0.5 + 44);
    try {
      await page.getByRole("button", { name: "Command ⌁" }).waitFor({ state: "attached", timeout: 3000 });
      return;
    } catch {
      // not in-game yet — try again
    }
  }
  throw new Error("clickContinueOnTitleScreen: never reached an in-game scene after 5 click attempts");
}

async function dismissTradeOutcomePopups(page: Page): Promise<void> {
  for (let i = 0; i < 5; i++) {
    const tradeBanner = page.getByTestId("trade-outcome-banner");
    if (await tradeBanner.isVisible().catch(() => false)) {
      await tradeBanner.getByText("Dismiss").click();
      await tradeBanner.waitFor({ state: "hidden", timeout: 3000 }).catch(() => {});
      continue;
    }
    const votingPopup = page.getByTestId("executive-voting");
    if (await votingPopup.isVisible().catch(() => false)) {
      await votingPopup.getByText("Decide later").click();
      await votingPopup.waitFor({ state: "hidden", timeout: 3000 }).catch(() => {});
      continue;
    }
    return;
  }
}

async function continueGame(page: Page): Promise<void> {
  await clickContinueOnTitleScreen(page);
  await dismissTradeOutcomePopups(page);
}

async function clickTab(page: Page, tab: string): Promise<void> {
  for (let attempt = 0; attempt < 5; attempt++) {
    await dismissTradeOutcomePopups(page);
    try {
      await page.getByRole("button", { name: tab, exact: true }).click({ timeout: 5000 });
      return;
    } catch {
      // a popup intercepted the click — loop back and dismiss again
    }
  }
  throw new Error(`clickTab: could not click "${tab}" after 5 attempts`);
}

test("the backend state seeds all six mentor tracks in roadmap order, only tjr active with real content", async ({ page }) => {
  await page.goto("/");
  const state = await page.evaluate(async () => {
    const res = await fetch("/api/load");
    return res.json();
  });
  const fm = state.foundationalMentorState;
  expect(fm).toBeTruthy();
  expect(fm.mentors.map((m: { id: string }) => m.id)).toEqual(["tjr", "al_brooks", "linda_raschke", "mark_douglas", "tom_hougaard", "mike_bellafiore"]);

  const tjr = fm.mentors.find((m: { id: string }) => m.id === "tjr");
  expect(tjr.status).toBe("active");
  expect(tjr.lessons.length).toBe(6);
  expect(tjr.contentNote).toContain("original TradeTown-authored teaching material");

  for (const mentor of fm.mentors.filter((m: { id: string }) => m.id !== "tjr")) {
    expect(mentor.status).toBe("planned");
    expect(mentor.lessons).toEqual([]);
  }
});

test("the MENTORLIB tab shows the content disclaimer and a real quiz round-trips through POST /api/foundational-mentors/quiz", async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push(msg.text());
  });

  await page.goto("/");
  await continueGame(page);

  for (let attempt = 0; attempt < 5; attempt++) {
    await dismissTradeOutcomePopups(page);
    try {
      await page.getByRole("button", { name: "Command ⌁" }).click({ timeout: 5000 });
      break;
    } catch {
      // a popup intercepted the click — loop back and dismiss again
    }
  }
  await page.getByRole("button", { name: "EXPAND — FULL COMMAND CENTER" }).click();
  await clickTab(page, "MENTORLIB");

  const detail = page.getByTestId("mentor-library-detail");
  await expect(detail.getByText(/original TradeTown-authored teaching material/)).toBeVisible();

  await detail.getByText("1. Trading Psychology: Process Over Outcome").click();

  const viewer = page.getByTestId("mentor-lesson-viewer");
  await expect(viewer.getByText("Trading Psychology: Process Over Outcome")).toBeVisible();

  await viewer.getByRole("button", { name: "It stays high — Discipline Score never reads trade P&L" }).click();

  await Promise.all([page.waitForResponse((res) => res.url().includes("/api/foundational-mentors/quiz") && res.ok()), viewer.getByRole("button", { name: "Submit Answer" }).click()]);

  await expect(viewer.getByText(/CORRECT|NOT QUITE/)).toBeVisible();

  const relevantErrors = consoleErrors.filter((e) => !e.includes("favicon"));
  expect(relevantErrors).toEqual([]);
});
