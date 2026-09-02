import type { Tab } from "../FullCommandCenter";

/**
 * Design Bible Chapter 67 (TradeTown Operating System) — Phase 1, the
 * smallest honest slice: grouping the Command Center's 34 real,
 * already-shipped tabs into TTOS's 7 permanent sections. Purely a
 * rendering-layer reorganization — every `Tab` string identifier and
 * every button's visible accessible name are left byte-for-byte
 * unchanged, since `frontend/tests/helpers.ts`'s `clickTab()` looks
 * buttons up by exact accessible name across the whole Playwright
 * suite, and `FullCommandCenter.tsx`'s number-key 1-9 shortcut indexes
 * into the `TABS` array positionally. Changing either would ripple into
 * every existing spec file for zero real user benefit — see this
 * chapter's own migration-plan discussion for why "don't rename, just
 * regroup" was the chosen approach over a true identifier restructure.
 *
 * Several placements are real judgment calls, not settled fact — this
 * file exists to make each one explicit and revisitable rather than
 * silently baked into JSX:
 * - TREASURY is CEO-*personal* capital, distinct from the company's own
 *   trading portfolio (see `TreasuryPanel.tsx`'s own "isolated second
 *   account" framing) — placed under Headquarters (an executive-personal
 *   matter), not Portfolio (the company's).
 * - OPS (`KnowledgeBasePanel.tsx`, the Company Operating System's
 *   Knowledge Absorption feed over six real learning sources) is placed
 *   under Research, not Operations — its content is a learning feed, not
 *   infrastructure/automation, despite the name collision with the TTOS
 *   section itself. Renaming the tab to avoid that collision is deferred
 *   to a later phase (it would change its button's accessible name).
 * - DISCIPLINE (Library of Mistakes/Successes, discipline case studies)
 *   and PERFORMANCE (monthly P&L reporting) each plausibly fit two
 *   sections; placed under AI Workforce and Archive respectively.
 * - EVOLUTION (Chapter 74's CLSIS Self-Improvement Proposals +
 *   Institutional Evolution Engine, and Chapter 74.5's CEO Vision
 *   Board — bundled into one tab, EvolutionPanel.tsx) sits next to
 *   DISCIPLINE/REASONING/REFLECTION under AI Workforce: it's company-
 *   wide learning about how the company itself operates, not a
 *   portfolio-facing control, despite the Vision Board's own CEO-
 *   authored mission/priorities content.
 * - Operations is real but thin (LOGS only) — Automation, Integrations,
 *   Infrastructure, and Broker Configuration have no backing feature
 *   anywhere in this codebase today, so no placeholder tabs were added
 *   to fill the section out (see Chapter 67's own "no placeholder pages"
 *   constraint).
 */
export const SECTION_ORDER = ["HEADQUARTERS", "MARKETS", "AI WORKFORCE", "RESEARCH", "PORTFOLIO", "OPERATIONS", "ARCHIVE"] as const;
export type Section = (typeof SECTION_ORDER)[number];

