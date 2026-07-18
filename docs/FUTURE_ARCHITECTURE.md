# Future Architecture: Fitting Coach, Simulation Lab, Hall of Fame, Paper Trading, and Brokerage Integration Into What Already Exists

**Status:** Canonical. This document answers one question per feature:
**exactly which existing extension point does this attach to, and why
doesn't it require rewriting anything that already ships?** Every
answer below points at a real mechanism already used at least once in
the shipped v0.1–v0.3 codebase — nothing here proposes a new
architectural pattern that doesn't already have a working precedent.

The single governing precedent, cited repeatedly below: **v0.3 added
five new pieces of state (`research`, `watchlist`, `memory`,
`meetingMinutes`, and a fifth agent) to a system originally built for
one agent and no research/memory concept at all, and did it without
rewriting `nexus.py`'s orchestration shape, `EventBus`'s event model, or
`RoomScene`'s agent-presence logic.** Every feature below follows the
exact same shape of change: add a field to `GameSaveState`, broadcast it
the same way every existing field is broadcast, diff it client-side the
same way `NexusManager` already diffs everything else, and add exactly
one new manager module following the existing function-module
convention (`CODING_STANDARDS.md`).

---

## Coach (v0.5)

**What it needs:** a new agent, and a new *reading* relationship to data
that already exists.

