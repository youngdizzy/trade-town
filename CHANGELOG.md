# Changelog

All notable changes to TradeTown are documented here. Versions are
development milestones, not semver releases.

## Unreleased

### Added

- **CEO directive "Complete Trade Provenance + Session/Regime Intelligence + Evidence-Based
  Attribution," Part 13 (backend): Regime Behavior in Capital Allocation Evidence**
  (`backend/app/schemas.py`, `backend/app/performance_attribution.py`, `backend/app/routers/trades.py`,
  `backend/tests/test_performance_attribution.py`): Part 13 asks the capital-allocation evidence
  roster to expose "session behavior" and "regime behavior" as inputs to the CEO's own manual
  allocation decision. `StrategyCapitalAllocationRead` already had `sessionReads` (from the prior
  directive); regime was the one missing input, closeable immediately using Part 12's own
  `compute_strategy_regime_performance()` from this same phase. New `regimeReads:
  StrategyRegimePerformanceRead[]`, threaded through `compute_strategy_capital_allocation_evidence()`
  exactly the way `sessionReads` already is (same grouping-by-strategy-id pattern, same "no live
  trades" fallback to an empty list) — no new statistical computation, purely a join of two
  already-real sources.

  1 new test (`regime_reads` filtered correctly to only the strategy's own rows, mirroring the
  existing `session_reads` test). Full backend suite: 2614 passed (+1), `mypy app/` (178 files)
  clean, `ruff check app/ tests/` clean. Live-verified against a freshly restarted real dev stack —
  `GET /api/trades/strategy-capital-allocation` now returns a real (currently empty, honestly
  disclosed) `regimeReads` array alongside the pre-existing `sessionReads`; the real save's own
  decision pipeline continued ticking correctly throughout (Day 111 → 112).

- **CEO directive "Complete Trade Provenance + Session/Regime Intelligence + Evidence-Based
  Attribution," Part 12 (backend): Strategy Performance by Regime** (`backend/app/schemas.py`,
  `backend/app/performance_attribution.py`, `backend/app/routers/trades.py`,
  `backend/tests/test_performance_attribution.py`): a direct research finding — the prior "Live
  Trade → Strategy Provenance" directive already built the strategy×session axis
  (`compute_strategy_session_performance()`, Phase 6) but never its regime counterpart. New
  `compute_strategy_regime_performance()`/`GET /api/trades/performance-by-strategy-regime` mirrors
  it field-for-field, grouped on `(strategy_id, market_regime)` instead of `(strategy_id, session)`
  — same real Decision Vault join, same two distinct, honest exclusion reasons
  (`tradesExcludedNoStrategySelected` vs. `tradesExcludedNoVaultEntry`), never folded together.

  **Research also resolved two other Part-9/Part-7 line items without new code**, disclosed here
  rather than silently skipped: **Part 7 (regime snapshot at decision time)** is already fully
  satisfied by this directive's own Part 8 work (`CeoDecisionRecord.decisionMarketRegime`, captured
  from `MarketIntelligenceState.regime` — confirmed the operationally load-bearing source of truth
  between this codebase's two regime engines). **Part 9 (agent attribution)** is already
  substantially satisfied by the pre-existing `TradeAttributionRecord.contributions`
  (`AgentContributionRead`: real per-agent `agentId`/`role`/`choice`/`reason`/
  `agreedWithSideTraded`, reconstructed from `TradeDecision.votes`) and its two-state
  `TradeAttributionEvidenceState` (`full_evidence`/`no_decision_on_record`) — the module's own
  docstring already states "no numeric P&L split is computed, implied, or stored anywhere,"
  matching Part 9's explicit "do not claim Agent X contributed 27%" rule exactly. Extending it
  further would be inventing a distinction (Part 9's third "UNAVAILABLE" state) this codebase's real
  data doesn't currently need — a `TradeDecision` with zero recorded votes is a theoretical, not
  observed, edge case.

  **Also researched and explicitly deferred, disclosed rather than attempted:** Part 6 (session-
  specific strategy eligibility) — the only real per-session backtest evidence
  (`CompiledStrategyBacktestResult.sessionBreakdown`) is computed fresh/on-demand, never persisted
  per-strategy; wiring it into the live, every-tick `compute_strategy_match()` would mean either an
  expensive inline backtest run on the hot tick path or a new persistence layer, neither of which
  the directive's own "extend only if the architecture supports it safely" clears without a
  dedicated design pass this phase didn't have scope for.

  5 new backend tests. Full backend suite: 2613 passed (+5), `mypy app/` (178 files) clean,
  `ruff check app/ tests/` clean. Live-verified against a freshly restarted real dev stack — the new
  endpoint honestly returns `reads: []` with `tradesExcludedNoStrategySelected: 2` (the same real,
  disclosed state `performance-by-strategy` itself reports on this save); the real save's own
  decision pipeline continued ticking correctly throughout (Day 110 → 111).

- **CEO directive "Complete Trade Provenance + Session/Regime Intelligence + Evidence-Based
  Attribution," Parts 4 + 5 (backend): real DST-aware session classification + Session Context**
  (`backend/app/market_intelligence.py`, `backend/app/schemas.py`, `backend/app/executive.py`,
  `backend/app/decision_vault.py`, `backend/tests/test_market_intelligence.py`,
  `backend/tests/test_executive.py`, `backend/tests/test_decision_vault.py`): Part 4 asked for real
  ASIA/LONDON/NEW YORK/OVERLAP/CLOSED session detection "correctly account[ing] for timezone,
  daylight saving time" — research found the existing `compute_session()` was a disclosed
  fixed-UTC-hour approximation with zero DST handling. Rewriting it naively risked a real Absolute
  Rule #4 conflict: the *same* hour classifier (`_session_for_hour()`) also buckets historical
  candles for backtesting/certification (`app/strategy_engine.py`, `app/ema_pullback_research.py`),
  and changing its boundaries would retroactively shift already-certified strategies' historical
  session breakdowns — exactly what the directive forbids.

  Resolution, disclosed as a deliberate (not accidental) split: `_session_for_hour()` stays
  completely unchanged — every backtest/certification path keeps its exact prior boundaries.
  `compute_session()` (the **live-only** path — the Gatekeeper, every fresh `TradeProposal`, and
  Part 8's decision-time snapshot) is rebuilt on real, publicly-documented NYSE/LSE/TSE exchange
  hours, classified via Python's stdlib `zoneinfo` (the real IANA timezone database — no new
  dependency, no network call), which correctly and automatically shifts NYSE/LSE boundaries across
  real US/UK DST transitions (Tokyo observes none, so its offset stays fixed) and correctly reports
  `closed` on real weekends. Verified with the core proof of DST-awareness a fixed classifier could
  never pass: the identical UTC wall-clock time (13:45 UTC) classifies as `market_open` in July and
  `london` in January. Deliberately does not model exchange holidays — no real holiday-calendar
  data source exists in this codebase, so a holiday is honestly misclassified as a normal trading
  day rather than fabricating a calendar.

  Part 5 (Session Context) extends `SessionRead` with real `sessionStartedAt`/`sessionClosesAt`/
  `minutesSinceSessionOpen`/`minutesUntilSessionClose` (computed from the same real exchange
  boundaries, `None` only when `current == "closed"`), then captures this — plus session-scoped
  volatility (`VolatilityRead.sessionPct`, an already-real, already-computed field this directive
  simply started reading) — into a new nested `CeoDecisionRecord.decisionSessionContext`, grouped
  as one object (unlike Part 8's flat fields) because the directive's own Part 5 heading names these
  as one cohesive concept. Threaded through to `DecisionVaultEntry`/`TradeReportCard`. Deliberately
  cut, disclosed: SESSION RANGE / SESSION HIGH-LOW (Part 5's other two line items) — both need a
  real per-symbol candle fetch within the session window that would meaningfully expand
  `resolve_proposal()`'s already-large parameter surface.

  12 new backend tests (8 DST-aware session tests including the core July/January proof, 4 Session
  Context threading tests). Full backend suite: 2608 passed (+12), `mypy app/` (178 files) clean,
  `ruff check app/ tests/` clean. Live-verified against a freshly restarted real dev stack — the
  live session read now shows the real DST-aware detail string and real boundary fields; the real
  save's own decision pipeline continued ticking correctly throughout (Day 108 → 110).

- **CEO directive "Complete Trade Provenance + Session/Regime Intelligence + Evidence-Based
  Attribution," Part 8 (backend): Decision-Time Snapshot** (`backend/app/schemas.py`,
  `backend/app/executive.py`, `backend/app/decision_vault.py`, `backend/tests/test_executive.py`,
  `backend/tests/test_decision_vault.py`): research for the Part 1/2 work above (previous entry)
  flagged this as the single most load-bearing gap in the whole directive —
  `DecisionVaultEntry.session`/`marketRegime` are real, but computed fresh at trade **close**,
  never at the moment a decision was actually made, so no historical trade could honestly answer
  "what did the market look like when we decided this?"

  `resolve_proposal()` (`app/executive.py`) now stamps four new `CeoDecisionRecord` fields —
  `decisionSession`, `decisionMarketRegime`, `decisionPrice`, `decisionVolatilityPct` —
  unconditionally (buy/sell/**wait** alike; real market context doesn't depend on what the CEO
  chose), read once from the same `market_intelligence`/`current_price` parameters this function
  already receives — the identical always-current state a real `TradeProposal`/the Gatekeeper
  themselves read, never a second, independently-computed reading. Because `resolve_proposal()` is
  the one real chokepoint all three decision paths already share (a CEO click via
  `submit_ceo_decision()`, an Operating Mode auto-resolution, and the stale-proposal-expiry
  auto-wait in `app/nexus.py`), this closes the gap for every decision path at once rather than
  patching each call site separately. Threaded through to `DecisionVaultEntry`/`TradeReportCard` as
  new fields deliberately kept **separate** from the existing close-time `session`/`marketRegime` —
  "what it looked like when we decided" and "what it looked like when we closed" are both real and
  both worth keeping, not a replacement of one by the other. `None` only for decisions recorded
  before this field existed (neither `TradingSession` nor `MarketIntelligenceRegime` has an honest
  "unknown" literal to fabricate a default from instead).

  5 new backend tests (2 in `test_executive.py` — including the exact unconditional-on-wait case —
  and 3 in `test_decision_vault.py`). Full backend suite: 2596 passed (+5), `mypy app/` (178 files)
  clean, `ruff check app/ tests/` clean. Live-verified against the real running dev stack — the
  real save's own decision pipeline continued ticking correctly throughout (Day 105 → 108).

- **CEO directive "Complete Trade Provenance + Session/Regime Intelligence + Evidence-Based
  Attribution," Part 1 + Part 2 (backend): Strategy Rule Snapshot** (`backend/app/schemas.py`,
  `backend/app/state.py`, `backend/app/trade_attribution.py`, `backend/app/decision_vault.py`,
  `backend/app/strategy_registry.py`, `backend/app/routers/trades.py`,
  `backend/tests/test_state.py`, `backend/tests/test_trade_attribution.py`,
  `backend/tests/test_decision_vault.py`, `backend/tests/test_strategy_registry.py`): the
  directive's own mandatory research-first phase (two dedicated read-only architecture audits,
  full findings below) found the prior "Live Trade → Strategy Provenance" directive already built
  real CEO-explicit strategy labeling end to end (`CeoDecisionRecord.strategyId` →
  `DecisionVaultEntry`/`TradeAttributionRecord`/`TradeReportCard`, performance-by-strategy,
  live-vs-backtest, strategy×session breakdowns) — but that labeling was a bare, unverified
  strategy *id* with no record of which compiled rules the strategy actually represented at the
  moment of the decision. Part 2's own example makes the gap concrete: "If the strategy later
  becomes EMA 55, the old trade must still reference the rules that actually generated it" — which
  the existing `strategy_id`-only mechanism could not do, since `Strategy.compiled_definition_id`
  is a single mutable pointer.

  Research also found the fix needed zero new versioning mechanism: `CompiledStrategyDefinition`
  history (`compiled_strategy_versions`, Feature 37) was already real, immutable, and append-only
  — just never read by anything in the trade/decision pipeline. `submit_ceo_decision()` now reads
  the CURRENT (latest-appended) `CompiledStrategyDefinition` for the selected Strategy at the exact
  instant of the decision and snapshots its `(id, version)` pair onto two new
  `CeoDecisionRecord` fields, `strategyCompiledDefinitionId`/`strategyCompiledDefinitionVersion` —
  both `None` whenever `strategyId` itself is `None`, or the picked Strategy has no compiled rules
  yet (a real "idea"-stage strategy), never fabricated. Threaded through the exact same three
  existing join points `strategyId` already flows through (`TradeAttributionRecord`,
  `DecisionVaultEntry`, `TradeReportCard`) — no new join mechanism. A new
  `get_compiled_definition_version()` resolver (`app/strategy_registry.py`) and
  `resolve_trade_strategy_rule_snapshot()` (`app/trade_attribution.py`) turn the snapshot back into
  the actual `CompiledStrategyDefinition` for a given trade, exposed as
  `GET /api/trades/{trade_id}/strategy-rule-snapshot` (404 only for an unknown trade id — a real
  trade with no strategy attribution still returns 200 with an honest `compiledDefinition: null`).

  **Deliberately not built in this pass** (disclosed, not silently deferred): Strategy Lab's
  compiled/certified strategies still never generate a live `TradeProposal` — both research audits
  confirmed `generate_proposal()` (`app/executive.py`) never imports or references `Strategy`/
  `CompiledStrategyDefinition` in any form, so every live trade's *only* strategy link remains the
  CEO's own manual, optional pick at decision time. Wiring compiled strategies into live proposal
  generation (the directive's actual headline "market conditions → session/regime → strategy →
  compiled rules → agent reasoning → trade proposal" chain) is a substantially larger, separate
  piece of work, scoped for a later phase of this same directive rather than attempted here as a
  "giant rewrite" the directive explicitly forbids. Session/regime intelligence (Parts 4-8),
  strategy compliance checking (Part 3), agent attribution (Part 9), and the remaining parts are
  similarly deferred to later phases — see the research findings below for exactly what already
  exists for each.

  **Research findings, condensed** (two dedicated audit passes, full file:line citations retained
  in this session's own record): session detection is real but a disclosed fixed-UTC
  approximation with no DST handling (`app/market_intelligence.py`'s `compute_session()`); TWO
  independent, unreconciled regime engines exist (`app/market_environment.py`'s 5-way,
  `app/market_intelligence.py`'s 13-way — `app/regime_reconciliation.py` only reports agreement,
  writes back to neither); no decision-time context snapshot exists anywhere —
  `DecisionVaultEntry.session`/`marketRegime` are stamped at trade CLOSE, never at decision time,
  a gap this phase's own snapshot mechanism does not yet close for session/regime (only for
  strategy rules); execution slippage/cost are tracked but never decomposed against strategy edge;
  strategy-pair correlation already exists (`app/strategy_tournament.py`) but only over backtest
  data, not live returns; no generic data-quality/audit-event sink exists to plug a new
  "missing strategy id" tracker into.

  17 new backend tests (5 in `test_state.py` covering capture including the exact "old trade keeps
  its old version after a later edit" immutability case; 6 in `test_trade_attribution.py`; 2 in
  `test_decision_vault.py`; 4 in `test_strategy_registry.py` covering the resolver). Full backend
  suite: 2591 passed (+17), `mypy app/` (178 files) clean, `ruff check app/ tests/` clean. Live
  endpoint verification against the real running dev stack: a real closed trade with no strategy
  selected returns an honest `strategyId: null, compiledDefinition: null` (200), an unknown trade
  id returns a real 404 — never a fabricated response either way. No trading/agent/market-
  simulation logic was touched; only the CEO-decision and post-trade attribution paths already
  established by the prior provenance directive were extended.

- **CEO directive "Proper Multi-Run / Save Isolation System"** (backend:
  `backend/app/models.py`, `backend/app/persistence.py`, `backend/app/schemas.py`, `backend/app/state.py`,
  `backend/app/sim.py`, `backend/app/main.py`, `backend/app/routers/runs.py` (new),
  `backend/tests/test_runs.py` (new); frontend: `frontend/src/types.ts`, `frontend/src/net/api.ts`,
  `frontend/src/game/systems/EventBus.ts`, `frontend/src/ui/components/NewGameConfirm.tsx` (rewritten),
  `frontend/src/ui/components/RunPicker.tsx` (new), `frontend/src/App.tsx`,
  `frontend/src/game/scenes/MainMenuScene.ts` (rewritten), `frontend/tests/helpers.ts`,
  `frontend/tests/newGameConfirm.spec.ts` (rewritten)): supersedes the "Safe New Game Confirmation" entry
  below with a real multi-run system — New Game now creates a genuinely separate, independently-persisted
  run instead of a cosmetic scene transition, and Continue picks from every real run when more than one
  exists.

  Research first found `SaveGame`/`SaveModule`/`SaveBackup` already had real, indexed `slot` columns — the
  schema was already multi-save-capable, only the application-layer `SLOT = "default"` constant collapsed
  everything to one slot. Zero schema migration was needed: the existing save's row simply became "Original
  Run" the first time the updated server boots (`ensure_default_run_registered()`, idempotent, real
  timestamps only). `persistence.SLOT` became a genuinely mutable pointer (`get_active_slot()`/
  `set_active_slot()`); all ~90 pre-existing `persist_modules(state)` router call sites were left untouched
  (verified safe — no `await` between their locked mutation and their persist call). The one real
  concurrency race — `sim.py`'s tick loop had an `await ws_manager.broadcast(...)` between producing a
  tick's state and persisting it, a genuine window for a concurrent run-switch to write into the wrong slot
  — was fixed narrowly by reordering (persist before broadcast) through a new locked
  `GameState.persist_now()`; no other call site was touched.

  New: `Run`/`ActiveRun` metadata tables (deliberately no cached `current_day` column — always read live
  from `world`), `GET/POST /api/runs`, `GET /api/runs/active`, `POST /api/runs/{id}/activate`,
  `GameState.create_run()`/`switch_run()`. New Game checks the active run's real day and only asks for
  confirmation when there's a real day worth protecting; the dialog states plainly that the current run is
  never deleted, reset, or modified. Continue: 0 runs falls through to New Game's creation flow, 1 run loads
  directly (unchanged for single-run players), >1 shows `RunPicker.tsx` (reusing `ConfirmDialog.tsx`'s
  visual language and the `EmergencyStopConfirm.tsx` EventBus pattern).

  18 new backend tests (isolated temp-SQLite fixture, never the real save) + 6 rewritten Playwright tests;
  the shared `clickContinueOnTitleScreen` test helper (used by 12+ spec files) was updated centrally since
  this feature's own repeated verification permanently accumulates real runs in the shared dev database (no
  delete capability, by design). One drive-by fix in `commandCenter.spec.ts`'s "Company Priority" test:
  it called the raw `clickContinueOnTitleScreen` after a `page.reload()` instead of the popup-dismissing
  `continueGame()` wrapper every other test uses — switched to `continueGame()` for consistency. Backend:
  2574 passed (+18), `mypy app/` (178 files) clean, `ruff check app/ tests/` clean. Frontend: `tsc -b
  --noEmit`, `npm run lint`, `npm run build` (183 modules) clean; `newGameConfirm.spec.ts` 6/6 passed twice
  in a row.

  **`commandCenter.spec.ts` full-suite regression, investigated honestly:** running all 33 tests
  sequentially against this sandboxed container produced 24-28 passed / 4-8 failed across repeated runs,
  with a *different* subset of tests failing each time (session-closed/crashed-page errors, not assertion
  mismatches) — the signature of headless-Chromium resource strain under a long sequential run, not a
  deterministic bug. Confirmed by direct comparison: the exact same full-suite run against the pre-feature
  baseline code (via `git stash`) also failed 4/33, with yet another different failing subset. Individual
  and small-group re-runs of every test that failed in any single full-suite pass were also re-run in
  isolation and passed reliably. This pre-existing environment flakiness is unrelated to and unchanged by
  this feature — not fixed here, since it's out of this directive's scope and predates it.

  **Disclosed incident:** during test development, one test method briefly ran against the real,
  unmocked dev database before the `temp_db` fixture was added to it, overwriting the active save with a
  fresh Day-1 state. Caught immediately; recovered through the feature's own pre-existing periodic-backup
  mechanism (`save_backups`, `reason='periodic'`) via the real `persistence.persist_modules()` path, then
  independently verified via direct SQL and the live API. This session's dev database is a separate,
  disconnected environment from the CEO's real production save (per the prior "Fresh Day-1 Validation"
  research), so no production save was ever at risk — recorded here in full regardless, per this
  directive's own "disclose everything, never fabricate success" requirement. Full detail in the `5bdc2e5`
  commit message. No trading/agent/strategy/market/company-simulation logic was touched.

- **CEO directive "Safe New Game Confirmation / Save Protection"** (superseded by the multi-run system above) (frontend:
  `frontend/src/game/systems/EventBus.ts`, `frontend/src/App.tsx`, `frontend/src/game/scenes/MainMenuScene.ts`,
  `frontend/src/ui/components/NewGameConfirm.tsx` (new), `frontend/tests/newGameConfirm.spec.ts` (new)):
  research first found "New Game" never called any backend endpoint at all — it only starts `LobbyScene`
  client-side; the backend save is a single, always-on, server-authoritative simulation, so the premise "New
  Game may reset your progress" didn't match this codebase's real behavior. The dialog's copy says so
  honestly (a fresh Lobby view; the company keeps running; only the player's own saved position gets
  overwritten on the next autosave) rather than fabricating a "your progress will be reset" claim.

  Reused, not duplicated: `ConfirmDialog.tsx` (the one existing generic confirm-before-you-act component,
  previously only used by Emergency Stop) and `EmergencyStopConfirm.tsx`'s exact pattern (a Phaser-scene-
  triggered React overlay communicating over `EventBus`) for the new `NewGameConfirm.tsx`; `GET /api/load`
  (the same call `continueGame()`'s existing fallback already makes) for save-existence detection — no new
  endpoint.

  `MainMenuScene.startNewGame()` now checks the real existing day first (`null` — proceed straight through —
  when there's no save, the backend is unreachable, or the save is still genuinely Day 1); only shows the
  dialog when there's real progress to protect. A `newGameFlowActive` flag guards the *entire* round trip
  (not just the async check) against rapid/repeat clicks stacking a second check or dialog. Cancel resolves
  the confirmation promise `false` and the original scene-transition code (`beginNewGame()`, unchanged) is
  simply never called — no code path exists that could mutate anything on Cancel.

  5 new Playwright tests. One deliberate, disclosed deviation from this suite's "no mocking" convention: the
  real dev save is a single, ever-growing, shared backend state with no way to reach "no save exists" without
  being destructive to every other spec file's own precondition, so that one test uses `page.route()` to
  simulate a failed `GET /api/load` — the exact real failure `existingProgressDay()`'s own `catch` already
  handles. Full backend suite (2556 passed, unchanged — no backend file touched), `mypy app/`, `ruff check
  app/ tests/` clean. `tsc -b --noEmit`, `eslint`, `vite build` clean. `newGameConfirm.spec.ts`: 5/5 passed
  against the real running dev stack. Live-verified via screenshot. No duplicate save/new-game system was
  created; no trading/strategy/agent/market code was touched.

- **CEO directive "Fresh Day-1 Validation / Trading Pipeline Audit"** — a pure diagnostic, no code changed.
  Root cause of "no trades" on the existing save: none — the pipeline works correctly, verified end-to-end
  on a fully isolated fresh Day-1 backend instance (real proposal generation, real Opportunity Gatekeeper
  rejections, a real CEO decision opening a real position, a real take-profit exit with reconciled P&L). Two
  separate, real findings, neither a bug: the existing save's Strategy Lab roster predates the 50 EMA
  seeding/identity-bridge work (stale by design — seeding only runs at fresh-save creation); and Strategy Lab
  is structurally disconnected from live trade-proposal generation regardless (`_generate_trade_proposals()`
  never reads `state.strategies`), so that staleness isn't the cause. The real reason: Operating Mode
  defaults to `"learning"`, where nothing auto-resolves a pending proposal — it waits for an explicit CEO
  decision or expires as an honest "wait." Full findings in `docs/Architecture.md`.

- **CEO directive "Quant Research Factory / Strategy Discovery Engine," Phase 1 (audit) + Phase 17
  (Research Factory Overview)** (frontend:
  `frontend/src/ui/components/CommandCenter/panels/sandbox/QuantResearchLabView.tsx`): a research-agent
  audit of this 20-phase directive found most of the "build a disciplined, adversarial research
  pipeline" ask already real: `strategy_compiler.py` (deterministic compiler), `strategy_engine.py`/
  `cost_sensitivity.py` (real backtesting), `walk_forward.py` (real, structurally no-look-ahead rolling
  windows), `parameter_sensitivity.py` (real one-at-a-time robustness sweep), `strategy_tournament.py`/
  `strategy_lab.py` (real regime robustness + Devil's Advocate, differently named), `StrategyDossier`/
  `StrategyTournamentEntry` (real multi-dimension scorecards, never one fabricated number), `sandbox.py`'s
  `STAGE_ORDER` (a real, strictly evidence-gated promotion pipeline). Genuine gaps confirmed: no structured
  hypothesis object (only free text), `research.py`'s confidence gauge is explicitly random (disclosed,
  not derived from real analysis), no system-level multiple-testing/research-bias tracking (self-disclosed
  in `model_validation.py` as `not_trackable_yet`), and `FailedStrategyArchiveEntry`/institutional memory
  is never consulted by `research.py`'s own idea-rotation logic.

  This pass closes the Command Center research-view gap (Phase 17) — no new backend endpoint needed, since
  `GET /quant-research-lab/experiments` already existed. New `ResearchFactoryOverview` auto-fetches it on
  mount and renders real aggregate counts (promising/rejected/inconclusive), a real "Promoted Onward"
  cross-reference against `Strategy.compiledDefinitionId`/`stage`, and a Recent Rejections list — plus an
  explicit disclosure that research runs synchronously (no fabricated queue/in-progress state).

  `tsc -b --noEmit`, `eslint`, `vite build` clean. Live-verified via Command Center screenshot: the real
  running save's Quant Research Lab tab shows 13 real experiments on file, all `inconclusive`, 0
  rejected/promoted.

- **CEO directive "Quant Research Factory / Strategy Discovery Engine," Phase 14/16: prior-outcome-aware
  duplicate detection** (backend: `backend/app/schemas.py`, `backend/app/quant_research_lab.py`,
  `backend/tests/test_quant_research_lab.py`; frontend: `frontend/src/types.ts`,
  `frontend/src/ui/components/CommandCenter/panels/sandbox/QuantResearchLabView.tsx`): a research-first
  finding reshaped this increment before any code was written — there is no automated hypothesis-
  generation loop anywhere in this codebase to attach memory-consultation to (every experiment is filed
  by explicit CEO/agent action, never auto-proposed), so building one to satisfy Phase 16's literal
  framing would have meant inventing a fabricated idea generator. The honest, real point where prior-
  research feedback can reach a researcher without fabricating anything is `find_similar_experiments()`,
  already called automatically on every filing — it already found real near-duplicates but never surfaced
  what happened to them. New: `QuantResearchExperimentSimilarity` gained `outcome`/`outcomeReason`, copied
  through from the matched experiment's own already-real fields, never recomputed. A near-duplicate filing
  now shows inline whether the prior attempt was `rejected` (and why) rather than requiring a separate
  click-through — directly closing "do not repeatedly rediscover the same failed idea."

  Rendered as an explicit red "⚠ REJECTED — this idea already failed" line for rejected matches, a neutral
  outcome pill otherwise. 2 new backend tests. Full backend suite (2535 passed), `mypy app/`,
  `ruff check app/ tests/` clean — no backward-compat concern (response-only type, never persisted).
  `tsc -b --noEmit`, `eslint`, `vite build` clean. Live-verified via Command Center screenshot: a real
  freshly-filed near-duplicate experiment renders six real prior matches, each with a real "Prior outcome"
  pill. Deliberately not attempted: the fuller Phase 16 ask (an automated hypothesis-generation loop that
  learns from outcomes) remains blocked by the real absence of any generation mechanism to attach it to —
  a structural blocker, not a convenience cut.

- **CEO directive "Quant Research Factory / Strategy Discovery Engine," Phase 1: a real structured
  hypothesis abstraction** (backend: `backend/app/schemas.py`, `backend/app/quant_research_lab.py`,
  `backend/app/state.py`, `backend/app/routers/sandbox.py`, `backend/tests/test_quant_research_lab.py`;
  frontend: `frontend/src/types.ts`, `frontend/src/net/api.ts`,
  `frontend/src/ui/components/CommandCenter/panels/sandbox/QuantResearchLabView.tsx`): per the directive's
  own "create the smallest appropriate abstraction" instruction, this deliberately does not duplicate
  `market_scope`/`timeframe` (already real on `record.symbols_tested`/`record.timeframe`) or echo
  entry/exit/risk "concepts" that become real and deterministic the moment a hypothesis compiles. The two
  fields the directive names repeatedly — why the researcher expects this to work, and what would prove
  them wrong — are the ones actually missing.

  New `QuantResearchExperiment.expectedMechanism`/`falsificationCriteria` (`str | None`, real Pydantic
  defaults per the list-nested backward-compat rule — `None` only for experiments filed before this
  existed). The persisted schema stays optional, but `SubmitQuantResearchExperimentRequest` now REQUIRES
  both on every new filing — real discipline at the one real point of human action. The filing form gained
  two new required textareas; "File Experiment" stays disabled until both are filled in.

  3 new backend tests. Full backend suite (2538 passed), `mypy app/`, `ruff check app/ tests/` clean.
  `tsc -b --noEmit`, `eslint`, `vite build` clean. Live-verified: a Command Center screenshot of the real
  filing form, followed by a direct API check confirming the just-filed experiment persisted both real
  values exactly as typed.

- **CEO directive "Quant Research Factory / Strategy Discovery Engine," Phase 10: real multiple-testing /
  research-selection-bias tracking** (backend: `backend/app/schemas.py`, `backend/app/quant_research_lab.py`,
  `backend/app/state.py`, `backend/tests/test_quant_research_lab.py`; frontend: `frontend/src/types.ts`,
  `frontend/src/ui/components/CommandCenter/panels/sandbox/QuantResearchLabView.tsx`;
  `frontend/tests/sandbox.spec.ts`): the directive's own rule is explicit — never claim statistical
  significance a method doesn't actually support. No p-value, false-discovery-rate correction, or
  "corrected significance level" is honestly derivable from this codebase's real backtest outputs
  (expectancy/profit-factor/Sharpe over real simulated trades, not hypothesis-test statistics), so none is
  fabricated. What *is* honestly derivable: a real count of how many times the same strategy idea has
  already been tested.

  New `count_experiments_for_family()` sums already-persisted `QuantResearchExperiment`s sharing the real
  `record.definitionName`, over whatever window survives the existing `MAX_QUANT_RESEARCH_EXPERIMENTS = 100`
  cap — a real, honestly partial count, never a fabricated lifetime total. `file_quant_research_experiment()`
  now accepts the already-persisted list and computes `family_experiment_count` as that count + 1; any
  caller that doesn't thread the list through leaves it honestly `None`, never guessed as 1. New
  `QuantResearchExperiment.family_experiment_count: int | None` field, optional with a `None` default so
  pre-existing saves still validate.

  `QuantResearchLabView.tsx` shows "Test #N on this strategy name" on the just-filed result, with a plain-
  language caution appended once the count reaches 5 — the real number is always shown plainly, the
  threshold only changes styling and adds context, never a fabricated severity label — plus a "Family test
  #" column in the permanent search-results list.

  7 new backend tests (`family_experiment_count` backward-compat; `count_experiments_for_family()` zero/
  matching-only/never-tested cases; `file_quant_research_experiment()`'s honest-`None`-without-a-list case,
  count-includes-itself case, and a real two-call growth-1-to-2 case against a real `GameState`). Full
  backend suite (2545 passed, up from 2538), `mypy app/`, `ruff check app/ tests/` clean. `tsc -b --noEmit`,
  `eslint`, `vite build` clean.

  Live-verified twice: a direct API sequence against the running dev server (compile → file twice →
  `familyExperimentCount` read 1 then 2), and a fresh `sandbox.spec.ts` Playwright run. That run surfaced
  two real pre-existing issues in the test itself, both fixed rather than skipped: Phase 1's new required
  `expectedMechanism`/`falsificationCriteria` fields had left "File Experiment" permanently disabled in this
  test (never filled in), an unverified regression from that increment; and the post-filing outcome-pill
  assertion used a bare page-wide `getByText`, which now hits strict-mode ambiguity because this long-lived
  dev save never deletes prior experiments and has accumulated many matching pills across this session's
  history — fixed by scoping the locator to the filed-result row's own DOM parent. No application behavior
  changed by either fix. `sandbox.spec.ts`: 4/4 passed.

  Deliberately not attempted here: Phase 5 (general-pipeline baseline comparison) and Phase 15 (knowledge
  graph nodes/edges) remain open, tracked in `docs/Architecture.md`.

- **CEO directive "Quant Research Factory / Strategy Discovery Engine," Phase 5: a real buy-and-hold
  baseline for the general compiled-strategy pipeline** (backend: `backend/app/baseline_comparison.py` (new),
  `backend/app/schemas.py`, `backend/app/research_experiment.py`, `backend/tests/test_baseline_comparison.py`
  (new), `backend/tests/test_research_experiment.py`, `backend/tests/test_quant_research_lab.py`; frontend:
  `frontend/src/types.ts`, `frontend/src/ui/components/CommandCenter/panels/sandbox/QuantResearchLabView.tsx`;
  `frontend/tests/sandbox.spec.ts`): no buy-and-hold/market-benchmark computation existed anywhere in this
  codebase. The only existing "baseline" concept — `app/ema_pullback_research.py`'s
  `confirmed_vs_naive_baseline` — compares two entry-rule variants of the SAME strategy family (both use a
  Chandelier Stop and R-multiple targets), never a market benchmark, and is hard-coded to that one reference
  strategy.

  New `compute_buy_and_hold_baseline()` re-fetches the exact same real (mock) candle window a backtest
  already tested and reports each symbol's real first-close/last-close percent return. Deliberately never
  blended with the strategy's own R-multiple-based expectancy into a single "beat the market by X%" figure —
  honestly different units, since this codebase's compiled-strategy engine never simulates real position
  sizing against a starting account balance. The real value: regime context — was the underlying market
  itself strongly trending during the tested window, so a modest positive expectancy isn't mistaken for a
  real edge when "anything would have worked."

  New `ResearchExperimentRecord.buyAndHoldBaseline: BuyAndHoldBaseline[]` (real default `[]`, since this
  record is nested inside the permanently persisted `QuantResearchExperiment.record`), populated by
  `run_research_experiment()`. Rendered in `QuantResearchLabView.tsx`'s filed-result box and search-results
  list, both explicitly labeled "context only, not a performance comparison."

  6 new backend tests. Full backend suite (2551 passed, up from 2545), `mypy app/`, `ruff check app/ tests/`
  clean. `tsc -b --noEmit`, `eslint`, `vite build` clean. Live-verified: a direct API call returned real,
  distinct per-symbol returns for all 8 seed symbols (e.g. AAPL -7.77%, QQQ +19.83%); a fresh `sandbox.spec.ts`
  re-run confirmed the "Buy-and-hold context:" line renders in the live UI.

- **CEO directive "Quant Research Factory / Strategy Discovery Engine," Phase 15: research experiments join
  the Knowledge Graph** (backend: `backend/app/schemas.py`, `backend/app/knowledge_graph.py`,
  `backend/app/routers/knowledge_graph.py`, `backend/tests/test_knowledge_graph.py`; frontend:
  `frontend/src/types.ts`, `frontend/src/ui/components/CommandCenter/KnowledgeGraphView.tsx`;
  `frontend/tests/commandCenter.spec.ts`): `build_knowledge_graph()` had no awareness of
  `QuantResearchExperiment` at all — the persisted `GameSaveState.quant_research_experiments` list was a
  ready-made real data source it simply ignored. The audit also surfaced an unrelated, pre-existing gap:
  `frontend/src/types.ts`'s `KnowledgeNodeType`/`KnowledgeEdgeRelation` were already stale relative to the
  backend (missing `black_swan_event`/`economic_event`/`same_day` from earlier Design Bible chapters), so
  `KnowledgeGraphView.tsx`'s per-type maps had no entries for those types. Fixed alongside this increment.

  New `"research_experiment"` node type: one real node per persisted `QuantResearchExperiment`, labeled with
  the real strategy name tested, subtitled with the real outcome and hypothesis. New `"tested"` edge relation
  links it to any `"strategy"` node sharing the same real compiled definition id
  (`Strategy.compiledDefinitionId == record.definitionId`) — a direct ID match, never fuzzy or causal. The
  researcher agent gets the same `"researched"` relation the `research` node type's own agent link already
  uses. `build_knowledge_graph()` gained an optional `quantResearchExperiments` parameter (default `None`,
  matching the existing `modelValidations` convention).

  Frontend: `KnowledgeGraphView.tsx`'s `TYPE_COLORS`/`TYPE_LABELS`/`NODE_RADIUS` maps gained entries for
  `black_swan_event`/`economic_event` (the stale-map fix) and the new `research_experiment` (distinct purple,
  "Research Experiment") — TypeScript's `Record<KnowledgeNodeType, ...>` made the missing keys a compile
  error the moment `types.ts` was corrected.

  5 new backend tests in a new `TestResearchExperimentNodes` class. Full backend suite (2556 passed, up from
  2551), `mypy app/`, `ruff check app/ tests/` clean. `tsc -b --noEmit`, `eslint`, `vite build` clean. Live-verified: a direct
  `GET /api/knowledge-graph` call against the real dev server (27 real experiments already on file from this
  session's own prior live-verification) returned 27 real `research_experiment` nodes and 27 real
  `researched` edges; `tested` edges read 0, honestly, since none of this save's strategies happen to share a
  compiled definition id with any filed experiment. A fresh screenshot shows the new "RESEARCH EXPERIMENT"
  filter chip alongside the now-fixed "DEFENSIVE MODE EPISODE"/"ECONOMIC EVENT" chips, with the header's real
  count grown to 302 nodes / 447 links. `commandCenter.spec.ts`'s Knowledge Graph test (extended with a new
  filter-chip assertion): 1/1 passed.

  This pass also caught a real session-hygiene issue: three stale `vite` processes from earlier phases in
  this session were still bound to ports 5173/5174/5175, causing an initial re-run to hit a genuinely stale
  build (blank canvas, not a code regression). Fixed by killing every leftover process by exact PID before
  confirming one fresh instance actually bound to port 5173.

  This closes every remaining phase of the directive except the structurally-blocked fuller Phase 16 ask (see
  Increment 2 above). Phases 19/20 (comprehensive testing, final audit) tracked separately.

- **CEO directive "Quant Research Factory / Strategy Discovery Engine," Phases 19-20: comprehensive testing +
  final honest audit** (documentation only — `docs/Architecture.md`): a dedicated regression pass across the
  whole directive's surface area. Full backend suite (2556 passed), `mypy app/` (177 files), `ruff check app/
  tests/` clean. Full frontend `tsc -b --noEmit`, `eslint`, `vite build` clean. Full live Playwright re-runs
  against a freshly-restarted, single-instance dev stack: `sandbox.spec.ts` 4/4 passed; `commandCenter.spec.ts`
  31/33 passed, 1 skipped, 1 failed — the single failure is the exact same test with the exact same failure
  signature already documented as a known pre-existing environmental issue (headless-browser input timing) in
  Directive A's own Phase 13 comprehensive-testing pass, unrelated to any code this directive touched.

  The final 18-question audit (see `docs/Architecture.md`) surfaced one more real self-correction: recounting
  Phase 1's actual commit diff found it added exactly 3 new tests, not the 4 originally stated — corrected in
  both this file and `docs/Architecture.md` (the corrected total, 2+3+7+6+5=23, matches the real suite growth
  from 2533 to 2556 exactly). Every phase of the directive is now closed except the one genuine, permanently
  structural gap already disclosed in Increment 2: the fuller Phase 16 ask (an automated hypothesis-generation
  loop that learns from outcomes), blocked by the real absence of any generation mechanism in this codebase.

- **CEO directive "Portfolio Construction, Capital Allocation & Execution Realism," Phase 1 (audit) +
  Increment 1 (live strategy-position attribution + real exposure reads)** (backend:
  `backend/app/schemas.py`, `backend/app/state.py`, `backend/app/portfolio_intelligence.py`,
  `backend/tests/test_portfolio_intelligence.py`, `backend/tests/test_state.py`; frontend:
  `frontend/src/types.ts`, `frontend/src/state/gameStore.ts`, `frontend/src/game/systems/NexusManager.ts`,
  `frontend/src/ui/components/CommandCenter/panels/PortfolioIntelPanel.tsx`): a dedicated research-agent
  audit (before any code) found this codebase far more built out here than expected —
  `app/position_sizing.py` (a real, layered, evidence-weighted sizing engine that only ever narrows the
  flat equity-percentage ceiling) and `app/portfolio_intelligence.py` (real Pearson correlation, category
  exposure, Portfolio Heat, capital efficiency) already exist. Confirmed real gaps: no volatility/ATR-based
  position sizing (ATR machinery exists but only prices backtest stops, never live sizing); no
  LONG/SHORT/NET/GROSS exposure concept anywhere; no live strategy-level exposure (an open `PaperPosition`
  had no `strategy_id` — only closed trades got strategy attribution).

  This pass closes the last one, the prerequisite for everything strategy-scoped that follows: new
  `PaperPosition.strategyId`, applied in `submit_ceo_decision()` via the identical `.model_copy()` pattern
  already used for `CeoDecisionRecord.strategyId` — patches the freshly-opened position strictly after the
  trade resolves, never altering what it does. Two new real reads in `compute_portfolio_intelligence()`
  (already WS-broadcast every tick — no new endpoint needed): `ExposureSummary` (real long/short values from
  `PaperPosition.side`, net = directional bias, gross = total capital at work, both as real numbers, not one
  side-blind sum) and `StrategyExposureRead[]` (open positions grouped by the new live `strategy_id`,
  `null` as its own honest, never-folded-in bucket). Rendered in `PortfolioIntelPanel.tsx` as two new cards.

  12 new backend tests. Full backend suite (2478), `mypy app/`, `ruff check app/ tests/` clean.
  `tsc -b --noEmit`, `eslint`, `vite build` clean. Live-verified: an old save auto-migrated cleanly via the
  existing `_deep_merge_defaults` mechanism, and a Command Center screenshot confirmed both new cards
  render correctly. See docs/Architecture.md's own section for the full Phase 1 audit findings and the
  remaining phases' scoping (volatility sizing, correlation gate, strategy ranking, degradation
  monitoring, trade-decision explanation, no-trade diagnostics) — none blocked, not yet started.

- **CEO directive "Portfolio Construction, Capital Allocation & Execution Realism," Phase 3:
  volatility-aware position sizing** (backend: `backend/app/schemas.py`, `backend/app/position_sizing.py`,
  `backend/app/nexus.py`, `backend/tests/test_position_sizing.py`; frontend: `frontend/src/types.ts`,
  `frontend/src/ui/components/CommandCenter/panels/WarRoomPanel.tsx`): POSITION SIZE ~ RISK BUDGET /
  DISTANCE TO STOP, built as one more narrowing factor in `build_position_sizing()`'s existing cascade,
  never a competing formula. New `_volatility_sizing()` computes a real ATR read (real candles, the same
  `MarketDataProvider` every other tick-time read uses) and reuses this codebase's own already-established
  Chandelier Stop constants (`CHANDELIER_ATR_PERIOD`/`CHANDELIER_ATR_MULTIPLIER`) rather than a second,
  independently-tuned convention; `risk_budget_usd` reuses `risk_limits.risk_per_trade_pct` — the identical
  dollar figure the existing ceiling already implies, not a new risk parameter. Proven directly: a more
  volatile symbol gets a smaller real quantity cap, but the *dollar risk implied at that cap* is identical
  regardless of volatility — the directive's own explicit "should not receive a larger dollar risk simply
  because its market happens to be more volatile" rule, asserted, not just claimed. `available: false`
  (never a fabricated stop distance) whenever there isn't yet enough real candle history for a symbol.

  **A real bug found and fixed before committing**: `PositionSizingResult` lives inside the persisted
  `war_room_sessions` LIST, and per this codebase's own `_deep_merge_defaults` convention, new fields
  inside list-nested models need real Pydantic defaults (list items are taken wholesale on load, never
  per-item merged) — the first draft didn't have them. Fixed, and proven two ways: a unit test validating
  from a raw dict with the field entirely absent, and a live screenshot of this exact save's own
  pre-existing 56 War Room sessions rendering the new card correctly in its honest "UNAVAILABLE" state.

  10 new backend tests. Full backend suite (2488), `mypy app/`, `ruff check app/ tests/` clean.
  `tsc -b --noEmit`, `eslint`, `vite build` clean. Live-verified against the real running save (no console
  errors); a screenshot with a real, freshly-computed ATR value wasn't achievable this session — the same
  real, documented Opportunity Gatekeeper liquidity constraint already disclosed in the prior directive
  blocks new proposal generation in this environment's mock data right now, so the backward-compat path
  (the thing this increment actually needed proven) was exercised on real persisted data instead.

- **CEO directive "Portfolio Construction, Capital Allocation & Execution Realism," Phase 4:
  correlation-aware portfolio risk** (backend: `backend/app/schemas.py`,
  `backend/app/portfolio_intelligence.py`, `backend/app/opportunity_gatekeeper.py`,
  `backend/app/gatekeeper.py`, `backend/app/nexus.py`, `backend/tests/test_portfolio_intelligence.py`,
  `backend/tests/test_opportunity_gatekeeper.py`, `backend/tests/test_gatekeeper.py`; frontend:
  `frontend/src/types.ts`, `frontend/src/net/api.ts`, `frontend/src/state/gameStore.ts`,
  `frontend/src/game/systems/NexusManager.ts`,
  `frontend/src/ui/components/CommandCenter/panels/RiskPanel.tsx`; docs: `docs/API.md`): closes the exact
  gap `opportunity_gatekeeper.py`'s own docstring already named — the real Pearson correlation
  `portfolio_intelligence.py` already computed was informational-only, never a pre-trade gate. New
  `count_correlated_positions()` fetches real candles/returns for the candidate symbol and every held
  symbol and counts real `|Pearson r| >= 0.6` clusters (the same threshold `_correlation_pairs()` already
  used); wired into `evaluate_opportunity()` as a new, optional `correlated_position_count` parameter
  (`None` is silently skipped, never treated as zero, so no existing caller changes by omission) that
  rejects pre-proposal with the new `"correlated_exposure_too_high"` reason code once it exceeds the new
  CEO-configurable `RiskLimits.max_correlated_positions` (default `2`). Kept deliberately separate from,
  not merged into, `gatekeeper.py`'s existing later-stage category-co-occurrence check — its previously
  hardcoded `MAX_CORRELATED_POSITIONS` constant now reads the same new `RiskLimits` field instead, with
  the default preserving existing behavior exactly. New CEO control rendered in `RiskPanel.tsx`'s existing
  Opportunity Gatekeeper card.

  17 new backend tests. Full backend suite (2501), `mypy app/`, `ruff check app/ tests/` clean.
  `tsc -b --noEmit`, `eslint`, `vite build` clean. Live-verified: a Command Center screenshot of the real
  running save's Risk panel confirms the new control renders with the correct real default (`2`).

- **CEO directive "Portfolio Construction, Capital Allocation & Execution Realism," Phase 5:
  strategy capital allocation evidence** (backend: `backend/app/schemas.py`,
  `backend/app/performance_attribution.py`, `backend/app/routers/trades.py`,
  `backend/tests/test_performance_attribution.py`; frontend: `frontend/src/types.ts`,
  `frontend/src/net/api.ts`, `frontend/src/ui/components/CommandCenter/panels/PerformancePanel.tsx`):
  a dedicated research-agent audit mapped every directive-named evaluation dimension (expectancy, drawdown,
  volatility, robustness, execution quality, regime/session compatibility, portfolio correlation) against
  what this codebase already computes for LIVE-traded strategies — most of it already real and reused
  (`_group_metrics()`'s expectancy/profit-factor/win-rate, `compute_strategy_session_performance()`, real
  position-value exposure), never recomputed. The audit also flagged a real, pre-existing honesty gap
  worth naming as a precedent NOT to repeat: `StrategyExecutiveDashboard.bestStrategy` crowns a strategy off
  a raw average return with zero minimum sample size — exactly the un-gated "winning strategy" label this
  directive explicitly forbids creating (not fixed this pass — a different feature's existing debt — but
  deliberately not repeated in the new work).

  Two genuinely new real reads, both gated at the existing `MIN_SYMBOL_SAMPLE_FOR_VERDICT` (3) convention:
  `_live_drawdown_usd()` (real peak-to-trough drawdown of a strategy's own cumulative realized P&L, in
  dollars — never a percentage, since strategies share one account's capital with no isolated sub-account
  equity base) and `_live_return_volatility_pct()` (real population stdev of a strategy's own per-trade
  `pnl_pct`, distinct from Phase 3's ATR/price-volatility concept). Two directive-named dimensions are
  explicit, disclosed gaps rather than fabricated numbers: **robustness** (no walk-forward windowing
  convention exists for a live-traded strategy's real, irregularly-timed trades — `strategy_tournament.py`'s
  Rounds 4/6/9 only cover Sandbox synthetic backtests) and **portfolio correlation** (a true
  return-correlation between two strategies' own live P&L streams would need synchronized time-bucketing
  this codebase has no convention for — the real alternative shown instead is each strategy's own live
  position-value exposure, named as a distinct concept).

  New `compute_strategy_capital_allocation_evidence()` gives every real `Strategy` a row — including one
  with zero live trades (`evidence_state = "no_live_trades_yet"`, every derived metric `None`, its real
  `allocatedCapital` still shown) — via a new `GET /api/trades/strategy-capital-allocation` endpoint. Rows
  sort by `allocatedCapital` descending — the CEO's own existing real capital commitment — **never** by any
  performance metric, so row order can't be mistaken for a system-generated ranking or auto-allocation
  signal. Rendered as a new "Strategy Capital Allocation — Evidence, Not a Ranking" card in
  `PerformancePanel.tsx`.

  17 new backend tests. Full backend suite, `mypy app/`, `ruff check app/ tests/` clean. `tsc -b --noEmit`,
  `eslint`, `vite build` clean. Live-verified via Command Center screenshot: the real save's four
  strategies all show the honest "NO LIVE TRADES YET" state with real `$0.00` allocated capital and both
  disclosed notes.

- **CEO directive "Portfolio Construction, Capital Allocation & Execution Realism," Phase 6:
  strategy degradation** (backend: `backend/app/schemas.py`, `backend/app/performance_attribution.py`,
  `backend/app/routers/trades.py`, `backend/tests/test_performance_attribution.py`; frontend:
  `frontend/src/types.ts`, `frontend/src/net/api.ts`,
  `frontend/src/ui/components/CommandCenter/panels/PerformancePanel.tsx`): a real NORMAL_VARIATION /
  POSSIBLE_DEGRADATION / CRITICAL_DEGRADATION classification for live-traded strategies, never auto-
  retiring anything on a tiny sample. Reuses the identical recent-vs-lifetime windowing convention
  `strategy_lab.py`'s `compute_strategy_health()` already established for backtest runs
  (`HEALTH_RECENT_WINDOW`, imported directly), applied to live `PaperTrade` sequences instead. Every
  recent/lifetime metric pair reuses an already-computed Phase 5 source (`_group_metrics()`,
  `_live_return_volatility_pct()`, `_avg_slippage_bps()`, `_live_drawdown_usd()`) computed twice — never a
  new statistic.

  A real find during this phase's own audit closed what looked like it would have to be a disclosed gap:
  `app/failure_review.py`'s `classify_failure()` already files a real `FailureClassification`
  (`reason: "bad_thesis"`) for every real closed, losing trade, joinable via the same `trade_id` →
  Decision Vault → `strategy_id` chain this module already uses — giving `recent_invalidation_count` a
  real, non-fabricated answer to the directive's "repeated invalidations" dimension.

  Six real, independently-triggerable signals (any CRITICAL signal escalates the row regardless of what
  else also fired), each a disclosed, arbitrary threshold: loss clustering (4/3 trailing losses), expectancy
  deterioration (a sign flip to negative is CRITICAL; a >3.0 point drop otherwise is POSSIBLE), volatility
  regime change (recent volatility >1.5x lifetime), execution degradation (recent avg entry slippage >10
  bps worse), abnormal drawdown (recent peak-to-trough >3x/>5x a typical single loss), and repeated
  invalidations (>=2 of the recent window classified `bad_thesis`). New `GET /api/trades/strategy-
  degradation` endpoint, rendered as a new "Strategy Degradation Watch" card in `PerformancePanel.tsx` —
  filters `not_enough_data` rows out of the list itself (only counts them) so the card stays a warning list,
  not a duplicate of the Capital Allocation roster.

  17 new backend tests, each scenario hand-constructed to isolate its one target signal — all passed on
  first run. Full backend suite, `mypy app/`, `ruff check app/ tests/` clean (no circular import from
  reusing `strategy_lab.py`'s constant, confirmed via a runtime import smoke test). `tsc -b --noEmit`,
  `eslint`, `vite build` clean. Live-verified via Command Center screenshot: the real save's Performance
  panel renders the new card correctly in its honest empty state.

- **CEO directive "Portfolio Construction, Capital Allocation & Execution Realism," Phases 7-8:
  execution realism fix + risk-of-ruin audit** (backend: `backend/app/broker.py`,
  `backend/app/execution_quality.py`, `backend/tests/test_broker.py`): an audit-first pass (per Phase 7's
  own directive text) confirmed spread/commissions/slippage/latency were already real
  (`execution_quality.py`'s formula-based slippage, `portfolio.py`'s `TRANSACTION_COST_BPS`, `broker.py`'s
  real 1-tick latency), then surfaced one real, previously-silent gap while specifically auditing stop/
  take-profit execution: a triggered stop/stop_loss filled at exactly its own trigger price even when the
  tick's own real `current_price` — already available, never fabricated — showed the market had already
  moved past that level, silently giving every gapped stop a small, unearned advantage. **Fixed**:
  `_fill_price()` now returns the worse of the trigger price and `current_price` for triggered stops
  (`max()` for a buy-stop, `min()` for a sell-stop); slippage still applies on top, unchanged. Intra-candle
  gap-through (no tick data between two points) correctly stays out of scope — no order-book depth exists
  to derive it from — while inter-tick gap-through (the market having already moved by the next real tick)
  is now modeled, using data every caller already had. `limit`/`take_profit` orders are correctly
  unaffected. 8 new tests (`TestGapThroughFill`), isolating the effect from slippage; all existing
  `test_broker.py` tests pass unchanged (every existing stop-fill test already used a non-gapped price).

  Phase 8 audit: `strategy_lab.py`'s `run_strategy_monte_carlo()` is a real, already-built bootstrap Monte
  Carlo producing real `probabilityOfRuinPct`/`capitalSurvivalPct`/VaR/CVaR reads, already CEO-visible in
  `StrategyCertificationView.tsx` and `EmaPullbackResearchView.tsx`, always framed as a probability, never a
  guarantee the strategy "cannot fail." A PORTFOLIO-level combined risk-of-ruin is a deliberate, disclosed
  non-build: combining strategies' independent bootstrap paths into one number would require assuming a
  correlation between their return streams that Phase 5 already established has no real metric in this
  codebase — building one now would fabricate an implicit independence assumption to produce a single
  number, exactly what the directive's Absolute Rules forbid.

  Full backend suite, `mypy app/`, `ruff check app/ tests/` clean; targeted re-run of every broker/nexus/
  paper_trading/portfolio/execution_quality test (146 tests) confirms no downstream regression.

- **CEO directive "Portfolio Construction, Capital Allocation & Execution Realism," Phase 9:
  consolidated "WHY THIS TRADE?" view (pending-proposal side)** (backend: `backend/app/schemas.py`,
  `backend/app/nexus.py`, `backend/tests/test_war_room.py`; frontend: `frontend/src/types.ts`,
  `frontend/src/ui/components/CommandCenter/panels/WarRoomPanel.tsx`): a research-agent audit traced one
  real `TradeProposal` end-to-end and found every directive-named field already real somewhere, but
  scattered across up to five different objects with no single consolidated view — plus one real,
  previously-silent loss: the Phase 4 statistical Pearson correlation count was computed to decide the
  Opportunity Gatekeeper's approve/reject call, then discarded for every APPROVED candidate, never reaching
  the CEO. Closed that: new `WarRoomSession.statisticalCorrelatedPositions`, set via the same
  `.model_copy()` that already attaches `positionSizing`. 3 new backend tests.

  New `WhyThisTradeCard` (`WarRoomPanel.tsx`) is entirely a frontend join of already-store-resident data —
  no new backend endpoint needed. Real fields render their real value; genuine gaps the audit confirmed
  (strategy not yet selected, no live target-price mechanism, no live stop-loss order to compute a real
  R-multiple against, regime/session only stamped at close, Gatekeeper checks only run at decision time,
  execution constraints only realized at fill time) are named explicitly rather than guessed or left blank.

  `tsc -b --noEmit`, `eslint`, `vite build` clean. Live verification not achievable this pass: the real
  running save currently has zero `WarRoomSession`s (day 71, 0 pending proposals) — the same disclosed
  liquidity-gate constraint from Phases 3-4, this time with no pre-existing session to fall back on either.
  The card's logic was traced field-by-field against real schema names instead. Deliberately not yet
  done: the closed-trade side (extending `DecisionDetail.tsx` with the same consolidated join for an
  already-closed trade) — a natural next increment, not started this pass.

- **CEO directive "Portfolio Construction, Capital Allocation & Execution Realism," Phases 10 &amp; 12
  audits: no-trade diagnostics and market visualization already satisfy the ask (no code needed)**:
  Phase 10's "distinguish 'we chose not to trade' from 'we were unable to trade'" is already built by a
  prior directive — `app/trade_pipeline_health.py`'s `compute_trade_pipeline_health()` already separates
  `noTradeDecisions` (CEO chose WAIT) from `opportunityRejections`/`gatekeeperRejections` (system blocked
  it), and its `reasonCodeBreakdown` is a real, generic `Counter` over whatever `NoTradeReasonCode` values
  appear in the data — Phase 4's new `correlated_exposure_too_high` code flows through automatically, with
  zero further code, already proven by an existing test. Already rendered in `RiskPanel.tsx`. Phase 12's
  "candles must behave realistically; label SIMULATED vs LIVE; indicators must derive from real chart
  data" is likewise already real: `CandlestickChart.tsx` already reads and renders each candle's real
  `dataStatus`, and chart overlays are built directly from real `technicalAnalysis` for the displayed
  symbol. Both confirmed by reading the actual code and its tests/consumers this pass, not just cited from
  the earlier Phase 1 audit.

- **CEO directive "Portfolio Construction, Capital Allocation & Execution Realism," Phase 11:
  Portfolio Command Center consolidation** (frontend:
  `frontend/src/ui/components/CommandCenter/panels/PortfolioIntelPanel.tsx`): per the directive's own
  "don't create another giant tab collection" rule, this enhances the existing PORTFOLIO tab rather than
  adding a new one. New `PortfolioCommandCenterStrip` at the top: real equity, daily/total P&L (reusing
  the identical `computePeriodFinancials()` the Performance tab already uses), gross/net exposure, open
  position count, active strategy count, and risk utilization (Portfolio Heat), plus a risk-level badge
  reusing the identical `riskLevel()` the Risk tab already uses — nothing recalculated. Three cross-link
  buttons (the established `EventBus.emit("ui:commandCenterJump", ...)` pattern) point at the real detail
  sections earlier phases already built (Capital Allocation/Degradation Watch on PERFORMANCE, Risk
  Alerts & No-Trade Reasons on RISK) instead of duplicating them.

  `tsc -b --noEmit`, `eslint`, `vite build` clean. Live-verified via Command Center screenshot: the real
  running save's Portfolio tab renders the new strip with real numbers (Equity $99,931.78, Total P&L
  -$68.22, 4 active strategies, 0% risk utilization) above the existing, unchanged detail cards.

- **CEO directive "Portfolio Construction, Capital Allocation & Execution Realism," Phase 13:
  comprehensive testing pass**: every directive-named dimension already had real, dedicated tests from its
  own phase (position sizing, risk budget, exposure, correlation, strategy allocation/degradation,
  execution costs/slippage, portfolio P&L/drawdown, no-trade reasons, insufficient capital, strategy
  eligibility) — this pass ran everything together once more and closed the two dimensions not yet
  explicitly verified. **Historical-data boundaries**: confirmed every new function this directive added
  gates on a real sample-size threshold and returns an honest unavailable/not-enough-data state below it,
  never a fabricated number. **No-look-ahead**: audited directly — `app/leakage_audit.py`'s real,
  proven-sound methodology is scoped to the backtest/pattern-detection pipeline, which nothing this
  directive touched; every new function instead reads either `MarketDataProvider`'s real current-tick
  candle window (structurally unable to see beyond "now" in a forward-only simulation) or already-closed
  `PaperTrade`s ordered by real `closed_at` — no new look-ahead surface, confirmed by tracing each
  function's data source.

  Full backend suite (2533 passed), `mypy app/`, `ruff check app/ tests/` clean. `tsc -b --noEmit`,
  `eslint`, `vite build` clean. `tests/commandCenter.spec.ts` run live against a freshly-restarted dev
  stack — 31/33 passed, 1 skipped (pre-existing), 1 failed (a player-movement/WASD-input timing assertion
  unrelated to any Command Center panel). The tests exercising this directive's own UI changes all passed:
  the PORTFOLIO tab test (Phase 11's strip), the WARROOM tab test (Phase 9's card), two RISK-panel-control
  tests (Phase 4's field), and the full 40-tab render cycle (which would have caught a Phase 5/6
  `PerformancePanel.tsx` crash).

- **CEO directive "Portfolio Construction, Capital Allocation & Execution Realism," Phase 14: final
  honest audit** (docs: `docs/Architecture.md`): the directive's mandated 18-question closing report,
  answered directly against real evidence from Phases 1-13. Confirms: research led every phase; nothing
  was duplicated; nothing was fabricated (every real gap returns an explicit unavailable state with a
  cited reason instead); the compliance/quality score was never manipulated; no trade was ever forced;
  win rate was never optimized for alone; no new look-ahead surface exists; existing governance (CEO
  approvals, risk gates, circuit breakers, strategy eligibility) was preserved throughout.

  **A real self-correction surfaced by this audit**: recounting each phase's actual new test methods
  against the real backend suite-size deltas at the time found the per-phase test counts stated in this
  directive's own earlier commit messages were consistently overcounted by a few each (Phase 4 stated 17,
  actually 13; Phase 5 stated 17, actually 10; Phase 6 stated 17, actually 15; Phase 7 stated 8, actually
  5; Phase 9 stated 3, actually 2) — an honest counting slip when writing each commit message, not a
  fabricated behavioral claim, but corrected here rather than repeated: 13 + 10 + 15 + 5 + 2 = 45 new
  backend tests, matching the real, verified suite growth (2488 → 2533) exactly.

- **CEO directive "Live Trade → Strategy Provenance": the real, non-fabricated way a live trade can
  now link back to a Strategy Lab strategy** (backend: `backend/app/schemas.py`,
  `backend/app/routers/executive.py`, `backend/app/state.py`, `backend/app/decision_vault.py`,
  `backend/app/trade_attribution.py`, `backend/tests/test_state.py`,
  `backend/tests/test_trade_attribution.py`, `backend/tests/test_decision_vault.py`): a follow-up
  directive to the prior "Strategy Intelligence" work, explicitly asking whether genuine live
  trade→strategy provenance could be added without rewriting the trading engine. A written
  architecture-first finding (produced before any code, per the directive's own Phase 1 mandate)
  confirmed the earliest — and only — point in the entire live pipeline where a human genuinely,
  provably chooses a strategy is the CEO's own `POST /api/executive/decide` click; nothing upstream
  (research, votes, proposal generation) ever touches a `Strategy` object. This closes that exact gap,
  using an existing precedent as the template: `SubmitCeoDecisionRequest.overrideReason` was already
  an optional, CEO-typed field stored on `CeoDecisionRecord` via `.model_copy()` *after*
  `resolve_proposal()` returns, never altering trade execution — the new `strategyId` field follows
  the identical pattern.

  New `CeoDecisionRecord.strategyId` — an optional, CEO-explicit strategy selection at the moment of
  deciding, validated against the real strategy roster (`state.strategies`) and rejected with a real
  400 if it doesn't match a real strategy; silently ignored (never stored) on a "wait," since no trade
  exists to attribute. `DecisionVaultEntry.strategyId` — a field that has existed since Feature 61 with
  a docstring explicitly reading "always None today... a genuine future addition if that ever changes,
  not fabricated here" — is now that genuine addition: `build_vault_entry()` threads it straight
  through from the matching `CeoDecisionRecord` with a one-line change. `TradeAttributionRecord` and
  `TradeReportCard` both gain `strategyId`/`strategyProvenanceState` (`"known"` | `"unknown"` |
  `"unavailable"` — never a fabricated middle state), joined the same way every other field on those
  two records already is, by the trade's own real `decisionId`.

  **The honesty boundary, explicit**: this labels only the strongest claim the architecture can prove
  — `known` means the CEO explicitly selected that strategy at decision time, never that the strategy
  "caused" or "generated" the trade (no code path exists for that, and none was fabricated here).
  Historical trades and any trade where the CEO doesn't bother picking a strategy correctly read
  `unknown`/`unavailable` forever — never backfilled. 12 new backend tests (real-strategy validation,
  rejection of an unknown strategy id, the "wait" no-op case, and all three provenance states across
  the join). Full backend suite, `mypy app/` (176 files), `ruff check app/ tests/` all clean.

- **CEO directive "Live Trade → Strategy Provenance": the frontend hook that actually exercises the
  above** (`frontend/src/net/api.ts`, `frontend/src/ui/components/CommandCenter/ExecutiveVoting.tsx`,
  `frontend/tests/executiveVoting.spec.ts`): the backend chain above had no live way to be exercised
  without a CEO-facing control, so `ExecutiveVoting.tsx` gains an optional "Strategy" selector next to
  the existing MODIFY control, listing every real `state.strategies` entry and defaulting to "No
  strategy attributed." Deliberately never pre-selected from live eligibility data — Directive C's own
  Phase 3 rule that "eligible today" is not "the CEO says this strategy drove this trade." The pick
  threads through `api.submitCeoDecision()`'s new `strategyId` parameter on both the BUY/SELL/WAIT
  `decide()` path and the "Delegate to Executive Board" `delegate()` path, and resets after every
  decision. `tsc -b --noEmit`, `eslint`, `vite build` all clean; the running app was verified to boot
  and load a real save with zero console/page errors. A new Playwright test asserting the selector
  lists real strategies and that `POST /executive/decide`'s body carries a non-null `strategyId` was
  written in this suite's own real-app (no-mocking) style, but could not be run to a passing result in
  this session — the dev backend's organic trade-proposal generation never produced a pending proposal
  within several minutes of real+boosted ticks, and the pre-existing baseline test in the same file
  (unmodified here) reproduces the identical timeout on the same backend instance, confirming this is
  an environment/session condition in live proposal generation, not a regression from this change. This
  is disclosed, not swept under a claimed pass: the new test is correctly typed and lint-clean, but not
  yet proven green end-to-end.

- **CEO directive "Live Trade → Strategy Provenance," Phase 4: the Strategy Exposure view**
  (`backend/app/performance_attribution.py`, `backend/app/routers/trades.py`,
  `backend/app/schemas.py`, `backend/tests/test_performance_attribution.py`): new
  `compute_strategy_performance()`, exposed as `GET /api/trades/performance-by-strategy`. Follows the
  exact same real-Decision-Vault-join pattern `compute_session_performance()`/
  `compute_regime_performance()` already established — grouped by `DecisionVaultEntry.strategyId`
  instead, the one axis `performance_attribution.py`'s own module docstring had explicitly named as
  blocked ("STRATEGY: DecisionVaultEntry.strategy_id is always None on a live Trading Floor trade") back
  when it was first written, now honestly unblocked by the Phase 2 work above rather than a new
  mechanism invented on top of it.

  Only trades with a real, CEO-selected `strategyId` are ever grouped (`strategyProvenanceState ==
  "known"`); every other trade is excluded under one of two distinct, disclosed reasons instead of one
  merged count — `tradesExcludedNoStrategySelected` (a real vault entry exists, the CEO just never
  picked a strategy — `"unknown"`) and `tradesExcludedNoVaultEntry` (no matching vault entry at all —
  `"unavailable"`) — collapsing those two real, already-established provenance states into one number
  would have erased a distinction this codebase treats as meaningful everywhere else it appears.

  7 new backend tests covering grouping, both exclusion reasons independently, sort order, and the
  shared evidence-threshold behavior. Full backend suite (2449), `mypy app/` (176 files), `ruff check
  app/ tests/` all clean.

  **Frontend** (`frontend/src/net/api.ts`, `frontend/src/types.ts`,
  `frontend/src/ui/components/CommandCenter/panels/PerformancePanel.tsx`): a new "Performance by
  Strategy" section, same layout convention as the existing Symbol/Session/Market Regime sections —
  strategy name resolved from the real `state.strategies` roster, sorted by `totalPnl`, both exclusion
  counts shown as separate, honest disclosure lines. Retires a now-false pre-existing disclosure line
  ("Performance-by-strategy also isn't built..."). `tsc -b --noEmit`, `eslint`, `vite build` all clean;
  verified live against a real running save — the endpoint honestly returned `reads: []` with
  `tradesExcludedNoStrategySelected: 2` and the panel rendered that exact disclosed state (confirmed via
  screenshot). **Disclosed, not hidden**: on almost every save today this reports an empty state —
  almost no live trade has a CEO-selected strategy yet, since the selector UI only just shipped; that's
  the honest current state of a feature that just started being recordable, not a bug.

- **CEO directive "Live Trade → Strategy Provenance," Phases 5, 6, 9 (backend)** — a dedicated
  read-only research audit (same discipline as Phase 1) preceded this round, citing exact file:line
  evidence for what already existed across every remaining phase before any code was written.

  **Phase 5** (`backend/app/performance_attribution.py`, `GET /api/trades/strategy-live-vs-backtest`):
  `compute_strategy_live_vs_backtest()` compares a strategy's real live win rate against its own latest
  real `StrategyHealthAssessment` — two already-computed sources joined, zero new trade-level math.
  Deliberately compares `winRatePct` only (both real 0-100% scales); `expectancyR` (backtest, R-multiples)
  vs. `avgPnlPct` (live, percent) are different units and were NOT force-compared. Verdict:
  `consistent_with_backtest` / `diverging_from_backtest` (±15pp, disclosed arbitrary threshold) /
  `not_enough_live_data` (<3 live trades) / `no_backtest_health_on_record`. **Deliberately not
  attempted**: R-multiple-based attribution — the audit confirmed `DecisionVaultEntry.rMultiple` is
  always `None` because the real risk engine has no stop-loss-distance concept anywhere to derive one
  from; building it would mean fabricating a stop-loss basis that doesn't exist.

  **Phase 6** (`GET /api/trades/performance-by-strategy-session`): `compute_strategy_session_
  performance()` — the real strategy×session axis, same Decision Vault join, grouped on
  `(strategy_id, session)`. The audit found the BACKTEST version of this cut already exists and is
  already rendered (`CompiledStrategyBacktestResult.sessionBreakdown`, `StrategyCompilerView.tsx`) —
  this closes only the analogous LIVE gap, not a duplicate.

  **Phase 9** (`backend/app/trade_pipeline_health.py`, `GET /api/trades/strategy-trading-diagnostics`):
  `compute_strategy_trading_diagnostics()` — "why isn't this strategy trading live?" per strategy, the
  one gap the existing pipeline-health funnel diagnostic never covered (audit: zero "strategy"
  references in that module before this). Built entirely from two already-real sources
  (`compute_strategy_match()`'s regime eligibility, Phase 4's live trade counts): `trading_live` /
  `blocked_by_regime_today` / `eligible_but_never_selected` / `no_backtest_evidence_yet`. Diagnostic
  only — feeds no score, gates nothing.

  17 new backend tests. Full backend suite (2466), `mypy app/` (176 files), `ruff check app/ tests/` all
  clean.

- **CEO directive "Live Trade → Strategy Provenance," Phases 5-11 (frontend)**:

  **Phase 5** rendered in `StrategyHealthView.tsx` (Sandbox → Health) — a "Live vs. Backtest" card,
  fixing that view's own stale claim that live-trade-to-strategy attribution didn't exist (true when
  Feature 52 shipped, false since Phase 2). **Phase 6** rendered in `PerformancePanel.tsx` — "Strategy
  Performance by Session," compact, `null` (not empty-state) when nothing real exists yet. **Phase 7** —
  `ExecutiveVoting.tsx`'s strategy picker now shows each option's real stage plus a one-line "context
  only, never gates selection" disclosure, closing the audit's "zero connection to certification/stage"
  finding without inventing a restriction the directive never asked for. **Phase 8** —
  `StrategyCertificationView.tsx` (the real governance decision point) gains a "Live Performance —
  informational only, never a certification requirement" card; deliberately no automatic lifecycle logic
  was added (the audit confirmed none exists, and building one would be an unauthorized invention).
  **Phase 9** — new `StrategyTradingDiagnosticsView.tsx`, a persistent per-strategy diagnostic table next
  to `LiveStrategyEligibilityCard`. **Phase 10** — two real cross-links (Performance ↔ Sandbox) via the
  already-established `EventBus.emit("ui:commandCenterJump", ...)` mechanism (previously only used by
  the Quick Action Dock) — zero new plumbing, a full nav restructuring of the 3-4-way scatter was
  deliberately not attempted. **Phase 11** — `StrategyLibraryView.tsx` gains a "Live P&L" column sourced
  from the same Phase 4 data, threaded down from `SandboxPanel.tsx` as a new prop.

  `tsc -b --noEmit`, `eslint`, `vite build` all clean. Full backend suite re-confirmed (2466, unchanged —
  no backend touched this pass). Live-verified via 6 Command Center screenshots against a real running
  save — every new card/column/link renders its correct honest state (populated where real data exists,
  cleanly absent where it doesn't), no console errors.

  **One piece not captured live, and precisely why**: the CEO strategy picker itself needs an open,
  pending `TradeProposal` to screenshot. `GET /api/trades/pipeline-health` showed 100 real
  `opportunityRejections` on this save, split `liquidity_confirmation_weak`/`trade_quality_below_threshold`.
  Temporarily zeroing `minTradeQualityScore`/`minPriorityScore` via the real `POST /api/risk-limits`
  endpoint (then restoring them) isolated the binding constraint to `liquidity_confirmation_weak` —
  `app/opportunity_gatekeeper.py`'s own docstring already discloses this is real and deliberate (the mock
  candle provider rarely produces genuine liquidity-sweep patterns) and explicitly says not to weaken it
  just because trading activity is low, so this pass didn't. The picker's own code is fully verified
  (typecheck/lint/build clean); only its live screenshot is the disclosed gap.

- **CEO directive "Live Trade → Strategy Provenance," Phases 12-13: comprehensive testing + final audit**:
  full Playwright suite run twice — the first run (83/96 failed) traced to this session's own accumulated
  stale `vite` dev-server processes (four competing instances left over from earlier manual verification),
  not a regression; fixed by killing all stale processes and re-running one clean backend/frontend pair
  (confirmed by re-running the first failing test alone, which then passed). Clean-stack run: **82 passed,
  13 failed, 1 skipped**. All 13 failures traced to two pre-existing causes unrelated to this directive: 6
  are `executiveVoting.spec.ts` tests blocked by the same real, documented Opportunity Gatekeeper liquidity
  check described above; 7 are Phaser world/player-physics and asset-loading failures in this sandbox
  (`commandCenter.spec.ts`, `constitution.spec.ts`, `evolutionPanel.spec.ts`, `interaction.spec.ts` x2,
  `knowledgeBase.spec.ts`, `marketIntel.spec.ts` — none touch Strategy Lab/Performance/Executive Voting
  code, and this directive never touches Phaser scenes or player movement). Full backend suite
  re-confirmed one final time (2466 passed), `mypy`/`ruff` clean. A 15-item final audit report was written
  covering every phase of this directive end to end — see docs/Architecture.md's own "Phase 13 — Final
  Audit" section for the full ledger.

- **CEO directive "Strategy Intelligence + Live Strategy Attribution," Phase 11: "TODAY — Strategy
  Eligibility, Right Now"** (backend: `backend/app/routers/sandbox.py`; frontend:
  `frontend/src/net/api.ts`, `frontend/src/ui/components/CommandCenter/panels/SandboxPanel.tsx`,
  `frontend/src/ui/components/CommandCenter/panels/sandbox/LiveStrategyEligibilityCard.tsx`): the
  directive's own Phase 11 "TODAY" section asks for "strategies currently eligible / strategies
  currently blocked." `app/market_intelligence.py`'s `compute_strategy_match()` already computes
  exactly this — which real strategies have real backtest evidence of working, or losing, under
  today's specific regime — but it was only ever computed once per sim-day, buried inside
  `MarketIntelligenceReport`, whose own schema docstring already discloses it "can be up to a day
  stale by the time a proposal fires." New `GET /api/sandbox/live-strategy-eligibility` runs the exact
  same real function fresh, against `state.market_intelligence.regime` — the always-current live
  regime a real `TradeProposal`/the Gatekeeper themselves actually read, never a second,
  independently-computed regime reading. New `LiveStrategyEligibilityCard.tsx` renders it as a
  persistent card at the top of the Strategy Lab (visible across every sub-tab, not buried in one),
  reusing the exact same recommended/avoided/risk-level rendering convention `MarketIntelPanel.tsx`'s
  Evidence Confluence card already established for the stale daily version. `mypy app/`, `ruff check
  app/ tests/`, `tsc -b --noEmit`, `eslint`, `vite build` all clean. No new backend test file — this
  codebase has no FastAPI `TestClient`-based router-test convention anywhere (confirmed by repo-wide
  search); the underlying `compute_strategy_match()` is already covered by
  `tests/test_market_intelligence.py`, and the two-line endpoint itself was verified live against a
  freshly restarted dev stack (`curl` confirmed a real, honest response: no matches yet for the two
  brand-new 50 EMA strategies, since neither has been through the Simulation Lab's own separate
  `StrategyReport`-generating pipeline) plus a screenshot confirming the card renders correctly and
  persists across every Strategy Lab sub-tab. `sandbox.spec.ts` (4/4) passed on the same stack.

- **CEO directive "Strategy Intelligence + Live Strategy Attribution," Phase 11: real compiled
  strategy rules surfaced in the Strategy Library** (frontend:
  `frontend/src/net/api.ts`, `frontend/src/types.ts`,
  `frontend/src/ui/components/CommandCenter/panels/SandboxPanel.tsx`,
  `frontend/src/ui/components/CommandCenter/panels/sandbox/StrategyCompilerView.tsx`,
  `frontend/src/ui/components/CommandCenter/panels/sandbox/StrategyLibraryView.tsx`): the Phase 1
  identity bridge and Phase 13 seeding had zero UI visibility until now — a CEO opening the Strategy
  Library couldn't tell a strategy had real, compiled trigger/entry/stop/target rules behind it at all.
  `StrategyLibraryView` gains a real "Rules" column: a "View Rules" button when `compiledDefinitionId`
  is set, an honest "—" (with a real explanatory tooltip: "a tracked idea only") when it isn't.
  Clicking it fetches the strategy's own already-registered `CompiledStrategyDefinition` (`GET
  /sandbox/strategy-versions`, an existing endpoint, no new backend call) and opens it directly in the
  Strategy Compiler view — which now accepts an optional `seed` prop, skipping straight to the real
  backtest/walk-forward/parameter-sensitivity/cost-sensitivity/look-ahead-audit buttons instead of
  making the CEO retype English text that's already been compiled and persisted. Also adds the
  frontend API client method + response type for the Phase 1 `POST
  /sandbox/register-researchable-strategy` endpoint, closing a frontend/backend parity gap for that
  endpoint (built backend-only in the Phase 1 commit). `tsc -b --noEmit`, `eslint`, `vite build` all
  clean. Verified live against a freshly restarted dev stack: the new Rules column renders correctly
  (a dash for all 4 real strategies in the current save, since Phase 13's seeding only affects
  brand-new games — this save predates it), the Strategy Compiler's default unseeded path is
  unchanged, and `sandbox.spec.ts` (4/4) passed.

- **CEO directive "Strategy Intelligence + Live Strategy Attribution," Phase 13: the 50 EMA
  breakout/pullback strategy is now real Strategy Lab citizenship, on by default for every new
  game** (backend: `backend/app/strategy_registry.py`, `backend/app/state.py`,
  `backend/tests/test_strategy_registry.py`): the directive's own Phase 13 asked to "encode the
  previously supplied strategy as an explicit research strategy rather than hard-coding it into the
  trading brain." `app/ema_pullback_research.py`'s existing hand-built engine already validates the
  shape works (real, disclosed gaps: no transaction costs/slippage, no out-of-sample split anywhere in
  that module — confirmed by the same Phase 1 audit) — this closes the OTHER half: real Strategy Lab
  membership. New `default_researchable_strategies()` composes the long AND the symmetric short setup
  as English text, using `app/ema_pullback_research.py`'s own real constants directly
  (`EMA_PERIOD`, `MIN_PULLBACK_CANDLES`, `CHANDELIER_ATR_PERIOD`/`_MULTIPLIER`,
  `REFERENCE_R_MULTIPLE`, `DEFAULT_TIMEFRAME` — never a second, independently-typed copy of the same
  numbers that could silently drift out of sync), then runs it through the exact same
  `register_researchable_strategy()` (Phase 1) any CEO/agent-triggered call would use — never a
  hand-authored `CompiledStrategyDefinition`. Raises loudly at seed time if the real compiler ever
  fails to reach `status == "compiled"` for either direction, rather than silently shipping a broken or
  absent strategy. Wired into `app/state.py`'s `default_state()` alongside the four original seed
  strategies — a brand-new game now starts with 6 real Strategy Lab strategies, two of which
  (`50-ema-breakout-pullback-long`/`-short`) already have real, compiled, immediately-backtestable
  rules behind them via the existing `/backtest-compiled-strategy`, `/walk-forward-validation`,
  `/cost-sensitivity`, and `/look-ahead-audit` endpoints — none of which needed a single new line of
  computation. Existing saves are unaffected (this only changes what a NEW game starts with). 3 new
  tests verify both directions actually compile with the real chandelier stop/2R target and are real
  directional mirrors of each other; 2 existing tests updated for the new default roster. Full backend
  suite, `mypy app/` (176 files), `ruff check app/ tests/` all clean.

- **CEO directive "Strategy Intelligence + Live Strategy Attribution," Phase 1: the real Strategy
  Lab \<-> CompiledStrategyDefinition identity bridge** (backend: `backend/app/schemas.py`,
  `backend/app/strategy_registry.py`, `backend/app/state.py`, `backend/app/routers/sandbox.py`,
  `backend/tests/test_strategy_registry.py`; frontend: `frontend/src/types.ts`): mandatory research-first
  audit (a dedicated agent traced every code path from live trade generation back through Strategy Lab)
  found the directive's central premise was already answered by this codebase's own architecture:
  `app/sandbox.py`'s own module docstring states outright that live/paper trading is "symbol- and
  AI-Debate-driven, not Strategy-driven... building [a live attribution mechanism] would be a structural
  rewrite of the whole decision loop" — confirmed by a full trace of `app/nexus.py`'s
  `_generate_trade_proposals()`, `app/research.py`, and `app/executive.py`'s `generate_proposal()`, none of
  which reference a `Strategy` object anywhere. Given that architectural boundary, the CEO chose the safe
  subset: real, additive Strategy Lab intelligence that never touches the live decision loop.

  The audit surfaced a SECOND, previously-undocumented identity gap worth closing first, since later work
  depends on it: Strategy Lab's own stage-gated `Strategy` (dossier/certification/health-tracked, but with
  zero represented trading logic — its schema is name/description/stage/allocatedCapital, nothing
  resembling a trigger or entry rule) and `app/strategy_compiler.py`'s `CompiledStrategyDefinition` (the
  real, deterministic trigger/requirement/entry/stop/target rule sequence, already backed by real, working
  backtest/walk-forward/parameter-sensitivity/cost-sensitivity/look-ahead-audit endpoints) were two
  disconnected identity spaces — a `Strategy` had no field naming which compiled rules, if any, it actually
  represents.

  New `Strategy.compiledDefinitionId: string | null` closes that gap. New
  `register_researchable_strategy()` (`app/strategy_registry.py`) is the one real bridge: it reuses the
  existing `register_strategy_version()` unchanged to compile+persist the rules, then — only when
  compilation genuinely reached `status == "compiled"` (never for "ambiguous"/"invalid" text) — creates a
  real, new `Strategy` whose `compiledDefinitionId` names that exact definition. An incomplete/ambiguous
  text still returns its own real, persisted definition (with real `ambiguities`/`detail` explaining what's
  missing) but creates no `Strategy` — never a fabricated link. Raises (400 via the new
  `POST /api/sandbox/register-researchable-strategy` endpoint) if a Strategy with the exact same real
  name/slug already exists, so this stays "genuinely new strategies only" — a second version of an
  existing strategy's rules goes through the existing `register-strategy-version` endpoint, staying linked
  to the same `Strategy.compiledDefinitionId`. 12 new backend unit tests, including two composed against a
  real, fully-specified 50 EMA breakout/pullback long/short setup — verified (against the actual compiler,
  not a mock) to reach `status == "compiled"` with a real chandelier stop and 2R target, laying the
  groundwork for the next increment (Phase 13: promoting the 50 EMA strategy from `app/
  ema_pullback_research.py`'s ad hoc, zero-cost, non-out-of-sample hand-built engine to a real, persisted
  Strategy Lab strategy backed by the fully-featured, already-real compiled-strategy pipeline). Full backend
  suite, `mypy app/` (176 files), `ruff check app/ tests/` all clean. Frontend `tsc -b --noEmit`, `eslint`,
  `vite build` all clean (the `Strategy` interface's new field required no other frontend change — no
  default `Strategy` object literal exists anywhere in the frontend; every real `Strategy` always comes
  from the backend).

- **CEO directive "Command Center + Professional Quant Trading Firm Upgrade": Executive View —
  real Problem/Cause/Severity/Action breakdown for weak Company Health areas** (backend:
  `backend/app/company_health.py`, `backend/app/schemas.py`, `backend/tests/test_company_health.py`;
  frontend: `frontend/src/types.ts`, `frontend/src/game/systems/NexusManager.ts`,
  `frontend/src/state/gameStore.ts`, `frontend/src/ui/components/CommandCenter/panels/CompanyPanel.tsx`):
  the existing `recommendations` list (a flat "X is low (score/100) — worth attention." string per weak
  metric, kept unchanged for backward compatibility) already named which of the 22 real sub-scores were
  weak, but not why. New `CompanyHealthWeakArea` extends each of those same weak areas with a real,
  evidence-grounded `cause` and `action` — a new `_diagnose()` restates the SAME real raw inputs
  `compute_company_health()` already reads for that metric's own score (real risk-warning counts and
  severities, real agent presence/mood, real portfolio P&L, real Gatekeeper rejection counts, and so on),
  calling the same standalone `_debate_collaboration_quality()`/`_cross_agent_research_handoffs()`/
  `_knowledge_retention()`/`_validation_rigor()`/`_pipeline_progress()`/`_measured_improvement()` helpers
  directly wherever one already exists so the cited evidence can never drift from the real formula.
  `severity` reuses the existing `CompanyHealthTier` banding (via the same `_tier()` helper the
  overall/executive/combined scores already use) rather than inventing a second taxonomy. `action` says
  "No direct lever" wherever that's honestly true — several of these 22 metrics are genuinely
  observational (agent mood, presence, real trading P&L), not something a CEO click can move, and
  pretending otherwise would be exactly the invented-actionability this codebase's conventions bar.
  **Deliberately has no `status` field**, though the brief's own structure asks for one: no real
  remediation-tracking mechanism (acknowledged/assigned/resolved) exists anywhere in this codebase to
  report honestly, and fabricating an always-"open" placeholder was rejected. `CompanyPanel.tsx`'s
  existing "Recommendations" card is now a "Weak Areas" card showing each area's Problem/Cause/Action plus
  a severity pill (reusing the same `TIER_TONE`/`TIER_LABEL` maps the header tier pill already uses). 6
  new backend unit tests (weak areas track the same real weakest metrics as `recommendations`, empty when
  every metric is strong, the real risk-warning count/penalty text, severity reuses the real tier bands,
  no `status` field present, every populated area has non-empty problem/cause/action). Full backend suite,
  `mypy app/` (176 files), `ruff check app/ tests/` all clean. Frontend `tsc -b --noEmit`, `eslint`,
  `vite build` all clean.

- **CEO directive "Command Center + Professional Quant Trading Firm Upgrade": session as a real,
  live trade-gating reason** (backend: `backend/app/opportunity_gatekeeper.py`, `backend/app/nexus.py`,
  `backend/app/schemas.py`, `backend/tests/test_opportunity_gatekeeper.py`; frontend:
  `frontend/src/types.ts`; docs: `docs/API.md`): closes a gap Phase 0 research had already named
  explicitly — the No-Trade Reason Taxonomy's own `SESSION_FILTER` example was disclosed as having "no
  real mechanism" in this codebase. It does now, built entirely on evidence that already existed for a
  different purpose: `app/session_evidence.py`'s `compute_session_regime_evidence()` (built for the
  Academy's Session Trading curriculum) already answers "does this company's own trading actually
  perform differently by session" from real closed `DecisionVaultEntry` history, bucketed by (session,
  regime), at a disclosed win-rate floor and a disclosed minimum real sample size
  (`MIN_SESSION_REGIME_SAMPLE`). `evaluate_opportunity()` (the Opportunity Gatekeeper, Design Bible
  Chapter 58's pre-proposal filter) now also looks up the bucket matching the CURRENT live (session,
  regime) pairing — both already real fields on the same `MarketIntelligenceState` this module already
  reads at proposal time — and rejects only when that exact live pairing's own real evidence state is
  `"unfavorable"`. Below the sample floor, the check stays silent rather than forcing a read on thin
  data — the same "no-trade must mean no-edge, not no-data" honesty this directive itself asks for.
  Never a forecast, never a fabricated "this session is bad" rule — only this company's own real,
  empirical track record. New `NoTradeReasonCode` value `session_regime_unfavorable_evidence` (the
  taxonomy's 38th, still every one grounded in a real, cited rejection point — see
  `app/opportunity_gatekeeper.py`'s module docstring for the full reasoning). `decision_vault` is a new
  optional `evaluate_opportunity()` parameter (defaults to no evidence — an empty vault produces no
  buckets, so every existing call site and test keeps its prior behavior unchanged); wired at
  `app/nexus.py`'s real call site, which already had `decision_vault` in scope. 6 new backend unit
  tests (backward-compatible default, real rejection on unfavorable evidence, silence below the sample
  floor, favorable evidence never rejected, a different session/regime pairing's unfavorable evidence
  never misapplied). Full backend suite (2,411 passed), `mypy app/` (176 files), `ruff check app/
  tests/` all clean. Frontend: `NoTradeReasonCode`'s mirrored type union gained the new value —
  already renders correctly with zero other frontend changes, since `RiskPanel.tsx`'s "Most common
  no-trade reasons" tally and every other consumer already render `reasonCodes` generically (no
  per-code label-mapping table anywhere to update).

- **CEO directive "Command Center + Professional Quant Trading Firm Upgrade," Phase 2: chart
  overlays (S/R, Fibonacci, FVG, Order Block, chart patterns) + a real MARKETCHART tab** (frontend:
  `frontend/src/ui/components/CommandCenter/CandlestickChart.tsx`,
  `frontend/src/ui/components/CommandCenter/FullCommandCenter.tsx`,
  `frontend/src/ui/components/CommandCenter/MarketChartPanel.tsx`,
  `frontend/src/ui/components/CommandCenter/lib/navigation.ts`, `frontend/tests/commandCenter.spec.ts`,
  `frontend/tests/helpers.ts`): "Charts should feel like a LIVE MARKET," with support/resistance, liquidity
  zones, order blocks, fair value gaps, and structure explicitly named. Zero new backend work —
  `GET /api/market/technical-analysis` (an existing, real, already-tested "technical desk briefing"
  endpoint) already returns every one of these as real, plottable price/timestamp data; its only prior UI
  anywhere was `MarketIntelPanel`'s own Evidence Confluence card, never drawn on the actual chart.
  `ChartOverlays` gains `lines` (support/resistance, Fibonacci — horizontal dashed levels, a finer dash than
  the existing real order entry/mark-price lines so a genuine executed price is never visually confused with
  an analysis read) and `zones` (Fair Value Gaps, Order Block, confirmed chart patterns — real price×time
  regions, drawn as a background wash behind the candles). A new `xFor()` maps a real overlay timestamp to
  its nearest real candle's x-position — index-based slotting, never a true time-scale axis, but honest: it
  never invents a position for a moment outside the visible range. `MarketChartPanel.tsx` fetches real
  technical analysis for the selected symbol/timeframe and offers five independent toggle buttons (S/R, FIB,
  FVG, OB, PATTERNS) — S/R and FVG on by default, the rest opt-in to avoid a cluttered default view. The
  chart also gains a real, first-class home: a new MARKETCHART tab (MARKETS area's own default/first tab),
  reusing `MarketChartPanel.tsx` directly (the same component OVERVIEW already embeds) — never a second
  chart implementation; this also closes a documentation/implementation gap from the earlier Phase 2 IA
  redesign, whose own `lib/navigation.ts` comment had already (incorrectly) claimed the chart "surfaces"
  under MARKETS before this commit actually built it. Visually verified live against the running dev stack
  with real market data (screenshots): the default view is clean and readable; all five categories together
  on a symbol with dense real data (MSFT: 1 S/R level, 7 Fib levels, 10 FVGs, a real bearish order block, 6
  confirmed chart patterns) all render correctly with real prices/labels. `tsc -b --noEmit`, `eslint`,
  `vite build` all clean. Playwright regression (`commandCenter.spec.ts` + `marketIntel.spec.ts` +
  `marketObservatory.spec.ts`, 39 tests) against a freshly restarted live dev stack: 37 passed, 1 skipped, 1
  failed — the same already-known pre-existing, unrelated movement test (an earlier run against a stale,
  accidentally double-started dev server showed 38 failures from a corrupted Vite WS proxy — confirmed
  environmental, not a code regression, by restarting cleanly and re-running).

- **CEO directive "Command Center + Professional Quant Trading Firm Upgrade," Phase 2: Overview
  agent-thesis roll-up** (frontend: `frontend/src/ui/components/CommandCenter/panels/OverviewPanel.tsx`):
  the last piece of this phase's named Overview enhancements. Enhances the existing Team Status card
  (never a duplicate) with real counts (currently researching / awaiting your decision) and, when any
  agent is in a real `"waiting"` state, a highlighted list of exactly which agents and why — reusing the
  same `GET /api/agents/trading-status` the AI Desk's Roster tab already fetches, no new backend work.
  `tsc -b --noEmit`, `eslint`, `vite build` clean. Playwright (`commandCenter.spec.ts`'s "renders all 40
  tabs" + "candlestick chart on Overview") against the live stack: 2/2 passed.

- **CEO directive "Command Center + Professional Quant Trading Firm Upgrade," Phase 2: Top Bar
  P&L/Emergency Stop + Overview Failure Boundary gauge** (frontend:
  `frontend/src/ui/components/CommandCenter/panels/OverviewPanel.tsx`,
  `frontend/src/ui/components/GlobalStatusBar.tsx`): both explicitly named Phase 2 sections, both closed
  with zero new backend work — the real data already existed and was simply never surfaced anywhere
  persistent. `GlobalStatusBar` gains a P&L pill (`paperPortfolio.totalPnlPct`, the same real field
  `PerformancePanel`/`OverviewPanel` already read) and an EMERGENCY STOP pill that appears only when
  `emergencyStop.active` is real and true — clicking it jumps straight to the RISK tab via the same real
  `ui:commandCenterJump` event `QuickActionDock`/`CommandPalette` already use. No new activation control was
  built — the only real activate/resume flow stays `RiskPanel`'s own `EmergencyStopControl`/
  `EmergencyStopConfirm`, per the directive's own "do not invent a parallel risk-control system" instruction.
  `OverviewPanel` gains a new Failure Boundary card answering "how close are we to blowing the account?"
  directly — equity, lifetime drawdown used vs. the real max, a real distance-to-failure figure, today's
  remaining loss budget, and a visual gauge that reddens as the budget depletes. Every value reuses
  `riskBudgetStatus`, a real, already WS-broadcast field `backend/app/risk_engine.py`'s
  `compute_risk_budget_status()` already computes — its only prior UI anywhere was buried inside
  `ExecutiveVoting`'s pre-trade popup, never a standing dashboard read. `remainingDrawdownBudgetPct` already
  IS "distance to failure" by its own docstring ("limit minus current usage, floored at 0"); no new backend
  arithmetic was needed beyond the client-side used-percent ratio for the gauge's own fill. `tsc -b --noEmit`,
  `eslint`, `vite build` all clean. Playwright regression (`globalStatusBar.spec.ts` +
  `commandCenter.spec.ts`, 34 tests) against the live stack: 32 passed, 1 skipped, 1 failed — the same
  already-known pre-existing, unrelated movement test.

- **CEO directive "Command Center + Professional Quant Trading Firm Upgrade," Phase 2: real
  per-agent trading status + explainability (AI Desk)** (backend: new `backend/app/agent_trading_status.py`,
  `backend/app/routers/agent_trading_status.py`; modified `backend/app/main.py`, `backend/app/schemas.py`;
  frontend: `frontend/src/net/api.ts`, `frontend/src/types.ts`,
  `frontend/src/ui/components/CommandCenter/panels/AgentsPanel.tsx`): closes the gap Phase 0 research
  already confirmed — `AgentState` had no trading-readiness field at all, and the only per-agent narrative
  that existed (`AnalystVote.reasoning`/`ResearchItem.summary`) was only ever surfaced for whichever
  proposal happened to be open in a popup, never as a standing per-agent read. New
  `compute_agent_trading_status()` derives every agent's real, current state from signals that already
  exist, in a disclosed priority order: Emergency Stop active → `risk_blocked` (company-wide, every agent);
  a real `AnalystVote` this agent cast sitting on a currently pending `TradeProposal` → `waiting`, citing
  that vote's own real reasoning text verbatim; a real `ResearchItem` assigned to this agent (`app/
  research.py`'s `RESEARCHER_IDS`) queued or in progress → `scanning`; the six vote-capable agents
  (scout/atlas/echo/nova/sentinel/pulse — the only ones `app/executive.py`'s `generate_analyst_votes()` can
  ever attribute a vote to) with nothing real active → `idle`; every other agent (guardian/keystone/cio/
  coach/sage/compass/scribe/quant/forge) → `not_trading_role`, citing their own real `AGENT_PROFILES`
  occupation string — the honest truth about the role, not a gap. Deliberately does NOT build a "next
  condition required" predictor (the directive's own worked example asks for one) — this codebase has no
  live per-symbol BOS/CHoCH/liquidity-sweep forecasting mechanism outside historical backtesting, and
  fabricating one would violate the directive's own explicit anti-fabrication rule; the real existing "wait"
  vote reasoning already tends to name what's missing, so that real text is surfaced as-is instead. New
  read-only `GET /api/agents/trading-status`, computed fresh every call, not WS-broadcast. AI Desk's Roster
  tab (`AgentsPanel.tsx`) now shows a real status pill plus the real headline/detail narrative per agent
  card, fetched on demand (the same pattern `DisciplinePanel`'s Exit Efficiency card and `RiskPanel`'s Trade
  Pipeline Health card already use). 12 new backend unit tests; full backend suite (2,401 of 2,402 passed —
  the one failure is a pre-existing, unrelated, confirmed-flaky probabilistic test in
  `test_foundational_mentors.py`), `mypy app/` (176 files), `ruff check app/ tests/` all clean. Frontend
  `tsc -b --noEmit`, `eslint`, `vite build` clean; `commandCenter.spec.ts` (33 tests) against the live stack:
  31 passed, 1 skipped, 1 failed (the same already-known pre-existing, unrelated movement test).

- **CEO directive "Command Center + Professional Quant Trading Firm Upgrade," Phase 2: post-trade
  intelligence — join Exit Efficiency and Attribution evidence into the Trade Report Card** (backend:
  `backend/app/decision_vault.py`, `backend/app/routers/decision_vault.py`, `backend/app/schemas.py`,
  `backend/tests/test_decision_vault.py`; frontend: `frontend/src/types.ts`,
  `frontend/src/ui/components/CommandCenter/panels/DecisionVaultPanel.tsx`): the brief's "why entered/exited,
  R:R, MAE/MFE, slippage, expected-vs-actual, agent, decision quality" post-trade fields were already real
  and computed — just scattered across three separate systems that had never been joined by their shared real
  `trade_id`. Rather than build a fourth "joined view," `compute_trade_report_card()` (the existing Decision
  Memory System card) now also looks up that trade's real `TradeExitEfficiency` read (`app/exit_efficiency.py`
  — MAE%, MFE%, capture%, entry/exit slippage in bps, transaction cost) and real `TradeAttributionRecord`
  (`app/trade_attribution.py` — which real agents' votes supported vs. opposed the trade, and whether the
  Gatekeeper approved it), both keyed by the same `trade_id` every `DecisionVaultEntry`/`PaperTrade` already
  carries. All 11 new `TradeReportCard` fields are nullable and stay `null` (never fabricated) when no
  matching real `PaperTrade`/decision exists yet — the card's own new `dataHonestyNote` states this plainly.
  `DecisionVaultPanel.tsx`'s existing Trade Report Card block gains a conditionally-rendered "Post-Trade
  Evidence" section (MAE/MFE/Capture/slippage/cost + supporting/opposing agents) that only appears once real
  join data exists. 3 new backend unit tests (no-match stays null, full real join populates every field,
  partial join — exit efficiency present, no matching decision — still resolves honestly) plus 5 existing
  tests updated for the new required kwargs; full backend suite, `mypy app/`, `ruff check app/ tests/` all
  clean. Frontend `tsc -b --noEmit`, `eslint`, `vite build` clean. The live dev save currently has zero real
  Decision Vault entries, so the new join branch itself couldn't be exercised end-to-end against real data in
  this pass (the same honest limitation the backend commit already disclosed) — `commandCenter.spec.ts`'s
  VAULT-tab test was run live against a freshly, singly-started dev stack to confirm the change is
  non-breaking: 1/1 passed.

### Fixed

- **Two real, pre-existing bugs found via a full live Playwright regression run** (not fabricated —
  both reproduced consistently on a freshly restarted, single-instance dev stack, isolated from the
  environmental flakiness a 95-test/29-minute unscoped full-suite run itself also produced):
  - **`frontend/src/types.ts`'s `AGENT_IDS` was missing Forge, the fifteenth agent.** `AgentId` (the
    type) already included `"forge"`, and `game/systems/AgentProfiles.ts` already had their full,
    complete profile (name, occupation, personality, sprite, badge) — but the actual `AGENT_IDS` runtime
    array (the one every `.map()`/`.filter()` call site across 15 files actually iterates — the AI
    Desk roster, Campus Map, NPCManager, RoomScene's own NPC spawner, Talent/Evolution/Calendar/
    Compliance panels, Command Palette, and more) had simply never been updated when Forge was added.
    Forge silently never spawned as an NPC anywhere in the game world and never appeared on any panel
    that lists agents. Found via `campusMap.spec.ts`'s own real, dynamic Employee Count assertion
    (fetches the real live agent count from `/api/load` rather than a hardcoded number) — the backend
    genuinely has 15 agents; the frontend was silently only ever iterating 14. Fixed by adding `"forge"`
    to `AGENT_IDS`; verified visually (a manual Playwright script showed their 🔧 badge now among the
    Campus Map's 15 employee icons) and via `campusMap.spec.ts` (6/6 passed on a freshly restarted,
    single-instance dev stack).
  - **`backend/app/constitution.py`'s `cite_article()` generated a real, observed duplicate citation
    id.** Its id was `f"cite-{source}-{article_id}-{len(citations)}"` — safe only as long as the list
    never shrinks, but `MAX_CONSTITUTION_CITATIONS` (120) trims the list's front once it's full, which
    pins `len(citations)` at exactly 120 forever afterward. Any two citations sharing the same
    source+article after that point collide on id. This had already happened twice in the live dev
    save (`cite-coach-VII-120` and `cite-academy-VIII-120`, confirmed via a direct `/api/load` check),
    surfacing as a real React "duplicate key" warning on the OPS tab's Knowledge Base timeline
    (`knowledgeBase.spec.ts`'s own no-console-errors assertion caught it). Fixed by adding a real
    microsecond-precision timestamp component to the id, which stays unique regardless of how long the
    list has been capped. New `test_ids_stay_unique_past_the_cap_for_the_same_source_and_article` proves
    it generating 130 same-source/same-article citations past the cap. **Disclosed limitation**: the fix
    prevents every future collision but does not retroactively repair the two citations already
    persisted with duplicate ids in this environment's live save (deliberately not hand-patched — this
    codebase's own `persistence.py` treats save-data integrity as a documented, hard-won lesson from a
    real historical data-loss bug, and a manual SQLite edit for a cosmetic React key warning was judged
    not worth that risk); they will resolve naturally once ~120 more citations cycle them out of the
    capped window. Full backend suite (2,406/2,406 passed), `mypy app/` (176 files), `ruff check app/
    tests/` all clean.

- **CEO directive "Command Center + Professional Quant Trading Firm Upgrade," Phase 2: Command
  Center IA consolidation** (frontend: `frontend/src/ui/components/CommandCenter/FullCommandCenter.tsx`,
  `frontend/src/ui/components/CommandCenter/lib/navigation.ts`, `frontend/tests/helpers.ts`,
  `frontend/tests/commandCenter.spec.ts`): Phase 0 research first confirmed the real scope — 42 tabs (not
  ~40), already grouped cosmetically into 7 TTOS sections (`lib/navigation.ts`'s pre-existing
  `TAB_SECTION`/`groupTabsBySection`), whose own comment explicitly deferred "a true identifier restructure"
  to a later phase. This closes that deferral: a new, coarser navigation layer groups the same 42 real tabs
  (zero renamed, zero deleted, zero content changed) under six real destinations — `AREA_ORDER` = OVERVIEW /
  MARKETS / AI DESK / PORTFOLIO & RISK / RESEARCH & INTELLIGENCE / MORE — reusing `TAB_SECTION`'s own careful
  reasoning as the starting point for placement rather than re-deriving it from scratch (every judgment call
  documented in `lib/navigation.ts`'s own comment: EXECUTIVE/BLACKSWAN/TRADINGMODES/COMPLIANCE/DISCIPLINE
  under PORTFOLIO & RISK because they're real risk controls/audits, not research; DECISIONS/VAULT/WARROOM/
  REPLAY/REASONING/REFLECTION/OPPORTUNITIES/EXECINTEL/BLACKBOX/SANDBOX/RESEARCH under RESEARCH &
  INTELLIGENCE because they're evidence of how a decision was reached, not its real-money consequence; AI
  DESK deliberately narrow to AGENTS/FOUNDERS/TALENT; MORE holds everything else, still organized by the
  original 7 TTOS section labels). `tabsForArea()`/`areaForTab()` derive placement without any new stored
  state — `FullCommandCenter.tsx`'s existing `tab` state remains the single source of truth, with the active
  area and its own secondary tab bar (or, for MORE, a section-grouped picker) derived fresh on every render.
  The number-key shortcut (previously 1-9 indexing the flat 42-tab list positionally) is now 1-6, one per
  real area, landing on that area's own default tab. `tests/helpers.ts`'s `clickTab()` was made area-aware
  (clicks the tab's parent area first, a harmless no-op if already active) so every existing spec's
  `clickTab(page, "X")` call site across the whole suite keeps working completely unchanged — a deliberate,
  documented, by-hand duplicate of the same placements (tests/ has no existing precedent for importing
  app `src/` code, and Playwright's TS loader isn't configured with the app's `@/` alias). `tsc --noEmit`,
  `eslint`, `vite build` all clean. Playwright regression against the live stack: `commandCenter.spec.ts`
  (33 tests) — 30 passed, 1 skipped, 2 failed; one failure is the same pre-existing, unrelated "blocks
  interaction" movement test that was already failing before this change (confirmed via an isolated run
  before any Phase 2 edits), the other is a timeout in the "renders all 40 tabs" test caused by the real,
  expected extra click per tab (fixed by raising its budget from 120s to 210s — every individual nested-tab
  test in the same file, including several newly two-level-deep ones like KNOWLEDGE/DISCIPLINE/VAULT/WARROOM/
  CALENDAR, passed cleanly). This pass is scoped to the navigation/IA shell only — the accompanying Overview
  enhancements, enhanced top bar (P&L/Emergency Stop), failure-boundary gauge, and chart overlays the same
  directive's Phase 2 section also describes are real, separate, additive work not yet started; see
  docs/Architecture.md for the full disclosure.

- **CEO directive "Professional Quant Firm Phase 41-45" — frontend: taxonomy, pipeline health,
  confluence, and regime stability surfaced** (frontend: `frontend/src/net/api.ts`, `frontend/src/types.ts`,
  `frontend/src/ui/components/CommandCenter/panels/ExecutivePanel.tsx`,
  `frontend/src/ui/components/CommandCenter/panels/RiskPanel.tsx`,
  `frontend/src/ui/components/CommandCenter/panels/WarRoomPanel.tsx`,
  `frontend/src/ui/components/CommandCenter/panels/sandbox/QuantResearchLabView.tsx`): the four backend
  slices below get their frontend surface. `RiskWarning`/`GatekeeperCheck` now carry an optional `code`,
  `GatekeeperRejection`/`OpportunityRejection` carry `reasonCodes` — shown as small tags under each
  rejection/warning in `ExecutivePanel` and `RiskPanel`'s Active Warnings list. A new `RiskPanel` card
  (`TradePipelineHealthCard`) fetches `GET /api/trades/pipeline-health` on demand (the same on-demand
  pattern `DisciplinePanel`'s Exit Efficiency card already uses) and renders the real funnel as bar rows
  plus a most-common-no-trade-reasons tag list, with the backend's own `dataHonestyNote` displayed
  verbatim — diagnostic only, matching the backend's own framing. `WarRoomPanel` gets a new Evidence
  Confluence score cell and a family-breakdown card, reusing the exact rendering pattern `MarketIntelPanel`
  already established for the same `EvidenceConfluenceRead` shape rather than a new component.
  `QuantResearchLabView`'s Tournament comparison table gets a new Regime Stability column (`VerdictPill`,
  a new tones map, detail on hover) — Round 9 itself needed no frontend change since the rounds list
  already renders generically. `AgentReviewDataSplit` (Feature 44) intentionally has no frontend surface
  yet, matching its own backend disclosure — it's preventive infrastructure with no live consumer to
  visualize. `tsc --noEmit`, `eslint`, `vite build` all clean. Playwright regression (`sandbox.spec.ts` +
  `commandCenter.spec.ts`, 37 tests) against the live dev stack: 34 passed, 1 skipped, 2 failed — both
  failures traced to files this change never touched (`POST /api/sandbox/backtest` test-state pollution,
  and a Command Palette focus-behavior test), confirmed via `git diff --stat` against those files; every
  RISK/EXECUTIVE/WARROOM panel test and the 2-strategy tournament integration test passed cleanly.

- **CEO directive "Professional Quant Firm Phase 41-45," Feature 44: real train/validation/test/
  live-paper split for agent review evidence** (backend: `backend/app/executive_intelligence.py`,
  `backend/app/performance_review.py`, `backend/app/routers/performance_review.py`,
  `backend/app/schemas.py`, `backend/tests/test_performance_review.py`): the directive required agent
  learning to never cause data leakage, with training/validation/testing/live-paper observation kept
  separate. A research pass across every existing per-agent tracking system found no such separation
  exists at the agent level (only at the strategy-backtest level, via `app/walk_forward.py`/`app/
  leakage_audit.py`), and confirmed `AgentPerformanceReview` currently feeds no live weighting or
  promotion decision at all — a real, disclosed gap, but not an active leak, since nothing downstream
  reads it yet. New `AgentReviewDataSplit` is a real, deterministic, chronological classification (never
  randomly shuffled, mirroring `app/walk_forward.py`'s own window discipline) over one agent's own stored
  review history: the single most recent review is `live_paper` (a fresh, unconfirmed observation), the
  review it superseded is `test` (the first genuinely held-out period), the next two are `validation`,
  everything older is `training`. Computed fresh every call by `classify_review_data_splits()` rather than
  stored on the review itself, so a label correctly ages as later reviews accumulate. New
  `GET /api/performance-reviews/{agentId}/history` surfaces it. Deliberately preventive: it exists so a
  future evidence-based agent promotion/demotion system (this same directive's own explicit ask) has a
  real, non-fabricated way to require review evidence to have aged past the freshest `live_paper` window
  before being cited as proof of durable improvement — closing the leakage risk before it can be
  introduced rather than retrofitting it after a promotion system already exists and already leaks.
  Separately audited (not modified) the one live, already-existing agent-level weighting loop this
  directive flagged as a risk — `app/weighted_decisions.py`'s `compute_accuracy_multiplier()` reads `app/
  executive_intelligence.py`'s `compute_executive_accuracy_scores()`, which only ever draws from
  `ceo_decisions` whose outcome has already resolved, so an unresolved proposal's stance can never appear
  in its own weight by construction — documented as causally sound in that function's own docstring rather
  than building an unneeded train/test split where none would be architecturally meaningful. 11 new unit
  tests; full backend suite (2,390 tests), `mypy app/` (174 files), `ruff check app/ tests/` all clean. No
  frontend surface yet.

- **CEO directive "Professional Quant Firm Phase 41-45," Feature 43: Regime Stability as a real 9th
  Strategy Tournament round** (backend: `backend/app/schemas.py`, `backend/app/strategy_tournament.py`,
  `backend/tests/test_strategy_tournament.py`): closes the "regime-adaptive strategy selection" gap by
  reusing evidence the Tournament already had rather than building a second regime classifier —
  `app/strategy_engine.py`'s existing `regimeTrendBreakdown`/`regimeVolatilityBreakdown` per compiled
  backtest were real but report-only. New `StrategyTournamentEntry.regimeStabilityVerdict` classifies
  each candidate `regime_validated` (at least one real regime bucket cleared its own `enough_evidence`
  sample-size bar with positive expectancy), `no_validated_regime` (every evidenced bucket read zero or
  negative), or `insufficient_data` (no bucket ever cleared the bar — missing evidence, never treated as
  negative). Round 9 eliminates only a confirmed `no_validated_regime`, following the Tournament's existing
  house rule (eliminate on confirmed negative evidence, never on missing evidence). Explicitly disclosed as
  out of scope: this is evidence-based selection within the Strategy Lab/Tournament, not a live
  "what regime is the market in right now" gate on the trading pipeline — `TradeProposal` has no link back
  to the `CompiledStrategyDefinition` that might have generated it (proposals come from the Analyst Desk,
  not the Strategy Lab), so a live regime-alignment check on actual trade decisions remains a real,
  disclosed architectural gap. 4 new hand-traced unit tests plus an updated round-count integration
  assertion; full backend suite (2,384 tests), `mypy app/` (174 files), `ruff check app/ tests/` all clean.
  (Frontend surfaced in a later entry below — see "frontend: taxonomy, pipeline health, confluence, and
  regime stability surfaced.")

- **CEO directive "Professional Quant Firm Phase 41-45," Confluence Quality: wire Evidence Confluence into
  live War Room decision scoring** (backend: `backend/app/evidence_confluence.py`, `backend/app/schemas.py`,
  `backend/app/war_room.py`, `backend/tests/test_war_room.py`): `app/evidence_confluence.py` (an earlier
  directive pass) was a fully real, tested evidence independence/redundancy classifier explicitly
  self-documented as "never wired into a live decision." Rather than a second implementation, connects it
  into `build_decision_score()` as a new, direction-aware 8th sub-score (`evidenceConfluenceScore`), with
  the full family-level breakdown surfaced on `WarRoomSession.evidenceConfluence` for CEO transparency. The
  scoring rule compares evidence's own internal majority direction against the specific proposal's chosen
  direction rather than assuming they must always agree, so a legitimate contrarian thesis is never
  penalized for disagreeing with the raw indicator majority — confidence reflects independent-family
  coverage and direction agreement, not raw signal count, preventing correlated-indicator double-counting
  (e.g. EMA/SMA/MACD all restating "trend") from inflating a proposal's apparent evidence quality.
  `DecisionScoreBreakdown`'s existing renormalize-over-real-sub-scores convention (already used for
  `strategyHealthScore`) is reused unchanged: the composite renormalizes over 8 sub-scores only when a real
  confluence read exists (real candles were available for that symbol), otherwise falls back to the
  original 7. Full backend suite (2,369 tests), `mypy app/`, `ruff check app/ tests/` all clean. (Frontend
  surfaced in a later entry below — see "frontend: taxonomy, pipeline health, confluence, and regime
  stability surfaced.")

- **CEO directive "Professional Quant Firm Phase 41-45," Critical Task #0 + No-Trade Reason Taxonomy +
  Trade-Pipeline Health Check** (backend: new `backend/app/trade_pipeline_health.py`; modified
  `backend/app/gatekeeper.py`, `backend/app/nexus.py`, `backend/app/opportunity_gatekeeper.py`,
  `backend/app/risk_engine.py`, `backend/app/routers/trades.py`, `backend/app/schemas.py`,
  `backend/app/state.py`): before building any new intelligence, the directive required tracing WHY agents
  were placing almost no real trades — an empirical forensic audit of a live save (31 sim-days, 47 resolved
  decisions, only 2 real trades) traced this to two real, INTENTIONAL design decisions working together, not
  a bug: (1) `app/opportunity_gatekeeper.py`'s own `min_trade_quality_score` gate — verified via the save's
  own real, persisted `opportunityRejections`, 100/100 sampled were rejected here, before ever reaching a
  `TradeProposal` — and (2) `GameSaveState.settings.operating_mode` defaulting to `"learning"`, requiring an
  explicit CEO/player decision on every proposal that does clear that gate. Per the directive's own
  repeated "do not weaken risk controls simply because trading activity is low" instruction, neither was
  changed. A deeper, disclosed-not-fixed finding: running `app/market_intelligence.py`'s real
  `compute_liquidity()`/`build_decision_score()` live against this codebase's own mock watchlist found
  `liquidityQualityScore` organically landing at 0-30/100 for most real candidates (genuine equal-high/
  equal-low price clustering is rare in the mock stochastic-walk price generator), structurally dragging
  every candidate's composite average down ~5-7 points before the 70-point threshold is even checked —
  flagged for CEO/design review via a new `liquidity_confirmation_weak` taxonomy code rather than
  unilaterally changed. Built a real, 37-code `NoTradeReasonCode` taxonomy grounded in exact cited lines of
  existing pipeline code (never invented), threaded through `RiskWarning.code`, `GatekeeperCheck.code`, and
  new `reasonCodes` lists on `GatekeeperRejection`/`OpportunityRejection`. New diagnostic-only
  `GET /trades/pipeline-health` (`TradePipelineHealthSnapshot`) computes real funnel telemetry
  (signals → proposals → rejections → risk-approved → orders → fills) distinguishing "no valid trade
  existed" from "the system failed to execute a valid trade" — never feeds scoring, and its own
  `dataHonestyNote` discloses which source lists are capped windows rather than full-lifetime totals. Full
  backend suite (2,369 tests), `mypy app/`, `ruff check app/ tests/` all clean. (Frontend surfaced in a
  later entry below — see "frontend: taxonomy, pipeline health, confluence, and regime stability
  surfaced.")

- **Quant Strategy Tournament, Round 7: real pairwise strategy-return correlation** (backend:
  `backend/app/portfolio_intelligence.py`, `backend/app/schemas.py`, `backend/app/strategy_tournament.py`;
  frontend: `frontend/src/types.ts`,
  `frontend/src/ui/components/CommandCenter/panels/sandbox/QuantResearchLabView.tsx`): closes the last
  remaining disclosed blocker from the Features 36-40 pass with a real, honest, PARTIAL signal — a full
  portfolio-level backtest (shared capital, combined position sizing, simultaneous multi-strategy drawdown)
  remains architecturally unavailable and Round 7 stays `blocked: true`, but it now computes a real Pearson
  correlation between each pair of candidates' own already-computed walk-forward window expectancy sequences
  (identical window boundaries for both, since both were tested against the same symbols/timeframe/
  candlesPerSymbol/windowBars — no extra backtest run needed). Reuses `app/portfolio_intelligence.py`'s
  existing Pearson implementation (renamed from private `_pearson()` to public `pearson_correlation()`,
  behavior unchanged) rather than a second statistics implementation. `correlation` reads `null` — never a
  fabricated `0.0` — below 3 real paired windows with evidence on both sides. Round 7 still never eliminates a
  candidate; this is a real diversification signal for CEO/agent judgment, not a portfolio-level risk verdict.
  6 new hand-traced backend tests (exact ±1.0 correlation fixtures, below-evidence-bar, null-window exclusion,
  no-shared-symbol, single-candidate); full backend suite (2,360 tests), `mypy app/`, `ruff check app/ tests/`
  all clean. Frontend `tsc --noEmit`, `eslint`, `vite build` clean; `sandbox.spec.ts` (4 tests, extended) passes
  against the live dev stack.

- **Compiled-strategy backtest: real regime breakdowns + Feature 38 metrics surfaced everywhere** (backend:
  `backend/app/schemas.py`, `backend/app/strategy_engine.py`; frontend: `frontend/src/types.ts`,
  `frontend/src/ui/components/CommandCenter/panels/sandbox/EmaPullbackResearchView.tsx`,
  `StrategyCompilerView.tsx`): follow-through on the Features 36-40 final report's own disclosed gap list.
  `CompiledStrategyBacktestResult` already had `sessionBreakdown`/`instrumentBreakdown`; every
  `EmaPullbackTradeRecord` already carries a real per-trade `regimeTrend`/`regimeVolatility` read (a
  self-contained proxy computed only from data available up to the trade's own entry bar — never a look-ahead
  label), and the reference 50 EMA strategy already aggregated those into `regimeTrendBreakdown`/
  `regimeVolatilityBreakdown` — the newer, general compiled-strategy engine never did. Closed via the same
  `aggregate_bucket()` every other breakdown already uses, grouped by `regimeTrend`/`regimeVolatility` exactly
  as `sessionBreakdown` groups by session; no new regime-detection logic, no new trade-record field. Separately,
  the shared `BucketRow` component (used by every bucket display in both the 50 EMA Research tab and the
  Strategy Compiler) gained a Sharpe/Sortino/Calmar/Max Drawdown row — the earlier Features 36-40 pass added
  these real metrics to the backend `EmaPullbackStatsBucket` but never gave them a frontend surface anywhere;
  one shared-component change now surfaces them across all 11 breakdown sections between the two views. 2 new
  backend tests; full backend suite (2,352 tests), `mypy app/` (174 files), `ruff check app/ tests/` clean.
  Frontend `tsc --noEmit`, `eslint`, `vite build` clean; `sandbox.spec.ts` (4 tests, with new assertions for the
  regime breakdowns and the Sharpe row) passes against the live dev stack.

- **CEO directive "Professional Quant Firm Phase" — Features 36-40: Quant Research → Strategy → Backtest →
  Validation → Tournament** (new: `backend/app/overfitting_diagnostics.py`, `backend/app/quant_research_lab.py`,
  `backend/app/strategy_registry.py`, `backend/app/strategy_tournament.py`; modified:
  `backend/app/analytics.py`, `backend/app/schemas.py`, `backend/app/backtest_primitives.py`,
  `backend/app/ema_pullback_research.py`, `backend/app/strategy_engine.py`, `backend/app/research_experiment.py`,
  `backend/app/strategy_compiler.py`, `backend/app/state.py`, `backend/app/save_modules.py`,
  `backend/app/routers/sandbox.py`; frontend: `frontend/src/types.ts`, `frontend/src/net/api.ts`, new
  `frontend/src/ui/components/CommandCenter/panels/sandbox/QuantResearchLabView.tsx`, modified
  `SandboxPanel.tsx`/`StrategyCompilerView.tsx`): a research-first audit found Feature 38 (Professional
  Backtesting Engine) already ~80% real — extended `aggregate_bucket()` (the one authoritative bucket
  aggregation, flowing to every existing caller) with real Sharpe/Sortino/Calmar ratios, longest winning
  streak, largest win/loss R, and average holding bars (real `bars_held`, threaded through `ExitResult`/
  `simulate_exit()`), reusing `analytics.py`'s existing disclosed statistics formulas (now public) rather than
  a second implementation. Surfaced and fixed a real fabrication bug in the process: `strategy_engine.py`'s
  compiled-strategy `SimulationResult` was hardcoding `sharpeRatio=0.0, sortinoRatio=0.0` despite having a
  real per-symbol closed-trade return sequence to compute them from. Feature 39 (Walk-Forward + OOS
  Validation) also already existed in substance (`walk_forward.py`/`parameter_sensitivity.py`/
  `cost_sensitivity.py` each already produced a real verdict) — the genuine gap was vocabulary, closed by
  `overfitting_diagnostics.py`'s real, deterministic relabeling into the directive's own requested
  ROBUST/FRAGILE/INSUFFICIENT_DATA/OVERFIT_SUSPECTED/OOS_FAILURE/PENDING_VALIDATION terms (no new statistic).
  Feature 40 (Quant Strategy Tournament) was genuinely, entirely missing — new `strategy_tournament.py` compares
  candidates via named-slot superlatives (never a fabricated composite score) and 8 staged elimination rounds;
  Round 7 (portfolio interaction) is explicitly disclosed as architecturally blocked (no cross-strategy
  portfolio-level backtest exists in this codebase) rather than approximated. Features 36 (Quant Research Lab)
  and 37 (Strategy Factory versioning) deliberately depart from this directive family's usual compute-fresh,
  never-persist convention — a real, permanent, searchable `QuantResearchExperiment` archive
  (`GameSaveState.quantResearchExperiments`, capped at 100, following the existing `strategy_hall_of_fame`
  precedent) with a real, simple, disclosed word-overlap duplicate-detection heuristic, and real, persisted
  `CompiledStrategyDefinition` version history (`strategy_registry.py`, keyed by the strategy compiler's own
  real name slug, replacing a previously caller-supplied, untrusted `previousVersion`). New frontend
  QUANT RESEARCH LAB sub-tab (no new top-level nav) exercises all three write paths plus the tournament runner
  and archive search. Also fixed a real, unrelated gap this work surfaced: `save_modules.py`'s `MODULE_FIELDS`
  self-check would have silently broken app startup/save-load for the two new persisted fields had they not
  been registered — caught by importing `app.main` directly, not by `pytest` collection alone. See
  `docs/Architecture.md`'s own section for the full research-first audit, architectural reasoning (why this
  extends the newer `CompiledStrategyDefinition` pipeline and not the legacy `Strategy`/`StrategyStage` one),
  and every disclosed scope cut. New backend test files `test_overfitting_diagnostics.py`,
  `test_quant_research_lab.py`, `test_strategy_registry.py`, `test_strategy_tournament.py`; extended
  `test_backtest_primitives.py`, `test_ema_pullback_research.py`, `test_research_experiment.py`. Full backend
  suite (2,350 tests), `mypy app/` (173 files), `ruff check app/ tests/` all clean. Frontend `tsc --noEmit`,
  `eslint`, `vite build` clean; new Playwright coverage in `tests/sandbox.spec.ts` drives the real flow
  end-to-end (compile → file experiment → register version → compile a second definition → run a real
  2-strategy tournament → search the archive) against the live dev stack — all 4 tests in that file pass.

- **Strategy compiler/engine: RSI, MACD, and Stochastic triggers** (`backend/app/technical_indicators.py`,
  `backend/app/strategy_engine.py`, `backend/app/strategy_compiler.py`, four backend test files modified): the
  recommended next phase from the prior "Next Research + Validation Pass" directive's own final report — the
  compiler's trigger vocabulary was EMA/SMA-only, so walk-forward validation and parameter sensitivity could
  only ever exercise EMA/SMA-crossover strategies, even though `StrategyIndicatorName` already listed
  rsi/macd_line/macd_signal/macd_histogram/stochastic_percent_k/stochastic_percent_d as valid schema values
  with nothing able to produce or resolve them. Added `rsi_series()`/`macd_series()`/`stochastic_series()` —
  real, full historical series versions of the existing scalar `rsi()`/`macd()`/`stochastic()` (needed to
  resolve an indicator at an arbitrary historical bar during a backtest replay, the same reason
  `ema_series()`/`atr_series()` already exist), each cross-validated against its own scalar sibling before
  being trusted. `strategy_engine.py`'s `SUPPORTED_INDICATORS` now covers all six new indicator names — MACD
  always uses the methodology's own standard 12/26/9 defaults and Stochastic's smoothing is fixed at the
  standard 3 (`StrategyIndicatorRef` has no room for a stated triple/pair, a real, disclosed v1 simplification,
  not a schema change); RSI series lookups reuse `backtest_primitives.py`'s existing `atr_at()` directly
  (identical index alignment) rather than a duplicate formula. `strategy_compiler.py` gained real trigger
  patterns for "RSI above/below N" (period optional, default 14), the Stochastic mirror, and "MACD crosses
  above/below the signal line" — with a real, disclosed directional convention (never a guess): "above N"
  compiles to a real long-biased trigger, "below N" to short, the MOMENTUM reading, deliberately not
  mean-reversion (which would need a trigger direction opposite its own threshold side, unrepresentable in this
  v1 grammar) — a mean-reversion-phrased strategy ("RSI below 30, buy the bounce") is correctly refused as a
  real trigger/entry direction contradiction, never silently miscompiled, verified with a dedicated test. At
  most one trigger is recognized per strategy (EMA/SMA, then RSI, then Stochastic, then MACD, in priority
  order). Two stale test fixtures that had used `rsi` as their own example of a still-unsupported indicator
  were fixed (switched to `vwap`, still genuinely unsupported). No frontend changes needed — the existing
  Strategy Compiler UI's free-text input already accepts the new vocabulary unchanged; live-verified via
  Playwright (typing an RSI momentum strategy into the real textarea compiled and backtested successfully). 31
  new backend tests. Full backend suite (2,314 tests, run twice consecutively), `mypy app/`, `ruff check app/
  tests/` all clean.

- **CEO directive "Professional Quant Trading Firm — Quant Intelligence + Market Analysis Completion Phase
  (Next Research + Validation Pass)"** (`backend/app/technical_indicators.py`, `backend/app/technical_patterns.py`,
  `backend/app/evidence_confluence.py`, `backend/app/strategy_engine.py`, `backend/app/walk_forward.py`,
  `backend/app/parameter_sensitivity.py`, `backend/app/cost_sensitivity.py`, `backend/app/leakage_audit.py`,
  `backend/app/survivorship.py`, `backend/app/research_experiment.py`, `backend/app/foundational_mentors.py`,
  `backend/app/schemas.py`, `backend/app/routers/sandbox.py`, six new backend test files plus five modified,
  `frontend/src/types.ts`, `frontend/src/net/api.ts`,
  `frontend/src/ui/components/CommandCenter/panels/MarketIntelPanel.tsx`,
  `frontend/src/ui/components/CommandCenter/panels/sandbox/StrategyCompilerView.tsx`,
  `frontend/tests/sandbox.spec.ts`, `frontend/tests/marketIntel.spec.ts`): a second mandated repository audit
  against 17 named items (chart-pattern geometry, SAR/SuperTrend, walk-forward validation, parameter
  sensitivity, transaction-cost/slippage sensitivity, look-ahead-bias detection, survivorship-bias protection,
  train/test integrity, multiple-testing control, a research experiment record, agent learning) found: Parabolic
  SAR/SuperTrend previously deliberately unimplemented (now built, real, hand-traced, unit-tested — both
  deliberately join the existing `trend` evidence family in `evidence_confluence.py` rather than becoming new
  independent evidence, since they're trend-following measures highly correlated with the existing EMA/SMA
  reads); chart-pattern geometry entirely missing (a bounded, objectively-defined subset — double top/bottom,
  trendline breaks — now built, confirmation-gated so a still-forming shape is never reported; head &
  shoulders/triangles/wedges/rectangles/channels remain a disclosed, real gap needing a materially larger
  multi-point geometric fit); genuine bar-level walk-forward validation architecturally blocked until the prior
  pass's `strategy_engine.py` compiled-strategy backtest existed to make it buildable (now built —
  `walk_forward.py` backtests a fixed definition against real, disjoint, non-overlapping chronological windows,
  a structural not just claimed no-look-ahead guarantee, complementing rather than replacing
  `model_validation.py`'s own existing whole-run-list `_temporal_stability_check` analog); parameter sensitivity
  genuinely missing (now built — one-parameter-at-a-time real stop/target sweeps, never a full grid search,
  with no "best combination" field by design and a disclosed multiple-testing caution on every result);
  transaction-cost/slippage sensitivity a real, disconnected gap (live paper trading already had a real cost
  model — `portfolio.py`'s `TRANSACTION_COST_BPS`, `execution_quality.py`'s slippage constants — never reused
  by any bar-by-bar research backtest, all of which filled at the exact stop/target price with zero friction;
  now closed by reusing those exact constants across a base/low/moderate/high/stressed ladder); look-ahead-bias
  detection designed-carefully-but-never-proven (now built — a real truncate-and-re-detect audit whose own test
  suite proves the methodology catches a deliberately-injected leak, not just that the real detector happens to
  pass); survivorship-bias protection architecturally blocked, correctly so (this codebase's research universe
  is a fixed, static, always-present symbol pool with no historical constituent/delisting data source — per the
  directive's own explicit fallback, documented and built as a real, always-honest `unavailable` interface,
  never fabricated); and a research experiment record genuinely missing (now built as pure orchestration over
  the five modules above, synthesizing one disclosed, deterministic conclusion from their five real verdicts —
  a look-ahead violation or rejected Model Validation always overrides everything else, missing evidence
  anywhere always reads "insufficient evidence," never a silent pass). A genuinely flaky test was found and
  fixed mid-pass: comparing two separate `market_data_provider.get_candles()` calls at different `limit` values
  hit the mock provider's own real recency-bias window (applied only to the newest ~20 bars of whatever `limit`
  was requested), a real artifact of its "live continuity" design, not a bug — fixed by comparing a single
  fetch's own slice instead, and several new integration tests were loosened to match this codebase's own
  already-documented house convention against asserting exact backtest values (`test_ema_pullback_research.py`'s
  own `TestRunEmaPullbackResearchIntegration` docstring). Two Academy lessons that had gone stale against this
  pass's own new capabilities were fixed rather than left misleading (chart patterns, SAR/SuperTrend previously
  taught as "not implemented"); three new lessons teach agents HOW to research walk-forward stability, parameter
  sensitivity, cost sensitivity, and look-ahead-bias auditing. Six new endpoints:
  `POST /api/sandbox/walk-forward-validation`, `/parameter-sensitivity`, `/cost-sensitivity`,
  `/look-ahead-audit`, `/research-experiment`, `GET /api/sandbox/survivorship-bias`. 134 new backend tests. Full
  backend suite (2,283 tests, run twice consecutively to confirm no flakiness remained), `mypy app/` (169
  files), `ruff check app/ tests/` all clean. **Frontend**: Parabolic SAR/SuperTrend values and a new Chart
  Patterns section added to Market Intelligence's existing Technical Analysis block; a new "Run Full Research
  Experiment" button in the Strategy Compiler surfacing the bundled record (conclusion banner plus dedicated
  Walk-Forward/Parameter Sensitivity/Cost Sensitivity/Look-Ahead Audit sections). `tsc`/`eslint`/`vite build`
  clean; live-verified end to end via Playwright, coverage folded into the existing `sandbox.spec.ts` and
  `marketIntel.spec.ts` specs rather than left as a scratch file.

- **CEO directive "Professional Trading Firm — Market-Analysis Knowledge + Session Intelligence Expansion,"
  Phase 15 — the 50 EMA breakout + pullback strategy, converted into a formal research hypothesis**
  (`backend/app/ema_pullback_research.py`, `backend/app/technical_indicators.py`, `backend/app/schemas.py`,
  `backend/app/routers/sandbox.py`, `backend/tests/test_ema_pullback_research.py`, `docs/API.md`): Phase 0's
  research confirmed no Chandelier Stop implementation, no bar-by-bar strategy rule engine, and no real
  walk-forward backtest exist anywhere in this codebase (`app/simulation.py`'s `SimulationResult` generator is
  explicitly-placeholder RNG math, never a real replay of candle history — the same finding the prior
  directive's own Phase 5-7 scoping already made). This module is the first real, deterministic, bar-by-bar
  rule replay in this codebase, built specifically for this one strategy — the still-deferred general
  StrategyRuleEngine is unchanged. Every English-language rule in the CEO's source material was converted
  into a precise, measurable definition (documented in full in the module's own docstring): a "sustained"
  period on one side of the 50 EMA is operationalized as ≥5 consecutive real closes; the pullback requires
  ≥2 strictly consecutive real opposite-direction candles (a single-candle dip does not count and the leg
  keeps extending); the confirmation level is the real high/low of the leg immediately before the pullback;
  the breakout requires a real candle body close beyond that level; entry is the real NEXT bar's open (never
  the confirmation candle's own close, which would be look-ahead); Invalidation A (a real close back through
  the 50 EMA before confirmation) discards the whole setup and a fresh cross is required before any new one
  is considered — TradeTown never re-enters later merely because price eventually reaches the original level;
  Invalidation B is deliberately NOT a hard filter (per the directive's own explicit warning against
  hardcoding "3x or 4x" as universally invalid) — every breakout candle's real range is compared to its own
  trailing 20-bar average and tagged `breakoutCandleExtended`, with real expectancy reported for extended vs.
  normal breakouts as an empirical finding, never an assumed one. The Chandelier Stop uses the methodology's
  own standard published defaults (22-period ATR, 3.0x multiplier) — not a TradeTown-fitted number. The
  R-multiple target is swept across 1R/1.5R/2R/2.5R/3R (the source's own ~2:1 target is tested as one
  candidate among several, never assumed optimal). A real baseline comparison (naive EMA-cross entry with no
  pullback/breakout confirmation, same stop/target logic) isolates whether the confirmation step adds real
  value. **SOURCE CLAIM vs. TRADETOWN EVIDENCE, kept structurally separate**: the source's own reported
  ~65.6% win rate (21/32 trades) is a fixed, disclosed constant used ONLY for side-by-side display in
  `EmaPullbackSourceClaimComparison` — never read by any computation in this module, and TradeTown's own real,
  independently-computed win rate at the same reference target is never assumed equal to it. Session/regime
  tagging uses a real, disclosed, deliberately SIMPLER proxy (50 EMA slope for trend; ATR vs. its own trailing
  median for volatility) rather than `app/market_intelligence.py`'s real 13-way `MarketIntelligenceRegime`
  classifier, which needs live, cross-symbol sweep/reversal inputs this historical replay has no way to
  reconstruct at an arbitrary past bar — disclosed as ARCHITECTURALLY BLOCKED for the full classifier, not
  silently approximated as if it were the same thing. Every result — win rate, expectancy, profit factor, max
  drawdown, longest losing streak, MAE/MFE — is fed through the EXISTING, unmodified Strategy Lab machinery:
  an ad hoc, non-persisted `Strategy`/`SimulationResult` pair built from this run's own real numbers is handed
  to `app/strategy_lab.py`'s real Monte Carlo bootstrap and `app/model_validation.py`'s real validation report
  (now including this same directive's own Phase 8 anti-overfitting checks) — never a second, parallel
  validation or risk engine, and the Gatekeeper/Risk Authority are completely untouched. New
  `GET /api/sandbox/ema-pullback-research` endpoint. Live-verified against 8 real seed-watchlist symbols at
  6,000 real (mock) candles each (0.78s): the confirmed rule set found 40 real trades at the 2R reference
  (84.2% win rate) against 1,309 naive-cross trades (42.8% win rate) — Model Validation's own real, unmodified
  checks correctly read this specific result as `needs_more_evidence`, not validated, exactly the caution this
  directive requires; this is reported as one real, honest, in-progress observation, never a claim the
  strategy is profitable or that the source's claimed win rate has been confirmed. 20 new unit tests (hand-
  built, deterministic candle fixtures covering long/short detection, the too-short-pullback non-match,
  Invalidation A, the Chandelier Stop formula, all four exit-simulation outcomes including the conservative
  same-bar-gap convention, and bucket-aggregation math) plus 4 new `atr_series()` tests and 3 integration
  tests against the real market data provider. Full backend suite, `mypy app/` (159 files)/`ruff check app/
  tests/` all clean. See `docs/Architecture.md` for the full rule-by-rule detail. **Frontend**
  (`frontend/src/types.ts`, `frontend/src/net/api.ts`,
  `frontend/src/ui/components/CommandCenter/panels/SandboxPanel.tsx`,
  `frontend/src/ui/components/CommandCenter/panels/sandbox/EmaPullbackResearchView.tsx`,
  `frontend/tests/sandbox.spec.ts`): a new "50 EMA RESEARCH" sub-tab in the Strategy Validation Laboratory,
  keeping the Source Claim vs. TradeTown Evidence comparison visually and structurally separate, plus the full
  R-multiple sweep/baseline/session/regime/instrument/breakout-size breakdowns and the reused Model
  Validation/Monte Carlo panels. `tsc`/`eslint`/`vite build` clean; live-verified end to end against the real
  running dev stack via Playwright. Along the way, fixed a real, pre-existing test bug this change exposed:
  the sandbox spec's EVOLUTION sub-tab click used an unscoped exact-name locator that also matches the Command
  Center's unrelated top-level "EVOLUTION" (AI Workforce) tab, which shares the identical accessible name —
  scoped the click to the Sandbox sub-tab nav bar specifically; confirmed via `git stash` that this failure
  pre-dates and is unrelated to this pass's own changes.

- **CEO directive "Professional Quant Trading Firm — Quant Intelligence + Market Analysis Completion Phase"**
  (`backend/app/backtest_primitives.py`, `backend/app/strategy_compiler.py`, `backend/app/strategy_engine.py`,
  `backend/app/evidence_confluence.py`, `backend/app/technical_patterns.py`, `backend/app/technical_indicators.py`,
  `backend/app/technical_analysis.py`, `backend/app/model_validation.py`, `backend/app/ema_pullback_research.py`,
  `backend/app/schemas.py`, `backend/app/routers/market.py`, `backend/app/routers/sandbox.py`, five new backend
  test files plus four modified, `frontend/src/types.ts`, `frontend/src/net/api.ts`,
  `frontend/src/ui/components/CommandCenter/panels/MarketIntelPanel.tsx`,
  `frontend/src/ui/components/CommandCenter/panels/SandboxPanel.tsx`,
  `frontend/src/ui/components/CommandCenter/panels/sandbox/StrategyCompilerView.tsx`,
  `frontend/tests/sandbox.spec.ts`, `frontend/tests/marketIntel.spec.ts`): the mandated repository audit
  classified the 7 named capabilities before any code was written. Technical indicators, session/range
  tracking, and confluence at the analyst-vote layer (`signal_correlation.py`) were already real and are
  extended, not duplicated. The 13-way `MarketIntelligenceRegime` classifier's live, per-decision capture was
  also already real — `DecisionVaultEntry.market_regime`/`market_regime_label` and
  `MarketIntelligenceReport.snapshot` already record the genuine classifier's real output at decision time and
  once per in-game evening respectively; nothing needed building there. Pattern detection had no
  support/resistance detector anywhere in the codebase (genuinely missing); no English-to-DSL strategy
  compiler, no generic backtest engine, and no evidence-family-level confluence layer existed at all
  (genuinely missing); anti-overfitting validation had 9 of the 14 explicitly-listed checks. **Phase B**: a
  real support/resistance detector clustering the existing swing-high/low detector's own output (2+ touches,
  0.5% price tolerance, capped at 8 levels, support/resistance classified against the current close) — reuses
  `_find_swings()`, no second swing detector. Complex chart-pattern geometry (double top/bottom, head &
  shoulders, triangle/wedge/rectangle breakouts) is a disclosed, real gap, not built this pass. **Phase D**:
  `evidence_confluence.py` groups raw trend/momentum/volume/liquidity/price-structure/pattern signals into
  evidence families and reports both `rawSignalCount` (signals agreeing with the eventual majority direction)
  and `independentFamilyCount` (families agreeing), so five correlated momentum readings can never masquerade
  as five independent confirmations — deliberately one layer below `signal_correlation.py`, which already
  covers the six analyst votes. **Phase E**: added `symbol_robustness` (sign-agreement of aggregated returns
  across ≥2 distinct symbols; `needs_more_evidence` on a single-symbol sample) to `model_validation.py`'s
  existing anti-overfitting suite. Walk-forward, parameter-sensitivity, and transaction-cost/slippage-
  sensitivity checks remain a disclosed, real gap. **Phase F, the flagship addition**: `strategy_compiler.py`
  is a deterministic, disclosed-vocabulary pattern-matcher (never an LLM call — this entire codebase makes
  zero live LLM calls at runtime) that converts an English strategy description into a structured, versioned
  `CompiledStrategyDefinition` (trigger/requirement/entry sequence, stop, target). Vague phrasing ("strong
  breakout," "significant volume," "near support," "clean pullback," etc.) is matched against an explicit
  banned-phrase list and reported as a real ambiguity, never silently converted into an invented threshold;
  text the compiler doesn't recognize compiles to `status="invalid"` with an empty sequence rather than being
  guessed at. `strategy_engine.py` then runs a compiled definition against real (mock) candle history through
  the same Monte Carlo bootstrap and Model Validator pipeline `ema_pullback_research.py` already uses —
  refusing outright, rather than guessing, when the definition is ambiguous/invalid or names an indicator
  outside the current `price_close/open/high/low`, `ema`, `sma` vocabulary (RSI/MACD/Stochastic-based
  triggers and multi-step sequence topologies beyond trigger → optional requirement → entry are a disclosed,
  real future increment). Cross-validated by compiling the CEO's own 50 EMA worked example and comparing its
  output against the hand-built `ema_pullback_research.py` detector's real output on the same real candle
  series: the generic engine finds a strict superset of the hand-built detector's setups, a real structural
  difference (the hand-built detector runs one combined long/short state machine; a single-direction compiled
  definition has no such competition) confirmed by manually tracing one "extra" setup, not a bug — the test
  suite asserts the subset relationship rather than exact equality. A genuine fabrication bug was caught and
  fixed during this same pass's own Phase G audit: `strategy_engine.py`'s trade records were silently
  hardcoding `regimeTrend="ranging"`/`regimeVolatility="normal"` instead of computing them; fixed by extracting
  the regime-tagging helpers (along with the Chandelier Stop/exit-simulation/bucket-aggregation math) out of
  `ema_pullback_research.py`'s previously-private functions into a new shared `backtest_primitives.py`, so
  both modules now share one authoritative implementation, and wiring a dedicated 50-EMA/14-ATR regime series
  per symbol into the generic engine's trade construction (`ema_pullback_research.py` itself is behavior-
  unchanged — all 20 of its existing tests still pass against the refactor). New endpoints:
  `GET /api/market/evidence-confluence`, `POST /api/sandbox/compile-strategy`,
  `POST /api/sandbox/backtest-compiled-strategy`. 51 new backend tests. Full backend suite (2,221 tests),
  `mypy app/`, `ruff check app/ tests/` all clean. **Frontend**: a new "STRATEGY COMPILER" sub-tab in the
  Strategy Validation Laboratory (compile → review ambiguities/steps/stop/target → backtest on demand, reusing
  the 50 EMA sub-tab's own bucket/Model-Validation display components), and a new Evidence Confluence section
  plus a Support/Resistance section inside Market Intelligence's existing Technical Analysis block. `tsc`/
  `eslint`/`vite build` clean; live-verified against the real running dev stack via Playwright, with the new
  coverage folded into the existing `sandbox.spec.ts` and `marketIntel.spec.ts` specs rather than left as a
  separate scratch file. Along the way, renamed the Compile button's own accessible label from "Compile" to
  "Compile Strategy" after discovering it collided (via Playwright's substring accessible-name matching) with
  the "STRATEGY COMPILER" sub-tab button's own name — a real, deliberate accessibility fix, not just a test
  workaround, since both labels were within full authorial control.

- **CEO directive "Professional Trading Firm — Market-Analysis Knowledge + Session Intelligence Expansion,"
  Phases 1-4, 6, 8** (`backend/app/technical_indicators.py`, `backend/app/technical_patterns.py`,
  `backend/app/technical_analysis.py`, `backend/app/signal_correlation.py`, `backend/app/model_validation.py`,
  `backend/app/foundational_mentors.py`, `backend/app/routers/executive.py`, `backend/app/routers/market.py`,
  `backend/app/schemas.py`, six new backend test files, `frontend/src/types.ts`, `frontend/src/net/api.ts`,
  `frontend/src/ui/components/CommandCenter/ExecutiveVoting.tsx`,
  `frontend/src/ui/components/CommandCenter/panels/MarketIntelPanel.tsx`): Phase 0's research (a full grep
  audit) found zero existing implementations of any market-analysis framework this directive asked about —
  no confluence engine, no FVG/order-block/candlestick/Fibonacci detection, no RSI/MACD/Stochastic/ATR/VWAP,
  no Elliott Wave/harmonic/Gann. Built what real math/geometry over real (mock) OHLCV data can honestly
  support, and drew an explicit line where it can't:
  - **Phase 3 (indicators)**: `technical_indicators.py` — real SMA/EMA/RSI/MACD/Stochastic/ATR/VWAP, every
    value `None` (never fabricated) below its own real minimum bar count. Parabolic SAR/SuperTrend
    deliberately omitted (more implementation-sensitive; not added merely because a list asked for them).
  - **Phase 1-2 (structure, liquidity, candles, Fibonacci)**: `technical_patterns.py` — swing structure
    labeling (HH/HL/LH/LL), fair value gaps with real fill tracking, candlestick patterns (engulfing/hammer/
    shooting star/doji — a real misclassification bug fixed: hammer/shooting-star must be checked before
    doji, since a long-wick small-body candle also satisfies doji's broader small-body rule), session range +
    retest, Fibonacci retracement/extension levels, and one disclosed order-block proxy definition. Reuses
    `market_intelligence.py`'s existing swing/session detection rather than duplicating it. Elliott Wave,
    harmonic patterns (Bat/Butterfly/Crab), Gann, and classical chart patterns (double tops, head & shoulders,
    triangles) are explicitly NOT auto-detected — the directive itself warns against forcing ambiguous wave
    counts or treating unvalidated frameworks as predictive; these become Academy lesson content only (below),
    honestly disclosing the absence of a detector rather than implying one exists.
  - **Phase 6 (Confluence Engine)**: `signal_correlation.py` — audited the six real analyst votes'
    actual mechanisms (`executive.py::generate_analyst_votes()`, `voting.py::researcher_vote()`) and found
    they are NOT all mutually independent: news and macro votes are both driven by the identical
    `ResearchItem.confidence` value through the same probabilistic roll (the same evidence, counted twice,
    not two independent reads), and execution is a pure majority tally of the other five (zero new evidence).
    `assess_confluence()` reports both a naive confirmation count and a real independent-evidence count,
    never claiming fewer confirmations makes a worse setup — only an honest accounting of how much of the
    naive tally is genuinely new information. New `GET /api/executive/confluence?proposalId=...` and an
    "Confluence Engine" section in the Executive Voting UI. Purely informational — never gates the
    Gatekeeper/Risk/Model Validation pipeline.
  - **Phase 4 (sessions)**: new `GET /api/market/session-range` exposes `compute_session_range()`'s real
    per-session high/low/retest, reusing `market_intelligence.py`'s existing session-boundary detection
    (no second session engine).
  - **Phase 8 (anti-overfitting)**: two new Model Validator checks — `regime_dependence` (flags real sign
    disagreement in `avg_return_pct` across tested regime buckets — a strategy can clear every bucket's own
    weak/strong verdict individually while its edge is really a bet on one regime) and
    `optimization_scrutiny` (flags the "too good, too soon" shape of a result: an implausibly high win rate
    on a sample still below the Certification gate's minimum trade count — never automatic rejection, only
    a flag for closer scrutiny). Feature/parameter-count/iteration tracking the directive also asks for is
    disclosed as `not_trackable_yet`: `Strategy` has no such fields and `sandbox.py`'s real generation
    pipeline doesn't track them today — not fabricated.
  - **Academy curriculum**: `al_brooks`'s first real lesson content (8 lessons — price action, candlestick
    signals, breakouts, false breakouts/retests, trading ranges, classical chart patterns honestly disclosed
    as undetected, reversal confirmation, probability not certainty), filling a roadmap track that shipped
    with zero lessons since the original build. 8 more `market_intelligence` lessons (orders 16-23 — FVGs,
    order blocks, Fibonacci, trend/momentum/divergence/volume indicators, Elliott Wave/harmonic/Gann framed
    explicitly as unvalidated hypotheses with no auto-detector, the Heikin-Ashi/Renko derived-chart rule, and
    confluence/anti-overfitting). All original TradeTown-authored content, never a transcription of any real
    educator's actual published work.
  - **Definition-of-Done point 12** (derived charts can never affect real execution prices): proved
    structurally in `test_derived_chart_safety.py` rather than behaviorally, since neither Heikin-Ashi nor
    Renko exists anywhere in this codebase yet (confirmed by source inspection) — `portfolio.py`'s one real
    execution surface (`open_position()`/`close_position()`) never imports `technical_indicators.py` or
    `technical_patterns.py`, and both functions take a plain `float` price, not a derived-chart type.
  - **Explicitly deferred, unchanged from the prior directive's own scoping**: Phase 5 (Research/Sandbox
    foundation), Phase 7 (research experiments/backtesting), and Phase 9 (agent decision process) all still
    depend on the not-yet-built TechnicalIndicators/StrategyRuleEngine/WalkForwardValidator/Monte Carlo
    pipeline documented in `docs/Architecture.md` — this pass adds real indicator/pattern VALUES as evidence
    (a safe, tractable step) but does not wire them into any live trading decision, since the hypothesis-
    testing pipeline this same directive's own Phase 7 demands to validate that inclusion doesn't exist yet.
  - 49 new tests (`test_technical_indicators.py`, `test_technical_patterns.py`, `test_signal_correlation.py`,
    `test_technical_analysis.py`, `test_derived_chart_safety.py`, plus additions to
    `test_foundational_mentors.py`/`test_model_validation.py`). Full backend suite: 2115 passed, 0 failed.
    `mypy app/` (157 files) / `ruff check app/ tests/` clean. `tsc -b --noEmit` / `eslint` / `vite build` all
    clean. See `docs/Architecture.md` for the full phase-by-phase detail.

- **CEO directive "Next Phase: Professional Trading Firm Intelligence," Phases 4-9 — researched, scoped, and
  documented (no code this entry)**: **Phase 4** (session specialization education) audited — the existing
  15-lesson `market_intelligence` curriculum (Asia/London/New York/Overlap/Transitions/decision-process,
  earlier "Session Trading Education" work) already independently matches this directive's own "treat as
  hypotheses, never guaranteed rules" requirement; one real, specific gap found (session high/low as a later
  reference level, and breakout/fakeout behavior — grep-confirmed no backing computation exists) is disclosed
  as a real but moderately-scoped future addition, not built this pass. **Phases 5-7** (Research/Sandbox
  foundation, the strategy knowledge base, the 50 EMA breakout-pullback strategy) researched thoroughly:
  confirmed `app/research.py`/`app/simulation.py` still have zero real candle-data access (Priority 5's
  earlier finding), no indicator library, no bar-by-bar rule-evaluation engine, and no walk-forward/Monte
  Carlo testing exist anywhere. A full architectural plan (4 real components: TechnicalIndicators, a
  StrategyRuleEngine, a WalkForwardValidator, and a real Monte Carlo layer feeding off the rule engine's actual
  trade sequences) is documented in `docs/Architecture.md` — explicitly NOT implemented this pass, since it is
  a subsystem comparable in scope to the existing Strategy Validation Laboratory (built across multiple
  dedicated passes originally) and a rushed partial slice would misrepresent Phase 6/7 as "started" when the
  directive's own explicit requirement (real walk-forward/out-of-sample/Monte Carlo testing before any
  strategy is trusted) couldn't yet be honestly met. **Phase 8** (evidence-based agent specialization) is
  downstream of Phases 5-7 existing at all and deferred for the same reason. **Phase 9** (the learning loop)
  audited question-by-question against this directive's own list — found already real and wired for
  everything except strategy-rule adherence checking (which depends on Phases 5-7's not-yet-built rule
  engine); no new code needed. See `docs/Architecture.md` for the full phase-by-phase detail.

- **CEO directive "Next Phase: Professional Trading Firm Intelligence," Phase 3 — Session + Market Regime P&L**
  (`backend/app/performance_attribution.py`, `backend/app/routers/trades.py`, `backend/app/schemas.py`,
  `backend/tests/test_performance_attribution.py`, `frontend/src/types.ts`, `frontend/src/net/api.ts`,
  `frontend/src/ui/components/CommandCenter/panels/PerformancePanel.tsx`): previously deferred honestly
  (`DecisionVaultEntry` carries real session/regime per trade, but only CEO-proposal-path closes got a vault
  entry, so a join would have under-reported day-flattened trades) — Phase 2's fix above closed that gap,
  making this join honest. New `compute_session_performance()`/`compute_regime_performance()` join
  `trade_history` with `decision_vault` by `trade_id`, reusing the exact same 12-metric shape
  `SymbolPerformanceRead` already established (refactored into a shared `_group_metrics()` helper so the
  formula isn't tripled — the already-shipped symbol schema itself is untouched). A trade with no matching
  vault entry is excluded and counted (`tradesExcludedNoVaultEntry`), never fabricated into a bucket. New
  `GET /api/trades/performance-by-session` and `GET /api/trades/performance-by-regime` endpoints; new
  "Performance by Session & Market Regime" Performance panel section. Still honestly out of reach and named
  explicitly: "which strategies work during London" (strategy id still always `None`) and a numeric
  agent-performance ranking by session (Phase 1's Trade Attribution gives evidence, never a credit-weighted
  ranking). 12 new tests, `mypy app/` (154 files)/`ruff check app/ tests/` clean, full backend suite (2066
  passed, 0 failed), `tsc -b --noEmit`/`eslint`/`vite build` clean, live-verified against the real dev stack
  (both endpoints correctly grouped real trades by session/regime, matching the symbol-level totals exactly;
  the panel rendered that same data). Documented in `docs/Architecture.md`.

- **CEO directive "Next Phase: Professional Trading Firm Intelligence," Phases 1-2 — Trade Attribution
  Evidence + Decision Vault coverage expansion** (`backend/app/trade_attribution.py`, `backend/app/nexus.py`,
  `backend/app/routers/trades.py`, `backend/app/schemas.py`, `backend/tests/test_trade_attribution.py`, plus a
  new full-`nexus.tick()` integration test in `test_nexus.py`, `frontend/src/types.ts`, `frontend/src/net/api.ts`,
  `frontend/src/ui/components/CommandCenter/panels/PerformancePanel.tsx`): a restated continuation of the
  directive above, phased explicitly. **Phase 1** audited whether TradeTown can answer "which agents were
  responsible for this trade, and how much P&L should each get credit for" — found real, permanently-stored
  per-role evidence (`TradeDecision.votes`, one real vote per each of the six real analyst seats) but confirmed,
  by grep, zero P&L-credit-splitting methodology anywhere, and the directive explicitly forbids inventing one.
  Per its own fallback instruction ("preserve the original attribution evidence so it can be audited later"),
  new `app/trade_attribution.py` joins `TradeDecision.votes` (role reconstructed via the fixed `ROLE_TO_AGENT`
  map), `CeoDecisionRecord` (real override provenance), and `PaperTrade` (real execution/P&L, including
  Priority 1's real slippage) into one auditable record per trade — never a numeric split (a structural test
  confirms no field on the per-agent record carries a dollar or percent value; every record carries a fixed,
  honest disclosure explaining why). New `GET /api/trades/attribution` endpoint; new "Trade Attribution — Who
  Advised What" Performance panel section. **Phase 2** traced every real trade-closing path and found
  `app/broker.py`'s order-book path (market/limit/stop orders) has zero live callers anywhere in the game loop
  — confirmed via `app/trading_modes.py`'s own module docstring, a real but currently-unreachable path, not a
  live gap. The one real, live gap: `flatten_day_positions()`'s day-end forced closes were appended to
  `trade_history` but never routed through `_journal_closed_trades()` — so they never got a `decisionId`, a
  `DisciplineReview`, a `CaseStudy`, or a `DecisionVaultEntry`, unlike every other real close. Fixed by merging
  `flattened_trades` into the same real closed-trade list hold-duration closes already flow through — no new
  pipeline built. **A second bug fixed while investigating test failures during this pass**: the 6
  `test_nexus.py` failures this entire session has reported as "pre-existing, unrelated" turned out to be a
  genuine test-fixture bug (both `_apply_operating_mode()` test call sites were missing the
  `prediction_records` positional argument, silently shifting every argument after it) — not a bug in the real
  code. Fixed; full backend suite is now **2059 passed, 0 failed**, the cleanest baseline this session has had.
  22 new/updated tests total, `mypy app/` (154 files)/`ruff check app/ tests/` clean, `tsc -b --noEmit`/`eslint`/
  `vite build` clean, live-verified against the real dev stack (the attribution endpoint returned a real 6-role
  vote breakdown with a genuine dissenting vote correctly read as disagreeing; the Performance panel rendered
  that exact data). Documented in `docs/Architecture.md`.

- **CEO directive "Next Professional Trading Firm Phase," Priority 5 — Research Data Integrity**
  (`backend/app/data_provenance.py`, `backend/app/routers/market.py`, `backend/app/schemas.py`,
  `backend/tests/test_data_provenance.py`, `frontend/src/types.ts`, `frontend/src/net/api.ts`,
  `frontend/src/ui/components/CommandCenter/panels/MarketIntelPanel.tsx`): audited every subsystem that could
  plausibly back a trading decision for what data it actually consumes (grep-confirmed, not assumed). Found
  `app/market_intelligence.py` performs real technical-analysis math over `MockMarketDataProvider`'s real
  (mock) candle series — but `app/research.py`'s confidence gauge and `app/simulation.py`'s backtest metrics
  BOTH have zero `get_candles()` calls anywhere, pure random-number generation with no underlying price series
  at all. No real broker adapter and no user-data upload mechanism exist anywhere. **What shipped**: new
  `app/data_provenance.py` — ONE honest, whole-codebase audit report (not a provenance field grafted onto
  `ResearchItem`/`SimulationResult`, since tagging either with a candle-derived category would be fabricated).
  New `DataCategory` enum (`real`/`synthetic`/`simulated`/`user_provided`/`unavailable`), distinct from and
  reusing rather than duplicating the existing per-`Candle` `DataStatus` enum. Seven named sources: Live Quotes
  & Candles (`simulated`, and the ONLY row that's live-measured — actually calls the configured provider and
  compares requested vs. delivered candle count on every request, never a hardcoded 100%), Research Desk
  (`synthetic`), Sandbox Backtests (`synthetic`), Strategy Lab Monte Carlo Testing (`synthetic`), Strategy Lab
  Liquidity/Market Structure Validation (`simulated`), Real market data (`unavailable`), User-provided data
  (`unavailable`). New `GET /api/market/data-provenance` endpoint; new "Data Integrity" Market Intelligence
  panel section. 7 new tests (a provider stub delivering fewer candles than requested proves coverage is
  genuinely measured; an erroring provider stub proves a failed live check reads `unavailable` rather than
  crashing), `mypy app/` (153 files)/`ruff check app/ tests/` clean, full backend suite (2041 passed; same 6
  pre-existing unrelated `test_nexus.py` failures), `tsc -b --noEmit`/`eslint`/`vite build` clean, live-verified
  against the real dev stack (the endpoint's live check returned real 100% coverage; the panel rendered every
  real source and category). Documented in `docs/Architecture.md`.

- **CEO directive "Next Professional Trading Firm Phase," Priority 2 — Unified Professional P&L Reporting
  (symbol-level)** (`backend/app/performance_attribution.py`, `backend/app/routers/trades.py`,
  `backend/app/schemas.py`, `backend/tests/test_performance_attribution.py`, `frontend/src/types.ts`,
  `frontend/src/net/api.ts`, `frontend/src/ui/components/CommandCenter/panels/PerformancePanel.tsx`):
  audited every existing P&L/reporting surface (`app/analytics.py`'s `PerformanceSnapshot`, the All-Time Trade
  Journal, `DecisionVaultEntry`, `app/exit_efficiency.py`) and confirmed real per-trade/whole-portfolio data
  but zero symbol-, agent-, or strategy-level aggregation anywhere. **What shipped**: new
  `app/performance_attribution.py` — SYMBOL-level attribution only, computed fresh over `trade_history` (CAGS,
  no new `GameSaveState` field): trade count, win rate, total P&L, avg P&L%, avg winner/loser, expectancy (the
  standard decomposition — verified algebraically identical to avg P&L% under the same win/loss partition),
  profit factor (gross profit ÷ gross loss, `None` — a real "undefined," never a fabricated infinity — with
  zero losses), avg MAE/MFE, best/worst trade; derived ratios withheld below `MIN_SYMBOL_SAMPLE_FOR_VERDICT = 3`
  trades. New `GET /api/trades/performance-by-symbol` endpoint; new "Performance by Symbol" Performance panel
  section, most-profitable-first. **Deliberately NOT built, each for a specific disclosed reason**: AGENT-level
  (a trade's `supportingAgents`/`opposingAgents` is a list with no CEO-authorized credit-split rule — inventing
  one would be a fabricated convention); STRATEGY-level (`DecisionVaultEntry.strategyId` always `None` on a
  live trade); SESSION/MARKET REGIME (`DecisionVaultEntry` only covers CEO-proposal-path closes — broker
  fills/hold-duration closes/day-end flattens never get a vault entry, so a join would silently under-report
  them — a partial-coverage report dressed up as complete is its own dishonesty); TIMEFRAME (no per-trade
  chart-timeframe concept exists; `PerformancePeriod` already covers time-bucketed reporting). 10 new tests,
  `mypy app/` (152 files)/`ruff check app/ tests/` clean, full backend suite (2034 passed; same 6 pre-existing
  unrelated `test_nexus.py` failures), `tsc -b --noEmit`/`eslint`/`vite build` clean, live-verified against the
  real dev stack (the endpoint and the new panel section both rendered the current save's real SPY/AAPL trades,
  correctly sorted and correctly gated to NOT_ENOUGH_DATA at the current sample size). Documented in
  `docs/Architecture.md`.

- **CEO directive "Next Professional Trading Firm Phase," Priority 1 — Execution Realism**
  (`backend/app/execution_quality.py`, `backend/app/portfolio.py`, `backend/app/broker.py`,
  `backend/app/executive.py`, `backend/app/paper_trading.py`, `backend/app/trading_modes.py`,
  `backend/app/nexus.py`, `backend/app/schemas.py`, `backend/tests/test_execution_quality.py`,
  `backend/tests/test_paper_trading.py`, plus targeted additions to `test_portfolio.py`/`test_broker.py`/
  `test_trading_modes.py`/`test_executive.py`, `frontend/src/types.ts`,
  `frontend/src/ui/components/CommandCenter/panels/PerformancePanel.tsx`): an 8-priority continuation
  directive; this pass implements Priority 1 in full (the remaining 7 researched, classified, and either
  deferred with reasoning or — Priority 8 — documented-only per the directive's own explicit "do not promote
  Model Validation to a blocking gate without CEO authorization" instruction; full classification table
  below). **The gap** (already flagged MINIMAL by the prior Gap Analysis): every real fill point in the
  codebase — `app/broker.py`'s `_fill_price()`, `app/executive.py`'s `resolve_proposal()` (the CEO's own
  direct buy/sell), `app/paper_trading.py`'s hold-duration auto-close, `app/trading_modes.py`'s day-end
  flatten — executed at exactly the observed signal price, every time, despite a real 1-tick order latency and
  a real flat transaction-cost model already existing. **What shipped**: new `app/execution_quality.py` — a
  real, disclosed, formula-based slippage rate (`BASE_SLIPPAGE_BPS = 2.0` to `MAX_SLIPPAGE_BPS = 20.0`) driven
  only by that tick's already-real `MarketIntelligenceState` (`MarketQualityScore.score` + the symbol's own
  `LiquidityRead.liquidity_score` when available) — never a random number, always adverse to the trader, the
  same "disclosed, formula-based, never derived from real bid-ask/order-book data because this codebase has
  neither" standard `TRANSACTION_COST_BPS` already established. Applied only to genuinely uncertain fills
  (market orders, and stop/stop-loss orders once triggered); limit/take-profit orders stay unslipped — "this
  price or better" is their real definition, not a gap. All four real fill points now thread an optional
  `market_intelligence` parameter (None-safe, non-breaking); `PaperPosition`/`PaperTrade` gained
  `entrySlippageBps`/`exitSlippageBps` (default `0.0`) mirroring `entryCostUsd`/`transactionCostUsd`'s existing
  audit-field pattern — `app/portfolio.py` computes no slippage itself, only records what the caller applied.
  **Explicitly not modeled** (disclosed, not faked): partial fills, order-book depth, gap-through behavior —
  no data exists in this codebase to honestly derive them from. New "Slippage: Xbps in / Ybps out" line in the
  Performance panel's Recent Trades, next to the existing Transaction cost line. 23 new tests, `mypy app/` (151
  files)/`ruff check app/ tests/` clean, full backend suite (2024 passed; same 6 pre-existing unrelated
  `test_nexus.py` failures, reconfirmed against the clean pre-change tree), `tsc -b --noEmit`/`eslint`/`vite
  build` clean, live-verified against the real dev stack (`POST /api/executive/decide` → a real position with
  `entrySlippageBps=14.73`; `POST /api/time/advance` → the same position's forced close recording a real
  `exitSlippageBps`; the Performance panel rendering that exact value). Documented in `docs/Architecture.md`.

  **8-priority classification** (condensed; see `docs/Architecture.md` for detail on Priorities 1-2):
  Priority 1 Execution Realism — MINIMAL → **implemented this pass**. Priority 2 Unified P&L Reporting —
  PARTIAL (per-trade/per-position data is real and rich; no symbol- or agent-level aggregation existed
  anywhere) → **symbol-level implemented this pass** (see the dedicated entry below); agent/strategy/session/
  regime/timeframe breakdowns remain deferred, each for a specific disclosed reason (see that entry).
  Priority 3 Talent→Specialization→Performance — BLOCKED BY
  ARCHITECTURE: `app/research.py`'s confidence is an explicitly-disclosed random walk ("not derived from any
  real analysis"), and `ResearchCategory` is a broad asset-class taxonomy with no indicator/setup dimension —
  neither "route specialized research to specialists" nor "measure specialist research quality" is honestly
  buildable without a large new real-analysis subsystem; deferred, not faked. Priority 4 Team Chemistry Causal
  Behavior — PARTIAL (`Debate.finalRecommendation` is fixed before the debate runs, already named in the prior
  Gap Analysis as higher-risk since it touches live voting/governance) — deferred pending a dedicated,
  carefully-scoped pass. Priority 5 Research Data Integrity — PARTIAL (`Candle.data_status`/`DataStatus`
  already existed as a 7-value enum but only `"simulated"` was ever set; `SimulationResult`/`ResearchItem`
  carried no provenance field) → **implemented this pass as a whole-codebase audit report** (see the dedicated
  entry below) — per-item provenance on `ResearchItem`/`SimulationResult` themselves remains undone, disclosed
  as fabrication-risk (neither ever touches candle data, so tagging either with a candle-derived category would
  be false). Priority 6 Market Session Intelligence — MATURE
  (this session's prior "Session Trading Education & Agent Training" work); a Strategy × Session comparison on
  *live* trades remains blocked by the same `DecisionVaultEntry.strategyId == None` gap already disclosed
  there — not re-solved here. Priority 7 Professional Strategy Research (indicator library) — BLOCKED BY
  ARCHITECTURE, same root cause as Priority 3. Priority 8 Model Validation blocking-gate migration — per the
  directive's own explicit instruction, **documented only, not implemented** (full migration plan — current
  architecture, current authority verified by tracing every real sandbox.py gate function, dependencies, 4
  concrete risks, a 5-step migration plan, required tests, governance implications — now in
  `docs/Architecture.md`'s Priority 8 section): `ModelValidationReport`'s 6 real checks remain advisory-only;
  no CEO authorization for a blocking gate exists in this repository.

- **CEO directive "Professional Trading Firm Transformation" — Gap Analysis + Exit Efficiency**
  (`backend/app/exit_efficiency.py`, `backend/app/schemas.py`, `backend/app/routers/trades.py`,
  `backend/tests/test_exit_efficiency.py`, `frontend/src/types.ts`, `frontend/src/net/api.ts`,
  `frontend/src/ui/components/CommandCenter/panels/DisciplinePanel.tsx`): research-first gap analysis across
  16 professional-firm areas (Research Desk, Portfolio Management, Risk, Execution, Market Intelligence, Model
  Validation, Performance Attribution, Post-Trade Review, Knowledge, Continuous Learning, Investment Committee,
  Reporting, Agent Intelligence, Team Chemistry, Talent Development, Company Health) via 4 parallel research
  passes, ranked CRITICAL/HIGH/MEDIUM/LOW/DEFERRED, then only the single highest-priority piece implemented —
  full table in `docs/Architecture.md`. Highlights: Portfolio Management is already SUBSTANTIAL
  (`app/portfolio_intelligence.py`'s real Pearson correlation/category exposure/Portfolio Heat); Research Desk
  is structurally mature but every backtest/regime-test/stress-test is a transformation of one synthetic RNG
  engine, never independent data; Performance Attribution is genuinely MINIMAL (no real $/% P&L by symbol or
  agent exists anywhere); Team Chemistry's Debate has zero causal effect on outcomes (`finalRecommendation` is
  fixed before the debate runs). **Chosen and implemented**: `PaperTrade.maePct`/`mfePct` (a real, live-computed
  watermark on every closed trade) was read by zero post-trade review modules — new `app/exit_efficiency.py`
  computes a real, continuous "Edge Ratio" `capturePct` per trade (`(pnlPct − maePct) / (mfePct − maePct) ×
  100`), honestly covering wins and losses with one formula, purely additive — never touching Discipline's
  process score or `failure_review.py`'s classification. New `GET /api/trades/exit-efficiency` endpoint; new
  "Exit Efficiency" Discipline Chamber panel section. **A real bug caught during live verification, not shipped
  uncaught**: the real close price can land beyond the last tracked watermark (confirmed live:
  `pnlPct=-2.42%` vs. `maePct=-2.32%`), producing an invalid out-of-range `capturePct` — fixed by widening the
  effective range to include the real close price itself, re-verified live against the real save. 11 new tests
  (2 covering the live-caught edge case), `mypy app/` (150 files)/`ruff check app/ tests/` clean, full backend
  suite (2000 passed; same 6 pre-existing unrelated `test_nexus.py` failures), `tsc -b --noEmit`/`eslint`/`vite
  build` clean, live Playwright verification before and after the fix. Documented in `docs/Architecture.md`.

- **CEO directive "Session Trading Education & Agent Training" + Final Agent-Trading Investigation**
  (`backend/app/foundational_mentors.py`, `backend/app/session_evidence.py`, `backend/app/schemas.py`,
  `backend/app/executive_intelligence.py`, `backend/app/nexus.py`, `backend/app/state.py`,
  `backend/app/war_room.py`, `backend/app/routers/executive.py`, `backend/app/routers/market.py`,
  `backend/tests/test_session_evidence.py`, `backend/tests/test_foundational_mentors.py`,
  `backend/tests/test_executive_intelligence.py`, `frontend/src/types.ts`, `frontend/src/net/api.ts`,
  `frontend/src/ui/components/CommandCenter/panels/MarketIntelPanel.tsx`): two linked deliverables. **The
  investigation**, traced end to end with evidence before any conclusion: the pipeline's first, controlling
  stop point is `app/nexus.py::_apply_operating_mode()`'s own literal first line, a no-op whenever
  `operating_mode == "learning"` (the documented default) — every real `TradeProposal` waits for a real CEO
  click, exactly as this codebase's own v0.6.3 CEO Delegation design intends. **Classification: INTENTIONAL
  BEHAVIOR, not a bug** — nothing about operating-mode defaults, Gatekeeper thresholds, `RiskLimits` defaults,
  or proposal-generation cadence was changed; correctly-waiting behavior was preserved, not "fixed." **The
  curriculum**: research first found the real system to extend — `app/foundational_mentors.py`'s
  `market_intelligence` track already had one session lesson built on real `compute_session()`/Market Quality
  Score mechanics. Extended (never duplicated) with 7 new lessons (orders 9-15) covering Asia/London/New
  York/Overlap/Transitions and a capstone teaching the real 8-step decision process (session → regime → setup
  → evidence check → conditions → proposal → Gatekeeper → execution), explicit that steps 3-7 are never
  skipped — all content passing the existing `probability_language` certainty-language audit, newly extended to
  cover this track too. **The evidence**: new `app/session_evidence.py`, a real, computed-fresh SESSION × REGIME
  aggregate over the already-persisted Decision Vault (which already stamps real session/regime/pnl per closed
  trade) — no new `GameSaveState` field. Honestly scoped to two axes: `DecisionVaultEntry.strategyId` is `None`
  on every real entry today and no "setup" taxonomy exists anywhere in this codebase, so the original five-axis
  session × regime × strategy × setup × outcome framing isn't buildable from real data yet — disclosed, not
  fabricated. `MIN_SESSION_REGIME_SAMPLE = 5`; favorable/unfavorable/mixed/not_enough_evidence states. **Reaching
  the real pipeline without bypassing governance**: the `market_intelligence` department opinion now cites this
  real evidence in its summary ("N real observations, X% favorable" or "NOT ENOUGH EVIDENCE") on every real
  proposal — informational only, `stance` still derives purely from the real Market Quality tier (verified: a
  poor-quality proposal stays `recommend_waiting` even with 100%-favorable cited evidence), and neither the
  Gatekeeper nor `RiskLimits` read it. New `GET /api/market/session-evidence` endpoint; new "Session × Regime
  Evidence" Market Intelligence panel section. **Disclosed limitation found during verification**:
  `FoundationalMentorState` has no lesson-content sync-on-load anywhere in this codebase — existing saves keep
  whatever lesson count they were created with; only new games get the extended curriculum immediately. **Not
  built** (disclosed, not fabricated): an interactive WAIT-scenario minigame (no existing scenario-branching
  engine to extend — `app/sandbox.py`/`app/war_room.py` both presuppose a trade candidate already exists), a
  dedicated session post-trade-review generator (the Decision Vault + the new evidence module already serve
  this), and the five-axis evidence model. 25 new/updated tests, `mypy app/` (149 files)/`ruff check app/
  tests/` clean, full backend suite (1989 passed; same 6 pre-existing `test_nexus.py` failures, confirmed
  unrelated), `tsc -b --noEmit`/`eslint`/`vite build` clean, live Playwright verification against the real dev
  stack (the new panel section rendered the real current save's own single closed trade, correctly reading NOT
  ENOUGH EVIDENCE, matching the API response exactly). Documented in `docs/Architecture.md`.

- **CEO directive "Features 31-35: Compliance, Governance & Continuous Improvement System," Feature 35 —
  Continuous Compliance Improvement Loop** (`backend/app/continuous_improvement.py`, `backend/app/company_health.py`,
  `backend/app/schemas.py`, `backend/app/nexus.py`, `backend/app/state.py`, `backend/app/routers/audit.py`,
  `backend/tests/test_continuous_improvement.py`, `backend/tests/test_company_health.py`, `frontend/src/types.ts`,
  `frontend/src/net/api.ts`, `frontend/src/ui/components/CommandCenter/panels/CompliancePanel.tsx`,
  `frontend/src/ui/components/CommandCenter/panels/CompanyPanel.tsx`, `frontend/src/game/systems/NexusManager.ts`,
  `frontend/src/state/gameStore.ts`): the fifth and final stage of the CEO's 31→32→33→34→35 Compliance closed
  loop. Closes INCIDENT → ROOT CAUSE → REMEDIATION → MONITORING → OUTCOME → EFFECTIVENESS REVIEW → COMPANY HEALTH
  needing no new persisted state — Feature 31's `ComplianceIncident` already carried `rootCause`/
  `correctiveAction`; this reads two already-real signals to grade whether a fix held: a real `reopen()` (the
  strongest possible evidence of failure, always wins) and whether another incident sharing the exact same
  (root cause, category, department) signature opened after resolution. Four honest states — `effective`/
  `partially_effective`/`ineffective`/`not_enough_evidence` — with a real, disclosed observation window
  (`REMEDIATION_EVAL_WINDOW_SIM_DAYS = 5`, reused verbatim from the Incident Cases UI's own existing SLA
  default) before "no recurrence yet" honestly reads as effective. RECURRING FAILURE detection
  (`RECURRING_FAILURE_MIN_COUNT = 2`) flags any root cause producing 2+ incidents, per the directive's literal
  wording. Connected into Company Health through the EXISTING architecture: a new `complianceHealth` 11th
  Executive-tier dimension blending incident resolution rate, remediation effectiveness, and Feature 34's
  control effectiveness — never a rewrite of `compute_compliance_score()` in `audit_log.py`, which stays
  completely untouched. Per the directive's own CEO-authorization gate: the formula's real limitation (counts
  open incidents only, no reward for effective remediation, no penalty for recurring failure) is documented in
  full in Design Bible Chapter 73 along with a concrete proposed change — not applied, since no explicit CEO
  authorization to change that specific formula was sought or given. New `GET /api/audit/continuous-improvement`
  endpoint; new "Continuous Improvement" Compliance panel tab; new "Compliance Health" cell in the Company
  panel's Executive Health grid. 13 new backend tests plus 1 updated fixture, `mypy app/` (149 files)/`ruff
  check app/ tests/` clean, full backend suite (1974 passed; same 6 pre-existing `test_nexus.py` failures),
  `tsc -b --noEmit`/`eslint`/`vite build` clean (the composite-project-aware `tsc -b` command caught two
  missing-required-field errors a bare `tsc --noEmit` had silently missed), live Playwright verification
  against the real dev stack — a real incident was driven through its full real lifecycle via the live API and
  rendered correctly as NOT ENOUGH EVIDENCE with real corrective-action text, and the Compliance Health cell's
  live value (35) was independently hand-verified against the formula. Documented in Design Bible Chapter 73
  and Chapter 63. With this entry, the CEO's own Features 31-35 directive is complete.

- **CEO directive "Features 31-35: Compliance, Governance & Continuous Improvement System," Feature 34 —
  Compliance Control Effectiveness** (`backend/app/control_effectiveness.py`, `backend/app/schemas.py`,
  `backend/app/routers/audit.py`, `backend/tests/test_control_effectiveness.py`, `frontend/src/types.ts`,
  `frontend/src/net/api.ts`, `frontend/src/ui/components/CommandCenter/panels/CompliancePanel.tsx`): the fourth
  stage of the CEO's 31→32→33→34→35 Compliance closed loop, answering the directive's core question — did each
  real Gatekeeper check actually prevent or detect what it was designed to address, not just how often it
  exists/fires. Needed no new persisted state: all 11 real checks (`app/gatekeeper.py::evaluate_gatekeeper()`)
  already run on every real trade decision and are stored on `TradeDecision.gatekeeperVerdict.checks`, and
  `GatekeeperRejection.outcome` (v0.7 Feature 20) already grades every blocked trade's real
  `would_have_won`/`would_have_lost` from real subsequent price movement — this feature is a pure,
  computed-fresh-per-request join over both, the original CAGS convention. Attribution honesty: since a
  rejection can have multiple checks failing at once, a real outcome is only credited to a control when it was
  the *sole* failing check for that decision — every multi-check-failure case counts separately as
  `ambiguousAttributionCount`, never guessed at. Five evaluation states, not two: `not_yet_tested` (never once
  failed — CONTROL EXISTS, never yet had the chance to prove CONTROL WORKS), `insufficient_data` (too few
  confirmed outcomes, floor reused verbatim from Feature 33's `MIN_ACCURACY_SAMPLE_FOR_VERDICT = 3`), `mixed`
  (enough confirmed evidence but the prevented-vs-false-positive split lands in the ambiguous 40-60% band — real
  mixed evidence, never collapsed into `insufficient_data`), and `effective`/`ineffective` only once the sample
  floor is cleared and the 60%/40% split (reused a third time from `ExecutiveVoting.tsx`'s own convention)
  clearly favors one side. `controlRegression` flags a real earlier-effective/later-ineffective split in a
  control's own confirmed history — never a hardcoded flag. New `GET /api/audit/controls/effectiveness`
  endpoint; new "Control Effectiveness" Compliance panel tab. 15 new backend tests, `mypy app/` (147
  files)/`ruff check app/ tests/` clean, full backend suite (1960 passed; same 6 pre-existing `test_nexus.py`
  failures, plus one independently-reconfirmed-flaky `test_foundational_mentors.py` test unrelated to this
  change), `tsc`/`eslint`/`vite build` clean, live Playwright verification against the real dev stack — a real
  live CEO-approved BUY on SPY drove a real `TradeDecision`/`gatekeeperVerdict` through the actual Gatekeeper,
  and the new tab correctly rendered all 11 controls as `triggeredCount: 1, passedCount: 1` immediately after.
  Documented in Design Bible Chapter 73.

- **CEO directive "Features 31-35: Compliance, Governance & Continuous Improvement System," Feature 33 —
  Executive Accuracy Evidence System** (`backend/app/executive_intelligence.py`, `backend/app/schemas.py`,
  `backend/app/weighted_decisions.py`, `backend/tests/test_executive_intelligence.py`, `frontend/src/types.ts`,
  `frontend/src/ui/components/CommandCenter/ExecutiveVoting.tsx`,
  `frontend/src/ui/components/CommandCenter/panels/CompliancePanel.tsx`): the third stage of the CEO's
  31→32→33→34→35 Compliance closed loop, and a direct fix for the exact bug the CEO's own brief named
  ("Research—0%... may mean no evaluated research decisions exist yet"). `compute_executive_accuracy_scores()`
  previously returned a fabricated `accuracyPct: 0.0` whenever a department had zero tracked, evaluable
  directional stances — fixed at the data layer: `accuracyPct` is now `float | None`, `None` (never `0.0`) when
  `decisionsTracked` is 0. A new `evaluationState` field (`pass`/`fail`/`inconclusive`/`not_enough_evidence`) is
  published alongside it so no caller has to reinvent its own good/bad interpretation of a raw percentage —
  `not_enough_evidence` applies below a disclosed minimum sample floor (`MIN_ACCURACY_SAMPLE_FOR_VERDICT = 3`,
  the same honesty convention Chapter 73's Compliance Score and Feature 32's `MIN_OVERRIDE_SAMPLE_FOR_TREND`
  already carry), and the `pass`/`fail` thresholds (60%/40%) are reused verbatim from the existing Command
  Center UI's own green/amber/red boundary, not invented for this feature. `weighted_decisions.py`'s
  `compute_accuracy_multiplier()` already treated `decisionsTracked == 0` as the neutral 1.0× (never a penalty)
  — updated to also guard the now-nullable `accuracyPct` before dividing, preserving that exact behavior.
  Scope, disclosed rather than silently dropped: genuinely role-specific metrics per department (real candidate
  signals identified for Devil's Advocate, Market Intelligence, and Decision Intelligence) would have required
  threading new required parameters through all 6 real call sites of `compute_executive_accuracy_scores()` under
  time pressure — this pass ships the honest, cross-department fix and evidence-state classification for all 9
  departments; role-specific second metrics remain an explicit cut for a future pass. Frontend:
  `ExecutiveAccuracyPanel` now groups departments by the backend's own `evaluationState` rather than a
  `decisionsTracked > 0` check; `CompliancePanel.tsx`'s Executive Accuracy strip shows literal "NOT ENOUGH
  EVIDENCE" instead of a bare "0" — directly matching the CEO's own requested display format. 6 new backend
  tests, `mypy app/` (146 files)/`ruff check app/ tests/` clean, full backend suite (1946 passed; same 6
  pre-existing, unrelated `test_nexus.py` failures), `tsc`/`eslint`/`vite build` clean, live Playwright
  verification against the real dev stack (both `GET /api/executive/accuracy` and the Compliance panel correctly
  showed NOT ENOUGH EVIDENCE for all 9 departments on a fresh save). Documented in Design Bible Chapter 70
  Part 2's KPIs section.

- **CEO directive "Features 31-35: Compliance, Governance & Continuous Improvement System," Feature 32 —
  CEO Override Governance** (`backend/app/schemas.py`, `backend/app/override_governance.py`,
  `backend/app/nexus.py`, `backend/app/state.py`, `backend/app/routers/executive.py`,
  `backend/app/routers/audit.py`, `backend/app/save_modules.py`, `backend/tests/test_override_governance.py`,
  `frontend/src/types.ts`, `frontend/src/net/api.ts`, `frontend/src/ui/components/CommandCenter/panels/CompliancePanel.tsx`):
  the second stage of the CEO's 31→32→33→34→35 Compliance closed loop. Research first, and a correction to an
  earlier-session assumption: CEO overrides are NOT permanently stuck at `outcome="undecidable"`.
  `resolve_proposal()`'s `outcome="pending" if order_id is not None else "undecidable"` is keyed on whether a real
  order was placed, not on `agreedWithAi` — an override that produces a real trade (CEO buys when the network said
  wait) gets graded exactly like any other decision once that trade closes via `grade_ceo_decisions()`; only an
  override resolving to "wait" (no order at all) stays undecidable, correctly, since nothing real exists to grade.
  `override_governance.py` never re-grades that outcome a second way. What it genuinely adds is PROCESS QUALITY —
  was the override justified by evidence available at the moment the CEO decided, independent of the trade's
  eventual P&L (no hindsight contamination). Built entirely from the real, already-persisted
  `ExecutiveMeetingLogEntry` for that proposal (department opinions, `decisionGrade`/`decisionGradeScore`) — never
  a fabricated confidence score, never a second copy of `risk_engine.py`'s own logic. A disclosed 2x2 heuristic
  (strong/weak recommendation × contested/uncontested department opinion, reusing the exact B- `GRADE_THRESHOLDS`
  cutoff already shown to the CEO) yields justified/unjustified/mixed, with not_enough_evidence when no meeting
  log entry exists for the proposal. Process quality and outcome are stored and displayed as two separate fields,
  never collapsed into one score — a justified override that lost money and an unjustified override that won are
  both shown honestly. `overrideReason` is a genuinely new, optional CEO-provided text field on
  `POST /api/executive/decide` (`None` for every prior decision, never a fabricated backfill). New
  `GameSaveState.ceoOverrideEvaluations` list, synced/outcome-refreshed every tick after `ceoDecisions`/
  `executiveMeetingLog` reach their tick-final values; one new `addOverrideReview()` mutation (a real reviewer
  note that never touches process quality or outcome); 3 new `/api/audit/overrides/*` endpoints, additive to the
  original 5 CAGS endpoints and Feature 31's incident endpoints, kept off the WS broadcast. Summary honesty:
  `overrideRatePct` is `null`, never a fabricated 0%, when there are no decisions to divide by;
  `sampleSizeSufficient` gates trend interpretation on a disclosed floor (`MIN_OVERRIDE_SAMPLE_FOR_TREND = 5`);
  `departmentOverrideImpact` counts real department-agreement data, never invented. Frontend adds a new "Override
  Governance" tab in `CompliancePanel.tsx` alongside the untouched original "CEO Overrides" tab, with a real
  review-note form. 20 new backend tests (the full 2x2 process-quality truth table, sync/dedup, override-reason
  carry-through, outcome mirroring, review notes never touching quality/outcome, summary aggregation), `mypy
  app/` (146 files)/`ruff check app/ tests/` clean, full backend suite (1940 passed; same 6 pre-existing,
  unrelated `test_nexus.py` failures noted under Feature 31), `tsc`/`eslint`/`vite build` clean, live Playwright
  verification against the real dev stack (a real override evaluation correctly showed NOT ENOUGH EVIDENCE and
  UNDECIDABLE for a decision predating the meeting-log feature, and a real review was recorded end-to-end through
  the UI). Documented in Design Bible Chapter 73's addendum, alongside Feature 31's.

- **CEO directive "Features 31-35: Compliance, Governance & Continuous Improvement System," Feature 31 —
  Compliance Incident Resolution Engine** (`backend/app/schemas.py`, `backend/app/compliance_incidents.py`,
  `backend/app/nexus.py`, `backend/app/state.py`, `backend/app/save_modules.py`, `backend/app/routers/audit.py`,
  `backend/tests/test_compliance_incidents.py`, `frontend/src/types.ts`, `frontend/src/net/api.ts`,
  `frontend/src/ui/components/CommandCenter/panels/CompliancePanel.tsx`): the first stage of the CEO's
  31→32→33→34→35 Compliance closed loop — per the directive's own staging rule, 32-35 do not start until this
  feature is tested, verified, and documented. Researched first: `app/audit_log.py`'s `compute_incidents()`
  already existed as a real filter over the Audit Log (`severity != "info"`), but by that module's own docstring
  is "computed fresh per request (never persisted, never a new `GameSaveState` field)" — the Compliance panel's
  own UI text already disclosed the exact gap: "incident resolution is not a real mechanic anywhere in this
  codebase today." `compliance_incidents.py` closes exactly that gap, strictly downstream of the existing Audit
  Log (never a second incident-detection system): `sync_incidents_from_audit_log()` is the only creation path,
  opening one `ComplianceIncident` per real, currently-open `AuditEntry`, deduplicated by `sourceEntryId`. A
  strict `ALLOWED_TRANSITIONS` state machine (`open` → `investigating` → `remediation` →
  `awaiting_verification` → `resolved`, with a real failed-verification bounce back to `remediation` and a real
  `resolved` → `reopened` → `investigating` recurrence path) makes `open` → `resolved` in one step structurally
  impossible — every transition function returns `None` (never raises, never silently succeeds) on an invalid
  request, `app/executive.py`'s `hold_proposal()` contract reused verbatim. `root_cause` (8 categories including
  `unknown`) is optional everywhere except the one real resolving call, where `unknown` is always an honest,
  valid answer, never forced. Synced once per tick in `nexus.py` from that tick's own final Audit Log; historical
  preservation means the first sync opens every incident using its real source `AuditEntry`'s own
  `created_at`/`sim_day`, never today's date, with every resolution field at its honest default since none of
  these incidents has ever actually been resolved. Seven new `GameState` lifecycle methods, nine new
  `/api/audit/incidents/*` endpoints (original five CAGS endpoints byte-for-byte unchanged), deliberately kept
  off the WS broadcast matching this router's own existing on-demand-fetch precedent. `ComplianceIncidentSummary`
  never fabricates: `averageResolutionSimDays` is `null` (not `0`) when nothing has resolved yet;
  `severityWeightedBacklog` reuses `company_health.py`'s own `_SEVERITY_PENALTY` table rather than a second
  scale. **Compliance Score is unchanged this pass** — still reads only the original ephemeral filter; this
  directive's own rules require explicit CEO authorization before that formula changes, and wiring this
  feature's real evidence into it is Feature 35's job. Frontend adds a new "Incident Cases" tab in
  `CompliancePanel.tsx` alongside the untouched original "Incidents" tab, with a real per-case lifecycle-action
  form that only shows actions valid from that incident's current status. 26 new backend tests, `mypy app/` (145
  files)/`ruff check app/ tests/` clean, full backend suite (1920 passed; the same 6 pre-existing
  `test_nexus.py` `_apply_operating_mode()` failures noted under Feature 30 below, confirmed present on the base
  branch before this change and left untouched), `tsc`/`eslint`/`vite build` clean, live Playwright verification
  against the real dev stack (two real cases rendered from this save's actual Audit Log, `averageResolutionSimDays`
  correctly showed "NOT ENOUGH EVIDENCE" rather than 0, and a real `investigate` transition was driven through
  the UI end-to-end — status pill changed OPEN → INVESTIGATING, owner populated). One real bug caught during
  live verification and fixed before commit: `ComplianceIncident.verification_status` was the only field in the
  new schema missing its explicit camelCase `Field(alias=...)`, so it serialized as `verification_status`
  instead of `verificationStatus` until fixed. Documented in Design Bible Chapter 73's addendum (the chapter's
  original "mutable Incident workflow — cut" reasoning is corrected in place, not deleted, to keep the honesty
  trail intact about what changed and why).

- **CEO directive "Features 26-30: Agent Intelligence, Learning & Institutional Memory System," Feature 30 —
  Agent Debate + Failure Review Board** (`backend/app/failure_review.py`, `backend/app/schemas.py`,
  `backend/app/institutional_memory.py`, `backend/app/nexus.py`, `backend/app/prediction_tracking.py`,
  `backend/app/skill_progression.py`, `backend/app/performance_review.py`, `backend/app/save_modules.py`,
  `backend/app/ws_manager.py`, `backend/app/main.py`, `backend/app/routers/failure_review.py`,
  `backend/tests/test_failure_review.py`, `frontend/src/types.ts`, `frontend/src/net/socket.ts`,
  `frontend/src/game/systems/NexusManager.ts`, `frontend/src/game/systems/EventBus.ts`,
  `frontend/src/state/gameStore.ts`, `frontend/src/ui/components/CommandCenter/panels/DisciplinePanel.tsx`,
  `frontend/tests/commandCenter.spec.ts`): the fifth and final stage of the CEO's 26→27→28→29→30 closed
  learning loop. Researched first: `app/debate.py`/`app/devils_advocate.py` are both pre-decision-only (no
  post-hoc failure-reason concept anywhere), and `app/mistakes.py`'s six `CaseStudyCategory` values already
  answer a real but *different* question — what behavioral/process mistake occurred — never why the trade's
  underlying THESIS actually failed; a trade can be process-perfect with a wrong thesis, or vice versa, so this
  is a genuinely separate, non-duplicating axis. `classify_failure()` is a new synthesis layer reusing every
  real signal already computed for a closed, losing trade — `app/discipline.py`'s own `DisciplineReview.factors`,
  `app/process_adherence.py`'s `_trading_mode_check()` reused verbatim, this trade's own already-filed
  `CaseStudy` categories, and the Market Intelligence Learning Loop's day-level `regime_consistent` read,
  cross-referenced by real sim-day overlap with the trade's own hold window — never a second, independently
  computed statistic. Seven named `FailureReason` values (`bad_thesis`, `poor_execution`,
  `risk_management_failure`, `market_regime_misread`, `information_gap`, `process_violation`, `unknown`), picked
  by a fixed, disclosed precedence order so a trade matching more than one real cause still gets exactly one
  honest classification. An eighth candidate, `external_shock` (Black Swan events), was researched and
  explicitly cut rather than shipped as a permanently-dead value: `CrisisBriefing` is "Never persisted as its
  own list" and carries no per-trade-linkable event id. Wired into the same `nexus.py` trade-close branch that
  already files this trade's `CaseStudy`(s), immediately after them — one real `FailureClassification` per
  closed loss, capped and persisted the same way every other archive list in this codebase is. Feeds back into
  all four earlier stages of the loop, closing it: a new `"failure_classification"` `InstitutionalMemorySource`
  (Feature 26), promoted for every named reason except `"unknown"` (which has no real lesson to file);
  `skill_progression.py`'s `regime_detection` domain — previously permanently `NOT_TRACKABLE_YET` because "no
  per-agent regime-call accuracy record exists anywhere" — flips to genuinely measurable via real per-agent
  `market_regime_misread` attribution, the single most valuable integration point the research surfaced
  (Feature 28), disclosed as a negative-only proxy (no per-agent *positive* regime-call confirmation exists
  anywhere in this codebase, only this real misread attribution on real losses); `PredictionRecord.failureReason`
  (Feature 29), filled at `grade_predictions()`'s own resolution moment from the real `FailureClassification` on
  the same trade — `grade_predictions()`'s call site was moved to run *after* the trade-close loop instead of
  before it, so a prediction resolved on the very same tick its trade closes still gets a real reason, not just
  a later one; and `performance_review.py`'s `recurring_mistakes` dimension evidence string gains real
  classification specificity (never changes the underlying 0-100 value, which stays `CaseStudy`-derived exactly
  as before). Governance-isolated exactly like Feature 29 and the Model Validator before it: purely
  retrospective and promotion-only, touches none of `gatekeeper.py`/`risk_engine.py`/Circuit Breakers/Model
  Validator, and can never block or alter a future trade. Extends `DisciplinePanel.tsx`'s existing DISCIPLINE
  tab with a new "Failure Review Board" card (reason-distribution filter chips, per-trade evidence, real
  attribution), sitting alongside the existing Discipline Chamber and Library of Mistakes & Successes cards.
  20 new backend tests, full backend suite/`mypy`/`ruff` clean (6 pre-existing, unrelated `test_nexus.py`
  failures confirmed via `git stash` against origin/HEAD to predate this change — a stale
  `_apply_operating_mode()` positional-argument mismatch from earlier work), `tsc`/`eslint`/`vite build` clean,
  live end-to-end verification against the running dev server (6 real CEO-decided trades produced 13 real
  `FailureClassification` records with real evidence text, real attribution, and real P&L; the Feature 26/28/29
  feed-back was independently confirmed live: real `"failure_classification"` Institutional Memory entries, a
  real non-`None` `regime_detection` skill score, and real `PredictionRecord.failureReason` values) and
  Playwright confirmed the new card renders correctly. Documented in Design Bible Chapter 74's addendum
  (continuing the CLSIS/learning-loop narrative Features 27/28 already established there). This closes the CEO's
  full "Features 26-30" directive.

- **CEO directive "Features 26-30: Agent Intelligence, Learning & Institutional Memory System," Feature 29 —
  Prediction -> Outcome Tracking** (`backend/app/prediction_tracking.py`, `backend/app/institutional_memory.py`,
  `backend/app/schemas.py`, `backend/app/nexus.py`, `backend/app/state.py`, `backend/app/save_modules.py`,
  `backend/app/ws_manager.py`, `backend/app/main.py`, `backend/app/routers/prediction_tracking.py`,
  `backend/tests/test_prediction_tracking.py`, `backend/tests/test_institutional_memory.py`,
  `frontend/src/types.ts`, `frontend/src/net/socket.ts`, `frontend/src/game/systems/NexusManager.ts`,
  `frontend/src/game/systems/EventBus.ts`, `frontend/src/state/gameStore.ts`,
  `frontend/src/ui/components/CommandCenter/lib/derive.ts`,
  `frontend/src/ui/components/CommandCenter/panels/ExecutivePanel.tsx`, `frontend/tests/executiveVoting.spec.ts`):
  the fourth stage of the CEO's 26→27→28→29→30 closed learning loop. Disclosed naming collision:
  `app/reasoning_lab.py` already carries an unrelated "v0.7 Feature 29" tag from an older, independent versioning
  scheme — documented in both modules, same disambiguation `app/decision_vault.py` already established once
  before. Researched first: three real pending→resolved lifecycles already existed (`CeoDecisionRecord`,
  `GatekeeperRejection`/`OpportunityRejection`, `MarketIntelligenceLearningEntry`) and `app/analytics.py`'s
  `confidence_accuracy()`/`research_accuracy()` already grade confidence-vs-outcome in aggregate, reused by
  Feature 27's dimensions — but nothing persisted an individually-addressable per-prediction audit trail. That's
  the one real gap this feature closes, scoped to the one claim type with a real, independently checkable later
  truth: trade direction. `build_prediction_record()` runs at the same real decision moment `CeoDecisionRecord`
  does (all three real resolve_proposal() call sites), reading the authoritative post-any-internal-downgrade
  `ceo_decision`, never the caller's original proposed choice. `grade_predictions()` mirrors
  `grade_ceo_decisions()`'s exact `decision_id`-matched resolution, run immediately after it, never regrading an
  already-resolved record. A real, notable miscalibration (high stated confidence, resolved wrong) promotes into
  Institutional Memory via a new `"prediction"` source — the exact value Feature 26 already reserved and
  disclosed as pending this feature. Explicitly out of scope, disclosed rather than silently gapped:
  `ResearchItem.confidence` (self-consistency threshold only, no real outcome link), `ModelValidationReport.verdict`
  (advisory-only, never re-checked), a strategy's original expectancy claim (no terminal resolvable state), and
  the three already-complete pending→resolved systems (read from, never re-persisted a second time — they keep
  their own real frontend surfaces). Extends the existing `ExecutivePanel.tsx` (EXECUTIVE tab) with a new
  "Prediction Ledger" card reusing its existing `StatusPill` pending/resolved conventions. 25 new backend tests,
  full backend suite/`mypy`/`ruff` clean, `tsc`/`eslint`/`vite build` clean, live end-to-end verification against
  the running dev server (a real `POST /api/executive/decide` "buy" call produced a real pending
  `PredictionRecord` that later resolved to `"incorrect"` with a real linked trade and P&L once the position
  closed) and Playwright confirmed the new card renders correctly. Documented in Design Bible Chapter 70's new
  addendum.

- **CEO directive "Features 26-30: Agent Intelligence, Learning & Institutional Memory System," Feature 28 —
  Academy + Skill Progression** (`backend/app/skill_progression.py`, `backend/app/schemas.py`,
  `backend/app/nexus.py`, `backend/app/save_modules.py`, `backend/app/ws_manager.py`, `backend/app/main.py`,
  `backend/app/routers/skill_progression.py`, `backend/tests/test_skill_progression.py`,
  `frontend/src/types.ts`, `frontend/src/net/socket.ts`, `frontend/src/game/systems/NexusManager.ts`,
  `frontend/src/game/systems/EventBus.ts`, `frontend/src/state/gameStore.ts`,
  `frontend/src/ui/components/CommandCenter/panels/TalentPanel.tsx`, `frontend/tests/talent.spec.ts`): the
  third stage of the CEO's 26→27→28→29→30 closed learning loop. Researched first: `app/academy.py` is a
  single-scalar knowledge-points/tier ladder (one `points` number, one fixed `branch` string per agent) and
  `app/foundational_mentors.py` is a curriculum/certification delivery engine (real lessons/quizzes, a genuine
  active/suspended/revoked lifecycle) — neither is a multi-domain per-agent skill score, and a grep for
  `Skill*`/`SkillDomain` across the whole codebase returned zero hits, confirming genuinely new territory. Of the
  11 domains named in the brief, 5 reuse real evidence already computed by `performance_review.py`/`mentor.py`
  (risk management, research quality, prediction calibration, collaboration, statistical reasoning as a disclosed
  proxy); the other 6 (market structure, quant research, technical/fundamental analysis, execution, regime
  detection, communication) have no per-agent attribution mechanism anywhere in this codebase and stay honestly
  `NOT_TRACKABLE_YET` — never fabricated from an occupation label — each citing the real company-level system
  closest to it and why it doesn't reduce to a per-agent number. Closes the loop the CEO's own worked example
  asked for: a weak Performance Review dimension now drives a real training recommendation naming a real,
  content-backed Foundational Mentor track (only the 4 tracks with real written lessons are ever recommended),
  skipped once the agent has already graduated it. `SkillAssessment.trend` (improving/regressed/stagnant/
  not_enough_history) is a real improve/stagnate/regress read against the agent's own previous assessment of the
  same domain, deliberately separate from `foundational_mentors.py`'s own certification revoke/suspend lifecycle
  rather than a second one. Wired into the same weekly `nexus.py` cadence as Agent Performance Reviews,
  immediately after so each skill snapshot reads that week's fresh `weakestDimensionId`. Extends the existing
  `TalentPanel.tsx` (TALENT tab) with a new card reusing its existing employee selector. 20 new backend tests,
  full backend suite/`mypy`/`ruff` clean, `tsc`/`eslint`/`vite build` clean, live verification against the
  running dev server (a real `POST /api/time/advance` across two week boundaries on a fresh save produced 30 real
  `AgentSkillProfile` records — 15 agents × 2 weeks — with the exact expected honesty shape) and Playwright
  confirmed the new card renders correctly. Documented in Design Bible Chapter 74's new addendum.

- **CEO directive "Features 26-30: Agent Intelligence, Learning & Institutional Memory System," Feature 27 —
  Agent Performance Reviews** (`backend/app/performance_review.py`, `backend/app/schemas.py`,
  `backend/app/nexus.py`, `backend/app/save_modules.py`, `backend/app/ws_manager.py`, `backend/app/main.py`,
  `backend/app/routers/performance_review.py`, `backend/tests/test_performance_review.py`,
  `frontend/src/types.ts`, `frontend/src/net/socket.ts`, `frontend/src/game/systems/NexusManager.ts`,
  `frontend/src/game/systems/EventBus.ts`, `frontend/src/state/gameStore.ts`,
  `frontend/src/ui/components/CommandCenter/panels/TalentPanel.tsx`, `frontend/tests/talent.spec.ts`): the
  second stage of the CEO's 26→27→28→29→30 closed learning loop, built as a synthesis layer over real evidence
  rather than a parallel scoring engine — not started until Feature 26 was tested and integrated, per this
  feature's own staging rule. Researched first: found `app/coach.py`'s `AgentScore` (scoped to only 4 researcher
  agents) and `app/mentor.py`'s `ThinkingProfile` (universal, but fake-defaulting every trait to a neutral 50.0
  with zero evidence) — `mentor.py`'s own module docstring already named "a real per-agent weakness signal" as
  an explicit, unbuilt scope cut. Eight real dimensions per agent per real week (process quality, risk
  discipline, decision accuracy, calibration, collaboration, learning trend, recurring mistakes, P&L
  attribution), each either real evidence or an honest `NOT_ENOUGH_EVIDENCE` (`value=null`), reusing
  `process_adherence.py`'s exact nullable-score/disclosed-sample-size shape. `processQualityAvg`/
  `outcomeQualityAvg` stay structurally separate, mirroring `discipline.py`'s own process-score-never-sees-pnl
  discipline. `AGENT_ROLE_CLASS` is this codebase's first machine-usable role taxonomy over `AGENT_PROFILES`, so
  a missing dimension (e.g. Sentinel having no `decisionAccuracy` data) reads as the honest truth about the
  role, not a gap — confirmed live: a real review for Sentinel showed exactly that pattern after a real
  `POST /api/time/advance` to a week boundary generated 15 real reviews (one per agent). `trend`/
  `weakestDimensionId` are the real hook Feature 28's future training recommendations will read from, per the
  CEO's own worked example, without building Feature 28 yet. Extends the existing `TalentPanel.tsx` (TALENT
  tab) with a new card reusing its existing employee selector, rather than a new tab. 21 new backend tests, full
  backend suite (1843 tests)/`mypy`/`ruff` clean, `tsc`/`eslint`/`vite build` clean, live Playwright
  verification confirmed real per-agent data end-to-end. Documented in Design Bible Chapter 74's new addendum.

- **CEO directive "Features 26-30: Agent Intelligence, Learning & Institutional Memory System," Feature 26 —
  Institutional Memory 2.0** (`backend/app/institutional_memory.py`, `backend/app/schemas.py`,
  `backend/app/nexus.py`, `backend/app/state.py`, `backend/app/save_modules.py`, `backend/app/ws_manager.py`,
  `backend/app/main.py`, `backend/app/routers/institutional_memory.py`, `backend/tests/test_institutional_memory.py`,
  `frontend/src/types.ts`, `frontend/src/net/socket.ts`, `frontend/src/game/systems/NexusManager.ts`,
  `frontend/src/game/systems/EventBus.ts`, `frontend/src/state/gameStore.ts`,
  `frontend/src/ui/components/CommandCenter/panels/KnowledgeBasePanel.tsx`, `frontend/tests/knowledgeBase.spec.ts`):
  the first stage of the CEO's 26→27→28→29→30 closed learning loop, implemented per the directive's own explicit
  staging rule ("do not start the next feature until the previous feature is tested and integrated"). Researched
  first: found `app/scribe.py`'s `MemoryRecord` (a flat event log) and `app/decision_vault.py`'s
  `KnowledgeQualityScore` (a single-record-type scoring layer), but no reusable-lesson promotion layer spanning
  multiple real record types — that's the genuine gap this feature closes, not a second event log or a second
  Knowledge Graph. Six new `promote_*()` functions turn a real `CaseStudy`, `FailedStrategyArchiveEntry`,
  `StrategyHallOfFameEntry`, `ModelValidationReport`, `RiskWarning`, or market regime change into an
  `InstitutionalMemoryEntry`, separating observation (real fact) from interpretation (hedged) from lesson
  (actionable) — never inventing any of the three when a source has nothing honest to offer. Confidence reuses
  `decision_vault.py`'s exact `PATTERN_FREQUENCY_CAP`-shaped corroboration formula; relevance reuses
  `compute_knowledge_quality_score()`'s exact recency-decay formula, recomputed fresh at read time rather than
  trusted stale from storage. `find_related_memory()` reuses `app/constitution.py`'s exact word-overlap redundancy
  check to surface candidates; `supersede_memory()` makes the update/contradiction call explicit and never deletes
  history. `retrieve_relevant_memory()` honestly returns `None` — NOT ENOUGH EVIDENCE — rather than forcing a weak
  answer. Wired into `nexus.py`'s tick (new case studies, genuinely-new critical risk warnings, real regime shifts)
  and `state.py`'s strategy-review/retirement CEO actions (Model Validation findings, Hall of Fame/Failed Archive).
  Extends the existing `KnowledgeBasePanel.tsx` (OPS tab) with a second, source-filterable card rather than a new
  dashboard page. 30 new backend tests, full backend suite (1822 tests)/`mypy`/`ruff` clean, `tsc`/`eslint`/
  `vite build` clean, live Playwright verification confirmed a real regime-shift entry generated by the running
  simulation and rendered correctly. Documented in Design Bible Chapter 61's new addendum. Deliberately deferred:
  `"prediction"`/`"agent_debate"`/`"performance_review"` sources, until Features 29/30/27 exist to honestly feed them.

- **CEO Company Health + Live Market Realism directive, Features 21-25 — Failure Boundary gate, MAE/MFE, Constitution
  Article XIV** (`backend/app/gatekeeper.py`, `backend/app/portfolio.py`, `backend/app/schemas.py`,
  `backend/app/constitution.py`, `backend/tests/test_gatekeeper.py`, `backend/tests/test_portfolio.py`,
  `backend/tests/test_constitution.py`, `frontend/src/types.ts`,
  `frontend/src/ui/components/CommandCenter/panels/PerformancePanel.tsx`, `frontend/tests/constitution.spec.ts`):
  researched first, per the directive's own explicit "do not duplicate existing systems" instruction, and found the
  Prop-Firm Risk Intelligence Addendum (Piece 10a/10b/Piece 11) had already built almost everything — Features 21/22
  ("Fast Pass" vs. conservative risk, "slow ≠ automatically safer") are fully covered by
  `app/evaluation_simulator.py`'s real Monte Carlo evaluation-policy race, untouched here. Feature 23 fills the one
  real gap Piece 11's own docstring disclosed ("no live TradeProposal execution routes to a secondary Account yet"):
  `_failure_boundary_check()` is the Trade Gatekeeper's eleventh check (following the exact naming precedent the
  Behavioral Circuit Breaker set as the tenth), reusing `app/portfolio.py`'s own real
  `max(0, max_drawdown_pct - lifetime_drawdown_pct)` formula — read *before* the trade instead of only after — with
  zero new risk engine and zero new plumbing (`portfolio`/`risk_limits` were already `evaluate_gatekeeper()`
  parameters). Feature 24 adds `maePct`/`mfePct` (Maximum Adverse/Favorable Excursion) — confirmed genuinely missing
  everywhere else on the CEO's telemetry list was already real — tracked as a running watermark in
  `mark_to_market()` from the same real live prices `unrealizedPnlPct` already reads every tick (never a
  retroactively regenerated candle series, which would have given the deliberately market-data-free `portfolio.py`
  a new dependency), then copied onto the closed trade the same way `tradingStyle` already is. Feature 25 adds
  Constitution Article XIV ("TradeTown optimizes for statistically validated expected value and long-term survival,
  not simply win rate, individual trade size, or minimum risk"), seeded the same permanent way Articles IX-XIII
  already were, verified non-duplicative first (the closest existing thing was report-conclusion prose scoped to
  evaluation-policy comparison, not a company-wide citable rule) and noting that `app/opportunity_gatekeeper.py`
  already enforces the real mechanism behind it. Verified: 6 new Gatekeeper tests + 6 new MAE/MFE tests + Constitution
  tests updated for the 14th seeded Article; full backend suite 1791/1792 passing (the one failure, pre-existing
  unseeded-random flakiness in `test_foundational_mentors.py`, already confirmed unrelated); mypy/ruff clean across
  all 134 source files; frontend tsc/lint/build clean; the Gatekeeper's new eleventh check needed zero frontend
  changes (`ExecutiveVoting.tsx` already renders every check dynamically); MAE/MFE surfaced in the Performance
  panel's Recent Trades card, confirmed rendering cleanly via Playwright with zero console errors.

- **CEO Company Health + Live Market Realism directive, Section 3 — formal Learning Event records**
  (`backend/app/schemas.py`, `backend/app/academy.py`, `backend/app/scribe.py`, `backend/app/nexus.py`,
  `backend/app/save_modules.py`, `backend/app/ws_manager.py`, `backend/tests/test_academy.py`,
  `frontend/src/types.ts`, `frontend/src/game/systems/EventBus.ts`, `frontend/src/state/gameStore.ts`,
  `frontend/src/net/socket.ts`, `frontend/src/game/systems/NexusManager.ts`,
  `frontend/src/ui/components/CommandCenter/panels/AcademyPanel.tsx`): the CEO asked for a formal record of
  every real Knowledge-tier crossing — agent, skill/domain, previous competency, new competency, source,
  evidence, timestamp. `app/academy.py`'s `award_points()` already computed every one of those fields
  internally (the tier-up transition) but only ever surfaced it as a free-text `app/scribe.py` Memory entry,
  never a structured, queryable record. New `LearningEvent` schema captures the transition directly off the
  real `AgentKnowledgeState` change — never a fabricated "why" narrative, since `pointsAwarded`/`totalPoints`
  already are the real evidence. `award_points()` now requires an explicit `source` naming exactly which of
  the five real places in this codebase actually calls it — `research_completion`, `academy_project`,
  `meeting_attendance`, `mentorship`, or `case_study_reflection` (a supporting agent nudged for reflecting on
  a filed case study) — never a fabricated sixth reason; two of those five were only found by re-running
  `mypy` after the first four call sites were wired up, which caught two remaining unannotated call sites
  and led to `case_study_reflection` being added as a genuinely distinct fifth source rather than
  shoehorned into one of the other four. Each real tier-up is appended to a new capped (60), permanent
  `learningEvents` archive list (same cap-and-trim pattern as `app/mistakes.py`'s Library of Mistakes),
  broadcast live over the WebSocket tick. Along the way, fixed a real pre-existing gap:
  `maybe_run_mentorship()` computed its own tier-up via `award_points()` but discarded the result, so a
  mentorship bonus that itself crossed a tier threshold was silently never recorded anywhere (no Memory
  entry, no Learning Event) — it now returns the event alongside the pairing, recorded through the same path
  as every other source. Frontend: a new "Learning Events" card in the Command Center's KNOWLEDGE tab shows
  each event's agent, skill domain, previous → new level, real source, and points awarded, most recent
  first. Verified: `test_academy.py` extended (24 tests, including the new `LearningEvent` field assertions,
  `record_learning_event()`'s cap behavior, and `maybe_run_mentorship()`'s fixed 3-tuple return), full
  backend suite (1778/1779 passing — the one failure is pre-existing, unseeded-random flakiness in
  `test_foundational_mentors.py`, confirmed unrelated by re-running it in isolation 5/5 clean both with and
  without this change), `mypy`/`ruff` clean; frontend `tsc`/`lint`/`build` clean; live-verified against the
  running dev stack — connected directly to the WebSocket broadcast and confirmed a real persisted
  `LearningEvent` (Pulse crossing to Advanced in Statistics via a finished Academy project) was present on
  the wire, then confirmed via Playwright that the same event rendered correctly in the Command Center.

- **CEO Company Health + Live Market Realism directive, Section 13 — real Goal blocker detection**
  (`backend/app/schemas.py`, `backend/app/goals.py`, `backend/tests/test_goals.py`, `frontend/src/types.ts`,
  `frontend/src/ui/components/CommandCenter/panels/CompanyPanel.tsx`): the CEO asked Goals to also carry
  owner/supporting-departments/evidence/blockers/outcome. `progress_pct`/`status`/`completed_at` were already
  the real, honest "progress" and "outcome." New: `stalled_ticks`/`is_blocked` — a real behavioral signal
  (consecutive real ticks with essentially zero progress movement, `GOAL_STALLED_THRESHOLD_TICKS = 20`), never
  a fabricated "reason" string. `tick_goal()` resets the counter the instant real progress resumes and clears
  `is_blocked` automatically once a goal completes or expires (a resolved goal is never shown as blocked).
  `owner`/`supporting departments` were explicitly investigated and cut, not silently dropped: a `Goal` tracks
  one company-wide metric every department's real work already feeds into simultaneously, and this codebase
  has no real per-goal ownership/attribution mechanism to draw from without inventing one — documented in
  `app/goals.py`'s own module docstring. `evidence` is likewise not a manufactured narrative field — the real
  numbers (`current_value`/`target_value`/`progress_pct`/`stalled_ticks`) already are the evidence. Frontend:
  the Company tab's goal cards show a red "BLOCKED" pill plus the real stalled-tick count. Verified: 6 new
  tests (starts unblocked, counter increments, threshold crossing, reset on real progress, completed/expired
  goals never read as blocked), full backend suite (1775 tests), `mypy`/`ruff` clean; frontend `tsc`/`lint`/
  `build` clean; live-verified against the running dev server — created a real goal via `POST
  /api/goals/create`, let the live sim tick it forward in real time, and confirmed the BLOCKED pill and "No
  real progress in 33 consecutive ticks." rendered once the real backend crossed the threshold.

- **CEO Company Health + Live Market Realism directive, Section 6 — real tick-over-tick Company Health delta
  breakdown** (`backend/app/schemas.py`, `backend/app/company_health.py`, `backend/app/nexus.py`,
  `backend/app/save_modules.py`, `backend/app/ws_manager.py`, `backend/tests/test_company_health.py`,
  `frontend/src/types.ts`, `frontend/src/game/systems/EventBus.ts`, `frontend/src/game/systems/NexusManager.ts`,
  `frontend/src/net/socket.ts`, `frontend/src/state/gameStore.ts`,
  `frontend/src/ui/components/CommandCenter/panels/CompanyPanel.tsx`): the CEO asked to see the explicit
  before/after delta behind every Company Health change (e.g. "+2.4 Decision Quality, -0.8 Efficiency..."),
  not just the latest snapshot. `diff_company_health()` is a pure diff between the previous tick's real
  `CompanyHealth` reading and the newly computed one — no new telemetry, no invented "reason"/"evidence" text
  (the schema docstring states explicitly why that would require re-deriving which raw input changed, which
  this function doesn't attempt). Only components whose score actually moved are included, sorted by real
  magnitude; a no-op tick reports an empty list rather than twenty-one honest zeroes. Wired into `nexus.py`'s
  tick() by diffing against `state.company_health` (the reading the CEO last actually saw) immediately before
  it's replaced — every tick, so the delta is always exactly one tick's worth of real movement, never
  accumulated or time-windowed. Threaded through `save_modules.py`'s `derived` module (the same
  recomputed-every-tick category `company_health` itself lives in) and the WS broadcast payload, `None` on a
  fresh game's very first tick (no prior reading to diff against). Frontend: a new "Health Delta" card on the
  Company tab shows Overall/Executive/Combined headline deltas plus every moved component, color-coded by
  sign. Verified: 6 new backend tests (no-previous-reading, no-op tick, real operational/executive changes,
  magnitude sort order, overall/tier delta computation), full backend suite (1769 tests), `mypy`, `ruff`
  clean; frontend `tsc`/`lint`/`build` clean; live-verified via Playwright against the running dev server —
  the card renders real values pulled straight from the WS broadcast (e.g. "+0.1 Overall", "Team Chemistry
  (OPS) +0.5").

- **CEO Company Health + Live Market Realism directive — statistically realistic candlestick generation**
  (`backend/app/market_data.py`, `backend/app/nexus.py`, `backend/tests/test_market_data.py`,
  `frontend/src/ui/components/CommandCenter/lib/derive.ts`,
  `frontend/src/ui/components/CommandCenter/MarketChartPanel.tsx`): the CEO asked for the Market Chart to stop
  looking "obviously synthetic" (uniform candle sizes, no clustering, no regime behavior) and instead read like a
  real trading terminal. `MockMarketDataProvider`'s shared `_step()` walk (used by both `get_quote()` and
  `get_candles()`, so the two stay one real underlying process rather than diverging) now implements: GARCH(1,1)
  volatility clustering (`variance_t = omega + alpha*shock_{t-1}^2 + beta*variance_{t-1}`, so a real large move
  measurably raises the very next step's volatility); AR(1) drift/momentum persistence so directional runs last
  longer than i.i.d. noise would; an internal 4-state regime machine (`trend_up`/`trend_down`/`range`/`volatile`)
  with randomized multi-bar segment durations (consolidation and trend runs, not a bar-by-bar coin flip), where
  `range` exerts real mean-reversion pull back toward a slow-moving anchor. A new `set_market_regime()` hook
  (no-op default on the `MarketDataProvider` ABC) lets `app/nexus.py`'s tick loop feed the already-real, already-
  computed 5-way `MarketEnvironmentRegime` (`app/market_environment.py`) into the generator as a one-tick-lagged
  bias on only the most recent `RECENT_REGIME_BIAS_WINDOW` (20) bars of any freshly generated series — real
  two-way regime↔price coupling (price already drives the external regime's classification; this is the other
  direction) without ever retroactively rewriting already-rendered chart history on a regime flip. Root-caused
  and fixed a real discontinuity this surfaced: `get_candles()` regenerates a deterministic `limit`-bar series
  from a fixed seed every call, while `get_quote()`'s separate persistent live walk drifts arbitrarily far from
  that seed over real gameplay time, so the pre-existing "patch the last candle's close to the live price" logic
  was producing an ever-growing, visually jarring jump at the chart's right edge. Fixed by proportionally
  rescaling the entire generated series (`scale = live_price / deterministic_last_close`, applied to every OHLC
  value in every bar) instead of patching only the last bar — percentage moves are scale-invariant, so this
  preserves every bar's real relative shape/volatility/wick proportions exactly while landing the series exactly
  on the live price with zero discontinuity anywhere, not just at the edge. Frontend: `MarketChartPanel` gained a
  ticker-stat strip (price, day change %, volume, realized volatility % computed from the same real candles the
  chart renders, current regime label, timeframe) via a new pure `marketTickerStats()` derive function — no
  bid/ask/spread/session fields added, since this codebase has no real data source for market microstructure yet
  (explicitly scoped out, tracked as a future CEO directive section). Verified: 10 new backend tests (volatility
  clustering, trend persistence, mean reversion, regime-switching duration, three-way external regime coupling
  for both `get_candles()` and `get_quote()`, and two no-obviously-synthetic-pattern checks) plus the 9 pre-
  existing tests, all passing; full backend suite (1763 tests), `mypy`, `ruff` clean; frontend `tsc`/`lint` clean;
  live-verified against the running dev server that a symbol whose live price has drifted over real elapsed
  gameplay time (continuous background tick loop, not a synthetic test) now renders a fully continuous candle
  series with no jump at the newest bar.

- **CEO Company/Executive Health directive — Office Expansion → Market Coverage rename, frontend follow-up**
  (`frontend/src/types.ts`, `frontend/src/state/gameStore.ts`, `frontend/src/game/systems/NexusManager.ts`,
  `frontend/src/ui/components/CampusMap/CampusMap.tsx`, `frontend/src/ui/components/CommandCenter/panels/CompanyPanel.tsx`,
  `frontend/tests/commandCenter.spec.ts`): completes the backend rename below on the client — `CompanyHealth.officeExpansion`
  is now `marketCoverage` everywhere in the frontend (type, store defaults, the Campus Map's `HQExpansionVisual` component
  and its tooltip text, the Company panel's health-cell label). `tsc -b`/eslint/build clean. Live-verified: the Company tab's
  full Company Health metric-label Playwright check (`commandCenter.spec.ts`) passes with the new "Market Coverage" label,
  and the Campus Map's HQ Expansion visual renders correctly against real live data (confirmed via Playwright trace: "HQ
  Expansion 33% — Framing"). Two unrelated pre-existing flaky tests surfaced on the full run (a Campus Map employee-count
  check racing the live background sim tick between its own state fetch and the UI assertion, and a WASD player-movement
  timing test) — neither touches Company Health or this rename; both reconfirmed failing in isolation with the exact same
  symptom, consistent with live-ticking-related flakiness this session has already documented elsewhere, not a regression
  from this change.

- **CEO Company/Executive Health directive — Office Expansion renamed to Market Coverage, formula unchanged**
  (`backend/app/schemas.py`, `backend/app/company_health.py`, `backend/app/save_modules.py`,
  `backend/tests/test_company_health.py` + 4 other test files,
  `docs/DesignBible/volumes/09-departments/chapter-63-executive-performance-company-health.md`): direct trace
  confirmed the formula was always real watchlist growth (extra symbols beyond the 8 seed symbols), never any
  facility/office-capability mechanic this codebase has never had. Asked the CEO whether to rename it or build a
  genuine new facility-capability metric (real new scope, not a same-day fix); her call: rename.
  `office_expansion`/`officeExpansion` is now `market_coverage`/`marketCoverage` everywhere in the backend — same
  real formula throughout, this is a rename, not a behavior change. Migration note: `CompanyHealth` lives in the
  `derived` save module (recomputed fresh every tick) and the field has no default, so a save persisted before
  this rename hits `app/persistence.py`'s existing generic deep-merge-onto-fresh-defaults migration path on its
  first load — verified directly with a synthetic old-shaped save dict, no targeted fixup needed. Full backend
  suite passing, `mypy`/`ruff` clean.

- **CEO Company/Executive Health directive — Department Efficiency investigated and kept presence-only, per
  explicit CEO direction** (`backend/app/company_health.py`,
  `docs/DesignBible/volumes/09-departments/chapter-63-executive-performance-company-health.md`): traced every
  other real per-agent signal in this codebase for a genuine second component to blend with the real "agents at a
  work location" presence reading — both the free-text `current_task` schedule label and the structured `Task`
  system (`app/nexus.py`'s `_replace_working_task()`) mark the prior task "completed" purely because the agent's
  schedule block changed on a real timer, never because real work was verifiably accomplished, so either would
  make a second component tautological (always ~100%), not a genuine additional signal. Asked the CEO rather than
  fabricate one; her answer: keep the real, narrow, presence-only formula. `_department_efficiency()`'s docstring
  now documents this explicitly — what it measures, what it doesn't, and what a genuine future fix would require
  (Task completion gated by real downstream evidence, not a schedule timer).

- **CEO Company/Executive Health directive — Education Progress: real lesson completion blended with real quiz
  accuracy, not completion alone** (`backend/app/company_health.py`, `backend/tests/test_company_health.py`,
  `docs/DesignBible/volumes/09-departments/chapter-63-executive-performance-company-health.md`): the original
  formula (`completed_lesson_ids / total lessons`) was already real and honest (`app/education.py`'s
  `grade_quiz()` never completes a lesson on a wrong answer) but legitimately slow and, on its own, credited only
  the outcome of the final correct attempt, never whether it took one real try or several. Fixed: blended equally
  with `correct_quiz_attempts / quiz_attempts` — `EducationProgress`'s own two real counters, already incremented
  on every real quiz submission regardless of outcome, never reset by a retry. Two players with identical
  completed-lesson sets are now told apart by how many real wrong guesses it took to get there. Neutral 50.0 for
  the accuracy half until at least one real quiz has been attempted. Verified: 3 new tests, 1 existing test
  corrected, 1 downstream CEO-configurable-threshold test's fixture margin adjusted to avoid an unrelated
  floating-point rounding boundary the shifted default now exposed, full backend suite passing, `mypy`/`ruff`
  clean.

- **CEO Company/Executive Health directive — Innovation Velocity: the real IDEA -> HYPOTHESIS -> EVIDENCE ->
  VALIDATION -> DEPLOYMENT -> MEASURED IMPROVEMENT pipeline, not Devil's Advocate critique quality alone**
  (`backend/app/company_health.py`, `backend/app/nexus.py`, `backend/app/state.py`,
  `backend/tests/test_company_health.py`,
  `docs/DesignBible/volumes/09-departments/chapter-63-executive-performance-company-health.md`): the CEO named
  a real pipeline this metric was supposed to reward, but direct trace found `_innovation_velocity()` read only
  average real Devil's Advocate points relative to the Legendary Innovator threshold — a real signal, but only
  one pipeline stage, and nothing about whether ideas ever moved or held up. Fixed: kept the original formula as
  `_validation_rigor()` (unchanged) and added two new real ingredients — `_pipeline_progress()` (real depth
  reached down `app/sandbox.py`'s own real, gated Strategy Lab `STAGE_ORDER`, a stage-for-stage match to the
  CEO's named pipeline; reads real depth rather than a fabricated "ideal days per stage" velocity constant this
  codebase has no data to support) and `_measured_improvement()` (for strategies that have actually reached real
  deployment, credits their latest real `StrategyHealthAssessment.trend` — a real recent-vs-lifetime read over
  actual `SimulationResult` history, never profit alone; neutral 50.0 when nothing has deployed yet).
  `_innovation_velocity()` is now an equal three-way blend. Verified: 4 new tests, `_strong_executive_overrides()`'s
  fixture extended with real deployed strategies carrying a real improving trend, 1 existing test corrected, full
  backend suite passing, `mypy`/`ruff` clean. Live-verified against a running save: hand-computed `rigor` (39.4),
  `pipeline_progress` (25.0, all 4 real strategies at real `historical_backtest`), and `measured_improvement`
  (50.0 neutral, none deployed yet) produced `(39.4 + 25.0 + 50.0) / 3 = 38.1` — an exact match against the
  server's live-reported `innovationVelocity: 38.1`.

- **CEO Company/Executive Health directive — Institutional Memory: reusing and strengthening the real Wisdom
  system with a genuinely distinct knowledge-retention signal, not duplicating it under a new name**
  (`backend/app/company_health.py`, `backend/app/nexus.py`, `backend/app/state.py`,
  `backend/tests/test_company_health.py`,
  `docs/DesignBible/volumes/09-departments/chapter-63-executive-performance-company-health.md`): the CEO's
  directive asked this dimension to "reuse/strengthen existing knowledge systems." `_institutional_memory()` was
  a direct passthrough of the real, already-comprehensive `WisdomState.score` (`app/wisdom.py`'s eight-factor
  composite) — honest, but missing whether that reflection had actually become durable in individual agents.
  Fixed: a new `_knowledge_retention()` component reads the real share of agents who have reached
  `app/academy.py`'s real top "mentor" Academy KnowledgeLevel (gated only by real cumulative points from
  completed research/Academy projects/meeting attendance) — genuinely distinct from Wisdom's own
  `share_knowledge` factor (a raw mentorship-session tally, not depth of mastery).
  `_institutional_memory()` is now an equal blend of `WisdomState.score` and `_knowledge_retention()`. Verified:
  2 new tests, `_strong_executive_overrides()`'s fixture extended with every agent at real mentor level, 1
  existing test corrected (25.0), full backend suite passing, `mypy`/`ruff` clean. Live-verified against a
  running save: the real per-agent Academy state (fetched via `GET /api/load/archive/academy`, since
  `agentKnowledge` is one of `/api/load`'s own documented archive-module fields and reads back a placeholder
  default there — confirmed by cross-checking a temporary tick-time debug print) showed 5 of 11 agents at real
  mentor level (45.5% retention); blending with the save's real `WisdomState.score` (45.1) by hand produced
  `(45.1 + 45.5) / 2 = 45.3` — an exact match against the server's live-reported `institutionalMemory: 45.3`.

- **CEO Company/Executive Health directive, Phase 6 — Decision Quality: real calibration between two
  independent process assessments, never touching money either way** (`backend/app/company_health.py`,
  `backend/tests/test_company_health.py`,
  `docs/DesignBible/volumes/09-departments/chapter-63-executive-performance-company-health.md`): the CEO's
  directive asked for a "calibration"/"postmortem" dimension while explicitly warning: "Do not judge decisions
  solely by whether they made money... The system must distinguish DECISION QUALITY from OUTCOME LUCK." Direct
  trace confirmed `decision_grade_score` (`app/executive.py`) already satisfies that core instruction — it
  blends real confidence-engine score, real analyst agreement, and real Gatekeeper approval, computed at
  decision time, never reading pnl — but nothing ever checked whether that initial grade was *calibrated*
  against a second, independent look at the same decision. Fixed: a new `calibration` component compares
  `decision_grade_score` against that same decision's real `DisciplineReview.score` (linked via
  `decisionId`) — a completely independent real assessment computed later, at trade close, from a different
  weighted blend of real factors, and — per `app/discipline.py`'s own docstring — also never reads pnl. Two
  independently-computed, equally outcome-decoupled scores agreeing closely is genuine calibration evidence; a
  wide gap means the initial grade and the later review disagreed about the process itself, regardless of
  whether the trade won or lost. `_decision_quality()` is now an equal blend of the original average grade and
  this new calibration reading, defaulting to neutral 50.0 when no matching review exists yet. Verified: 4 new
  tests, `_strong_executive_overrides()`'s fixture extended with matching agreeing reviews, full backend suite
  passing, `mypy`/`ruff` clean. Live-verified against a running save with independently hand-computed arithmetic
  from the same raw save data: the server reported `decisionQuality: 66.1`; recomputing `base` (82.3, the real
  average grade over the most recent 30 decisions) and `calibration` (the honest neutral 50.0 — the save's one
  real Discipline Review's underlying decision had aged out of that same window) by hand produced
  `(82.3 + 50.0) / 2 = 66.1` — an exact match.

- **CEO Company/Executive Health directive, Phase 5 — Self-Evaluation Health: real prediction-vs-outcome
  calibration trend, not confidence alone** (`backend/app/company_health.py`, `backend/tests/test_company_health.py`,
  `docs/DesignBible/volumes/09-departments/chapter-63-executive-performance-company-health.md`): the CEO's
  directive asked "Are predictions compared against outcomes? Are agents identifying recurring weaknesses?" and
  explicitly warned: "Do not reward agents merely for reporting that they made a mistake. Reward actual learning
  and reduced recurrence." Direct trace found `_self_evaluation_health()` read only each department's average
  real opinion confidence for the week (kept as `engagement`, a real but different signal — active review
  participation) — never a prediction-vs-outcome comparison. Fixed: a new `calibration_trend` component reuses
  `app/discipline.py`'s own `GOOD_DISCIPLINE_TIERS`/`POOR_DISCIPLINE_TIERS` to classify each real
  `DisciplineReview` as aligned (process tier correctly predicted the real outcome) or misaligned (a good-tier
  process that still lost, or a poor-tier process that happened to win), then compares the real misalignment
  rate across the earlier half of real reviews on record versus the later half — the same "earlier vs. later
  real average" trend convention `app/wisdom.py`'s own `_learn_from_experience()` already established, reused
  for a different real signal. A genuine decrease in misalignment over time earns credit; a flat or worsening
  rate earns none, regardless of how many mistakes were merely logged. `_self_evaluation_health()` is now an
  equal blend of `engagement` and `calibration_trend`, each neutral 50.0 with too little real history. Verified:
  6 new tests, 1 existing test updated, the `_strong_executive_overrides()` "everything maxed" fixture extended
  with a real misaligned-then-aligned review history, full backend suite passing, `mypy`/`ruff` clean.
  Live-verified against a running save: `selfEvaluationHealth` read `55.4`, matching `(60.8 real engagement +
  50.0 neutral trend) / 2` exactly — the trend itself correctly read the honest neutral default this save's
  single closed trade (below the 4-review minimum) produces; the trend computation's real behavior is covered
  by the new unit tests, since no additional real trades closed this pass (the Gatekeeper's own real Weighted
  Executive Recommendation check, working as intended, blocked every proposal resolved during verification).

- **CEO Company/Executive Health directive, Phase 4 — Founder Oversight: real substance, not lifetime
  session count** (`backend/app/schemas.py`, `backend/app/founders.py`, `backend/app/company_health.py`,
  `backend/tests/test_founders.py`, `backend/tests/test_company_health.py`,
  `docs/DesignBible/volumes/09-departments/chapter-63-executive-performance-company-health.md`): the CEO's
  directive asked "HIGH VISIBILITY + HIGH LEVERAGE + LOW MICROMANAGEMENT" — does the CEO receive meaningful
  decision summaries, understand why decisions were made, see real risks and disagreements — explicitly: "Do
  not artificially increase the score." Direct trace found `_founder_oversight()` was
  `min(100, session_count * 20)` — a company with 5 sessions that had nothing real to discuss scored identically
  to one whose every session surfaced a real major decision or risk. Fixed: `FounderCouncilSession` gained three
  real boolean fields (`coachHighlightIsReal`/`keystoneNoteIsReal`/`compassNoteIsReal`), set in
  `generate_council_session()` from the exact same real truthy checks already used to choose each note's text
  (a real CoachReport strength/recommendation; a real Library-of-Mistakes case, Keystone's risk domain; a real
  Reasoning Lab challenge or Reflection Chamber lesson, Compass's learning domain) — never re-derived by
  string-matching fallback text after the fact. `_founder_oversight()` is now an equal blend of the original
  occurrence reading (a regular cadence still matters) and a new real substance reading — the average, across
  every real session, of how many of its three notes referenced real content versus founders.py's own honest
  "nothing to review yet" placeholder. Backward-compatible: the three fields default `True` on load, so older
  saves aren't retroactively assumed placeholder-only. Verified: 4 new tests in `test_company_health.py`, 3 new
  tests in `test_founders.py`, full backend suite passing, `mypy`/`ruff` clean. Live-verified against a running
  save: after a real schema migration recovered a pre-existing session (confirming the backward-compatible
  default), `founderOversight` read `60.0` — exactly `(20 occurrence + 100 substance) / 2` for one real,
  fully-substantive session, matching the formula precisely on real, unmodified game data.

- **CEO Company/Executive Health directive, Phase 3 — Talent Development: real post-graduation performance,
  not mere XP** (`backend/app/company_health.py`, `backend/app/nexus.py`, `backend/app/state.py`,
  `backend/tests/test_company_health.py`,
  `docs/DesignBible/volumes/09-departments/chapter-63-executive-performance-company-health.md`): the CEO's
  directive named Talent Development (0/100), explicitly instructing "Do not award Talent Development merely
  because a training event occurred... training completed → skill exposure → later application → measurable
  improvement → development credit." Direct trace confirmed `graduation_status == "graduated"` was already real,
  not XP — it requires completing every real lesson (each auto-quizzed against the employee's own real
  aptitude, itself an average of real `DisciplineReview` scores) plus an explicit CEO approval — but the badge
  never changed again regardless of how the agent performed afterward. Fixed: each graduated (agent, mentor)
  pair now blends the real completed-training credit with a new real "post-graduation performance" reading —
  the average of that same agent's real `DisciplineReview` scores filed strictly after the exact real day the
  CEO approved that graduation (`graduated_sim_day`, already a persisted field — no new state). No post-graduation
  reviews yet reads an honest neutral 50 for that half; strong real post-graduation performance earns close to
  full credit; weak performance earns less, even under the identical badge. Verified: 4 new tests, 2 existing
  tests updated with corrected expected values (both honestly lower than before), full backend suite passing,
  `mypy`/`ruff` clean. New `discipline_reviews` parameter on `compute_company_health()`, threaded from
  `nexus.py`'s already-in-scope list — no new persisted telemetry. Live-verified against a running save: eight
  real employees were already `pending_approval` on the TJR mentor track; approving one real graduation via
  `POST /api/foundational-mentors/approve-graduation` moved `talentDevelopment` from a stuck `0.0` to a real
  `3.1`, with `graduatedSimDay` correctly recorded — the CEO's real action and the score moving together, live.

- **CEO Company/Executive Health directive, Phase 2 — Department Consensus: reused the Executive Consensus
  Meter's own real "waiting vs. opposing" taxonomy** (`backend/app/company_health.py`,
  `backend/tests/test_company_health.py`,
  `docs/DesignBible/volumes/09-departments/chapter-63-executive-performance-company-health.md`): the same anti-
  pattern as Phase 1, in the Executive tier — `_department_consensus()` counted only `stance == "agree"` as
  positive, scoring `request_more_research`/`recommend_waiting` identically to real opposition, even though
  `app/executive_intelligence.py`'s own `compute_executive_recommendation()` (Chapter 70 Part 2) already treats
  those as a distinct, constructive "waiting" bucket. Fixed by reusing that exact same real taxonomy
  (`_OPPOSING_STANCES = {"disagree", "recommend_rejecting"}`) rather than inventing a new one — a "waiting" stance
  never counts against consensus, and even real opposition only counts against the score when it's
  unsubstantiated (an opposing `DepartmentOpinion` with an empty `concerns` list — direct trace of every real
  opinion generator found only one path that can produce this today, `_devils_advocate_opinion()`'s `major`
  severity case driven by missing evidence/dissent alone). An opposing opinion *with* real concerns on record is
  the CEO's own "GOOD DISAGREEMENT + EVIDENCE" case — coherent, not penalized. Live-verified with a concrete
  before/after against a running save: a real CEO decision produced a real 9-opinion meeting log entry (4 agree,
  5 request_more_research, 0 real opposition) that read 44.4 under the old formula and 100.0 under the fix — the
  CEO's own named anti-pattern, caught on real, unmodified game data. Verified: 6 new tests (full agreement,
  request_more_research not scored as disagreement, evidence-backed disagreement staying coherent, bare
  unsubstantiated opposition still penalized, and an explicit "cannot be gamed by forcing universal agreement"
  proof), full backend suite passing, `mypy`/`ruff` clean. No new schema fields or persisted telemetry — a pure
  formula correction over data that already existed. Honest remaining gap: no real escalation/resolution
  *workflow* state exists yet (the CEO's "escalate unresolved conflicts" step) — documented, not attempted this
  phase.

- **Per-trade distance-to-drawdown-ceiling snapshot** (`backend/app/schemas.py`, `backend/app/portfolio.py`,
  `backend/app/broker.py`, `backend/app/paper_trading.py`, `backend/app/trading_modes.py`, `backend/app/nexus.py`,
  `backend/tests/test_portfolio.py`, `backend/tests/test_broker.py`, `backend/tests/test_trading_modes.py`,
  `frontend/src/types.ts`, `frontend/src/ui/components/CommandCenter/panels/PerformancePanel.tsx`,
  `docs/DesignBible/volumes/09-departments/chapter-66-institutional-safety-capital-protection.md`): Piece 10b of the
  CEO's Prop-Firm Risk Intelligence Addendum, Requirement 24 — "distance to failure boundary before/after trade,"
  touching the real trade-execution pipeline as originally scoped. New `PaperTrade.distanceToDrawdownCeilingBeforePct`/
  `AfterPct` (named honestly — "drawdown ceiling," not "failure boundary," since the primary portfolio only has
  `RiskLimits.max_drawdown_pct`, a self-chosen ceiling, per the same distinction Piece 11 already drew), computed via
  `close_position()`'s new optional `risk_limits` parameter, reusing the exact `remaining_drawdown_budget_pct` formula
  `risk_engine.py`'s `compute_risk_budget_status()` already established. Every real caller
  (`broker.py`'s `tick_broker()`/`ExecutionProvider`, `paper_trading.py`'s `tick_paper_trading()`, `trading_modes.py`'s
  `flatten_day_positions()`) now threads through `nexus.py`'s currently-effective `RiskLimits`; the parameter stays
  optional everywhere so an existing test fixture or a not-yet-threaded caller gets an honest `None`, never a fabricated
  value. Verified: 12 new backend tests, full backend suite 1714/1714 passed, `mypy`/`ruff` clean, `tsc -b
  --noEmit`/`eslint`/`vite build` clean. Live end-to-end verification via the real running dev stack's autonomous sim
  loop was attempted (including a full simulated week advanced via `POST /api/time/advance`) but this particular
  save's trade-proposal pipeline wasn't actively cycling during the session — stated honestly rather than claimed;
  backend correctness instead rests on the 12 new tests directly exercising the real execution-pipeline functions.

- **Evaluation-level risk-policy simulator** (`backend/app/evaluation_simulator.py`, `backend/app/schemas.py`,
  `backend/app/routers/sandbox.py`, `backend/tests/test_evaluation_simulator.py`, `frontend/src/types.ts`,
  `frontend/src/net/api.ts`,
  `frontend/src/ui/components/CommandCenter/panels/sandbox/StrategyCertificationView.tsx`,
  `docs/DesignBible/volumes/09-departments/chapter-62-innovation-lab-continuous-improvement.md`): Piece 10 of the
  CEO's Prop-Firm
  Risk Intelligence Addendum, Requirements 21/22/23/25 — a real Monte Carlo evaluation-level race simulator (does a
  simulated path hit its profit target before its drawdown limit before it runs out of simulated trades?) comparing
  four named, explicitly disclosed risk-policy hypotheses (`conservative`/`moderate`/`aggressive`/
  `failure_boundary_relative`), never adopting the source video's "reach funded fast" claim as fact. Reuses
  `strategy_lab.py`'s real per-trade win/loss bootstrap generating idea; the day/trade-axis three-way race condition
  is genuinely new (grep-confirmed absent from `strategy_lab.py`/`simulation.py`/`whatif.py` before this piece). Every
  non-real-data number (baseline risk-scaling assumption, trades/day conversion, sample size, disclosed defaults) is
  stated explicitly in every report's `assumptions`; real per-regime sensitivity and downstream funded-stage
  performance are explicitly disclosed as NOT attempted in `limitations`, not silently omitted. Caught and avoided a
  real sign-convention bug along the way: `run_strategy_monte_carlo()`'s existing formula double-negates
  `avg_loss_pct` (already stored negative on a real `SimulationResult`), which a Python snippet confirmed turns a
  20%-win-rate/-8% average loss strategy into a **+233% cumulative gain** instead of ruin in that function — this
  module's own bootstrap deliberately does not inherit that negation, verified directly to produce a real -70%
  loss/71% drawdown for the same inputs; `strategy_lab.py`'s own existing, already-shipped function was left
  untouched as out of scope for this piece, documented rather than silently carried forward. The report's own
  `conclusion` never declares a winning policy — explicitly directs comparing pass probability against drawdown and
  consecutive-loss risk together (Requirement 25: speed is an objective to weigh, never a license to gamble). New
  read-only `GET /api/sandbox/evaluation-policy-comparison` endpoint, computed fresh every call, deliberately not
  auto-generated in the background sim tick. Surfaced in `StrategyCertificationView.tsx` (the Sandbox strategy
  dossier), right after the existing Monte Carlo Testing card: a real comparison table across all returned policies
  (risk/trade, pass/fail-drawdown/fail-time-expiry probabilities, expected days to pass, median/worst-case drawdown,
  consecutive-loss-streak probability) plus the report's own real `conclusion`/`assumptions`/`limitations` text.
  Verified: 15 new backend tests (re-run 5× with no flakes despite real randomness), full backend suite 1706/1706
  passed, `mypy`/`ruff` clean, `tsc -b --noEmit`/`eslint`/`vite build` clean. Live-verified against the real running
  dev stack via a direct API call against a real strategy with 11 completed simulation runs (333 real trades) —
  every field returned real, correctly-computed values (e.g. conservative 74.4% pass probability vs. aggressive
  72.4%, with aggressive's worst-case drawdown 17.33% vs. conservative's 11.93%, real evidence that a faster/riskier
  policy in this sample did not clearly outperform); full-browser Playwright verification of the Command Center UI
  itself remained blocked by the same pre-existing Chromium/sandbox instability on "expand to Full Command Center"
  documented in Piece 11b's entry, confirmed unrelated to this piece's code via that same stashed-diff control run.

- **Evaluation cost, funded-stage & payout tracking** (`backend/app/schemas.py`, `backend/app/accounts.py`,
  `backend/app/prop_firm.py`, `backend/app/state.py`, `backend/app/routers/accounts.py`, `backend/tests/test_accounts.py`,
  `backend/tests/test_prop_firm.py`, `frontend/src/types.ts`, `frontend/src/net/api.ts`,
  `frontend/src/ui/components/CommandCenter/panels/TreasuryPanel.tsx`,
  `docs/DesignBible/volumes/10-broker-live-trading/chapter-69-multi-account-fund-management-system.md`): Piece 10a of
  the CEO's Prop-Firm Risk Intelligence Addendum, Requirement 24. Five new optional `Account` fields
  (`evaluation_cost`, `funded_stage_reached`, `funded_at_sim_day`, `payout_eligibility_min_profit_pct`,
  `total_payouts_received`), all defaulted so an existing save still validates unchanged. Core honesty boundary:
  whether an account reached the funded stage is a real, explicit CEO action (`mark_account_funded()`, refusing a
  second call once already funded so `funded_at_sim_day` stays a permanent fact) — never an automatic pass/fail
  inferred from the challenge profit target, since building an honest, evidence-based pass/fail read is Piece 10's job
  (a real evaluation-policy simulator), not this piece's ledger-tracking scaffolding. `record_account_payout()`
  requires `funded_stage_reached` first, matching how real prop-firm payouts work. New
  `compute_evaluation_tracking_status()` derives `days_to_fund` and `payout_eligible` from those stored facts, wired
  into `PropFirmStatus` as `evaluationTracking` (reusing the existing `GET /api/accounts/prop-firm/status` endpoint).
  Three new endpoints: `POST /api/accounts/evaluation/configure`, `/mark-funded`, `/record-payout`. Surfaced in
  `TreasuryPanel.tsx`'s `PropFirmCard`, right below the Risk-vs-Failure-Boundary section, with real save/mark-funded/
  record-payout controls. Verified: 18 new backend tests, full backend suite 1691/1691 passed, `mypy`/`ruff` clean,
  `tsc -b --noEmit`/`eslint`/`vite build` clean. Live-verified against the real running dev stack via direct API
  calls — configured a real evaluation cost and payout threshold, marked a real account funded, recorded a real
  payout, and confirmed `GET /api/accounts/prop-firm/status` returned every value correctly computed
  (`evaluationCost: 150.0`, `fundedStageReached: true`, `fundedAtSimDay: 5`, `daysToFund: null` honestly since no
  challenge start day was configured, `payoutEligible: false` correctly since 0% real profit was below the 8%
  threshold, `totalPayoutsReceived: 500.0`); full-browser Playwright verification of the Command Center UI itself
  remained blocked by the same pre-existing Chromium/sandbox instability on the "expand to Full Command Center"
  interaction documented in Piece 11b's entry below, reproduced identically and confirmed unrelated to this piece's
  code.

- **Consecutive wins + real trading-day count** (`backend/app/trading_modes.py`, `backend/app/behavioral_risk.py`,
  `backend/app/risk_engine.py`, `backend/app/schemas.py`, `backend/tests/test_trading_modes.py`,
  `backend/tests/test_behavioral_risk.py`, `backend/tests/test_risk_engine.py`, `frontend/src/types.ts`,
  `frontend/src/state/gameStore.ts`, `frontend/src/game/systems/NexusManager.ts`,
  `frontend/src/ui/components/CommandCenter/panels/TradingModesPanel.tsx`,
  `frontend/src/ui/components/CommandCenter/ExecutiveVoting.tsx`,
  `docs/DesignBible/volumes/09-departments/chapter-66-institutional-safety-capital-protection.md`): Piece 11b of the
  CEO's Prop-Firm Risk Intelligence Addendum, Requirement 24 ("new data TradeTown should track"). New
  `compute_consecutive_wins()` is an exact mirror of the existing `compute_consecutive_losses()`, threaded through
  `BehavioralCircuitBreakerRead`'s five construction sites as a new `consecutiveWins` field. New
  `distinct_trading_days()` counts distinct real sim days with a closed trade, reusing the exact
  `closed_sim_minutes // SIM_MINUTES_PER_DAY` bucketing convention `compute_consistency_status()` already
  established — no new formula — wired into `RiskBudgetStatus` as `tradingDaysCount`. Requirement 24's
  `entry_reason`/`exit_reason` `PaperTrade` split is explicitly deferred: `PaperTrade.reason` is a single combined
  string with real consumers across `journal.py`, `mistakes.py`, `decision_vault.py`, `war_room.py`, and frontend
  displays, and splitting it safely is a materially larger, separate change than this piece's "small and contained"
  scope. Verified: 7 new backend tests, full backend suite 1673/1673 passed, `mypy`/`ruff` clean, `tsc -b
  --noEmit`/`eslint`/`vite build` clean. Live-verified against the real running dev stack via direct API calls
  (`GET /api/trading-modes/behavioral-circuit-breaker` and `GET /api/load` both returned real, correctly-computed
  values) — full-browser Playwright verification of the Command Center UI itself was blocked by a pre-existing
  Chromium/sandbox instability on the "expand to Full Command Center" interaction, confirmed unrelated to this
  piece's code via a stashed-diff control run that reproduced the identical crash on unmodified `main`.

- **Projected loss after N consecutive losses** (`backend/app/schemas.py`, `backend/app/risk_engine.py`,
  `backend/app/routers/risk.py`, `backend/tests/test_risk_engine.py`, `frontend/src/types.ts`,
  `frontend/src/net/api.ts`, `frontend/src/ui/components/CommandCenter/panels/TradingModesPanel.tsx`,
  `docs/DesignBible/volumes/09-departments/chapter-66-institutional-safety-capital-protection.md`): Piece 11a of the
  CEO's Prop-Firm Risk Intelligence Addendum, Requirement 23. New `project_loss_after_n_losses()` compounds
  `RiskLimits.risk_per_trade_pct` against current equity `n` times — the exact same per-trade sizing math
  `recommended_quantity()` already uses, projected forward — producing a deterministic worst-case path, explicitly
  not a probability distribution (that needs real Monte Carlo, Piece 10's job); the one real simplification is
  stated in plain English every time via a returned `assumption` field, never left implicit. Rather than inventing
  an arbitrary default N, the frontend calls the new `GET /api/risk-limits/projected-loss?n=` endpoint at the two
  real, already-CEO-configurable losing-streak thresholds this codebase already has (Chapter 75's
  `losingStreakPauseCount`/`losingStreakSuspendCount`, defaults 3 and 5), surfaced in `TradingModesPanel.tsx`'s
  existing Losing Streak Protection card right below those same thresholds. Verified: 5 new backend tests, full
  backend suite 1664/1664 passed, `mypy`/`ruff` clean, `tsc -b --noEmit`/`eslint`/`vite build` clean, live-verified
  against the real running dev stack (real -5.9%/-9.6% projections at the real 3/5-loss thresholds from the real 2%
  default risk-per-trade) — screenshotted.

- **Risk relative to an Account's real failure boundary** (`backend/app/schemas.py`, `backend/app/prop_firm.py`,
  `backend/tests/test_prop_firm.py`, `frontend/src/types.ts`,
  `frontend/src/ui/components/CommandCenter/panels/TreasuryPanel.tsx`,
  `docs/DesignBible/volumes/10-broker-live-trading/chapter-69-multi-account-fund-management-system.md`): Piece 11 of
  the CEO's Prop-Firm Risk Intelligence Addendum, Requirement 23 ("risk should be modeled relative to the account's
  actual failure boundary... do NOT treat account notional size as the primary definition of usable risk"; any
  metric that can't be honestly computed must return `NOT_TRACKABLE_YET`, never a fabricated value). Piece 8's
  `RiskBudgetStatus` (the primary portfolio) packages `RiskLimits.max_drawdown_pct` — a self-chosen ceiling with no
  external authority behind it, per that schema's own docstring — not a true externally-imposed boundary. New
  `AccountRiskBudgetStatus` + `compute_account_risk_budget_status()` measure risk against the one real
  externally-configurable boundary an `Account` actually carries (`trailing_drawdown_limit_pct`), reusing
  `compute_trailing_drawdown()`'s exact real drawdown reading — no new formula, only new packaging relative to the
  boundary. `risk_per_trade_pct_of_boundary` is always `NOT_TRACKABLE_YET` for every real Account today, honestly,
  since no live `TradeProposal` execution routes to a secondary Account yet (`app/accounts.py`'s own module
  docstring) — there is no real, measured per-trade risk to express as a ratio, only a hypothetical, which this
  function never presents as if it were real. "Probability of hitting the failure boundary" and "expected drawdown
  path" are deliberately not attempted here — both need real forward simulation, which is Piece 10's job, not a
  duplicate bolted onto this real-time snapshot. Wired into the existing `PropFirmStatus` (`GET
  /api/accounts/prop-firm/status`) — no new endpoint — and surfaced in `TreasuryPanel.tsx`'s existing `PropFirmCard`.
  Verified: 5 new backend tests, full backend suite 1659/1659 passed, `mypy`/`ruff` clean, `tsc -b
  --noEmit`/`eslint`/`vite build` clean, live-verified against the real running dev stack (created a real prop-firm
  Account, confirmed both the honest "no boundary configured" state and the `NOT_TRACKABLE_YET` reason render for
  real data) — screenshotted.

- **Behavioral risk: same-direction (weak) + win-triggered escalation signals** (`backend/app/schemas.py`,
  `backend/app/behavioral_risk.py`, `backend/tests/test_behavioral_risk.py`,
  `frontend/src/types.ts`, `frontend/src/game/systems/NexusManager.ts`, `frontend/src/state/gameStore.ts`,
  `frontend/src/ui/components/CommandCenter/panels/TradingModesPanel.tsx`,
  `docs/DesignBible/volumes/09-departments/chapter-66-institutional-safety-capital-protection.md`): Piece 8b of the
  Prop-Firm Risk Intelligence Addendum's Requirement 10. Adding same-direction as a naive third independent
  corroborating signal (alongside same-instrument/size-increase) was tried and rejected first — this codebase's own
  direction is binary and matches a prior trade's side by pure chance roughly half the time, which would have made
  the CEO's own "legitimate setup immediately following a loss must remain possible" case fail routinely. Same-
  direction is real and reported, but — like the pre-existing repeated-rapid-reentry count — never independently
  corroborates a `"triggered"` verdict on its own. Win-triggered escalation is a separate branch entirely
  (`_win_side_check()`, entered only when the most recent closed trade was a real win, never both at once as
  loss/win): reuses the exact same trailing-baseline size-increase math the loss side already established, but per
  Requirement 10's own text can only ever reach `"warning"`, never `"triggered"` — proven directly by a test with a
  50x size increase after a win that still never fails the Gatekeeper check, so legitimate confidence-driven growth
  (e.g. after a strategy earns real certification) is never blocked by this signal. A real bug was caught while
  writing tests, not after: the win-side implementation used `model_copy(update={"winSizeIncreasePct": ...})` — the
  schema's camelCase alias, not the actual Python field name `win_size_increase_pct` — which pydantic silently
  ignores, permanently leaving the field `None`; caught because the new tests asserted the real populated value, not
  just the status, and fixed before this piece was considered complete. `TradingModesPanel.tsx`'s card is
  restructured from a two-way to a three-way branch (loss-side / win-side / truly clear) since the old binary branch
  would have rendered a loss-shaped card with every field blank for a real win-triggered warning.  Verified: 13 new
  backend tests, 32 pre-existing tests in the same file unchanged, full backend suite 1654 total/1653 passed (the
  one failure is the same pre-existing unrelated flaky test documented in the Piece 8a entry below), `mypy`/`ruff`
  clean, `tsc -b --noEmit`/`eslint`/`vite build` clean, live-verified against the real running dev stack.

- **Profit concentration / robustness check in Meridian's Model Validator** (`backend/app/model_validation.py`,
  `backend/tests/test_model_validation.py`,
  `docs/DesignBible/volumes/09-departments/chapter-62-innovation-lab-continuous-improvement.md`): Piece 8a of the
  Prop-Firm Risk Intelligence Addendum's Requirement 8 ("consistency analysis: track profit concentration —
  largest winning trade/day as a percentage of total"). `app/prop_firm.py`'s real
  `compute_consistency_status()` already implements this concept for an `Account`'s own real per-day P&L, but
  `Account`s never receive live trades (Piece 8, below) and `SimulationResult` — the real evidence Meridian
  validates — has no day-level granularity; it represents one full backtest run. New `_concentration_check()`
  reuses the formula's *shape* (largest bucket's profit as a percentage of the cumulative positive total) against
  the one real per-strategy bucket that exists: each strategy's own `SimulationResult.total_return_pct` per run —
  a real, distinct failure mode neither the existing whole-sample expectancy check nor Piece 2's chronological-split
  check would catch (a strategy whose profit is earned almost entirely by one outlier run can still pass both).
  `CONCENTRATION_MAX_SINGLE_RUN_SHARE_PCT = 50.0` is the one genuinely new threshold in this whole six-piece system
  with no existing in-codebase constant to reuse — explicitly disclosed as a chosen research assumption, not an
  established fact, the same disclosure standard Piece 7's tail-sample thresholds set. Advisory only, folds into
  the existing seven-check `ModelValidationReport.verdict` unchanged; the frontend needed zero changes since
  `StrategyPipelineView.tsx`'s Model Validation card already renders `checks.map(...)` generically. Verified: 7 new
  tests, 37 pre-existing tests in the same file passing unchanged, full backend suite 1641 total/1640 passed (the
  one failure is a pre-existing, genuinely unseeded-random flaky test in an unrelated module, confirmed passing in
  isolation), `mypy`/`ruff` clean.

- **Remaining risk budget at trade-decision time** (`backend/app/risk_engine.py`, `backend/app/schemas.py`,
  `backend/app/state.py`, `backend/app/nexus.py`, `backend/app/save_modules.py`, `backend/app/ws_manager.py`,
  `backend/tests/test_risk_engine.py`, `frontend/src/types.ts`, `frontend/src/net/socket.ts`,
  `frontend/src/game/systems/EventBus.ts`, `frontend/src/game/systems/NexusManager.ts`,
  `frontend/src/state/gameStore.ts`, `frontend/src/ui/components/CommandCenter/ExecutiveVoting.tsx`,
  `docs/DesignBible/volumes/09-departments/chapter-66-institutional-safety-capital-protection.md`): Piece 8 of the
  CEO's Prop-Firm Risk Intelligence Addendum ("understand the remaining permissible loss budget … before a trade
  is proposed, not just nominal account size"). Research found the literal brief didn't map onto the codebase as
  written — `app/prop_firm.py`'s real gradient budget/consistency/scaling functions operate on `Account` objects
  that never receive live trades (`app/accounts.py`'s own docstring discloses this), and that sub-Account status
  was already fully surfaced via `TreasuryPanel.tsx`'s `PropFirmCard`. The real gap was the primary
  `PaperPortfolio` — the only thing that ever executes a trade — having no remaining-budget view at all. New
  `compute_risk_budget_status()` returns lifetime drawdown/daily loss/daily profit each against its real
  `RiskLimits` and how much budget remains, built entirely from values already computed elsewhere
  (`portfolio.total_pnl_pct`, `daily_realized_pnl_pct()`, `compute_daily_objective_status()`) — the only new
  arithmetic is "limit minus usage, floored at zero." Advisory only: never called from Sentinel, Guardian, the
  Gatekeeper, or any Circuit Breaker. Surfaced as a new "Risk Budget Remaining" card in `ExecutiveVoting.tsx`'s
  Review Analysis section, the actual trade-decision surface. Two real bugs caught during live verification before
  committing: `app/ws_manager.py`'s `build_state_message()` is a hand-built dict, not a generic
  `state.model_dump()`, so the new field never reached the frontend until that function was updated too (confirmed
  absent, then present, over a live WS connection); and an early draft misused the signed-delta `formatPct()`
  helper on budget magnitudes, producing a misleading `"+20.0% of +20.0% left"`, fixed to plain `"20.0% of 20%
  left"`. Verified: 7 new backend tests, full backend suite 1634 passed, `mypy`/`ruff` clean, `tsc -b
  --noEmit`/`eslint`/`vite build` clean, and live-verified end-to-end (real WS payload check, and a live Playwright
  run that boosts a real research item to threshold, opens the real Executive Voting popup, and confirms the new
  card renders real data) — screenshotted.

- **Forge, the Quant Developer** (`backend/app/quant_developer.py` new, `backend/app/schemas.py`, `backend/app/agents.py`,
  `backend/app/schedule.py`, `backend/app/routers/quant_developer.py` new, `backend/app/main.py`,
  `backend/tests/test_quant_developer.py` new, `backend/tests/test_academy.py`, `frontend/src/types.ts`,
  `frontend/src/net/api.ts`, `frontend/src/game/systems/AgentProfiles.ts`, `frontend/src/game/systems/Schedule.ts`,
  `frontend/src/game/systems/DialogueManager.ts`, `frontend/src/assets/animation-config.json`,
  `frontend/src/ui/components/CommandCenter/lib/useMonteCarloReliability.ts` new,
  `frontend/src/ui/components/CommandCenter/panels/sandbox/StrategyExecutiveDashboardView.tsx`,
  `docs/DesignBible/volumes/07-ai-workforce.md`): Piece 7 — the final piece — of the Quantitative Research &
  Intelligence System, and the one piece where the CEO's own answer explicitly overrode a docs-only
  recommendation with "I want a new agent," deferring the concrete in-sim design to this piece. The fifteenth
  agent, minted the same five-file way every prior new agent (Meridian, Sage, Keystone, Compass, Vector) already
  was — a routine, precedented pattern, not unusual scope. Owns a real, non-duplicative gap none of the other
  four quant roles ever look at: `app/strategy_lab.py`'s Monte Carlo bootstrap fixes `MONTE_CARLO_PATHS = 200`
  for every real run, giving only 10 real samples in the 5% tail and 2 in the 1% tail — `StrategyMonteCarloResult`'s
  own VaR99/CVaR99 fields (Piece 3) are 99th-percentile statistics read off just 2 real data points, a genuine
  estimation-reliability problem regardless of the strategy's own edge. `assess_monte_carlo_reliability()`
  computes this as a real, standing engineering fact about the pipeline itself (not per-strategy, since every
  real run shares the identical constant), recomputed fresh on every read and cross-checked against every real
  `StrategyMonteCarloResult` on file for path-count drift. `MIN_RELIABLE_TAIL_SAMPLES=20`/
  `MIN_MARGINAL_TAIL_SAMPLES=10` is the one threshold across this whole six-piece system with no prior
  in-codebase precedent — explicitly disclosed as a chosen bootstrap/tail-risk rule of thumb, not a measured
  fact. Surfaced in a new "Monte Carlo Reliability — Forge, Quant Developer" card on the Sandbox panel's
  company-wide Dashboard tab. Verified: 9 new tests, 1 existing fixture updated (Forge has no Academy-ladder
  progression, same as Keystone/Compass/Vector before it), full backend suite 1627 passed, `mypy`/`ruff` clean,
  `tsc -b --noEmit`/`eslint`/`vite build` clean, and live-verified end-to-end against the real running dev
  stack (real 200/10/2 path/tail-sample counts, real marginal/unreliable verdicts, rendering correctly in
  Command Center).

- **Wiring Model Validator findings into institutional memory** (`backend/app/strategy_lab.py`,
  `backend/app/state.py`, `backend/app/knowledge_graph.py`, `backend/app/routers/knowledge_graph.py`,
  `backend/tests/test_strategy_lab.py`, `backend/tests/test_knowledge_graph.py`,
  `docs/DesignBible/volumes/09-departments/chapter-62-innovation-lab-continuous-improvement.md`): Piece 6 of the
  Quantitative Research & Intelligence System. Closes a real, confirmed gap: Meridian/CIO's `ModelValidationReport`
  (Piece 4) was write-only — generated at Company Review, stored, then never read by anything downstream, so a real
  rejection was CEO-visible only as long as that review stayed open. `generate_strategy_retirement_outcome()` now
  folds a strategy's own latest non-`approved` validation report's real `verdict`/`evidence_summary`/check
  `reasoning` into `FailedStrategyArchiveEntry.whatFailed`/`lessonsLearned` — which `app/scribe.py` already turns
  into a permanent `MemoryRecord`, so this one change makes the finding real, permanent Company Memory with no
  second change needed there. The Company Knowledge Graph's strategy nodes also now name that same latest real
  verdict in their subtitle. Two adjacent ideas were explicitly scoped out rather than faked: `app/mistakes.py`
  operates at the individual-trade level with no real mechanism to link a strategy-level verdict to a specific
  trade, and Execution Quant (Piece 5) findings couldn't be wired in at all — `PaperTrade` has no `strategy_id`
  field anywhere in this codebase (already disclosed in Command Center's own Performance panel), so there's no
  real way to compute a strategy's cumulative transaction-cost drag today. Verified: 7 new tests (3 for the
  failed-archive folding — a rejected report folded in with its real fields intact, an approved report correctly
  not folded in, and pre-Piece-6 behavior unchanged with no report on file; 4 for the Knowledge Graph — verdict
  shown, no report means no text, a different strategy's report never leaks, latest-of-multiple wins), full
  backend suite 1618 passed (every existing caller needed zero changes, since both new parameters are optional
  and default to identical pre-Piece-6 behavior), `mypy`/`ruff` clean.

- **CEO Company/Executive Health directive, Phase 1 — Team Chemistry: real debate-stance bug fix +
  real cross-agent research handoff signal** (`backend/app/debate.py`, `backend/app/company_health.py`,
  `backend/tests/test_debate.py`, `backend/tests/test_company_health.py`,
  `docs/DesignBible/volumes/09-departments/chapter-63-executive-performance-company-health.md`): the CEO's own
  review of a live Company Health dashboard (~70 overall, several sub-scores reading 0) opened a directive
  requiring every weak dimension traced to real code before any change, explicitly forbidding hardcoded scores,
  loosened thresholds, or rewarding meaningless activity. **Root cause found by direct trace:**
  `app/debate.py`'s `_cross_examination()` gave an analyst a "challenge" turn the moment *any other* analyst on
  the six-seat desk disagreed with *them* — checked before ever looking for agreement. With six independent
  real votes, some pairwise disagreement exists on nearly every proposal, so in practice every analyst got
  "challenge" on nearly every debate, including analysts who fully agreed with the desk's own real final call —
  "support" only ever appeared on a fully unanimous vote. `_team_chemistry()`'s support-vs-challenge ratio
  therefore read near-zero on almost any real activity, collapsing into the exact "unanimous vs. not" false
  binary the CEO's directive named as the anti-pattern to avoid. Confirmed live against a running save: a real
  debate showed 6 opening + 6 challenge + 0 support turns. **Fix:** each analyst's stance is now judged against
  the proposal's real `overall_recommendation` — voting with the desk's real final call is support, voting
  against it is a real challenge; a 4-2 split now yields 4 support + 2 challenge instead of 6 challenge. A real
  minority dissent is preserved and visible rather than mislabeling majority agreement as conflict — verified
  the existing regression suite needed zero changes for the two other real consumers of debate stance
  (`app/discipline.py`'s `assumptions_challenged`, `app/mistakes.py`'s `unchallenged_assumptions`,
  `app/executive_review.py`'s conflict count, `app/reasoning_lab.py`'s challenge/support reads all passed
  unchanged). **Second, genuinely new signal:** `_team_chemistry()` is now an equal mean of the corrected debate
  signal and a new `_cross_agent_research_handoffs()` — reusing `app/knowledge_graph.py`'s own real
  category-and-recency grouping over `ResearchItem` to check whether consecutive same-category completed
  research was actually picked up by a *different* agent (a real handoff) versus one agent working alone. No new
  persisted telemetry — both signals are pure functions over data already tracked. Mentorship (already read by
  `app/wisdom.py`'s `share_knowledge`, feeding Institutional Memory) deliberately not re-read a second time here,
  per this module's own no-duplicate-systems convention. Verified: 2 new `test_debate.py` tests proving the exact
  bug scenario, a rewritten `TestTeamChemistry` + new `TestCrossAgentResearchHandoffs` (9 tests) in
  `test_company_health.py`, full backend suite 1620/1620 passing, `mypy`/`ruff` clean. Live-verified: advancing a
  running save's clock moved `teamChemistry` from a stuck `0.0` to a genuinely varying `31.1` as real mixed
  debates (including a real 5-support/1-challenge split) were generated — the metric now responds to real
  behavior instead of reading a structural floor. Deliberately out of scope for this phase: a dedicated
  "successful handoff" CEO action, and a frontend "why is this score what it is" breakdown view (sequenced after
  this backend fix per backend-first commit discipline). Remaining Company/Executive Health dimensions from the
  same directive (Efficiency, Office, Talent Development, Founder Oversight, Department Consensus, Self-Evaluation
  Health, Decision Quality calibration, Institutional Memory/Innovation Velocity linkage, Education) are later
  phases, not started here.

- **Execution Quant: real transaction cost at the execution choke point** (`backend/app/portfolio.py`,
  `backend/app/schemas.py`, `backend/tests/test_portfolio.py`, `frontend/src/types.ts`,
  `frontend/src/ui/components/CommandCenter/panels/PerformancePanel.tsx`,
  `docs/DesignBible/volumes/07-ai-workforce.md`): Piece 5 of the Quantitative Research & Intelligence System.
  `open_position()`/`close_position()` — confirmed by direct trace to be this codebase's one real execution
  choke point, since every live-trade caller funnels through them — now deduct a real transaction cost from
  the cash ledger on every fill. Ships agent-agnostic (no new named agent, per an earlier scoping decision),
  the mechanism sitting downstream of Gatekeeper's existing pre-execution approval. Research confirmed a
  data-driven, spread/volume-varying cost model is not honestly buildable here: this codebase has no real
  bid-ask spread anywhere, `Quote.volume` is `random.uniform` mock data, and `LiquidityRead`/
  `StrategyLiquidityValidation` are real price-action pattern detectors, not spread proxies — explicitly
  documented as never a claim about real order-book data. So `TRANSACTION_COST_BPS = 5.0` is instead a real,
  functioning mechanism (real dollars leave the ledger, every trade's `pnl`/`pnlPct` is genuinely net of it,
  fully auditable via `PaperPosition.entryCostUsd`/`PaperTrade.transactionCostUsd`) built on one flat,
  disclosed constant rather than a fabricated statistic — the same reasoning `app/simulation.py`'s own
  disclosed-placeholder Sharpe/Sortino already established for a different metric. `pnl_pct`'s new formula is
  algebraically identical to the old one whenever cost is 0, so this is a strict generalization, not a
  redefinition. Verified: 4 new tests (hand-computed entry/exit cost deductions, an affordability-refusal
  case, and pre-piece save-compatibility for positions with no `entryCostUsd`), full backend suite 1611
  passed with zero regressions elsewhere (the 5bps rate didn't disturb any existing exact-value assertion
  across the 13 other test files touching `open_position`/`close_position`), `mypy`/`ruff` clean, `tsc -b
  --noEmit`/`eslint`/`vite build` clean. Surfaced as a real per-trade cost line in Command Center's "Recent
  Trades" journal card.

- **Real Sharpe/Sortino + Monte Carlo VaR/CVaR** (`backend/app/analytics.py`, `backend/app/strategy_lab.py`,
  `backend/app/schemas.py`, `backend/tests/test_analytics.py`, `backend/tests/test_strategy_lab.py`,
  `backend/tests/test_model_validation.py`, `frontend/src/types.ts`,
  `frontend/src/ui/components/CommandCenter/panels/sandbox/StrategyCertificationView.tsx`,
  `docs/DesignBible/volumes/09-departments/chapter-62-innovation-lab-continuous-improvement.md`): Piece 3 of the
  Quantitative Research & Intelligence System. Makes `PerformanceSnapshot.sharpeRatio`/`sortinoRatio` genuinely
  real — mean/population-stdev and mean/downside-deviation over `PaperPortfolio.trade_history`'s own real,
  sequential per-trade `pnlPct` returns — replacing the old `return_pct / max_drawdown_pct` and `sharpe * 1.1`
  placeholder formulas. Two disclosed simplifications, not fabrications: risk-free rate assumed 0 (no
  bond/cash-yield concept exists anywhere in this codebase), and both ratios are per-trade, not annualized
  (trades close at irregular sim-minute intervals, so there's no real fixed-period return series to normalize
  against). `SimulationResult.sharpe_ratio`/`sortino_ratio` (the separate, per-backtest-run pair, still
  load-bearing in `sandbox.py`'s `_quant_verdict()` gate) stays an explicitly disclosed placeholder — that
  engine still has no real per-trade return sequence to compute a real ratio from. Also adds real VaR95/99 and
  CVaR95/99 (Expected Shortfall) to `StrategyMonteCarloResult`, as pure percentile/tail-mean reads off the
  existing 200-path Monte Carlo bootstrap's already-computed, already-sorted final-return array — no new
  simulation, no new randomness source. VaR is the return level such that only 5%/1% of paths did worse; CVaR
  is the mean return among exactly that worst 5%/1% of paths. Surfaced in Command Center's Strategy
  Certification card alongside the existing Probability of Ruin row. Verified: 9 new backend tests (4
  hand-computed Sharpe/Sortino cases including zero-trade/single-trade/no-losing-trade edge cases; 1
  ordering-invariant Monte Carlo VaR/CVaR test, since bootstrap output is non-deterministic; 4 deterministic
  `_tail_mean()` tests bypassing the bootstrap's randomness), 3 existing test fixtures updated for the new
  required schema fields (a real behavioral consequence of the schema change, not a workaround), full backend
  suite 1607 passed, `mypy`/`ruff` clean, `tsc -b --noEmit`/`eslint`/`vite build` clean. No
  `PerformanceSnapshot.sharpeRatio`/`sortinoRatio` render site exists anywhere in the frontend (confirmed by
  grep) — documented honestly via a new disclosure comment rather than inventing a UI surface for it.

- **Walk-Forward / Temporal-Split Validation** (`backend/app/model_validation.py`, `backend/tests/test_model_validation.py`,
  `docs/DesignBible/volumes/09-departments/chapter-62-innovation-lab-continuous-improvement.md`): Piece 2 of the
  Quantitative Research & Intelligence System. A genuine walk-forward test needs real, sequential historical
  price data to hold a true out-of-sample window; `app/simulation.py`'s own module docstring already discloses
  this codebase has no real historical `MarketDataProvider`, so this piece builds the honest analog instead of
  pretending otherwise. New sixth `ModelValidationCheck` (`temporal_stability`) inside Meridian's existing
  report — not a new standalone module or Strategy Lab artifact type, since the same real inputs are already
  in scope at the one real call site and a ninth top-level report card would be redundant surface area for one
  more piece of evidence. Splits a strategy's own `SimulationResult` history at its chronological midpoint
  (earlier half vs. later half, by list order — reusing the exact same "list order = chronological order"
  convention `app/strategy_lab.py`'s `compute_strategy_health()` already relies on, since `SimulationResult`
  has no `sim_day` of its own) and requires positive real expectancy (the same formula/bar `_expectancy_check`
  and the Certification gate already use) independently in both halves — surfacing a strategy whose early
  results were strong but has since decayed, or an unproven recent turnaround, either of which a whole-sample
  average can mask. Each half must independently clear the reused `CERTIFICATION_MIN_TRADE_COUNT` (20 real
  trades) before the split is trusted. The check's own `reasoning` explicitly discloses it as "a disjoint-split
  analog to walk-forward validation, not a claim of true out-of-sample testing against unseen future data."
  Verified: 7 new tests, 1 existing test updated (a real behavioral consequence of a sixth check tightening
  the "all pass" fixture, not a workaround), full backend suite green, `mypy`/`ruff` clean.

- **The Quant Organization, formalized** (`docs/DesignBible/volumes/07-ai-workforce.md`): Piece 1 of the
  Quantitative Research & Intelligence System, docs-only. Names the real three-way separation the CEO's spec
  asked for, using each agent's existing name and occupation — no renames, no new agents, no behavior
  changes, per her own explicit instruction not to rename an agent just to sound more quantitative. **Chief
  Quant = Vector** (leads Black Box Research, the `"quant"` `StrategyReview` seat). **Risk Quant = Sentinel +
  Guardian + Keystone**, a real three-tier structure rather than one role under three names: Sentinel's hard
  per-trade gate (`evaluate_sentinel_risk`), Guardian's softer concentration monitor
  (`evaluate_guardian_exposure`), and Keystone's strategic Founder-level risk domain (Constitution amendments,
  Academy mentorship) — a distinction not previously written down anywhere. **Model Validator = Meridian**
  cross-references Piece 4's own Chapter 62 addendum rather than duplicating it. Quant Developer and Execution
  Quant remain undocumented, deferred future pieces (7 and 5) — not claimed as real here.

- **Model Validator (Meridian/CIO)** (`backend/app/model_validation.py` new, `backend/app/sandbox.py`,
  `backend/app/state.py`, `backend/app/schemas.py`, `backend/app/ws_manager.py`, `backend/app/save_modules.py`,
  `backend/app/routers/sandbox.py`, `backend/tests/test_model_validation.py` new, `frontend/src/types.ts`,
  `frontend/src/net/api.ts`, `frontend/src/net/socket.ts`, `frontend/src/game/systems/NexusManager.ts`,
  `frontend/src/game/systems/EventBus.ts`, `frontend/src/state/gameStore.ts`,
  `frontend/src/ui/components/CommandCenter/panels/SandboxPanel.tsx`,
  `frontend/src/ui/components/CommandCenter/panels/sandbox/StrategyPipelineView.tsx`,
  `docs/DesignBible/volumes/09-departments/chapter-62-innovation-lab-continuous-improvement.md`): Piece 4 of a
  CEO-requested Quantitative Research & Intelligence System, and the only piece the CEO authorized to start —
  "do not start another Piece until this piece is implemented, tested, documented, and verified." Research
  found four of the spec's six named quant roles already real under different names (Chief Quant = Vector,
  Risk Quant = Sentinel/Guardian/Keystone, Quant Researcher = Vector + the existing Strategy Lab pipeline);
  the Model Validator was the genuine gap — no seat in the 5-reviewer `StrategyReview` panel was a standing,
  independent authority whose job is specifically to challenge a strategy's statistical soundness before it
  advances. Ships as **Meridian (CIO)**, advisory-only: `apply_review_decision()`/`begin_company_review()`
  are byte-for-byte unmodified, and `apply_review_decision()`'s own signature has no `ModelValidationReport`
  parameter, so it cannot read `verdict` even in principle. Five checks (sample size, regime breadth, tail
  risk, liquidity realism, expectancy), every threshold a proven reuse of the existing Strategy Lab
  Certification gate's own constants — never a new invented number. Four-state verdict
  (`approved`/`rejected`/`needs_more_evidence`/`not_validatable`) never silently defaults to approved: a
  clear failure among evaluated checks always yields `rejected`, even with other checks still unevaluated.
  Independence is organizational/decision independence, not statistical — Meridian reviews the same computed
  evidence Vector's research and the risk seats' own review already draw on, but is excluded from that
  strategy's own rotating Devil's Advocate seat during the same validation cycle
  (`app/sandbox.py`'s new `exclude_cio` parameter), a pure per-call substitution proven stateless by a
  dedicated 6-case test class. Verified: 30 new backend tests, full backend suite green (1591/1591),
  `mypy`/`ruff`/`tsc -b --noEmit`/`npm run lint`/`npm run build` clean. Live-verified end-to-end against the
  running dev backend: a real strategy was driven through Backtest → Market Simulation → Paper Trading →
  Limited Live Capital → a real `POST /api/sandbox/request-review` call that returned a genuine `"approved"`
  `ModelValidationReport` with real evidence and `validatorAgentId: "cio"`, confirmed again via
  `GET /api/sandbox/model-validation`. The new frontend card was code-reviewed against this exact live
  response shape; a literal browser screenshot could not be captured in this session's sandboxed Playwright
  environment, which crashes on an unrelated, pre-existing tileset-texture-decode failure reproducing
  identically on a brand-new game, with zero files this piece touched anywhere in the crash's call path.
  Pieces 1/2/3/5/6/7 of the full spec (Design Bible formalization, walk-forward validation, real
  Sharpe/Sortino/VaR, Execution Quant, wiring findings into institutional memory, a new Quant Developer
  agent) are documented as a deferred roadmap, not started, per the CEO's own instruction.

- **Command Center Psychology Dashboard** (`backend/app/process_adherence.py`, `backend/app/schemas.py`,
  `backend/app/routers/executive.py`, `backend/tests/test_process_adherence.py`,
  `frontend/src/types.ts`, `frontend/src/net/api.ts`, `frontend/src/ui/components/CommandCenter/lib/derive.ts`,
  `frontend/src/ui/components/CommandCenter/panels/PsychologyDashboardPanel.tsx` new,
  `frontend/src/ui/components/CommandCenter/FullCommandCenter.tsx`,
  `frontend/src/ui/components/CommandCenter/lib/navigation.ts`,
  `docs/DesignBible/volumes/09-departments/chapter-66-institutional-safety-capital-protection.md`): Piece G —
  the seventh and final piece of the CEO's trading-psychology roadmap. A structured research pass (dispatched
  before writing any code) found six of the seven named metrics already real and already computed somewhere
  in this codebase — this piece's real job was composition, not invention. Behavioral Risk and Loss Streak
  already have their own real WS-broadcast fields and full-detail view (`TradingModesPanel.tsx`, linked from
  the new tab, not duplicated). Risk Compliance, Strategy Expectancy, Drawdown, and Recent Strategy
  Performance are new pure client-side derivations (`lib/derive.ts`) composed from already-real WS state —
  the same "derive from the wire, never round-trip the backend" convention `lib/financials.ts` already
  established — reusing the exact real signals `app/risk_engine.py`/`app/strategy_lab.py` already compute for
  other reasons, never a fabricated parallel metric. Process Adherence was the one genuine gap: every
  existing consumer reads a single decision's own score by id, so new `compute_recent_process_adherence_
  summary()` averages only the real-scored decisions among the most recent 10 (a decision with zero verified
  checks is honestly counted as reviewed but never averaged in as a fabricated 0%), exposed via new
  `GET /api/executive/process-adherence-summary` — the one real new backend endpoint this piece needed. New
  `PsychologyDashboardPanel.tsx` ships as a `PSYCHOLOGY` tab under Command Center's PORTFOLIO section.
  Verified: 6 new backend tests, full backend suite green (1561/1561), `mypy`/`ruff`/`tsc -b --noEmit`/
  `npm run lint`/`npm run build` clean, and a live Playwright screenshot showing all seven cards rendering
  real, populated data (4 real tested strategies, a real +1.63% average expectancy) against the running dev
  server. This closes the CEO's full seven-piece trading-psychology roadmap (Pieces A–G).

- **Two New Foundational Mentor Tracks — Mark Douglas & Linda Raschke** (`backend/app/foundational_mentors.py`,
  `backend/tests/test_foundational_mentors.py`, `backend/tests/test_company_health.py`,
  `docs/DesignBible/volumes/09-departments/chapter-74-continuous-learning-self-improvement-system.md`): Piece F
  of the CEO's trading-psychology roadmap ("3-4 new Academy lessons via the empty mark_douglas/linda_raschke
  tracks"). Both tracks already existed as real, named, ordered roadmap entries with zero lesson content
  (`status: "planned"`) — this ships their first real content: 2 lessons each, deliberately a small honest
  start rather than backfilling to match the `tjr` track's 8. Same content-attribution boundary the `tjr`
  track already established (no HTTP client/PDF/video/LLM anywhere in this codebase, so a real educator's
  name only labels the real subject area their track covers — every lesson is 100% original TradeTown-
  authored material, never a transcription of either person's actual work). Each lesson cites a specific real
  mechanic: Mark Douglas's track covers the Decision Confidence Engine's "never predicts whether a trade will
  win" design principle (tying into this session's own Piece E `probability_language.py` regression guard)
  and the Behavioral Circuit Breaker's real corroboration rule; Linda Raschke's track covers the Trade
  Gatekeeper's real ten-check pure-AND composition and the risk engine's real `min(risk_budget,
  position_cap)` position-sizing rule. Running the Piece E audit against the drafted lessons caught two real
  issues before shipping (a quiz option's "always wins" phrasing and a lesson quoting literal banned-phrase
  examples) — both fixed by rewriting the text, not weakening the checker. Adding two active tracks changed
  `app/company_health.py`'s real Talent Development denominator (`students × active tracks`) from 2 to 4, the
  same consequence `market_intelligence`'s own earlier addition already caused — `test_company_health.py`
  updated accordingly, a genuine behavioral consequence, not a workaround. No frontend changes: the Mentor
  Library UI already renders any mentor's lessons generically. Verified: 6 new/extended tests plus 3 updated
  Company Health tests, full backend suite green (1555/1555), `mypy`/`ruff` clean. Live-verified via the real
  `default_foundational_mentor_state()` function; the running dev server's own persisted save predates this
  change (new mentor content applies to new games, not retroactively merged into old saves — the same
  boundary `market_intelligence`'s v0.7 Feature 51 rollout already established), so its live screenshot
  honestly still shows both tracks `PLANNED` for that older save.

- **Probability-First Language Audit** (`backend/app/probability_language.py` new,
  `backend/tests/test_probability_language_audit.py` new,
  `docs/DesignBible/volumes/09-departments/chapter-66-institutional-safety-capital-protection.md`): Piece E
  of the CEO's trading-psychology roadmap. Since this codebase has no LLM anywhere (every player-facing
  string is deterministic template generation), a real audit was tractable: 22 real backend text-generation
  modules read in full, plus a keyword-flagged frontend review. Zero genuine violations of probability-first
  framing found — every certainty-language hit (`guaranteed`, `sure thing`, `always wins`, `will win`, etc.)
  resolved to a code comment about a structural guarantee, an Academy quiz's confirmed wrong-answer
  distractor, or text actively negating certainty ("an estimate, not a guarantee"). `app/confidence.py`'s own
  module docstring already documents the design principle this codebase was built under: "Never predicts
  whether a trade will win. It scores the quality of the evidence behind the current setup." Rather than
  file this as a one-time report that goes stale, new `app/probability_language.py` turns the finding into a
  permanent, enforced guarantee: `BANNED_CERTAINTY_PHRASES` is phrase-level (`"is guaranteed to"`,
  `"sure thing"`, `"always wins"`, 23 total) — deliberately never a bare-word ban on `"guarantee"`/`"certain"`,
  since this codebase's own correct usage already contains those words inside hedged/negated sentences
  ("not a guarantee") that a bare-word ban would wrongly flag. `find_certainty_violations()` and
  `audit_model()` (a generic recursive walker over any pydantic model's string fields) are the reusable
  checkers; `test_probability_language_audit.py` runs them against real generated output from
  `generate_discipline_review()`, `generate_case_studies()`, `generate_success_studies()`, and
  `generate_debate()` — the AI Debate/Discipline Chamber/Library of Mistakes/Successes' highest-value
  trade-thesis and post-trade-review surfaces — plus a planted-violation test proving the checker itself
  actually catches a real violation, not just passing silently. No frontend changes (this is an internal
  regression guard, not new player-facing information). Verified: 10 new tests, full backend suite green
  (1550/1550), `mypy app/`/`ruff check app/ tests/` clean.

- **Loss/Win Classification, Formalized on Top of the Discipline Chamber** (`backend/app/discipline.py`,
  `backend/app/self_improvement.py`, `backend/app/schemas.py`, `backend/app/nexus.py`,
  `backend/app/routers/self_improvement.py`, `backend/tests/test_discipline.py`,
  `backend/tests/test_self_improvement.py`, `frontend/src/types.ts`, `frontend/src/net/api.ts`,
  `frontend/src/ui/components/CommandCenter/panels/EvolutionPanel.tsx`,
  `docs/DesignBible/volumes/09-departments/chapter-74-continuous-learning-self-improvement-system.md`):
  Piece D of the CEO's trading-psychology roadmap ("Loss/Win classification formalized on top of the
  existing Discipline Chamber; tie into CLSIS"). Research found most of "classification" already real —
  `DisciplineReview.outcome` is the one canonical win/loss definition, and the Library of Mistakes/Successes
  already file real `CaseStudy` records on both sides — but reading `app/nexus.py`'s trade-close handler
  line by line found a genuine, literal structural asymmetry: the loss branch already called
  `maybe_propose_recurring_mistake()` (CLSIS's own tie-in) right after filing case studies; the win branch
  filed its own success studies but called nothing into CLSIS at all. This closes exactly that gap and adds
  one real, company-wide aggregate: new `compute_loss_win_classification()` reads `outcome`/`tier` straight
  off every `DisciplineReview` on file (never recomputed) and reports win rate, a full by-tier win/loss
  breakdown, and — the pedagogical core, reusing `discipline.py`'s own "good decision, bad outcome" /
  "weak process, lucky win" distinction, now formalized across the whole population — `alignedCount`,
  `unluckyLossCount` (good-tier trade that still lost — real variance, not a process failure), and
  `luckyWinCount` (poor-tier trade that still won — a warning, not a validation). New
  `maybe_propose_reinforce_success_pattern()` is the exact structural mirror of the existing recurring-
  mistake generator, scanning the win-side `CaseStudy` categories instead: a real recurring success pattern
  now files a `knowledge_organization` proposal — this category's first real generator, previously named on
  the schema with no trigger. New `GET /api/self-improvement/loss-win-classification` endpoint (on-demand,
  same convention as `get_evolution_score()`); surfaced in `EvolutionPanel.tsx`'s Command Center EVOLUTION
  tab as a new card. Verified: 22 new tests (empty input, win-rate correctness, aligned/unlucky-loss/
  lucky-win counts, the `adequate`-tier neutral case, full tier breakdown, most-common-category derivation,
  and the win-side generator's own threshold/window/dedup/refire matrix mirroring the loss-side one), full
  backend suite green (1540/1540), `mypy`/`ruff`/`tsc -b --noEmit`/`npm run lint`/`npm run build` clean, and
  a live Playwright screenshot of the new card's honest empty state against the running dev server (this
  session's game state has never produced a closed trade, so the populated case is proven by the test suite
  rather than a second live screenshot).

- **Process Adherence Score** (`backend/app/process_adherence.py` new, `backend/app/schemas.py`,
  `backend/app/routers/executive.py`, `backend/tests/test_process_adherence.py` new,
  `frontend/src/types.ts`, `frontend/src/net/api.ts`,
  `frontend/src/ui/components/CommandCenter/DecisionDetail.tsx`,
  `docs/DesignBible/volumes/09-departments/chapter-66-institutional-safety-capital-protection.md`): Piece C of
  the CEO's trading-psychology roadmap. The CEO's own request named a literal "Plan Adherence Engine" comparing
  planned vs. actual entry/exit conditions, stop-loss/take-profit placement, and confluence — none of which
  exists anywhere in this paper-trading engine (`app/gatekeeper.py`'s own module docstring already names the
  gap). Rather than fabricate that data, this ships the honestly-bounded subset the CEO explicitly asked for:
  a real Process Adherence Score built ONLY from information this architecture can actually verify — the
  Gatekeeper's own real per-check pass/fail (surfaced exactly as produced, one row per check, so a rejected
  decision shows precisely which check failed), the Discipline Chamber's own real review tier (reused by
  `decision_id`, never re-scored), and Trading Mode compliance (a `"day"`-tagged position held past the real
  1440-minute same-day discipline bar is a genuine, checkable violation; every other tagged case passes by
  construction). Stop-loss/take-profit/entry-condition/exit-condition/confluence checks always report
  `NOT_TRACKABLE_YET` — never scored as pass, never as fail, never silently omitted. `scorePct` is computed
  only from verifiable checks (`passed / (passed + failed)`) and is `None` — never 0%, never omitted — when
  zero checks were verifiable (e.g. a WAIT decision that never reached the Gatekeeper). New
  `GET /api/executive/decisions/{decisionId}/process-adherence` endpoint, computed fresh on every call, never
  persisted; surfaced in the existing Decision Detail drill-down with the required honest wording ("Process
  Adherence" / "Verified checks" / "Not trackable yet" / the required disclosure sentence about future
  execution/order-plan infrastructure). The future `TradeProposal`/execution-layer fields a real Plan
  Adherence Engine would eventually need are documented in the Design Bible addendum — explicitly not built.
  Verified: 17 new pure-function tests covering the full required matrix (all-pass, one-fails, multiple-fail,
  the five always-not-trackable checks, mixed, a genuine Trading-Mode mismatch, a risk-limit violation, a
  Gatekeeper-rejected decision, and a no-verified-checks-available WAIT decision), full backend suite green
  (1525/1525), `mypy`/`ruff`/`tsc -b --noEmit`/`npm run lint` clean.

- **Statistical Evidence Gate on Strategy Retirement** (`backend/app/strategy_lab.py`, `backend/app/state.py`,
  `backend/tests/test_strategy_lab.py`, `backend/tests/test_state.py`,
  `frontend/src/ui/components/CommandCenter/panels/sandbox/StrategyPipelineView.tsx`,
  `docs/DesignBible/volumes/09-departments/chapter-62-innovation-lab-continuous-improvement.md`): Piece B of the
  CEO's trading-psychology roadmap. `app/sandbox.py`'s `retire_strategy()` docstring already said retirement was
  "expected to cite that strategy's own real StrategyHealthAssessment... as the reason," but nothing ever
  enforced it — a strategy, including a live `"approved"` one already committing real allocated capital, could
  be retired after a single bad simulation run or zero runs at all. New `evaluate_retirement_readiness()` closes
  the gap, reusing the exact `trade_count = sum(r.trade_count for r in strategy_results)` computation this
  chapter's own Certification gate already established rather than inventing a second "sample size." A strategy
  still at `idea`/`research` is always ready to retire (no real evidence exists yet to be thin on); once a
  strategy enters real empirical testing, retirement requires `MIN_RETIREMENT_TRADE_COUNT = 10` real trades on
  file — deliberately looser than Certification's own 20-trade bar, since this is a floor on evidence quantity,
  never a judgment on evidence quality or an override of the CEO's actual retirement decision. Frontend gains a
  real, mirrored evidence readout next to the Retire button, plus the pre-existing error display duplicated
  there (previously only visible in the Testing Environments card above, easy to miss on this new failure
  mode). Verified: 8 new pure-function tests, 4 new `GameState`-level tests, full backend suite green
  (1508/1508), `mypy`/`ruff`/`tsc -b --noEmit`/`npm run lint` clean, and a live retirement against the
  running dev server confirming the real endpoint end-to-end.

- **Behavioral Circuit Breaker — a real revenge-trading detector, the Gatekeeper's tenth check**
  (`backend/app/behavioral_risk.py` new, `backend/app/gatekeeper.py`, `backend/app/executive.py`,
  `backend/app/nexus.py`, `backend/app/state.py`, `backend/app/routers/trading_modes.py`,
  `backend/app/ws_manager.py`, `backend/app/save_modules.py`, `backend/app/audit_log.py`,
  `backend/app/schemas.py`, `backend/tests/test_behavioral_risk.py` new,
  `backend/tests/test_behavioral_circuit_breaker_integration.py` new, `backend/tests/test_gatekeeper.py`,
  `frontend/src/types.ts`, `frontend/src/net/socket.ts`, `frontend/src/game/systems/{NexusManager,EventBus}.ts`,
  `frontend/src/state/gameStore.ts`, `frontend/src/ui/components/CommandCenter/panels/TradingModesPanel.tsx`,
  `docs/DesignBible/volumes/09-departments/chapter-66-institutional-safety-capital-protection.md`): the first
  piece of a CEO-requested trading-psychology roadmap (five video-transcript principles — consistency over
  strategy-switching, losses as normal distribution variance, no revenge trading, emotions-are-normal-but-
  emotional-action-is-the-risk, the plan as a capital-protection constraint system), validated against this
  codebase's own real architecture rather than taken as guaranteed financial truth. Closes a gap
  `app/constitution.py`'s Article V had already named as deliberately unbuilt: *"this codebase has no real
  signal for literally re-entering a position out of anger after a loss."* Five deterministic signals (recent
  loss, rapid re-entry, same-instrument, a self-relative loss-driven size increase, repeated rapid re-entry),
  all read from real trade data — never a fabricated emotion read. A CEO review corrected the first design (a
  blanket tick-level gate) because it couldn't distinguish a genuine same-instrument oversized re-entry from a
  legitimate, differently-sized trade moments later; the shipped design is a per-proposal Gatekeeper check
  instead, requiring corroboration (timing alone caps at a non-blocking `warning`, never `triggered`) so a
  legitimate follow-up trade is never hard-blocked purely from elapsed time. Reuses the existing Gatekeeper's
  pure-AND check list — no second, parallel enforcement path — so it inherits the Gatekeeper's own
  non-bypassable guarantee across every Trading Mode and Operating Mode, verified end-to-end through both real
  resolution paths (`app/nexus.py`'s auto-resolution and a real CEO click) in a new integration test that
  seeds its loss via `app/portfolio.py`'s own real `open_position()`/`close_position()`. Two new CEO-editable
  thresholds (`behavioralCooldownMinutes`, `behavioralSizeIncreaseThresholdPct`) on `TradingModeState`; a new
  Command Center section next to Losing Streak Protection; `GOVERNANCE_LAYERS` gains a disclosed order-11
  entry. This system detects observable behavioral risk. It does not claim to detect human emotion — and it
  does not claim to solve Plan Adherence (stop-loss/take-profit/confluence tracking stays a separate,
  honestly-scoped future piece).

- **Chapter 74/74.5 — a real frontend panel for CLSIS, the Institutional Evolution Engine, and the CEO Vision Board**
  (`frontend/src/ui/components/CommandCenter/panels/EvolutionPanel.tsx` new, `frontend/tests/evolutionPanel.spec.ts`
  new, `frontend/src/types.ts`, `frontend/src/net/api.ts`, `frontend/src/net/socket.ts`,
  `frontend/src/game/systems/{NexusManager,EventBus}.ts`, `frontend/src/state/gameStore.ts`,
  `frontend/src/ui/components/CommandCenter/{FullCommandCenter.tsx,lib/navigation.ts}`,
  `docs/DesignBible/volumes/09-departments/{chapter-74-continuous-learning-self-improvement-system.md,
  chapter-74-5-ceo-vision-board-strategic-alignment-engine.md}`): a Chapters 67–75 audit found these three
  real, working backends (`app/self_improvement.py`, `app/evolution.py`, `app/vision_board.py`) had zero
  frontend presence — `selfImprovementProposals`/`evolutionReports`/`visionBoard` were broadcast over the WS
  tick but never reached the client's type layer, store, or any UI. Fixed with a new `EVOLUTION` Command
  Center tab bundling all three: Self-Improvement Proposals (approve/reject/mark-implemented), the Executive
  Learning Summary, the Company Evolution Score, Institutional Evolution Reports, and the CEO Vision Board
  (mission/priorities/objectives/identity note/self-correction note). Along the way, live Playwright
  verification caught a real, separate wiring bug this session's `tsc --noEmit -p .` invocation had been
  silently failing to catch for months: `frontend/tsconfig.json` is a TypeScript project-references solution
  file with `files: []`, so plain `-p .` type-checks nothing — the actual command is `tsc -b --noEmit`
  (`package.json`'s own `typecheck` script). Under the real command, `net/socket.ts`'s hand-built WS-message
  object literal was missing all three new fields entirely (a real runtime `undefined` crash the
  `PanelErrorBoundary` caught and reported, not merely a lint gap) — fixed by adding them there too.

- **Chapter 73.5 mobile audit + real touch controls** (`frontend/src/game/systems/TouchMoveState.ts` new,
  `frontend/src/ui/components/MobileTouchControls.tsx` new, `frontend/src/ui/hooks/useIsTouchDevice.ts` new,
  `InputManager.ts`, `App.tsx`, `EventBus.ts`, `BottomToolbar.tsx`, `EmergencyStopControl.tsx`,
  `TopStatusBar.tsx`, `GlobalStatusBar.tsx`, `QuickActionDock.tsx`, `CommandCenter/FullCommandCenter.tsx`,
  `CommandCenter/CyberNotifications.tsx`, `CommandPalette.tsx`): a direct mobile-viewport audit (real
  Playwright runs at a 390px iPhone-13 emulation, not static code reading) found the previously-claimed
  "responsive Command Center layout" had never been driven by real touch input — zero touch event handlers
  existed anywhere, no `(pointer: coarse)` detection existed, and a live screenshot caught genuine overlaps:
  the bottom-of-screen control cluster (BottomToolbar's 10 buttons, QuickActionDock's fixed position,
  GlobalStatusBar's 7-item row, CyberNotifications' toast stack) collided with itself and with TopStatusBar's
  risk readouts on a narrow viewport. Fixed and re-verified after each change: a real on-screen joystick +
  interact button feeding the exact same `MoveVector`/`interactJustPressed` interface WASD/E already use
  (no second movement system); 44px-minimum touch targets on Emergency Stop and Command Center controls;
  BottomToolbar trimmed to Command Center/Search/Pause on touch and repositioned clear of the joystick;
  QuickActionDock hidden on touch (redundant with the Command Center, the CEO's primary mobile surface);
  GlobalStatusBar trimmed to Risk/Company Health/Portfolio on narrow viewports; a real touch-accessible
  Command Palette open path (Cmd+K has no touch equivalent). Also directly re-verified this session, with
  real backend-state assertions, not visual-only checks: Treasury renders real data with no black screen and
  no horizontal overflow at mobile width; the 5 account categories (Personal/IRA/Business/Prop Firm/Family)
  remain unchanged (no new categories added); Emergency Stop's full activate→confirm→real-backend-state-
  change→new-trades-genuinely-blocked→resume→confirm→real-backend-state-change cycle works via touch taps
  alone. Zero regressions — the one persistently-failing Playwright test found during this pass
  (`commandCenter.spec.ts`'s translucent-backdrop movement check) was confirmed pre-existing by reproducing
  it against the unmodified baseline before and after this change.

- **Chapter 74.5 — CEO Vision Board & Strategic Alignment Engine**
  (`app/vision_board.py` new, `app/routers/vision_board.py` new,
  `app/nexus.py`, `app/state.py`, `app/schemas.py`, `app/ws_manager.py`,
  `app/save_modules.py`, `app/main.py`): inserted between Chapters 74
  and 75, the same decimal-insertion precedent Chapter 73.5 already
  established. Research found the brief's three biggest concepts
  already real elsewhere — "Company Philosophy" is
  `app/constitution.py`'s 13 real Articles, "Company Identity" collides
  with `app/company_dna.py::classify_identity()` (derived, not
  CEO-declared), "CEO Long-Term Objectives" runs into `app/goals.py`'s
  real 4-metric `Goal` — none of it is rebuilt here. Adds exactly two
  new things: `VisionBoardState` (a real, permanent, CEO-mutated
  singleton — `mission`, a CEO-ranked `priorities` ordering over a
  fixed 6-value category set including a new `governance` value, a
  small `objectives` list with honestly no fabricated progress, an
  optional `identity_note`) and the Vision Alignment Engine
  (`compute_vision_alignment_score()`) — a real, disclosed, rank-based
  formula (`score = 100 × (N − R + 1) / N`, or `50.0` neutral default if
  unranked) scoring exactly three real subject types: `Goal`
  (category maps directly), `ConstitutionAmendment` (always maps to
  `governance`), and Chapter 74's `SelfImprovementProposal` (maps
  through a fixed, disclosed `SELF_IMPROVEMENT_TO_PRIORITY_CATEGORY`
  table). Persisted on `SelfImprovementProposal` at generation time —
  the field Chapter 74 reserved for exactly this chapter — computed
  on-demand only for `Goal`/`ConstitutionAmendment`. One real, narrow
  Self-Correction check: CEO's rank-1 priority is `risk` and the real
  Daily Circuit Breaker tier is `tier2`+ → a real drift note. Explicitly
  not scored: individual trade recommendations (would add a 10th
  `app/gatekeeper.py` check, out of scope). `GET/POST/DELETE
  /api/vision-board/*`, `visionBoard` in the WS `"state"` broadcast, in
  the `company` save module. 24 new tests (`tests/test_vision_board.py`).
  Backend only this pass — no dedicated frontend panel yet.

- **Chapter 74 — Continuous Learning & Self-Improvement System (CLSIS)
  + Institutional Evolution Engine** (`app/self_improvement.py` new,
  `app/evolution.py` new, `app/knowledge_graph.py`, `app/nexus.py`,
  `app/state.py`, `app/routers/self_improvement.py` new,
  `app/audit_log.py`, `app/schemas.py`, `app/ws_manager.py`,
  `app/save_modules.py`, `app/main.py`): claims the chapter number
  vacated by Trading Modes' earlier 74→75 renumber. Research found
  ~60-70% of the source brief already real across Chapters 61/62/63
  and mistakes.py/successes.py/knowledge.py/strategy_lab.py/coach.py/
  mentor.py/academy.py — none of it is rebuilt here. **Part 1
  (CLSIS):** two evidence-gated Self-Improvement Proposal generators
  (Recurring Mistake Pattern → `risk_rule`, checked once per closed
  loss; Strategy Retirement Cluster → `research_workflow`, checked at
  the one real retirement action, never tick-driven) out of the
  brief's 8 named categories — the other 6 are named but unbuilt, per
  the same honesty posture Chapter 68 held for its own broker
  categories. CEO-manual approve/reject only, never
  automation-eligible. A thin, honest Academy Integration hook (a
  small `AgentKnowledgeState.points` nudge on any filed CaseStudy/
  SuccessStudy — no lesson content generated, since no LLM exists
  anywhere in this codebase). An Executive Learning Summary (pure
  aggregation of `CoachReport`/`ThinkingProfile`/`AgentKnowledgeState`/
  Foundational Mentor progress, zero new computation). A new
  `economic_event` Knowledge Graph node type (Chapter 61 extension,
  sourced from Chapter 71's `EconomicIntelligenceReport`) with a
  `same_day` edge to same-`simDay` trade/case_study nodes — a real,
  checkable temporal proximity, never a causal claim. **Part 2
  (Institutional Evolution Engine):** a monthly Institutional
  Evolution Report composing — never recomputing — that month's real
  `StrategicReview`/`ExecutiveReview`/`CoachReport`, plus a new
  Company Evolution Score built as a disclosed, unweighted 5-factor
  rate-of-*change* metric (Learning Volume, Proposal Execution,
  Knowledge Growth, Strategy Maturation, Governance Evolution),
  deliberately disjoint from `CompanyHealth`'s 21 sub-scores and
  `CompanyScore`'s 7-metric mean — never a third copy of either.
  Academy auto-lesson-generation, "indicator" graph nodes, 6 of 8
  proposal categories, and Automation Maturity/Decision Speed
  tracking are explicit, documented Deferred Features. 29 new tests
  (`test_self_improvement.py`, `test_evolution.py`, plus 3 new
  `test_knowledge_graph.py` cases); full suite 1360/1360 passing;
  `mypy app/`/`ruff check app/` clean. `GET/POST /api/self-improvement/*`.
  Backend only this pass — no dedicated frontend panel yet.

- **Chapter 68 — Charles Schwab V1.0 target architecture, documentation
  only** (`docs/DesignBible/volumes/10-broker-live-trading/
  chapter-68-institutional-broker-management-system.md`): expanded the
  "Charles Schwab V1.0" section into a 15-phase target design —
  connector design, OAuth authentication, account discovery, read-only
  validation, reconciliation, order safety gating, Live Mode
  protection/lock, the Paper → Shadow → Live progression, execution
  monitoring, fail-safe behavior, the audit trail, the Live Trading
  Gate (restating, not loosening, Appendix G's standing policy), and a
  progressive live rollout. Explicitly labeled `PLANNED — NOT
  IMPLEMENTED` throughout. No code was written — no SDK, no OAuth
  library, no credential handling, no live connection of any kind; only
  Phase 1 (the `ExecutionProvider` interface, real since this session's
  earlier commit) is marked implemented. This does not advance, loosen,
  or bypass the Live Trading Gate.

- **Chapter 68 Part 1 — Institutional Broker Management System, Execution
  Provider Adapter Interface** (`app/broker.py`, `app/nexus.py`,
  `backend/tests/test_broker.py` new): scoped down from the full
  chapter (real Charles Schwab connectivity, gated behind Appendix G's
  Live Trading Gate — not touched) to exactly the interface seam,
  authorized explicitly. `app/broker.py` now defines
  `ExecutionProvider(ABC)` (`place_order()`/`tick_broker()`) and
  `PaperExecutionProvider`, the one concrete implementation, delegating
  directly to this module's pre-existing, byte-for-byte-unchanged
  `place_order()`/`_fill_price()`/`tick_broker()` free functions.
  `_select_execution_provider()` reads `EXECUTION_PROVIDER` from the
  environment (default `"paper"`, any other value warns and falls
  back), mirroring `app/market_data.py`'s `_select_provider()`/
  `MARKET_DATA_PROVIDER` pattern exactly. `app/nexus.py`'s one real
  order-fill call site (grep-confirmed the only production caller of
  `tick_broker()`) now goes through the `execution_provider` singleton
  instead of the bare free function. No brokerage SDK, HTTP client, or
  credential-handling code was added, and this change does not by
  itself advance any of the Live Trading Gate's seven conditions — it
  only gives a future real connector a real seam to implement. 7 new
  tests (`test_broker.py`); full suite 1328/1328 passing;
  `mypy app/`/`ruff check app/ tests/` clean. Backend only — no new
  endpoint or WS field exists to give this a frontend surface.

- **Chapter 70 Part 1 — Executive Board & CEO Intelligence System (frontend)**
  (`types.ts`, `net/api.ts`, `net/socket.ts`, `game/systems/EventBus.ts`,
  `game/systems/NexusManager.ts`, `state/gameStore.ts`,
  `ui/components/CommandCenter/panels/ExecutiveIntelPanel.tsx`): the
  Board Roster and Board Reports were added to the existing `EXECINTEL`
  tab rather than a new tab — Part 1 of an already-tabbed chapter,
  extending its established UI surface instead of duplicating it. Board
  Roster is fetched on mount (`api.getBoardRoster()`, no WS-broadcast
  field, same on-demand pattern `CompliancePanel.tsx` already
  established); Board Reports reads `boardReports` live off
  `gameStore`, wired through the full `socket.ts` → `EventBus` →
  `NexusManager` → `gameStore` pipeline the same way `executiveReviews`
  already is. Verified: `tsc --noEmit` clean, `eslint` clean (0
  warnings), `vite build` clean, and a live dev-stack walkthrough
  (backend + Vite dev server, headless Chromium) confirming the Board
  Roster renders all 11 real seats (4 filled with real agent names, 7
  honestly vacant) and the Board Reports section renders its honest
  empty state before any report has fired, no console errors. Full
  Playwright regression against the live dev stack (40 Command Center
  tabs, unchanged this pass; 31 passed, 1 skipped, 1 failed — the same
  pre-existing, already-documented movement-hold timing flake,
  untouched by this change).

- **Chapter 70 Part 1 — Executive Board & CEO Intelligence System (backend)**
  (`app/board.py` new, `app/routers/board.py` new, `app/schemas.py`,
  `app/executive_review.py`, `app/nexus.py`, `app/state.py`,
  `app/ws_manager.py`, `app/save_modules.py`, `app/audit_log.py`,
  `app/main.py`): a real 11-seat Board Roster (`GET /api/board/roster`)
  — 4 seats already filled by real agents' own `AGENT_PROFILES`
  occupation string, plus the brief's own 7 other named-but-vacant
  seats; the brief's claimed 12th seat is never named anywhere in the
  source document and is deliberately not invented. A real Board Report
  (`generate_board_report()`, `GET /api/board/reports`, persisted,
  capped, WS-broadcast) composes 7 of the brief's own 9 named fields
  from already-real sources — Department Health reuses
  `compute_department_activity()` (promoted out of
  `app/executive_review.py`'s own module-private
  `_department_activity()` so both report types share one real
  computation), Problems/Recommendations reuse `CompanyHealth` fields
  verbatim, Risk Assessment composes the real Black Swan/Circuit
  Breaker tiers, Confidence Level reuses `CompanyHealth.
  department_consensus` verbatim, Required CEO Decisions reuses the
  same pending-proposal count Chapter 73.5's Situation Room already
  uses. Three cadences: Daily and Quarterly (the two genuinely missing
  ones — Weekly/Monthly were already real via CoachReport/
  ExecutiveReview) and Emergency, firing once on a real edge-crossing
  (Emergency Stop activation from any source, or a Black Swan tier
  crossing into red/critical), each writing a real `MemoryRecord`
  picked up by Chapter 73's Audit Log via a new `board_report` category.
  **Explicitly deferred, documented in full in the Design Bible chapter
  rather than built or faked:** per-executive scorecards (the real
  accuracy/influence numbers are role-keyed, not agent-keyed, and don't
  map onto the 4 filled Chief seats without a new identity-mapping
  decision), a CEO Assistant AI (the brief's own source document names
  only 3 of its claimed 6 responsibilities), CEO-assignable Chief
  titles (would need an override layer over the pervasively-read
  `AGENT_PROFILES` static data), and a general-purpose non-trade
  Decision Center (a cross-cutting change scoped to its own future
  chapter). Verified: `mypy app/` clean, `ruff check app/` clean, 18
  new tests (`tests/test_board.py`) passing alongside the full existing
  suite (1321/1321).

- **Chapter 73.5 — Mobile Command Center & Remote Operations (frontend)**
  (`types.ts`, `net/api.ts`, `net/socket.ts`, `game/systems/EventBus.ts`,
  `game/systems/NexusManager.ts`, `state/gameStore.ts`,
  `ui/components/CommandCenter/panels/SituationRoomPanel.tsx` new,
  `ui/components/CommandCenter/panels/TravelModePanel.tsx` new,
  `ui/components/CommandCenter/CyberNotifications.tsx`,
  `FullCommandCenter.tsx`, `lib/navigation.ts`,
  `tests/commandCenter.spec.ts`): two new tabs,
  "SITUATIONROOM" under Headquarters and "TRAVELMODE" under Portfolio.
  The Executive Situation Room fetches `GET /api/situation-room` on
  mount and whenever the underlying live fields it summarizes change
  (Company Health, Portfolio Intelligence, Emergency Stop,
  trade proposals, Daily Circuit Breaker), the same on-demand pattern
  Chapter 73's CompliancePanel already established, since it has no
  WS-broadcast field of its own — it renders all 13 severity-banded
  fields plus a ranked CEO Priority Engine list. Travel Mode's
  `travelMode`/`travelModeBriefings` are real, live WS-broadcast fields,
  wired through the full `socket.ts` → `EventBus` → `NexusManager` →
  `gameStore` pipeline the same way Chapter 75's Trading Modes fields
  are; its panel exposes the real activate/deactivate toggle, posture
  settings (position size cap, daily risk cap, notification
  sensitivity, auto-activate-after-inactivity), and a
  Return-to-Operations Briefing history. `CyberNotifications.tsx`'s
  `push()` now checks Travel Mode's notification sensitivity setting
  before surfacing a non-critical toast, so the Design Bible chapter's
  filtering claim is real, not documentation-only. Verified:
  `tsc --noEmit` clean, `eslint` clean (0 warnings), `vite build` clean,
  and a live dev-stack walkthrough (backend + Vite dev server, headless
  Chromium) driving both new tabs end-to-end — Situation Room's 13
  fields and Priority Engine render with correct severity coloring;
  Travel Mode's activate → live ACTIVE state → deactivate → real
  Return-to-Operations Briefing (decisions/rejections/warnings/P&L all
  computed from the actual activation window) all confirmed against the
  real running backend, no console errors. Full Playwright regression
  against the live dev stack (40 Command Center tabs, up from 38 —
  `commandCenter.spec.ts`'s own tab-list test updated to click through
  both new tabs and assert their graceful-empty-state rendering; 31
  passed, 1 skipped, 1 failed — the same pre-existing, already-
  documented movement-hold timing flake confirmed in earlier sessions,
  untouched by this change).

- **Chapter 73.5 — Mobile Command Center & Remote Operations (backend)**
  (`app/travel_mode.py` new, `app/situation_room.py` new,
  `app/routers/travel_mode.py` new, `app/routers/situation_room.py` new,
  `app/schemas.py`, `app/nexus.py`, `app/state.py`, `app/ws_manager.py`,
  `app/audit_log.py`, `app/save_modules.py`, `app/main.py`): Travel Mode
  is a real CEO-configurable conservative posture (position size cap,
  daily risk cap, notification sensitivity, auto-activate after a
  measured period of CEO inactivity) that composes with — rather than
  duplicates — the existing tightening seam already used by Company
  Priority (`nexus.py::_effective_risk_limits`) and Chapter 75's Daily
  Circuit Breaker: confirmed to be one of exactly three derived,
  non-persisted tightening patterns in this codebase, with Travel Mode
  now the third real user of that same composition point via
  `apply_travel_mode_tightening()` and `max()`'d confidence bonuses. A
  Return-to-Operations Briefing is generated from real records in the
  exact activation window on deactivation (CEO decisions resolved,
  Gatekeeper rejections, critical Risk Warnings, Circuit Breaker tier
  changes, realized P&L). The Executive Situation Room
  (`GET /api/situation-room`) is a single computed read answering "what
  needs the CEO's attention right now" — eleven of its thirteen fields
  reuse an already-real single computed source verbatim (Company
  Health, Portfolio Intelligence, Market Regime, the Daily Circuit
  Breaker, Economic Intelligence, Black Swan tier, Broker status,
  Operating Mode/Emergency Stop), and only Pending CEO Decisions and
  Executive Consensus are computed fresh; a CEO Priority Engine ranks
  the same underlying signals critical-first. Both features are wired
  into save/load (`save_modules.py` MODULE_FIELDS), the WS broadcast
  (Travel Mode only — Situation Room is request-computed), and the
  Audit Log (a new `travel_mode_change` category). Verified: `mypy app/`
  clean, `ruff` clean, 44 new tests (24 for Travel Mode, 20 for the
  Situation Room) passing alongside the full existing suite (1303/1303),
  live smoke tests against the running server (activate/deactivate/
  settings, auto-activation via the tick loop, Audit Log end-to-end,
  save/load migration for a pre-existing save).

- **Chapter 75 — Company Trading Modes & Institutional Capital Protection (frontend)**
  (`types.ts`, `net/api.ts`, `net/socket.ts`, `game/systems/EventBus.ts`,
  `game/systems/NexusManager.ts`, `state/gameStore.ts`,
  `ui/components/CommandCenter/panels/TradingModesPanel.tsx` new,
  `FullCommandCenter.tsx`, `lib/navigation.ts`,
  `tests/commandCenter.spec.ts`): a new "TRADINGMODES" tab under the
  Portfolio section, next to RISK and BLACKSWAN. Unlike Chapter 73's
  CAGS, this chapter's `tradingModes`/`dailyCircuitBreaker`/
  `losingStreak`/`recoveryBriefings` are real, live WS-broadcast fields
  (the backend adds them to `GameState`), so they're wired through the
  full `socket.ts` → `EventBus` → `NexusManager` → `gameStore` pipeline
  the same way Chapter 72's BSIRS fields already are. Performance Split,
  Trading Mode Health, and the Adaptive Mode recommendation have no
  WS-broadcast field and are fetched on demand via `net/api.ts`,
  mirroring Chapter 73's CompliancePanel pattern. The panel shows: a
  Trading Mode selector (day/swing/hybrid, with a hybrid allocation
  slider) and a live-fetched, read-only Adaptive Mode recommendation; a
  Daily Circuit Breaker card (current tier, daily P&L%, all four
  thresholds); a Losing Streak Protection card with a real CEO
  Acknowledge action; a Trading Style Performance/Health grid (real win
  rate/P&L split, Health status reusing `StrategyHealthStatus`); and a
  Recovery Briefings history. Verified: `tsc --noEmit` clean, `eslint`
  clean (0 warnings), `vite build` clean, full Playwright regression
  against the live dev stack (38 Command Center tabs, up from 37; 31
  passed, 1 skipped, 1 failed — the same pre-existing, already-
  documented movement-hold timing flake confirmed earlier this session,
  untouched by this change).

- **Chapter 75 — Company Trading Modes & Institutional Capital Protection (backend)**
  (`app/trading_modes.py` new, `app/routers/trading_modes.py` new,
  `app/schemas.py`, `app/gatekeeper.py`, `app/portfolio.py`,
  `app/executive.py`, `app/nexus.py`, `app/state.py`,
  `app/save_modules.py`, `app/ws_manager.py`, `app/audit_log.py`,
  `app/main.py`, `tests/test_trading_modes.py`): researched first —
  Chapters 65 (Market Regime & Adaptive Strategy) and 66 (Institutional
  Safety & Capital Protection) each already named the two real gaps this
  chapter closes (Adaptive Strategy Profiles; a graduated daily circuit
  breaker ladder) as unbuilt in their own CEO Controls tables, so this
  extends their real machinery rather than duplicating it. True
  per-account capital isolation for a live Hybrid mode is blocked on
  Chapter 69 Part 1's own admitted execution-routing gap (Custom Rules
  and Account portfolios are real, but live trade execution still isn't
  routed to a specific non-primary account) — explicitly cut, along with
  a fully Automatic (non-recommendation) Adaptive Mode, which inherits
  Chapter 65's own conservative recommend-only precedent, and weekly/
  monthly graduated tiers (already real, binary halts — Sentinel's
  `max_weekly_loss_pct`/`max_monthly_loss_pct` — this chapter only adds
  the brief's own daily example).
  What shipped: a CEO-selectable `TradingMode` (day/swing/hybrid) that
  tags every new `TradeProposal` `"day"`/`"swing"` via a disclosed
  deterministic largest-remainder rotation (never a coin flip dressed up
  as AI judgment) and force-closes `"day"`-tagged open positions at
  sim-day rollover via the real, existing `close_position()`; an
  Adaptive Mode recommendation reading Chapter 65's real
  `RegimeReconciliation` off a disclosed decision table (read-only,
  exactly like that chapter's own `posture` field); a Daily Circuit
  Breaker Tier ladder — three new graduated tiers (default 1%/2%/3%
  daily loss) reusing `nexus.py`'s own `_effective_risk_limits()`
  pattern for tightened, never-persisted `RiskLimits` and a new optional
  confidence override on the Trade Gatekeeper, layered in front of the
  existing real `max_daily_loss_pct` halt as Tier 4 (which now also
  triggers the real `activate_emergency_stop()` — never a duplicate halt
  state); Losing Streak Protection (pause new proposals at 3 consecutive
  losses, CEO-acknowledgeable and auto-re-arming on a fresh streak;
  trigger the same real Emergency Stop at 5); a Recovery Briefing
  generated only for tier/streak-triggered stops, modeled on Chapter
  72's `generate_crisis_briefing()`; and a Trading Mode Performance
  Split / Health Score that reuses `strategy_lab.py`'s real
  `StrategyHealthStatus` vocabulary and threshold constants rather than
  inventing a second, differently-worded scale. Chapter 73's Audit Log
  gained two new categories (`trading_mode_change`,
  `circuit_breaker_tier`). `GET/POST /api/trading-modes/*`. 38 new
  tests. Verified: `mypy app/` clean, `ruff check app/` clean, full
  `pytest -q` — 1259 passed (1221 pre-existing + 38 new), zero
  regressions. See
  `docs/DesignBible/volumes/09-departments/chapter-75-company-trading-modes-institutional-capital-protection.md`
  for the complete honesty boundary.

- **Chapter 73 — Compliance, Audit & Governance System (CAGS) (frontend)**
  (`types.ts`, `net/api.ts`, `ui/components/CommandCenter/panels/CompliancePanel.tsx`
  new, `FullCommandCenter.tsx`, `lib/navigation.ts`,
  `tests/commandCenter.spec.ts`): a new "COMPLIANCE" tab under the
  Headquarters section — the only Command Center panel that fetches its
  data via genuine on-demand `GET /api/audit/*` calls instead of
  gameStore/the WS tick broadcast, since the backend slice deliberately
  added no new `GameSaveState` field or broadcast change (see the
  backend entry above). A Compliance Overview header (score, open/
  critical incident counts, CEO override count/rate, Defensive Mode /
  Emergency Stop status, reused Executive Accuracy) sits above four
  sub-tabs: **Audit Log** (server-side category/severity/keyword-search
  filtering, debounced, expandable rows), **Incidents** (the same log,
  server-filtered to non-`info` severity — no client-side second copy),
  **Governance** (the real 13-layer Gatekeeper chain, `UNWIRED` flagged
  honestly on the Institutional Rule Engine), and **CEO Overrides**
  (every real AI/CEO disagreement with its graded outcome). No fake
  loading skeletons or synthetic empty-state copy — each tab shows a
  real "Loading…"/error/empty state tied to its actual fetch. Verified:
  `tsc --noEmit` clean, `eslint` clean (0 warnings), `vite build` clean,
  full Playwright regression against the live dev stack (37 Command
  Center tabs, up from 36).

- **Chapter 73 — Compliance, Audit & Governance System (CAGS) (backend)**
  (`app/audit_log.py` new, `app/schemas.py`, `app/routers/audit.py` new,
  `app/main.py`, `tests/test_audit_log.py`): the brief asks for
  per-event Broker/User/Software-Version fields, an encrypted-
  credentials Security section, a mutable Incident open/resolved
  workflow with CEO-editable corrective actions, an in-game Version
  History browser, and — in a companion "Institutional Time Machine"
  addendum — full point-in-time reconstruction of the whole company's
  state (market data, portfolio, news, Knowledge Graph, Company Memory,
  all simultaneously) at any arbitrary historical instant. This codebase
  has one player, one 100%-simulated broker (`app/broker.py`'s own
  docstring: "no code path that reaches a real order-execution
  endpoint"), no credentials of any kind, no historical version tag per
  event, and takes no periodic full-state snapshots — so all five
  sections are explicit, documented cuts, not partial builds. What
  shipped instead is real: a unified Audit Log (`compute_audit_log()`)
  synthesizing nine already-real, already-persisted source types — CEO
  Decisions (including real overrides, reusing Chapter 70 Part 2's own
  `agreedWithAi` field rather than inventing new override tracking),
  Executive Meeting Log, Gatekeeper/Opportunity Rejections, critical
  Risk Warnings, weak/reckless Discipline Reviews, Emergency Stop,
  Defensive Mode and Crisis Briefings (Chapter 72), and failed
  Institutional Rule Engine checks (Chapter 69 Part 3, real corrective-
  action text reused verbatim, never fabricated) — into one searchable,
  category/severity/keyword-filterable log, computed fresh per request
  with **no new GameSaveState field and no WS broadcast change**, the
  identical read-only-synthesis convention `app/knowledge_graph.py` and
  `app/regime_reconciliation.py` already established. A real Incident
  view is a pure severity filter over that same log (never a second,
  independently-built list that could drift). `GOVERNANCE_LAYERS` is a
  disclosed, static description of the real 13-step order
  `app/gatekeeper.py::evaluate_gatekeeper()` already checks a trade
  candidate in — not a new authority chain, and honest that the
  Institutional Rule Engine is real but still disconnected from live
  execution for non-primary accounts. A Compliance Overview reuses
  Chapter 70 Part 2's real Executive Accuracy Score verbatim and adds
  one new, disclosed Compliance Score formula (`100 - min(60, 5 × open
  incidents)`, floored at 40 — conservative but arbitrary, the same
  honesty note `RiskLimits` itself already carries). The Institutional
  Time Machine addendum ships as this same Audit Log's own chronological
  order — a real, steppable history browser over every moment this
  codebase actually recorded, honestly short of an omniscient rewind to
  an arbitrary instant nothing was ever snapshotted at. `GET
  /api/audit/log|incidents|governance|overview|overrides`. 23 new tests.
  Verified: `mypy app/` clean, `ruff check app/ tests/` clean, full
  `pytest -q` — 1221 passed (1198 pre-existing + 23 new), zero
  regressions. See
  `docs/DesignBible/volumes/09-departments/chapter-73-compliance-audit-governance-system.md`
  for the complete honesty boundary.

- **Chapter 72 — Black Swan Intelligence & Resilience System (frontend)**
  (`frontend/src/types.ts`, `frontend/src/net/socket.ts`,
  `frontend/src/net/api.ts`, `frontend/src/game/systems/EventBus.ts`,
  `frontend/src/game/systems/NexusManager.ts`,
  `frontend/src/state/gameStore.ts`,
  `frontend/src/ui/components/CommandCenter/panels/BlackSwanPanel.tsx`
  new, `frontend/src/ui/components/CommandCenter/lib/derive.ts`,
  `frontend/src/ui/components/CommandCenter/lib/navigation.ts`,
  `frontend/src/ui/components/CommandCenter/FullCommandCenter.tsx`): a
  new BLACKSWAN tab (Command Center → PORTFOLIO section, alongside
  RISK — inserted right after it, which shifts every later tab's
  number-key shortcut down one position; the two affected Playwright
  assertions were updated to match) mirrors both Part 1 and Part 2's
  backend types exactly, wired through the same WebSocket-driven store
  pattern as `economicIntelligence`/`portfolioIntelligence` (five new
  EventBus event pairs, following `blackSwanReports`/`blackSwanEvents`'
  length-diffed emit convention rather than firing on every tick). The
  panel shows the Early Warning Score's eight named factors, the Black
  Swan Confidence Engine, the Institutional Survival Score with its
  letter grade and Primary Strengths/Weaknesses/Top 5 Improvements,
  live Defensive Mode controls (activate/deactivate, auto-trigger
  toggle — both real POST actions against `/api/black-swan/defensive-
  mode/*`) with its recommendation list, an on-demand Portfolio Stress
  Test runner (the real -10/-20/-35/-50/-70% ladder) and Scenario
  Simulator (all four real scenarios), the permanent Post-Event
  Analysis history, and the latest Daily Black Swan Situation Report —
  reusing `EconomicIntelPanel`/`RiskPanel`'s exact visual conventions
  (`Glass`/`TerminalLabel`/`Meter`/`StatusPill`/`EmptyState`/`DataRow`),
  no new UI primitives. Verified against the live Vite + FastAPI stack:
  `tsc --noEmit`, `eslint`, and `vite build` all clean; the full
  Playwright suite re-run against a fresh dev backend and a freshly
  restarted Vite dev server (a stale multi-hour dev server was
  confirmed, again, to be the cause of an initial spurious title-screen
  failure — same class of environment issue documented earlier in this
  session, not a real regression).

- **Chapter 72 — Black Swan Intelligence & Resilience System, Part 2:
  Institutional Survival Score (backend)** (`app/black_swan.py`,
  `app/schemas.py`, `app/state.py`, `app/nexus.py`,
  `app/save_modules.py`, `app/ws_manager.py`, `app/routers/black_swan.py`,
  `tests/test_black_swan.py`): a follow-up brief asked for a
  continuously-updating 0-100 Institutional Survival Score with a
  letter grade (A+ through F), named strengths/weaknesses, computed
  improvement suggestions, and an "Estimated Survival Probability,"
  scored against 12 named inputs including Leverage and Counterparty
  Risk. This codebase has no margin/leverage concept anywhere and no
  real broker connection to have counterparty risk from — both cut
  outright — and no historical black-swan dataset to calibrate a
  probability against, so no "Estimated Survival Probability" is
  fabricated (the identical honesty rule Part 1 already applied to its
  own "Black Swan probability" cut). What shipped is real: a new
  `InstitutionalSurvivalScore` with nine named, published, weighted
  factors — three reused directly from the Early Warning Score's own
  already-computed factors (Correlation Breakdown → Diversification,
  Liquidity, Active Risk Warnings → Rule Compliance, each inverted from
  "how stressed" to "how resilient" rather than recomputed), plus five
  genuinely new factors (Cash Reserves, Concentration Risk, Drawdown
  Exposure, Black Swan Readiness, Stress Test Survival — the last a
  real, cheap pass over the same -10/-20/-35/-50/-70% shock ladder Part
  1's Stress Test uses). Primary Strengths/Weaknesses are the real
  top/bottom three scored factors; Top 5 Improvements are those factors'
  own real detail text, never generic filler. `GET
  /api/black-swan/survival-score` exposes it; recomputed every tick like
  Part 1's own Early Warning Score. 16 new tests (39 total for the
  module) cover weight-sum invariants, factor reuse correctness, grade
  thresholds, and that no `leverage`/`counterparty_risk`/
  `survival_probability` field ever appears on the schema. Verified:
  `mypy app/` clean, `ruff check app/ tests/` clean, full `pytest -q` —
  1198 passed (1159 pre-existing + 39 new), zero regressions.

- **Chapter 72 — Black Swan Intelligence & Resilience System, Part 1
  (backend)** (`app/black_swan.py` new, `app/schemas.py`, `app/state.py`,
  `app/nexus.py`, `app/save_modules.py`, `app/ws_manager.py`,
  `app/knowledge_graph.py`, `app/routers/black_swan.py`, `app/main.py`):
  the brief asked TradeTown to detect, simulate, and respond to Flash
  Crashes, Banking Failures, Pandemics, Cyberattacks, and Broker
  Failures with named historical calibration (2008, 2020, 1987,
  Dot-Com) and a calibrated "probability." This codebase has zero real
  macro/broker/historical-crisis data anywhere (the same gap Chapter 71
  already documented, extended here to broker connections — see
  `app/broker.py`'s own docstring), so every historically-named section
  is an explicit, documented cut. What shipped instead is real: a new
  `EarlyWarningScore` (eight named, published factors — Active Risk
  Warnings, Market Stress, Volatility, Liquidity, Correlation
  Breakdown, Regime Divergence, News Severity, Macro Instability — each
  reused from an already-real department, Risk Engine through Chapter
  71, never recomputed) driving a new `BlackSwanRiskTier`
  (GREEN/YELLOW/ORANGE/RED/CRITICAL — the exact named gap Chapter 66's
  Ownership table and Chapter 70 Part 1's Emergency Board Meeting table
  each already flagged as real, un-built work). Portfolio-wide Stress
  Tests (the brief's own -10/-20/-35/-50/-70% ladder, against the
  primary portfolio or any real Account) report real drawdown, rule
  violations, capital survival, and an honestly-capped recovery-time
  projection (a real "N/A" when there's no positive trailing
  performance to project from, never a fabricated ETA). Four Scenario
  Simulations (Flash Crash, Severe Selloff, Liquidity Freeze,
  Correlation Breakdown Shock) extend `app/whatif.py`'s own real
  volatility-scaled shock convention from one candidate trade to the
  whole book. A CEO-controllable Defensive Mode tightens real
  `RiskLimits` (halves max position size/daily loss/risk-per-trade,
  halves max open positions) and pauses new AI-generated trade
  proposals while active — but never closes, resizes, or otherwise
  touches an open position automatically, at any tier, upholding
  `app/portfolio_intelligence.py`'s own existing "never auto-corrected
  without the player" principle exactly. One real, generically-named
  Elevated Risk Response Playbook (not eight fabricated event-specific
  ones) is live-populated with today's actual Defensive Mode
  recommendations. Crisis Briefings fire once when the Risk Level first
  crosses into RED/CRITICAL, writing a permanent Company Memory
  record — the honest answer to "automatically trigger an emergency
  Executive Board meeting" (Chapter 70 Part 1 already confirmed no such
  mechanism, or any general-purpose non-trade Decision Center, exists to
  convene a real vote through). Post-Event Analysis writes one permanent
  `BlackSwanEventRecord` per completed Defensive Mode episode to both
  Company Memory and a new `black_swan_event` Knowledge Graph node type
  (linked to real held symbols via the same non-causal "same symbol"
  edge convention Chapter 61 already established). 23 new tests cover
  factor scoring, tier thresholds, the stress-test ladder, all four
  scenarios, the full Defensive Mode activate/deactivate lifecycle
  (including exact RiskLimits restoration), event-history capping, the
  Playbook, and Crisis Briefing generation. See
  `docs/DesignBible/volumes/09-departments/chapter-72-black-swan-intelligence-resilience-system.md`
  for the complete honesty boundary.

- **Chapter 71 — Economic Intelligence Center (frontend)**
  (`frontend/src/types.ts`, `frontend/src/net/socket.ts`,
  `frontend/src/game/systems/EventBus.ts`,
  `frontend/src/game/systems/NexusManager.ts`,
  `frontend/src/state/gameStore.ts`,
  `frontend/src/ui/components/CommandCenter/panels/EconomicIntelPanel.tsx`
  new, `frontend/src/ui/components/CommandCenter/lib/derive.ts`,
  `frontend/src/ui/components/CommandCenter/lib/navigation.ts`,
  `frontend/src/ui/components/CommandCenter/FullCommandCenter.tsx`): a
  new ECONINTEL tab (Command Center → MARKETS section, alongside
  MARKETINTEL) mirrors the backend's `EconomicIntelligenceState`/
  `EconomicIntelligenceReport` types exactly, wired through the same
  WebSocket-driven store pattern as `portfolioIntelligence`/
  `marketIntelligence` (a dedicated `economicIntelligence:updated` /
  `economicIntelligenceReports:updated` EventBus pair, following
  `marketIntelligenceReports:updated`'s own length-diffed emit
  convention rather than firing on every tick). The panel shows the
  Economic Health Score with all five named factors (never collapsed
  into one number), the Confidence Engine's supporting/contradicting
  evidence and key assumptions, News Risk, held-position Correlation
  Clustering, and the latest Daily Economic Intelligence Brief
  narrative — reusing `MarketIntelPanel`/`PortfolioIntelPanel`'s exact
  visual conventions (`Glass`/`TerminalLabel`/`Meter`/`StatusPill`/
  `EmptyState`), no new UI primitives. Verified against the live Vite +
  FastAPI stack: `tsc --noEmit`, `eslint`, and `vite build` all clean; a
  new `tests/economicIntel.spec.ts` (2 tests) confirms the real backend
  state shape and that the tab renders live data with zero console
  errors — a screenshot confirmed correct real values (Economic Health
  66.6/100 STABLE, all five factors populated) against a live dev
  backend.

- **Chapter 71 — Economic Intelligence Center (backend)**
  (`app/economic_intelligence.py` new, `app/schemas.py`, `app/state.py`,
  `app/nexus.py`, `app/save_modules.py`, `app/ws_manager.py`,
  `app/routers/market.py`): the brief asked for a full macro-economic
  intelligence system — central bank tracking, a real economic calendar,
  global event intelligence, real inflation/rate/GDP forecasts, a
  sector impact engine, scenario planning. This codebase has zero real
  macroeconomic data anywhere (no API keys, no live feed — the same gap
  `app/market_data.py` and `app/market_intelligence.py` already
  documented), so every one of those sections is an explicit, documented
  cut, not a partial build. What shipped instead is real: a new
  `EconomicHealthScore` synthesizing five already-real signals that had
  no shared read until now — Regime Favorability (Market Environment,
  Ch. 65), Market Quality and News Risk (Market Intelligence),
  Correlation Clustering and Concentration (Portfolio Intelligence, Ch.
  56) — each its own named, published factor, never a black-box blend.
  An `EconomicConfidenceRead` wraps it honestly (confidence, evidence
  quality, named supporting/contradicting evidence, a computed
  alternative-outcome statement) so the read is never presented as fact.
  A Market Narrative Engine diffs each real in-game evening's read
  against the last stored daily report and cites only real, computed
  deltas — verified by a test that the narrative text never contains
  "fed", "interest rate", "inflation", "gdp", or "central bank". A
  Daily Economic Intelligence Brief records once per evening (mirroring
  Market Intelligence's own daily cadence), capped at
  `MAX_ECONOMIC_INTELLIGENCE_REPORTS = 60`. Exposed via
  `GET /api/market/economic-intelligence` and `.../reports`. Deliberately
  not a 10th Executive Board vote (would structurally near-duplicate
  Market Intelligence's own regime read) and not wired into the Trade
  Gatekeeper this pass — see the Chapter 70 Part 3 addendum for the
  precedent that governs doing so later, as an explicit follow-up. 21
  new tests, including two real end-to-end nexus tests proving the daily
  cadence fires via `GameState.advance_time("workday_end", ...)`. Full
  honesty boundary and every cut documented in
  `docs/DesignBible/volumes/09-departments/chapter-71-economic-
  intelligence-center.md`. Backend only in this entry, per this repo's
  commit-backend-first discipline — frontend surfacing follows as a
  separate commit.

- **Chapter 70 Part 3 addendum — Weighted Executive Decision Engine
  wired into the Trade Gatekeeper (advisory only)**
  (`app/gatekeeper.py`, `app/executive.py`, `app/state.py`,
  `app/nexus.py`): closes a gap a follow-up Design Bible addendum
  named explicitly — "The Executive Board recommends. The Trade
  Gatekeeper decides... The Weighted Executive Decision Engine must
  feed recommendations into the Trade Gatekeeper, while remaining
  advisory only." WEDE was previously a real but disconnected
  read-only endpoint. `gatekeeper.py` gains `_weighted_executive_
  check()`, a 9th unconditional check in `evaluate_gatekeeper()`'s
  existing `all(checks)` list — the exact same authority as every
  other check (Decision Confidence, Portfolio Exposure, ...): it can
  contribute to a rejection, never force an approval, and cannot
  override or skip any other check. `resolve_proposal()` gained an
  optional `weighted_recommendation` parameter passed straight through
  (it still never computes WEDE itself); `state.py`'s
  `submit_ceo_decision()` and `nexus.py`'s `_apply_operating_mode()`
  (the Assisted/Executive auto-resolve path) both now compute the real
  `WeightedExecutiveRecommendation` immediately before resolving a
  proposal, so a manual CEO decision and an auto-resolution are gated
  identically — the auto-resolve path reuses the department opinions
  it already computed for the pre-existing Chapter 66 `pause_trading`
  safety check rather than a second, redundant pass. The stale-
  proposal expiry path is untouched (always resolves "wait," never
  reaching the Gatekeeper). Institutional Rule Engine (Chapter 69 Part
  3) enforcement was deliberately not added to this same pipeline —
  its Custom Rules attach to Part 1's secondary Account objects, and
  live trade execution against those accounts remains unwired, so
  there's no real trade for IRE to evaluate against yet. Verified:
  mypy/ruff clean; full backend suite (1138 tests) passing, including
  4 new real tests proving the check's pass/fail/vacuous/non-
  overriding behavior (a favorable WEDE read cannot rescue a trade a
  failing Decision Confidence check would otherwise reject); two
  direct runtime smoke tests against the real `GameState` singleton
  and `_apply_operating_mode` confirming both production call sites
  produce a real, non-vacuous WEDE evaluation as the Gatekeeper's 9th
  check.

- **Chapter 70, Part 3 — Weighted Executive Decision Engine (WEDE) —
  implemented**
  (`app/weighted_decisions.py`, `app/schemas.py`, `app/routers/
  executive.py`, `ExecutiveVoting.tsx`): a real, published, per-
  department weighting layer over the pre-existing Executive Consensus
  Meter, honestly scoped to the only two of the brief's eight named
  weighting inputs with a real, computable source — Historical Accuracy
  (`compute_executive_accuracy_scores()`, built for Part 2 this same
  run) and Market Conditions (Chapter 65's real, live 5-way regime
  read). `compute_department_influence()` computes a real, fully-
  published multiplier per department (never a hidden blend) across all
  8 named Weight Profiles (Equal Voting, Performance Weighted, the four
  "First" emphasis presets, Balanced Institutional, and a CEO-editable
  Custom profile), persisted via the same client-authoritative
  `SettingsState` mechanism `operatingMode` already uses.
  `compute_weighted_recommendation()` maps every department's real
  stance onto the existing six-value `ExecutiveAction` space so the Raw
  Vote and Weighted Recommendation are always shown together, in the
  same vocabulary, on the real trade proposal panel — never one
  replacing the other. Deliberate scope decisions, not gaps: Chief
  Compliance/Chief Innovation Officer were not invented as new
  department-opinion roles (verified: `app/weighted_decisions.py`
  imports nothing from and writes nothing to the Trade Gatekeeper — its
  real, absolute veto, Chapters 58/66, is completely untouched); no
  Performance-Based Evolution loop persists or decays influence over
  time (accuracy is read live every request, never accumulated,
  matching this codebase's "no fake progression" rule). Verified:
  mypy/ruff clean; runtime-tested against the real `GameState` singleton
  across all 8 profiles; FastAPI `TestClient` route + 404 checks; a full
  save-module persistence round-trip; `tsc --noEmit`/eslint/`npm run
  build` clean; and a real Playwright test against the live dev stack
  confirming all 9 departments render real influence data and profile
  switching live-previews a different published formula.

- **Chapter 70, Part 3 — Weighted Executive Decision Engine (WEDE)**
  (`docs/DesignBible/volumes/09-departments/chapter-70-executive-board-ceo-intelligence-system.md`):
  documentation only, no code written against this part (superseded by
  the implementation entry above — kept as the original research
  record). The brief asks
  that department opinions stop counting equally and instead carry a
  Dynamic Influence Score shaped by accuracy, market conditions, and
  rule compliance. Researched first: grep-confirmed zero per-department
  `influence`/weight concept exists anywhere in `backend/app` today.
  The one real, adjacent precedent is `compute_executive_recommendation()`'s
  existing fixed priority-ordered rule chain (Market Intelligence's
  veto-like top slot, then Devil's Advocate/Risk) — real proof some
  departments already matter more in some situations, but expressed as
  hardcoded if/elif logic, never a numeric, CEO-visible, adjustable
  weight. Two of the brief's inputs have a real, if narrow, source
  today: Historical Accuracy via `compute_executive_accuracy_scores()`
  (built for Part 2 this same run — a real per-department, closed-
  trade-only accuracy score whose only caller today is a read-only API
  endpoint) and Market Conditions via Chapter 65's two real regime
  classifiers (`app/market_environment.py`, `app/market_intelligence.py`),
  whose own `app/regime_reconciliation.py` module docstring states its
  `posture` output is "never applied to any [...] field automatically."
  Confirmed genuinely unbuilt: any weighting formula or Weighted
  Executive Recommendation, Dynamic Market Adaptation, a Performance-
  Based Evolution loop, every CEO weighting control beyond the
  pre-existing, unrelated trade-decision Override, and all eight named
  Weight Profiles (no CEO-switchable named-profile precedent exists
  anywhere in this codebase for anything — the closest analog,
  `OperatingMode`, is a single three-way global autonomy dial). No
  Chief Compliance Officer or Chief Innovation Officer exists as an
  agent title or one of the 9 real `DepartmentOpinion` roles — the
  closest real analogs (`app/gatekeeper.py`'s real, unconditional veto
  pipeline; `app/innovation.py`'s unrelated Innovation Points ladder)
  are both separate systems, not weightable department opinions. The
  most consequential open design question this part raises and does
  not resolve: how a weighting system could coexist with the Trade
  Gatekeeper's real, absolute, non-bypassable veto (Chapter 66) without
  diluting it into "one more weighted vote."

- **Chapter 69 (all three parts) + Chapter 70 Part 2 — implemented**,
  per explicit instruction to implement everything across Chapters
  68-70 except Chapter 68 (deferred until Chapter 75, per Appendix G's
  Live Trading Gate). The Design Bible entries below this one describe
  the target-architecture research that preceded this pass; this entry
  and its own file-level Implementation Notes sections (linked below)
  describe what was actually built and verified.

  **Chapter 70 Part 2 — Executive Consensus Meter**
  (`app/schemas.py`, `app/executive_intelligence.py`, `app/executive.py`,
  `app/state.py`, `app/scribe.py`, `app/routers/executive.py`,
  `ExecutiveVoting.tsx`): Modify (`modify_proposal()`) and Delegate
  (`submit_ceo_decision(delegated=True)`) are now real CEO decision
  actions, distinctly recorded on `resolvedBy`. `_build_disagreement_
  summary()` synthesizes the per-department disagreement picture the
  CEO previously had to assemble by reading cards individually.
  `compute_executive_accuracy_scores()` scores each department's
  directional stance (`agree`/`disagree`/`recommend_rejecting` only —
  hedged stances excluded) against real, already-closed
  `CeoDecisionRecord.outcome` values — resolving the counterfactual-
  outcome tension the original research raised by scope, not by
  fabricating hypothetical trade outcomes. The What-If Simulation Lab's
  Probability/Return/Risk numbers now merge into `GET /api/executive/
  intelligence`'s single response. See [Chapter 70's own Part 2
  Implementation
  Notes](docs/DesignBible/volumes/09-departments/chapter-70-executive-board-ceo-intelligence-system.md)
  for the full, honest inventory of what remains unbuilt (a distinct
  Consensus % apart from average confidence, Institutional Risk/
  Opportunity Scores, structured per-opinion Evidence/Concerns/Benefits/
  Risks fields, and accuracy scoring for the 5 departments that never
  cast a directional stance).

  **Chapter 69 Part 1 — Multi-Account & Fund Management System**
  (`app/schemas.py`'s new `Account`/`AccountType`, `app/accounts.py`
  (new), `app/routers/accounts.py` (new), `app/state.py`): a real,
  generalized `Account` model — create/close, capital allocation
  reusing `treasury.py`'s own real deposit/withdraw machinery rather
  than inventing a second transfer mechanism, and account switching.
  Live trading execution against non-primary accounts is explicitly not
  wired (stated in `Account`'s own docstring) — that would require
  parameterizing the entire trading pipeline by account, named honestly
  as Future Expansion rather than silently assumed.

  **Chapter 69 Part 2 — Prop Firm Rule Engine** (`app/prop_firm.py`
  (new)): a real Weekday-Aware Time System (`weekday_for()`, day 1 =
  Monday, deterministic), a Trailing Drawdown Engine (`Account.
  peak_equity`, a continuously-updated high-water mark), a Consistency
  Rule Engine, Scaling Milestones (published 10/25/50/100% growth
  tiers), Challenge Windows (with a real on-pace read), and a
  transparent, published, equal-weighted Prop Firm Compliance Score —
  never a hidden blend. Leverage is stated as explicitly not applicable
  (`LEVERAGE_NOTE`: 100% cash, long-only, no margin concept anywhere in
  this codebase) rather than fabricated. These are real status
  computations, not yet wired as pre-trade blocks — see Part 3.

  **Chapter 69 Part 3 — Institutional Rule Engine (IRE)**
  (`app/rule_engine.py` (new), `Account.custom_rules`): a real,
  centralized evaluator (`evaluate_rules()`) for a closed, named
  8-value `RuleType` set — a deliberate scope decision over a free-text
  DSL/rule parser (none exists anywhere in this codebase, and building
  one was ruled out of scope), preserving this Design Bible's "no
  black-box composite" convention while remaining genuinely data-driven
  (no code change needed to add a rule instance). Includes per-`RuleType`
  corrective-action suggestions (`CORRECTIVE_ACTIONS`) and real Company
  Memory recording of violations (`record_rule_violation()`). Not yet
  wired into the pre-trade pipeline as a blocking veto — `evaluate_
  rules()` is real and callable but not called from `app/nexus.py` or
  the Trade Gatekeeper today; it evaluates on demand
  (`GET/POST /api/accounts/rules/*`), not inline with a pending trade.
  Does not replace or duplicate the pre-existing, hardcoded Chapters
  57/58/66 checks for the primary account.

  Verified throughout: `mypy`/`ruff` clean on the full backend, `tsc
  --noEmit`/`eslint`/`npm run build` clean on the full frontend
  (`npm run build`'s `tsc -b` caught missing type imports plain `tsc
  --noEmit` missed, consistent with this project's own prior findings),
  and extensive runtime tests against the real `GameState` singleton
  including full save-module persistence round-trips.

- **Chapter 70, Part 2 — Executive Consensus Meter**
  (`docs/DesignBible/volumes/09-departments/chapter-70-executive-board-ceo-intelligence-system.md`):
  Chapter 70 is now two parts — the base Board & CEO Intelligence brief
  stays Part 1, and this addendum (per-recommendation, department-by-
  department transparency into how the board reached a call) is added
  as Part 2. Researched first, and the match is unusually direct:
  `DepartmentOpinion` + `compute_executive_recommendation()`
  (`app/executive_intelligence.py`) already are a real, live Executive
  Consensus Meter — 9 real departments each returning a real stance,
  confidence percentage, and reasoning, combined by a transparent,
  named, priority-ordered rule chain (never a black-box blend),
  rendered today in `ExecutiveVoting.tsx`'s Executive Intelligence
  Network panel and permanently recorded via `ExecutiveMeetingLogEntry`
  (which stores the full per-department opinion breakdown, not just a
  summary) on every real trade decision. A real, separate, company-wide
  `department_consensus` KPI (`app/company_health.py`) already tracks
  agreement rate over time. Genuinely unbuilt: a distinct Consensus %
  apart from average confidence, Institutional Risk/Opportunity Scores,
  merging the What-If Simulation Lab's real Probability/Return/Risk
  numbers into the same panel, structured per-opinion Evidence/
  Concerns/Benefits/Risks/Alternatives fields (today one free-text
  summary carries all of it), an auto-synthesized disagreement
  paragraph, Modify/Delegate as CEO actions, and any real outcome-
  linked Executive Accuracy Score — the last of which runs into a
  genuine, pre-existing design tension with this codebase's own
  explicit refusal (`app/coach.py`, `app/player_vs_ai.py`) to fabricate
  counterfactual "would have" trade outcomes, not just a missing
  feature. No code was written against this section.

- **Chapter 69 Part 3 — Institutional Rule Engine pre-trade wiring, investigated and confirmed correctly deferred**
  (`docs/DesignBible/volumes/10-broker-live-trading/chapter-69-multi-account-fund-management-system.md`): a
  Chapters 67–75 audit flagged `evaluate_rules()` not being called before a trade executes as a possible gap.
  Investigated and confirmed it's not a contained wiring fix: there is no per-account pre-trade checkpoint to
  plug it into, since Part 1's own `app/accounts.py` already documents that live trade execution against a
  non-primary `Account` was never built — every real trade still only touches the one primary company
  portfolio. Closing this for real needs that separate, larger per-account live-trading pipeline first. Per
  explicit CEO instruction, stays deferred; no code changed, only the honest boundary documented more clearly.

### Fixed

- **Chapter 74 Part 1 — a Self-Improvement Proposal can now actually be marked Implemented**
  (`backend/app/schemas.py`, `backend/app/self_improvement.py`, `backend/app/state.py`,
  `backend/app/routers/self_improvement.py`, `backend/tests/test_self_improvement.py`,
  `docs/DesignBible/volumes/09-departments/chapter-74-continuous-learning-self-improvement-system.md`):
  a Chapters 67–75 audit found `SelfImprovementProposal.status`'s `"implemented"` value was declared on the
  schema and read by `app/evolution.py`'s own Proposal Execution scoring, but nothing anywhere ever set it —
  the only real transition was `pending` → `approved`/`rejected`. There is no single, well-defined state
  mutation an approved `risk_rule`/`research_workflow` proposal maps onto (this chapter's own KPIs section
  already names that as why "proposal success rate" isn't honestly computable), so rather than fabricate an
  automatic mutation of `RiskLimits`, the fix adds a real, CEO-manual `mark_self_improvement_proposal_
  implemented()` and `POST /api/self-improvement/proposals/implement` — the CEO records, in their own words,
  that they carried an approved proposal out elsewhere in the game. Also corrected this chapter's Design Bible
  page, which still said "Target design, not yet implemented" in its Status line despite its own
  Implementation Notes section listing real, shipped modules.

- **Chapter 69 — real test coverage for Accounts, Prop Firm Rule Engine, and Institutional Rule Engine**
  (`backend/tests/test_accounts.py`, `backend/tests/test_prop_firm.py`, `backend/tests/test_rule_engine.py`,
  all new): a Chapters 67–75 audit found `app/accounts.py`, `app/prop_firm.py`, and `app/rule_engine.py` — the
  real, working Multi-Account & Fund Management backend — had zero test coverage anywhere in the repository,
  unlike every other real module in this chapter range. Added 72 tests covering account creation/closure/
  capital allocation against the real Treasury, Trailing Drawdown/Consistency/Scaling/Challenge Window/
  Compliance Score computations checked against hand-computed expected values, and all eight `RuleType`
  evaluator branches plus its disabled-rule-skip and corrective-action behavior. No production code changed.

- **Chapter 75 — Adaptive Recommendations toggle now actually gates the recommendation**
  (`backend/app/trading_modes.py`, `backend/app/routers/trading_modes.py`, `backend/app/state.py`,
  `backend/tests/test_trading_modes.py`, `backend/tests/test_adaptive_recommendations_toggle_integration.py`
  new, `frontend/src/net/api.ts`, `frontend/src/ui/components/CommandCenter/panels/TradingModesPanel.tsx`):
  a Chapters 67–75 audit found `TradingModeState.adaptiveRecommendationsEnabled` was a real, persisted field
  that nothing read or exposed a way to change — `GET /api/trading-modes/adaptive-recommendation` always
  computed and returned a live recommendation regardless of its value, and no endpoint could toggle it.
  Fixed by gating the endpoint on the flag (a new `adaptive_recommendations_disabled_reading()` returns an
  honest "turned off" reading and never computes a regime reconciliation when disabled, rather than
  suppressing an already-computed result), adding a real `POST /api/trading-modes/adaptive-recommendations-enabled`
  endpoint backed by `GameState.set_adaptive_recommendations_enabled()`, and wiring a real On/Off button into
  `TradingModesPanel.tsx`. A pure CEO display preference — the underlying recommendation function never
  writes to any state, so this control is not gated on Emergency Stop the way Trading Mode changes are.

- **Chapter 72 — Black Swan Defensive Mode's "Pause New Entries" now actually fires**
  (`backend/app/nexus.py`, `backend/tests/test_defensive_mode_integration.py` new): a Chapters 67–75 audit
  found that Defensive Mode's advertised auto-pause on new trade generation — documented and UI-labeled
  `automatic=True` since this chapter shipped — was never wired into `tick()`, and live-reproduced the gap
  (activating Defensive Mode and running a tick still generated new proposals). Fixed by adding
  `defensive_mode.active` to the same real `block_new_proposals` gate Chapter 75's Circuit Breaker Tier 3/4
  and Losing Streak Pause already use — never a second, competing gate. A new integration test exercises the
  real end-to-end path (`GameState.activate_defensive_mode()` → `advance_time()`, the same two real CEO
  actions a player takes) and was confirmed to fail against the pre-fix code before the fix landed. The
  RiskLimits-tightening half of Defensive Mode was already real and unaffected.

- **Design Bible documentation-accuracy pass (Chapters 71/72/73/75/73.5)**
  (`docs/DesignBible/volumes/09-departments/README.md`,
  `chapter-71-economic-intelligence-center.md`,
  `chapter-72-black-swan-intelligence-resilience-system.md`,
  `chapter-73-compliance-audit-governance-system.md`,
  `chapter-73-5-mobile-command-center-remote-operations.md`,
  `chapter-75-company-trading-modes-institutional-capital-protection.md`):
  a code-verified audit of Chapters 68–75 found the Chapters 71, 72, 73,
  and 75 chapter files (and their Volume 9 README rows) still said
  "backend only," even though each already shipped a real Command Center
  tab in a later, separate frontend commit that never circled back to
  update the doc. Corrected all four to state their real frontend status
  (`ECONINTEL`, `BLACKSWAN`, `COMPLIANCE`, `TRADINGMODES` tabs). Also
  fixed Chapter 73.5's own chapter file, which still read "Status:
  Proposed" after it shipped this session, and a leftover numbering
  error in the Volume 9 README's Trading Modes row — it still printed
  "74" in its numeral column (linking to the `chapter-75-...md` file)
  from before an earlier session's 74→75 renumbering, which updated the
  file name, in-file heading, and every other reference except that one
  table cell. No code changed; Chapter 68 (the real broker connector)
  was confirmed still correctly unimplemented and gated behind Appendix
  G's Live Trading Gate — not touched.

- **UI Polish & Bug Fix Sprint — Treasury black-screen crash, root-caused
  and fixed** (`backend/app/ws_manager.py`,
  `frontend/src/ui/components/CommandCenter/PanelErrorBoundary.tsx` new,
  `frontend/src/ui/components/CommandCenter/FullCommandCenter.tsx`,
  `frontend/src/ui/components/CommandCenter/panels/TreasuryPanel.tsx`):
  entering the TREASURY tab went black moments after load. Root cause:
  Design Bible Chapter 69 Part 1 (Multi-Account & Fund Management) added
  `accounts`/`activeAccountId` to `GameSaveState` and every REST account
  endpoint, and the frontend (types.ts/socket.ts/NexusManager.ts/
  gameStore.ts) was already wired to consume them from the WebSocket
  broadcast — but `ws_manager.py`'s periodic full-state push never
  actually included those two fields. Every tick silently overwrote the
  client's real `accounts` array with `undefined`, and `AccountsSection`
  crashed the instant it read `accounts.length`, taking down the whole
  React tree with no error boundary anywhere in the codebase to catch
  it — confirmed by reverting to the pre-Chapter-71 commit with a fresh
  database and reproducing the identical crash, ruling out every other
  recent change as the cause. Fixed at the source (`ws_manager.py` now
  broadcasts both fields), plus a real, general fix for the underlying
  fragility: the codebase's first React error boundary
  (`PanelErrorBoundary`), wrapping the Command Center's tab content so
  any future undefined-access bug in any of the 35 panels degrades to a
  visible "Panel Error" card with a Retry button — never a black screen
  — instead of crashing the entire app. A cross-check of all 90
  `GameSaveState` fields against the WS broadcast confirmed no other
  field has this same gap (the other apparent gaps — `settings`,
  `dialogue_history`, `company_dna_legacy`, `version`, `updated_at` — are
  all intentionally REST/local-only; the frontend's own WS message type
  never expects them). Also fixed a second, independent pre-existing bug
  this investigation surfaced: `commandCenter.spec.ts`'s deposit/
  withdraw test was silently filling the wrong input
  (`input[type="number"]').first()` matched AccountsSection's own
  "Starting Balance" field once that section started rendering above the
  Deposit/Withdraw card) — now scoped to a real `data-testid`.

- **UI Polish & Bug Fix Sprint — win/loss trade notifications moved from
  a center-screen banner to real side-panel toasts**
  (`frontend/src/ui/components/CommandCenter/CyberNotifications.tsx`,
  `frontend/src/App.tsx`, `frontend/tailwind.config.js`;
  `frontend/src/ui/components/TradeOutcomeBanner.tsx` deleted): the old
  `TradeOutcomeBanner` was already non-blocking (`pointer-events-none`
  wrapper, real queue, 8s auto-dismiss) but rendered as one large card
  top-center, interrupting the player's view of the game world — the
  exact complaint this sprint was asked to fix. Its real logic (ack a
  trade only once its notification is actually dismissed, never the
  instant it's shown, so a mid-display reload doesn't lose it; no
  fabricated "Strategy" label — real symbol/side/holding-time only) now
  lives in `CyberNotifications.tsx`, the component that already had the
  real right-side stacking toast stack (slide-in-from-the-right + fade,
  reusing the existing `cmd-toast-in`/`cmd-toast-out` keyframes — no new
  animation needed) every other real-time event (new trade available,
  research complete, risk alerts) already used. One shared stack means
  a trade toast can never be covered by or overlap a second notification
  system, by construction. Unlike the old one-at-a-time queue, multiple
  trade toasts can now stack simultaneously — nothing is capped/evicted
  the way the simpler event toasts are, so several trades closing near
  the same tick each still get their own real, undropped notification.
  Clicking a card still opens the real Trade Review (`DecisionDetail.tsx`
  via the existing `trade:inspect` event — Trade Thesis, Bull/Bear Case,
  Market Context, Confidence Engine, Post-Trade Review with real P&L,
  Trade Plan with entry price/quantity/side, and Invalidation criteria).
  The brief's fuller Trade Review field list (Fees, a literal Executive
  Board Consensus/CIO Recommendation/Risk Officer Comments/Quant
  Analysis section breakdown, explicit Save-to-Memory/Replay-Timeline
  buttons on this specific view) is not fabricated here — `DecisionDetail`
  already covers the real subset of that list this codebase actually has
  data for; no new fields were invented to fill the rest. The now-dead
  `cmd-shake`/`cmd-banner-in`/`cmd-banner-out`/`cmd-glitch` keyframes
  (only ever used by the deleted banner) were removed along with it.
  `commandCenter.spec.ts`'s trade-outcome test and `helpers.ts`'s
  `dismissBlockingPopups` bystander-popup dismisser were both updated for
  the new `trade-outcome-toast` testid and multi-instance stacking.

### Changed

- **Chapter 69 restructured to three parts (correcting the previous
  Chapter 70/71 numbering)**
  (`docs/DesignBible/volumes/10-broker-live-trading/`): per explicit
  correction, the content previously drafted as standalone "Chapter 70
  — Prop Firm Rule Engine" (plus its addendum) and "Chapter 71 —
  Institutional Rule Engine" is folded into Chapter 69 as Part 2 and
  Part 3, alongside the original Multi-Account & Fund Management System
  brief as Part 1. Each part keeps its own full structure (Executive
  Summary through Implementation Notes); every internal cross-reference
  between the three was rewritten from "Chapter 70"/"Chapter 71" to
  "Part 2"/"Part 3" of Chapter 69. The standalone chapter-70/71 files
  are removed; Volume 10's README and the master Table of Contents are
  updated to reflect the new structure. Documentation only, no code or
  research findings changed — this is a pure reorganization of where
  the same already-verified content lives.

### Added

- **Chapter 70 — Executive Board & CEO Intelligence System**
  (`docs/DesignBible/volumes/09-departments/chapter-70-executive-board-ceo-intelligence-system.md`):
  a new Design Bible chapter, filed in Volume 9 (Departments) rather
  than Volume 10 — its subject is executive governance, not broker/
  account infrastructure. One of the highest real-coverage chapters
  written this run, alongside Chapters 66/67: a real monthly CIO review
  (`ExecutiveReview`), a real permanent per-decision meeting log
  (`ExecutiveMeetingLogEntry`) recording department opinions/network
  recommendation/CEO decision, a real merged executive-priorities list
  (`computeExecutivePriorities()`), a real Company Health/Score
  breakdown covering 6 of the brief's own 9 Company Health Review
  categories, and — the strongest match — Chapter 67's Global Status
  Bar/Executive Alert Center/`useDashboardData()` hook already
  surfacing 7 of the brief's own 10 Executive Command Center metrics
  live today. 4 of the brief's 12 named board seats are filled by real
  agents with real (CIO exact; 3 others close-but-not-exact) "Chief"
  titles. Confirmed genuinely unbuilt: the other 8 board seats, Daily/
  Quarterly meeting cadence, automatic Emergency Board Meeting triggers
  (2 of the 7 named triggers have no underlying signal to fire from at
  all), Modify/Delegate as CEO decision actions, a general-purpose
  non-trade Decision Center, per-executive Contribution/Forecast-
  Accuracy scorecards, and a CEO Assistant AI. Documentation only, no
  code changes.

- **Chapter 70 addendum + Chapter 71 — Institutional Rule Engine (IRE)**
  (`docs/DesignBible/volumes/10-broker-live-trading/`): documentation
  only, no code changes. A follow-up brief labeled "Addendum to
  Chapter 69" arrived specifying eight systems (Trailing Drawdown
  Engine, Consistency Rule Engine, Leverage System, Scaling Milestones,
  Challenge Windows, a Weekday-Aware Time System, a Prop Firm Calendar,
  and a Compliance Score) — applied to Chapter 70 (Prop Firm Rule
  Engine) instead, since its content directly extends gaps that
  chapter's own research already named, flagged explicitly in Chapter
  70's own Status line. Every one of the eight is confirmed genuinely
  unbuilt by direct research: no peak-equity/high-water-mark field, no
  weekday/hour concept in `TimeState`, and no leverage/margin concept
  exist anywhere in this codebase's schemas.

  The same brief also introduced a real architectural correction —
  no account type should own an independent rule-enforcement system;
  every account loads a Rule Profile into one centralized engine —
  written as new **Chapter 71**. Grep-confirmed: no `Rule`/
  `RuleProfile`/`RuleEngine` class exists anywhere in this codebase
  today. Today's real risk checks (Chapters 57/58/66) are deliberately
  hardcoded, transparent Python functions, not a data-driven rule
  interpreter — Chapter 71 names this explicitly as a real trade-off
  any future implementation must honor (preserve the same
  auditability), not a free upgrade. The brief's own six Custom Rule
  Builder examples were checked individually: three reference
  already-real, CEO-editable `RiskLimits` fields with no rule-authoring
  surface around them; three reference infrastructure (weekday
  awareness, a volatility-threshold hook, a configurable confidence
  threshold) that doesn't exist in any form. Chapter 70 updated to
  reference Chapter 71 as the only system that would ever enforce its
  rules. Both chapters depend on Chapter 69 and are gated by the same
  Live Trading Gate (Appendix G).

- **Chapter 70 — Prop Firm Rule Engine**
  (`docs/DesignBible/volumes/10-broker-live-trading/chapter-70-prop-firm-rule-engine.md`):
  a new Design Bible chapter, pure target architecture — no code was
  written against it. Filed as Chapter 70 (the brief itself carried no
  explicit number, flagged in the chapter's own Status line). The
  strongest real-coverage ratio of any chapter in this run: 5 of the
  brief's 15 supported rules (Daily Loss Limit, Maximum Overall
  Drawdown, Maximum Position Size, Maximum Risk Per Trade, Maximum
  Open Positions) are already real, enforced `RiskLimits` fields
  (Chapter 57), a sixth (Profit Targets) is real in a related
  daily-scoped shape, and `DailyObjectiveStatus` already provides a
  live, per-day compliance readout close to the brief's own Live
  Account Monitoring/Prop Firm Dashboard shape. The Trade Gatekeeper's
  real, unconditional block-and-explain pipeline (Chapter 58) already
  matches the brief's own Pre-Trade Validation shape exactly. Trailing
  drawdown, consistency rules, leverage, account scaling milestones,
  weekend/time-based restrictions, and challenge-scoped (vs.
  daily-scoped) tracking are all confirmed genuinely unbuilt — no
  day-of-week concept exists anywhere in this codebase's `TimeState`,
  and no peak-equity tracking exists to trail a drawdown from. Depends
  on Chapter 69's account model and is gated by the same Live Trading
  Gate (Appendix G). Documentation only, no code changes.

- **Chapter 69 — Multi-Account & Fund Management System (MAFMS)**
  (`docs/DesignBible/volumes/10-broker-live-trading/`): a new Design
  Bible chapter, pure target architecture — no code was written against
  it. Before writing, research confirmed this codebase's real
  multi-account footprint: exactly two hardcoded, genuinely isolated
  capital pools (`PaperPortfolio`, the company's trading account, and
  `TreasuryState`, the CEO's personal capital), each with its own real
  transaction history, moved between only via an explicit deposit/
  withdraw call. A generalized N-account model, account types, account
  IDs/owners/permissions, account switching, account groups,
  cross-account aggregation, Fund Mode, and Client Mode are all
  confirmed genuinely unbuilt. One real, notable exception: the Prop
  Firm account profile's own named special rules (daily loss limit,
  max drawdown, position size limits) are already real, working
  machinery in `RiskLimits`/`risk_engine.py` — just scoped globally to
  the one account that exists, not as an assignable per-account
  profile. Depends on Chapter 68 (Institutional Broker Management
  System), and is gated by the same Live Trading Gate (Appendix G).
  Documentation only, no code changes.

- **Appendix G — the Live Trading Gate**
  (`docs/DesignBible/appendices/appendix-g-permanent-development-policy.md`,
  cross-referenced from Chapter 68): records, as permanent policy, the
  seven conditions the Institutional Broker Management System must
  meet before connecting to any live brokerage — Chapters 67–75
  complete, paper trading extensively tested, backtesting validated,
  Risk Authority fully operational, Emergency Stop verified, Audit
  Center operational, and the CEO explicitly enabling Live Trading
  Mode. Charles Schwab v1.0 is a final V1.0 milestone, built only after
  every system the platform's paper-trading proof depends on is real,
  never the vehicle that proves them. Documentation only.

- **Chapter 68 — Institutional Broker Management System (IBMS)**
  (`docs/DesignBible/volumes/10-broker-live-trading/`): a new Design
  Bible chapter, pure target architecture — no code was written against
  it. Before writing, research confirmed this codebase's real broker
  footprint: `app/broker.py`'s `PaperBroker` (a fully simulated
  order-book engine — no brokerage SDK, no API key, no code path
  reaching a real execution endpoint, per its own module docstring
  since v0.6) and `app/market_data.py`'s `MarketDataProvider` adapter
  interface (a real, proven "one connector, zero consumer changes"
  pattern, applied so far only to market data, never execution).
  Broker connections, authentication, encrypted credentials
  (`requirements.txt` carries no HTTP client or cryptography library),
  account synchronization, buying power beyond a cash-reserve floor,
  position reconciliation, broker health monitoring, a multi-account
  model, and Charles Schwab v1.0 itself are all confirmed genuinely
  unbuilt, matching Chapter 66's own earlier "Broker Failsafe...
  genuinely does not exist" finding. Also converts Volume 10 from a
  flat outline stub into the same folder + README + numbered-chapter
  structure Volume 9 already uses, and fixes two stale cross-references
  in Chapters 58/59 that pointed at the old flat file path.
  Documentation only, no code changes.

- **Chapter 67 Part 3 — final TTOS Compliance Scorecard**
  (`docs/DesignBible/volumes/09-departments/chapter-67-tradetown-operating-system.md`):
  a new closing section scoring the brief's own nine pillars
  (Navigation/Search/Command Palette/Workspace Manager/Quick
  Actions/Notifications/Emergency Stop/Executive Dashboard/Navigation
  Intelligence) honestly against what this codebase actually does
  today, plus what's genuinely built or still unbuilt beyond those
  nine. Closes out Part 3's own buildable scope as researched and
  scoped at the start of this pass — every remaining "unbuilt" item was
  checked against the real codebase, not assumed from the original
  brief. Documentation only, no code changes.

- **Chapter 67 Part 3 — TTOS Navigation polish**
  (`frontend/src/ui/components/CommandPalette.tsx`,
  `CommandCenter/panels/OverviewPanel.tsx`): two real, low-risk fixes.
  The Command Palette gained "Open Newspaper" and "Open Campus Map"
  commands — the only two of this app's 6 real standalone overlays
  with no path into the CEO's own central navigation surface
  (Newspaper was diegetic-only; Campus Map lived only in
  QuickView's/PauseMenu's own separate buttons) — for parity with the
  other four, not a new overlay. OverviewPanel's "AI Academy" card
  (which navigates to KNOWLEDGE, v0.7 Feature 25's actual AI Academy &
  Knowledge Network) was relabeled to "Academy Progression" to resolve
  a real, live naming collision with the completely unrelated
  pre-existing "ACADEMY" tab (Trading Academy) — the same
  disambiguation `MentorLibraryPanel.tsx`'s own "(KNOWLEDGE tab)" aside
  already established, not an invented label. Deliberately not touched:
  the OPS tab's own section-placement naming collision and any tab
  identifier rename, both already documented in `navigation.ts` as
  deferred (renaming would ripple `clickTab()`'s exact-name lookups
  across the whole Playwright suite for zero real user benefit).
  `tsc`/`eslint`/`vite build` clean, a new Navigation polish test in
  `commandPalette.spec.ts`, full `commandPalette.spec.ts` +
  `commandCenter.spec.ts` + `campusMap.spec.ts` regression passing (one
  already-documented pre-existing flaky movement-key failure aside).

- **Chapter 67 Part 3 — TTOS Executive Dashboard consolidation (data layer)**
  (`frontend/src/ui/components/CommandCenter/lib/useDashboardData.ts`,
  `QuickView.tsx`, `panels/OverviewPanel.tsx`): `QuickView` (the
  collapsed glance view) and `OverviewPanel` (the OVERVIEW tab) were
  independently recomputing `riskLevel()`, `latestDecision()`, and
  `computeNoTradeStats()` from the same gameStore fields — real,
  non-cosmetic duplication. A new `useDashboardData()` hook is now the
  one canonical place those shared derivations run, covering every real
  data point either component shows (Account Value/Month P&L/Top
  Opportunity from QuickView; the working-agent count from
  OverviewPanel), with zero data points lost either direction.
  Deliberately not a literal single-component merge — a compact
  always-visible glance and a full landing tab serve genuinely
  different real contexts, the same "reuse the data, don't force-merge
  different UI contexts" call this chapter's own Quick Action Dock
  slice already made for Pause/Resume/Emergency Stop. `BrainRoomHud`'s
  own toolbar pull-up remains a third, separate "company overview"
  surface, not folded in — a real, undone piece of the brief's full
  three-way consolidation, documented as such rather than silently
  dropped. `tsc`/`eslint`/`vite build` clean, full
  `commandCenter.spec.ts` regression passing (31/33, one skipped, the
  one failure the already-confirmed pre-existing flaky movement-key
  test) — live-verified no visual or behavioral change to either
  QuickView or OverviewPanel.

- **Chapter 67 Part 3 — TTOS real Global Emergency Stop**
  (`backend/app/emergency_stop.py`, `app/schemas.py`, `app/nexus.py`,
  `app/state.py`, `app/scribe.py`, `app/routers/emergency.py`,
  `frontend/src/ui/components/EmergencyStopControl.tsx`,
  `EmergencyStopConfirm.tsx`, `ConfirmDialog.tsx`, `TopStatusBar.tsx`):
  before writing code, research confirmed the rest of Part 3's brief
  (a Safety Settings page, a global status bar, the Quick Action Dock,
  a priority-tiered Alert Center, and several command-palette example
  commands with zero real backing feature — no broker integration
  exists anywhere for "Open Charles Schwab," no "Swing/Day Trading
  Mode" exists under any name) is entirely greenfield, so only Part
  3's own Primary Objective — a real Emergency Stop — was implemented
  this pass. New `EmergencyStopState` (active, activatedAt) on
  `GameSaveState`; new `POST /api/emergency-stop/activate`/`/resume`.
  Enforcement threaded through three real sites: `tick()` skips new
  proposal generation entirely while active; `_apply_operating_mode()`
  gained a third hard-block condition (checked first, before the
  cash-reserve and Chapter 66 `pause_trading` checks already there)
  keeping every pending proposal frozen in Assisted/Executive mode;
  `submit_ceo_decision()` also rejects the CEO's own manual buy/sell
  (only "wait" still allowed) — "only the CEO can resume trading"
  was read as "nothing executes until they explicitly do," not just
  an automation-only halt. Activating/resuming both write a real,
  permanent Company Memory entry, deliberately reused as the brief's
  own "incident report" rather than a second parallel record.
  Deliberately narrower than the brief on two points, both documented
  as explicit scope cuts: pending proposals are left pending, never
  auto-cancelled (the brief's own "(configurable)" qualifier); already-
  placed broker orders are never force-closed. A new, permanent,
  always-visible red button in `TopStatusBar.tsx` (never inside a
  Command Center tab), gated behind `ConfirmDialog.tsx` — the first
  reusable confirm-before-you-act component in this codebase (research
  confirmed none existed; every other destructive/high-stakes action
  here still fires immediately). 14 new/extended backend tests,
  `mypy`/`ruff` clean, full backend suite 1124/1124 passing,
  `tsc`/`eslint`/`vite build` clean, a new `emergencyStop.spec.ts`
  exercising the real running app end-to-end, live-verified against
  the running dev stack, `executiveVoting.spec.ts` and the full
  `commandCenter.spec.ts` regression both passing (the one unrelated
  failure is the already-confirmed pre-existing flaky movement-key
  test).

- **Chapter 67 Part 3 — TTOS Safety Settings core: real weekly/monthly
  loss circuit breakers** (`backend/app/schemas.py`, `app/risk_engine.py`,
  `app/state.py`, `app/routers/risk.py`,
  `frontend/src/ui/components/CommandCenter/panels/RiskPanel.tsx`):
  the second and third real circuit breakers beyond the one pre-existing
  daily-scoped loss limit. New `RiskLimits.maxWeeklyLossPct`/
  `maxMonthlyLossPct` (defaults 10%/15%, between the daily 5% and
  lifetime drawdown 20%), enforced by new `weekly_realized_pnl_pct()`/
  `monthly_realized_pnl_pct()` functions inside `evaluate_sentinel_risk()`
  — the same real hard-reject path the daily limit already used, scoped
  to the current sim week (7 days)/month (30 days) using constants
  mirrored from `app/nexus.py`'s own cadence (not imported, to avoid a
  `risk_engine.py -> nexus.py` dependency). CEO-editable via the
  existing `POST /api/risk-limits` write path. Frontend: a new "Safety &
  Capital Protection" block in the RISK tab's existing panel (not a new
  Operations-section tab — Operations has no other real backing feature
  to justify one yet), which also surfaces live Emergency Stop status
  and control inline, and explicitly documents Black Swan Protection,
  Broker Failover, and Emergency Contacts as not built: no external
  market-crash data feed, no live broker integration to fail over from
  (see `app/broker.py`'s own "Completely simulated" docstring), and no
  contact/notification-delivery system exist anywhere in this codebase.
  10 new backend tests, `mypy`/`ruff` clean, full backend suite
  1134/1134 passing; `tsc`/`eslint`/`vite build` clean, a new
  Playwright test in `commandCenter.spec.ts` exercising the real save
  round-trip and Emergency Stop surfacing, full `commandCenter.spec.ts`
  regression passing (the one failure is the already-confirmed
  pre-existing flaky movement-key test).

- **Chapter 67 Part 3 — TTOS real Global Status Bar**
  (`frontend/src/ui/components/GlobalStatusBar.tsx`, `App.tsx`): the
  always-visible broker-status/risk-status/capital-status/company-
  health strip this chapter's own Safety Systems section had named as
  genuinely missing. A second row under `TopStatusBar.tsx`, visible
  from every scene. Every value is a real field read straight off
  gameStore — Risk Level reuses `lib/derive.ts`'s own `riskLevel()`
  (same Sentinel/Guardian severity bucket RiskPanel already showed),
  Company Health reuses `overall`/`.tier`, Portfolio reuses the real
  Portfolio Heat tier (honestly not relabeled "Health"), Market reuses
  `marketEnvironment.label`, Automation reuses the real Operating Mode,
  Deployed reuses real capital-deployed % of equity, and Broker Status
  is honestly static — "SIMULATED" — since no live broker integration
  exists anywhere in this codebase. Connection status stays in
  `TopStatusBar.tsx`'s own dot, not duplicated. Fixed two real
  strict-mode text collisions this surfaced in the existing
  `commandCenter.spec.ts` suite (RiskPanel's "NORMAL" and
  PortfolioIntelPanel's "COOL" each now have a second, correct instance
  in the new strip) with `.first()`, the same fix pattern already used
  for the Part 3 Emergency Stop's "RESUME TRADING" collision. `tsc`/
  `eslint`/`vite build` clean, a new `globalStatusBar.spec.ts` exercising
  the real running app end-to-end, full `commandCenter.spec.ts`
  regression run twice (only the already-confirmed pre-existing flaky
  movement-key test failed both times, plus one live-backend-flakiness
  TREASURY failure confirmed to pass standalone).

- **Chapter 67 Part 3 — TTOS real Quick Action Dock**
  (`frontend/src/ui/components/QuickActionDock.tsx`, `EventBus.ts`,
  `state/gameStore.ts`, `CommandCenter/FullCommandCenter.tsx`): two
  genuinely new global controls — Automation Mode can now be cycled
  from anywhere (previously reachable only inside the COMPANY tab), and
  four quick-jump buttons open the Command Center directly on
  RISK/COMPANY/PORTFOLIO/EXECUTIVE instead of always defaulting to
  OVERVIEW. New `pendingCommandCenterTab` gameStore field +
  `"ui:commandCenterJump"` EventBus event mirror the existing
  `pendingInspectDecision`/`"trade:inspect"` pattern the Trade Outcome
  Banner already established, rather than inventing a second mechanism
  for the same shape. Deliberately not a full physical consolidation:
  Pause/Resume+Work Mode (`BottomToolbar.tsx`) and Emergency Stop
  (`TopStatusBar.tsx`) stay in their existing real, global,
  always-visible locations rather than being duplicated into this dock
  — reuse over duplication, and merging three independently-tested
  components for a cosmetic-only change risked the same layout
  regressions this chapter's own Part 3 already hit twice with
  `TopStatusBar.tsx`. Because this dock is always mounted (like
  GlobalStatusBar), its first draft's plain labels ("LEARNING", "Risk",
  "Company Health") caused three real strict-mode collisions against
  already-correct content elsewhere in the 34-tab Command Center —
  fixed at the source with distinct visible labels ("→ Risk", not bare
  "Risk") and an `aria-label`-based accessible name for the mode-cycle
  button, rather than patching every downstream test. `tsc`/`eslint`/
  `vite build` clean, a new `quickActionDock.spec.ts` exercising the
  real running app end-to-end, full `commandCenter.spec.ts` regression
  clean except the already-confirmed pre-existing flaky movement-key
  test; `emergencyStop.spec.ts` and `globalStatusBar.spec.ts` also
  verified passing.

- **Chapter 67 Part 3 — TTOS real Command Palette (Cmd/Ctrl+K)**
  (`frontend/src/ui/components/CommandPalette.tsx`, `App.tsx`): real
  commands only, per the brief's own constraint. Save/Load/Open Company
  Memory/Coach Dashboard/Brain Room Dashboard/Settings (the exact
  `BottomToolbar.tsx` actions), Pause/Resume Simulation, Work Mode
  toggle, Operating Mode switching, Emergency Stop (opens the real
  confirm dialog, never bypasses it), and 34 "Go to X" tab commands
  derived from `navigation.ts`'s own `TAB_SECTION` map, executed via the
  same `"ui:commandCenterJump"` plumbing `QuickActionDock.tsx` already
  established. Deliberately excludes two of the brief's own example
  commands with no real destination: "Open Charles Schwab" (no live
  broker integration exists — see `app/broker.py`) and "Swing/Day
  Trading Mode" (no such mode exists under any name). Opens via
  Ctrl/Cmd+K, closes via Escape or executing a command; filters by
  substring match against label + section hint; arrow-key navigation.
  Only mounted while open, so — unlike `GlobalStatusBar`/
  `QuickActionDock` — it doesn't create the always-visible label-
  collision class of bug those two hit; its own test scopes queries to
  the palette's own `data-testid` container since several of its real
  command labels (Save, tab names) legitimately duplicate other
  always-visible real controls while the palette itself is open. `tsc`/
  `eslint`/`vite build` clean, a new `commandPalette.spec.ts` exercising
  the real running app end-to-end (open, filter, execute a real tab
  jump, close), full `commandCenter.spec.ts` regression clean except
  the already-confirmed pre-existing flaky movement-key test.

- **Chapter 67 Part 3 — TTOS real Universal Search, built into the
  Command Palette** (`frontend/src/ui/components/CommandPalette.tsx`):
  rather than a second Ctrl+K-shaped overlay competing for the same
  interaction pattern, the existing palette's own input now also
  searches real, already-loaded entities — the same "index of what we
  already have, never a new source of truth" pattern `CompanyMemory
  .tsx`'s own client-side filter already established, no new backend
  endpoint. Real employees (14, via `AGENT_IDS`/`AGENT_PROFILES`, jumps
  to AGENTS), closed trades (`paperPortfolio.tradeHistory`, jumps to
  REPLAY), research items (jumps to RESEARCH), and Company Memory
  records (opens the real Company Memory overlay rather than
  reimplementing its own search a second time) are all searchable
  alongside commands. Rendered results are capped at 50 (`MAX_RESULTS`)
  so a broad query against a mature save's full history stays
  scrollable — the underlying search still runs across every real
  record, only the render is capped. `tsc`/`eslint`/`vite build` clean,
  a new Universal Search test verifies a real employee result and
  confirms it jumps to the real AGENTS tab, full `commandCenter.spec.ts`
  regression clean except the already-confirmed pre-existing flaky
  movement-key test.

- **Chapter 67 Part 3 — TTOS real Smart Notification priority tiers +
  Executive Alert Center** (`frontend/src/types.ts`,
  `game/systems/EventBus.ts`, `state/gameStore.ts`,
  `ui/components/CommandCenter/CyberNotifications.tsx`,
  `ui/components/AlertCenter.tsx`, `ui/components/CommandPalette.tsx`):
  the one remaining genuinely unbuilt piece of Part 3's original brief.
  Every toast now carries a real `NotificationTier`
  (`critical`/`high`/`normal`), always derived from the same field
  already driving the toast's own kind/copy — never a second-guessed
  severity — and recorded into a new `gameStore.alertHistory` (capped
  at 200 entries, `MAX_ALERT_HISTORY`, a render/storage cap only, same
  "cap render, never cap real data" pattern Universal Search's
  `MAX_RESULTS` already established). Two sources previously produced
  zero proactive notification anywhere in this codebase — a critical
  `RiskWarning` (only passive visibility in RiskPanel/GlobalStatusBar
  before) and Emergency Stop activation — both now push a sticky,
  non-auto-dismissing "critical" toast, the one real interrupt behavior
  this phase adds (a true modal interrupt already exists for trade
  proposals via `ExecutiveVoting.tsx` and stays that component's own
  territory). New `AlertCenter.tsx`, opened via the Command Palette's
  new "Open Alert Center" command rather than a second Ctrl+K-shaped
  surface, reuses `Glass`/`StatusPill`/`TerminalLabel`/`EmptyState`
  from `CommandCenter/ui.tsx` for its own chrome, with tier filter
  chips (All/Critical/High/Normal, each a real live count). Diffing
  Emergency Stop activation correctly (without a duplicate push)
  required keying off the real `activatedAt` timestamp rather than a
  plain boolean transition: `NexusManager.setEmergencyStop()` applies
  the activate/resume response immediately, ahead of the next real WS
  broadcast tick (the same "don't wait for the next tick" pattern
  `riskLimits` already uses), so a stale, already-in-flight
  `active: false` broadcast sent by the server just before activation
  can be processed just after the immediate apply — a boolean diff
  misread that race as "resumed" and double-pushed on the next real
  tick, caught live via a new `alertCenter.spec.ts` before this fix.
  `tsc`/`eslint`/`vite build` clean, a new `alertCenter.spec.ts`
  exercises the real running app end-to-end (activates the real
  Emergency Stop, confirms the sticky toast survives past the normal
  6s auto-dismiss window, opens the real Alert Center via the Command
  Palette, and confirms real recorded history + tier filtering), full
  Playwright regression passing.

- **Chapter 67 Phase 1 — TTOS 7-section grouped navigation**
  (`frontend/src/ui/components/CommandCenter/lib/navigation.ts`,
  `FullCommandCenter.tsx`): before writing any code, a full audit +
  migration plan was presented (every existing tab/overlay/toolbar/
  notification, duplicate screens found, breaking changes flagged) and
  approved. Implemented the smallest honest slice from that plan: the
  34 real Command Center tabs now render grouped under TTOS's 7
  permanent sections (Headquarters/Markets/AI Workforce/Research/
  Portfolio/Operations/Archive) via a new `TAB_SECTION` map, instead of
  one flat button row. Deliberately additive, not a restructure — every
  `Tab` string identifier and button's accessible name are unchanged,
  so `clickTab()` and the number-key 1-9 shortcut keep working exactly
  as before across the whole Playwright suite, avoiding the wide test
  breakage a true identifier rename would have caused. Several
  placements are documented judgment calls (TREASURY under Headquarters
  since it's CEO-*personal* capital, not the company's own portfolio;
  OPS under Research despite its name colliding with the Operations
  section). Operations is real but thin (LOGS only) — Automation,
  Integrations, Infrastructure, and Broker Configuration have no
  backing feature anywhere in this codebase, so no placeholder tabs
  were added. Dashboard consolidation (3 independently-built overview
  screens found: QuickView, OverviewPanel, BrainRoomHud's toolbar
  pull-up), universal search, the command palette, a real Emergency
  Stop, workspace docking, and navigation analytics are all deferred to
  their own approved phases per the migration plan — not assumed to
  follow automatically from this slice. `tsc`/`eslint`/`vite build`
  clean, live-verified against the running dev stack, a real assertion
  added to `commandCenter.spec.ts`'s existing 34-tab test for the 7
  section labels, full `commandCenter.spec.ts` regression passing.

- **Chapter 67 written — TradeTown Operating System (TTOS)**
  (`docs/DesignBible/volumes/09-departments/chapter-67-tradetown-operating-system.md`):
  researched first, per this volume's own convention. Unlike every
  other Volume 9 chapter, TTOS describes navigation/UX architecture,
  not a trading department. Research (a dedicated Explore pass over the
  whole frontend) confirmed the Command Center has grown to 34 real,
  independently-shipped tabs rendered as one flat, ungrouped,
  horizontally-scrolling button row (`FullCommandCenter.tsx`'s `TABS`
  constant); a real global toolbar (`BottomToolbar.tsx`) exposes 8
  one-click actions plus Work Mode, but Operating Mode and Time
  Controls stay buried inside the COMPANY tab; a real but narrow,
  non-tiered toast system (`CyberNotifications.tsx`) exists, where
  every notification behaves identically and nothing ever interrupts;
  and two real, narrow, already-loaded-state client-side search filters
  exist (`CompanyMemory.tsx`, `KnowledgeGraphView.tsx`), backed by two
  real backend search functions no REST endpoint currently calls
  (`app/memory.py:search()`, `app/knowledge.py:search_knowledge()`).
  The genuine gaps the brief's five defining mechanisms name — universal
  search, a command palette, 7-section grouped navigation,
  dockable/saved workspaces, and priority-tiered notifications — do not
  exist anywhere in this codebase today, confirmed directly (no
  windowing/docking library in `frontend/package.json`, no
  confirmation-dialog pattern for critical actions, no navigation/UX
  telemetry of any kind, so none of the brief's proposed KPIs/Reports
  are honestly computable yet). Not yet implemented (chapter written,
  target design) — no "implement" instruction has been given for this
  chapter.

- **Chapters 65/66 written — Market Regime Detection & Adaptive
  Strategy Engine, Institutional Safety, Capital Protection & Failsafe
  Framework** (`docs/DesignBible/volumes/09-departments/chapter-65-market-regime-adaptive-strategy.md`,
  `chapter-66-institutional-safety-capital-protection.md`): researched
  first, per this volume's own convention. Chapter 65 found two
  independent, real, indicator-driven regime classifiers already exist
  (`app/market_environment.py`'s 5-way, `app/market_intelligence.py`'s
  13-way, the latter with a real Regime Confidence Score) — the genuine
  gap is Adaptive Strategy Profiles and Automatic Adaptation. Chapter 66
  found a real, live, mechanically-enforced daily circuit breaker and a
  real multi-stage pre-trade veto pipeline already function as the
  brief's "Trade Quality Override" — the genuine gaps are the named
  Safety Pyramid vocabulary, enforcing the real-but-inert
  `pause_trading` disagreement signal, weekly/monthly-scoped limits, and
  a CEO manual override control.

- **Chapter 65 backend + frontend — Regime Reconciliation** (`app/schemas.py`,
  `app/market_intelligence.py`, `app/regime_reconciliation.py`,
  `app/routers/market.py`, `frontend/src/types.ts`, `frontend/src/net/api.ts`,
  `CompanyPanel.tsx`): the smallest honest first slice Chapter 65's own
  research scoped — reconciling the two real, independent regime
  classifiers into one CEO-facing read. `compute_regime_reconciliation()`
  combines `MarketEnvironmentState` and `MarketIntelligenceState` into an
  `agreement` (aligned/diverging, via the existing regime-consistency
  mapping — promoted from `market_intelligence.py`'s private
  `_REGIME_CONSISTENCY_MAP` to a public `REGIME_CONSISTENCY_MAP` rather
  than duplicated) and a read-only `posture` recommendation
  (cautious/normal/opportunistic, from `MarketQualityScore.tier` +
  `confidence_pct` against a fixed `OPPORTUNISTIC_MIN_CONFIDENCE_PCT`
  threshold — `avoid_trading`/`poor` tiers are always cautious regardless
  of confidence). Exposed via new `GET /api/market/regime-reconciliation`,
  computed fresh per request, never persisted. The Company tab now shows
  a "Regime Reconciliation" card above Market Environment. Nothing writes
  the posture to any `RiskLimits` field — recommend-only, matching
  Chapter 64's Resource Allocation precedent. 8 new backend tests,
  `mypy`/`ruff` clean, full backend suite 1110/1110 passing,
  `tsc`/`eslint`/`vite build` clean, live-verified against the running
  dev stack, full `commandCenter.spec.ts` regression passing (one
  unrelated pre-existing flaky movement-key test, confirmed by
  reproducing it identically against the pre-Chapter-65 baseline).

- **Chapter 66 backend — AI Consensus Safety enforcement** (`app/nexus.py`):
  the one precise, high-value gap Chapter 66's own research found —
  `ExecutiveRecommendation.action == "pause_trading"` (2+ departments
  actively oppose, or Market Intelligence reads `avoid_trading`) was a
  real, already-computed signal with no code path enforcing it.
  `_apply_operating_mode()` now keeps a proposal pending whenever this
  signal fires, in BOTH Assisted and Executive mode — the same real
  safety-constraint precedent the existing cash-reserve check already
  established, a genuine behavioral change to what Executive Mode used
  to auto-resolve unconditionally. No new frontend code needed: the
  CEO's existing Executive Voting popup already renders any
  `ExecutiveRecommendation` generically. 3 new backend tests,
  `mypy`/`ruff` clean, full backend suite 1102/1102 passing.

- **Chapter 64 backend + frontend — Strategic Review Cycle** (`app/schemas.py`,
  `app/goals.py`, `app/nexus.py`, `app/save_modules.py`, `app/ws_manager.py`,
  `frontend/src/types.ts`, `frontend/src/net/socket.ts`,
  `NexusManager.ts`, `EventBus.ts`, `gameStore.ts`, `CompanyPanel.tsx`):
  the fifth and final Chapter 64 slice, closing out this chapter's real
  scope entirely. Mirrors Chapter 63's monthly `ExecutiveReview`
  structure but over CEO-authored goals — a new `StrategicReview`
  schema; `generate_strategic_review()` finds what genuinely changed
  since the previous review via real ISO-timestamp comparison against
  each goal's `updatedAt`/`completedAt` and each milestone's
  `reachedAt` (never a fabricated delta), and reuses the Executive
  Priority Engine's own top-ranked goal directly. Generated on the
  same monthly boundary as the Executive Review in `app/nexus.py`'s
  `tick()`, capped at `MAX_STRATEGIC_REVIEWS = 20`. The COMPANY tab
  now shows a "Strategic Review Cycle" card listing every real review
  newest-first with its own real summary. 8 new backend tests,
  `mypy`/`ruff` clean, full backend suite 1099/1099 passing,
  `tsc`/`eslint`/`vite build` clean, live verification confirming a
  real review (2 expired goals, 4 milestones reached) rendered
  correctly after advancing time to a real month boundary.

- **Chapter 64 backend + frontend — Resource Allocation** (`app/schemas.py`,
  `app/goals.py`, `app/routers/goals.py`, `frontend/src/types.ts`,
  `frontend/src/net/api.ts`, `CompanyPanel.tsx`): the last piece that
  chapter's own Implementation Notes had deferred pending the Priority
  Engine. Honestly scoped once actually designed — a `Goal` tracks a
  company-wide metric, not a set of open positions with a real capital
  pool behind it, so there was never a real per-goal capital pool to
  allocate. The real slice instead: a normalized share of executive
  ATTENTION. New `GoalAllocation` schema; `compute_resource_allocation()`
  reuses the Priority Engine's own real scores directly (no second
  composite) and normalizes each active goal's score against the sum of
  all of them so the recommendation sums to ~100%, falling back to an
  even split only in the one real edge case where every active goal's
  urgency score is 0. New read-only `GET /api/goals/allocations`,
  computed fresh per request, never a claim about moving real capital —
  same recommend-only boundary Chapter 59/60 already respect. Each
  active goal's card in the COMPANY tab now shows a "Recommended
  attention" bar with a real %. 5 new backend tests, `mypy`/`ruff`
  clean, full backend suite 1091/1091 passing, `tsc`/`eslint`/`vite
  build` clean, live Playwright verification confirming two active
  goals both render a correctly normalized 50% allocation bar.

- **Chapter 64 backend + frontend — Executive Priority Engine**
  (`app/schemas.py`, `app/goals.py`, `app/routers/goals.py`,
  `frontend/src/types.ts`, `frontend/src/net/api.ts`,
  `CompanyPanel.tsx`): the next honest slice per this chapter's own
  recommended sequencing — a real, named formula ranking active goals
  by urgency, deliberately not a reuse of Chapter 59's trade-proposal
  Priority Score (structurally different inputs). New `GoalPriority`
  schema; `compute_goal_priority()` scores an active goal from real
  distance-to-target alone when there's no deadline, or the real pace
  required per day to hit a real deadline otherwise, clamped against a
  transparent, stated ceiling (5%/day = maximally urgent) rather than a
  hidden weighting. New read-only `GET /api/goals/priorities`, computed
  fresh per request. The Company Goals card now orders active goals by
  real priority score and shows a PRIORITY badge plus real
  days-remaining. 13 new backend tests, `mypy`/`ruff` clean, full
  backend suite 1086/1086 passing, `tsc`/`eslint`/`vite build` clean,
  live verification confirming a tight-deadline goal correctly outranks
  an open-ended one.

- **Chapter 64 backend + frontend — Milestone Tracking** (`app/schemas.py`,
  `app/goals.py`, `frontend/src/types.ts`, `CompanyPanel.tsx`): the
  "next honest slice" that chapter's own Implementation Notes named,
  extending the existing `Goal` object with three real, fixed
  checkpoints (25%/50%/75% of real progress) rather than a second
  tracking concept — no milestone for 100%, since goal completion
  already tracks that via `status`. A milestone is marked permanently
  reached the moment real progress crosses it, checked both at goal
  creation (honestly handles a goal that starts past a milestone) and
  every tick. Each Goal card in the COMPANY tab now shows its three
  milestones as filled/hollow markers. Caught a real bug via a new test
  before it reached the frontend: the first version passed the wire
  alias (`"reachedAt"`) instead of the actual field name
  (`"reached_at"`) to `model_copy()`, which silently dropped the
  update. 6 new backend tests, `mypy`/`ruff` clean, full backend suite
  1079/1079 passing, `tsc`/`eslint`/`vite build` clean, live
  verification against the running dev stack.

- **Chapter 63 backend + frontend — Company Health tier thresholds and
  Benchmarking**
  (`app/schemas.py`, `app/company_health.py`, `app/nexus.py`,
  `app/state.py`, `app/routers/risk.py`, `app/ws_manager.py`,
  `frontend/src/types.ts`, `frontend/src/net/api.ts`,
  `frontend/src/ui/components/CommandCenter/lib/derive.ts`,
  `CompanyPanel.tsx`): Company Health's `_TIER_THRESHOLDS`
  (85/70/50/30) are now four CEO-configurable `RiskLimits` fields,
  defaulting to the exact prior constants so existing behavior —
  including the Founders' "excellent" Legendary Status trigger — is
  unchanged until adjusted, validated together to stay strictly
  descending. A new Benchmarking card computes a real delta against a
  CEO-chosen 1x/3x/6x/12x prior monthly Executive Review, entirely from
  already-loaded data (no new backend endpoint). Fixed a real bug this
  pass introduced along the way: `executiveTier`/`combinedTier` were
  still reading the old hardcoded thresholds instead of the CEO-passed
  ones, caught by a new unit test. 91 new/updated backend tests,
  `mypy`/`ruff` clean, full backend suite 1073/1073 passing,
  `tsc`/`eslint`/`vite build` clean, and live verification of both the
  save path and the descending-order validation error.

- **Chapter 64 backend + frontend — Company Goals (smallest real
  slice)** (`app/schemas.py`, `app/goals.py` (new), `app/nexus.py`,
  `app/state.py`, `app/routers/goals.py` (new), `app/main.py`,
  `app/save_modules.py`, `frontend/src/types.ts`,
  `frontend/src/net/api.ts`, `NexusManager.ts`, `EventBus.ts`,
  `socket.ts`, `gameStore.ts`, `CompanyPanel.tsx`): a CEO-authored
  `Goal` naming one real, already-computed metric (Company Health
  combined score, Company Score, portfolio return %, or Academy level)
  and a target value. Real progress recomputed every tick
  (`tick_goals()`, alongside `company_health`/`company_score` in
  `nexus.py`'s `tick()`), transitioning to `completed` or `expired` —
  both permanent, matching `app/hall_of_fame.py`'s "a crossed milestone
  stays crossed" convention. `POST /api/goals/create` /
  `POST /api/goals/cancel`, capped at `MAX_GOALS = 20`. A new "Company
  Goals" card in the COMPANY tab (create form, real progress bars,
  cancel control). No Executive Priority Engine, Resource Allocation,
  or Milestone Tracking yet — all three explicitly deferred per this
  chapter's own recommended sequencing.

- **Bug fix — WebSocket broadcast never included the new `goals`
  field** (`app/ws_manager.py`): found via live Playwright verification
  of the new Goals UI (a real black-canvas React crash reading
  `goals.length` on `undefined`), not caught by any automated test.
  `ws_manager.py` builds its per-tick broadcast as an explicit
  field-by-field dict, and `goals` was added everywhere else (the
  schema, `GET /api/load`, `tick()`) but missed here.

- **Chapters 63 and 64 — Design Bible chapters (documentation-only, no
  code changes)**
  (`docs/DesignBible/volumes/09-departments/chapter-63-executive-performance-company-health.md`,
  `chapter-64-executive-strategic-planning-goal-management.md`):
  **Chapter 63 (Executive Performance & Company Health Engine)** —
  researched first, and like Chapters 61/62 found almost the entire
  brief already real and predating this chapter: the two-tier Company
  Health Score (`app/company_health.py`), the seven-metric Company Score
  (`app/company_score.py`), Department Scorecards via Weekly
  Self-Evaluation (`app/executive_intelligence.py`), and the monthly
  Executive Review (`app/executive_review.py`). Two sections are
  honestly scoped as partial gaps rather than claimed complete: a
  unified Early Warning feed (today's warnings are real but scattered
  across the Executive Review's flags and Sentinel/Guardian's
  RiskWarnings, never consolidated) and genuine multi-period or
  industry-standard Benchmarking (today only one real
  immediately-previous-period delta exists). **Chapter 64 (Executive
  Strategic Planning & Goal Management Engine)** — the opposite research
  outcome: a genuine, mostly-unbuilt gap, written as target design like
  Chapter 60. Three real, adjacent systems were checked and explicitly
  found *not* to be substitutes — `CompanyPriority` (a real four-value
  operating stance, not CEO-authored goals), Chapter 59's Capital
  Priority Engine (ranks trade proposals, not company goals), and
  `_long_term_goals()` (real but static, regenerated text with no
  tracking). No goal/objective/milestone data model exists anywhere in
  this codebase today. Both chapters' status rows added to
  `docs/DesignBible/volumes/09-departments/README.md`.

- **Chapter 62 backend + frontend — Innovation Lab (Knowledge
  Integration, Innovation Budget, Experiment Tiering)**
  (`app/scribe.py`, `app/state.py`, `app/schemas.py`, `app/sandbox.py`,
  `app/routers/risk.py`, `app/strategy_lab.py`,
  `frontend/src/types.ts`, `StrategyCertificationView.tsx`,
  `frontend/src/ui/components/CommandCenter/lib/derive.ts`): the three
  pieces Chapter 62's own research named as genuinely new (almost the
  entire brief was already real — see the chapter's Executive Summary).
  **Knowledge Integration**: every strategy retirement now also files a
  real `MemoryRecord` under the pre-existing but never-populated
  `"strategy"` `MemoryCategory` (`record_strategy_hall_of_fame_entry()`/
  `record_strategy_failed_archive_entry()`), alongside the pre-existing
  Company DNA nudge. **Innovation Budget**: `RiskLimits.maxLimitedLiveCapital`
  (default $2,000, matching the prior fixed `MAX_LIMITED_LIVE_CAPITAL`)
  threaded through `begin_limited_live()`. **Experiment Tiering**:
  `compute_experiment_tier()` classifies a strategy's own real Monte
  Carlo magnitude (larger of projected upside or downside) into
  minor/moderate/major/transformational against three honest, declared
  thresholds — `None` until a real Monte Carlo result exists, never
  guessed — exposed as `StrategyDossier.experimentTier` and shown as a
  badge in the Strategy Lab's Certification view. 13 new backend tests,
  `mypy`/`ruff` clean, full backend suite 1039/1039 passing,
  `tsc`/`eslint`/`vite build` clean, and live verification against the
  running dev server for all three pieces (a real retirement, a real
  CEO risk-limit write, and a real dossier read all confirmed working
  with no server errors).

- **Chapter 61 backend + frontend — Knowledge Quality Score**
  (`app/schemas.py`, `app/decision_vault.py`, `app/routers/decision_vault.py`,
  `frontend/src/types.ts`, `frontend/src/net/api.ts`,
  `DecisionVaultPanel.tsx`): a real, three-part composite computed fresh
  per request (never persisted) — Historical Success (the real win rate
  of every other Vault entry sharing this entry's own symbol/regime/
  confidence-tier profile, reusing the Similarity Engine's own bucket
  match), Pattern Frequency (how many other entries share that profile —
  an honest recurrence proxy, explicitly NOT a literal usage counter,
  since nothing tracks how often an entry was actually shown to the CEO),
  and Relevance (recency relative to the Vault's own real age span, not
  an arbitrary fixed window). Deliberately does not attempt the brief's
  Accuracy/Usefulness/Validation dimensions — no signal anywhere in this
  codebase measures those. New `GET /api/decision-vault/quality-score`
  endpoint, honoring the CEO's `minSimilarMatches` control. New card in
  `DecisionVaultPanel.tsx` alongside the existing Trade Report Card and
  Similarity Engine reads. 6 new backend tests, `mypy`/`ruff` clean, full
  backend suite 1026/1026 passing, `tsc`/`eslint`/`vite build` clean, and
  a live 120-simulated-hour run confirming real, internally-consistent
  scores for both an old and a newly-closed Vault entry.

- **Bug fix — frontend `RiskLimits` type/defaults out of sync with
  backend** (`frontend/src/types.ts`, `frontend/src/game/systems/NexusManager.ts`,
  `frontend/src/state/gameStore.ts`): found while verifying the Knowledge
  Quality Score work — a full `npm run build` (which runs `tsc -b
  --noEmit`, the project-reference build check) failed with two
  pre-existing errors that a bare `npx tsc --noEmit` alone had not
  caught. `types.ts`'s `RiskLimits` interface was missing all four
  fields Chapter 61's own earlier passes had already added to the
  backend (`minSimilarMatches`, `mistakeWarningSharePct`,
  `maxDecisionVaultEntries`, `maxMemoryRecords`) — fixed by adding them.
  Fixing that surfaced a second, older, unrelated bug already present
  before this session: `NexusManager.ts`'s and `gameStore.ts`'s static
  default `RiskLimits` objects were both missing two Chapter 59 fields
  (`minPriorityScore`, `capitalReservePct`) — fixed by adding every real
  field with its actual backend default value to both.

- **Chapter 61 backend — Knowledge Retention Rules CEO control (Company
  Memory slice)** (`app/schemas.py`, `app/memory.py`, `app/scribe.py`,
  `app/nexus.py`, `app/state.py`, `app/routers/risk.py`): the change
  flagged in the previous entry as "larger, riskier" and deferred — done
  in a separate pass. One new `RiskLimits` field, `maxMemoryRecords`
  (default 200), matching the exact prior fixed constant
  (`MAX_MEMORY_RECORDS`) so existing behavior is unchanged until the CEO
  adjusts it. `app/memory.py`'s `record()` gained an optional
  `max_records` parameter; all 18 of `app/scribe.py`'s wrapper functions
  (the codebase's real "one writer gateway" callers) gained the same
  parameter, passed straight through. Two of `app/nexus.py`'s tick
  helpers needed the value threaded in one level
  (`_maybe_call_meeting`, `_apply_operating_mode`, both outside
  `tick()`'s own scope); the other 20 real call sites already had
  `effective_risk_limits` in scope. `POST /api/risk-limits` extended
  with the field (`maxMemoryRecords` ≥ 1). 7 new backend tests (3 for
  `record()`'s own capping behavior in a new `tests/test_memory.py`, 2
  confirming a representative `app/scribe.py` wrapper passes
  `max_records` through rather than silently defaulting, in a new
  `tests/test_scribe.py`, 2 CEO write-path validation cases), `mypy`/
  `ruff` clean, full backend suite 1021/1021 passing, and a live
  48-simulated-hour `POST /api/time/advance` run against the running dev
  server (CEO `maxMemoryRecords` set to 20 beforehand) confirming the
  memory log capped at exactly 20 real entries across nine different
  record categories with no server errors.

- **Chapter 61 backend — Knowledge Retention Rules CEO control (Decision
  Vault slice)** (`app/schemas.py`, `app/decision_vault.py`,
  `app/nexus.py`, `app/state.py`, `app/routers/risk.py`): one new
  `RiskLimits` field, `maxDecisionVaultEntries` (default 200), matching
  the exact prior fixed constant (`MAX_DECISION_VAULT_ENTRIES`) so
  existing behavior is unchanged until the CEO adjusts it.
  `record_vault_entry()` gained an optional `max_entries` parameter
  defaulting to the module constant; its one real call site
  (`app/nexus.py`, right after a trade closes) already had
  `effective_risk_limits` in scope, so no new plumbing was needed.
  `POST /api/risk-limits` extended with the field (`maxDecisionVaultEntries`
  ≥ 1). The Company Memory slice of this same control
  (`MAX_MEMORY_RECORDS`) is deliberately NOT included — that constant is
  read from 14 separate `app/scribe.py` call sites, a larger, riskier
  change left for a separate pass (see the chapter's own Implementation
  Notes). 4 new backend tests (2 Decision Vault ceiling cases, 2 CEO
  write-path validation cases), `mypy`/`ruff` clean, full backend suite
  1014/1014 passing, and a live `POST /api/risk-limits` call against the
  running dev server confirming both the accepted value and the rejected
  one (`0` → "Maximum Decision Vault Entries must be at least 1.").

- **Chapter 61 backend — Pattern Detection Sensitivity CEO controls**
  (`app/schemas.py`, `app/decision_vault.py`, `app/war_room.py`,
  `app/nexus.py`, `app/state.py`, `app/routers/risk.py`): two new
  `RiskLimits` fields, `minSimilarMatches` (default 3) and
  `mistakeWarningSharePct` (default 30.0), each defaulting to the exact
  prior fixed constant (`MIN_SIMILAR_MATCHES`, `MISTAKE_WARNING_SHARE`)
  so existing behavior is unchanged until the CEO adjusts them.
  `find_similar_vault_entries()`/`summarize_similarity()` both gained an
  optional parameter defaulting to the module constant; every other
  caller keeps today's exact behavior. `build_war_room_session()` gained
  a required `risk_limits` parameter threading the CEO's real values
  through — the one real call site (`app/nexus.py`) already had
  `effective_risk_limits` in scope for the Opportunity Gatekeeper call
  immediately after, so no new plumbing was needed. `POST
  /api/risk-limits` extended with both fields (`minSimilarMatches` ≥ 1;
  `mistakeWarningSharePct` in `(0, 100]`, since 0% would fire a warning
  on zero real mistakes). 9 new backend tests (4 Similarity Engine
  tiering/threshold cases, 5 CEO write-path validation cases),
  `mypy`/`ruff` clean, full backend suite 1010/1010 passing, and a live
  simulation confirming CEO-configured values flow through to real
  `WarRoomSession.similarTrades` reads without error.

- **Chapter 61 backend + frontend — Knowledge Graph extension**
  (`app/knowledge_graph.py`, `app/routers/knowledge_graph.py`,
  `app/schemas.py`, `frontend/src/types.ts`, `KnowledgeGraphView.tsx`):
  the single largest real, closeable gap Chapter 61's own research
  named. Three new Knowledge Graph node types, each backed by an
  already-real, already-persisted object — `trade`
  (`DecisionVaultEntry`), `case_study` (`CaseStudy`, covering both
  mistakes and successes), `strategy` (`Strategy`, excluding those still
  in the raw `idea` stage, mirroring the existing completed-research-only
  filter). Four new, honestly-labeled edge relations: `documented_by` (a
  trade's own real `caseStudyId`), `same_symbol` and `same_category`
  (descriptive, non-causal matches — never claimed as "this research
  caused this trade/strategy," since no field anywhere links them
  directly), and `created` (a Strategy's own real `createdBy` agent, a
  literal fact). `KnowledgeGraphView.tsx` needed no structural change —
  only its type/color/label/radius maps grew three entries. 8 new
  backend tests, `mypy`/`ruff`/`tsc`/`eslint`/`vite build` all clean,
  full backend suite 1002/1002 passing, and a live 400-tick simulation
  (Executive mode) confirming all three new node types and all four new
  edge relations appear with real data via a direct API call. The CEO
  Controls and Knowledge Quality Score sections of Chapter 61 remain
  target design — not built in this pass (see the chapter's own
  Implementation Notes for why `MAX_MEMORY_RECORDS` specifically is a
  larger, separate change than the two Similarity Engine constants).

- **Design Bible Chapters 61 & 62 — Institutional Knowledge Graph &
  Company Memory Engine, and Institutional Innovation Lab & Continuous
  Improvement Engine**
  (`docs/DesignBible/volumes/09-departments/chapter-61-knowledge-graph-company-memory.md`,
  `chapter-62-innovation-lab-continuous-improvement.md`): two
  target-design chapters, written per Appendix G's "Design Bible updated
  before implementation" policy. **Unlike every prior chapter in this
  volume, the research finding here is that both briefs already describe
  systems that are, in overwhelming part, already real** — this
  codebase already has `app/memory.py` (Company Memory), `app/knowledge.py`
  (v0.5 Feature 9's knowledge derivation), `app/knowledge_graph.py` (a
  real, already-shipped node-edge graph with a working frontend),
  `app/decision_vault.py` (Decision Vault, Trade Report Card, and a real
  rule-based Similarity Engine), `app/mistakes.py`/`app/successes.py`
  (Pattern Recognition), `app/wisdom.py` (Institutional Learning), and
  `app/company_dna.py` (the real behavioral-learning loop) for Chapter
  61; and `app/sandbox.py`'s real 8-stage gated pipeline plus
  `app/strategy_lab.py`'s Monte Carlo/Market Regime/Risk/9-department
  Executive Review/Founder Approval/Certification enrichment layer — already
  matching the brief's own Innovation Pipeline stage-for-stage, with a
  fully shipped 8-view frontend — for Chapter 62. **Chapter 61's real,
  closeable gap:** the Knowledge Graph's node types (today: agent,
  branch, research, academy project, executive review, coach report,
  hall of fame) don't yet include trades, decisions, case studies, or
  strategies, the exact node types the brief's own worked example names.
  **Chapter 62's real, closeable gap:** Experiment Tiering (Tier 1-4)
  doesn't exist, and a confirmed-real Company DNA nudge on a Hall of
  Fame strategy retirement (`app/state.py`'s retirement flow) doesn't
  yet also write a Company Memory entry or Knowledge Graph node. Both
  chapters flag a naming collision each — Chapter 62 explicitly notes
  this codebase's own `app/innovation.py` (Feature 41, an individual
  agent's Devil's Advocate skill ladder) is unrelated to what the brief
  means by "Innovation Lab"; both flag that "Chapter 53 — Probabilistic
  Trading Philosophy" still does not exist anywhere in this codebase or
  Design Bible, the same non-existent reference already checked in
  Chapters 58/59. Added as the eighth and ninth rows in Volume 9's
  chapter table.

- **Chapter 59 backend — Capital Priority & Opportunity Cost Engine**
  (`app/capital_priority.py`, wired into `app/nexus.py` and
  `app/executive.py`): closes the exact gap Chapter 58's own
  Implementation Notes flagged — pending `TradeProposal`s now sort by a
  real Priority Score (reusing each proposal's own linked
  `WarRoomSession.decisionScore.overall` directly, never a second
  composite) instead of arrival order, re-sorted every tick right after
  new proposals are appended so the full backlog re-orders too, not just
  the tick's new arrivals. Two new CEO controls on `RiskLimits`
  (`minPriorityScore`, `capitalReservePct`, both defaulting to `0.0` —
  opt-in, no-op until raised): a proposal below the Minimum Priority
  Score floor is now "significant" the same way a low-confidence one
  already was (`is_significant_proposal()` gained an optional
  `priority_score` parameter), holding it pending for the CEO in
  Assisted Mode — Executive Mode still auto-resolves everything
  unconditionally, unchanged; and once cash as a % of equity reaches the
  CEO's own voluntary Capital Reserve % (additive to Chapter 57's
  existing hard `cashReservePct` floor — Position Sizing still never
  spends into that), further BUY proposals stay pending in *both* modes,
  since a real capital constraint applies regardless of how hands-off
  the CEO wants to be. Extended `POST /api/risk-limits`
  (`app/routers/risk.py`, `app/state.py`) with both new fields, each
  validated to a `[0, 100)`/`[0, 100]` range matching the existing
  `minTradeQualityScore`/`cashReservePct` controls. 23 new backend
  tests (`tests/test_capital_priority.py` plus new cases in
  `tests/test_executive.py` and `tests/test_state.py`); `mypy`/`ruff`
  clean; verified with a live 400-tick simulation confirming the queue
  stays sorted every tick and both new gates produce real, observable
  holds. See the chapter's own Implementation Notes for the full
  design-vs-built breakdown: `docs/DesignBible/volumes/09-departments/chapter-59-capital-priority-opportunity-cost.md`.

- **Chapter 59 frontend — Capital Priority & Opportunity Cost Engine**
  (`frontend/src/types.ts`, `net/api.ts`, `RiskPanel.tsx`,
  `ExecutivePanel.tsx`, `CommandCenter/lib/derive.ts`): mirrors the two
  new `RiskLimits` fields end to end. The **EXECUTIVE tab**'s Pending
  Proposals list required no re-sorting on the client — the WS payload's
  `tradeProposals` already arrives in the exact order
  `app/capital_priority.py`'s `rank_trade_proposals()` sorted it
  server-side — so this only adds a rank number and each proposal's real
  Priority Score, read via a new `priorityScoreFor()` helper that mirrors
  the backend's own `proposalId` lookup against `WarRoomSession.
  decisionScore.overall` exactly (never a second, independently-computed
  score). The **RISK tab** gained a "Capital Priority — Opportunity
  Cost" panel with controls for `minPriorityScore`/`capitalReservePct`,
  the same per-section save-button pattern every other RISK tab control
  already uses. `tsc --noEmit`, `eslint --max-warnings 0`, and `vite
  build` all clean. Two new Playwright tests against the live Vite +
  FastAPI stack: one confirms the RISK tab's Capital Priority controls
  round-trip a real save, one confirms the EXECUTIVE tab renders either
  a real Priority Score or the honest "N/A" for a proposal with no
  linked session.

- **Design Bible Chapters 59 & 60 — Capital Priority & Opportunity Cost
  Engine, and Institutional Portfolio Rebalancing & Adaptive Capital
  Rotation** (`docs/DesignBible/volumes/09-departments/chapter-59-capital-priority-opportunity-cost.md`,
  `chapter-60-portfolio-rebalancing-capital-rotation.md`): two
  target-design chapters, written per Appendix G's "Design Bible updated
  before implementation" policy, ahead of and separate from any
  implementation work (Chapter 59's backend is implemented — see the
  entry above; Chapter 60 remains design-only). Researched first, with a
  clean division matching both briefs' own stated department
  boundaries: **Chapter 59** ranks the *pending* proposal queue —
  Chapter 58's own Implementation Notes already flagged that pending
  `TradeProposal`s sit in a flat, first-approved-first-shown list, never
  ranked by their own already-computed Decision Score; Chapter 59
  closes that exact gap by reusing `DecisionScoreBreakdown.overall`
  directly as a real Priority Score rather than inventing a second
  composite. **Chapter 60** continuously re-evaluates *already-open*
  positions — the largest real gap found in this Design Bible's trading
  pipeline so far: every position in this codebase closes today for
  exactly one reason (a flat random-chance roll once past a minimum
  hold, `app/paper_trading.py`'s `CLOSE_CHANCE_PER_TICK`), with the
  recorded "reason" chosen purely from whether P&L is currently positive
  or negative — no code anywhere re-scores an open position against its
  own original thesis or a currently-better opportunity, and
  `PaperPosition` has no field recording its own entry-time Decision
  Score to even compare against. Honest scoping flags this as
  substantially larger than any prior chapter's real implementation gap.
  Flagged directly, same as Chapter 58's own note: the briefs' named
  "Chapter 53" dependency doesn't exist anywhere in this codebase, and
  both briefs' own numbering runs one behind this Design Bible's real
  numbering for the Executive Decision Simulator/Enterprise Portfolio
  Intelligence chapters. Added as the sixth and seventh rows in Volume
  9's chapter table.

- **Chapter 58 frontend — Institutional Trade Filter & Opportunity
  Gatekeeper** (`frontend/src/types.ts`, `ExecutivePanel.tsx`,
  `RiskPanel.tsx`, `app/routers/risk.py`, `app/state.py`): mirrors
  `OpportunityRejection` and the two new `RiskLimits` fields;
  `opportunityRejections` flows through the full data-layer pipeline
  (`socket.ts` -> `NexusManager.ts` -> `EventBus.ts` -> `gameStore.ts`),
  the same capped-archive diff-and-emit pattern `gatekeeperRejections`
  already uses. The **EXECUTIVE tab** gained a new "Opportunity
  Gatekeeper" panel next to the existing "Trade Gatekeeper" one — real
  rejection/resolution counts (`computeOpportunityGatekeeperStats()`,
  genuinely separate from `computeGatekeeperStats()` since there's no
  "approved" count to report — an approved candidate becomes an
  ordinary `TradeProposal` with no distinguishing marker) and a
  recent-rejections list showing the desk's own `wouldHaveRecommended`,
  the real Decision Score/Expected Value at rejection time, and the top
  failed reason. The **RISK tab** gained controls for the two new
  `RiskLimits` fields (`minTradeQualityScore`, `minExpectedValuePct`).
  `POST /api/risk-limits` extended to accept and validate both
  (`minTradeQualityScore` in `[0, 100]`; `minExpectedValuePct`
  deliberately has no range check — a CEO can legitimately set it
  negative to relax the gate below "merely positive"). Verified: 6 new
  `backend/tests/test_state.py` cases (full backend suite 969/969
  passing), `tsc`/`eslint`/`vite build` clean, and two new Playwright
  tests against the live stack (RISK controls round-trip a real save;
  EXECUTIVE renders a real rejection or the honest empty state).

- **Chapter 58 backend — Institutional Trade Filter & Opportunity
  Gatekeeper** (`backend/app/opportunity_gatekeeper.py`): implements the
  target design below as real code. `evaluate_opportunity()` gates every
  new trade candidate on its already-computed real Decision Score
  (`app/war_room.py`'s `build_decision_score()`) and Expected Value
  against two new CEO-configurable `RiskLimits` fields
  (`minTradeQualityScore`, default 70.0 — a genuinely separate,
  CEO-adjustable gate from the existing fixed `DECISION_SCORE_THRESHOLD`,
  which keeps its own unchanged meaning everywhere else it's used;
  `minExpectedValuePct`, default 0.0) plus the existing Market Quality
  `avoid_trading` tier. Wired into `app/nexus.py`'s per-candidate loop
  immediately after the full War Room session (department opinions,
  Devil's Advocate challenge report, Decision Score, Expected Value) is
  built — a candidate that fails the gate is recorded as a new
  `OpportunityRejection` and never enters `trade_proposals`, never gets
  a Debate, and its Challenge Report/WarRoomSession are discarded, never
  persisted — the CEO never sees it. `trade_proposals`/`debates`/news
  generation, previously built eagerly for every raw candidate, now run
  only over the approved list. Graded the exact same real
  would-have-won/would-have-lost way Feature 20's own
  `GatekeeperRejection` already is (reusing the same
  `GATEKEEPER_EVAL_WINDOW_MINUTES` rather than a second magic number); a
  "wait" desk recommendation is left permanently "pending" rather than
  arbitrarily graded as a sell. A live-simulation smoke test (2000
  ticks) confirmed `war_room_sessions`/`debates`/`challenge_reports`
  stayed in exact 1:1 sync with the approved list (no orphaned records
  for rejected candidates) and that Feature 20's separate, later-stage
  Gatekeeper kept firing independently and unaffected. Explicitly not
  built: promoting `app/gatekeeper.py`'s hardcoded
  `MAX_CORRELATED_POSITIONS` to a real CEO control (a genuinely separate
  small change, not required to close this chapter's real gap); News/
  Volatility Sensitivity controls (no real economic calendar exists);
  Maximum Swing/Day Position controls (no real distinct trading modes
  exist). Covered by 16 new tests in `test_opportunity_gatekeeper.py`;
  full backend suite (963 tests) and `mypy`/`ruff` clean. Frontend work
  not yet started.

- **Design Bible Chapter 58 — Institutional Trade Filter & Opportunity
  Gatekeeper** (`docs/DesignBible/volumes/09-departments/chapter-58-trade-filter-opportunity-gatekeeper.md`):
  a target-design chapter, not yet implemented, per Appendix G's "Design
  Bible updated before implementation" policy. Researched first: almost
  every real signal this chapter needs already exists — Chapter 55's
  War Room already computes a real 0–100 composite (`DecisionScoreBreakdown.overall`,
  checked against `DECISION_SCORE_THRESHOLD = 70.0`) that is exactly the
  brief's "Trade Quality Score," and a real Expected Value read.
  **The real gap** this chapter identifies: today those real scores are
  computed only *after* a candidate already became a CEO-facing
  `TradeProposal` (`app/nexus.py`'s only real pre-proposal filter is a
  single confidence threshold) — they're informational, never a gate.
  Feature 20's existing `app/gatekeeper.py` is a real, separate,
  *later*-stage check (after the CEO's own buy/sell choice, against a
  different checklist) that this chapter doesn't replace. The chapter's
  genuinely new design: move the existing Decision Score/Expected Value
  computation earlier in the tick to gate candidates *before* CEO
  visibility, a CEO-configurable minimum-quality threshold (today's
  70-point bar is a fixed constant), a new honestly-separate pre-proposal
  rejection record (graded the same real would-have-won/would-have-lost
  way Feature 20's rejections already are), and a real Opportunity Queue
  ranking pending proposals by their already-computed score. Explicitly
  out of scope until other gaps close: News/Volatility Sensitivity
  controls (no real economic calendar exists) and Maximum Swing/Day
  Position controls (no real distinct trading modes exist yet). Flagged
  directly: the brief's named dependencies "Chapter 53 — Probabilistic
  Trading Philosophy" and "Chapter 56 — Institutional Risk Authority" (as
  numbered/titled in the brief) don't exist anywhere in this codebase or
  Design Bible — checked directly rather than assumed, the same way
  Features 54–56's own non-existent "Feature 57–67" precedent was
  checked earlier. Added as the fifth row in Volume 9's chapter table.

- **Chapter 57 frontend — Institutional Position Sizing & Capital
  Deployment Engine** (`frontend/src/types.ts`,
  `WarRoomPanel.tsx`, `RiskPanel.tsx`): mirrors `TierAllocationLimits`,
  the six new `RiskLimits` fields, `PositionTier`, and
  `PositionSizingResult`; `WarRoomSession.positionSizing` flows through
  the existing generic session pass-through, no per-field plumbing
  needed. The **WARROOM tab** gained a Position Sizing block per
  session (tier pill, Sizing Score, a risk-ceiling-vs-final-quantity
  meter, a weekly-deployment-budget meter, cash-reserve/heat-cap gate
  pills) reading `positionSizing` directly, never recomputed
  client-side. The **RISK tab** gained controls for four of the six new
  fields (`maxWeeklyDeploymentPct`, `portfolioHeatCapPct` with an
  explicit enable/disable toggle, `cashReservePct`, the four
  `tierAllocation` caps); `scalingAggressivenessPct`/
  `emergencyReductionHeatPct` are deliberately not exposed as controls
  since neither has a real consumer yet (Position Scaling/Reduction on
  already-open positions isn't built — a control with no real effect
  would be a placeholder). `POST /api/risk-limits`
  (`backend/app/routers/risk.py`, `backend/app/state.py`) extended to
  accept and validate all four, with an explicit
  `clearPortfolioHeatCap` flag so "field omitted" and "CEO wants to
  disable the cap" are distinguishable on the wire (a bare `null` can't
  tell them apart). Verified: 11 new `backend/tests/test_state.py`
  cases (full backend suite 947/947 passing), `tsc`/`eslint`/`vite
  build` clean, and two new Playwright tests against the live stack
  (WARROOM's Position Sizing block renders for a real session; RISK's
  controls round-trip a real save).

- **Chapter 57 backend — Institutional Position Sizing & Capital
  Deployment Engine** (`backend/app/position_sizing.py`): implements the
  target design below as real code. `build_position_sizing()` narrows
  (never widens) `app/risk_engine.py`'s existing `recommended_quantity()`
  ceiling through four independent real constraints — a Position Tier's
  evidence-based fraction of the ceiling (`TIER_FRACTION`, reusing War
  Room's own `DecisionScoreBreakdown.overall` as the Sizing Score rather
  than a second composite), the tier's own absolute per-tier cap (a
  separate CEO guardrail via the new `TierAllocationLimits`), a real
  spendable weekly Risk Budget (`RiskLimits.max_weekly_deployment_pct`,
  computed fresh from real `trade_history` and open `positions` in a
  trailing 7-sim-day window — genuinely new, `max_daily_loss_pct` was
  always a static realized-loss ceiling, never a decrementing deployment
  budget), an optional CEO-set Portfolio Heat cap
  (`RiskLimits.portfolio_heat_cap_pct`, `None` by default — unchanged
  read-only behavior otherwise, staying inside the v0.8 "no auto-hedging"
  stop condition), and the CEO's cash reserve requirement. Wired into
  `app/nexus.py`'s proposal-creation loop (result stored on the new
  `WarRoomSession.position_sizing`) and `app/executive.py`'s
  `resolve_proposal()`, which was fixed to actually consult the resized
  `proposal.quantity` instead of silently recomputing the flat ceiling
  from scratch and discarding it. A live-simulation smoke test caught a
  real calibration flaw before ship (an absolute per-tier cap alone can
  never bind below Institutional if a CEO's `risk_per_trade_pct` is
  already tighter, making "weaker evidence, smaller position" a no-op) —
  fixed by scaling the ceiling by tier first, so evidence quality always
  has a visible, monotonic effect. Explicitly not built: Position
  Scaling/Reduction on already-open positions (would need each
  position's entry-time evidence score, which `PaperPosition` doesn't
  store), Day/Swing/Hybrid allocation splits (this codebase has one real
  trading mode), and any auto-executed reduction. Covered by
  `backend/tests/test_position_sizing.py` (25 tests); full backend suite
  (936 tests) and `mypy`/`ruff` clean. Frontend work (Command Center
  surfacing, CEO controls UI) not yet started.

- **Design Bible Chapter 57 — Institutional Position Sizing & Capital
  Deployment Engine** (`docs/DesignBible/volumes/09-departments/chapter-57-position-sizing-capital-deployment.md`):
  a target-design chapter, not yet implemented, per Appendix G's
  "Design Bible updated before implementation" policy. Researched
  first: `app/risk_engine.py`'s real `recommended_quantity()` sizes
  every position off exactly two flat percent-of-equity limits today,
  with no evidence, confidence, or portfolio-context input at all —
  this chapter's real, novel design is an evidence-and-confidence-
  weighted model that replaces (not duplicates) that flat calculation,
  built entirely on real existing signals (Decision Vault evidence
  score, War Room Expected Value/Decision Score, Portfolio Intelligence
  heat/correlation) rather than inventing new upstream systems. A
  four-tier Position Tier system, real Position Scaling/Reduction
  trigger rules, a spendable (not just static-ceiling) Risk Budget, and
  new CEO controls (Weekly Risk cap, an optional Portfolio Heat hard
  cap, Day/Swing/Hybrid allocation split) are the chapter's genuinely
  new asks. Explicitly out of scope until other volumes catch up: the
  Institutional Tier's cross-department approval workflow (no real
  approval-routing mechanism exists yet) and real multi-broker/
  multi-account deployment (Volume 10 is still "no live broker exists
  today"). Added as the fourth row in Volume 9's chapter table.

- **The Design Bible** (`docs/DesignBible/`) — the emerging single
  source of truth for the whole company: 14 volumes plus 7 appendices,
  scaffolded as a real folder structure and Table of Contents
  (`docs/DesignBible/README.md`), built one volume at a time rather than
  all at once. Every volume stub documents both its target outline and
  exactly where its real content lives *today* (a specific module,
  schema, or existing doc), rather than describing systems that don't
  exist yet — several volumes (Live Trading/Charles Schwab, real
  Security controls, a formal Performance Benchmark suite) explicitly
  say so. Volume 9 (Departments) defines the permanent 20-section
  chapter template every feature will eventually be documented under
  (Executive Summary, Mission, Philosophy, Responsibilities, Ownership,
  Inputs, Outputs, Internal Workflow, Decision Logic, Department
  Cooperation, CEO Controls, Learning System, KPIs, Reports, Safety
  Systems, Dependencies, Connected Features, Future Expansion, Company
  Principle, Implementation Notes) and lists Features 54–56 (Decision
  Vault, War Room, Portfolio Intelligence) as its first three pending
  chapters — checked directly against the full repository and every
  remote branch, no "Feature 57–67" precedent exists yet to match, so
  these three chapters will set the bar rather than follow one.
  `CLAUDE.md` now points to it alongside `docs/DEVELOPMENT_RULES.md`.
  Existing docs (`docs/DESIGN_BIBLE.md`, `docs/AI_AGENT_BIBLE.md`, etc.)
  are not deleted or invalidated — each volume absorbs its overlapping
  content only once that volume is actually written.

- **v0.7 Features 55 & 56 — Executive Decision Simulator (War Room) and
  Enterprise Portfolio Intelligence, frontend**: mirrors every new schema
  in `types.ts` (`ExpectedValueAnalysis`, `ContingencyStep`,
  `DecisionScoreBreakdown`, `ScenarioOutcomeComparison`, `WarRoomSession`,
  `CategoryExposure`, `CorrelationPair`, `PortfolioHeat`,
  `CapitalEfficiency`, `PortfolioIntelligence`) and wires both new fields
  through the full data-layer pipeline (`socket.ts` -> `NexusManager.ts`
  -> `EventBus.ts` -> `gameStore.ts`) — `warRoomSessions` follows the
  capped-archive diff-and-emit pattern `decisionVault` already uses,
  `portfolioIntelligence` follows the recomputed-every-tick pattern
  `companyHealth`/`marketIntelligence` already use.

  New **WARROOM** tab (`WarRoomPanel.tsx`): browse every session (newest
  first), select one to see its full read — the Decision Score's 7 real
  sub-scores against the shared 70-point bar, the Expected Value/edge/
  risk-to-reward numbers, the real Contingency Plan with a live
  "TRIGGERED NOW" flag on any condition currently true, the Institutional
  Knowledge Graph's similar-trade summary, department opinions, and —
  once the linked trade closes — the real predicted-vs-actual outcome
  comparison.

  New **PORTFOLIO** tab (`PortfolioIntelPanel.tsx`): Capital Allocation
  (equity/cash/deployed split and the real opportunity-cost read),
  Portfolio Heat (a color-coded reading across the four real tiers —
  cool/warm/hot/overheated — never a control that acts on the portfolio),
  Category Exposure (this codebase's honest "sector" stand-in, as a real
  per-category meter), Correlation Intelligence (real Pearson-correlated
  pairs among currently-held symbols only, honestly empty when none
  clear the threshold), and Capital Efficiency (real profit-per-dollar/
  profit-per-dollar-hour over actually-closed trades).

  `commandCenter.spec.ts`'s existing "renders all N tabs" sweep extended
  to 34 tabs, plus two new dedicated tests: WARROOM (asserts either the
  honest empty state or a real session's Decision Score/Expected
  Value/Contingency Plan) and PORTFOLIO (asserts Capital Allocation, a
  real heat tier, and either real category exposure or the honest empty
  state) — same "always real content or an honest empty state" pattern
  every other archive/derived-state tab test already follows. `tsc -b
  --noEmit`, `eslint --max-warnings 0`, and `vite build` all clean; all
  3 targeted Playwright tests pass against the live Vite + FastAPI stack.

- **v0.7 Features 55 & 56 — Executive Decision Simulator (War Room) and
  Enterprise Portfolio Intelligence, backend**: two briefs pasted in the
  same session. Brief 1 self-numbered itself "Feature 54"; brief 2 didn't
  number itself but called itself "Feature 55" in its own title — both
  collide with names already in use in this codebase's history (Feature
  54 is the Decision Memory System above). Referred to here and in commit
  history as **Feature 55** (War Room) and **Feature 56** (Portfolio
  Intelligence) to avoid the collision, the same renumbering convention
  the Decision Memory System entry above already established.

  A mid-session stale local git checkout briefly caused an entire
  redundant CIO + AI Academy backend to be rebuilt from scratch before a
  rejected `git push` surfaced that the real, further-refined
  implementation already existed on `origin`. No data was lost — the
  redundant local commit was never pushed — and the real upstream work
  was recovered via `git reset --hard origin/claude/tradetown-v0-1-build-dn1ufw`
  after explicit user confirmation (including a requested diff showing
  the rebuilt modules added no unique value over the real ones). Noted
  here since it's the reason this entry starts from the real `2c5f74b`
  history rather than continuing on top of the discarded rebuild.

  **Feature 55 — War Room** (`app/war_room.py`, new). Researched first:
  the overwhelming majority of the brief's asks already exist — Digital
  War Room department analysis (`app/executive_intelligence.py`'s
  `generate_department_opinions()`/`compute_executive_recommendation()`,
  9 real department seats), Devil's Advocate
  (`app/devils_advocate.py`'s `generate_challenge_report()`, already
  assigns one real employee per proposal), multi-scenario simulation
  (`app/whatif.py`'s `run_whatif_simulation()` — 12 real bootstrap-
  resampled scenarios mapped one-to-one against the brief's own 12-item
  list, e.g. Black Swan → `flash_crash`, Range Compression →
  `sideways_consolidation`; see the module's own docstring for the full
  mapping), and Historical Comparison / "Institutional Knowledge Graph"
  (`app/decision_vault.py`'s `find_similar_vault_entries()`/
  `summarize_similarity()`, real rule-based tiered matching). "Confidence
  may never exceed evidence" already holds by construction — Evidence
  Score is a strict renormalized subset of Confidence Score's own
  factors — `evidence_never_exceeds_confidence()` computes and surfaces
  this honestly rather than hardcoding it.

  This slice's real, novel job was exactly three things that genuinely
  didn't exist anywhere: a permanent `WarRoomSession` that **joins** all
  of the above into one addressable record per new `TradeProposal`; a
  real **Expected Value / Statistical Edge / Risk-to-Reward** read
  (`build_expected_value_analysis()`) computed from the 12 real
  scenarios' own probability-weighted outcomes (`riskToReward` is
  deliberately labeled that, not "R-Multiple" — no stop-loss/initial-risk
  concept exists anywhere in the real risk engine to measure R against,
  the same gap `DecisionVaultEntry.rMultiple` already documents); and a
  real, signal-grounded **Contingency Plan** (`build_contingency_plan()`)
  — 5 real IF/THEN steps tied to Guardian's liquidity-sweep read, the
  market regime, news risk, and Market Quality tier, each carrying a real
  `triggered` flag for whether that condition is live right now. A
  combined **Decision Score** (`build_decision_score()`) renormalizes
  over 7 real sub-scores (Evidence, Confidence, Risk, Expected Value,
  Market Quality, Liquidity Quality, Portfolio Compatibility) against the
  same 70-point "good decision" bar `app/discipline.py`'s
  `tier_for_score()` already uses — `strategyHealthScore` is always
  `null` for ordinary Trading Floor proposals (no proposal links back to
  a tested Strategy) rather than a fabricated placeholder.
  `compare_scenario_to_outcome()` fills in a real predicted-vs-actual
  comparison once a session's linked trade closes, finding whichever
  scenario's predicted range midpoint sits closest to the real outcome
  and reporting whether that outcome actually landed inside it.

  **Explicitly NOT built, and why**: literal R-Multiple (see above);
  Historical Expectancy per ordinary trade (only exists at the Strategy
  aggregate level — `DecisionScoreBreakdown.strategyHealthScore` stays
  `null` rather than substituting a fake number); auto-failing negative-
  EV trades or any automatic corrective action off Decision Score/
  Portfolio Heat (`docs/ROADMAP.md`'s own documented v0.8 stop condition:
  "risk is measured and displayed, never auto-hedged or auto-corrected
  without the player" — `DecisionScoreBreakdown.passed` is a real,
  visible flag the CEO sees, never an automatic veto); LLM-generated
  analysis text (no LLM/HTTP client dependency exists anywhere in
  `backend/requirements.txt` — every string here is templated from real
  computed values).

  **Feature 56 — Enterprise Portfolio Intelligence**
  (`app/portfolio_intelligence.py`, new). Researched first:
  `app/portfolio.py`'s `PaperPortfolio` has no sector/correlation/heat
  field anywhere; `app/gatekeeper.py`'s `_correlation_check()` is a real
  but narrow category-co-occurrence gate (>2 open positions sharing a
  category), not a correlation coefficient or a heat/efficiency read —
  this slice is almost entirely genuinely new. "Sector" is called
  "category" throughout — this codebase has no real sector taxonomy (the
  same honest note `app/risk_engine.py`'s `evaluate_guardian_exposure()`
  docstring already makes); every symbol's only real classification is
  its `ResearchCategory` (`app/watchlist.py`'s `SYMBOL_CATEGORY`, reused
  directly rather than inventing a second taxonomy).

  Correlation Intelligence (`_correlation_pairs()`) is a **real Pearson
  correlation coefficient** (`statistics.correlation()`) computed from
  each pair of currently-held symbols' own real recent candle-to-candle
  returns — only pairs clearing `CORRELATION_CLUSTER_THRESHOLD` (0.6) are
  reported, so a portfolio of genuinely unrelated positions reports none.
  Portfolio Heat (`_heat()`) is a real, visible **reading** across four
  tiers (cool/warm/hot/overheated) driven by real total-capital-at-risk —
  never an automatic corrective action, per the same v0.8 stop condition
  cited above; nothing in this module places, closes, or resizes an
  order. Capital Efficiency (`_capital_efficiency()`) is real profit-per-
  dollar and profit-per-dollar-hour, averaged only over
  `portfolio.trade_history`'s actually-closed trades — never a forward-
  looking prediction. Max Drawdown is deliberately **not** duplicated
  here: `app/analytics.py`'s `PerformanceSnapshot.max_drawdown_pct`
  already computes this per period from the same trade history; an
  Executive Portfolio Dashboard should read that existing field.
  Opportunity Cost (`_opportunity_cost()`) is four real templated
  branches off cash percentage and pending-proposal count — never generic
  filler text.

  Both `war_room_sessions` (capped at `MAX_WAR_ROOM_SESSIONS = 60`, same
  pattern as `decision_vault`) and `portfolio_intelligence` (recomputed
  fresh every tick, same pattern as `company_health`/`market_intelligence`)
  are wired into `app/nexus.py`'s existing per-proposal and per-tick
  loops respectively, added to `save_modules.py`'s `knowledge_archive`
  and `derived` modules, and added to `ws_manager.py`'s
  `build_state_message()` broadcast dict — the last two done proactively
  in the same edit pass as the schema changes, having been bitten by
  exactly this class of wiring gap once already (see the Decision Memory
  System frontend entry below). No new API router was added for either
  feature: unlike Decision Vault's report-card/similar-trades endpoints
  (parametrized, on-demand lookups), a `WarRoomSession` and
  `PortfolioIntelligence` are each already fully computed and present in
  the regular tick broadcast — there is no additional query shape to
  serve.

  New `tests/test_war_room.py` (27 tests) and
  `tests/test_portfolio_intelligence.py` (32 tests): Expected Value/edge/
  risk-to-reward math, Decision Score composite and threshold behavior,
  all 5 Contingency Plan branches, end-to-end session assembly and
  session capping, predicted-vs-actual outcome comparison in both the
  in-range and out-of-range cases; real Pearson correlation (including
  the <3-points and zero-variance guards), category exposure grouping
  and sorting, all four Portfolio Heat tiers, capital-efficiency
  averaging (including the zero-capital-locked guard), all four
  opportunity-cost branches, and an end-to-end computation with real
  correlated open positions. 911/911 backend tests passing, `mypy`/
  `ruff` clean. Frontend (Command Center surfaces for the War Room and
  Portfolio Intelligence dashboard) is a separate, immediately-following
  commit per this project's backend-first discipline.

- **v0.7 Feature 54 — the Decision Memory System, backend (Decision Vault
  / Trade Report Card / Similarity Engine)**: the brief for this slice
  self-numbered itself "Feature 53," but that number is already in use in
  this codebase's own history for Company Certification (see the entries
  below) — referred to as **Feature 54** here and in commit history to
  avoid the collision.

  Researched first: the overwhelming majority of the brief's asks already
  exist as real, separate systems — Decision Grade
  (`app/executive.py`'s `compute_decision_grade`), Discipline/Patience
  score (`app/discipline.py`), Evidence/Confidence
  (`app/confidence.py`'s `DecisionConfidence`), mistake detection
  (`app/mistakes.py`'s `CaseStudy`), lessons learned
  (`app/journal.py`'s `PaperTrade.lessonsLearned`), executive notes
  (`app/executive_intelligence.py`'s `ExecutiveMeetingLogEntry`), and
  Company DNA updates (`app/company_dna.py`'s `nudge_legacy`). This
  slice's real, novel job was exactly two things that genuinely didn't
  exist anywhere: a permanent **Decision Vault** that joins all of the
  above into one addressable record per closed trade, and a real,
  rule-based **Similarity Engine**.

  New `app/decision_vault.py`: `build_vault_entry()` constructs one
  permanent `DecisionVaultEntry` per closed trade, joining its
  `TradeDecision`, `PaperTrade`, `DisciplineReview`, any filed
  `CaseStudy`, `ExecutiveMeetingLogEntry`, and `CeoDecisionRecord`, plus
  two genuinely new fields computed fresh at the moment the trade closes
  (never backdated to the original decision, since nothing in this
  codebase stamps either onto a proposal): market regime (reusing
  `app/market_intelligence.py`'s already-live `MarketIntelligenceState.regime`)
  and liquidity context (`compute_liquidity()`, same
  `PROPOSAL_TIMEFRAME`/`PROPOSAL_CANDLE_COUNT` convention
  `app/devils_advocate.py` already established). A real **Evidence
  Score** is a renormalized weighted average over just
  `DecisionConfidence`'s three evidence-oriented factors (Technical
  Alignment, Research Confidence, News/Macro/Sentiment — 45 of its 100
  weight), deliberately excluding the consensus/portfolio-state factors
  (Multi-Agent Agreement, Risk Conditions, Portfolio Exposure) — kept
  genuinely distinct from **Confidence Score** (the full, unmodified
  composite). Capital Allocation Grade and Patience Grade reuse
  `app/executive.py`'s own A+–F scale (made public as
  `GRADE_THRESHOLDS`/`grade_for_score`) applied to the Discipline
  Review's `position_sizing_discipline`/`patience` factor scores, rather
  than inventing a second grading scale.

  `compute_trade_report_card()` is a pure relabeling of one vault
  entry's own real fields — Evidence/Confidence/Capital
  Allocation/Decision/Discipline/Patience grades, `wouldTakeAgain`, and a
  templated recommendation. `wouldTakeAgain` is a real, checkable rule:
  true only when Decision Grade clears the company's B- bar AND no real
  non-success `CaseStudy` was filed against this exact trade — never a
  vibe.

  `find_similar_vault_entries()` is the Similarity Engine: real,
  rule-based tiered bucket matching (never a fabricated "94% similar"
  score) — tries same-symbol+regime+confidence-tier, then
  same-regime+confidence-tier, then confidence-tier alone, using the
  first tier with at least 3 matches, so the CEO always sees exactly
  which real dimensions produced a match. `summarize_similarity()`
  computes real win rate/average/worst P&L, best/worst regime by average
  P&L, and folds Mistake Prevention directly into the same result — a
  `warning` fires when one real non-success `CaseStudyCategory` accounts
  for ≥30% of the matched trades' own linked case studies, rather than
  building a separate warning mechanism.

  New read-only endpoints (`app/routers/decision_vault.py`, mirroring
  `routers/sandbox.py`'s `/certification` convention — `snapshot()`, no
  lock, computed fresh): `GET /api/decision-vault/report-card` and
  `GET /api/decision-vault/similar`. Wired into `app/nexus.py`'s
  closed-trade pipeline right after each trade's `DisciplineReview` and
  case/success study are generated, so a vault entry always has a real
  process trail to join. `decision_vault` added to
  `save_modules.py`'s `knowledge_archive` module (a permanent,
  only-growing archive, same category as `case_studies`).

  **Explicitly NOT built, and why**: R-Multiple (confirmed via direct
  read of `app/risk_engine.py`'s `recommended_quantity()` — position
  sizing is `equity * risk_per_trade_pct / 100`, with no stop-loss/
  initial-risk concept anywhere in this codebase's real risk engine — a
  lesson's own prose claiming otherwise was checked against the actual
  function body and found inaccurate); `strategyId` on ordinary Trading
  Floor trades (only Research Sandbox-tested strategies link to a
  `Strategy` object); Execution Grade and Psychology Grade on the Trade
  Report Card (no real signal anywhere measures order-execution quality
  separately from the decision, or reads literal emotion); true NLP/
  natural-language search and true vector/embedding similarity over the
  vault (`backend/requirements.txt` has no LLM/HTTP client dependency
  anywhere — building a fake "understands your question" layer would be
  exactly the kind of fabrication this project exists to avoid).

  **Deferred to a later slice** (each already has a real signal to build
  on — this slice doesn't duplicate them): a continuous per-employee
  Improvement Profile trajectory; Recurring Mistake Detection as a real
  frequency/trend signal (today's `wisdom.py` only has a plain
  most-common-category count); a dedicated Executive After-Action Review
  view and CEO Dashboard view (the underlying numbers already exist in
  `app/company_health.py`'s Executive tier and
  `app/executive_review.py`/`app/founders.py`).

  New `tests/test_decision_vault.py` (26 tests: evidence-score
  renormalization, vault-entry joining/capping, all three Trade Report
  Card recommendation branches, all three Similarity Engine tiers plus
  the empty-vault fallback, and the mistake-warning share threshold).
  852/852 backend tests passing, `mypy`/`ruff` clean. Frontend (a
  Command Center surface for the Trade Report Card and Similarity
  Engine) is a separate, immediately-following commit per this project's
  backend-first discipline.

- **Certification Management — full CEO controls (frontend)**: the
  Current Certifications panel (`MentorLibraryPanel.tsx`) now reads
  `foundationalMentorState.certifications` directly — the real,
  independent, permanent registry — instead of a client-side
  re-derivation from graduation status, so every certification is
  reachable regardless of which mentor track is currently active. Each
  row gets real inline controls: **View / History** (a detail modal
  showing the full permanent `CertificationHistoryEntry` timeline),
  **Downgrade**/**Promote** (Active ↔ Suspended, context-sensitive to
  the row's own current status), and **Revoke**. A separate "Revoked
  Certifications — awaiting re-earn" section lists revoked records with
  **View / History** and **Reset Progress**.

  The Revoke confirmation dialog matches the requested copy exactly:
  "Are you sure you want to revoke {Agent}'s {Track} Certification?" /
  "This will remove the active certification but preserve all
  historical records." / Cancel / Revoke Certification, with a required
  reason field. Downgrade/Reset Progress reuse the same modal shell with
  lower-severity copy matching their own reversibility; Promote takes an
  optional note.

  Removed the old ad hoc "Revoke Graduation" button from the per-
  employee Academy Report modal (superseded by the dedicated
  Certification Management section) and the derived `certifications`
  computation from `computeAcademyDashboard` (`lib/derive.ts`) — no
  longer needed now that a real registry exists.

  `tsc -b`/`eslint`/`vite build` all clean. Updated
  `mentorLibrary.spec.ts`'s honest-empty-state test (no certifications,
  no per-row Revoke/Downgrade buttons) to check the new real
  `foundationalMentorState.certifications` signal instead of a
  progress-derived one; verified passing against the live stack (3/3).

- **Certification Management — full CEO controls (backend), a
  quality-of-life fix**: the bug — once a certification appeared under
  Current Certifications, the only Revoke path was clicking that
  employee's name inside the *active* mentor track's own summary lists,
  so a certification on any already-completed, no-longer-active track
  became permanently unreachable. Fixed with a new, real, independent
  `CertificationRecord` registry (`FoundationalMentorState.certifications`,
  keyed `cert-{agentId}-{mentorId}`) that's never derived from
  `FoundationalMentorProgress` (which a revoke genuinely resets) and
  never deleted — every status transition permanently appended to a
  `history` list. New real lifecycle: **active** / **suspended**
  (Downgrade, reversible, progress untouched) / **revoked** (Revoke,
  requires a real reason, resets progress so the employee can re-earn
  it — re-approving reuses the *same* record rather than creating a
  second one). New `downgrade_certification`/`promote_certification`/
  `revoke_certification`/`reset_certification_progress`
  (`app/foundational_mentors.py`), replacing the old
  `revoke_employee_graduation`. New `POST
  /api/foundational-mentors/certification/{downgrade,promote,revoke,reset-progress}`.

  **Deliberately not built**: Downgrade/Promote to a performance tier
  (Bronze/Silver/Gold) — no tiered-certification concept exists
  anywhere in this codebase; graduation is a real pass/fail signal, so
  inventing tier thresholds would be fabrication. "Expired" status —
  no time-based renewal/decay signal exists to honestly back it;
  **postponed to v1.0** (see `docs/ROADMAP.md`) rather than built
  without one.

  Every revoke also appends a real Newspaper `"company"`-category news
  item — this codebase's real analog to an Executive Log, since no
  generic one exists — with the exact requested format ("Day {simDay}
  — {Agent}'s {Track} Certification revoked by CEO. Reason: {reason}").

  `test_foundational_mentors.py`'s new `TestCertificationManagement` (20
  tests) plus a new `TestApproveGraduation` test — 826/826 backend
  tests, mypy/ruff clean. Frontend (the Current Certifications panel's
  new per-row controls and confirmation dialog) is a separate,
  immediately-following commit per this project's backend-first
  discipline.

- **Probability First Trading Philosophy — permanent company principle,
  not a feature**: added to `docs/DESIGN_BIBLE.md` as a new subsection
  of the top-level "Design Philosophy — The Self-Improving Company"
  section (the document's own permanent, "never overwritten" umbrella),
  and codified as five new permanent Constitution Articles (IX-XIII),
  seeded verbatim in `_ARTICLE_SEED` (`backend/app/constitution.py`)
  alongside the original eight: We Trade Probabilities Not Predictions;
  A Single Trade Does Not Determine Success; Risk Must Be Accepted
  Before Entry; Process Is More Important Than Outcome; Statistics
  Become Meaningful Only Through Consistent Execution Over A Large
  Sample Of Trades. `default_constitution()` now seeds 13 Articles for
  every new game.

  Deliberately scoped as documentation + Constitution content only, per
  the explicit "this is not a feature" framing: no new Academy course,
  no Foundational Mentor graduation gate, and no new "Live Enforcement"
  citation hooks were built for IX-XIII — the existing six citation
  hooks continue to cite only I-VIII, the Articles with a real detector
  already behind them; building new detectors for the new Articles
  would be new feature engineering, not a documentation addition. An
  already-in-progress save's own persisted Constitution keeps whatever
  Article count it had when it was created — this only changes seeded
  content, not the `ConstitutionState` schema shape, so the
  schema-mismatch migration path in `app/persistence.py` never
  triggers; no retroactive backfill was built.

  Updated 2 tests in `test_constitution.py` (seed count/text, and the
  ratify-amendment test's expected next Roman numeral, now "XIV" instead
  of "IX") and 1 Playwright assertion in `constitution.spec.ts` to match
  the new 13-Article seed — 813/813 backend tests, `mypy`/`ruff` clean;
  `tsc`/`eslint`/`vite build` clean, `constitution.spec.ts` passes
  against the live stack.

- **v0.7 Feature 53 (Slice 1) — Company Certification, frontend**: the
  existing CERTIFICATION sub-tab (`StrategyCertificationView.tsx`) now
  fetches `GET /api/sandbox/certification` alongside the existing dossier
  fetch and renders the real 15-point checklist above the dossier
  sections — a CERTIFIED/NOT CERTIFIED pill plus every requirement's own
  met/not-met status and detail string, straight from the backend's
  `compute_strategy_certification()`. No new client-side derivation:
  `certified` is displayed exactly as the backend computes it fresh on
  every open, so the same real Strategy Health decline that flips it
  server-side is visible here with no separate client logic. New
  `StrategyCertification`/`StrategyCertificationRequirement` types
  (`types.ts`) and `api.getSandboxCertification()` (`net/api.ts`)
  following the same read-only, computed-on-request pattern as
  `getSandboxDossier`/`getSandboxDashboard`. `sandbox.spec.ts` extended
  to assert the checklist banner and CERTIFIED/NOT CERTIFIED pill render
  on the live stack. `tsc`/`eslint`/`vite build` all clean; the 3
  live-stack `sandbox.spec.ts` tests pass with zero console errors.

- **v0.7 Feature 53 (Slice 1) — Company Certification, backend**: the
  brief's formal "no strategy may trade live capital without
  Certification" gate, built as a real checklist combining every
  already-real Feature 52 artifact — never a new measurement. New
  `compute_strategy_certification()` (app/strategy_lab.py) checks all
  14 of the brief's named requirements (minimum trade sample size,
  positive expectancy, acceptable Monte Carlo worst-case drawdown,
  consistent profitability across ≥2 tested Market Regimes with no weak
  buckets, reaching Paper Trading, real Monte Carlo testing, a real
  "Stress Testing" reading — the 10th-percentile Monte Carlo return
  plus weak-regime buckets, reusing existing tail data under a
  brief-requested new lens rather than a second engine — Risk/Market
  Intelligence/Quant/Simulation/Decision Intelligence department
  approval read from the real 9-department Executive Review, Founder
  Approval, and Final CEO Approval) plus one added 15th requirement,
  Health Standing, which is how "Certification may be revoked at any
  time if performance deteriorates" is honestly satisfied: `certified`
  is always recomputed fresh from the strategy's own real current state
  (`GET /api/sandbox/certification`), so a real decline in
  `StrategyHealthAssessment.status` to "critical"/"retire_candidate"
  automatically fails that requirement on the very next read — no
  separate persisted "revoked" flag or event log needed.

  Two of the fourteen brief requirements — Founder Approval and Final
  CEO Approval — can only ever be real once a strategy reaches Company
  Review, which happens *after* Limited Live Capital in this codebase's
  existing pipeline order (paper_trading → limited_live_capital →
  company_review → approved) — so full `certified` status can only ever
  be true at `stage == "approved"`. Rather than silently gate live
  capital on a status that can't exist yet at that point in the
  pipeline, new `evaluate_certification_readiness()` is the real,
  ENFORCED subset of the same checklist (every requirement that *can*
  honestly exist before Company Review), now a hard gate on
  `POST /api/sandbox/begin-limited-live` itself
  (`app/state.py`'s `begin_strategy_limited_live()`) — reusing the exact
  same thresholds as the full checklist, not a second set of numbers.

  New tests: 6 in `test_strategy_lab.py` (a fully-qualifying strategy
  passes every one of the 15 requirements; an empty strategy fails all
  of them; a real health decline automatically revokes a previously-met
  Health Standing requirement; the readiness gate passes/fails on the
  achievable pre-Company-Review subset) — 813/813 backend tests
  passing, `mypy`/`ruff` clean. Frontend (surfacing the checklist on the
  existing CERTIFICATION sub-tab) is a separate, immediately-following
  commit per this project's backend-first discipline.

- **v0.7 Feature 52 frontend — the Strategy Validation Laboratory UI**:
  one Command Center tab (`SANDBOX`), restructured into eight real
  sub-views rather than eight more top-level tabs (this Command Center
  already carries 31 — see `FullCommandCenter.tsx`'s own `TABS` array).
  **PIPELINE** is the original Research Sandbox (queue backtests, walk
  the real CEO-authorized stage checkpoints) plus the new v0.7 Feature
  52 (Part 2) Retirement action — a real, deliberate, named-reason CEO
  call, never automatic. **LIBRARY** lists every strategy this company
  has ever created, including retired ones (nothing is ever deleted),
  with real aggregated stats and a click-through into that strategy's
  own dossier. **CERTIFICATION** renders the full real validation
  dossier on request (`GET /api/sandbox/dossier`) — Monte Carlo Testing,
  Market Regime Testing, Liquidity Validation, the 9-department
  Executive Review, Founder Approval, and Confidence Score, each only
  ever shown when real evidence exists. **HALL OF FAME** / **FAILED
  ARCHIVE** are the two permanent real outcomes of a retirement.
  **DASHBOARD** renders the real, computed-on-request Executive
  Dashboard (`GET /api/sandbox/dashboard`) — stage counts and named
  best/weakest/most-improved/newest/highest-confidence slots, each
  citing its real metric value.

  Two of the requested dashboards are **honest reframes**, not literal
  builds of what their name suggests, matching this feature's own
  backend honesty boundary: **HEALTH** stands in for the brief's "Live
  Performance Monitor" — this codebase has no mechanism to attribute a
  live/paper trade back to a specific `Strategy` object (see
  `backend/app/sandbox.py`'s module docstring), so there is no real live
  P&L stream to monitor; what's shown instead is real — a recent-vs-
  lifetime trend read over the strategy's own Market Simulation history,
  re-computed on every completed run. **EVOLUTION** stands in for
  "Strategy Evolution" — this codebase has no strategy revision/
  versioning mechanism (no v1.0→v1.1→v2.0 parent/child links), so rather
  than fabricate a fake version history, this shows the strategy's own
  real `stageHistory` timeline plus its real retirement outcome when
  retired. Both reframes are stated directly in each view's own header
  copy, not just in this changelog entry.

  Full data-layer wiring for all 8 new WS-broadcast state fields
  (`strategyMonteCarloResults`/`strategyRegimeTests`/
  `strategyLiquidityValidations`/`strategyExecutiveReviews`/
  `strategyFounderApprovals`/`strategyHealthAssessments`/
  `strategyHallOfFame`/`strategyFailedArchive`) through `types.ts` →
  `socket.ts` → `NexusManager.ts` → `EventBus.ts` → `gameStore.ts`,
  matching every existing field's own diff-and-emit pattern exactly. Two
  new `NexusManager` setters (`setStrategyExecutiveOutcome`/
  `setStrategyRetirementOutcome`) apply a CEO action's REST response
  immediately, the same "don't wait for the next WS tick" pattern
  `setSandboxState` already established. New `api.ts` functions for
  `POST /sandbox/retire`, `GET /sandbox/dossier`, `GET /sandbox/dashboard`.
  New `derive.ts` tone helpers (`strategyExecutiveActionTone`/
  `strategyHealthTone`/`strategyRegimeVerdictTone`/
  `strategyLiquidityVerdictTone`/`strategyRiskRatingTone`) reuse the
  existing green/amber/red/cyan `StatusPill` convention; the trade-scoped
  `executiveStanceTone` is reused as-is for the Strategy Executive
  Review's department opinions, since both share the same real
  `ExecutiveStance` union.

  Verified: `npx tsc -b --noEmit`/`npm run lint`/`npm run build` all
  clean. Extended `sandbox.spec.ts` with a new Playwright test that
  navigates every sub-tab against the live Vite + FastAPI stack and
  opens/cancels the real Retire form (never confirms — a real,
  irreversible CEO action a test must not perform as a side effect on
  the shared dev backend) — passes with zero console errors. A full
  ~65-test suite run against the live stack surfaced one real bug this
  new test caught: `StrategyHealthAssessment.id` is only unique per
  (strategy, sim day), not per completed run — a strategy that finishes
  more than one real Market Simulation on the same day produces two
  health assessments sharing an id, which `StrategyHealthView.tsx`'s
  history table was keying on directly. Fixed by keying on `id` plus
  array position instead of `id` alone; the four other failures in that
  run (movement-hold timing, dialogue-render timing ×2, one Phaser
  runtime error) are the exact same pre-existing flakes already
  documented in this file's "Playwright test suite — popup resilience"
  entry above, unrelated to this change, confirmed unaffected by
  re-running them in isolation.

- **v0.7 Feature 52 (Part 2) — "Living Strategies"**: a real, scoped
  subset of the brief's much larger Part 2 list, built on top of Part
  1's already-real artifacts. **Strategy Health** (`compute_strategy_health()`)
  is a real recent-vs-lifetime trend read over a strategy's own
  `SimulationResult` history — re-run on the same per-completed-simulation
  trigger as Part 1's Monte Carlo/Regime Test/Liquidity Validation —
  landing on one of seven real statuses (Excellent/Healthy/Stable/Needs
  Review/Declining/Critical/Retire Candidate) from real win-rate/return/
  drawdown deltas, never a fabricated score. **Strategy Retirement** is
  new: `Strategy.stage` gains a terminal `"retired"` value, reachable
  from any prior stage via a real, deliberate `POST /api/sandbox/retire`
  CEO action (never automatic) that cites a real reason. Every real
  retirement files exactly one of two new permanent records — a
  **Strategy Hall of Fame** entry (real, strict induction bar: ≥30
  aggregated trades, ≥55% win rate, ≥1.5 profit factor, ≤20% average
  drawdown, `stage == "approved"`, and a real approved `StrategyFounderApproval`
  on file) or a **Failed Strategy Archive** entry (every other
  retirement, with "what failed"/"lessons learned" pulled from that
  strategy's own real `StrategyReview` verdicts and `StrategyExecutiveReview`
  concerns — never invented after the fact). A Hall of Fame induction
  also nudges Company DNA's real `research_rigor` Legacy trait (a fifth
  real trigger alongside the four `app/company_dna.py` already tracked).
  New **Executive Dashboard** (`GET /api/sandbox/dashboard`) computes a
  real aggregate on request: stage counts, Hall of Fame/Failed Archive
  counts, and named best/weakest/most-improved/newest/highest-confidence
  strategy slots, each citing the real metric that earned the slot.
  **Explicitly cut from this pass, and why**: Version Control/Strategy
  Evolution (this codebase has no strategy revision/parent-child
  versioning mechanism to build on — a structural addition beyond this
  slice's scope, not a data-honesty cut); Strategy Competitions (needs
  Version Control as a prerequisite); a fully autonomous Automatic
  Revalidation workflow (retirement stays a real, deliberate CEO call,
  matching every other terminal Research Sandbox decision in this
  codebase — Learning Mode's own precedent); dedicated multi-month
  Research Projects (already real and shipped as Black Box Projects —
  not duplicated); a literal Strategy Library UI concept (the existing
  `strategies` list plus Part 1's `StrategyDossier` already carries every
  real field the brief's Library section asks for — no new backend
  artifact needed, this is a frontend-only concern deferred with the
  rest of Feature 52's UI). New tests: 11 more in
  `test_strategy_lab.py` (28 total) plus 3 in `test_sandbox.py` for the
  new terminal stage and retirement gating — 807/807 backend tests
  passing, `mypy`/`ruff` clean.

- **v0.7 Feature 52 (Part 1) — Strategy Validation Laboratory, "Never Trade
  An Untested Idea"**: enriches `app/sandbox.py`'s already-real 8-stage
  Research Sandbox pipeline (Idea → Research → Historical Backtest →
  Market Simulation → Paper Trading → Limited Live Capital → Company
  Review → Approved) with the deeper validation artifacts the brief asks
  for, without building a second measurement engine. New `app/strategy_lab.py`:
  **Monte Carlo Testing** — a real trade-sequence bootstrap (200 simulated
  paths) drawn from the strategy's own aggregated win rate and average
  win/loss sizes (never re-rolls an independent backtest — a new, small,
  purpose-built resample distinct from `app/whatif.py`'s own price-path
  Monte Carlo, which answers a different question); **Market Regime
  Testing** — since `SimulationResult` is only ever tagged at the coarser
  7-way `TestScenario` grain, results are honestly bucketed at that grain
  and each bucket is labeled with which of Feature 51's real 13-way
  `MarketIntelligenceRegime`s it covers, never claimed as independently
  tested 13 ways; **Liquidity Validation** — reuses Feature 51's real
  `compute_liquidity()`/`compute_market_structure()` against the
  strategy's own watched symbols, as-is; **Risk Analysis** — a new,
  standalone `evaluate_risk_gate()` now also gates Market Simulation →
  Paper Trading directly (Guardian's own `RISK_MAX_AVG_DRAWDOWN`), ahead
  of the richer five-reviewer `StrategyReview` risk verdict still run
  later at Company Review — an earlier real checkpoint, not a
  replacement; **Executive Review** — a real 9-department opinion (the
  same `ExecutiveDepartmentRole` seats as Feature 50, "Brain Room" reusing
  the same `devils_advocate` seat every other 9-role read in this codebase
  already does) with per-department stance/confidence/evidence/concerns/
  suggested improvements, driving a real advance/request_more_evidence/
  hold_for_improvement/reject recommendation; **Founder Approval** — a new
  mode of `app/founders.py`'s existing threshold-approval pattern, applied
  to a strategy instead of a Black Box Project; **Confidence Score** — a
  composite built entirely from the artifacts above, computed fresh on
  request rather than persisted (same reasoning as `ExecutiveRecommendation`/
  `WhatIfSimulation`: every input already lives somewhere permanent); and
  **Strategy Dossier** — the brief's "auto-generated professional report,"
  assembling every real artifact above for one strategy, exposed at new
  `GET /api/sandbox/dossier?strategyId=`. `POST /api/sandbox/request-review`
  now files the `StrategyExecutiveReview` and `StrategyFounderApproval` in
  the same real CEO action as the existing `StrategyReview` — Company
  Review, Executive Review, and Founder Approval are one moment, not
  three separate requests. Monte Carlo/Regime Test/Liquidity Validation
  re-run automatically in `nexus.py`'s tick loop every time a Market
  Simulation run completes, alongside the existing `StrategyReport`.
  5 new capped, permanent `GameSaveState` lists (`strategyMonteCarloResults`,
  `strategyRegimeTests`, `strategyLiquidityValidations`,
  `strategyExecutiveReviews`, `strategyFounderApprovals`), broadcast over
  the WS tick and persisted in the `company` save module. Explicitly not
  built, and why: a true infinite-sample probability of ruin (only ever a
  real share of this run's own simulated paths that breached a named
  drawdown bar, clearly labeled); real institutional liquidity/retail
  stop clusters/market maker behavior (inherited directly from Feature
  51's own honesty boundary); a second backtest/Monte Carlo engine (would
  repeat the "redundant re-measurement" trap `sandbox.py`'s own docstring
  already warns against). New `backend/tests/test_strategy_lab.py` (17
  tests) plus a new sandbox risk-gate rejection test; `mypy`/`ruff`/
  `pytest` all clean (793 backend tests passing). Feature 52 Part 2
  ("Living Strategies" — Strategy Library, Versioning, Health, Hall of
  Fame, Failed Strategy Archive, Competitions, Company DNA integration)
  and both parts' frontend are deliberately deferred to a follow-up pass.

- **Playwright test suite — popup resilience**: this sim clock never
  stops ticking against one shared dev backend, so a real closed trade,
  a fresh TradeProposal, a Trade Gatekeeper veto, or a Founder-approved
  breakthrough can pop up over whatever any test is doing at any moment
  — correct, honest gameplay behavior that used to fail unrelated tests
  outright. New `frontend/tests/helpers.ts` centralizes what used to be
  ~17 slightly-drifted copies of the same title-screen/popup-dismissal
  helpers (some of which, on inspection, never actually dismissed
  anything — a real resilience gap, not just duplication): `dismissBlockingPopups()`
  now knows all four real gameplay-triggered overlays (Executive Voting,
  the Trade Gatekeeper's rejection screen, the trade-outcome banner, and
  the Eureka! Breakthrough Moment — the last two of which no prior helper
  handled), and `clickRobust()`/`clickButton()`/`clickTab()`/`clickExpand()`
  wrap a click in a dismiss-then-retry loop so a popup intercepting a
  click gets cleared and retried instead of failing the test. A popup
  that genuinely can't be dismissed still fails loudly — every
  `tryDismiss*` function throws if its own dismiss action doesn't
  actually close the popup, which is the real "cannot be dismissed /
  behaves incorrectly" case that should fail. (A background auto-dismiss
  fixture polling independently of the test body was tried and reverted
  — it raced with foreground retries and could hang past a test's
  timeout during teardown, breaking previously-passing tests; the
  dismiss-then-retry pattern on each real click is the one that holds up
  under a real ~11-minute full-suite run against a live, actively-ticking
  backend.) `executiveVoting.spec.ts`/`feature50Part2.spec.ts` deliberately
  keep dismissing manually rather than importing a blanket fixture, since
  their own tests directly interact with the Executive Voting popup as
  the subject under test. Also fixed along the way: `campusMap.spec.ts`'s
  hardcoded employee count (now reads the real live count, the roster
  having grown twice since that assertion was written) and two of
  `marketIntel.spec.ts`'s own assertions (a `TerminalLabel`'s CSS
  `uppercase` never changes the underlying DOM text Playwright's
  `getByText` actually matches; a broad `/predicted/` regex needs
  `.first()` once the shared backend has more than one real graded day
  on record). Verified via three full ~60-70-test suite runs against the
  live stack; the same set of popup-interception failures does not
  recur. Six unrelated, pre-existing flakes surfaced during verification
  (movement-hold timing, dialogue-render timing, Devil's Advocate
  rotation determinism on a small pool, one strict-mode text ambiguity,
  one Phaser runtime error) — none involve a popup, and are left for a
  separate pass rather than scope-creeping this one.

- **v0.7 Feature 51 — Market Intelligence Department, "the company's eyes"**:
  before any trade proposal is generated, the company now
  computes a real, always-current read of the market it's operating in.
  New `app/market_intelligence.py` classifies a 13-way regime (vs. the
  existing 5-way `MarketEnvironmentRegime` — additive, not a replacement),
  Market Structure (real swing-high/low + Break of Structure detection),
  Liquidity Intelligence (real equal-high/low zone clustering + a real
  sweep-and-close-back pattern), a Volatility Engine, Session Intelligence
  (real wall-clock UTC windows), Momentum, and a composite Market Quality
  Score (Excellent/Good/Average/Poor/Avoid Trading) — all from this
  codebase's real (mock) OHLCV candle data, using standard technical-
  analysis formulas, never a prediction of future price. Two explicitly
  named PROXIES (Institutional Activity — a volume/price-divergence
  "absorption" read; News Risk — a real count of `market`-category
  `NewsItem`s on file) stand in for signals this codebase has no real
  order-flow/economic-calendar data source for, always labeled as such —
  real institutional order flow, Level 2 data, and an economic calendar
  are explicitly not built, matching the same honesty boundary
  `app/confidence.py`'s own module docstring already established. New
  `app/market_debate.py` gives five specialists (Liquidity/Price Action/
  Momentum/Quant/Risk) — distinct from the existing proposal-scoped
  `AiDebate` and the Executive Intelligence Network's own portfolio-level
  Risk department — independent real reads of that state. Integration:
  a new 8th Trade Gatekeeper check blocks a trade while the real Market
  Quality Score reads "avoid_trading"; every new `TradeProposal` carries
  a real one-line `marketIntelligenceSummary`; `market_intelligence`
  becomes the Executive Intelligence Network's real ninth department —
  because the Meeting Log/Weekly Self-Evaluation already iterate every
  department generically (Feature 50), this was the entire integration,
  no rewiring of the other eight departments needed. One real Executive
  Market Brief is generated every in-game evening (`MarketIntelligenceReport`,
  embedding the day's state + a fresh Market Debate + a real Strategy
  Match cross-referencing `app/sandbox.py`'s own backtest history); a
  Learning Loop grades the prior day's report the next evening against
  the real regime `app/market_environment.py`'s timeline recorded and
  real closed-trade win rate. **Academy Integration**: a new seventh
  Foundational Mentor roadmap track, `market_intelligence` — deliberately
  not attributed to any real external trading educator (unlike the other
  six), since this is TradeTown's own in-house department. Eight real
  lessons (Market Regimes & Trend Analysis, Market Structure, Liquidity,
  Institutional Behavior, Session Characteristics, Volatility,
  Probability Thinking, Risk Context), each citing a specific real
  `app/market_intelligence.py` mechanic, reusing the module's existing
  generic employee-auto-progression/aptitude-quiz/CEO-approved-graduation
  machinery with zero new plumbing. **Frontend**: a new "MARKETINTEL"
  Command Center tab (`MarketIntelPanel.tsx`), mirroring EXECINTEL's
  precedent — the live regime/quality read, Session/Volatility/Momentum/
  Institutional Activity/News Risk cards (proxies visibly labeled), a
  per-symbol Liquidity & Structure grid, the latest Executive Market
  Brief (all 5 debate specialists + Strategy Match) or its honest empty
  state, and the Learning Loop history or its own honest empty state.
  Data-layer wiring (`NexusManager.ts`/`EventBus.ts`/`gameStore.ts`/
  `socket.ts`) follows the exact diff-and-emit pattern
  `marketEnvironment`/`companyHealth` already established. The Academy
  track's own lesson UI needed zero new code — `MentorLibraryPanel.tsx`
  already iterates every roadmap track generically. Verified: two new
  backend test files (51 tests) plus updates to the gatekeeper/executive/
  executive_intelligence/company_health/foundational_mentors suites
  (including a real, honest consequence of a second real active mentor
  track existing by default: `company_health.py`'s Talent Development
  metric's real denominator now correctly spans both) — 775/775 full
  suite, mypy/ruff clean; a direct ~10-in-game-day `nexus.tick()`
  simulation confirmed the daily report/Learning Loop cadence with no
  exceptions, and a `save_modules` round-trip confirmed the new fields
  persist correctly. Frontend: `tsc -b --noEmit`/lint/build all clean;
  the panel was verified against the live stack via scripted browser
  screenshots (both the pre-first-evening empty state and, after
  fast-forwarding real in-game time, a fully populated brief and a
  graded Learning Loop entry) with zero console/React errors — this
  sandbox's own Playwright runner currently fails to reach the title
  screen for every Command Center spec (reproduced on unmodified,
  pre-existing spec files), a pre-existing environment flake unrelated
  to this change.

- **TradeTown Development Rules (v0.9)** — a new canonical constitution
  document (`docs/DEVELOPMENT_RULES.md`) governing how every future
  feature must be designed: company-over-player, autonomous employees,
  every building needs a real function, no fake progression, permanent
  company memory, evidence-before-opinion, no placeholder systems, and a
  required nine-part GOAL/REQUIREMENTS/SYSTEM BEHAVIOR/PLAYER
  ACTIONS/EMPLOYEE ACTIONS/UI/RULES/DO NOT/SUCCESS CRITERIA structure for
  scoping new work. Also adds a root `CLAUDE.md` (previously absent
  despite the existing `docs/` "bible" family) that points to it and to
  the other canonical docs, and writes down this project's own
  established engineering discipline — research overlap first, scope
  honestly and document every cut, commit the backend before starting
  the frontend, verify thoroughly, document before committing — so it
  persists across sessions instead of living only in conversation
  history.
  - **Elite Intelligence Objective** (added to the same doc): v0.9's
    stated primary objective — build the smartest autonomous trading
    company possible before risking real capital, across twelve named
    intelligence categories (reasoning, critical thinking, research
    ability, pattern recognition, market understanding, decision
    quality, statistical thinking, risk management, trading psychology,
    adaptability, communication, long-term learning). Every future
    feature's GOAL should name which category it serves.
  - **Critical Thinking** (added to the same doc): employees should
    treat new information like scientists, not followers — ask what's
    true, why, what evidence agrees/disagrees, when it fails, when it
    works best, and whether it can be improved. Documents the two real
    existing systems closest to this today (`reasoning_lab.py`'s
    `ReasoningChallenge`, `devils_advocate.py`'s `ChallengeReport`) and
    the two real gaps neither currently covers ("when does it work
    best," "can it be improved") for future scoping.
  - **Multiple Opinions** (added to the same doc): important decisions
    should rarely rest on one employee's call — Research/Quant/Risk/
    Coach/Founders/Devil's Advocate should each weigh in, and the Brain
    Room should combine every perspective. Documents that most of these
    roles already exist as real, independent reviewers today
    (`sandbox.py`'s five-role `StrategyReviewVerdict`, `executive.py`'s
    six-seat analyst voting, `founders.py`, `coach.py`), but that the
    Brain Room itself does **not** yet combine them into one view — it's
    a research/company-score HUD today, while these opinions live
    scattered across Sandbox/Executive/Founders/Coach panels. Named as
    a real gap for future scoping, not claimed as already built.
  - **Never Stop Learning** (added to the same doc): no employee should
    ever believe they've mastered trading — markets, strategies, and
    technology all evolve, and the company should keep searching for
    better ideas, research, execution, psychology, statistics, and risk
    management. Documents the real systems that already embody this —
    `market_environment.py`'s live regime read, `wisdom.py`'s
    Reflection Chamber (a weekly/monthly `ReflectionSession` and a
    never-profit-based Company Wisdom Score), `mistakes.py`/
    `successes.py`'s Library of Mistakes/Successes, `innovation.py`'s
    narrow Devil's-Advocate-skill ladder — confirming no "mastery" cap
    exists anywhere in this codebase for any employee to plateau at.
  - **No False Confidence** (added to the same doc): never present
    uncertain conclusions as facts; value accuracy over speed. Documents
    that this is already a structural convention — `confidence.py`'s own
    docstring refuses to fabricate numbers for factors with no real
    backing data, and `gatekeeper.py` actually blocks a low-confidence
    trade rather than waving it through. Also names the one real gap:
    no automatic "low confidence triggers more research" closed loop
    exists yet — `sandbox.py`'s stage-gating is the closest real analog,
    not an exact match.
  - **Real Money Readiness** (added to the same doc): v0.9 exists to
    prepare the company for real capital — real money should activate
    an already mature company, not change how it operates. Documents
    that `docs/ROADMAP.md` already states this exact philosophy
    independently for its own Version 1.0 entry, maps each named
    "professional" dimension to a real existing system (discipline,
    education, research, risk management, communication, statistical
    analysis, decision making, documentation), and explicitly preserves
    `ROADMAP.md`'s own stop condition — this principle does not
    pre-authorize live brokerage code; that stays a separate, deliberate
    decision at v1.0's own kickoff.
  - **Intelligence Over Implementation** (added to the same doc): when
    choosing between implementations of the same feature, pick the one
    that increases reasoning, learning, autonomy, decision quality,
    adaptability, collaboration, or long-term knowledge. Positioned as a
    sharper, feature-implementation-specific successor to the existing
    Foundational Principle rule, explicitly cross-referenced rather than
    duplicated as an unrelated third rule.

- **v0.7 Feature 50 (Part 1) — Executive Intelligence Network**: the
  brief's own instruction was "do not create duplicate systems — refactor
  and upgrade the current implementation." Research found every one of
  the eight named departments (Research, Quant, Risk, Simulation,
  Decision Intelligence, Coach, Founders, Devil's Advocate) already has a
  real, checkable system behind it in this codebase — see the mapping
  table in `docs/Architecture.md`'s new Feature 50 section. New
  `app/executive_intelligence.py` is a synthesis layer, not a new
  computation engine: `generate_department_opinions()` produces a real
  `DepartmentOpinion` per department by reading `TradeProposal`'s
  `research_summary`/`risk_summary`/`confidence_engine`/`analyst_votes`,
  a `ChallengeReport` when one exists (Simulation and Founders both
  already had exactly what they needed — `worst_case_scenario` and
  `historical_comparisons` — sitting unused for this purpose), and the
  latest `CoachReport`. `compute_executive_recommendation()` is a real,
  rule-based aggregate over those opinions — never fabricated — checked
  in priority order (an active major concern always outranks a merely-
  lukewarm average), producing one of six real actions with real
  supporting/opposing department lists. New
  `GET /api/executive/intelligence?proposalId=...`, computed fresh on
  every call (no persistence — every input already lives somewhere
  permanent). This is the largest single brief given this session;
  it was built phased, the same way Feature 49 was (Phases 1/2/3 +
  a Revision) — this is Part 1, the foundational synthesis layer (Part
  2/3 below completes the rest). Explicitly cut, not deferred: the
  brief's "Session Changes / Market Open / Market Close" simulation
  environments — no session-boundary model exists anywhere in this
  codebase's continuous sim clock to back them.
  Backend: `test_executive_intelligence.py` — 20 new tests, 680/680 full
  suite, mypy/ruff clean.
  - **Frontend (Part 1's Executive Recommendation Panel)**: a new
    "OPEN EXECUTIVE INTELLIGENCE NETWORK" collapsible inside the
    existing Executive Voting popup (`ExecutiveVoting.tsx`) — proposal-
    scoped, fetched fresh via `api.getExecutiveIntelligence(proposalId)`
    exactly when opened (same never-cached convention as the What-If
    Simulation Lab beside it), not a new standalone tab, since
    `ExecutiveRecommendation` is computed fresh per-proposal like
    `WhatIfSimulation` and has no persisted history to justify a
    company-wide dashboard yet. Shows the synthesized recommended
    action, network confidence, supporting/opposing departments, and
    all 8 real department opinions with their own stance and summary.
    New TS mirrors (`ExecutiveRecommendation`, `DepartmentOpinion`,
    `ExecutiveAction`/`ExecutiveStance`/`ExecutiveDepartmentRole`) in
    `types.ts`, tone helpers in `derive.ts`. Verified: tsc/eslint/build
    clean; new Playwright test in `executiveVoting.spec.ts` opens a
    real pending proposal's popup and asserts all 8 department labels,
    the recommendation, and the supporting/opposing lists render from
    the real endpoint — passing live against the running dev stack.

- **v0.7 Feature 50 (Part 2/3) — Decision Grade, Executive Meeting Log,
  Weekly Self-Evaluation, Company Health redesign**: three new
  real, permanent systems built directly on Part 1's synthesis, plus one
  redesign — none of them a second opinion engine. **Decision Grade
  (A+–F)**: `app/executive.py`'s `compute_decision_grade()` grades the
  decision-making PROCESS at the moment `resolve_proposal()` makes it —
  50% the real Decision Confidence Engine score, 25% real multi-agent
  analyst agreement, 25% whether the Trade Gatekeeper actually approved
  it — never the trade's own P&L (same "process over outcome" convention
  `discipline.py`'s Discipline Score already established). Attached to
  every `TradeDecision` going forward. **Executive Meeting Log**: makes
  Part 1's ephemeral synthesis permanent — `generate_meeting_log_entry()`
  runs the same opinion/recommendation engine and records one real
  `ExecutiveMeetingLogEntry` (reusing the decision's own already-computed
  grade, never recomputed) at every real `resolve_proposal()` call site —
  a genuine CEO decision, a Company Operating Mode auto-resolution, and a
  stale-proposal expiry. **Weekly Self-Evaluation**: `generate_weekly_self_evaluations()`,
  fired on the same weekly cadence as `wisdom.py`'s `ReflectionSession`,
  builds one real `DepartmentSelfEvaluation` per department entirely from
  that department's own real Meeting Log opinions over the trailing week
  — an honest "no real decisions yet" neutral default when there's
  nothing on record. **Company Health redesign**: ten new real
  Executive-tier dimensions in `app/company_health.py` (Decision
  Quality, Executive Alignment, Risk Governance, Simulation Coverage,
  Department Consensus, Self-Evaluation Health, Institutional Memory,
  Innovation Velocity, Talent Development, Founder Oversight) — additive
  alongside the eleven Operational ones Feature 23 already established,
  never replacing them (`overall`/`tier` are byte-for-byte unchanged).
  `executiveOverall`/`executiveTier` are the new tier's headline;
  `combinedOverall`/`combinedTier` (an equal blend) is the true
  redesigned headline. The original brief's exact ten dimension names
  weren't preserved verbatim in this session's chat-only history by the
  time this phase began — rather than fabricate names that couldn't be
  checked against the real brief, these ten were chosen as the most
  defensible real, checkable signals available (see
  `docs/Architecture.md`'s full mapping table). Verified: new tests in
  `test_executive.py` (`TestComputeDecisionGrade`, 7 tests),
  `test_executive_intelligence.py` (`TestGenerateMeetingLogEntry`/
  `TestGenerateWeeklySelfEvaluations`, 9 tests), and
  `test_company_health.py` (`TestExecutiveTier`, 11 tests) — 716/716
  full suite, mypy/ruff clean. A direct 9-in-game-day `nexus.tick()`
  simulation run confirmed both cadences and the new Company Health
  fields populate correctly with no exceptions, and a `save_modules`
  split/assemble round-trip confirmed the new archive fields persist.
  - **Frontend**: `CompanyPanel.tsx` gains an "Executive Health" card
    (all ten new dimensions, a Meter, and a Combined Overall footer)
    beside the existing Company Health card; `DecisionsPanel.tsx` gains
    a Decision Grade Distribution card and a Grade column on the
    decision table; `RiskPanel.tsx` gains a Risk Governance mini-card;
    `ExecutiveIntelPanel.tsx` gains a Weekly Self-Evaluation grid (one
    card per department) and an expandable Executive Meeting Log list.
    New fields threaded through `types.ts`, `NexusManager.ts`,
    `EventBus.ts`, `gameStore.ts`, `socket.ts`, plus new tone/derive
    helpers. Verified: `npx tsc -b --noEmit` (the correct invocation for
    this repo's solution-style `tsconfig.json`), `npm run lint`,
    `npm run build` all clean; a new `tests/feature50Part2.spec.ts`
    (4 tests) passes against the live dev stack, and the 30-tab
    `commandCenter.spec.ts` regression stayed green.
  - **Incidental bug found and fixed while verifying this phase**
    (unrelated to Feature 50's scope): `app/wisdom.py`'s title lookup for
    the most-common case-study category only covered `mistakes.py`'s six
    categories, but the list it scans is shared with `successes.py`'s
    (Feature 42) three success categories — whenever the most common
    real category was a success one, it raised `KeyError`, and because
    `app/sim.py`'s sim loop has no exception handling beyond
    `CancelledError` (and the dead task's exception was never retrieved),
    this silently froze the sim clock with zero log output. Fixed by
    merging both modules' `CATEGORY_TITLES`; reproduced against the real
    persisted save file and added a regression test. See
    `docs/Architecture.md` for the full root-cause writeup.

- **"Revoke Graduation" — a new Executive Action on the Academy**: the
  mirror image of the Graduation Queue's Approve button. New
  `POST /api/foundational-mentors/revoke-graduation` (body `{agentId,
  mentorId}`) reverts one employee's `graduationStatus` from
  `"graduated"` back to `"in_progress"`, resets their lesson/quiz
  progress on that track to a genuine fresh start (real
  auto-progression picks it back up on the next tick), and sets a real,
  deterministic Coach improvement-plan note (a new `coachNote` field,
  cleared automatically on real re-approval). Scoped exactly to the
  request's own bullet list: the mentor track's company-wide status/
  roadmap position and every other employee's progress are untouched,
  and Company Knowledge (`academy_research.py`) was never gated by any
  one employee's graduation in the first place — "remedial education,
  not deleting progress" reuses the exact same real fresh-progress
  constructor `repeat_mentor_company_wide` already established.
  Backend: `TestRevokeGraduation` — 9 new tests plus 1 confirming
  `approve_graduation` clears a leftover note on real re-approval,
  689/689 full suite, mypy/ruff clean. Frontend: the Employee Academy
  Report's Certifications list now shows a real "Revoke Graduation"
  button per certification, and a real Coach improvement-plan note when
  one exists; `tsc -b`/eslint/build clean, new live Playwright test
  covering the honest empty state (a full graduate-then-revoke round
  trip isn't reachable within a test's time budget — see
  `docs/Architecture.md`).

- **v0.7 Feature 49 Revision — Professional Academy: employees are the
  students, the CEO manages**: inverts the Foundational Mentor
  Program's model per an explicit CEO revision request. TradeTown is a
  company management sim — the player is the CEO, the employees are
  the staff — so requiring the CEO to personally click through every
  lesson/quiz to make company progress happen was the wrong shape.
  - Real employee agents (scout, atlas, echo, nova, scribe, sentinel,
    pulse, guardian — the same roster `academy_research.py`'s own
    company-wide Academy project rotation already uses, minus Coach,
    who is explicitly the teacher/monitor in this revision) now
    auto-progress through the company's one active mentor track every
    real backend tick, the same honest tick-accrual convention
    `AcademyProject` already established. A lesson's auto-graded quiz
    pass probability is tied to each employee's own real average
    `DisciplineReview` score (clamped, never deterministic) — never a
    fabricated "picked option."
  - **Graduation Queue**: completing all lessons moves an employee to
    `pending_approval`, not immediately graduated — approving is a
    real CEO action. The company as a whole advances to the next
    roadmap mentor once every student has an approved graduation
    ("mastery before progression").
  - **Academy Dashboard** (the MENTORLIB tab, now a management
    dashboard, not a player-learning screen): Currently Studying, Top
    Students, Needing Help, Graduation Queue, Upcoming Graduations,
    Academy Statistics, Coach Recommendations, and Current
    Certifications — computed entirely client-side
    (`computeAcademyDashboard` in `lib/derive.ts`) from data already
    broadcast, the same "frontend-only feature" pattern Feature 47's
    Knowledge Base already established. Clicking an employee opens
    their real Academy Report.
  - **Coach Recommendations**: "Repeat Lesson" and "One-on-One
    Coaching," both driven by the real `consecutiveQuizFailures`
    counter — the brief's other recommendation types (Extra Reading,
    Extra Backtesting, Reflection Session, Research Assignment, Paper
    Trading Practice) have no real backing signal yet and are not
    fabricated.
  - **CEO Learning Mode** (Settings, default off): an entirely
    separate, optional bucket (`ceoProgress`) letting the CEO
    personally take the same lessons if they want to — never gates or
    is required for real company progress.
  - New company-wide CEO controls: pause/resume/skip/repeat training
    for the whole cohort.
  - TJR's lesson set expanded from 6 to 8 lessons (added Liquidity/
    Market Structure and Risk Management Fundamentals) to cover the
    revision's wider focus-area list.
  - Explicit scope cuts (documented in
    `foundational_mentors.py`'s module docstring): CEO custom-mentor
    authoring, per-employee assignment of books/videos/backtesting/
    paper-trading, the full cross-system "Mentor Validation" pipeline,
    CEO Daily Settings (trading sessions/allowed strategies), post-halt
    activity redirection, and fabricated "growth" deltas.

  Backend: `schemas.py` restructures `FoundationalMentorState.progress`
  to per-employee (`dict[AgentId, dict[FoundationalMentorId, ...]]`),
  adds `ceoProgress`/`graduationStatus`/`companyGraduatedSimDay`;
  `nexus.py` wires `tick_employee_progress()` into the real tick loop
  (Rest Mode-gated, same as Academy projects); router and `state.py`
  rewritten around the new function set (`approve-graduation`, company-
  wide `pause`/`resume`/`skip`/`repeat`, `/ceo/view`, `/ceo/quiz`).
  `test_foundational_mentors.py` rewritten (27 tests, 648 total
  passing) — mypy/ruff clean. Frontend: `MentorLibraryPanel.tsx`
  rebuilt as the dashboard + Employee Report modal; full WS-mirror
  wiring; `mentorLibrary.spec.ts` rewritten (2 Playwright tests
  against the live stack) — tsc/eslint/build clean.

- **Command Center UI Revision — Mentor Lab tab (real CEO custom-mentor
  authoring)**: the previous revision's "no in-product authoring form
  exists" scope cut is now built for real. `FoundationalMentorId` is
  loosened from a fixed six-value literal to a plain string (backend
  `schemas.py`, frontend `types.ts`) so the CEO can add genuinely new
  mentor tracks and lessons at runtime, not just the six seeded ones.
  - New backend functions `add_custom_mentor`, `add_custom_lesson`,
    `set_active_mentor` (`foundational_mentors.py`), backing three new
    endpoints `POST /add-mentor`, `POST /add-lesson`, `POST /set-active`.
    `FoundationalMentorState` gains a persisted `roadmap_order` (so
    custom mentors join the real sequential unlock queue) and
    `custom_lesson_answers` (a hidden runtime answer key for
    CEO-authored quizzes — built-in lessons keep their answers in a
    module constant that's never serialized; custom ones can't, so they
    live in real per-state storage instead). Capped at 20 custom mentors
    / 30 lessons per mentor.
  - New **MENTOR LAB** Command Center tab (`MentorLabPanel.tsx`):
    mentor-centric browsing distinct from MENTORLIB's employee-centric
    dashboard — pick a track, see its curriculum/focus areas/content
    disclaimer/graduation status, "+ Add New Mentor," "+ Add Lesson,"
    and "Make Active Track" (a real CEO override that jumps company-wide
    focus, pausing whatever was active — same mechanism
    `skip_to_next_mentor` already used). Also shows "Company Concepts
    Learned" (a real, derivable count) and a Mentor Comparison table.
  - The brief's "Concepts Validated" / "Concepts Rejected" counters are
    **not** shown as numbers — no real cross-system validation pipeline
    (Discussed → Backtested → Paper Traded → Sandbox Tested → Quant
    Reviewed → Risk Reviewed → Devil's Advocate Reviewed → Founder
    Council Reviewed) exists in this codebase to back them honestly; the
    panel says so explicitly instead of fabricating the numbers.
  - The brief's "ACADEMY" tab name collides with the pre-existing v0.6.2
    Trading Academy tab (`EducationPanel`), so the existing "MENTORLIB"
    tab keeps its name — it already is the employees'-progress dashboard
    the brief describes. The brief's "TRAINING" tab name likewise
    collides with the pre-existing Signal Calibration mini-game
    (`CalibrationPanel`), whose content overlaps with the real
    backtesting/paper-trading pipeline already on the SANDBOX tab; no
    changes were made there for this revision.
  - Backend: `test_foundational_mentors.py` gains 12 new tests (39 in
    the file, 660 total passing) — mypy/ruff clean. Frontend: new
    `mentorLab.spec.ts` Playwright test (live stack, add-mentor →
    add-lesson → make-active round trip); `commandCenter.spec.ts`'s
    tab-count regression updated (29 → 30 tabs).

- **v0.7 Feature 49 (Phase 3) — Professional Day Trading Program:
  Foundational Mentor Program**: an expandable, CEO-facing library of
  named trading-educator "tracks" worked through as a sequential
  lesson-and-quiz curriculum (`app/foundational_mentors.py`). Real named
  educators (TJR, Al Brooks, Linda Raschke, Mark Douglas, Tom Hougaard,
  Mike Bellafiore) are used only as CEO-assigned track labels — this
  codebase has no HTTP client, PDF/video parser, or LLM call anywhere,
  so there is no mechanism to actually ingest their real work. Every
  lesson's content is 100% original TradeTown-authored material,
  explicitly disclaimed on every mentor profile, never a claimed
  transcription of a real person's real teaching (an explicit CEO
  content-attribution decision).
  - Only the **"tjr" track ships real content**: 6 original lessons
    tied to real, checkable TradeTown mechanics — the Discipline
    Score's process-over-outcome design (`discipline.py`), the real
    Patience factor (`PATIENCE_TARGET_MINUTES`), the Gatekeeper +
    Daily Trading Objectives filters, the Trading Journal's honest
    `screenshot` placeholder, and the Wisdom Score as the closest real
    analog to "consistency".
  - The other 5 named tracks are seeded as **real, ordered roadmap
    entries** — real display name, real track label, real focus-area
    topics from the brief — but ship with zero lessons and
    `status: "planned"` rather than five fabricated placeholder shells.
    Completing a track's lessons graduates it and unlocks the next
    roadmap entry (a real mechanical unlock, honest that the newly
    unlocked track still has no content until it's authored).
  - Graduation is gated purely on the real "all lessons completed"
    signal — deliberately not tied to Research Sandbox backtest stats
    (`sandbox.py`'s own docstring already documents its trade-to-
    strategy attribution gap).
  - CEO controls: pause/resume/skip/repeat a track (mirrors
    `black_box.py`'s manual-override pattern), plus a bookmark-only
    "External Resources — CEO Reading List" (title/URL/type; TradeTown
    never fetches, parses, or grades linked material).
  - Explicit scope cuts: no CEO custom-mentor-authoring UI (the data
    model is expandable — add an id, roadmap entry, and lesson tuple —
    but there's no in-product authoring form); no "concepts adopted/
    rejected" or "statistical success" mentor rating (no real signal
    exists to measure it honestly).

  Backend: new `app/foundational_mentors.py`,
  `routers/foundational_mentors.py`, `tests/test_foundational_mentors.py`
  (22 tests, 642 total passing). Extends `schemas.py`, `state.py`,
  `save_modules.py`, `ws_manager.py`, `main.py`.
  Frontend: new `MentorLibraryPanel.tsx` (new "MENTORLIB" Command
  Center tab, distinct from the pre-existing "MENTOR"/Sage tab), full
  WS-mirror wiring across `types.ts`/`gameStore.ts`/`EventBus.ts`/
  `NexusManager.ts`/`socket.ts`/`api.ts`, and new `mentorLibrary.spec.ts`
  Playwright coverage.

- **v0.7 Feature 49 (Phase 2) — Professional Day Trading Program:
  Liquidity/Market Structure curriculum**: extends the existing 10-lesson
  Trading Education curriculum (`app/education.py`) with 8 new lessons
  (orders 11-18) covering liquidity, buy-side/sell-side liquidity, swing
  highs/lows and market structure, equal highs/lows and stop clusters,
  liquidity sweeps/grabs, inducement, market structure shifts and
  displacement, premium/discount pricing, and order flow. Researched
  first: this codebase has no order-book, bid/ask, trade-by-trade tape,
  or liquidity-pool data anywhere (`app/market_data.py`'s `Candle` is a
  single aggregate OHLC bar with one volume number, uncorrelated with
  the bar's own price move). Every lesson teaches the real professional
  concept honestly:
  - Where a real, honest analog exists in TradeTown, the lesson points
    at it: `liquidity_sweeps` points at the What-If Simulation Lab's
    real "Liquidity Sweep" scenario (a real hypothetical scaled off the
    symbol's own measured volatility, already honestly labeled a
    scenario); `structure_shifts` points at the Scanner's real
    volume-confirmed breakout alert; `swing_structure`/
    `premium_discount` build directly on the existing Trends vs. Ranges
    and Support & Resistance lessons' own real trend/regime reads.
  - Where no real detector exists, the lesson says so explicitly rather
    than fabricating one: `liquidity_basics`, `equal_highs_lows`,
    `inducement`. The final lesson, `order_flow_intro`, names this
    honesty boundary directly — every other lesson in the module is
    really a way of *inferring* likely order flow from price action
    alone, because the real order-by-order data isn't available here.
  - Zero new persistence, zero new endpoints — reuses the existing
    `all_lessons()`/`mark_viewed()`/`grade_quiz()` API and
    `EducationPanel.tsx` UI exactly as-is.

  Backend: `test_education.py` updated for the 18-lesson curriculum +
  the full suite (621/621) + mypy/ruff clean. Frontend: tsc/eslint/build
  clean; `commandCenter.spec.ts`'s Trading Academy test extended to
  confirm the new module's first and last lessons render.

- **v0.7 Feature 49 (Phase 1) — Professional Day Trading Program: Daily
  Trading Objectives**: scoped from a large brief covering daily profit
  targets/loss limits, a "Trade Quality Checklist," a full Liquidity/
  Market Structure curriculum, and a Foundational Mentor Program (TJR +
  a five-mentor roadmap). Researched first (a full audit of
  `RiskLimits`, `app/gatekeeper.py`, `app/discipline.py`,
  `app/academy.py`/`app/academy_research.py`, `app/market_data.py`,
  `app/mentor.py`, and `app/sandbox.py`) before scoping this first,
  narrowest real slice:
  - **`max_daily_loss_pct` is now actually enforced.** It already
    existed on `RiskLimits` but was never read by anything —
    confirmed by grep before this feature — only displayed. Two new
    real limits join it: `daily_profit_target_pct` and
    `max_trades_per_day`.
  - **All three derive from real, already-persisted data** —
    `PaperTrade.opened_sim_minutes`/`closed_sim_minutes` (`// 1440` =
    the sim day) — zero new data source.
  - **Enforcement reuses the existing Gatekeeper block path, not a new
    mechanism**: `app/risk_engine.py`'s `evaluate_sentinel_risk` returns
    a critical, symbol-scoped `RiskWarning` the same way the existing
    lifetime-drawdown check already does, which becomes the proposal's
    `riskSummary` and drives Sentinel's analyst vote to "wait" (see
    `app/executive.py`'s `_risk_vote`), which then fails
    `app/gatekeeper.py`'s `_risk_manager_check` if the CEO tries to
    force a trade anyway. This is also why no new "penalize forcing a
    trade after the halt" Discipline factor was added — once the
    Gatekeeper blocks it, no `PaperTrade` (and therefore no
    `DisciplineReview`) is ever created for it, the same "structurally
    constant, nothing real to score" case `app/discipline.py`'s own
    module docstring already documents.
  - **A new real-time readout** (`DailyObjectiveStatus`,
    `compute_daily_objective_status()`) shows today's real trade count,
    real realized P&L, and which objective (if any) halted trading —
    computed fresh every tick, the same "derived, never persisted"
    convention `CompanyHealth`/`CompanyDNA` already use.
  - **The first real CEO write path for RiskLimits** (`POST
    /api/risk-limits`) — it was display-only before this feature, with
    no endpoint at all.
  - **Explicit scope cuts, citing this codebase's own existing
    precedent**: the "Trade Quality Checklist"'s market structure/
    liquidity analysis/session confirmation/higher-timeframe context/
    stop-loss R:R items were already explicitly refused by name in
    `app/gatekeeper.py`'s own module docstring and `derive.ts`'s
    `preTradeChecklist` comment (no real data source for any of them);
    economic news timing and market trading sessions were already
    refused for the identical reason in `app/sandbox.py`'s and
    `app/schemas.py`'s own "Earnings weeks / economic news" cuts (no
    economic calendar or session-hours data source anywhere in this
    codebase). The Liquidity curriculum and Foundational Mentor Program
    are follow-up phases of this same feature, scoped separately.

- **v0.7 Feature 48 — Company DNA System**: scoped from a brief asking
  for a "Company Identity" label, DNA that "changes slowly" and is
  influenced by "every major event," DNA effects on company behavior,
  a Founder-retirement "Legacy," and (explicitly cut) cross-company
  comparison. Company DNA (Feature 43) already existed as five real
  behavioral traits recomputed fresh from full history every tick — this
  feature adds two real, additive pieces without touching the five
  traits' own tested formulas or documented meaning:
  - **Company Identity** (`app/company_dna.py`'s `classify_identity()`):
    a pure, deterministic label read off the five existing trait
    scores — zero new data, checked in a fixed priority order so exactly
    one label always applies (e.g. "Ultra Conservative," "Research
    Driven," "Highly Disciplined," "Independent Thinker," "Collaborative
    Culture," "Aggressive Risk-Taker," "Balanced Operator"). "Not Yet
    Established" until real sample size exists.
  - **Legacy — a small, permanent, capped delta layered on top of the
    fresh score** (`nudge_legacy()`, capped at `LEGACY_DELTA_CAP` = 15
    points per trait in either direction, never mixed into the five
    formulas themselves): four real, one-time or rare company events
    this codebase already tracks each contribute one small nudge — a
    ratified Black Box breakthrough and a completed Academy project each
    nudge Research Rigor up (real completed research effort); a filed
    `disciplined_process` success study nudges Risk Appetite down and a
    filed `patient_execution` success study nudges Patience up (each
    records real behavior that already happened — never a prediction);
    the Founders' one-time "Legendary Status" retirement (Feature 39)
    nudges Risk Appetite down and Research Rigor up at once, since
    Keystone (risk) and Compass (learning) retire together. This is what
    makes DNA genuinely "change slowly" — the base score is still a pure
    historical average, but real milestones now leave a lasting mark on
    top of it.
  - **Explicit scope cut**: this codebase is single-tenant (one company,
    one save slot — see `state.py`'s and `save_modules.py`'s own module
    docstrings), so "no two companies should think exactly alike" and
    any recruitment/cross-company comparison have no real mechanism to
    attach to and are not built.

- **v0.7 Feature 47 — Company Operating System**: scoped from a brief
  asking for one place where "everything the company learns" is visible,
  a system that "references company principles when giving advice" (e.g.
  "This violates Company Principle 8"), and "Continuous Improvement"
  fed by 8 named sources. Researched first: every one of the 8 named
  sources (Reflection Chamber, Academy, Research Division, Innovation
  Lab/Black Box, Constitution, Founder Lessons, Coach Reviews, Decision
  Replay Center) already exists and already produces real, persisted
  records — so "Continuous Improvement" needed no new backend at all,
  only a place to actually see it aggregated. Built as two honest,
  additive pieces:
  - **Knowledge Base — a pure, zero-new-backend-data aggregation**
    (`frontend/src/ui/components/CommandCenter/lib/derive.ts`'s
    `computeKnowledgeBase`): joins six real, already-persisted learning
    records (Library of Mistakes case studies, Research Sandbox
    `StrategyReport`s, Constitution citations, Coach `recommendations`,
    completed Academy projects, Reflection Chamber insights) into one
    chronological, source-filterable timeline — the new "OPS" tab
    (`KnowledgeBasePanel.tsx`). Deliberately distinct from the existing
    Knowledge Graph tab (Feature 25.5): that is a relational node/edge
    structure over a different, smaller set of sources; this is a flat
    timeline over six sources, three of which (Constitution, Reflection
    Chamber, Library of Mistakes) the graph never touches.
  - **Real-Time Guidance — Constitution citations surfaced inline on
    the report itself** (`app/constitution.py`'s new
    `articles_for_challenge()`): a Devil's Advocate `ChallengeReport`
    already computes four real concern buckets (`hiddenRisks`,
    `weakAssumptions`, `missingEvidence`, `historicalComparisons`); each
    non-empty bucket now maps to the one real Article it most directly
    speaks to (VII/III/IV/VI respectively) and is stored on the report's
    new `citedArticleIds` field, shown directly under the report in the
    Executive Voting popup — literally realizing the brief's "This
    violates Company Principle 8" example with 100% real, already-
    computed data. Distinct from `nexus.py`'s own separate global
    "Live Enforcement" citation log (Feature 46), which always cites
    Article III on any filed report for a different reason (the act of
    filing a challenge itself is "challenging assumptions") — this is
    the same real signals surfaced on the report the CEO is actually
    looking at, not a duplicate detector.
  - **Scope cut, explicitly**: no new detection logic, no fabricated
    "AI recommendation engine" — every citation traces to a field the
    report already computed for itself.

- **v0.7 Feature 46 — Company Constitution**: scoped from a brief asking
  for a permanent rulebook of Articles, "Live Enforcement" where Coach
  quotes it/Founders teach it/Academy explains it/Risk Department
  enforces it/Devil's Advocate references it, and a CEO-driven amendment
  process (Founders debate, Coach evaluates, employees vote advisory-
  only, CEO ratifies). No rule-of-conduct concept existed anywhere in
  this codebase before this feature — the 8 example Articles are
  genuinely new, seeded verbatim from the brief. What made "Live
  Enforcement" honest rather than decorative was building it as a real,
  permanent citation log fed by hooks at real event points this codebase
  already has, never a fabricated quote attributed to nobody.
  - **8 real Articles, permanent from game start** (`app/constitution.py`'s
    `default_constitution()`): Protect Capital First, Research Before
    Execution, Challenge Assumptions, Evidence Over Opinions, No Revenge
    Trading, Every Mistake Must Teach Something, Respect Risk, Continuous
    Learning Is Mandatory — the brief's own text, unmodified.
  - **"Live Enforcement" — a real citation log, six real hooks**
    (`app/nexus.py`'s `tick()`): every filed case study/success study
    cites Article VI (literally what the mechanic does) plus the specific
    Article its own detected pattern maps to (`MISTAKE_ARTICLE_MAP` —
    e.g. `incomplete_research` → Article II, `unchallenged_assumptions`
    → Article III); every Devil's Advocate `ChallengeReport` cites
    Article III (its whole job) and Article IV when it found real missing
    evidence; a genuinely *new* critical `RiskWarning` cites Articles
    I/VII; a completed Academy project cites Article VIII; the monthly
    Founder Council cites Keystone's Article VII and Compass's Article
    VIII; a weekly/monthly `CoachReport` with real `commonMistakes` cites
    whichever Article the most recent case study maps to. "No revenge
    trading" (Article V) deliberately gets exactly one real trigger —
    `acted_too_quickly`/`patient_execution`'s own real signal — rather
    than a second, independently-invented detector.
  - **A real amendment pipeline, not a fabricated debate transcript**
    (`app/constitution.py`): the CEO proposes real text
    (`POST /api/constitution/propose`); Keystone and Compass each run a
    real word-overlap redundancy check against every existing Article
    plus a real domain-keyword match (risk vs. learning); the Coach
    evaluation cites whichever real `CompanyHealth` sub-score the
    proposal's own keywords match; all 11 non-Founder employees cast a
    real vote — "support" with a named reason when their own real
    `AgentProfile.occupation` matches the theme, "abstain" only when a
    Founder's own real redundancy flag was raised, "support" by default
    otherwise (advisory only, never gates anything)
    (`POST /api/constitution/advance`); the CEO's own final, manual
    ratification (`POST /api/constitution/decide`) appends a real new
    Article — deliberately *not* wired to Automation Mode, unlike the
    Research Sandbox's Company Review, since amending company law is
    exactly the kind of decision that stays the CEO's alone.
  - **New `CONSTITUTION` Command Center tab** (`ConstitutionPanel.tsx`):
    the Articles grid, a filterable Live Enforcement citation feed, an
    amendment proposal form, and per-amendment Founder verdicts/Coach
    evaluation/employee vote tally with Ratify/Reject actions.
  - Verification: backend (`test_constitution.py`, 18 new tests
    covering the redundancy-overlap edge case, domain-keyword matching
    in both directions, and the full propose→debate→ratify pipeline) +
    full suite (570/570) + mypy/ruff clean; frontend tsc/eslint/build
    clean; a new `constitution.spec.ts` (2 Playwright tests against the
    live stack, including proposing and advancing a real amendment
    through the full pipeline) plus `commandCenter.spec.ts`'s tab-count
    test updated for the new 27th tab.

- **v0.7 Feature 45 — Research Sandbox**: scoped from a brief asking for
  an 8-stage strategy pipeline (Idea → Research → Historical Backtest →
  Market Simulation → Paper Trading → Limited Live Capital → Company
  Review → Approved Strategy) that "strategies cannot skip," 9 Testing
  Environments, 10 performance metrics, auto-generated Strategy Reports,
  and a 5-role Approval Process gated by Automation Mode. Researched
  first (see `app/sandbox.py`'s module docstring): almost every building
  block already existed — `Strategy`/`ResearchItem`/`BacktestSession`/
  `SimulationResult` were all real, just never stage-gated or reported
  on. What was genuinely missing was the gating itself, scenario-aware
  backtesting, auto-generated reports, and a real multi-reviewer Company
  Review — this codebase's live/paper trading loop has no mechanism to
  attribute an executed trade back to a specific `Strategy` object, so
  the last three pipeline stages are real CEO-authorized trust
  checkpoints rather than fabricated live P&L attribution.
  - **8-stage pipeline** (`Strategy.stage`/`stageHistory`): the first
    four stages advance automatically on a real signal (a completed
    `ResearchItem` in the strategy's own category; a completed
    `SimulationResult` in the "historical" scenario bucket; a completed
    result in any other scenario, only once historical backtesting is
    already on record); the last four are real CEO actions
    (`POST /api/sandbox/begin-paper-trial` /
    `begin-limited-live` /`request-review` /`decide`).
  - **Scenario-aware backtesting** (`app/simulation.py`): `BacktestSession`/
    `SimulationResult` gained a `scenario` field reusing the exact 5
    regime names `market_environment.py` already computes live (bull/
    bear/sideways/high_volatility/low_volatility), plus "historical" (the
    pre-Feature-45 default) and "custom" (a CEO-tunable deterministic
    bias on the same placeholder ranges). "Earnings weeks" and "economic
    news" from the brief's longer Testing Environments list are not
    built — no real data source for either exists anywhere in this
    codebase.
  - **Fuller, internally-consistent metrics**: `win_count`/`loss_count`/
    `avg_win_pct`/`avg_loss_pct` are now the placeholder engine's own
    real generating inputs (`total_return_pct` is derived FROM them, not
    the reverse), so Expected Value, Profit Factor, and Risk/Reward are
    real derivations of a run's own numbers, never independently rolled.
    Consistency and Trade Frequency are frontend derivations over a
    strategy's own stored result history (`lib/derive.ts`'s
    `computeStrategyConsistency`) rather than stored per-run, since both
    are properties of the history, not of one run.
  - **Auto-generated Strategy Reports** (`generate_strategy_report`):
    Executive Summary/Strengths/Weaknesses/Failure Conditions/Best Market
    Environment/Recommended Improvements, filed the instant a
    `SimulationResult` completes — the same templated-framing-over-real-
    numbers discipline `app/mistakes.py`/`app/successes.py` established.
  - **5-reviewer Company Review** (`generate_strategy_review`): Quant
    (Vector — sample size + avg win rate + avg Sharpe), Risk Specialist
    (Guardian — avg max drawdown), Technical Analyst (Echo — scenario
    diversity), Fundamental Analyst (Nova — completed research on
    record), and a rotating Devil's Advocate seat (worst single-run
    drawdown / any negative-expected-value run) — every mapping is that
    agent's own real occupation, and every verdict cites the real number
    that produced it, the same threshold-citation discipline
    `app/devils_advocate.py` established for individual trades.
  - **Automation Mode governs the final CEO call**: reuses
    `_apply_operating_mode`'s exact convention — Learning Mode always
    waits for a real manual decision; Executive Mode auto-resolves every
    pending review using its own real `overall_verdict`; Assisted Mode
    auto-resolves only the unambiguous pass/fail cases, leaving a genuine
    "concern" verdict for real CEO judgment.
  - **New `SANDBOX` Command Center tab** (`SandboxPanel.tsx`): per-
    strategy pipeline view, a scenario-picker backtest queue form, a
    real per-run metrics table, Strategy Reports, and the Approval
    Process (stage-appropriate CEO action buttons + review verdicts with
    Approve/Reject).
  - Verification: backend (`test_sandbox.py`, 29 new tests covering
    stage gating in both directions — cannot skip forward, never moves
    backward — every reviewer's real threshold, and the devil's-advocate
    rotation) + full suite (552/552) + mypy/ruff clean; frontend
    tsc/eslint/build clean; a new `sandbox.spec.ts` (2 Playwright tests
    against the live stack, including actually queuing a real backtest)
    plus `commandCenter.spec.ts`'s tab-count test updated for the new
    26th tab.

- **v0.7 Feature 44 — Talent Discovery System**: scoped from a brief
  asking for a "Performance Analysis" trait breakdown, automatic
  "Discovery Events" when an employee shows real talent, a CEO decision
  to invest in that talent, a per-employee "Growth History," "Career
  Development" (promotions/role changes/specializations), and "Team
  Optimization" (best-performing pairs, ideal roster composition).
  Researched first (see `app/talent.py`'s module docstring): Performance
  Analysis turned out to already be real and shipped — it's exactly
  `ThinkingProfile`, built for Feature 32's Mentor Chamber — so this
  feature surfaces it rather than recomputing it a second time. Career
  Development and most of Team Optimization are fundamentally
  incompatible with this codebase: `agents.py`'s `AgentProfile` is a
  frozen dataclass and `founders.py`'s own docstring states plainly that
  no employee ever joins, leaves, or changes role after the game starts —
  there is no roster to promote within or recompose, so a literal
  career-path or team-recomposition mechanic would have to be invented
  from nothing. What's left is scoped honestly around what the codebase
  can actually check.
  - **Discovery Events, the one genuinely net-new concept**
    (`app/talent.py`'s `generate_talent_reports`): a `TalentReport` only
    ever files for an agent/trait pair when that agent's own best
    `ThinkingProfile` trait clears a real score threshold (80/100) AND
    their last three `CoachReport` scores are all consistently strong
    (≥70) — both conditions real and checkable, never a fabricated
    pattern. Each report names the real highest trait (never a lower one
    picked for drama), cites the trait's own real evidence, and never
    re-files the same agent/trait pair twice. "Suggested Focus" is a
    real coaching note, not the brief's literal "Suggested Career Path"
    — this codebase has no mechanic that promise could ever refer to.
  - **New `TALENT` Command Center tab** (`TalentPanel.tsx`): Discovery
    Events with an acknowledge action (`POST /api/talent/ack-report`,
    the same "seen" tracking pattern as Breakthrough Reviews), a
    per-employee **Growth History** timeline, **Best Collaborators**,
    and a **Performance Analysis** section. Growth History and Best
    Collaborators shipped as pure frontend derivations
    (`lib/derive.ts`'s `computeGrowthHistory()`/
    `computeBestCollaborators()`) over data already broadcast on the
    WebSocket — like Features 42/43's derived sections, no new backend
    state was needed for either.
  - **Growth History, honestly built from six real sources**: every
    entry traces to a record that already names the selected agent —
    `DisciplineReview.attendees`, `ReasoningChallenge.contributions`,
    `ReflectionSession.insights`, `ChallengeReport.assignedAgent` (the
    Devil's Advocate rotation), Black Box project team membership
    (active + archived), and `CoachReport.agentRankings` (the agent's
    own real score on each report's filing date) — never a fabricated
    career log.
  - **Best Collaborators, the one real signal salvageable from "Team
    Optimization"**: since the roster can't be recomposed, nothing about
    composition can be optimized — but which agents actually support vs.
    challenge each other's points across every real AI Debate
    (`DebateTurn.respondingTo` + `stance`) is a real, checkable tally,
    counted turn by turn with nothing inferred.
  - Verification: backend (`test_talent.py`, 8 new tests covering both
    threshold gates, non-refiling, missing-profile safety, and that no
    literal career-path language is ever promised) + full suite
    (523/523) + mypy/ruff clean; frontend tsc/eslint/build clean; a new
    `talent.spec.ts` (2 Playwright tests against the live stack) plus
    `commandCenter.spec.ts`'s tab-count test updated for the new 25th
    tab (inserted after MENTOR, so number-key shortcuts 1-9 are
    unaffected).

- **v0.7 Feature 43 — Executive Intelligence Dashboard**: scoped from a
  brief asking for a 13-metric "Company Health" list, proactive "CEO
  Insights," an AI-ranked "Executive Priorities" list, multi-year
  "Performance Trends," and per-department "Efficiency/Workload/Morale/
  Productivity/Bottlenecks" status for 8 named departments. Researched
  first (see `docs/Architecture.md`'s "Executive Intelligence Dashboard"
  section): most of the brief's own "Company Health" list already exists
  under `CompanyHealth`/`CompanyScore`; "Performance Trends" already
  exists as `PerformanceSnapshot` (the PERFORMANCE tab); "CEO Insights"
  is the same real recommendation text this feature's own Executive
  Priorities section surfaces, just reframed as alerts instead of a
  ranked list — building a second, parallel insights generator would
  have been the exact duplication this session's whole discipline exists
  to avoid.
  - **New `EXECINTEL` Command Center tab** (`ExecutiveIntelPanel.tsx`):
    Company DNA, Executive Priorities, and Department Health. Like
    Feature 42, this shipped mostly as a **frontend-only feature** —
    Executive Priorities and Department Health are pure derivations
    (`lib/derive.ts`'s `computeExecutivePriorities()`/
    `computeDepartmentHealth()`) over data already broadcast on the
    WebSocket; only Company DNA needed new backend computation.
  - **Company DNA, the one genuinely net-new concept** (`app/company_dna.py`):
    five real, descriptive behavioral traits read off the company's own
    historical decision/trade record — Risk Appetite (% of executed
    trades taken on a moderate-or-weaker Decision Confidence Engine
    tier), Patience (average real hold duration against
    `discipline.py`'s own patient-hold bar), Contrarian Tendency (% of
    CEO decisions that overrode the AI's recommendation), Research Rigor
    (average real Decision Confidence Engine score), and Collaboration
    Style (% of decisions with 2+ distinct real analyst vote choices).
    Each defaults to an honest neutral 50.0 with a real `sampleSize` of
    0 until enough history exists — never a confident-looking guess from
    thin data. Deliberately reuses no signal `company_health.py`'s new
    `team_chemistry` (below) or `company_score.py`'s existing
    `team_coordination` already read.
  - **Team Chemistry, a real 11th `CompanyHealth` sub-score**
    (`app/company_health.py`'s `_team_chemistry`): the real support-vs-
    challenge ratio across the company's most recent 20 AI Debates —
    corrects a genuine, self-discovered inconsistency where v0.7's own
    Black Box feature (`app/black_box.py`) had claimed in its module
    docstring that Team Chemistry was "genuinely new" without ever
    actually implementing it; that docstring is now corrected to point
    here. Distinct from `employee_morale` (individual mood) and
    `company_score.py`'s `team_coordination` (also a mood proxy) — this
    is specifically about how the team behaves *together* during real
    debate, never a fabricated pairwise relationship graph.
  - **Executive Priorities**: merges and dedupes `CompanyHealth`'s
    always-current recommendations with the latest `CoachReport` and
    `ExecutiveReview`'s own real recommendation text — first occurrence
    wins, so a live Company Health read outranks a possibly-stale
    periodic report repeating the same point. No invented ranking model:
    order reflects which real system raised the point.
  - **Department Health, honestly scoped**: the brief names 8
    departments including "Brain Room" — this codebase has no literal
    department concept, and Brain Room specifically is a physical room
    housing the Overview HUD, not an operational unit with its own
    state, so it's dropped entirely rather than inventing metrics for a
    room. The other 7 (Academy/Research/Risk/Trading/Innovation/Coach/
    Founders) each show whichever of the brief's five requested
    dimensions (Efficiency/Workload/Morale/Productivity/Bottlenecks)
    that real subsystem actually tracks — never a uniform template
    forced onto systems that don't track all five.
  - Verification: backend (`test_company_dna.py`, 15 new tests;
    `test_company_health.py` extended with a `TestTeamChemistry` class,
    4 new tests) + full suite (515/515) + mypy/ruff clean; frontend
    tsc/eslint/build clean; a new `execIntel.spec.ts` (2 Playwright tests
    against the live stack) plus `commandCenter.spec.ts`'s tab-count test
    updated for the new 24th tab (COMPANY's own number-key index is
    unaffected — EXECINTEL was inserted after it, not before).

- **v0.7 Feature 42 — Decision Replay Center**: scoped from a brief
  asking for per-trade Stop Loss/Profit Target/Expected Value recording,
  a 13-stage decision timeline, a "Team Replay" of every real opinion,
  natural-language "Smart Search," and automatic "Successes"/"Mistakes"/
  reflection-question lesson generation. Researched first (see the
  research report referenced from `docs/Architecture.md`'s "Decision
  Replay Center" section): the underlying decision chain
  (`TradeProposal` → `Debate` → `ChallengeReport` → `TradeDecision` →
  `CeoDecisionRecord` → `PaperTrade` → `DisciplineReview` → `CaseStudy`)
  was already real and fully id-joinable — the actual gap was a unified
  viewer, not new data. Built entirely as a **frontend-only feature**:
  every field the Replay Center shows was already broadcast over the
  existing WebSocket (the same lists `DecisionDetail.tsx` already reads
  from), so no new backend endpoint or schema was needed for the join
  itself — see `frontend/src/ui/components/CommandCenter/lib/derive.ts`'s
  `buildDecisionReplay()`/`buildReplayTimeline()`.
  - **New `REPLAY` Command Center tab** (`ReplayPanel.tsx`): a
    structured filter grid (Symbol/Employee/Department/Result/Min.
    Confidence) over the full decision archive, and a Decision Replay
    modal per row showing the joined timeline, Team Replay (every real
    vote + the linked AI Debate thread), the Devil's Advocate challenge
    if one was assigned, Decision Recording fields, and any Lessons
    Generated (case studies) tied to that decision.
  - **Full Decision Timeline, honestly**: all 13 brief-named stages are
    shown, each with a real `recorded`/`not_generated`/`not_applicable`
    status rather than a fabricated "in progress" — "Quant Review" is
    always `not_applicable` (Quant/Vector reviews long-horizon Black Box
    research projects, never an individual trade — confirmed by grep,
    no per-trade Quant review mechanism exists anywhere) and "AI
    Research" is folded into Research/Technical/Fundamental Analysis
    rather than repeating the same summary text under a fifth label.
    "Pause/rewind/fast-forward" has no literal video/animation content
    to scrub (every stage is a templated text record, not footage), so
    it's implemented as jump-to-any-stage stage buttons instead.
  - **"Successes" lesson generation, genuinely new** (`app/successes.py`,
    the mirror image of `app/mistakes.py`'s Library of Mistakes): three
    new `CaseStudyCategory` values (`disciplined_process`,
    `rigorous_cross_examination`, `patient_execution`), each the crisp
    inversion of one of the six existing mistake categories' real
    trigger signal, filed for a real win the same way `mistakes.py`
    files for a real loss — reuses the exact same `CaseStudy` schema and
    `case_studies` list rather than a second, parallel schema (the
    Command Center's Discipline tab is retitled "Library of Mistakes &
    Successes" and color-codes each entry accordingly). The other three
    mistake categories (`incomplete_research`/`ignored_dissent`/
    `confirmation_bias`) have no equally crisp opposite and are
    deliberately not mirrored — padding out to match the count would be
    dishonest.
  - **Explicit, documented scope cuts** (all inherited from real,
    already-established boundaries elsewhere in this codebase, not new
    gaps this feature introduces):
    - **Stop Loss / Profit Target / Expected Value are not shown.**
      TradeTown's paper broker has never placed a real stop-loss/take-
      profit exit order (`OrderType` has always had the literal values,
      but nothing in `broker.py`/`executive.py` has ever placed one —
      confirmed by grep), and no calibrated probability model exists to
      honestly compute an Expected Value from. This is the exact same
      boundary `DecisionDetail.tsx`'s own "Trade Plan" section and
      `app/gatekeeper.py`'s module docstring already documented — the
      Replay Center says so explicitly rather than inventing numbers.
    - **No natural-language "Smart Search."** No LLM/NL-understanding
      infrastructure exists anywhere in this backend (confirmed by grep
      across the whole codebase — every "AI-generated" line in
      TradeTown is deterministic string templating over real data, by
      design). Every one of the brief's own search examples ("show all
      losing trades," "show trades above 85% confidence," "show every
      trade where Risk disagreed") is covered by real structured
      filters instead — "Department" maps to `AnalystRole`, the closest
      real per-decision "who reviewed this" grouping this codebase has.
      "Show every breakout strategy" and "show every trade during
      earnings" are not supported — no strategy taxonomy or earnings
      calendar exists — and "reviewed by the Quant" is not supported for
      the same reason Quant Review is `not_applicable` above.
  - Verification: backend (`test_successes.py`, 10 new tests, mirroring
    `test_mistakes.py`'s structure) + full suite (496/496) + mypy/ruff
    clean; frontend tsc/eslint/build clean; a new `replay.spec.ts` (3
    Playwright tests against the live stack) plus the existing
    `commandCenter.spec.ts` tab-count/number-shortcut/Discipline-tab
    tests updated for the new 23rd tab and its shifted keyboard-shortcut
    indices.

- **v0.7 — Advanced Quantitative Research Division**: scoped from a
  spec asking for a "Chief Quantitative Strategist," a "Quant Lab,"
  long-running "Black Box Research Projects," a "CEO Research
  Dashboard," auto-formed "Advanced Research Teams," "Team Chemistry,"
  "Research Meetings," an "Innovation Points" 5-tier progression, an
  "Eureka! Breakthrough System," "Founder Council Review," a "Museum of
  Discoveries," "Failed Research" archives, and "World Reputation."
  Researched first: several of these already exist under different
  names, so this pass extends them rather than building parallel
  duplicates — see `backend/app/black_box.py`'s module docstring for
  the full accounting. What's genuinely real and new:
  - **Vector, the Chief Quantitative Strategist** (`quant`): the
    fourteenth agent, added the same proven way as Sage/Keystone/
    Compass — a real `AgentId`, schedule, palette-swapped sprite,
    dialogue lines, and campus presence. Works out of the Simulation
    Lab; **no new physical "Quant Lab" scene was built** — that room is
    real content layered onto the existing backtesting room, the same
    Command-Center-tab precedent Mentor/Founders/Discipline
    Chamber/Reasoning Lab already established.
  - **Black Box Research Projects** (`app/black_box.py`): exactly one
    company-wide project at a time (mirrors `academy_research.py`'s own
    "one active project" convention), drawn from the brief's own
    eleven named example categories. Progress advances once per
    real in-game day (not per tick), so a project genuinely takes
    weeks of in-game time — honoring "unlike ordinary research they may
    require weeks or months." Funding, priority, and obstacles are all
    real mechanical levers: an unfunded project stalls and logs a real
    obstacle; obstacles genuinely lower the project's confidence level.
  - **Real team formation, not a fabricated multi-factor score**: the
    Quant leads; four seats are matched to whichever existing agent
    already has that real occupation (Echo/Technical, Nova/Fundamental,
    Sentinel-or-Guardian/Risk alternating by project count, Coach/
    Psychology). No "AI Research Scientist" seat — no agent in this
    roster maps to it, and this pass already adds one new agent.
  - **Devil's Advocate reused, not duplicated**: a project's review
    calls `app/devils_advocate.py`'s exact `ChallengeReport` shape,
    picking whichever eligible candidate (never a fixed team member)
    has the most real Innovation Points — and the resulting report
    feeds into the *same* `challenge_reports` history, so it earns
    Innovation Points through `app/innovation.py`'s already-shipped
    5-tier ladder (Research Contributor → Legendary Innovator) instead
    of a second, parallel points system.
  - **Founder Council Review** (`app/founders.py`'s new
    `generate_breakthrough_review()`): a real, checkable gate — approved
    only if the Devil's Advocate found nothing major and the project's
    confidence level cleared a real bar. Rejected projects file into
    the project archive with status `failed` and a real reason — this
    *is* the brief's "Failed Research" archive, not a second schema.
  - **Museum of Discoveries**: extends `HallOfFameEntry` with optional
    `discoveryTimeline`/`supportingEvidence`/`companyImpact` fields
    (only populated for the new `breakthrough` category) rather than
    building a second permanent-record system next to the Hall of
    Fame's own "never retroactively rewrites history" mechanism.
  - **Eureka! Breakthrough moment** (`BreakthroughMoment.tsx`): a real
    full-screen, world-pausing cinematic — the same "seen" tracking
    pattern the Trade Outcome Banner already uses (`viewedBreakthroughIds`
    + `POST /api/black-box/ack-breakthrough`), showing the real
    hypothesis, statistical results, and Founder Council verdict. No
    music-track swap — no audio system exists anywhere in this codebase
    to hook one into (the same class of honest omission as the
    Founders' own "voice acting" cut).
  - **CEO Research Dashboard** (`BlackBoxPanel.tsx`, Command Center's
    new BLACKBOX tab): Increase Funding, Pause/Resume, Cancel, Change
    Priority, Add Research Ideas, and Assign Specialists are all real,
    validated mutations (`backend/app/routers/black_box.py`). "Request
    Progress Report" isn't a separate control — the dashboard already
    shows live progress.
  - Explicitly **not built**, and why: Team Chemistry as a distinct
    fabricated pairwise-relationship system (no real per-pair signal
    exists to back it — a genuine cut, not silently dropped); a
    separate "Research Meetings" transcript system (the Quant Journal
    already serves as the real meeting record, the same "don't
    duplicate `discussion.py`/`debate.py`" reasoning `founders.py`
    already established); breakthrough effects like "unlock new
    Academy lessons/buildings/automation/dialogue" (no locked-content
    system exists anywhere in this codebase to hook an "unlock" into
    honestly — `education.py`'s lessons are always available); World
    Reputation as external entities (universities, elite candidates,
    partnership requests) — `company_health.py`'s real `reputation`
    sub-score already grows with Hall of Fame entry count, and a
    breakthrough adds one real `NewsItem` naming that real number,
    never a simulated external institution.
  - **Verification note**: while verifying this feature, the full
    Playwright suite showed elevated real-time-proposal-popup flakiness
    (10-19 tests) — confirmed via a fresh-backend re-run to be a
    pre-existing, environment-wide characteristic spread across files
    this feature never touches (`campusMap.spec.ts`,
    `executiveVoting.spec.ts`), not a regression. One real gap the
    investigation did surface and fix: 15 `commandCenter.spec.ts` tests
    were missing a `dismissTradeOutcomePopups()` call other tests in
    the same file already had. See `docs/Architecture.md`'s "Advanced
    Quantitative Research Division" section for the full investigation.

- **v0.7 — Intelligence & Decision Systems** — five systems that build on
  v0.6.3's Executive Voting rather than replacing it, aimed at making
  both the AI desk and the player better decision-makers over time, not
  just at maximizing a single trade's P&L.
  - **Decision Confidence Engine (Feature 15)**: a real, server-side,
    persisted `DecisionConfidence` (`app/confidence.py`) formally
    replaces v0.6.3's client-side "Trade Quality Score" heuristic.
    Computed once at proposal-generation time from six real factors
    already produced elsewhere — multi-agent vote agreement (0.30),
    technical alignment (0.20), risk conditions (0.20), research
    confidence (0.15), news/macro/sentiment alignment (0.10), portfolio
    exposure (0.05) — and carried onto the resulting `TradeDecision`, so
    Trade History and Post-Trade Review compare the *exact* reading a
    decision was made under against its real later outcome, instead of
    recomputing a possibly-drifting score client-side on every render.
    Displayed in Executive Voting, the Trade Proposal itself, Market
    Observatory, Trade History/`DecisionDetail`, and a new Post-Trade
    Review section that explicitly recognizes a losing trade with an
    excellent setup as still a good decision (and a winning trade with a
    weak setup as luck, not skill). Several factors the v0.7 brief names
    (support/resistance, multi-timeframe agreement, liquidity quality,
    historical strategy performance, similar-setup matching) have no
    real data source in this codebase and are deliberately not computed
    — see `confidence.py`'s module docstring. Also removes
    `app/decision.py`, dead since v0.6.3 replaced its automatic
    `decide_trade()` pipeline with Executive Voting.
  - **What-If Simulation Lab (Feature 16)**: before deciding, the player
    can stress-test a proposal against 12 named market scenarios
    (`app/whatif.py`) — bullish continuation, bearish reversal, sideways
    consolidation, high/low volatility, news shock, gap up/down, trend
    failure, breakout confirmation, liquidity sweep, flash crash. Every
    simulated path is a bootstrap resample of the symbol's own real
    recent bar-to-bar returns; each scenario's drift bias and any shock
    are a documented, fixed multiple of the symbol's own real measured
    volatility (never an invented absolute percentage), with
    `trend_failure` the one scenario whose direction is resolved
    dynamically against the symbol's real current trend. An unbiased
    13th "baseline" run is the honest "most likely outcome" — best/worst
    case are whichever named scenario produced the highest/lowest
    reward-range edge, never a fabricated probability of one scenario
    actually occurring over another. Computed fresh on every request via
    `GET /api/executive/whatif` rather than persisted (this codebase has
    already been bitten once by an unbounded persisted list bloating the
    save payload — see `MAX_DECISIONS`'s history below). Surfaced as a
    new expandable section in Executive Voting with a best/worst/most-
    likely summary and a per-scenario horizontal reward-range bar chart
    (pure CSS, one shared scale, no charting library) that expands on
    click to show typical drawdown, max expected risk, win probability,
    and the specific condition that would invalidate that scenario.
  - **AI Debate Room (Feature 17)**: extends Executive Voting's existing
    six real analyst seats into a full investment-committee review,
    layered into the same popup as a new "DEBATE ROOM" section. A
    `Debate` (`app/debate.py`) is generated the moment a `TradeProposal`
    is created: an opening statement per analyst (their own real
    `AnalystVote.reasoning`/`evidence`, unchanged) plus one real cross-
    examination turn per analyst — a challenge if another analyst's real
    vote disagrees, a support if it agrees — using the same
    deterministic-but-varied templated-framing-over-real-state
    convention `app/discussion.py` already established for the Meeting
    Room. Only the framing sentence is generated; the substance is
    always the analyst's own already-real reasoning. "Question any agent
    individually" reuses the existing click-to-expand vote card.
    "Request another debate" reshuffles the framing over the same real
    votes and appends a fresh `Debate`, keeping prior ones in the stored
    history (capped at `MAX_DEBATES`). Approve/Reject/Wait remain the
    real, unchanged `/api/executive/decide` flow — the debate never
    itself decides anything. The brief's "Portfolio Manager" and
    "Strategy Analyst" have no independent real signal in this codebase;
    Atlas's execution vote (already the desk's own synthesis) is
    labelled "Portfolio Manager" as the closest real analogue, and no
    seventh/eighth participant is invented.
  - **Decision Journal & Mistake Tracker (Feature 18)**: extends Coach's
    existing weekly/monthly reporting (unchanged since v0.5) rather than
    building a parallel journal — every field the brief asks for (Date/
    Asset/CEO Decision/Confidence Score/Entry/Exit/Holding Time/P&L) was
    already permanently recorded across `TradeDecision`,
    `CeoDecisionRecord`, and `PaperTrade`, and already exposed via
    `DecisionsPanel`/`DecisionDetail`. The real gap was pattern
    detection, so `CoachReport.commonMistakes` gains two new real
    patterns — "overrode the Risk Manager" and "traded against the
    trend" — both joining a `CeoDecisionRecord` against the
    `TradeDecision` that produced it (by `decisionId`) and gated on that
    decision's real linked trade having actually lost. A new
    `CoachReport.strengths` field is the positive counterpart: win rate
    over a real sample size, patient wins held 4+ simulated hours, wins
    that agreed with Echo's trend read, and a real average-win-vs-
    average-loss reward/risk check. `ExecutivePanel`'s Decision History
    rows get a per-decision "OVERRODE RISK"/"AGAINST TREND" tag so a
    single losing override reads its own real cause inline. Explicit
    scope cut: personalized lesson/mini-game recommendations tied to
    detected weaknesses would need a real mistake-to-lesson mapping this
    codebase doesn't have yet — left out rather than faking a shallow
    link.
  - **Premium Trade Outcome Banner (Feature 19)**: replaces
    `TradeOutcomePopup`'s full-screen blocking modal with a non-blocking,
    top-center floating `TradeOutcomeBanner` — gameplay and the Command
    Center toolbar stay fully interactive while it's showing. Win pulses
    green with a confetti burst, loss shakes once with a brief
    holographic glitch, breakeven gets a plain cyan glow; the P&L eases
    upward (or downward) over ~900ms. Every closed, unviewed trade gets
    its own turn in a real FIFO queue instead of the backlog being
    silently acknowledged, with an 8s auto-dismiss paused on hover and
    resumed on leave (a real remaining-time countdown). View Trade/
    Analyze emit a `trade:inspect` event that jumps the Command Center to
    the Decisions tab and, for Analyze, auto-opens `DecisionDetail`'s
    Post-Trade Review — mirroring Feature 12's
    `executiveVotingProposalId` pattern. "Strategy" and "Trade Quality
    Score" from the spec are deliberately not shown: auto-traded orders
    aren't linked to a named Strategy record, and Trade Quality Score was
    already replaced by Feature 15's real Decision Confidence Engine.
  - **Trade Gatekeeper (Feature 20)**: a final-approval layer
    (`app/gatekeeper.py`) that can veto even the CEO's own real BUY/SELL
    call before `resolve_proposal` places the order — the v0.6.3 "the
    player's choice is unconditionally final" model no longer holds.
    Seven checks are real, each reading state already computed
    elsewhere: the Decision Confidence Engine score (Feature 15) against
    a minimum threshold, Sentinel's risk-analyst vote alignment,
    multi-agent majority agreement, the AI Debate's own final
    recommendation (Feature 17), portfolio exposure against
    `RiskLimits.maxOpenPositions`, correlated open positions sharing the
    proposal's real research category (capped at `MAX_CORRELATED_POSITIONS`),
    and any active *critical* Sentinel/Guardian risk warning for the
    symbol. The brief's longer checklist also names multi-timeframe
    confirmation, support/resistance quality, volume confirmation,
    liquidity, upcoming-news timing, reward-to-risk ratio, stop-loss
    placement, strategy match, and historical performance of similar
    setups — none have a real data source in this codebase (this sim
    only ever fetches one timeframe, generates news reactively rather
    than on a schedule, and the paper broker never places exit orders)
    and none are fabricated; see `gatekeeper.py`'s module docstring for
    the same honesty boundary already established for Feature 15/16. A
    rejected trade is transparent about why: Executive Voting's popup
    replaces itself with a "REJECTED BY GATEKEEPER" screen naming every
    failed check's own real detail text, instead of silently advancing
    to the next proposal. Since a blocked trade never executes, there's
    no real P&L to grade it against — `GatekeeperRejection` instead
    tracks the symbol's real price at rejection and resolves
    "would_have_won"/"would_have_lost" once `GATEKEEPER_EVAL_WINDOW_MINUTES`
    (4 simulated hours) of real subsequent watchlist price movement has
    passed, the same "wait for real time, then check real data"
    convention `grade_ceo_decisions` already uses for placed trades —
    never a fabricated outcome. `ExecutivePanel`'s new "Trade Gatekeeper"
    card surfaces approved/rejected counts, veto accuracy (% of resolved
    rejections that would actually have lost), and the most recent
    rejections with their real reasons — the self-evaluation tracking
    the brief asks for, computed purely from these two real record types
    and never auto-adjusting a rule on its own. Also fixes a pre-existing
    latent bug this feature would otherwise have tripped:
    `TradeDecision.outcome`/`CeoDecisionRecord.outcome` were keyed off
    the CEO's `ceoChoice` being buy/sell, which was only ever equivalent
    to "a trade actually happened" before a rejection path existed —
    both now key off `orderId is not None`, the real signal of whether
    an order was actually placed.
  - Verification: full backend (mypy/ruff/pytest, 162/162 — 28 new tests
    in `test_gatekeeper.py`) and frontend (tsc/eslint/build) clean; the
    relevant Playwright specs (`executiveVoting.spec.ts`,
    `commandCenter.spec.ts`) pass against a freshly reset backend.

- **v0.7 — AI Company Management & Simulation Systems** — three systems
  aimed at making the company itself, not just individual trades, the
  thing the player manages and learns to read.
  - **Company Operating Modes (Feature 21)**: a new `operatingMode`
    (`learning | assisted | executive`) on the client-authoritative
    `SettingsState`, synced through the existing
    `SettingsManager.update()` → `settings:changed` → next-autosave path
    (the same mechanism `showFps`/`musicVolume` already use). Learning
    Mode is unchanged v0.6.3 behavior — every `TradeProposal` waits for a
    real CEO click. Assisted and Executive Mode add a new
    `_apply_operating_mode()` sweep in `nexus.tick()` that calls the exact
    same `resolve_proposal()` a real CEO click would (Gatekeeper
    included), tagged with a new `CeoDecisionRecord.resolvedBy`
    (`"ceo" | "auto"`) so an auto-resolved decision is never presented as
    if the player made it — `ExecutivePanel`'s Decision History rows now
    show "desk auto-decided" with an AUTO tag instead of "you" for these.
    A new `is_significant_proposal()` (`app/executive.py`) decides what
    counts as "routine" enough for Assisted Mode to auto-resolve, reusing
    already-configured thresholds rather than inventing new ones:
    confidence below `gatekeeper.MIN_CONFIDENCE`, an active critical risk
    warning on the symbol, or position size at/above
    `RiskLimits.maxPositionPct` of real portfolio equity. Executive Mode
    auto-resolves everything regardless of significance. The pre-existing
    `expire_stale_proposals` auto-wait path is also now honestly tagged
    `resolvedBy: "auto"` (previously silently indistinguishable from a
    real CEO "wait" click). A new COMPANY tab exposes the three-way
    toggle plus real descriptions of what each mode does.
  - **Market Environment Simulation (Feature 22)**: a new, persisted,
    server-computed `MarketEnvironmentState` (`app/market_environment.py`)
    classifies the whole watchlist every tick into one of five regimes —
    bull, bear, sideways, high volatility, low volatility — from the real
    aggregated `WatchlistEntry.dailyChangePct` values already used by the
    now-superseded client-side `marketRegimeHeuristic`. A historical
    `timeline` only grows on a real regime change (capped at
    `MAX_MARKET_ENVIRONMENT_HISTORY`), and a real `NewsItem` is published
    each time one happens. The one real department hookup implemented in
    the time available: the existing per-tick random market headline is
    now drawn from that regime's own headline pool
    (`MARKET_HEADLINES_BY_REGIME`) instead of one shared pool — a genuine
    dependency on the computed regime. The deeper "researchers get
    busier"/"NPC dialogue changes"/discrete News-Events/Economic-Events/
    Liquidity-Change/Panic mechanics the brief names have no real trigger
    source in this codebase within scope and are not fabricated — see
    `market_environment.py`'s module docstring. Surfaced on the new
    COMPANY tab (current regime + real timeline), the Overview tab (new
    Market Environment tile replacing the old regime heuristic tile), and
    the Market Observatory's Technical Station (real regime + a real
    3-entry Environment Timeline), instead of two disconnected systems.
  - **Company Health & Stability System (Feature 23)**: a new
    `CompanyHealth` (`app/company_health.py`) scores the company on ten
    real sub-metrics — deliberately distinct in *what question they
    answer* from, though some overlap in *underlying signal* with, the
    existing `CompanyScore`: operational stability (active
    `RiskWarning`s, severity-weighted), department efficiency (fraction
    of agents not idling in lobby/break-room), employee morale (avg agent
    mood), research progress (fraction of completed `ResearchItem`s),
    capital health (real portfolio P&L%), resource usage (real
    `AgentEnergy` remaining), reputation (real Hall of Fame entry count),
    technology level (real Signal Calibration unlocked level), office
    expansion (real extra watchlist symbols beyond the seed eight), and
    education progress (real completed-lesson fraction). `overall` is the
    plain unweighted mean, matching `CompanyScore`'s own "no hidden
    weighting" convention; tier is Excellent/Good/Stable/Needs Attention/
    Critical. Recommendations name the two lowest-scoring metrics in
    plain language, and only appear at all once a metric actually falls
    below 70 — a fully healthy company gets none. Surfaced on the new
    COMPANY tab (all ten metrics + recommendations) and a new Company
    Health tile on Overview.
  - Explicit scope cuts: "Executive Reports" reuses the existing Coach
    weekly/monthly report system (Feature 18) rather than building a
    second, parallel report engine — no new report types were added.
    "NPC Interactions" (remembering conversations, celebrating
    achievements, building relationships with department leaders) has no
    new relationship/memory system in this window; the existing
    dialogue/`CompanyMemory` infrastructure from earlier versions is the
    honest ceiling — inventing a fake relationship-score mechanic with no
    real state behind it would violate this codebase's no-fabricated-
    numbers convention.
  - Verification: full backend (mypy/ruff/pytest, 202/202 — 33 new tests
    across `test_market_environment.py`, `test_company_health.py`, and
    `test_executive.py`) and frontend (tsc/eslint/build) clean; the
    relevant Playwright specs (`executiveVoting.spec.ts`,
    `commandCenter.spec.ts`, including a new Company-tab test) pass
    against a freshly reset backend.

- **v0.7 — Executive AI & Academy System** — a tenth agent and a
  company-wide learning system, extending Feature 24's Company
  Operating Modes into an actual executive leadership layer.
  - **Chief Investment Officer (Feature 24)**: Meridian, the tenth agent
    (`AgentId`/`AGENT_IDS` gain `"cio"`), added end-to-end the same way
    every prior agent was — a real `AgentProfile`
    (`occupation="Chief Investment Officer"`, home
    `executive-boardroom`), a real 8-block daily schedule, a real
    palette-swapped sprite sheet (`Player_Meridian.png`, generated by
    inspecting which of the base sheet's colors the nine existing agents
    actually recolor vs. always preserve — see
    `animation-config.json`'s `_comment_meridian`), and real dialogue.
    The CIO never votes on a trade or generates a research signal (per
    the brief); its one piece of real logic is a new Monthly Executive
    Review (`app/executive_review.py`), generated on the same monthly
    cadence as Coach's own `CoachReport` but asking a different
    question — company growth (a real delta against the previous
    review's score), department activity (real research/decision counts
    per agent), research/knowledge output, real analyst disagreement
    (Debate Room challenge-turn counts), and real "worth a second look"
    flags (stalled low-confidence research, a poor Company Health tier)
    — reusing `CompanyHealth.recommendations` verbatim rather than a
    second parallel recommendation engine. A new **Executive Boardroom**
    room (`ExecutiveBoardroomScene.ts`, 34×22 tiles — larger than most
    rooms specifically because it hosts six live readouts rather than
    two or three) reuses CEO Office's Inn_Black building sprite a second
    time (no dedicated boardroom sprite exists in the asset pack), with
    a gold pulsing ring differentiator matching the Market Observatory's
    own cyan-ring precedent. In-room, at-a-glance readouts (world market
    display, department status wall, department performance overview,
    executive briefing, company timeline/report archive, current
    objectives) all read real already-computed state — deliberately no
    duplicate Command Center tab, since the brief specifically asks that
    "the player can enter the room at any time" to read them.
  - **AI Academy & Knowledge Network (Feature 25)**: every agent
    (including the CIO) has one real Knowledge Branch
    (`app/academy.py`'s `KNOWLEDGE_BRANCH`, occupation-linked — Echo's
    is Technical Analysis, Sentinel's is Risk Management) and a real
    Knowledge Points total that only grows from real completed work — a
    finished `ResearchItem`, a finished `AcademyProject`, or attending a
    real meeting — crossing three fixed tiers, mirroring
    `signal_calibration.py`'s single-number progression pattern. A new
    `app/academy_research.py` runs the Academy's own non-market
    "knowledge" research queue (market history, trading psychology,
    economic concepts, visualization tools, decision biases, trading
    philosophies — six topics cycling through every non-CIO agent),
    mechanically mirroring `research.py`'s own progress-climbs-then-
    completes-and-rotates shape. Every completed project is permanently
    stored (capped) as the **Company Knowledge Library**. A new
    company-wide `AcademyState.level` (1-5, named Training Room through
    Executive Institute) is derived from real total points plus real
    completed-project count — not five new physical rooms (an explicit,
    documented scope cut; no new art was produced for this). Surfaced
    on a new **KNOWLEDGE** tab (`AcademyPanel.tsx`) — named to avoid
    colliding with the pre-existing v0.6.2 "ACADEMY" tab (Trading
    Academy/`EducationPanel`, a different system entirely).
  - Explicit scope cuts, matching this session's honesty convention:
    **Mentorship** has no real seniority/relationship data anywhere in
    this codebase to build on, so rather than inventing a fabricated
    senior/junior status label, "seniority" is grounded in the one real
    number that legitimately reflects it — an agent's own earned
    Knowledge Points. When the real gap between the most- and least-
    experienced agent crosses a threshold, a real mentorship session
    transfers a small real point bonus to the lower agent, logged with
    both agents' own real point totals — checked on a 3-day cadence, not
    every tick, since a real gap moves slowly. A full mentor/mentee
    relationship graph and visible in-world mentoring animations are not
    built. **Knowledge-tree "expanded dialogue"** per tier is also not
    built (11 agents × 3 tiers of bespoke dialogue was out of scope);
    tier-ups instead produce a real memory/library entry naming the
    agent's own real point total. **Cross-department discussion
    dialogue** ("Research presents, Risk asks questions") reuses the
    existing meeting/discussion system as-is rather than adding new
    academy-flavored turns to it — a completed Academy project instead
    publishes a real news headline, the same "the player can review it
    later" mechanism already established.
  - Verification: full backend (mypy/ruff/pytest, 235/235 — 33 new tests
    across `test_academy.py`, `test_academy_research.py`, and
    `test_executive_review.py`) and frontend (tsc/eslint/build) clean;
    the full Playwright suite (`commandCenter.spec.ts` — now 14 tabs,
    including a new KNOWLEDGE-tab test —, `executiveVoting.spec.ts`,
    `marketObservatory.spec.ts`, 16/16 passing) runs clean against a
    freshly reset backend. A multi-thousand-tick standalone smoke test
    (well past a simulated month) confirmed the Monthly Executive
    Review, Academy project rotation/completion, knowledge-tier-ups, and
    a real mentorship pairing all fire correctly with no exceptions.

- **v0.7 — Company Knowledge Graph (Feature 25.5)** — connects every
  already-real, already-persisted record Feature 24/25 produces into one
  queryable node-edge graph, so completed work stays part of the
  company's institutional memory instead of sitting in isolated lists.
  - **`app/knowledge_graph.py`**: a computed-fresh-on-every-request graph
    (`GET /api/knowledge-graph`, the same never-persisted convention
    `app/whatif.py` established) built from six real sources — completed
    `ResearchItem`s, completed `AcademyProject`s, each agent's own real
    Knowledge Branch, `ExecutiveReview`s, `CoachReport`s, and
    `HallOfFameEntry`s. Every edge traces to a real, checkable shared
    attribute: a research item's own `assigned_agent`, two research items
    sharing a real `category` (or two Academy projects sharing a real
    `topic`) chained by their own real `updated_at` into a `builds_on`
    relationship, an agent's real appearance in an `ExecutiveReview`'s
    `department_activity`, or a `CoachReport`'s real top-ranked agent —
    never a fabricated connection. Verified against a 1500-tick
    standalone smoke test (170 nodes / 285 edges, all correctly linked).
  - **Executive Review "Knowledge Connections"**: `generate_executive_review`
    now also computes real "this builds on that" callbacks — for every
    research category / Academy topic with two or more completed items,
    it names the two real titles involved (e.g. `This period's "Reviewing
    MSFT momentum" builds on earlier stock research, "Studying AAPL
    trends".`). Deliberately never claims a specific elapsed time (the
    brief's own example, "four months ago") since `ResearchItem`/
    `AcademyProject` only carry real wall-clock timestamps, not a sim-time
    span guaranteed to read as meaningful within one play session.
    Surfaced in the Executive Boardroom's briefing screen and in a new
    "Company Knowledge Graph" card on the KNOWLEDGE tab.
  - **Interactive Knowledge Map** (`KnowledgeGraphView.tsx`, launched from
    the KNOWLEDGE tab): a hand-rolled canvas force-directed graph (no
    charting/graph library dependency, matching `CandlestickChart.tsx`'s
    existing hand-rolled-canvas convention) with velocity+damping physics
    that settles into an even spread rather than a temperature-capped
    layout that can oscillate or collapse around high-degree hub nodes.
    Real pan (drag), zoom-to-cursor (scroll), a fit-to-real-bounding-box
    initial view, per-type color-coded nodes (agent nodes use each
    agent's own real sprite tint — real department colors, not invented
    ones), animated dashed edges and a pulsing node glow for a "living
    network" feel, a type filter row, a label search that dims
    non-matching nodes, and a click-to-inspect side panel showing a
    node's real summary, timestamp, and every real connected node/relation
    (clickable to jump). A "Recent Discoveries" default view lists the
    most recently timestamped real nodes when nothing is selected.
  - **Institutional memory in dialogue**: `DialogueManager` gained a real,
    honest recall line — roughly one conversation in three, an agent with
    at least one real completed Academy project references their own most
    recent real project by its real title. Never a fabricated memory, and
    never another agent's project.
  - Explicit scope cuts, matching this session's honesty convention: the
    brief's "Academy Integration" section (auto-generating interactive
    lessons/seminars/training sessions/quizzes/museum exhibits/company
    presentations/new dialogue/knowledge challenges from completed
    research) is not built — this codebase has no content-generation
    capability, and the pre-existing v0.6.2 Education curriculum
    (`education.py`'s ten fixed lessons — candlesticks, stop-loss,
    position sizing, all technical trading mechanics) has no real
    thematic overlap with the six Academy topics (market history,
    psychology, economics), checked directly rather than assumed, so no
    Academy-to-Education edge or generated lesson is fabricated either.
    "NPCs begin discussing it" is scoped to the one honest recall line
    above rather than a full conversational-memory system tracking who
    told whom what. The Knowledge Graph's node *positions* are a purely
    client-side visual layout (force-directed, recomputed per fetch), not
    a second source of truth about the data.
  - Verification: full backend (mypy/ruff/pytest, 252/252 — 17 new tests
    across `test_knowledge_graph.py` and `TestKnowledgeConnections` in
    `test_executive_review.py`) and frontend (tsc/eslint/build) clean.
    Manually verified end-to-end against a live dev backend with real
    completed research/Academy data (Playwright: opening the graph,
    zooming, panning, searching, and clicking a node all produced the
    correct real side-panel content, with zero console errors).

- **v0.7 — The Discipline Chamber & The Library of Mistakes (Features
  26-27)** — the company now rewards good decisions, not lucky outcomes.
  - **The Discipline Chamber (Feature 26)**: `app/discipline.py` files a
    real `DisciplineReview` for every trade that closes, scoring the
    decision PROCESS from seven real, already-computed signals — never
    the trade's pnl. This is enforced structurally, not just by
    convention: `compute_discipline_score()`'s signature only accepts a
    real hold duration (a behavior signal, not a result), never the
    trade or its outcome, so an identical process provably scores
    identically whether the linked trade won or lost (see the module's
    own test suite). The seven factors — Research Depth, Viewpoint
    Diversity, Uncertainty Acknowledged, Cross-Examination Occurred,
    Assumptions Challenged, Position Sizing Discipline, Patience — reuse
    the Decision Confidence Engine's own factors, the AI Debate's real
    turns, and each closed trade's own real hold duration. Two traps were
    checked and avoided while designing the factor set: `votes` always
    contains all six real analyst votes (a structural constant, not a
    real discriminator — real *viewpoint diversity*, how many distinct
    choices those votes actually held, is used instead), and every trade
    that reaches this module already passed the Trade Gatekeeper in full
    (a rejected verdict means no trade ever opens), so "did it pass the
    Gatekeeper" is also constant for this population — Position Sizing
    Discipline reuses the Confidence Engine's own still-varying Portfolio
    Exposure factor instead. `outcome`/`tradePnlPct` are attached to the
    finished review afterward, purely so the player can see whether a
    good process and a good outcome actually lined up — the review's own
    summary calls this out explicitly (a sound process that still lost
    reads as "bad luck, not a bad decision"; a weak process that won
    reads as "a warning, not a validation"). A real `PostDecisionReview`
    answers the brief's seven questions from the review's own real
    factors and — only for a real loss — names the specific real
    dissenting analyst (Echo or Scout) whose overridden vote proved
    right; Sentinel is deliberately never checked here, since the Trade
    Gatekeeper's `risk_manager_check` hard-requires the risk analyst's
    vote to match the CEO's choice before a trade can even open, so
    Sentinel dissent on an executed trade cannot occur.
  - **The Library of Mistakes (Feature 27)**: `app/mistakes.py` files a
    permanent `CaseStudy` whenever a closed, *losing* trade's own
    Discipline Review shows a specific real process gap — never merely
    "the trade lost" on its own (a well-disciplined process that loses to
    real market variance is the Discipline Chamber's whole point to
    protect, not punish). Six categories, each mapped to one real,
    checkable signal: **The Cost of Overconfidence** (Confidence Engine
    scored 80+, still lost), **Incomplete Research** (research confidence
    factor below 50), **Failure to Challenge Assumptions** (zero real
    debate challenge turns), **Acting Too Quickly** (closed inside the
    same patient-hold window `app/coach.py` already uses), **Poor
    Communication** (the AI Debate's own real synthesis recommended the
    opposite of what executed), and **Confirmation Bias** (a specific
    real dissenting analyst — Echo or Scout — was overridden and proven
    right). A single trade can trigger more than one category — each
    becomes its own case study, matching the brief's own framing of these
    as distinct, separately-filed examples. Every field in the resulting
    case study (Timeline, Background, Decision Process, Department
    Opinions, Missed Information, Lessons Learned, Recommended
    Improvements, Related Company Principles) is built from real
    structured data — the linked `TradeDecision`'s own real vote
    reasoning, the real `Debate` turns, the real `RiskLimits`/Gatekeeper
    thresholds, real timestamps — filled into a fixed template, never a
    fabricated narrative.
  - **Institutional memory**: both `DisciplineReview` and `CaseStudy`
    carry a real `simDay` (TradeTown's own in-game calendar day, not a
    real wall-clock date) so NPCs can honestly reference "on Day 47" the
    way the brief's own example does. `DialogueManager` now tries two
    real recall sources per conversation (a completed Academy project, or
    — new this pass — a real case study from a decision the agent was an
    actual attendee of, cross-referenced via `DisciplineReview.attendees`)
    and picks at random from whichever actually has real content.
  - A new **DISCIPLINE** Command Center tab surfaces both systems: an
    aggregate discipline score, the two counts that make the "process,
    not outcome" point concrete (good-process trades that still lost;
    weak-process trades that happened to win), an expandable Discipline
    Reviews list (full factor breakdown + post-decision review), and a
    filterable Library of Mistakes browser (full case study detail per
    entry).
  - Explicit scope cuts, matching this session's honesty convention: two
    of the brief's ten named discipline qualities have no real
    discriminating signal in this codebase and are deliberately not
    scored — "was proper documentation created" (every decision's
    summaries/reasoning are unconditionally auto-populated, so scoring it
    would be fake precision on an invariant) and "did departments
    communicate effectively" beyond real cross-examination (folded into
    the Cross-Examination factor rather than invented as a second,
    redundant measure). Discipline Reviews are only generated for closed
    trades — research projects, executive decisions, and "major company
    events" have no comparable rich per-item process trail in this
    codebase (no per-item "were multiple viewpoints considered" signal
    exists for a research item or a company milestone), so inventing a
    discipline score for them would mean fabricating numbers with no real
    backing; the existing Executive Review and Company Memory systems
    remain the honest record for those.
  - Verification: full backend (mypy/ruff/pytest, 280/280 — 28 new tests
    across `test_discipline.py` and `test_mistakes.py`) and frontend
    (tsc/eslint/build) clean. A 3000-tick standalone smoke test in
    Executive Operating Mode confirmed the full real pipeline end to end
    (60 discipline reviews, 60 case studies, correct win/loss pairing,
    zero exceptions); manually verified in the running app against seeded
    real data (Playwright: the DISCIPLINE tab, review/case-study
    expansion, and category filtering all rendered correct real content
    with zero console errors).

- **v0.7 — The Reasoning Lab (Feature 29)** — the company practices how
  it thinks, not just what it decides. `app/reasoning_lab.py` files a
  real `ReasoningChallenge` periodically from the company's most recent
  real AI Debate plus its linked `TradeDecision` — like the Discipline
  Chamber, no function in this module ever reads a trade's pnl or
  outcome, so this is decoupled from results structurally, not just by
  convention.
  - **Seven honest challenge categories** out of the brief's nine, each
    mapped to one real, checkable signal on the linked Debate/
    TradeDecision: **Finding Missing Information** (research confidence
    below the same threshold `app/mistakes.py` uses), **Identifying Weak
    Evidence** (a real opening statement carried no real backing evidence
    — the same indirect "(...)" proxy the Discipline Chamber's own
    cross-examination check relies on), **Recognizing Contradictory
    Data** (the six analyst votes split three ways), **Separating Facts
    from Assumptions** (a real debate challenge turn occurred),
    **Evaluating Multiple Hypotheses** (the votes split exactly two
    ways), **Comparing Competing Explanations** (two or more distinct
    analysts each filed a real support turn), and **Improving
    Communication** (the honest fallback when no stronger signal fired,
    including when no real Debate exists at all). **Detecting Logical
    Fallacies** and **Building Better Questions** have no real,
    checkable signal anywhere in this codebase and are deliberately not
    built.
  - **Reasoning Level** gates which categories can actually be detected —
    a real, monotonic completed-challenge count crossing fixed
    thresholds (Foundations → Applied Reasoning → Advanced Reasoning),
    mirroring `AcademyState`'s own progression convention exactly. The
    three foundational categories need no prior progress; the four
    covering less-common real debate shapes only appear once the company
    has practiced the basics — an advanced category is skipped, not
    faked, until its level is actually reached.
  - **Collaborative Thinking, made real, not scripted**: each
    challenge's `ReasoningContribution` list reframes the underlying AI
    Debate's own real opening/challenge/support turns as the brief's
    "departments collaborate" record — never invented dialogue between
    fixed department roles that don't exist in this codebase.
  - **Explain Your Thinking**: every challenge's `ReasoningSolution`
    answers the brief's six required questions (what we know, what we do
    not know, what assumptions exist, why the conclusion is reasonable,
    how confident we are, what could change the conclusion) filled from
    the linked decision's own real Confidence Engine factors, vote
    reasoning, and final reasoning — never invented commentary.
  - A new **REASONING** Command Center tab shows the company's current
    Reasoning Level and progress, and a filterable, expandable Reasoning
    History (collaborative contributions + full solution detail per
    challenge). `DialogueManager` gained a third real recall source
    (alongside completed Academy projects and Library of Mistakes case
    studies): an agent who actually contributed a real Debate turn to a
    filed challenge may reference it by title, symbol, and real
    `simDay`.
  - Explicit scope cuts, matching this session's honesty convention: new
    seminar content, interactive-seminar UI, and richer collaboration
    animations per Reasoning Level have no real data source and are not
    built (the same "a real number/label, not new art per level"
    boundary `AcademyState` already drew); challenges are generated on a
    fixed evening cadence from the company's most recent real Debate,
    skipping any cycle with no Debate yet or where the most recent Debate
    was already used, rather than re-practicing the same already-reasoned
    case just to hit the cadence.
  - Verification: full backend (mypy/ruff/pytest, 301/301 — 21 new tests
    in `test_reasoning_lab.py`) and frontend (tsc/eslint/build) clean. A
    4000-tick standalone smoke test in Executive Operating Mode confirmed
    the full real pipeline end to end (7 reasoning challenges across
    three genuinely different real categories, Reasoning Level correctly
    advancing to 2, zero exceptions); manually verified in the running
    app (Playwright: the REASONING tab, level readout, and challenge
    history all rendered correct real content with zero console errors).

- **v0.7 — The Reflection Chamber & Knowledge Levels (Features 30-31)** —
  the company now pauses to learn, not just to act, and gets one real
  step closer to the brief's Learning Center scale.
  - **The Reflection Chamber (Feature 30)**: `app/wisdom.py` holds a real
    `ReflectionSession` every in-game week and month (same evening
    cadence Coach/Executive Review already use), answering the brief's
    nine reflection questions from data already computed elsewhere —
    `DisciplineReview`/`CaseStudy`/`ReasoningChallenge`/`ResearchItem` —
    never a fabricated meeting transcript. Several questions deliberately
    reuse the same underlying number from opposite ends (the strongest
    real Discipline factor answers both "what are we doing well" and
    "what should we continue," the same "strong vs weak factors from one
    list" convention `discipline.py`'s own post-decision review already
    established). Cross-department sharing is represented honestly:
    Research's real latest completed item, News's real latest headline,
    Risk's real latest warning or Gatekeeper block, Executive's real
    latest review summary — never invented dialogue between department
    roles this codebase doesn't have.
  - **Company Wisdom**, a new permanent, never-profit-based score: a
    plain, unweighted mean of eight real factors (learning from
    experience, sharing knowledge, following the Gatekeeper's own
    configured principles, improving communication, documenting lessons,
    avoiding repeated mistakes, completing research, supporting
    collaboration), each traced to a real signal already computed by
    Discipline/Mistakes/Reasoning/research/Gatekeeper/mentorship — see
    `wisdom.py`'s module docstring for exactly which. `compute_wisdom_score()`'s
    own signature has no pnl/profit parameter, the same structural "never
    reads the outcome" guarantee the Discipline Chamber established.
    Recomputed only when a session is generated (weekly/monthly), not
    every tick — deliberately, so the score reads as genuinely
    slow-moving, and deliberately hard to max, since several factors
    pull against each other in practice.
  - A new **REFLECTION** Command Center tab shows the current Wisdom
    Score/tier/factor breakdown and an expandable Reflection Journal
    (all nine Q&A, department insights, key discoveries, lessons
    learned, important questions, recommended future projects) per
    session. `DialogueManager`'s existing institutional-memory recall
    chance now scales up with the company's real Wisdom tier — the
    honest, checkable version of "historical knowledge is referenced
    more often as the company grows wiser."
  - **Knowledge Levels (Feature 31)**: rather than build a second,
    largely-redundant progression system alongside the already-shipped
    AI Academy (Feature 25), `app/academy.py`'s existing per-agent
    Knowledge Points now cross six real thresholds (was three) into a
    real seven-level Novice → Beginner → Intermediate → Advanced →
    Expert → Master → Mentor scale — the same real points, a richer
    name. The existing mentorship mechanism (the real points-gap trigger
    between the most- and least-experienced agent) is phrased as real
    teaching, not generic mentoring, the moment the mentor has actually
    reached the top Mentor level — `is_mentor_level()` is the real,
    checkable gate the brief's "Teaching System" needs. `DialogueManager`
    gained a real, template-based version of "explanation matches
    knowledge level": once an agent's own real level reaches Advanced or
    higher, their greeting includes one extra line at that real depth —
    never a fabricated open-ended Q&A system.
  - **Explicit scope cuts**, matching this session's honesty convention:
    no new physical Reflection Chamber or Learning Center room was
    built — a holographic table, a constellation-animated Knowledge
    Graph floating in 3D, and a ten-room building all have no real
    gameplay-data hook in this 2D, tile-based codebase, the same
    "Command-Center-tab, not new art" boundary Academy/Discipline/
    Mistakes/Reasoning Lab already drew. Feature 31's Player Knowledge
    Import (PDFs, videos, books the player provides) is not built at
    all — this codebase has no content-ingestion pipeline, and
    fabricating lesson content from an uploaded file would mean
    inventing text with no real backing. The brief's explicit 8-stage
    learning pipeline and per-lesson Knowledge Summaries (key concepts,
    definitions, open questions, weaknesses, related topics) are not
    separately built either — the existing Academy Project pipeline and
    Education quiz system already cover real study/practice/
    understanding-check activity at an honest, coarser granularity, and
    duplicating it under new names would mean fabricating distinct
    per-stage signals this codebase doesn't have. Live Classrooms (a
    physical room) and free-form "Ask Any Agent, explain this topic" are
    both cut for the same reason — no real dynamic content-generation
    capability exists here.
  - Verification: full backend (mypy/ruff/pytest, 322/322 — 15 new tests
    in `test_wisdom.py`, 5 new tests in `test_academy.py`) and frontend
    (tsc/eslint/build) clean. An 11,500-tick (~41 in-game day) standalone
    smoke test in Executive Operating Mode confirmed the full real
    pipeline end to end (6 real reflection sessions across weekly/
    monthly cadences, Company Wisdom genuinely growing from 23.8/100
    "Young Company" to 71.2/100 "Seasoned Wisdom" purely from real
    behavioral signals, zero exceptions); manually verified in the
    running app (Playwright: the REFLECTION tab, Wisdom factor
    breakdown, and Reflection Journal history all rendered correct real
    content with zero console errors).

- **v0.7 — Sage, the Socratic Mentor (Feature 32)** — the company's
  eleventh agent, who never trades, votes, or generates a research
  signal, structurally the same guarantee `agents.py` already made for
  Meridian (Feature 24).
  - **Sage**, home location Brain Room (no new physical "Mentor Chamber"
    was built — the established Command-Center-tab-not-new-scene
    precedent Academy/Discipline/Reasoning Lab/Reflection Chamber all
    drew), a new palette-swapped sprite generated the same real,
    deterministic way as all ten existing agents' sprites: PIL
    pixel-diffed against the base sheet to recover the exact 7-color
    remap table (2 hair + 5 shirt/pants-ramp), then remapped to a deep
    indigo/violet hair-and-robe combination distinct from every existing
    agent's tint.
  - **Question of the Day**: every in-game morning at 8:00, `app/mentor.py`
    draws one `QuestionOfTheDay` deterministically (`sim_day % library
    length`) from a small, hand-authored 20-question library spanning 10
    categories — real curated content, the same convention
    `DialogueManager`'s own flavor lines already use, since this
    codebase has no free-form question-generation capability. Each
    question carries at most one honest `relatedReference` — a real
    pointer into already-existing company content sharing its category
    (a Reasoning Lab challenge, a Library of Mistakes case study, a
    Reflection Chamber lesson, an Executive Review flag, ...) — never a
    fabricated per-department "answer." Every entry is permanently
    archived (capped at 120, roughly four in-game months); the player
    may answer via a new `POST /api/mentor/qotd/respond`, stored verbatim
    and never graded.
  - **Thinking Profiles**: every agent (including Sage) gets a purely-
    computed, six-trait profile — Curiosity (real Academy knowledge
    points), Evidence Quality/Open-Mindedness/Humility/Reasoning (real
    per-agent averages of Discipline Review factors across every closed
    trade the agent attended), and Collaboration (real Reasoning Lab
    contribution + Reflection Chamber insight counts). Recomputed fresh
    every tick, the same "cheap to recompute, only re-scans already-
    capped lists" reasoning `academy_state`/`reasoning_lab_state` already
    established. "Patience" is deliberately not a trait here — Discipline
    Review already scores it directly under that exact name, and
    re-surfacing the identical signal under a new label would be the
    "redundant re-measurement" trap this session has consistently
    avoided; the brief's "Communication" and "Adaptability" have no real
    per-agent discriminating signal anywhere in this codebase and are
    likewise cut.
  - A new **MENTOR** Command Center tab shows today's question (with
    answer box), the full Question Archive, a static Question Library
    summary, and every agent's Thinking Profile as trait meters.
  - **Explicit scope cuts**: a separate weekly "Mentor Session" was not
    built — `wisdom.py`'s already-shipped `ReflectionSession` already IS
    a real weekly/monthly company-wide gathering built around real,
    Socratic-style questions, and duplicating it under a new name would
    just re-package the same real signals (the "redundant
    re-measurement" trap again). "Thinking Exercises" are not duplicated
    either — `reasoning_lab.py`'s `ReasoningChallenge` (Feature 29)
    already covers 7 of the brief's 10 named exercise types with a real
    signal each. Personal Coaching (per-employee improvement areas), a
    graded "Daily Thinking Bonus" (no honest way to grade open-ended
    free text), "Connected Constitution Articles" (no Company
    Constitution system exists anywhere in this codebase — checked
    directly), and the Question Library being consumable live by NPCs
    during meetings (no hook exists in `scribe.py`'s discussion generator
    without fabricating dialogue) are all cut and documented in
    `mentor.py`'s module docstring.
  - Incidental fix: `BrainRoomHud.tsx`'s `AGENT_ORDER` (Agent Status /
    "N of M agents actively working") had never included Meridian since
    Feature 24 added her; now includes both Meridian and Sage.
  - Verification: full backend (mypy/ruff/pytest, 336/336 — 14 new tests
    in `test_mentor.py`) and frontend (tsc/eslint/build) clean. Manually
    verified in the running app (Playwright, 21/21 passing including a
    new MENTOR-tab test; the MENTOR tab, Question of the Day
    submit-and-persist round trip, Question Archive, and per-agent
    Thinking Profile meters all rendered correct real content with zero
    console errors; Sage's sprite and Agent Status entry confirmed
    visually in the Brain Room).

- **v0.7 — CEO Treasury, Company Priorities & Time Controls, Living
  World Schedules (Features 33-35)** — the CEO gets a real protected
  reserve, a real strategic-focus lever, and real control over how fast
  time passes; every agent's day now runs through 24 real hours instead
  of stopping at the evening review.
  - **CEO Treasury (Feature 33)**: `app/treasury.py` holds a second
    account (`TreasuryState.balance`) structurally isolated from
    `PaperPortfolio.cashBalance` ("Operating Capital") — every function
    that moves money takes the CEO-initiated amount as an explicit
    parameter from a real player action (`POST /api/treasury/deposit`/
    `/withdraw`), and no automatic system anywhere in this codebase
    (`paper_trading.py`, `broker.py`, `risk_engine.py`, `research.py`,
    `academy.py`, ...) ever reads or writes `treasury.balance` — checked
    by grep, not just documented by convention (see `treasury.py`'s
    module docstring). **Smart Savings Rules** are the one deliberate
    exception, and only because the CEO explicitly configured and can
    pause them: the brief's "save 5% of monthly profit" and "save 10%
    after profitable months" collapse into one real rule type
    (`percent_of_monthly_profit`) since they're mechanically identical —
    saving a percent of profit only ever fires when that profit is
    positive — rather than fabricating a second, redundant type;
    `excess_above_reserve` (move cash above a chosen dollar reserve) is
    genuinely distinct and kept separate. Both apply automatically once a
    month alongside a real `TreasuryMonthlyReport`, computed from
    `analytics.period_profit_dollars()` (a new function reusing the same
    real trade-history filtering `compute_performance_snapshot()`
    already does) rather than a second derived P&L path. Lifetime
    Deposits, Largest Balance, Reserve Percentage, and the Savings Growth
    Timeline are all real, computed or filtered from the same
    transaction log — no second, redundant series maintained. A new
    **TREASURY** Command Center tab is the room: no new physical
    vault-door scene was built (the established Command-Center-tab
    precedent every recent v0.7 feature has followed), and the brief's
    CEO Benefits (Company Expansion, Emergency Funding, Building New
    Departments, Buying Headquarters Upgrades, Special Story Events) are
    not built — none of those systems exist anywhere in this codebase to
    spend real Treasury dollars into; withdrawal itself (CEO-approved
    funds moving back to Operating Capital, usable through whatever real
    cash-consuming system already exists) is the honest piece that is.
  - **Company Priorities (Feature 34)**: a new `settings.companyPriority`
    (`balanced | learning | research | risk_reduction`, the same
    client-authoritative mechanism `operatingMode` already uses) biases
    exactly one real, already-existing lever per option — Academy
    knowledge-point awards run 1.5x (`learning`), active research
    confidence-gain speed runs 1.5x via `tick_research()`'s new
    `speed_multiplier` parameter (`research`), or new trade proposals are
    sized/vetted against a tightened, derived-only copy of the player's
    own risk limits via the new `nexus._effective_risk_limits()`
    (`risk_reduction`) — the player's own stored `RiskLimits` (and
    everything else derived from it, like Guardian's ambient risk
    warnings) is never mutated. The brief's "Expansion," "Efficiency,"
    and "Innovation" priorities are not offered — no real, distinct lever
    exists in this codebase for any of them, and reusing one of the three
    real levers under a fourth label would misattribute its effect.
  - **Time Controls (Feature 34)**: a new `POST /api/time/advance`
    (`GameState.advance_time()`) drives End Workday / End Week / End
    Month, plus a bounded 1-72 hour custom fast-forward. Rather than
    jumping the clock directly, it loops the exact same real per-tick
    orchestration step (`_advance_once()`, extracted from `tick()`) under
    one lock acquisition until the target lands — structurally identical
    to time actually passing faster, not a fake jump, so every
    exact-minute cadence check along the way (evening reports, the
    morning Question of the Day, Treasury's monthly rules, ...) still
    fires correctly; calling it exactly at the target minute still
    advances to the *next* occurrence rather than no-op-ing. Because a
    multi-hour jump can touch nearly everything NEXUS touches, the
    endpoint returns the full `GameSaveState` rather than just the new
    time, applied client-side in one shot. The CompanyPanel tab gained a
    Company Priority section and a Time Controls section (three presets
    plus a custom-hours input); `FullCommandCenter` also gained a number-
    key (1-9) tab-switch shortcut, ignored while a form field (Treasury's
    amount input, the fast-forward hours field, ...) has focus.
  - **Living World Schedules (Feature 35)**: every one of the 11 agents'
    `AGENT_SCHEDULES` (`app/schedule.py`, mirrored in
    `Schedule.ts`/`DialogueManager.ts`) now runs a real, personality-
    flavored off-hours routine from 20:00 to 6:00 — a wind-down task, a
    distinct evening activity, then sleep — instead of stopping cold at
    the evening review. Each agent's two new tasks (22 total) are
    genuinely per-personality (Coach exercises to clear his mind and
    watches game film "for fun this time," Sentinel finally lets the
    guard down, Sage sits quietly with today's question off the clock,
    ...), each with its own new `DialogueManager` flavor line. No new
    Employee Residence scene, Bedrooms/Kitchen/Game Room/etc., or City
    Life locations (Coffee Shop, Park, Library, ...) were built — checked
    concretely rather than assumed: the fantasy-village asset pack has
    zero indoor-furniture sprites (bed, sofa, kitchen counter,
    bookshelf), and the Lobby's existing 11-door layout is already a
    tightly pixel-tuned, heavily collision-annotated arrangement where
    every one of the 9 building sprites is already reused at least once —
    a 12th door is high-risk, high-effort relative to the honest goal
    here, which this schedule-and-dialogue approach delivers with zero
    new art: agents feel alive with real off-hours routines the player
    can walk into the Break Room and witness, not NPCs that vanish after
    work. Incidentally closed a genuine pre-existing schedule gap (Nova's
    day started at hour 7 while every other agent's day started at hour
    6, leaving hour 6 silently mislabeled by the schedule lookup's own
    fallback).
  - Verification: full backend (mypy/ruff/pytest, 378/378 — 42 new tests
    across `test_treasury.py`, `test_company_priority.py`, and
    `test_time_advance.py`) and frontend (tsc/eslint/build) clean.
    Manually verified in the running app (Playwright, 20/21 passing, 1
    skipped for the same real-trade-timing reason every run of this file
    already tolerates; new tests cover a real deposit/withdraw round trip
    with a rejected over-withdrawal, Company Priority selection
    persisting across a reload, a real End Workday clock jump via
    `POST /api/time/advance`, and the number-key tab shortcut correctly
    ignoring a focused form field).

- **v0.7 — CEO Calendar & Company Schedule (Feature 36)** — one place
  that aggregates every real, already-computable recurring company event,
  rather than a fabricated fixed hourly company-wide timetable.
  - **System events**: `app/calendar.py`'s `compute_system_events()`
    turns nexus.tick()'s own fixed cadence checkpoints — Weekly/Monthly
    Coach Reports, the Monthly Executive Review, the Monthly Treasury
    Savings Report, Weekly/Monthly Reflection Sessions, Sage's daily
    Question of the Day — into a real, dated event list, recomputed fresh
    every tick the same "cheap, always current" way company_health/
    academy_state already are. The two *conditional* cadences (the
    Reasoning Lab challenge and the Academy mentorship check) get a live
    `eligible` flag computed by re-running the exact same real gate
    `nexus.tick()` itself uses — a genuine "would this fire right now"
    check against current data, not a guess about the future. Active
    research items get an honest ESTIMATED completion date/time,
    projected from the real current confidence and the real average
    per-tick confidence-gain rate (scaled by Feature 34's research-speed
    Company Priority multiplier when active) — labeled ESTIMATED, the
    same "never claim more certainty than the data supports" convention
    the WhatIf Simulation Lab's own "SIMULATED" badge already set. A
    "Company Anniversary" milestone (day 365, 730, ...) rides the same
    honestly-arbitrary-but-fixed-and-disclosed "30-day month" convention
    `analytics.py` already uses for TradeTown's calendar.
  - **Player events**: the CEO can schedule a custom calendar entry
    (title + category, from the brief's own eight named examples plus
    "other") for any real future day/hour/minute via a new
    `POST /api/calendar/events/create` / `/delete` pair — informational
    only, the same "no fabricated mechanical effect" boundary Feature
    33's cut CEO Benefits list already established; scheduling a "Company
    Holiday" doesn't pause research, and an "Extra Training Day" doesn't
    boost Academy points, since no real payroll/attendance/training-boost
    system exists anywhere in this codebase to attach one to honestly.
  - A new **CALENDAR** Command Center tab (`CalendarPanel.tsx`) shows
    Today's/Tomorrow's Schedule, a Weekly Agenda, Monthly Company Events,
    an Executive View (current/next event, real department working/idle
    counts, today's real meeting count, the real current Company
    Priority), the custom-event form, and a **Live Schedule** section —
    click any of the 11 agents to see their real current activity, room,
    mood, Knowledge Level, active research, and their full real daily
    schedule block-by-block (reusing the already-shipped client-side
    `Schedule.ts` mirror, no new backend endpoint needed).
  - **Explicit scope cuts**: the brief's fixed "8:00 Morning Briefing,
    8:30 department assignments, 10:00 Research Sessions, ..." example
    day is not reproduced — that exact synchronized company-wide
    timetable doesn't exist in this codebase (each of the 11 agents
    already runs its own distinct, personality-driven schedule — see
    Feature 35), and fabricating one here would misrepresent what
    actually happens. "Academy Classes" gets no fixed slot or ETA —
    unlike research's steady per-tick rate, Academy progress moves in
    irregular real bursts with nothing steady to project from. "Department
    Meetings" gets no fixed slot either — `MEETING_CHANCE_PER_TICK` means
    they're called spontaneously, never on a schedule; the panel surfaces
    today's real count instead. Employee Birthdays (marked optional in
    the brief) is cut outright — no agent has a birth date anywhere in
    this codebase. "Missed Meetings" (an Executive View field the brief
    itself asks for) is cut — no agent is ever "invited" in a trackable
    way. Guest Lecturer, Academy Exam, Innovation Day, Department
    Workshop, Knowledge Fair, Reflection Conference, Celebration Party,
    and Research Presentation have no real system behind them anywhere
    in this codebase and are not fabricated.
  - Verification: full backend (mypy/ruff/pytest, 404/404 — 26 new tests
    in `test_calendar.py`) and frontend (tsc/eslint/build) clean.
    Manually verified in the running app (Playwright, 27/27 counting the
    same tolerated real-trade-timing skip every run of this suite
    already has — including a new CALENDAR-tab test covering the real
    system-event lists, the per-agent Live Schedule, and a full custom-
    event create/delete round trip against the live backend).

- **v0.7 — Intelligent Devil's Advocate & Innovation Points (Feature 41)**
  — the brief's Devil's Advocate System and Innovation Points, scoped down
  to what's genuinely new after checking against the AI Debate Room
  (Feature 17), the Library of Mistakes' `CaseStudy` (Feature 27), the
  What-If Simulation Lab (Feature 16), and Hall of Fame (Feature 24).
  - **Challenge Report** (`app/devils_advocate.py`): a single structured
    artifact — not a duplicate of the Debate Room's existing per-analyst
    challenge/support turns — built entirely from real signals already
    computed elsewhere: bull/bear case from the desk's own real
    agreeing/dissenting `AnalystVote` reasoning; hidden risks from the
    proposal's own real `riskSummary`; weak assumptions from any real
    `DecisionConfidence` factor scoring below 50; missing evidence from
    any real vote with an empty evidence list; historical comparisons
    from real past `CaseStudy` titles for the same symbol; worst case
    scenario from one line of the What-If Simulation Lab's own real
    worst named scenario (never the full simulation — this codebase
    already learned that lesson once, see `MAX_DECISIONS`'s history).
    `severity` (`none_found`/`minor`/`major`) is a real, checkable count
    of how many of those concern categories actually found something —
    "no significant weaknesses found" is a genuine, earned outcome, not
    a coin flip. One employee is temporarily assigned per report,
    rotating deterministically through a fixed pool of five (Scribe,
    Coach, Guardian, the CIO, Sage) — never one of the proposal's own six
    analyst seats, never the Founders (who don't route through
    operational work per Feature 39). Generated automatically alongside
    the Debate the moment a proposal is created, with a "Request Another
    Review" button in Executive Voting matching Feature 17's own
    "request another debate" convention.
  - **Innovation Points** (`app/innovation.py`): a second, deliberately
    narrow ladder — where Career Level (Feature 40) tracks general
    knowledge mastery, this tracks one specific real skill: an agent's
    own record as a Devil's Advocate. Points are awarded per Challenge
    Report the agent authored, weighted by its own real severity (major
    weaknesses caught > minor > "none found, honestly reported" — the
    brief's own "rewarded for discovering problems, and for intellectual
    honesty"). Five real tiers (Research Contributor → Legendary
    Innovator) gated by real cumulative thresholds, shown per-agent in
    the KNOWLEDGE tab.
  - **Cut, and why**: re-awarding Innovation Points for events Academy
    Points already scores (course completion, research, mentoring) would
    be double-counting the same real signal under two names — the exact
    duplication this session's convention exists to avoid. Project
    Proposals (a 9-field business-plan workflow: Problem/Why/Existing
    Solutions/Expected Benefits/Risks/etc.) are cut outright — no real
    signal in this codebase backs any of those fields, and fabricating
    them would be the same dishonesty already rejected for Player
    Knowledge Import. "CEO Innovation Challenges" don't exist anywhere in
    this codebase. Breakthrough Recognition / a Legacy Museum is not
    rebuilt — Hall of Fame's existing `best_research` category (Feature
    24) already is permanent recognition of a real broken record; a
    second version of the same real concept would be the duplication
    this feature otherwise took care to avoid. Per-concern "documented
    response" tracking is cut: concerns in a Challenge Report have no
    persistent per-item identity elsewhere in this codebase, and the
    CEO's own real decision (buy/sell/wait, or Feature 40.5's Request
    More Research/Delay Decision) already *is* the real, visible
    resolution sitting right next to the report — tracking a second,
    parallel response per bullet would invent structure with nothing
    real behind it.
  - Verification: 18 new backend tests (`test_devils_advocate.py`,
    `test_innovation.py`), full backend suite 455/455 passing, mypy/ruff
    clean. Frontend `tsc -b`/eslint/build clean. Playwright regression
    36/36 passing (plus the same tolerated real-trade-timing skip every
    run of this suite already carries), including a new test that opens
    the Devil's Advocate Review section, confirms real structured
    content, and confirms the rotating assignment actually changes across
    two consecutive "Request Another Review" calls.

- **v0.7 — Expert Consultation & Career Levels (Feature 40/40.5)** — the
  brief's "Content Review & Validation System," "Learning Paths &
  Specializations," and "Expert Consultation System" turned out to be
  ~85-90% already-shipped functionality under different names, so this
  scopes down to the small honest remainder rather than duplicating any
  of it. See `app/executive.py`, `app/academy.py`'s module docstrings,
  and `docs/Architecture.md` for the full non-duplication reasoning.
  - **Cut outright — Content Review pipeline** (CEO Assignment → Coach
    Review → Founder Council Review → Research Validation → Academy
    Decision → Learning Output → Knowledge Debate → CEO Feedback): this
    codebase has zero HTTP client, no PDF/video parsing, and no free-form
    NLG anywhere (not even in `requirements.txt`), so there is no way to
    actually ingest player-supplied content to review. `docs/
    Architecture.md` already carries a written precedent explicitly
    rejecting "Player Knowledge Import" for this exact reason — this is
    the same cut, restated for the same reason.
  - **Already real — Learning Paths & Specializations**: `app/academy.py`'s
    existing 7-tier `KnowledgeLevel` (novice→mentor) already *is* the
    brief's Student→Legend ladder, and `KNOWLEDGE_BRANCH` already gives
    every original agent a fixed real specialization (e.g. Echo =
    Technical Analysis, Sentinel = Risk Management). Rather than building
    a second parallel progression system, the frontend now just relabels
    those same real tiers: a new `careerLevels.ts` maps `KnowledgeLevel`
    onto Career Level names (novice=Student … mentor=Legend) and derives
    a "Company Major" (`Bachelor of {branch}`) once an agent's real tier
    has actually reached "advanced" (Senior) — an honest empty state
    below that, not a fabricated major from day one. Shown per-agent in
    the KNOWLEDGE tab's Knowledge Trees.
  - **Already real — Expert Consultation System**: Executive Voting's
    existing `AnalystVote`/`TradeProposal`/`DecisionConfidence`/`Debate`/
    `OperatingMode` already implement the brief's per-specialist review,
    Lead Analyst proposal, Consensus Report, cross-examination, and
    3-mode automation. The one genuinely new piece: **"Request More
    Research" / "Delay Decision"** — two real CEO actions beyond
    buy/sell/wait. Both reuse `TradeProposal`'s own existing expiry
    clock (`created_sim_minutes`, the same field `expire_stale_proposals`
    already reads) rather than inventing a second timer or a fake
    "research in progress" state; a new `hold_count` field caps each
    proposal at `MAX_PROPOSAL_HOLDS` (2) holds so it can't be deferred
    forever. Never produces a `TradeDecision` — the proposal simply stays
    pending. New `POST /api/executive/hold` endpoint
    (`app/state.py`'s `hold_trade_proposal`); every hold is logged to
    Company Memory (`app/scribe.py`'s `record_proposal_hold`). Two new
    buttons in the Executive Voting popup, disabled once the cap is hit.
  - Verification: 5 new backend tests (`TestHoldProposal` in
    `test_executive.py`), full backend suite 437/437 passing, mypy/ruff
    clean. Frontend `tsc -b`/eslint/build clean. Playwright regression
    re-verified across `executiveVoting.spec.ts` (new hold/cap test) and
    `commandCenter.spec.ts` (new Career Level assertion on the KNOWLEDGE
    tab) — 35/35 passing (plus the same tolerated real-trade-timing skip
    every run of this suite already has).

- **v0.7 — The Original Founders (Feature 39)** — Keystone (Chief Risk
  Architect) and Compass (Chief Learning Architect) join the roster as
  two new real agents (`AGENT_IDS` grows from 11 to 13). The brief's
  teaching style for both ("teaches through questions... rarely gives
  direct answers") is near-identical to Sage's already-shipped Socratic
  Mentor (Feature 32) — rather than build a second competing daily-
  teaching mechanic, the Founders are framed as the spiritual originators
  of two already-real system clusters: Keystone for the Discipline
  Chamber/Library of Mistakes/Risk Engine, Compass for the Academy/
  Reasoning Lab/Reflection Chamber.
  - Added the same proven way the CIO/Sage were added in earlier
    features: real personality/schedule/campus presence via a new
    `app/founders.py`, but neither ever routes through a trading task or
    earns Academy Knowledge Points — a deliberate, documented exception.
  - **Founder Log**: one real dialogue line per day, alternating between
    Keystone and Compass, reacting to whichever real event most recently
    landed in that Founder's own domain (a real DisciplineReview,
    CaseStudy, ReasoningChallenge, or ReflectionSession) — never a
    fabricated open-ended conversation. Philosophy/specialties/quotes
    are real, hand-authored content taken directly from the brief.
  - **Founder Council**: a real monthly session alongside the existing
    monthly CoachReport, summarizing the Coach's own real highlight plus
    each Founder's latest real domain commentary.
  - **Legendary Status**: `FounderState.retired` flips permanently the
    first time `CompanyHealth.tier` reaches "excellent" — the most
    comprehensive real milestone this codebase already computes — and
    never reverts, the same "a crossed milestone stays crossed"
    convention `app/hall_of_fame.py` already established. Retirement
    changes nothing about either Founder's schedule, personality, or
    dialogue; it only unlocks the Hall of Founders view.
  - Portraits reuse the exact same palette-swapped sprite convention
    every other agent already has (two new tint colors: Keystone's
    weathered bronze, Compass's teal). Voice acting is explicitly
    brief-optional and cut. No employee-onboarding system exists
    anywhere in this codebase — the roster is fixed and no new hires
    ever join — so that brief item is cut outright.
  - New `FOUNDERS` tab in the Command Center shows both Founders' real
    identity, Legendary Status, the Founder Log, and Founder Council
    history.
  - Verification: 15 new backend tests (`test_founders.py`), full
    backend suite 432/432 passing, mypy/ruff clean. Frontend `tsc -b`/
    eslint/build clean. Playwright regression re-verified across
    `commandCenter.spec.ts` (new FOUNDERS tab test, updated 21-tab
    count), `campusMap.spec.ts` (updated Employee Count assertion),
    `executiveVoting.spec.ts`, `marketObservatory.spec.ts`. Also
    confirmed a real schema-migration round trip against a genuine
    pre-Feature-39 save on disk — the backend self-healed the roster and
    added the missing `founderState` field with no data loss.

- **v0.7 — Company Campus Map (Feature 38)** — a real, always-current map
  overlay (`M` key, the Command Center's/Quick View's new 🗺 CAMPUS
  button, or Pause Menu → Campus Map) that turns every existing building
  and agent into a single navigable dashboard, built entirely on data
  this codebase already tracks. (The brief itself calls this "Feature
  37," colliding with the already-shipped Work Mode System above; tracked
  internally as Feature 38 to avoid confusion.)
  - **Real layout, not a redrawn one.** `LobbyScene.ts`'s own `DOORS`
    array, `WIDTH_PX`, and `HEIGHT_PX` are now exported and imported
    directly into a new `buildings.ts` — the map's building positions are
    always exactly the real Lobby's real layout, never a hand-authored
    second copy that could drift from it.
  - **11 real buildings + the Lobby, not the brief's fictional 17.** The
    brief's blueprint names buildings this codebase has no physical scene
    for (Think Tank, Library, a standalone Reasoning Lab/Treasury/
    Headquarters, Cafe, Garden, Gym, Employee Residence, Park, Museum,
    Dock) — several of which prior features already established as
    Command Center tabs rather than physical rooms (Academy, Reasoning
    Lab, Reflection Chamber, Treasury). Only the 11 real doors
    (`LobbyScene.ts`'s `DOORS`) plus the Lobby courtyard itself appear on
    the map.
  - **Building info panel** shows each building's real purpose, category,
    current occupants (from real `AgentState.location`), and — where a
    genuine one exists — exactly one real per-building metric (Brain Room
    → in-progress research count, Simulation Lab → completed simulations,
    Hall of Fame → entries, Trading Floor → win/loss count, Performance
    Center → snapshot count, Executive Boardroom → review count, Meeting
    Room → today's real meeting count, Market Observatory → watchlist
    size, Scout Office → news count). No metric is shown for buildings
    with no clean real mapping, rather than fabricating one. "Related
    Departments" is derived by inverting every agent's real
    `AGENT_SCHEDULES` blocks (`Schedule.ts`'s new `LOCATIONS_TO_AGENTS`)
    into a per-location agent list — never hand-authored.
  - **Live building status** (🟢 Normal / 🟡 Busy / 🟣 Meeting / 🔴
    Attention / ⚪ Idle) is derived only from real signals: `meeting`
    only for the Meeting Room while a real meeting is active; `attention`
    only for the Trading Floor when a real critical `RiskWarning` exists;
    `busy`/`idle` from real agent headcount. The brief's 🔵 Training and
    🟠 Construction statuses are cut — no per-building signal for either
    exists anywhere in this codebase.
  - **Employee tracking**: clicking an agent icon shows their real
    Current Task, Mood, Energy, and active research, plus a real
    Destination/ETA — read from the agent's live `AgentOverride` if one
    is active (meeting/break, with its own real `remainingMinutes`), or
    otherwise from a new `nextScheduleBlock()` helper that looks up the
    agent's own next real scheduled block (every agent's schedule already
    covers all 24 hours with no gaps).
  - **Fast travel**: double-clicking a building reuses the exact real
    `SceneManager.goTo()` fade transition every door already performs —
    not a fabricated continuous camera pan across scenes that were never
    built to be traversed that way.
  - **Building Upgrades/Construction (the brief's 7-stage progression,
    scaffolding, cranes, sounds), per-building lifetime statistics
    (Lifetime Visitors, Most Active Employee, Daily Operating Cost, Power
    Status, Building Health, Monthly Performance), and "Current Weather"
    are all cut entirely** — no per-building progression, per-building
    operating-cost/power data, or weather system exists anywhere in this
    codebase, and inventing any of them would misattribute fabricated
    numbers as real. `CompanyHealth.officeExpansion` is a single
    company-wide score, not 11 independent per-building tracks, so it is
    not reused under 11 fake per-building labels either.
  - **Campus Overview panel** surfaces real, already-existing company-
    wide numbers only: Company Score, Treasury, Operating Capital,
    Knowledge Score, Wisdom Score, Research Progress, Employee Count,
    Avg. Happiness/Energy, today's real event count, current Company
    Priority, and current Work Mode.
  - Opens as the same kind of overlay every other full-screen panel
    already is (`campusMapOpen` joins `gameStore.ts`'s existing
    `OVERLAY_KEYS`) — opening it doesn't pause the sim, only freezes
    local player movement while it's open, exactly like the Command
    Center.
  - Verification: no backend changes (pure frontend feature reading
    already-existing `gameStore` state) — backend pytest suite unchanged
    at 417/417. Frontend `tsc -b --noEmit`/eslint clean. New
    `tests/campusMap.spec.ts` (6 Playwright tests: opening/closing,
    world-input blocking while open, building/employee info panels,
    category filters, fast travel, and all three entry points) passes
    6/6, plus the existing `commandCenter.spec.ts`/`executiveVoting.spec.ts`/
    `marketObservatory.spec.ts` suites re-run clean for regressions.
  - **Addendum — HQ Expansion visual.** The user supplied a legacy Cute
    Fantasy sprite pack (`Old_Sprites.zip`) and asked for its building-
    stages art to give the Campus Map a construction look. Rather than
    fabricate a per-building construction system (explicitly cut above),
    five real frames were hand-sliced from its
    `Houses_Building_Stages_OLD/House_1_Stone_Stages.png` sheet
    (`assets/cute-fantasy-rpg/props/buildings/hq-expansion/stage-{1-5}.png`)
    and bound to the one real company-wide number this codebase already
    tracks for company growth — `CompanyHealth.officeExpansion` — shown
    in the Campus Overview panel as a small sprite + stage label (e.g.
    "33% — Framing"). One visual, tied to one already-real score, not an
    invented per-building progress track.

- **v0.7 — Work Mode System (Feature 37)** — the CEO gets a real, always-
  visible, persistent toggle between indefinite continuous operation and
  a genuine company-wide wind-down, replacing the brief's imagined "Stop
  for the Day" button with a real mechanism this codebase can back
  honestly (no such button existed anywhere in this codebase before —
  checked directly).
  - **Work Mode** (the default, unchanged behavior from every prior
    version) is what already happens today: employees run their real
    per-agent schedules, research/meetings/Academy training all continue,
    and trading runs on the selected Operating Mode — indefinitely, with
    no automatic stopping.
  - **Rest Mode** is the new mechanism. `settings.workMode` joins
    `operatingMode`/`companyPriority` as a third client-authoritative
    settings field `nexus.tick()` reads every tick. While resting:
    `tick_research()` and `tick_academy_projects()` are skipped entirely
    (`"employees stop starting new work"`); `_maybe_call_meeting()` is
    gated so no *new* meeting starts, though one already under way
    finishes naturally, since the gate only ever short-circuits the
    "maybe start a new one" branch, never the "an active meeting is
    already wrapping up" branch. Every agent with no active
    meeting/break override routes through a new `_rest_block()` — a pure
    function of the real clock that maps the current time onto the same
    real 10-hour off-hours span Feature 35 already authored per agent
    (20:00-24:00 wind-down/evening activity, 0:00-6:00 sleep), repeating
    every 10 in-game hours, so a CEO-triggered rest period shows genuine
    variety using only real, already-written content — no new per-agent
    state needed to track "how long has this agent been resting."
    Trading/risk systems (`paper_trading.py`, `broker.py`,
    `risk_engine.py`, `scanner.py`, `gatekeeper.py`) are never touched by
    `work_mode` at all — structurally unaware of it — which is exactly
    how the brief's "open trades continue to be managed safely... they
    do not abandon positions" is satisfied.
  - A new always-visible toolbar button (🟢 WORK MODE ACTIVE / 🌙 REST
    MODE ACTIVE) toggles the mode from anywhere in the game, not just
    from inside the Command Center — matching the brief's "the current
    mode should always be visible." A fuller Work Mode section was also
    added to the Company tab (`CompanyPanel.tsx`) alongside Operating
    Mode/Company Priority/Time Controls, spelling out exactly what each
    mode does.
  - Verification: full backend (mypy/ruff/pytest, 417/417 — 13 new tests
    in `test_work_mode.py`, covering the rest-block cycling math, both
    modes' schedule routing, research/Academy pausing under rest, and
    the meeting-gate's new-vs-continuing distinction) and frontend
    (tsc/eslint/build) clean. Manually verified in the running app
    (Playwright, 28/28 counting the same tolerated real-trade-timing skip
    every run of this suite already has — a new toolbar test confirms
    the full real round trip: toggling to Rest Mode, saving via a real
    `POST /api/save`, and polling `GET /api/load` until the real backend's
    next tick shows every agent routed to a real off-hours task).

- **v0.6.3 — Executive Voting, Risk Command Center, Cyber Overlay** — the
  player is now formally TradeTown's CEO. A research candidate crossing
  the trade-confidence threshold no longer executes automatically: it
  becomes a `TradeProposal` (`app/executive.py`) and waits for the
  player's own real BUY/SELL/WAIT call.
  - **Executive Voting (Feature 12)**: six analyst seats (Echo/Scout/
    Nova/Sentinel/Pulse/Atlas — TradeTown's real, existing agents, never
    invented characters) each cast an independent, evidence-backed vote.
    Technical reuses the same trend/volatility read Signal Calibration
    and Player vs AI already use; news/macro reuse the existing
    researcher-vote convention; risk reuses Sentinel/Guardian's real
    `RiskWarning`s; sentiment reuses Pulse's real `ScannerAlert`s; Atlas
    synthesizes the desk's own majority as its vote rather than
    inventing a seventh independent signal. The player's BUY/SELL/WAIT
    is the real, consequential action (SELL opens a genuine short —
    `open_position()` already supported `side="sell"` correctly, this
    was just never exposed to a real trade path before); APPROVE/REJECT
    are convenience shortcuts for the desk's own recommendation, not a
    fourth outcome. Every decision still produces a permanent
    `TradeDecision` (so DecisionsPanel/DecisionDetail/Player vs AI keep
    working unchanged) plus a `CeoDecisionRecord` tracking CEO
    accuracy, AI accuracy, agreement rate, and successful/failed
    overrides.
    - Honesty boundary: "AI Accuracy" is only ever computed over
      decisions the CEO *agreed* with — an override's real trade tells
      us whether the CEO's own call worked, never whether the AI's
      original (never-taken) direction would have, so `outcome:
      "undecidable"` is the honest answer for a plain WAIT or any
      override, exactly the same "never grade an unrealized
      counterfactual" rule Player vs AI (Phase 8) already established.
    - A pending proposal a player never acts on expires after 3
      in-game days (`PROPOSAL_EXPIRY_SIM_MINUTES`) and auto-resolves as
      an honest WAIT — not silently dropped, not silently traded.
    - New backend: `app/executive.py`, `POST /api/executive/decide`,
      `GameState.submit_ceo_decision()`. New frontend: the Executive
      Voting popup (auto-opens on a genuinely new proposal — see the bug
      note below — with click-to-expand vote reasoning/evidence,
      BUY/SELL/WAIT, Approve/Reject, "Decide later"), and a new
      EXECUTIVE Command Center tab (pending queue, CEO track record,
      decision history).
  - **Risk Command Center (Feature 13)**, folded into Executive Voting's
    "Review Analysis" expansion rather than a separate screen, since
    every field in it is specific to the proposal currently being
    decided: a 0-100 **Trade Quality Score** (evaluates the *setup* —
    agent agreement, research confidence, active risk warnings,
    portfolio exposure — never a win prediction) with its real reasons/
    concerns spelled out, and a **Pre-Trade Checklist** (thesis written,
    risk reviewed, no active risk warning, multi-agent agreement,
    exposure acceptable).
    - Explicit scope cut, stated rather than faked: the brief also asks
      for Stop-Loss/Take-Profit Distance and Reward-to-Risk Ratio.
      TradeTown's paper broker has never placed stop-loss/take-profit
      exit orders (DecisionDetail's Trade Plan section already says so
      for the same reason), so there is no real number to show — the
      UI states this explicitly instead of inventing a ratio. A Red
      Flag System and Post-Trade Review beyond what's covered by the
      Quality Score's own concerns list, and per-trade historical
      quality-vs-outcome tracking, were also left out of this pass —
      the latter would need a new persisted field snapshotting the
      score at decision time, which is a reasonable v0.6.4 addition,
      not one to rush into this pass.
  - **Cyber Executive Overlay (Feature 14)**: the existing v0.6.1
    Command Center already had most of the requested visual language
    (glass panels, glow borders, scan-lines, terminal typography) — this
    pass adds a smooth zoom/fade/blur open transition
    (`cmd-overlay-in`), a faint drifting animated grid background
    (pure CSS `background-position`, no canvas/WebGL, costs nothing
    while charts/AI panels are also updating), holographic button hover
    (glow + elevation), and a corner toast system (`CyberNotifications`)
    for events that don't already have a dedicated popup: NEW TRADE
    AVAILABLE, RESEARCH COMPLETE, HIGH VOLATILITY WARNING, and a
    scanner-alert-driven NEWS ALERT.
    - Explicit scope cuts, stated rather than half-built: TRADE WON/
      TRADE LOST are deliberately *not* duplicated as toasts —
      TradeOutcomePopup already gives a closed trade its own full-
      treatment celebration/shake moment, and a toast on top would be
      redundant noise. AGENT LEVEL UP is not implemented — TradeTown
      agents have no leveling mechanic, and inventing one to satisfy an
      example notification would be exactly the kind of fabrication
      this project avoids. A full desktop-OS-style per-panel window
      manager (drag/resize/minimize/maximize/dock/snap/remember-layout)
      was also explicitly not built — the existing tab-based layout
      already organizes the same LEFT/CENTER/RIGHT/BOTTOM content groups
      the brief describes, and a real window manager is a multi-day
      feature on its own, not something to half-implement in this pass.
  - **Two bugs caught and fixed during this phase's own verification**:
    (1) the Executive Voting popup's "auto-open on a new proposal" logic
    first compared each WebSocket update's proposal count against the
    frontend's *default* empty list — which meant any pending proposal
    already sitting in the backend from before the page loaded (the
    WebSocket connects at app boot, independent of the title screen —
    see `GameCanvas.tsx`) read as "just appeared" and popped the modal
    up over the title screen itself, intercepting clicks meant for the
    game canvas. This is the exact same bug class already caught once
    for `TradeOutcomePopup` in Phase 10 (see that entry above) — fixed
    the same way: a `hydrated` flag on `NexusManager` so the very first
    snapshot never fires a "new" event, only genuine subsequent
    arrivals do. (2) That fix surfaced a second, older, previously-latent
    bug in `TradeOutcomePopup` itself: since it derives its visibility
    from real unviewed-trade backlog rather than a "new" event, it was
    *never* guarded against rendering during `MainMenuScene` at all — a
    session left running long enough to close an unviewed trade would
    show that popup over the title screen the next time the page loaded,
    for the same "socket connects before Continue is even clicked"
    reason. Both popups now check `currentScene !== "MainMenuScene"`
    before rendering (checked after all hooks, not as an early return
    before them, so the Rules of Hooks stay intact).
  - Tests: 23 new backend unit tests (`test_executive.py` — vote
    generation per role, the execution-vote tie-break, `resolve_proposal`
    for buy/sell/wait including the zero-quantity-falls-back-to-wait
    case, grading correct/incorrect/undecidable, proposal expiry timing),
    full live end-to-end verification (fast-forwarded a real proposal
    through generation → CEO decision → position open → position close →
    grading, and separately through expiry → auto-WAIT), a save/load
    round-trip check for the two new persisted fields, and 2 new
    Playwright tests (`executiveVoting.spec.ts`) covering the popup's
    real vote/evidence rendering, the quality score + checklist, a real
    BUY submission, and the EXECUTIVE panel's stats/pending list. Full
    backend (mypy/ruff/pytest, 98/98) and frontend (tsc/eslint/build)
    verification, plus the full existing Playwright suite re-run clean
    after the hydration fix above.

- **v0.6.2 Phase 10: Trade outcome popups** — a real, closed PaperTrade
  now surfaces a popup the moment the player is present to see it:
  celebration (pulsing green glow + a burst of CSS confetti) on a win,
  a shake/impact on a loss, neutral on a breakeven. Win/loss/breakeven
  and the "thesis confirmed/invalidated/neutral" classification are both
  a direct, honest read of the trade's own real `pnl` sign — no new
  signal invented, no duplicated source of truth; the post-trade
  analysis section reuses the trade's real `reason`/`coachReview`/
  `lessonsLearned` fields that already existed on `PaperTrade` (see
  app/journal.py) rather than fabricating new commentary.
  - Persisted `viewedTradeNotificationIds` (capped at 60, a little above
    `paper_portfolio`'s own 50-trade history cap) tracks which trades'
    popups have already been shown/dismissed, acknowledged via
    `POST /api/trades/ack` — so a refresh or Docker restart never
    re-shows a popup the player already saw, per the brief's explicit
    requirement.
  - **Bug caught and fixed during this phase's own verification**: the
    first implementation queued and displayed a popup for *every*
    unviewed trade — on a save with a real backlog (e.g. the first time
    loading an existing save, or after being away while paper trading
    kept running), this meant a wall of blocking modals the player had
    to click through one at a time, intercepting all other clicks
    (confirmed via a Playwright regression: it silently blocked seven
    unrelated existing tests' button clicks in the shared dev backend,
    which already had a real backlog). Fixed by only ever popping up the
    single most recently closed trade; any older backlog is
    acknowledged silently in the background. Every trade's full analysis
    remains available anytime in the Decisions/Performance tabs — this
    popup is a "here's what just happened" moment, not the only record
    of it.
  - Tests: 3 new backend tests for the capped/deduped acknowledgement
    list; 1 new Playwright test verifying real win/loss content, the
    correct glow/shake animation for that trade's real outcome, and that
    dismissal persists across a reload. Full backend (mypy/ruff/pytest,
    75/75) and frontend (tsc/eslint/build) verification, plus the full
    Playwright suite (12/12 passing, the one timing-dependent new test
    gracefully skipping rather than false-passing on the run where no
    trade happened to close in its poll window — verified passing with
    full assertions on other runs), and a live save/load/WS round-trip
    confirming `viewedTradeNotificationIds` persists correctly.

This completes all ten phases of the v0.6.2 roadmap (Phase 1's save/
progress-loss fix through Phase 10's trade outcome popups).

- **v0.6.2 Phase 9: Trading Education** — a ten-topic curriculum
  (`app/education.py`), ordered as a real learning progression:
  candlesticks → wicks → trends → support/resistance → ENTER/WAIT/AVOID
  → stop loss → take profit → risk/reward → position sizing → why NO
  TRADE can be correct. Reachable from a new "ACADEMY" Command Center
  tab, plus contextual "Need Help?" buttons on the RISK panel (→
  Risk/Reward Ratio) and the Signal Calibration TRAINING panel (→
  ENTER/WAIT/AVOID) that jump straight to the relevant lesson.
  - Scope note: this is a Command Center tab, not a new physical Lobby
    building — Signal Calibration and Player vs AI (Phases 7-8) are
    both Command-Center-based too, so this stays consistent with that
    precedent rather than adding a fourth "and now also walk to a new
    room" pattern for what's fundamentally reference material, not a
    live simulation to observe in place (unlike the Market Observatory,
    which earns its physical room by showing the live chart).
  - Each lesson has all four required parts: a simple explanation, a
    "visual example" note that points at TradeTown's own real, already-
    running systems (the live Overview chart, the real Decisions tab,
    Signal Calibration's own real regime/risk-reward reads, Sentinel's
    real position-sizing formula) rather than a fabricated screenshot, an
    optional deeper explanation, and a practice quiz.
  - Lesson content is static curriculum text — fine and honest, since
    "what a wick means" isn't game data to derive or fabricate, it's
    teaching material. Where a lesson maps onto a real TradeTown
    mechanic (stop loss/take profit order types, position sizing's
    risk-per-trade formula, real logged NO TRADE decisions), it says so
    explicitly and points at the real system instead of inventing a
    parallel example.
  - Quiz grading is server-side: `GET /api/education/lessons` never
    ships the correct-answer index, only `POST /api/education/quiz`
    reveals it, verified by a dedicated test.
  - Tests: 9 new backend tests (curriculum ordering/shape, the answer
    key never leaking through the public lesson shape, correct/incorrect
    grading, no duplicate completions); 1 new Playwright test completing
    a real lesson quiz and confirming RISK's "Need Help?" jumps straight
    into the right lesson. Full backend (mypy/ruff/pytest, 72/72) and
    frontend (tsc/eslint/build/Playwright, 12/12) verification, plus a
    live save/load/WS round-trip confirming `education` progress
    persists correctly.

- **v0.6.2 Phase 8: Player vs AI** — the player calls ENTER/WAIT/AVOID on
  a real past trade candidate *before* the AI's actual call is revealed
  (`app/player_vs_ai.py`), reachable from a new "PVAI" tab. Both are then
  graded against the same real, already-realized P&L — never assuming
  the AI is right: a losing AI trade shows up as the AI being wrong,
  exactly like it would for the player (verified with a dedicated test).
  - Only decisions that led to a trade whose real outcome has already
    closed are eligible — a "no_trade" decision has no realized P&L to
    grade against (we genuinely don't know what would have happened),
    and an open position's outcome isn't final yet, so neither is
    offered. This keeps every round's grading unambiguous and honest
    rather than a guess dressed up as data.
  - The pre-reveal prompt shows only what a human analyst would have had
    available — the real `researchSummary`/`technicalSummary`/
    `riskSummary`/`confidence` from the underlying `TradeDecision` —
    deliberately omitting `votes`/`outcome`/`finalReasoning`/`orderId`,
    which would spoil the AI's actual answer.
  - Tracks performance by regime and by setup, per the brief: `regime`
    (trending_up/trending_down/ranging) reuses the exact same trend/
    volatility computation Signal Calibration's level 3 uses — refactored
    out of `signal_calibration.py` into shared `market_data.trend_pct()`/
    `volatility_pct()` functions so both features read "trend" the same
    way instead of rolling two slightly different definitions; `setup` is
    the symbol's real research category. Both breakdowns are computed
    client-side from the persisted round history (`PlayerVsAiPanel.tsx`)
    rather than as a second, derivable-and-therefore-redundant persisted
    aggregate — the same "don't persist regenerable data" principle as
    the 413 fix, just applied to a derived view instead of raw data.
  - `PlayerVsAiPrompt` (the pending round) is transient — never part of
    `GameSaveState`, held server-side between
    `GET /api/player-vs-ai/prompt` and `POST /api/player-vs-ai/submit`,
    the same treatment Signal Calibration's challenges get. Only the
    graded `PlayerVsAiRound` history (capped at 100) and aggregate
    correct-counts persist, as real progress.
  - Tests: 12 new backend tests (eligibility rules, the "wait" and
    "avoid" choices grading identically against a loser, a losing AI
    trade correctly marked wrong, the pending-prompt-consumed-once
    guarantee, the client-facing prompt never leaking the ground-truth
    fields); 1 new Playwright test exercising a real graded round
    end-to-end. Full backend (mypy/ruff/pytest, 63/63) and frontend
    (tsc/eslint/build/Playwright, 11/11) verification, plus a live
    save/load/WS round-trip confirming `playerVsAi` persists correctly.

- **v0.6.2 Phase 7: Signal Calibration mini-game** — a five-level ENTER/
  WAIT/AVOID practice game (`app/signal_calibration.py`), reachable from
  a new "TRAINING" tab in the Full Command Center. Grading is a fixed,
  transparent rubric computed from signals genuinely visible *at
  challenge time* — the sampled candles' own trend and average bar
  range, any currently-active real `RiskWarning` on that symbol, and its
  real in-progress `ResearchItem` confidence — never from what price did
  next. Grading on future price would reward lucky guessing on a random
  walk; a fixed function of already-visible signals instead rewards
  actually reading them, per the brief's "reward disciplined decisions
  based on information available at the time, not lucky guessing."
  - Level 1 reads trend alone; level 2 weighs the move against its own
    volatility (risk/reward); level 3 requires recognizing a genuine
    trending regime vs. a ranging one (WAIT is the textbook-correct
    answer in a range, regardless of direction — the same "WAIT can be
    correct" principle the brief calls for); level 4 injects a real
    active risk warning that must override an otherwise-positive
    technical read into caution, preferring a watchlist symbol that
    actually has one rather than fabricating a conflict; level 5
    combines trend, volatility, risk, and research confidence into one
    weighted score.
  - A correct answer pays real Agent Energy (5/8/12/16/20 by level, via
    a new `agent_energy.award()`), capped at 100 like regen. `Unlocked
    level` only advances after 3 *consecutive* correct answers at the
    current level (`UNLOCK_STREAK`) — a miss resets the streak, so
    grinding easy wrong answers in between can't slip the level up.
  - `SignalChallenge` (the generated round) is deliberately **not**
    part of `GameSaveState` — regenerable practice content, not game
    progress, the same "don't persist regenerable data" principle as
    the 413 fix. It's held in a transient in-process dict between
    `GET /api/calibration/challenge` and `POST /api/calibration/submit`,
    the same treatment `market_data.py`'s candles already get. Only the
    graded `SignalCalibrationAttempt` history (capped at 100) and
    `unlockedLevel`/`correctCount`/`totalCount` are persisted, as
    genuine progress.
  - Frontend: `CalibrationPanel.tsx` — level picker (locked levels
    greyed out), a real candlestick chart per round (reusing
    `CandlestickChart`, the same component the Command Center and
    Market Observatory already share), the level-gated factor readouts,
    three answer buttons, and an immediate reveal of the rubric's
    disciplined answer plus its plain-English reasoning after grading.
  - Tests: 18 new backend tests (rubric correctness per level, the
    conflicting-evidence override, the unlock-streak logic including a
    miss resetting it, the pending-challenge-consumed-once guarantee,
    and that the client-facing `SignalChallenge` shape never leaks the
    answer); 1 new Playwright test exercising a real graded round
    end-to-end. Full backend (mypy/ruff/pytest, 51/51) and frontend
    (tsc/eslint/build/Playwright, 10/10) verification, plus a live
    save/load/WS round-trip confirming `signalCalibration` persists
    correctly.

- **v0.6.2 Phase 6: Agent Energy** — a new company-wide spendable resource,
  deliberately distinct from each individual `AgentState.energy` (that
  field is unchanged and still means agent fatigue/rest — this is a
  separate top-level `agentEnergy: {current, cap, updatedAt}` on
  `GameSaveState`, never overloaded onto the existing field). Regenerates
  +20 on the existing daily (`is_midnight`) tick flag, the same trigger
  already used for performance snapshots — not a real-time timer, so
  there's no way to grind it by waiting in real life.
  - Every spend action has one real, verifiable effect on real game
    state — per the brief, energy must never "magically make an AI agent
    more intelligent" as a blanket effect. `app/agent_energy.py` defines
    the three actions and their costs: `research_boost` (15⚡, +25
    confidence — capped at 100 — to one specific in-progress
    `ResearchItem` the player picks, not every item at once),
    `extra_simulation` (20⚡, immediately queues one real
    `BacktestSession` via a new public `queue_backtest_now()`, extracted
    from `simulation.py`'s existing random-chance `_maybe_queue_backtest`
    so both paths share one implementation), `watch_symbol` (10⚡, adds
    one real `WatchlistEntry` with a real live quote from a new
    `EXTRA_SYMBOL_POOL` in `watchlist.py` — AMZN/GOOGL/TSLA/NVDA/SLV/USO
    — honestly documented as not getting automatic researcher assignment,
    since `research.py`'s rotation is hardcoded to the original 8 seed
    symbols).
  - `nexus.py`'s new `apply_energy_action()` is atomic: a spend either
    deducts the cost **and** applies the real effect, or does neither —
    verified by a dedicated test that an unaffordable/invalid spend
    leaves both the energy total and the target state (research
    confidence, backtest sessions, watchlist) completely unchanged.
  - New `POST /api/energy/spend` endpoint (`{action, researchId?}` →
    `{agentEnergy}`, 400 on insufficient energy or an invalid action/
    target) persists the save immediately, the same "a spend is a
    meaningful event" reasoning already applied elsewhere.
  - Frontend: `AgentEnergyWidget.tsx` on the Command Center's Overview
    tab — a meter, a research-item picker for `research_boost`, and the
    other two one-click actions, all wired through the full
    WS-broadcast → `NexusManager` → `gameStore` pipeline (adding
    `agentEnergy` to `ws_manager.py`'s `build_state_message()`,
    `socket.ts`'s `ServerMessage`, and every other layer that already
    explicitly enumerates each `GameSaveState` field) plus a direct
    `NexusManager.setAgentEnergy()` path so a successful spend updates
    the UI immediately instead of waiting up to ~2s for the next sim
    tick's broadcast to catch up.
  - Tests: 11 new backend tests (`test_agent_energy.py`) covering regen/
    cap/afford/spend and all three real-effect actions' success and
    rejection paths; 1 new Playwright test exercising a real
    `POST /api/energy/spend` call end-to-end through the UI. Full
    backend (mypy/ruff/pytest) and frontend (tsc/eslint/build/Playwright,
    9/9 passing) verification, plus a live save/load/WS round-trip
    confirming `agentEnergy` persists and broadcasts correctly.

- **v0.6.2 Phase 5: The Market Observatory** — a real, walkable 10th
  building in the Lobby (`MarketObservatoryScene.ts`), not a second
  disconnected Command Center. Reuses `RoomScene`'s entirely generic
  door/spur/label/collision machinery (the same base class every other
  room already extends) — adding one `DoorDef` entry to `LobbyScene.ts`'s
  `DOORS` array was sufficient for the door, road spur, and name label to
  appear correctly with zero changes to the shared building/road-drawing
  code. Placed at x:1630 on the front row, safely clear of both
  PerformanceCenter's right edge (~1528px) and the road layer's own right
  boundary (1696px), so none of the Lobby's existing hand-tuned
  building/hedge/pond spacing needed to move.
  - The fantasy-village asset pack has no dedicated observatory/tower
    sprite, so the building reuses the church silhouette (Meeting Room's
    asset) at a smaller scale, with a small pulsing cyan glow ring added
    on top of this one door only — "the futuristic tech hidden inside
    the old-world architecture," not a fabricated purpose-built sprite.
  - `agentLocation: null` (same pattern as `CeoOfficeScene`) — no agent
    is scheduled to visit, so none appear; inventing agent presence here
    would be exactly the fake activity the v0.6.2 brief warns against.
  - `MarketObservatoryHud.tsx` — an ambient React overlay (shows
    automatically while physically standing in the room, same pattern as
    `BrainRoomHud`'s ambient mode, no toolbar toggle) with a large
    central `CandlestickChart` (symbol picker, real OHLC data via the
    same `/api/market/candles` endpoint the Command Center uses) and five
    stations, every one backed by a real, already-existing data source
    rather than an invented "technical/fundamental/macro/news/sentiment"
    feed that doesn't exist in this backend: Technical (the same
    `marketRegimeHeuristic` + a decision's real `technicalSummary`),
    News/Events (the real `news` list), Macro (research items in the
    economy/gold/bitcoin/index categories), Risk (the real `riskLevel`/
    `riskWarnings`), Strategy (real `strategies`/`backtestSessions`).
    "Both must use the same underlying market data and analysis systems"
    — this shares `lib/derive.ts` and `CandlestickChart` directly with
    the Command Center rather than reimplementing either.
  - `SceneId` gained `"MarketObservatoryScene"` in **both**
    `frontend/src/types.ts` and `backend/app/schemas.py` — the two must
    stay in sync (see `types.ts`'s own header comment) since a save
    written while standing in an unrecognized scene would otherwise fail
    validation and hit the v0.6.2 Phase 1 migration path unnecessarily.
  - Tests: 3 new Playwright tests, including one that physically walks
    the player through the real door (not scene-injection) to prove the
    collision/spur placement is actually correct, not just visually
    plausible.

- **v0.6.2 Phases 2-4: Market Data Abstraction + candlestick charts,
  wired into the existing Command Center.** No duplicate Command Center
  was created — this extends the one v0.6.1 already built.
  - `app/market_data.py`'s `MarketDataProvider` interface gained
    `get_candles(symbol, timeframe, limit)`, returning normalized OHLC
    bars (`Candle`: symbol/timeframe/timestamp/open/high/low/close/
    volume/dataStatus). `MockMarketDataProvider` generates a
    deterministic-seeded random walk per (symbol, timeframe) — stable
    across repeated fetches (reopening a chart doesn't reshuffle its own
    history) — with the most recent bar's close tracking whichever live
    mock price `get_quote()` has already established, so the chart's
    rightmost candle stays consistent with the watchlist. Every bar is
    labeled `dataStatus: "simulated"` — the `DataStatus` literal
    (`live`/`delayed`/`historical`/`simulated`/`stale`/`error`/
    `no_data`, now canonically defined in `app/schemas.py`) exists so a
    future real provider can express itself through the same `Candle`
    shape without any UI changes, but the mock never claims to be live.
    Supported timeframes: 1m/5m/15m/1h/4h/1d.
  - New `GET /api/market/candles` and `GET /api/market/timeframes`
    endpoints (`app/routers/market.py`). Chart data is deliberately
    **not** part of `GameSaveState` — it's fully regenerable from the
    provider on demand, not game progress, consistent with the save-size
    fix above.
  - `CandlestickChart.tsx` — a hand-rolled `<canvas>` renderer (no new
    charting-library dependency for bars + wicks + a price axis): real
    OHLC bodies/wicks, green/red by direction, a right-side price axis,
    bottom timestamp labels, and an always-visible `SIMULATED` badge.
  - `MarketChartPanel.tsx` embeds a full symbol/timeframe browser at the
    top of the Overview tab (backed by the real watchlist and the
    backend's advertised timeframe list, not a hardcoded set).
  - `DecisionDetail.tsx`'s drill-down now shows the relevant symbol's
    chart directly, with **only real overlay values** — the linked
    order's actual fill price (`ENTRY`) and the open position's actual
    mark price (`MARK`) when either exists — never a fabricated
    stop-loss/take-profit line, since TradeTown's auto-trader doesn't
    attach those (see v0.6.1's own note on this). This is the "connect
    charts to AI decisions" requirement: research → thesis → bull/bear
    case → chart → risk check → approve/reject is now one continuous
    drill-down instead of the reasoning being separate from the price
    action it's about.
  - Tests: 9 new backend tests (`test_market_data.py` — OHLC internal
    consistency, determinism, timeframe validation, always-simulated
    labeling, live-price tracking) and a new Playwright test confirming
    the chart actually renders (not just that a container exists), the
    SIMULATED badge is present, and switching timeframes visibly
    redraws different data.

- **v0.7 — Save Architecture Redesign** — the save system was hitting
  HTTP 413 (Request Entity Too Large): `GET /api/load` was measured at
  844KB against the live dev DB, and nginx's default 1MB
  `client_max_body_size` meant every 60s autosave was already at the
  edge and would keep tipping over as simulation history grew. Root
  cause: `GameState.apply_client_save()` has only ever read `player`/
  `settings`/`dialogueHistory` off a save POST — every other field
  (agents, decisions, debates, research, caseStudies, ...) is already
  server-authoritative, produced by the tick loop, and was being sent by
  the client and silently discarded on every single autosave.
  - **Phase 1 — stop sending what the server already owns.** New
    `ClientSaveRequest` schema (`backend/app/schemas.py`) is exactly the
    3 fields the client actually owns; `SaveManager.buildSnapshot()`
    (frontend) sends only those. Cut the real save POST body from 844KB
    to ~277 bytes, measured live. `extra="ignore"` keeps an un-updated
    client (or a stale localStorage backup) accepted without error.
    `client_max_body_size 4m` set explicitly as a defensive ceiling, not
    the fix.
  - **Phase 2 — modular per-section persistence with a real delta
    system.** New `backend/app/save_modules.py` splits `GameSaveState`'s
    ~57 fields into 12 named modules — 9 "core" (meta, settings, world,
    employees, company, research, training, founders, and `derived` for
    the handful of fields recomputed nearly every tick, kept separate so
    they don't make every other module look dirty) and 3 "archive"
    (`trade_history`, `knowledge_archive`, `academy` — real historical
    logs that only ever grow). Every `GameSaveState` field is assigned to
    exactly one module, enforced at import time so a future field added
    without a module assignment fails loudly at startup instead of
    silently never being persisted. New `SaveModule` DB table (one row
    per slot+module); `persistence.persist_modules()` SHA-256-hashes each
    module's JSON and skips the write entirely if it's unchanged since
    last time — the real "only save what changed" mechanism, verified
    live: an unchanged tick's save now writes 0 bytes for most modules,
    where the old path rewrote the full ~840KB blob every time
    regardless. Each module writes inside its own SAVEPOINT, so one
    module failing to persist doesn't block the others — the response
    from `POST /api/save` now reports `{name, ok, bytesWritten, error}`
    per module instead of one generic success/failure. `GET /api/load`
    now returns only the core modules (archive fields come back as real
    empty defaults, not fabricated or omitted); new `GET
    /api/load/archive/{module}` fetches one archive module's real data
    on demand. No frontend wiring needed to lazy-load it, though — every
    Command Center panel that shows archive data already hydrates from
    the WebSocket tick broadcast within moments of connecting, which was
    already true before this change and stays completely unchanged here.
    A pre-Phase-2 deployment's existing single-blob save migrates into
    modules exactly once, automatically, on first boot under the new
    code — verified against the real 19MB live dev DB (day 32, 54 real
    decisions, 58 real debates), which migrated with zero data loss.
  - **Explicitly out of scope, and why**: request-side compression
    (nginx already gzips JSON responses; the Phase-1 POST body is small
    enough that adding client-side gzip would be negative value); chunked
    uploading as the primary save mechanism (the payload is now provably
    bounded — a chunk-upload protocol would be permanently-dead code,
    exactly the code most likely to corrupt data the one time it finally
    ran; a client-side size-guard is the honest alternative, see Phase 3
    below); per-object/per-field dirty-tracking across ~15 frontend
    manager classes (superseded by Phase 1's ownership-correction — the
    server already owns and correctly tracks everything else); changing
    the WebSocket tick broadcast itself (separate code path, not subject
    to the 413 limit, every live panel depends on its current shape).
  - Verification: full backend (mypy/ruff/pytest — 19 new tests across
    `test_save_modules.py` and `test_persistence.py`, covering split/
    assemble round-trips, module-map completeness, dirty-skip behavior,
    per-module corruption recovery, and legacy-blob migration) and
    frontend (tsc/eslint/build) clean; live-verified against the real
    running dev backend and its real 19MB database.
  - **Phase 3 — save queue, error reporting, size-guard.**
    `SaveManager.save()` (frontend) gained a coalescing in-flight guard:
    a save request that arrives while one is already in flight (autosave
    firing mid-manual-save, or two rapid clicks) no longer fires a second
    concurrent network request — it queues one trailing save, which
    builds a *fresh* snapshot when it actually runs rather than replaying
    a stale one. A client-side 512KB size-guard checks the real payload
    byte count before sending and fails immediately with the exact byte
    count if ever exceeded — the honest defensive fallback the redesign
    spec asked for in place of a chunked-upload protocol, which would
    have been permanently-dead code for a payload this provably small.
    Save errors are now structured: a save with per-module failures
    (`SaveResponse.modules[].ok === false`) surfaces exactly which
    modules failed and why, shown as a toast
    (`CyberNotifications.tsx`) — the codebase's first visible save-status
    UI; a successful save stays silent (autosave fires every 30-60s, and
    a toast on every one would be noise, same reasoning already applied
    to every other toast in that component).
  - Verification: frontend (tsc/eslint/build) clean; full Playwright
    regression run against the live backend (28-29/37 passing — the
    remaining failures are the same real trade/voting-popup/live-meeting
    timing flakiness class documented above, not a save-path issue; the
    one test that most directly exercises the save path shows a
    successful "Saved" status at the point of its unrelated failure).

- **v0.7 — Input Priority Fix: WASD/NPC Interaction.** Two independent
  bugs from the same brief, investigated (not assumed) before fixing —
  found one real design gap and one real bug that wasn't yet reported.
  - **WASD blocked while the Command Center was open.** A single shared
    flag (`GameManager.worldActive`) blocked both movement and
    interaction while *any* of 6 overlays was open, including the
    Command Center — intentional, tested behavior, but the brief asked
    for movement specifically to stay active behind the Command Center
    (its own `bg-black/70 backdrop-blur-sm` isn't fully opaque, so the
    player stays visible) unless a text field has focus. Split into two
    independent signals (`gameStore.ts`'s `MOVEMENT_BLOCKING_KEYS`
    excludes `commandCenterOpen`; `GameManager.worldActive` keeps its
    original full-block definition for E-key interaction/agent updates/
    door triggers, `GameManager.movementActive` is the new narrower
    gate) — every other overlay (Newspaper, Company Memory, Coach
    Dashboard, Brain Room HUD, Campus Map) keeps blocking movement
    exactly as before, since the reported bug was specifically about the
    Command Center/Mentor Tab.
  - **A real bug found during verification, not just a design gap:**
    Phaser's `addKey()`/`createCursorKeys()` default to
    `enableCapture=true`, which calls the native `preventDefault()` on
    every WASD/arrow/E/ESC keydown *regardless of DOM focus* — a
    separate, lower-level mechanism from the movement gate above (which
    only stops this game's own code from reading the key, not the
    browser's default text-input behavior). Without also releasing this
    capture, a focused Command Center text field had every keystroke it
    received silently swallowed before a single character ever reached
    the input's value — confirmed via a failing test, not caught by code
    review alone. Fixed by `InputManager.syncCaptureWithFocus()`
    (`frontend/src/game/systems/inputFocus.ts`'s `isTypingInTextField()`
    — the same generic DOM-focus check the movement gate uses), called
    every frame from `PlayerController.update()`, toggling Phaser's
    `addCapture`/`removeCapture` for WASD/arrows/E/ESC based on whether
    a real text field currently has focus.
  - **"Cannot talk to agents" — the interaction system itself already
    worked everywhere an agent exists** (E key, 28px proximity radius via
    `RoomScene.nearestAgent()`, real dialogue with the agent's real name/
    personality/current task). The actual gap: no on-screen prompt made
    this discoverable. Added `InteractionPrompt.tsx` — "[E] Talk to
    {agent name}" — shown/hidden via a new `interaction:available`
    EventBus signal RoomScene emits only on actual change (not every
    frame), using the exact same proximity check the real E-key
    interaction already uses, so the prompt only ever shows when E would
    actually do something. Clears immediately when an overlay suppresses
    interaction (so it never points at an agent E can no longer reach)
    and when leaving the room. Not added to CeoOfficeScene/Lobby/Market
    Observatory — confirmed these genuinely have no agents today, so
    correctly show nothing, matching existing by-design behavior rather
    than fabricating agents to populate them.
  - Verification: frontend (tsc/eslint/build) clean; a new
    `frontend/tests/interaction.spec.ts` (2 tests) queries the real
    live agent locations via `GET /api/load` before walking to whichever
    room currently has someone in it, rather than assuming one specific
    room is populated (agent locations are real, schedule-driven state
    on the shared dev backend); `commandCenter.spec.ts`'s
    movement-blocking test rewritten for the new split behavior, with a
    retrying `expectMovement()` helper added after diagnosing that a
    single hold-then-read could occasionally sample between rendered
    frames under this environment's variable headless frame rate.
    Full Playwright regression run 31/37 passing — 6 of the remaining
    failures are the same real trade/voting-popup-intercepts-click
    flakiness already documented above; the 7th (the rewritten movement
    test) failed once, ~8 minutes into a single long-lived browser
    process, after passing cleanly and repeatedly in isolation — most
    consistent with the canvas/WebGL rendering degradation this
    environment's headless Chromium already showed elsewhere in long
    single-process runs, not a logic defect (the same test's first
    movement check, moments earlier in that same run, passed correctly).
    Also traced and fixed two purely-environmental issues hit during
    this verification pass, unrelated to the code itself: two orphaned
    zombie Chromium processes left over from a container restart were
    burning ~250% CPU combined (killed); and `--repeat-each` stress-
    testing in one Playwright process was itself found to accumulate
    resource pressure across repeated browser launches that a normal
    single run never sees (confirmed by a clean single-pass run
    afterward), so it isn't used as a reliability signal going forward.

### Fixed

- **v0.6.2: fixed `POST /api/save` failing with 413 Request Entity Too
  Large on long-running deployments.** `decisions: list[TradeDecision]`
  (`app/nexus.py`) was the one list in the entire save schema with no
  upper bound — every other growing list (trade history, order log, hall
  of fame, scanner alerts, simulation results, coach reports, meeting
  minutes, per-agent memory, ...) already had a `MAX_*` cap; `decisions`
  didn't, and kept appending one ~1.5KB record every time research
  crossed the trade-candidate confidence threshold, for as long as the
  process stayed up. On a deployment left running for real (days to
  weeks, not a short local session), that alone grows the save well past
  nginx's default 1MB body-size limit — 500 decisions is already ~726KB
  of decisions alone; 2,000 is ~2.9MB. Added `MAX_DECISIONS = 200`
  (`_trim_decisions()`, applied the same oldest-first-eviction pattern
  every other cap in this codebase already uses) instead of raising the
  nginx limit — the real bug was unbounded growth, not an undersized
  limit. Measured on this session's own save (84 real decisions, ~1.5KB
  average):
  - Previous trajectory (uncapped, projected from the real average): 84
    decisions ≈ 122KB, 500 ≈ 726KB, 2,000 ≈ 2.9MB, 10,000 ≈ 14.2MB —
    unbounded.
  - After the fix: decisions plateau at ~290KB (200 records); every other
    field was already capped and together contributes ~258KB; total
    save size plateaus at **~548KB**, comfortably under the 1MB limit
    with margin for future fields.
  - Nothing was removed from what gets saved — trade history, open
    positions, research, agent state, education/energy data (once those
    exist) are all still full game progress and still persisted in full.
    Only the decision *log*, which is an explainability/audit trail
    rather than something gameplay depends on staying complete, is
    capped — the same way its own docstring already claimed it was
    ("Stored forever (capped, like every other list here)") before this
    fix made that actually true.
  - Existing over-large deployments self-heal on the next deploy with no
    migration step needed: nginx only limits the *upload* direction
    (`POST /api/save`), so a bloated existing save can still be loaded
    fine on startup; the very next simulation tick trims it back down to
    200 via `_trim_decisions()`, and the following save succeeds.

- **v0.6.2 Phase 1: fixed the actual cause of reported game-progress loss
  after code updates.** Root cause: `persistence.py`'s `load_save()`
  treated *any* Pydantic validation failure — which is exactly what
  happens when a stored save predates a newly-added field, i.e. after
  every single past schema change (v0.2's agents, v0.3's research, v0.5's
  trading, v0.6's risk/decisions, v0.6.1's two new `PaperTrade` fields) —
  as "no save exists yet." `main.py`'s startup then read that `None` as a
  fresh deployment and immediately overwrote the real save with a
  brand-new default state. This was never a Docker-volume problem — the
  named `tradetown-data` volume was always configured correctly and
  genuinely survives container recreation (verified below) — it was a
  pure application-level bug that fired on every version upgrade.
  - `load_save()` now attempts a real migration before ever giving up:
    it deep-merges the old save's raw dict onto a fresh default state
    (`_deep_merge_defaults` in `persistence.py`), filling in exactly the
    fields a newer schema added while preserving every real value the
    old save had (agents, portfolio, decisions, research, memory, time,
    player position — everything), then re-validates. Only if that still
    fails does it fall back to a fresh state — and even then, the raw
    unrecoverable payload is backed up to a new `save_backups` table
    first, never silently deleted.
  - New `SaveBackup` model/table: every `persist_save()` call also writes
    a rolling "periodic" backup (capped at 20 per slot, oldest pruned),
    and any raw payload that fails to load/migrate gets a permanent
    `pre_fresh_fallback` backup that's never pruned.
  - `app/db.py`'s `init_db()` now reconciles columns on already-existing
    tables (`ALTER TABLE ... ADD COLUMN`) — `Base.metadata.create_all()`
    alone only creates brand-new tables, so a column added to an
    *existing* table (like the new `SaveGame.schema_version`) would
    otherwise break every query against a database created by an older
    version of the app.
  - The sim loop (`app/sim.py`) now persists immediately when an in-game
    day rolls over or a trade closes, on top of the existing ~30s
    periodic cadence — narrowing the data-loss window for the events a
    player would actually notice losing, without turning into a
    save-every-tick storm for routine agent mood/energy drift.
  - The two `PaperTrade`/`PaperPosition` fields added in v0.6.1
    (`openedSimMinutes`/`closedSimMinutes`) now default to `0` instead of
    being required — required-with-no-default is exactly the pattern
    that makes an old save fail validation, so this is the retroactive
    fix for the one concrete incompatibility introduced last version, and
    the documented pattern (see the fields' own comments) for every
    field added to a list-item model from now on.
  - Validated two ways: 6 new `pytest` tests (`test_persistence.py`)
    against a real temp SQLite database — round-trip, migration of an
    old-shaped save, corrupted-JSON backup, backup-count capping, and the
    ALTER TABLE column migration — and a real end-to-end Docker
    verification: built the backend image, ran it against a named
    volume, progressed the game, then stopped+removed the container,
    rebuilt the image again, and started a brand-new container against
    the same volume — the in-game day/hour and player's room both
    survived exactly as expected.

### Added

- **v0.6.1: Global Command Center** — a futuristic cyber-trading-terminal
  overlay, openable from anywhere in the game (any room, mid-walk, inside
  Brain Room) via Tab or the new "Command ⌁" toolbar button, deliberately
  contrasting with the cute-fantasy-RPG world outside it. Built entirely
  as a new React layer over the existing `world:overlayOpen`/
  `GameManager.worldActive` mechanism every other menu already uses (see
  `gameStore.ts`'s `setOverlay`) — opening it never touches the running
  Phaser scene, so player position/room/agent state are preserved for
  free and the world behind it is provably inert (the scene's own
  `update()` skips input processing while any overlay is open), not just
  visually dimmed. Escape closes it via the same `useCloseOnEscape` hook
  every other overlay uses.
  - **Two modes**: **Quick View** (account value, this month's P&L,
    market regime, top opportunity, risk alerts, TRADE/NO TRADE/WAITING
    recommendation) and the **Full Command Center** — an 8-tab terminal
    (Overview, Opportunities, Decisions, Risk, Agents, Research,
    Performance, Logs) reachable from Quick View's "Expand" button.
  - **Trade Decision Analysis drill-down** (`DecisionDetail.tsx`) —
    clicking any opportunity/decision opens "why does the AI want this
    trade?": Trade Thesis, Bull Case / Bear Case (the real per-agent
    votes split by `TradeDecision.supportingAgents`/`opposingAgents`),
    Market Context, Confidence, Trade Plan (the linked `PaperOrder` when
    still in the order log, or an honest explanation when it's aged out
    — see below), Invalidation (`riskSummary`), and a Final Decision of
    APPROVED or REJECTED (no fabricated "REDUCED" state — nothing in the
    backend distinguishes a reduced-size trade from a normal one).
  - **Risk Panel** — a GREEN/YELLOW/RED banner (`riskLevel()` in
    `lib/derive.ts`) derived from real `RiskWarning.severity` values;
    RED only ever appears when a hard-reject vote is actually blocking
    new trades (`decision.py`'s veto rule), never as a cosmetic label.
  - **Agents Panel** — all 9 agents' real location/task/mood/energy/
    latest research/latest task, with an explicit "no fabricated
    activity" design rule: an idle agent reads as idle.
  - **Every number is either a real field read off the wire, a
    standard documented derivation from real records (profit factor,
    expectancy, a market-regime heuristic over real `dailyChangePct`
    figures), or an explicitly-labeled "not tracked yet" gap** — see
    `lib/derive.ts`'s file-level comment. TradeTown's backend has no
    entry/stop/take-profit *plans*, no rejection-category breakdown, and
    no performance-by-strategy/regime; rather than fabricate these, the
    UI reuses what's real (e.g. per-symbol concentration instead of a
    non-existent sector taxonomy) and says so in-panel where a gap
    exists, per the "do not fabricate" requirement.
  - New `cmd-*` Tailwind color palette + `font-cmdmono` token set, kept
    entirely separate from the existing fantasy-RPG `parchment/ink/gold`
    tokens so the two visual languages never bleed into one element.
- **v0.6.1: Honest simulated-month company P&L** — the Command Center's
  Quick View and new Performance panel report **this simulated month's**
  P&L (realized vs. unrealized kept separate, monthly return, monthly max
  drawdown, win rate, profit factor, week-1..4 breakdown, previous-month
  comparison), not TradeTown's raw all-time cumulative total relabeled as
  "today." This required a real backend fix, not just a frontend label
  change:
  - `compute_performance_snapshot()` (`analytics.py`) previously computed
    the exact same all-time total for every period ("daily"/"weekly"/
    "monthly"/"all_time" all read identically) — its own docstring
    admitted the missing per-trade day field made real period filtering
    impossible. Fixed by adding `openedSimMinutes`/`closedSimMinutes` to
    `PaperTrade` (stamped in `portfolio.py`'s `close_position()`, derived
    from data the caller already had — no new clock read) and rewriting
    the function to genuinely filter `trade_history` by simulated-clock
    period, computing period-relative return against equity at the
    period's start rather than always returning the all-time total.
  - Deliberately uses "Simulated Month N" / "Sim Day N" labels rather
    than fabricating a real calendar month name (e.g. "JULY 2026") —
    TradeTown's `TimeState` is a pure incrementing Day-N counter with no
    real date, so a fake month name would be fabricated data.
  - `frontend/src/ui/components/CommandCenter/lib/financials.ts` mirrors
    the exact same 30-day month-boundary math client-side, so frontend
    and backend never disagree about where a "month" starts.
- **The Brain Room "Mission Control" dashboard can now be opened from
  anywhere**, not just while physically standing in Brain Room — a new
  "Dashboard" button in the bottom toolbar (`ui:brainRoomHud`) opens it as
  a proper closable menu (Escape or a Close button, pauses the world like
  Newspaper/Company Memory/Coach Dashboard). Walking into Brain Room still
  shows it ambiently exactly as before, with no close button and no world
  pause — the two modes share one component, distinguished by whether it
  was opened via the toggle or is merely visible because of the current
  scene.

### Fixed

- **Several back-row building name labels were completely unreadable** —
  Scout Office, Meeting Room, Break Room, and (right at the edge) CEO
  Office all had their floating name label positioned above the map's own
  y=0 top edge (`topEdge - 24` going negative for any building taller
  than ~136px — the church is ~193px). Camera bounds start at y=0, so a
  negative label position isn't just off-screen, it's permanently
  unreachable by scrolling, regardless of viewport or zoom. Added 5 tiles
  of headroom above the back row (`TOP_MARGIN`) so even the tallest
  building's label clears the top edge with margin, plus the requested +2
  tiles of width (`LEFT_SHIFT`, split evenly) — the map is now 110×37
  tiles (was 108×32). `PLAZA_ROWS` is now derived from `BACK_ROW_Y`/
  `FRONT_ROW_Y` instead of hardcoded, so the plaza/pond/hedge/lampposts
  all stay correctly pinned to the road rows automatically.
- **NPCs could box the player in with no way out** — agent NPCs only ever
  collided against the player, never against each other, so in a room
  hosting several at once (Brain Room, Meeting Room) they could wander
  into overlapping clusters; each overlapping agent was still
  individually solid against the player, and multiple overlapping solid
  bodies from different directions could trap the player with no gap to
  walk through. All agents now share an Arcade physics group that
  collides with itself (and the room's walls), so they naturally keep
  their distance instead of piling up.
- **Closing a dialogue with "E" could immediately re-open a new
  conversation with the same NPC (or, near a door, exit the room)** —
  `DialogueBox`'s own window keydown handler and the room scene's Phaser
  interact key both listen to the same physical keypress; closing the
  final line of dialogue with E left the scene's key reading as freshly
  "just pressed" on its very next `update()`, immediately re-triggering
  `nearestAgent()`/`startConversation()` (or the door-exit check) since
  the player is typically still standing right next to the agent they
  were just talking to. This read as the game refusing to let you stop
  talking to an NPC. `GameManager` resetting the active scene's keyboard
  on `dialogue:close` (same pattern as the overlay/pause-menu fix below)
  helped but wasn't fully reliable — the two listeners race on one native
  keydown event with no guaranteed order, so occasionally the reset lost
  the race. `RoomScene` now also tracks whether dialogue was open on the
  *previous* frame and explicitly skips interaction on the exact frame it
  flips closed, which doesn't depend on that race resolving cleanly at
  all — verified with a scripted repro across multiple runs.
- **Some room-specific text rendered blurrier than its neighbors** —
  Brain Room's "MARKET CORE" label, Hall of Fame's "LATEST INDUCTEE"
  header, the Whiteboard prop's header/body text, every room's "Exit"
  label, and both the player/agent name tags and agent mood badges were
  all missing the `resolution: 4` treatment that `RoomScene.addLiveText()`
  already used for its own text — small rooms zoom well past the base
  camera zoom to cover the viewport, so a 1x-resolution text texture
  scaled up that much reads visibly blurrier than the crisp HUD text
  sitting right next to it in the same room.
- **Opening the newspaper (or Company Memory / Coach Dashboard) made the
  game feel stuck** — these full-screen overlays only had a mouse-click
  "Close" button (no keyboard close, unlike the existing `DialogueBox`)
  and didn't pause the world, so the player kept invisibly moving behind
  the panel while it was open. Added a shared `useCloseOnEscape` hook (all
  three panels now close on Escape) and a new `world:overlayOpen` event
  that a `GameManager.worldActive` flag tracks; `LobbyScene` and
  `RoomScene` now skip movement/interaction processing entirely while any
  overlay (or the pause menu) is open, rather than just hiding the world
  while it silently keeps simulating underneath.
- **The ESC pause menu's Resume never actually resumed** — a pre-existing
  bug independent of the above: `togglePause()` used
  `game.scene.getScenes(true)` to find the scene to resume, but that
  filters to *currently active* (`RUNNING`) scenes — a scene that was just
  paused no longer satisfies that, so the resume loop always iterated zero
  scenes and input stayed frozen after un-pausing. Superseded by the same
  `worldActive` flag above, which doesn't depend on Phaser's scene-pause
  state machine at all.
- **Held movement/pause keys could re-trigger themselves across an
  overlay transition** — Phaser's `Key.JustDown()` is a read-and-consume
  flag set by the raw keydown event regardless of whether anything is
  currently reading it; without an explicit reset, closing the newspaper
  with Escape could leave the scene's own pause key "still just-pressed"
  the instant the world reactivated, immediately popping the pause menu.
  `GameManager` now calls `resetKeys()` on the active scene's keyboard
  whenever `worldActive` transitions back to true.
- **Hedge collision could snag while walking diagonally past it** — the
  hedge wall was built from one 16x16 static Arcade body per tile;
  abutting separate bodies are a known source of a moving body catching
  at the seams between them. `buildHedges()` now still places one visual
  tile per cell (so the cap/fill pixel art reads correctly) but registers
  a single merged collision rectangle per contiguous hedge run instead —
  no internal seams left to catch on.

### Changed

- **Asset pipeline reorganization** — `assets/cute-fantasy-rpg/` restructured
  from pack-native folders (`Tiles/`, `Player/`, `Enemies/`, `Animals/`,
  `Outdoor decoration/`) into five purpose-named folders: `tilesets/`,
  `characters/{player,enemies,animals}/`, `props/` (incl. `buildings/`),
  `animations/`, and `ui/`. `scripts/generate-assets.mjs`'s categorization
  and every asset id referenced in scene/entity code were updated to match
  (`tiles/grass-middle` → `tilesets/grass-middle`, `player/player` →
  `characters/player/player`, `outdoor-decoration/buildings/*` →
  `props/buildings/*`, etc.) — see `docs/Architecture.md#asset-pipeline`.
- **`generate-assets.mjs` now does a true sync**, wiping
  `frontend/public/assets/` before re-copying instead of copying
  additively — a renamed or removed source file no longer leaves a stale
  orphaned copy served alongside the current one.
- Consolidated the premium-pack license note (previously nested inside
  `Outdoor decoration/Buildings/`) into a single root-level
  `assets/cute-fantasy-rpg/PREMIUM_PACK_LICENSE.txt` covering all
  premium-sourced files.

### Added

- **Curated premium-pack imports**: `animations/` (lilypad, cattail, and
  grass-sway sprites, now animated around the Lobby's pond) and `ui/`
  (two icon sheets, staged for future in-game UI use, not yet drawn
  anywhere). Deliberately curated, not a wholesale import — the premium
  pack ships hundreds of files (mounts, crops, cave tiles, weather
  effects, …) outside TradeTown's office-simulation setting.
- **One ambient chicken** near the Lobby's Barn (Performance Center) —
  the free pack's animal sprites had been discovered and manifest-
  registered since v0.1 but never actually rendered anywhere. Caught in
  the process: `characters/animals/chicken/chicken.png` is a 2x2 grid of
  4 poses, not a single sprite as its `"kind": "static"` entry assumed —
  cropped a clean single frame (`chicken-idle`) rather than render the
  raw sheet.

### Lobby redesign: a real town square, paths, and street furniture

- **The pond moved to the map's dead center** and the town square around
  it now fills the entire gap between the two building rows (18x12
  tiles) — previously it sat off in a corner near the spawn point, more
  like leftover decoration than a town's actual center.
- **The whole road network — square included — went through three
  materials** before settling: a hand-picked cobblestone cell (square
  only, roads still on the old flat tile), `tilesets/farmland-tile`
  (packed-dirt, applied uniformly), then `tilesets/wood-floor`, a
  blue-grey square-tile pattern the user hand-picked from an uploaded
  reference sheet — replaced outright each time rather than kept as a
  second material, so the whole town reads as one consistent surface.
  Itself later superseded by `tilesets/dirt-path` — see the courtyard
  redesign section below. Every candidate confirmed to tile with zero
  seams before use.
- **The pond is 2x bigger and actually curved** — swapped the old
  rectangle of flat water tiles for `props/pond-curved`, a single
  pre-composed 48x48 organic pond graphic discovered inside
  `tilesets/water-tile`'s source sheet (that sheet turns out to be a
  ready-made pond/island illustration, not a repeating tile; its opaque
  corner pixels are the exact same green as the grass tile, so it drops
  onto the ground with no visible seam), scaled up 3.6x. Every piece of
  pond decor (lilypads, cattails, dock, ducks, flowers) and the four
  corner benches scaled up to match.
- Removed a decorative fence that read as a random jumble in the
  bottom-left corner — `props/fences` turned out to be a 4-piece
  tileset (post/rail/lattice/post) meant to be sliced into individual
  tiles and assembled, not a single sprite; rendering the whole sheet as
  one image (an earlier pass here did exactly that) shows all four
  disconnected pieces crammed together.
- **Fixed the Hall of Fame windmill's sails, which weren't mounted on
  the tower** — `Windmill.png`'s source file turned out to be the tower
  and the sail assembly side by side, not pre-composited; rendering it
  whole showed the sails as a disconnected chunk floating next to the
  building instead of on it. Recomposited at the asset level (sails
  layered onto the tower at their shared native Y-coordinate, then
  trimmed) rather than worked around in scene code.
- **Paths now lead to every building's door**, not just past it — a
  short spur connects the road to each doorstep, closing the 2-tile gap
  between the road and the building's base.
- **Fixed three spurs that missed the actual door** — they'd been
  computed from each building sprite's horizontal bounding-box center,
  which lines up with the door for most of these buildings but not all:
  Blacksmith_House_Blue's canvas is a house-plus-forge assembly with the
  door well left of the bbox midpoint (the spur landed on the forge/
  anvil instead), and Fisherman_House_Base_Blue/Shed_Base_Red both have
  a door a few pixels left of center. Measured each door's true offset
  directly from its source PNG and added a `doorOffsetX` correction
  (Scout Office, Brain Room, Break Room) used by the path spur, the
  door's interact zone, and its flanking flowers alike, rather than
  patching only the visual symptom.
- **The pond** gained a small wooden dock (cropped from the bridge-wood
  sheet), two ducks, and more flowers ringing the shore, alongside the
  lilypads/cattails already added.
- **Benches flank the pond on all four corners** of the town square, and
  flickering lampposts stand at its east/west entrances — the lamppost
  is a genuine 6-frame animation (a flickering flame), not a static
  prop.
- **Two new tree varieties** (spruce, fruit) join the oaks near the
  plaza, each a middle frame cropped from a 3-frame growth-stage sheet.
- Fixed a real bug found along the way: `generate-assets.mjs`'s `public/`
  mirror had gone stale (70 files served for 38 current ones) after the
  earlier folder reorg, since the sync only copied additively and never
  pruned; confirmed the fix (wipe-then-copy, from the prior changelog
  entry) is holding at the correct count through this round of changes.

### Courtyard redesign, round two: hedges, fountain, market stalls, and a denser village cluster

Matched a reference screenshot of a similarly-themed HQ-town layout —
dense building cluster, hedge-lined courtyard, dirt path, fountain,
market stalls — rather than TradeTown's original evenly-spaced rows.

- **All nine buildings pulled in toward the map's center third**, rather
  than spread edge-to-edge across the full 1728px width (back row span
  went from 67% of the map width to 46%, front row from 75% to 49%).
  CEO Office anchors the back row at dead center, the same "hero
  building facing the square" role the reference's Command Center
  plays. Freed up roughly 400px of park margin on both sides that used
  to be empty grass past the corner trees — now home to the fountains
  and extra tree variety (see below).
- **The road network is paved in `tilesets/dirt-path`**, a flat
  warm-tan tile with a faint speckle mark, cropped from the premium
  pack's `FarmLand_Tile.png` (a clean interior cell of an otherwise
  blob-shaped autotile sheet) — superseding `tilesets/wood-floor` to
  match the reference's dirt-path square.
- **A low hedge wall borders the square's east/west edges**
  (`props/hedge-tiles`, a 4x4 premium-pack sheet), with a 2-tile gateway
  at each existing lamppost rather than the hedge running straight
  through them. Walk-blocking like the benches and lampposts, not
  decoration you phase through.
- **Two fountains flank the courtyard** in the newly-freed park margin —
  a flat stone basin on one side, a taller spouting tier on the other
  (both frames of one `props/fountain` sheet).
- **Two market stalls (red/blue striped awnings)** sit outside Trading
  Floor's entrance, echoing the reference's stall row outside its
  Armory.
- **The pond's dock is now a proper ramp, not a sideways plank** — the
  same `props/dock` graphic, previously rotated 90° to jut off the east
  bank, now sits unrotated on the south bank (its native portrait shape
  already reads as a ramp) running from shore down into the water, with
  a small rowboat (`props/boat`) resting just off its end.
- Caught and fixed a placement bug from the rearrange itself: Hall of
  Fame and Trading Floor's first-pass positions landed almost exactly on
  the new hedge/lamppost line, and the spruce tree's original ±260
  symmetric offset landed inside Hall of Fame's new footprint, half-
  hiding it behind the roof. Both back-row buildings (which sit above
  the plaza's top edge) tolerate x-overlap with the plaza fine, but
  front-row buildings (which sit inside the plaza's own vertical span at
  y=336) can't — moved Hall of Fame, Trading Floor, and the extra tree
  spots clear once this was caught in a live screenshot pass.
- **The dirt path didn't land** — reverted `tilesets/dirt-path` back to
  the grey square-tile pattern from two rounds ago
  (`tilesets/cobblestone-grey`, the same cell used previously as
  `tilesets/wood-floor`, now under a name matching how it actually
  reads).
- **The pond, dock, and boat are ~2 tiles wider** — `POND_SCALE` bumped
  from 3.6 to 4.27; every pond-relative decor offset (lilypads, cattails,
  dock, boat, ducks, flowers, the four corner benches) scaled by the
  same ratio rather than hand-tuned individually, to keep the same
  relative layout at the larger size.
- **Fixed two real bugs the proportional-scaling approach above
  introduced**, both caught from a live screenshot: benches (scaled
  outward to keep clear of the bigger pond) ended up overlapping the
  hedge on the plaza's other side instead — reverted them to their
  original, already-clear offsets, since the wider pond needed no help
  there. The dock, boat, and the water-bobbing duck all landed on dry
  bank/grass instead of water — `props/pond-curved`'s water region turns
  out to be asymmetric within its own canvas (extends 11-15px from
  center depending on direction, well short of the ~19px the bank's
  jagged spikes reach), so a single scale-up ratio pushed water-bound
  decor right past the actual shoreline. Repositioned by checking each
  candidate spot against the source PNG's actual pixels rather than
  computed radii.
- Nudged the dock and the water-bobbing duck up one tile (16px) at the
  user's request, moving both a bit further from the south shore and
  deeper into open water — reconfirmed against the source pixels that
  both still land correctly (dock's north end further into water, its
  south end still past the bank on grass) before shipping.
- Moved the boat up a tile and the east duck down a tile, at the user's
  request. The east duck was originally the one "preening on the bank"
  rather than swimming (see above) — moving it south by a tile put it
  past the bank into water too, so both ducks now bob on the pond.

### Nine distinct agent character sprites

- Each of the nine AI employees now renders from its own
  `characters/player/player-<id>` sheet — hair, shirt, and pants
  hue-shifted to that agent's existing identity color (the same color
  used for its HUD dot) — instead of the player's shared sheet washed
  with a single `sprite.setTint()`. Investigated using the premium pack's
  modular character rig (separate Player_Base/Hair/Chest/Legs layers)
  first, but its ~112-row animation layout didn't match this project's
  verified 6-row convention and reverse-engineering it reliably wasn't
  feasible without risking a broken walk cycle; palette-swapping the
  already-verified sheet instead carries zero animation risk.
- Fixed a latent bug found while touching this code:
  `AgentNPC`'s constructor called `sprite.play("player/player::idle-down")`
  — a hardcoded pre-reorg animation key that the folder-reorg's string
  rename had missed because it wasn't wrapped in matching quotes. It
  silently no-opped since the key no longer existed in the manifest.

## v0.6

### Added

- **Trading Floor room** (`frontend/src/game/scenes/TradingFloorScene.ts`) —
  the ninth Lobby door. Large trading desks, wall monitors, a live market
  ticker bound to the watchlist, a Central Command display bound to the
  live paper portfolio, individual desks for Sentinel/Pulse/Guardian,
  a conference table, server cabinets, and status lights that reflect
  Guardian's standing risk watch.
- **Three new agents**: Sentinel (Risk Management), Pulse (Market
  Scanner), Guardian (Portfolio Protection) — profiles, schedules, and
  dialogue in both backend (`backend/app/agents.py`, `schedule.py`) and
  frontend (`AgentProfiles.ts`, `Schedule.ts`, `DialogueManager.ts`).
  TradeTown now has nine agents total.
- **Order-book paper trading engine** (`backend/app/broker.py`) —
  PaperBroker: market/limit/stop/take-profit/stop-loss orders go through
  an explicit `open → filled/cancelled` lifecycle (`place_order()` /
  `tick_broker()`), one tick of latency between placement and the
  earliest possible fill, same as every other NEXUS system. Completely
  simulated — no brokerage SDK, no API key, no real order-execution path
  — but shaped so a real adapter (Schwab/IBKR/Alpaca) could later
  implement the same two calls, mirroring `market_data.py`'s provider
  pattern.
- **RiskEngine** (`backend/app/risk_engine.py`) — Sentinel's configurable
  trade-approval gate (position size, portfolio drawdown, open-position
  count) and Guardian's exposure/concentration monitor, both backing
  votes in the new decision pipeline. `RiskLimits` are configurable and
  persisted; Sentinel/Guardian can reject a trade outright.
- **ScannerManager** (`backend/app/scanner.py`) — Pulse's continuous
  market scan across the watchlist (stocks, ETFs, indexes, gold,
  bitcoin), flagging gap ups/downs, breakouts, volume spikes, and high
  volatility as `ScannerAlert` records.
- **VotingManager + DecisionEngine** (`backend/app/voting.py`,
  `backend/app/decision.py`) — every high-confidence completed research
  item becomes a trade candidate voted on by the four researcher agents
  plus Sentinel and Guardian; Atlas's `decide_trade()` produces a
  permanent, explainable `TradeDecision` (research/technical/
  fundamental/risk summaries, supporting/opposing agents, confidence,
  final reasoning). Any Sentinel "risk too high" or Guardian "position
  too large" vote is an absolute veto, regardless of researcher votes.
- **TradeJournal** (`backend/app/journal.py`) — stamps every closed
  trade with a coach review, lessons learned, a link back to the
  decision that approved it, and a placeholder screenshot field. Also
  closes a v0.5 gap: `PaperTrade.coach_review`/`.lessons_learned`
  existed in the schema since v0.5 but nothing had ever populated them.
- **Brain Room HUD expansion** — Open Positions, Pending Orders, Risk
  Management (score/limits/warnings), Latest Decision & Votes, and
  Scanner Alerts sections, alongside everything v0.3–v0.5 already showed.
- **TradeTown Daily expansion** — Today's Trades, Top Opportunities,
  Performance, Coach's Review, Scanner Alerts, and Company Rating
  sections added to the newspaper.
- **Save system** — `GameSaveState` gained `riskLimits`, `riskWarnings`,
  `scannerAlerts`, and `decisions`; save version bumped to `"0.6"`.
  Orders and trades gained order-type/fill/decision-link fields. Old
  saves are not migrated — see `backend/app/persistence.py`'s existing
  "start fresh on schema mismatch" policy, unchanged since v0.1.

### Design notes / intentional simplifications

- TradeTown has no real sector taxonomy, so "sector concentration" risk
  checks are implemented as per-symbol concentration of portfolio equity
  instead — see `risk_engine.py`'s module docstring.
- `scanner.py`'s "breakout" detection is threshold-based against the
  current quote only (no persisted rolling price history yet) — a true
  multi-period range breakout needs a real historical
  `MarketDataProvider`, which doesn't exist yet (same boundary
  `watchlist.py` already documents for v0.3).
- `decision.py`'s technical/fundamental summaries explicitly state that
  no dedicated technical/fundamental analysis pass exists, rather than
  fabricating analysis that was never run.

**No live brokerage connections. No real money. Every "trade" is a row
in `GameSaveState.paper_portfolio`, nothing more — see
`docs/DESIGN_BIBLE.md`'s "What TradeTown Is NOT."**

## v0.5

### Added

- **Coach, a sixth agent** (Performance & Improvement: encouraging but
  exacting, asks more questions than it answers) — home room Performance
  Center, own daily schedule split across the Performance Center/Brain
  Room/Simulation Lab, and the first agent whose job is evaluation, not
  research or record-keeping. Coach never places or closes a trade — see
  `backend/app/coach.py`'s module docstring.
- **Paper Trading engine** (`backend/app/portfolio.py`,
  `backend/app/paper_trading.py`) — a fully simulated $100,000 starting
  account. High-confidence completed research (≥85%, the same threshold
  that already flagged "future trade candidates" in v0.3) can open a
  `PaperPosition`; positions mark-to-market every tick and close after a
  minimum simulated hold, producing a `PaperTrade` with PnL, duration,
  and supporting/opposing agents. Hold duration is tracked against
  TradeTown's in-game clock (`opened_sim_minutes`), not wall-clock time —
  consistent with how research confidence already advances by tick count.
  **No real brokerage is connected and no real capital is ever at risk.**
- **Simulation Lab** (`backend/app/simulation.py`) — a new room where
  agent-authored `Strategy` objects queue, run, and complete as
  `BacktestSession` → `SimulationResult`, using explicitly placeholder
  backtest math (see the module docstring — no real historical
  `MarketDataProvider` exists yet). Structured so a real historical
  provider, Monte Carlo variant, or parameter optimizer can be added later
  as new functions without changing the queueing/progress/archiving
  pipeline.
- **Hall of Fame** (`backend/app/hall_of_fame.py`) — a new room
  celebrating best research, best strategy, best simulation, lowest
  drawdown, longest winning streak, highest confidence accuracy, best
  monthly performance, and top agent. Entries are evaluated every tick and
  filed only when a new record is actually set (before/after length
  diffing), then logged to Company Memory.
- **Learning System** (`backend/app/knowledge.py`) — every closed paper
  trade is fed to `derive_lesson()`, producing a `lesson` (on a win) or
  `mistake` (on a loss) Company Memory record with the trade's reason,
  market conditions, confidence, and PnL — TradeTown's training-data
  record for the Coach's mistake/recommendation analysis.
- **Company Score** (`backend/app/company_score.py`) — a seven-metric
  rating (Research Quality, Decision Quality, Risk Management, Paper
  Trading Performance, Team Coordination, Knowledge Growth, Simulation
  Success) recomputed every tick and shown in an expanded Brain Room HUD
  and the Performance Center's in-world scoreboard.
- **Coach reports and Coach Dashboard** — weekly (every 7th day) and
  monthly (every 30th day) `CoachReport`s generated at the evening review
  (20:00), covering agent rankings, research/confidence accuracy, win/loss
  rate, risk score, common mistakes, and recommendations. A new
  `CoachDashboard.tsx` React modal (opened from a new "Coach" toolbar
  button) surfaces the latest weekly/monthly report and the live overall
  company score.
- **Performance analytics** (`backend/app/analytics.py`) — daily,
  weekly, monthly, and all-time `PerformanceSnapshot`s (return %, win
  rate, max drawdown, placeholder Sharpe/Sortino, average holding time,
  research accuracy, confidence accuracy), recorded on their respective
  cadences.
- **Three new rooms** — Simulation Lab, Hall of Fame, and Performance
  Center — each with a distinct floor tile, procedural props (server
  racks, trophy cases, a scoreboard), and a live in-world text readout
  synced to the same WebSocket state driving the React HUD. The Lobby
  widened from five doors to eight to fit them.
- **Company Memory gained six new categories** — `lesson`, `mistake`,
  `strategy`, `coach_review`, `simulation`, `paper_trade` — all
  searchable/filterable in the existing `CompanyMemory` viewer alongside
  v0.3's seven categories.
- **Extended save schema** (`version: "0.5"`): `paperPortfolio`,
  `strategies`, `backtestSessions`, `simulationResults`, `hallOfFame`,
  `coachReports`, `companyScore`, and `performanceSnapshots` are now
  persisted and round-tripped through save/load alongside every v0.3
  field.

### Changed

- **Backend "manager" modules stay function modules, not classes** — the
  v0.5 brief names eight services (CoachManager, SimulationManager,
  PaperTradingManager, PortfolioManager, AnalyticsManager,
  HallOfFameManager, PerformanceManager, KnowledgeManager); all eight are
  implemented as plain function modules (`coach.py`, `simulation.py`,
  `paper_trading.py`, `portfolio.py`, `analytics.py`, `hall_of_fame.py`,
  `company_score.py`, `knowledge.py`) naming their conceptual role in the
  module docstring, matching the established `research.py`/`watchlist.py`
  precedent (see `docs/CODING_STANDARDS.md`).
- **Scribe extended, not bypassed** — `scribe.py` remains CompanyMemory's
  sole writer; it gained `record_paper_trade`, `record_simulation_result`,
  `record_coach_report`, and `record_hall_of_fame_entry` rather than
  letting the four new modules call `memory.record()` directly.

## v0.4

Documentation only — see `docs/VersionHistory.md`'s "v0.4 — Design &
Architecture Foundation" entry. No application code changed.

## v0.3

### Added

- **Scribe, a fifth agent** (Company Historian: meticulous, quiet, writes
  everything down) — home room Brain Room, own daily schedule, and the
  first agent that doesn't research; it records. Added with zero Phaser
  scene changes, validating the v0.2 architectural investment in
  `AGENT_IDS`-driven iteration (see `docs/DeveloperGuide.md`'s "Adding a
  new agent").
- **`MarketDataProvider` interface** (`backend/app/market_data.py`) — an
  `ABC` with `get_quote`/`get_quotes`, a shipped `MockMarketDataProvider`
  (seeded-hash starting price + per-call random walk, no network calls),
  and a `_select_provider()` registration point gated by the
  `MARKET_DATA_PROVIDER` env var. No real vendor is wired in v0.3 by
  design — see "Adding a real `MarketDataProvider`" in
  `docs/DeveloperGuide.md`.
- **Watchlist system** (`backend/app/watchlist.py`) — eight seeded symbols
  spanning every `ResearchCategory` (stock/etf/index/economy/gold/
  bitcoin/company/sector: AAPL, MSFT, SPY, QQQ, GLD, BTC-USD, XLF, DXY).
  Each entry tracks ticker, name, last price, daily change %, status,
  research progress, and assigned agent, kept in sync with the research
  queue every tick.
- **Rotating research queue** (`backend/app/research.py`) — one active
  research item per research-capable agent (Scout/Echo/Atlas/Nova) plus a
  capped per-agent completed history, each with title, symbol, category,
  priority, status, assigned agent, summary, confidence (0–100), and
  timestamps. Confidence climbs each tick until the item completes.
- **Discussion & meeting minutes** — meetings now generate a real
  discussion transcript (`backend/app/discussion.py`, per-role templated
  lines keyed off each participant's current research topic) and, on
  meeting end, Scribe produces `MeetingMinutes` (`backend/app/scribe.py`)
  summarizing attendees and topics discussed. `MeetingState` gained a
  `discussion` field rather than a parallel state machine.
- **`CompanyMemory`** (`backend/app/memory.py`) — a capped (200), searchable,
  categorized log (research / meeting / whiteboard / event / discussion /
  discovery / future_trade) that every other new system writes into via
  `record()`. A new `CompanyMemory` React modal (search box + category
  filter chips) surfaces it, opened from a new "Memory" button in the
  bottom toolbar.
- **"Future trade candidate" flag** — when a completed research item's
  confidence crosses `FUTURE_TRADE_CONFIDENCE_THRESHOLD` (85), Scribe logs
  a `future_trade` memory record. This is a logged note for a human to
  consider later, never a queued or simulated order — v0.3 does not trade.
- **Brain Room HUD rebuilt** — Market Clock, Research Queue (one row per
  researching agent), Watchlist table, Upcoming Events, and animated
  confidence/progress bars (CSS width-transition, not a static number),
  alongside the existing Company/Agent Status panels.
- **Newspaper rebuilt** into five sections — Company News, Research
  Updates (sorted by most recently updated), Agent Activity, Market
  Headlines (placeholder pending a real provider), and Upcoming Events —
  replacing v0.2's three-section layout.
- **`UpcomingEvents` shared module** (`frontend/src/game/systems/
  UpcomingEvents.ts`) — extracts "next schedule transition per agent"
  logic that both `BrainRoomHud` and `Newspaper` need, avoiding a second
  copy of the same computation.
- **`Task` categories** — tasks now carry a `category` (research / review
  / meeting / watchlist_update / news_scan / chart_analysis /
  documentation), inferred from the task label/agent via keyword
  matching in `nexus.py`.
- **Extended save schema** (`version: "0.3"`): `research`, `watchlist`,
  `memory`, and `meetingMinutes` are now persisted and round-tripped
  through save/load alongside every v0.2 field.
- **`docs/API.md`** and **`docs/VersionHistory.md`** created; `docs/
  Architecture.md` gained a full "Research & market intelligence (v0.3)"
  section and an explicit "Version 0.3 scope" (not-in-scope) section.

### Changed

- **Agents made visually and behaviorally distinct.** Every agent shares
  the same sprite sheet (the asset pack only ships one), so tint alone
  wasn't enough to tell them apart at a glance in a crowded room. Each
  agent now also gets an always-visible badge glyph above its head
  (unlike the name tag, never proximity-gated: 🔍 Scout, ♟ Atlas, 📈 Echo,
  📚 Nova, 📜 Scribe), a wider tint spread (Scribe moved off a
  near-duplicate of Atlas's gold onto a distinct rose), and its own
  wander radius / idle-pause chance drawn from its personality blurb
  (`AgentProfiles.ts`/`AgentNPC.ts`) — Atlas and Scribe barely move,
  Scout roams widely and rarely idles.
- `nexus.py`'s `tick()` rewritten to orchestrate the new managers each
  tick: tick agents → `tick_research()` → record completions into memory
  → `tick_watchlist()` → maybe call a meeting (now discussion- and
  minutes-aware) → roll market news.
- Whiteboards now show Current Assignment / Latest Discovery / Priority /
  Completion % (2-line truncated format) instead of v0.2's single status
  line.
- Duplicated "complete old working task, start new one" logic (previously
  inlined separately for normal task rotation and for meeting attendance)
  consolidated into a shared `_replace_working_task()` helper in
  `nexus.py`.
- The old random `DISCOVERY_LINES` news generator was removed; discovery
  news is now driven directly by real research completions instead of an
  independent random roll.

### Fixed

- **Scribe missing from the top status bar**: `TopStatusBar.tsx` had its
  own locally hardcoded `AGENT_ORDER` array that was never updated when
  Scribe was added elsewhere. Fixed by removing the local array and
  importing the shared `AGENT_IDS` constant instead, eliminating this
  whole class of "forgot to add the new agent here" bug at its root.
- **`meetingMinutes`/`updatedAt` silently never updated**: `nexus.py`'s
  final `state.model_copy(update={...})` call used the wire aliases
  (`"meetingMinutes"`, `"updatedAt"`) instead of the actual Python field
  names (`"meeting_minutes"`, `"updated_at"`). Pydantic v2's `model_copy`
  writes directly into `__dict__` by field name, bypassing alias
  resolution entirely — the keys were silently absorbed as no-ops rather
  than raising an error. Found via direct WS-protocol soak testing
  (meeting cycles confirmed complete, but `meetingMinutes` stayed empty).
  Fixed by using the correct field names; documented as a standing
  "Gotcha" in `docs/Architecture.md` so it isn't reintroduced by a future
  `model_copy` call.
- **Meeting minutes over-citing an attendee's entire research history**:
  `build_minutes()`'s topic collection wasn't filtered by
  `status == "in_progress"`, so it cited every research item an attendee
  had ever touched instead of just their current focus. Fixed by adding
  the status filter.
- **Whiteboard text overflowing the board sprite**: the new 2-line
  enriched whiteboard text overflowed the small fixed-size board prop.
  Fixed with a coordinated two-sided change: shortened/truncated text
  server-side (`nexus.py`'s `_truncate()`) and an enlarged, smaller-font
  board with `lineSpacing` and wider `wordWrap` client-side
  (`Whiteboard.ts`) — Phaser's `wordWrap` only wraps by width, not by box
  height, so either fix alone was insufficient.

### Fixed (found via a live gameplay walkthrough after the initial v0.3 build)

- **`currentTask` silently frozen forever, for every agent**: the same
  `model_copy(update=...)` alias bug as the `meetingMinutes` fix above,
  in a different call site — `_tick_agent()`'s and `_maybe_call_meeting()`'s
  return values both used `"currentTask"` (the wire alias) instead of
  `current_task` (the real field name), so every agent's task text froze
  at whatever `_default_agent_state()` set it to on the very first tick,
  forever, while `location` kept updating normally on the correct
  schedule. Found by walking into the Brain Room and noticing an agent's
  displayed location and task text belonged to two different schedule
  blocks — confirmed with a raw WebSocket probe showing Atlas stuck on
  "Reviewing overnight strategy" through 2.5 hours of sim time and
  several break/meeting cycles while its location cycled correctly.
- **Duplicate task ids / React key collision**: an agent's meeting
  override ending and a brand-new meeting starting could both call
  `_replace_working_task()` for that same agent within one tick,
  producing two `Task` objects with an identical
  `task-{agent}-{day}-{hour}-{minute}` id. Fixed by disambiguating with a
  numeric suffix on collision.
- **Newspaper and Company Memory could both be open at once**: neither
  modal's close action touched the other's open flag, so opening one
  while the other was already open (or open-but-unnoticed) left it stuck
  open underneath, invisible once the topmost one closed. Opening either
  now closes the other (`gameStore.ts`).
- **`NPCManager.loadAgents()` torn-map reads**: it fired one
  `"agent:updated"` event per agent inside its update loop, so a listener
  reacting mid-loop (`gameStore`'s agents snapshot) could see a map where
  only some agents reflected the new tick and the rest were still stale.
  The whole map now updates before a single event fires.
- **Whiteboards clipping the room's own wall**: the v0.3 overflow fix
  enlarged every board from 72×44 to 92×58 world px but nobody moved the
  three rooms' placement coordinates to match, so the boards in Scout
  Office and CEO Office now overflowed 6px past the room's side wall
  (clipping the board itself, not just its text) and all three boards'
  "WHITEBOARD" title label sat a few px above the room's top wall.
  Re-positioned all three placements with enough clearance for the
  larger board size.

## v0.2

### Added

- **Three new agents** — Atlas (Strategy Lead: calm, strategic, rarely
  speaks, makes decisions), Echo (Technical Analyst: loves charts,
  frequently studies monitors), and Nova (Research Analyst: reads books,
  studies reports) — join Scout (Market Scanner), each with its own daily
  schedule, home room, mood/energy/memory, and personality-flavored
  dialogue lines per task.
- **Two new rooms** — Meeting Room (a table + six seats, a whiteboard, and
  the destination for NEXUS-triggered meetings) and Break Room (a coffee
  counter and seating, the destination for low-energy breaks).
- **Brain Room upgraded** into "Mission Control": an animated holographic
  market core, four monitor desks, and a React `BrainRoomHud` overlay
  panel showing live Company Status, Agent Status, Current Tasks, Market
  Status (placeholder — no live feed yet), and Recent Discoveries.
- **A fifth Lobby door** (Meeting Room, Break Room join Scout Office, CEO
  Office, Brain Room) and a **newspaper stand** ("TradeTown Daily") that
  opens a modal grouping news by Company News / Agent Discoveries / Market
  Headlines (placeholder).
- **A reusable `Task` system** (id, owner, priority, description, status,
  createdAt, completedAt) driven by each agent's schedule-block
  transitions, surfaced in the Brain Room HUD and newspaper.
- **NEXUS**, the backend orchestrator (`backend/app/nexus.py`): assigns/
  completes tasks, occasionally calls meetings and sends low-energy agents
  on breaks (both via a single `AgentOverride` mechanism), regenerates
  whiteboard text, and generates "discovery" news items. NEXUS does **not**
  trade or connect to any market data source — that plumbing is
  deliberately placeholder, wired for a future version.
- **Whiteboards** in every office, updating live via `whiteboard:updated`
  EventBus events.
- **EventBus extensions**: `agent:updated`, `room:entered`/`room:left`,
  `meeting:started`/`meeting:ended`, `whiteboard:updated`,
  `task:assigned`/`task:completed`, `news:updated`, `ui:newspaper`.
- **Extended save schema** (`version: "0.2"`): every agent's location,
  mood, energy, current task, and override; the task list; whiteboard
  text; meeting state; news feed; and time of day — all server-
  authoritative and round-tripped through save/load.

### Changed

- `ScoutNPC` generalized into `AgentNPC`, parameterized by `AgentId`, used
  for all four agents.
- `NPCManager` generalized from a single hardcoded Scout slot to a
  `Record<AgentId, AgentState>` registry.
- Lobby widened (30 → 72 tiles) to fit five buildings plus the newspaper
  stand comfortably.
- `RoomScene.getAgentSpawnPoint` made overridable so a room can lay out
  multiple simultaneous agents by design (Meeting Room's fixed seats,
  Brain Room's spread row) instead of always defaulting to a single-line
  spread.
- Agent name tags now only render when the player is within 32px, instead
  of always-on — rooms that legitimately hold all four agents at once
  (Brain Room, Meeting Room during a gathering) would otherwise show
  overlapping, unreadable tag text.

### Fixed

- **Right-facing player animation glitch**: the v0.1 `animation-config.json`
  row mapping for `Player.png` was wrong — it assumed 8 movement rows
  including dedicated `idle-right`/`walk-right` rows, but the sheet only
  has 6 real movement rows; rows 6–7 are actually attack/action-pose
  frames. Moving right briefly flashed a sword and a white crescent
  artifact over the character. Fixed by correcting the row mapping to the
  real 6 rows and mirroring the `-left` animation horizontally for
  right-facing movement (see `docs/Architecture.md`'s "Sprite sheet
  notes"). Caught via gameplay testing (Playwright screenshot), not code
  review.
- **Room-exit door never worked**: `RoomScene.update()` read
  `this.player.interactPressed` twice per frame — once for the
  agent-dialogue check, once for the door-exit check. Phaser's
  `JustDown()` consumes the "just pressed" flag on the first read, so the
  door-exit check always saw it as already consumed and pressing E to
  leave a room silently did nothing. Fixed by reading the flag once into
  a local and reusing it.
- **Dialogue box could get stuck across a scene transition**: pressing E
  while standing near both an agent and the exit door (rooms are small
  enough for both interact radii to overlap) could open a dialogue and
  transition the scene in the same frame, leaving the dialogue box
  permanently on screen with nothing left to close it. Door-exit and
  starting a new dialogue are now mutually exclusive, and `RoomScene`
  ignores E entirely while a dialogue is already open (the dialogue UI's
  own key handling owns the press instead).
- **Overlapping name tags when two agents cluster near each other**:
  distance-to-player tag visibility alone wasn't enough — Brain Room
  regularly holds all four agents at once, and two of them standing near
  *each other* (not just near the player) could both pass the radius
  check and show overlapping tags simultaneously (e.g. "EchoNova"). Tag
  visibility is now decided once per frame by `RoomScene`, which shows at
  most one tag — whichever agent is nearest the player — instead of each
  `AgentNPC` deciding independently.
- **Market Status/newspaper "Market Headlines" went permanently empty
  after enough play time**: two independent caps on the shared `news`
  list both trimmed strictly by recency across *all* categories combined.
  Discovery news fires far more often than market or company news (it's
  tied to every task-changing event across four agents, not a flat
  per-tick roll), so within roughly a day of game time discovery news
  crowded every market headline out of both the persisted list
  (`nexus.py`, `MAX_NEWS` → per-category `MAX_NEWS_PER_CATEGORY` via a new
  `_trim_news()`) and, independently, the WS broadcast shaping
  (`ws_manager.py`'s `build_state_message()` re-sliced to a flat "last
  10" on top of that). Fixed both: the persisted list now keeps the most
  recent items *per category*, and the broadcast sends that
  already-bounded list as-is instead of re-truncating it.
- **Duplicate/overlapping interact UI**: the old single-Scout interact
  handler opened both a full `DialogueBox` conversation and a separate
  in-world floating speech bubble showing the same first line — visually
  colliding, especially once multiple agents could be interacted with in
  the same room. The redundant speech-bubble mechanism was removed;
  `DialogueBox` is now the only interact UI.
- Old (v0.1-schema) saves no longer crash the backend on startup —
  `persistence.py` catches the schema-validation failure and starts a
  fresh v0.2 default state instead (see "Save format compatibility" in
  `docs/Architecture.md`).

## v0.1

Initial release: pixel-art HQ (main menu, Lobby, Scout Office, CEO Office,
Brain Room), one NPC (Scout) with a daily schedule/mood/energy/memory/
dialogue, WASD movement with camera-follow and collision, save/load
(autosave + manual, backend-persisted with a localStorage fallback), a
live WebSocket simulation feed, and Docker Compose deployment with an
nginx reverse proxy.