export const TAB_SECTION: Record<Tab, Section> = {
  OVERVIEW: "HEADQUARTERS",
  COMPANY: "HEADQUARTERS",
  EXECUTIVE: "HEADQUARTERS",
  EXECINTEL: "HEADQUARTERS",
  CALENDAR: "HEADQUARTERS",
  CONSTITUTION: "HEADQUARTERS",
  FOUNDERS: "HEADQUARTERS",
  TREASURY: "HEADQUARTERS",
  COMPLIANCE: "HEADQUARTERS",
  SITUATIONROOM: "HEADQUARTERS",

  MARKETCHART: "MARKETS",
  LIVEDESK: "MARKETS",
  MARKETINTEL: "MARKETS",
  ECONINTEL: "MARKETS",

  AGENTS: "AI WORKFORCE",
  KNOWLEDGE: "AI WORKFORCE",
  MENTOR: "AI WORKFORCE",
  MENTORLIB: "AI WORKFORCE",
  MENTORLAB: "AI WORKFORCE",
  TALENT: "AI WORKFORCE",
  TRAINING: "AI WORKFORCE",
  PVAI: "AI WORKFORCE",
  ACADEMY: "AI WORKFORCE",
  REASONING: "AI WORKFORCE",
  REFLECTION: "AI WORKFORCE",
  DISCIPLINE: "AI WORKFORCE",
  EVOLUTION: "AI WORKFORCE",

  RESEARCH: "RESEARCH",
  SANDBOX: "RESEARCH",
  BLACKBOX: "RESEARCH",
  OPS: "RESEARCH",

  RISK: "PORTFOLIO",
  BLACKSWAN: "PORTFOLIO",
  TRADINGMODES: "PORTFOLIO",
  TRAVELMODE: "PORTFOLIO",
  PORTFOLIO: "PORTFOLIO",
  WARROOM: "PORTFOLIO",
  DECISIONS: "PORTFOLIO",
  OPPORTUNITIES: "PORTFOLIO",
  PSYCHOLOGY: "PORTFOLIO",

  LOGS: "OPERATIONS",

  VAULT: "ARCHIVE",
  REPLAY: "ARCHIVE",
  PERFORMANCE: "ARCHIVE",
};

/** Groups `tabs` (in their original declared order) by TTOS section,
 * in `SECTION_ORDER`. Returns only sections that have at least one tab
 * in the input — every section is populated today, but this keeps the
 * function honest if that ever changes. */
export function groupTabsBySection(tabs: readonly Tab[]): { section: Section; tabs: Tab[] }[] {
  return SECTION_ORDER.map((section) => ({
    section,
    tabs: tabs.filter((t) => TAB_SECTION[t] === section),
  })).filter((group) => group.tabs.length > 0);
}

/**
 * CEO directive "TradeTown — Command Center + Professional Quant
 * Trading Firm Upgrade," Phase 2 — the real IA consolidation this
 * chapter's own comment above deferred ("a true identifier restructure
 * ... is deferred to a later phase"). Five primary destinations plus a
 * MORE drawer, replacing the old flat 42-button/7-section bar as the
 * PRIMARY navigation layer.
 *
 * Deliberately NOT a rename: every `Tab` string identifier above is
 * completely untouched (still exactly what `FullCommandCenter.tsx`'s
 * big tab === "X" render block switches on, and still exactly what
 * every existing Playwright spec's `clickTab()` call looks up by exact
 * accessible name) — this is a second, coarser grouping layered on top
 * of the same 42 tabs, not a replacement for them. `clickTab()` itself
 * (see tests/helpers.ts) was made area-aware so every existing spec
 * call site keeps working unchanged: it looks up a tab's area, clicks
 * into that area first if it isn't already active, then clicks the
 * tab's own button exactly as before.
 *
 * The five areas roughly consolidate the existing seven TTOS sections
 * (not a coincidence — TAB_SECTION's own careful reasoning above was
 * the starting point for these placements, not re-derived from
 * scratch). Real judgment calls, documented rather than silently
 * baked in:
 * - EXECUTIVE (Trade Gatekeeper stats/rejections/CEO decisions) sits
 *   under PORTFOLIO & RISK, not RESEARCH & INTELLIGENCE — it's the
 *   final approval gate on real capital, not a research artifact.
 * - BLACKSWAN, TRADINGMODES, COMPLIANCE, DISCIPLINE join PORTFOLIO &
 *   RISK for the same reason: all four are real controls/audits over
 *   the company's actual risk posture, not market analysis or
 *   research evidence.
 * - DECISIONS, VAULT, WARROOM, REPLAY, REASONING, REFLECTION,
 *   OPPORTUNITIES, EXECINTEL, BLACKBOX, SANDBOX, RESEARCH all sit
 *   under RESEARCH & INTELLIGENCE — every one of them is either a
 *   research/backtesting workspace or a record of HOW a decision was
 *   reached, not the decision's real-money consequence.
 * - AI DESK is deliberately narrow (AGENTS/FOUNDERS/TALENT only) —
 *   "who's doing what right now and how they're rated," not the whole
 *   Academy/Mentor learning-content cluster, which stays in MORE
 *   alongside the rest of the company's slower-moving systems.
 * - MARKETS is deliberately narrow (MARKETCHART/MARKETINTEL/
 *   ECONINTEL). MARKETCHART is a new real `Tab` added alongside this
 *   redesign (chart overlays — support/resistance, Fibonacci, Fair
 *   Value Gaps, Order Block, confirmed chart patterns — all reusing
 *   `MarketChartPanel.tsx`, the same component OVERVIEW already
 *   embeds, never a second chart implementation) so the "central
 *   market intelligence workspace" the directive asks for has a real,
 *   first-class home rather than staying buried only inside OVERVIEW.
 * - Every tab NOT listed under one of the first five areas falls into
 *   MORE by construction (`tabsForArea` below), and MORE's own picker
 *   still uses `groupTabsBySection` on just its own 17 tabs — so the
 *   TTOS section labels this codebase already carefully reasoned about
 *   keep doing real organizational work there instead of being thrown
 *   away.
 */