**Why it doesn't require a rewrite:** Coach reads `CompanyMemory`
records already being written by Scribe (`future_trade` category
specifically). No new backend computation is required — `memory.search()`
already implements the filter contract Coach's review flow needs. Coach
joins the roster through the exact five-step checklist every agent
already follows (`docs/DeveloperGuide.md`'s "Adding a new agent"): an
`AgentId` union member, an `AgentProfile` entry, a schedule, dialogue
lines, and — since Coach doesn't research — it's simply *excluded* from
`RESEARCHER_IDS`, the same way Scribe already is. The only genuinely new
piece is a dialogue *shape* (questions, not statements — see
`AI_AGENT_BIBLE.md`), which is a new set of entries in
`DialogueManager.ts`'s `AGENT_TASK_LINES`, not a new dialogue mechanism.

**Concrete attachment points:**
- `backend/app/agents.py` / `frontend/.../AgentProfiles.ts` — new roster
  entry, same shape as Scribe's.
- `backend/app/schedule.py` / `frontend/.../Schedule.ts` — new schedule
  block set.
- `frontend/.../DialogueManager.ts` — new `AGENT_TASK_LINES.coach` array,
  with the question-first phrasing documented in `AI_AGENT_BIBLE.md`.
- No `schemas.py` change required unless Coach's review flow wants to
  persist which records the player has already seen — if so, one new
  optional field on `MemoryRecord` (e.g. `reviewedByCoach: bool`),
  following the exact "add an aliased field, mirror it in `types.ts`"
  pattern every existing field already uses.

## Simulation Lab (v0.6)

**What it needs:** a new room, two new agents (Quant, Lab; Oracle
overlaps here too), and — the one piece that looks new but isn't — a
second implementation of an interface that was built to have more than
one implementation from day one.

**Why it doesn't require a rewrite:** `MarketDataProvider`
(`backend/app/market_data.py`) is an `ABC` with exactly one shipped
implementation (`MockMarketDataProvider`) specifically so a second
implementation could be added later without touching any consumer.
Simulation Lab's historical-data need is *architecturally identical* to
this — a `HistoricalMarketDataProvider` implementing the same
`get_quote`/`get_quotes` interface, selected the same way
`_select_provider()` already selects the mock provider today, consumed
by the exact same `tick_watchlist()` call site `watchlist.py` already
has. `tick_watchlist()` itself never needs to know whether it's talking
to live, mock, or historical data — that's the entire point of the
adapter pattern being there in the first place.

**Concrete attachment points:**
- `backend/app/market_data.py` — new `HistoricalMarketDataProvider(MarketDataProvider)`
  class; extend `_select_provider()`'s env-var gate.
- A new room scene (`SimulationLabScene.ts`), extending `RoomScene`
  exactly like every other room — no change to `RoomScene` itself
  required, since it was already built to be extended by an arbitrary
  number of rooms.
- A new `GameSaveState` field for backtest results (e.g.
  `simulationRuns: list[SimulationRun]`), following the `research`/
  `watchlist` precedent: broadcast in `build_state_message()`, diffed in
  `NexusManager.applyServerUpdate()`, surfaced via a new `EventBus` event
  (`simulation:completed`).
- Quant/Lab/Oracle join the roster via the same five-step checklist as
  Coach, above.

## Hall of Fame

**What it needs:** nothing new at the data layer — it's a *view*, not a
new system, and its natural home is alongside Strategy Marketplace
(v0.8), since both are about surfacing what's already been recorded in
a shareable, celebratory form rather than generating new state.

**Why it doesn't require a rewrite:** by the time Hall of Fame is worth
building, `CompanyMemory` already contains everything it needs to
display: `future_trade` flags (v0.3, shipped), and — once Paper Trading
(v0.7) exists — actual paper P&L outcomes tied to those same flags via
`Ledger`'s bookkeeping records. Hall of Fame is a *read-only, ranked
presentation* of that existing data (best-calibrated agent, highest-
confidence completed research, most-successful paper positions) — no
new write path, no new NEXUS pipeline stage. It's the closest thing on
this entire roadmap to a "pure UI feature": a new modal
(`HallOfFame.tsx`, following `CompanyMemory.tsx`'s exact structure —
filter chips, a scrollable ranked list) reading data three other
features already produced.

**Concrete attachment points:**
- No backend change required beyond, optionally, a `GET
  /api/hall-of-fame`-style read endpoint if client-side ranking of the
  full history (not just the last-200-record window) proves necessary —
  same shape as the already-planned Company Memory REST search endpoint
  (`TASK_BACKLOG.md`'s N6).
- `frontend/src/ui/components/HallOfFame.tsx` — new modal, opened from
  `BottomToolbar.tsx` exactly like Company Memory is today.
- Ranking logic is pure client-side computation over already-synced
  data, no new `EventBus` event required unless real-time rank changes
  need their own notification.

## Paper Trading (v0.7)

**What it needs:** the first genuinely new *pipeline stage* in
`nexus.tick()` since v0.3's research/meeting stages — but still just
another stage in the same ordered call chain, not a parallel system.

**Why it doesn't require a rewrite:** `nexus.tick()` is already an
ordered sequence of pipeline stages (tick agents → tick research → tick
watchlist → maybe call a meeting → roll market news — see
`NEXUS_ARCHITECTURE.md`'s System Overview diagram). Paper Trading adds
one more stage, after the research pipeline, exactly the same shape as
every existing stage: take the current state, apply a deterministic
transformation, return updated data, thread it through to the final
`state.model_copy(update={...})` call the same way `research`,
`watchlist`, and `memory` already are. Ledger (the new agent) owns this
stage's logic, following the exact `scribe.py`/`memory.py` split
already in place — Ledger's module holds the domain logic
(`open_paper_position()`, `close_paper_position()`, following
`record_research_completions()`'s shape), and writes into `CompanyMemory`
through the same `record()` gateway every other write already goes
through, under a new category.

**Concrete attachment points:**
- `backend/app/ledger.py` (new) — mirrors `scribe.py`'s structure:
  pure functions taking a ledger list and returning an updated one.
- `schemas.py` — a new `PaperPosition` model and a `ledger:
  list[PaperPosition]` field on `GameSaveState`, following the exact
  `Field(default_factory=list)` pattern every list field already uses.
- `nexus.tick()` — one new call between the research pipeline and the
  meeting pipeline: `ledger = tick_ledger(ledger, research, watchlist,
  ...)`.
- `MemoryCategory` (`schemas.py`) already anticipates this — the
  `future_trade` category exists specifically as the upstream signal
  Paper Trading consumes; no new memory-category plumbing needed beyond
  adding whatever category Ledger's own records use.
- Frontend: a new `PaperLedger.tsx` component (or a new `BrainRoomHud.tsx`
  section, per `UI_UX_BIBLE.md`'s visual-hierarchy rules) plus the usual
  `EventBus` event (`ledger:updated`) and `NexusManager`/`gameStore.ts`
  wiring, identical in shape to how `watchlist:updated` was added in
  v0.3.
- **The boundary that makes this safe**: Paper Trading's pipeline stage
  never calls anything resembling a brokerage adapter, because no such
  adapter exists in the codebase until v1.0 is separately authorized.
  There is no flag to check and no code path to disable — the
  capability to place a real order simply isn't present, which is a
  stronger guarantee than a runtime check would be.

## Brokerage Integration (v1.0, gated)

**What it needs:** a second adapter interface, structurally identical to
`MarketDataProvider`, plus — unlike every other feature in this document
— a deliberate, separate authorization step before any of its code is
written at all.

**Why it doesn't require a rewrite:** the shape is, again, the adapter
pattern. A new `TradeExecutionProvider` `ABC` (`get_positions()`,
`place_order()`, `cancel_order()`, mirroring `MarketDataProvider`'s
`get_quote()`/`get_quotes()` shape) would sit next to `market_data.py`
as `execution.py`, selected via the same `_select_provider()`-style env-
var gate, called from a *new*, clearly-labeled pipeline stage that is
structurally separate from `tick_ledger()`'s paper-only stage — Paper
Trading's code does not become live-trading code by flipping a flag; a
brokerage-backed order flow is new code, written new, at v1.0, that
happens to reuse Paper Trading's UI patterns and Ledger's
record-keeping shape for consistency, not its execution logic.

**Concrete attachment points (all deferred until v1.0 authorization):**
- `backend/app/execution.py` (new) — `TradeExecutionProvider` ABC.
- Guardian (the agent) becomes the in-code, not just in-fiction,
  enforcement point: every call into a real `TradeExecutionProvider`
  implementation passes through a Guardian-owned confirmation/audit
  function first — see `AI_AGENT_BIBLE.md`'s Guardian entry and
  `KNOWN_LIMITATIONS.md`'s note that credential storage security is a
  research question, not a solved pattern, at v1.0's start.
- The double-confirmation UX (`TASK_BACKLOG.md`'s T16) is a new,
  dedicated modal — not a checkbox bolted onto the existing Paper
  Trading UI, specifically so the two experiences never look similar
  enough to confuse.
- **This is the one feature in this document that is *not* simply "add
  a field and wire it through."** Every other feature above reuses
  `nexus.tick()`'s existing orchestration shape by design. Brokerage
  Integration deliberately does not get a shortcut: it is scoped,
  authorized, and reviewed as its own architectural decision when v1.0
  actually starts, per `ROADMAP.md`'s explicit stop condition on that
  version. This document describes *where it would attach if
  authorized* — it is not the authorization itself.

---

## The Pattern, Stated Once

If a future feature can be described as "add a field to
`GameSaveState`, add a manager module that transforms it, add a pipeline
stage to `nexus.tick()`, broadcast it, diff it, add an `EventBus` event,
add a UI component" — it fits the existing architecture and this
document's job is done. If a future feature *can't* be described that
way (Brokerage Integration is the only one on this list that can't, and
only because of its authorization gate, not its technical shape), that's
the signal it needs its own architecture document before it needs any
code — the same way this document exists before any of Coach, Simulation
Lab, Hall of Fame, or Paper Trading has a single line written.
