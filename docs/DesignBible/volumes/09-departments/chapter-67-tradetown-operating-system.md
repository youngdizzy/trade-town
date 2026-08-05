# Chapter 67 — TradeTown Operating System (TTOS)

**Status:** Chapter written — target design, researched first. This
chapter is structurally different from every other chapter in this
volume: it does not describe a trading/research/risk department with
its own real backend module. It describes the *navigation and UX
architecture* that would organize all 34 of those departments' existing
Command Center surfaces into one system. Research found real, working
navigation infrastructure — a fixed Command Center overlay with two
distinct "home" screens, a global always-visible toolbar, and a scoped
non-blocking toast system — but none of TTOS's five defining mechanisms
(universal search, a command palette, 7-section grouped navigation,
dockable/saved workspaces, priority-tiered notifications) exist
anywhere in this codebase today. See
[Volume 9's chapter template](README.md) for what every section below
must contain, and the Implementation Notes at the bottom for the exact
honesty boundary between what's real today and what a future
implementation would add.

## Executive Summary

TradeTown's Command Center has grown, one honestly-scoped chapter at a
time, to 34 real tabs — OVERVIEW through LOGS — each backed by real
data and real logic. **Researched first:** that growth has outpaced its
own navigation. All 34 tabs render as one flat, horizontally-scrolling
button row with zero grouping (`FullCommandCenter.tsx`'s `TABS`
constant), there is no way to search across any of it, there is no
command palette, and the CEO's actual global one-click controls
(Save/Load/Memory/Coach/Dashboard/Command/Settings/Pause/Work Mode) are
scattered between a global bottom toolbar and individual buried tabs —
Operating Mode and Time Controls, for instance, are reachable only by
opening the Full Command Center and clicking into the COMPANY tab. TTOS
is the proposal to organize what already exists, not to build new
trading, research, or risk logic — every real feature stays exactly
where its own chapter put it; this chapter only changes how the CEO
gets there.

## Mission

Give the CEO complete situational awareness of every real, already-built
department within 30 seconds, by organizing existing Command Center
surfaces into one coherent, searchable, groupable navigation system —
never by duplicating, replacing, or re-implementing any department's
actual logic.

## Philosophy

Complex systems require simple interfaces. A flat list of 34 buttons is
not simplicity — it is unsorted completeness. Information should be
layered: a CEO glancing for ten seconds and a CEO auditing for an hour
should both find what they need, at different depths of the same
system, never in two disconnected UIs. Consistency above creativity —
this department invents no new visual language, no new interaction
pattern per feature; every department gets the same navigation
treatment.

## Responsibilities

**Owns:** Navigation (how the CEO reaches any panel), Dashboard
Architecture (what renders by default), Workspace Management (layout
persistence — not built today), Universal Search (not built today),
Command Palette (not built today), Window Management (not built
today), Notifications (the *presentation* layer only — priority
routing, not what triggers a notification), Quick Actions (a
single global one-click action surface), Information Hierarchy
(grouping/ordering of the 34 existing tabs).

**Does NOT own** (see Appendix E): Trading Logic (every panel's actual
data and decisions stay owned by their own chapter — e.g. RISK stays
Chapters 57/58's, EXECINTEL stays the Executive Intelligence Network's),
Risk Management (Chapters 57/58/66's own veto and circuit-breaker
authority is never touched by this chapter), Research (Chapters 61/62's
own systems), Execution (broker/order logic stays wherever it already
lives). TTOS never computes a trading decision, a risk limit, or a
research result — it only decides where the CEO clicks to see one.

## Ownership

Real, already-shipped navigation infrastructure this chapter does
**not** own outright but must honestly account for and would reorganize:

| Real system | What it already does | Where it lives |
|---|---|---|
| `CommandCenter.tsx` | Top-level fixed overlay; renders either Quick View or Full Command Center depending on `commandCenterMode` | `frontend/src/ui/components/CommandCenter/CommandCenter.tsx` |
| `FullCommandCenter.tsx` | The 34-tab interface — one flat, horizontally-scrolling `<nav>`, no grouping, no sections; a single `useState<Tab>` shows exactly one tab at a time (no split view) | `frontend/src/ui/components/CommandCenter/FullCommandCenter.tsx` (`TABS` constant, lines 68-103) |
| `QuickView.tsx` | A second, separate "home" screen shown by default on Tab-press — Portfolio, Market Regime, Top Opportunity, Risk Alerts, System Recommendation | `frontend/src/ui/components/CommandCenter/QuickView.tsx` |
| `OverviewPanel.tsx` | A third, distinct "home"-like screen — the default tab inside the Full Command Center, its own doc comment calling itself "the landing tab" | `frontend/src/ui/components/CommandCenter/panels/OverviewPanel.tsx` |
| `BottomToolbar.tsx` | The one real always-visible global control surface: Save/Load/Memory/Coach/Dashboard/Command/Settings/game-level Pause, plus the Work Mode toggle and save-status indicator | `frontend/src/ui/components/BottomToolbar.tsx` |
| `CyberNotifications.tsx` | Non-blocking corner toasts, 4 fixed `ToastKind`s (trade/research/volatility/alert/save) — a visual color category, not a severity tier; all auto-dismiss after 6s; nothing ever interrupts | `frontend/src/ui/components/CommandCenter/CyberNotifications.tsx` |
| Number-key tab jump (1-9) | Jumps to the first 9 tabs, but only while `FullCommandCenter` is already mounted — not a global shortcut | `FullCommandCenter.tsx`, lines 129-140 |
| `useCloseOnEscape` hook | Shared Escape-to-close behavior across every overlay | `frontend/src/ui/hooks/useCloseOnEscape.ts` |

Three "home" screens exist today (QuickView, OverviewPanel, and
implicitly the flat tab list itself as a browsing surface) that overlap
without being unified — a genuine symptom of the exact problem this
chapter exists to name.

## Inputs

TTOS needs no new *data* inputs — every real number, chart, and record
it would organize is already fetched by its own owning panel via the
existing REST/WS layer. What it needs that does not exist: a real
navigation index (which of the 34 tabs maps to which proposed
top-level section — a genuine design decision this chapter must make
explicit, not leave implicit), and, for search/command-palette to work
honestly, either a real backend search endpoint or an honestly-scoped
client-side index over already-loaded state (the same "index of what
we already have, never a new source of truth" pattern
`CompanyMemory.tsx`'s existing client-side filter already uses).

## Outputs

**Real today:** the Command Center overlay itself, the flat 34-tab
list, two overlapping "home" screens (QuickView + OverviewPanel), a
global bottom toolbar exposing 8 real one-click actions plus Work Mode,
and non-blocking, non-tiered toast notifications. **Not built:**
grouped/sectioned navigation, universal search results, command
execution, saved/dockable workspace layouts, a unified notification
center with priority tiers, a single unified Quick Action bar, and any
navigation/UX telemetry.

## Internal Workflow

**Real today:** CEO presses Tab → Command Center opens in Quick View →
CEO either reads the glance summary, presses Escape, or clicks "EXPAND
— FULL COMMAND CENTER" → Full Command Center opens on the OVERVIEW tab
→ CEO manually scans the flat, horizontally-scrolling 34-button row to
find the tab they want → clicks it → that panel fetches and renders its
own already-real data. **Genuinely not built:** any workflow where the
CEO types (a search query or a command) instead of scanning/clicking; a
workflow that opens more than one panel at once; a workflow that
remembers which panel(s) the CEO had open last session.

## Decision Logic

This chapter's only real "decision" is architectural, not
trading-related: which of the brief's 7 proposed top-level sections
(Headquarters / Markets / AI Workforce / Research / Portfolio /
Operations / Archive) each of the 34 existing tabs would belong under.
That mapping is not invented here as a byproduct — it is the single
most load-bearing design decision a real implementation would need to
make explicit and defend, since several existing tabs (e.g. TREASURY,
which is CEO-personal capital, distinct from the company's own
portfolio; CONSTITUTION, which is governance, not research or
operations) do not cleanly fit one obvious bucket. A future
implementation's Decision Logic section would need to publish this
mapping table itself, not gesture at it.

## Department Cooperation

**Would receive from:** every existing chapter — each one already owns
a real Command Center surface (a tab, a card, a widget) that TTOS would
organize but never re-implement. **Would send to:** the CEO only — one
coherent way to reach any of those 34 real surfaces, plus (if
built) a real-time feed of whichever notification-worthy events each
department already emits via EventBus. TTOS is explicitly a pure
integration layer: it has no department to send trading, research, or
risk output to, because it never produces any.

## CEO Controls

| Control | Status |
|---|---|
| Navigation grouping (7 sections) | **Not built** — all 34 tabs render flat today, no CEO-facing grouping or collapsing exists. |
| Universal Search | **Not built** — the only search anywhere in this codebase is two narrow, already-loaded-state client-side filters (`CompanyMemory.tsx`'s memory search, `KnowledgeGraphView.tsx`'s node search); neither is global, and no backend search endpoint is ever called from the frontend despite two real backend search functions existing (`app/memory.py`'s `search()`, `app/knowledge.py`'s `search_knowledge()`). |
| Command Palette | **Not built** — no "type a command, press Enter" UI exists anywhere. |
| Workspace layouts (dockable/saved) | **Not built** — the Command Center is one fixed, non-resizable, non-dockable overlay; `frontend/package.json` carries no windowing/docking library of any kind. |
| Notification priority tiers | **Not built** — `CyberNotifications.tsx`'s `ToastKind` is a color category (trade/research/volatility/alert/save), not a severity level; every toast behaves identically (auto-dismiss, non-blocking, capped to 4 visible); nothing ever interrupts today because nothing is marked as needing to. |
| Quick Action bar (Pause Trading / Emergency Stop / Resume) | **Not built as a unified surface.** The real global toolbar (`BottomToolbar.tsx`) exposes Work Mode and a game-level Pause/Resume (the sim clock, not trading specifically) — genuinely real and genuinely global. Operating Mode (Learning/Assisted/Executive) and Time Controls are real but buried inside the COMPANY tab, not global. "Emergency Stop" does not exist under any name anywhere in this codebase — Chapter 66's `pause_trading` signal is real but is computed automatically and enforced only inside the auto-resolve tick loop; it is never CEO-triggerable through any API route or button (confirmed: no pause/stop/emergency route exists in `app/main.py`). |
| Themes | **Not built as a CEO control** — the dark cyberpunk visual language is real and consistent (see Chapter 65/66's own Command Center surfacing), but it is fixed in code, not a CEO-selectable option. |
| Widget/dashboard customization | **Not built** — OverviewPanel and QuickView both show a fixed, code-defined set of cards; no CEO-facing widget picker or layout editor exists. |

## Learning System

**Not built.** No navigation/UX telemetry of any kind exists in this
codebase today — no event log of which tabs get opened, which buttons
get clicked, or how long anything takes to reach. A future
implementation's "observe frequently-used pages, recommend better
layouts" mechanism would need to be built the same evidence-based way
every other real Learning System in this Design Bible already is (see
Chapter 61's Pattern Detection Sensitivity, Chapter 64's Executive
Priority Engine) — grounded in a real, checkable click/navigation log,
never simulated or invented usage statistics.

## KPIs

**Not honestly computable today, for any of them:** Navigation Time,
Search Speed (no search exists to time), Dashboard Load Time, Feature
Discovery Rate, User Efficiency, Clicks Per Task, Workspace Usage (no
workspaces exist). None of these have any instrumentation anywhere in
this codebase — inventing a number for any of them would violate this
Design Bible's own no-fabrication rule. A future implementation would
need to build real client-side event logging before any of these KPIs
could be reported honestly.

## Reports

**Not built, for the same reason as the KPIs above:** Navigation
Analytics, Search Analytics, Workspace Usage, Dashboard Performance,
Notification History, User Activity. Zero instrumentation exists to
generate any of them today.

## Safety Systems

**Real today, narrowly:** `BottomToolbar.tsx`'s global Pause/Resume
halts the sim clock (not trading specifically); the Work Mode toggle is
a real, global, always-visible, one-click control. **Genuinely not
built:** a confirmation step before any "critical" action anywhere in
this codebase — no confirmation-dialog pattern exists for any
destructive or high-stakes CEO action (checked directly: no such
component or pattern found in `frontend/src/ui/components`); an
Emergency Stop specifically for trading (distinct from the general game
pause); an always-visible broker-status/risk-status/capital-status/
company-health strip (today, Risk Status, Company Health, and Market
Environment are all real but only shown inside OverviewPanel/QuickView,
not as a persistent global strip visible from every scene the way
`BottomToolbar.tsx` is).

## Dependencies

Every chapter in this volume that owns a real Command Center surface —
this chapter reorganizes, not replaces, all of them. Chapter 66
(Institutional Safety) specifically, for the Emergency
Stop/manual-override CEO control this chapter's Quick Action bar would
surface — that control does not exist in either chapter today and
would need to be built once, in Chapter 66's own ownership, never
duplicated here; TTOS would only ever provide the button, never the
underlying pause-authority logic.

## Connected Features

Every one of the 34 existing tabs, without exception — this chapter's
entire subject is how the CEO reaches all of them. Any future Volume 9
chapter would, per this chapter's own proposed Design Bible Integration
requirement (see Implementation Notes), need to declare where in TTOS's
navigation it lives, rather than inventing an independent menu or
overlay the way `CompanyMemory.tsx`, the Coach Dashboard, the Brain
Room HUD, and Settings currently each do (each is its own separate
overlay today, opened from `BottomToolbar.tsx`, outside the Command
Center's own tab system entirely — a second, smaller instance of the
same "independent navigation" problem this chapter's Company Principle
below argues against).

## Future Expansion

A real Command Palette and Universal Search become materially more
valuable as more chapters ship (more surfaces to search/jump to); a
real multi-workspace docking system matters more once the CEO is
routinely cross-referencing 3+ panels at once (e.g. RISK + PORTFOLIO +
EXECINTEL during a real drawdown) — none of that changes what's
buildable today, since none of it requires real market history, real
multi-asset data, or an LLM dependency this codebase does not have; it
requires only the UI/state-management work itself, deliberately not
started without an explicit implementation request (see Implementation
Notes).

## Company Principle

TradeTown should never feel like software with 34 separate features —
it should feel like one operating system, and every existing feature
already earned its place in it; this chapter's only job is to stop
making the CEO hunt for what the company already built.

## Implementation Notes

**What's real today, found by direct research before this chapter was
written (not assumed):** a real, working fixed-overlay Command Center
with 34 real, independently-shipped tabs, each backed by real backend
data (confirmed by reading `FullCommandCenter.tsx`'s `TABS` constant
and every panel file it renders); a real always-visible global toolbar
exposing 8 one-click actions plus Work Mode
(`BottomToolbar.tsx`); a real, if narrowly-scoped and non-tiered,
non-blocking toast notification system (`CyberNotifications.tsx`); two
real, narrow, already-loaded-state client-side search filters
(`CompanyMemory.tsx`, `KnowledgeGraphView.tsx`) and two real unexposed
backend search functions (`app/memory.py:search()`,
`app/knowledge.py:search_knowledge()`) that no REST endpoint currently
calls; real (if buried and not global) Operating Mode and Time Controls
inside the COMPANY tab; and a real, if partial, "landing tab" concept
split confusingly across two components (QuickView, OverviewPanel).
None of this needed to be rebuilt, and this chapter does not claim
otherwise.

**What's genuinely not built, and what a real future implementation
would need to design first (per Appendix G's Permanent Development
Policy — design before code):** the 7-section grouped navigation and
its own explicit tab-to-section mapping; a real universal search (most
honestly built first as a client-side index over already-loaded state,
the same pattern `CompanyMemory.tsx` already established, before any
new backend search endpoint is considered); a command palette; any
dockable/resizable/saved-layout workspace system (this codebase has no
windowing library today — adopting one is a real, non-trivial
dependency decision this chapter does not make unilaterally); a
priority-tiered notification center distinct from the existing toast
system; a single unified Quick Action bar (which would need Chapter 66
to first build the actual Emergency Stop / manual pause-trading control
this chapter would only ever surface, never own); CEO-facing themes and
widget customization; and any navigation/UX telemetry to honestly back
the KPIs and Reports this chapter names. Also genuinely new: the
"declare Navigation Location / Quick Actions / Search Tags /
Notifications / Dashboard Widgets" integration-contract requirement
this chapter's brief proposes for all future chapters — checked
directly against `README.md`'s current 20-item chapter template, and
confirmed this is a real, new addition (only "Dependencies," item #16,
already exists under that exact name today). The smallest honest first
slice, if implementation is requested, is almost certainly the 7-section
grouped navigation itself — a pure reorganization of the existing 34
tabs with zero new data dependencies — matching this Design Bible's own
repeated "smallest independently-useful slice first" convention (see
Chapters 61, 63, 64, and 65, all of which started with the smallest
real, checkable piece rather than the full brief at once). Universal
Search, the Command Palette, and Workspace Management are each
substantially larger, separable slices that should not be assumed to
follow automatically from an "implement" on this chapter alone.