export const AREA_ORDER = ["OVERVIEW", "MARKETS", "AI DESK", "PORTFOLIO & RISK", "RESEARCH & INTELLIGENCE", "MORE"] as const;
export type Area = (typeof AREA_ORDER)[number];

const PRIMARY_AREA_TABS: Record<Exclude<Area, "MORE">, Tab[]> = {
  OVERVIEW: ["OVERVIEW"],
  MARKETS: ["LIVEDESK", "MARKETCHART", "MARKETINTEL", "ECONINTEL"],
  "AI DESK": ["AGENTS", "FOUNDERS", "TALENT"],
  "PORTFOLIO & RISK": ["RISK", "PORTFOLIO", "PERFORMANCE", "EXECUTIVE", "TRADINGMODES", "COMPLIANCE", "DISCIPLINE", "BLACKSWAN"],
  "RESEARCH & INTELLIGENCE": ["SANDBOX", "RESEARCH", "DECISIONS", "VAULT", "WARROOM", "REASONING", "REFLECTION", "BLACKBOX", "OPPORTUNITIES", "EXECINTEL", "REPLAY"],
};

const PRIMARY_TAB_SET = new Set<Tab>(Object.values(PRIMARY_AREA_TABS).flat());

/** Every real `Tab` this area contains, in `TABS`' own declared order
 * (so a primary area's default/first tab is always the same one
 * `groupTabsBySection` would have shown first, and MORE's own default
 * lands on whichever of its tabs appears earliest in TABS — COMPANY
 * today). `MORE` is derived (every tab none of the five primary areas
 * claims) rather than hand-listed, so a newly added `Tab` can never
 * silently vanish from the navigation entirely — it always lands in
 * MORE by default until a primary-area placement is deliberately
 * chosen for it. */
export function tabsForArea(area: Area, tabs: readonly Tab[]): Tab[] {
  if (area === "MORE") return tabs.filter((t) => !PRIMARY_TAB_SET.has(t));
  return tabs.filter((t) => PRIMARY_AREA_TABS[area].includes(t));
}

const AREA_BY_TAB: Partial<Record<Tab, Area>> = {};
for (const area of AREA_ORDER) {
  if (area === "MORE") continue;
  for (const t of PRIMARY_AREA_TABS[area]) AREA_BY_TAB[t] = area;
}

/** Which of the six top-level areas a given real `Tab` lives under —
 * `MORE` for anything not explicitly placed in one of the five primary
 * areas above. */
export function areaForTab(tab: Tab): Area {
  return AREA_BY_TAB[tab] ?? "MORE";
}
