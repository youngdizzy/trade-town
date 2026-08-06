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

  RESEARCH: "RESEARCH",
  SANDBOX: "RESEARCH",
  BLACKBOX: "RESEARCH",
  OPS: "RESEARCH",

  RISK: "PORTFOLIO",
  PORTFOLIO: "PORTFOLIO",
  WARROOM: "PORTFOLIO",
  DECISIONS: "PORTFOLIO",
  OPPORTUNITIES: "PORTFOLIO",

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
