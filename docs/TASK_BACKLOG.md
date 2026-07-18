# TradeTown Task Backlog

**Status:** Canonical, living. 268 tracked tasks across twelve
categories, none of them implemented as part of v0.4 (this version
produces documentation only — see `ROADMAP.md`'s v0.4 entry). This is
the backlog of *individual tasks*; `ROADMAP.md` is the backlog of
*versions*. A task's `Milestone` column points at the `ROADMAP.md`
version it most naturally belongs to, or `Backlog` if it isn't tied to
a specific committed version yet.

**Legend**

- **Priority:** Critical (blocks its milestone) / High / Medium / Low
- **Complexity:** XS (<1hr) / S (a few hours) / M (1–2 days) / L (3–5
  days) / XL (1–2+ weeks)
- **Dependencies:** the real file, system, or prior task this needs —
  `none` where a task is genuinely standalone

Two honest baselines worth stating before the tables, since several
tasks below exist specifically to close these gaps: **there are zero
automated tests anywhere in this repository today**, and **there is no
audio system of any kind today** (no `this.sound` usage, no music, no
SFX — `SettingsManager`'s `musicVolume`/`sfxVolume` settings currently
control nothing). Both are called out again in their own sections below
rather than hidden in a generic "add tests"/"add audio" one-liner.

---

## Gameplay (34)

| # | Task | Priority | Complexity | Dependencies | Milestone |
|---|---|---|---|---|---|
| G1 | Implement Coach's core review loop (surface a `future_trade` record, ask the player about it) | Critical | L | `CompanyMemory` (shipped) | v0.5 |
| G2 | Implement Simulation Lab room + backtest trigger UI | High | XL | Historical `MarketDataProvider` (A12) | v0.6 |
| G3 | Implement Paper Trading ledger + position lifecycle | Critical | XL | Simulation Lab, Ledger agent | v0.7 |
| G4 | Implement Strategy Marketplace save-sharing format | High | L | Save schema extension | v0.8 |
| G5 | Implement Risk Engine HUD panel | High | L | Paper Trading ledger | v0.9 |
| G6 | Add "propose new watchlist symbol" flow (Hunter) | Medium | M | Hunter agent implemented | Backlog |
| G7 | Add player-adjustable research priority weights | Medium | M | Strategy Marketplace | v0.8 |
| G8 | Add "what happened while you were away" return summary | High | M | none | v0.5 |
| G9 | Add on-demand agent status request (no wait for HUD refresh) | Low | S | none | Backlog |
| G10 | Add day-length/pacing variation to schedule blocks | Low | M | `schedule.py` | Backlog |
| G11 | Add multiple save slots | High | L | `persistence.py` rework | v1.2 |
| G12 | Add non-competitive milestone tracker | Low | M | `CompanyMemory` | Backlog |
| G13 | Add real-elapsed-days company anniversary event | Low | S | `TimeManager.ts` | Backlog |
| G14 | Add ambient agent-to-agent hallway small talk (non-mechanical) | Low | M | `DialogueManager.ts` | Backlog |
| G15 | Add player-triggerable "call a meeting" action | Medium | M | `nexus.py`'s `_maybe_call_meeting` | v0.5 |
| G16 | Add drag-to-reorder watchlist priority | Medium | M | Watchlist UI | v0.8 |
| G17 | Add new-employee onboarding beat (in-world, per new agent) | Low | M | `DialogueManager.ts` | Backlog |
| G18 | Add interactive props to CEO Office | Low | S | `CeoOfficeScene.ts` | Backlog |
| G19 | Add research-item detail modal (click a Research Queue row) | Medium | M | `BrainRoomHud.tsx` | v0.5 |
| G20 | Add watchlist symbol detail modal with price history chart | Medium | L | Real `MarketDataProvider` | v0.6 |
| G21 | Add meeting-attendance history view | Low | M | `CompanyMemory` | Backlog |
| G22 | Add "why did this happen" news-item → source-research link | Medium | M | News + Company Memory | v0.5 |
| G23 | Add configurable simulation speed (fast-forward) | Medium | M | `config.py` | Backlog |
| G24 | Add agent vacation/PTO simulation | Low | M | `schedule.py` | Backlog |
| G25 | Add cosmetic multi-day Lobby weather/ambiance cycle | Low | S | `LobbyScene.ts` | Backlog |
| G26 | Add progressive hiring flow unlocking planned agents | High | L | `AI_AGENT_BIBLE.md` roster | v1.1 |
| G27 | Add player-nameable company | Low | S | `GameSaveState` | Backlog |
| G28 | Add end-of-day special-edition newspaper summary | Medium | M | `Newspaper.tsx` | v0.5 |
| G29 | Add agent retirement/replacement mechanic | Low | L | `AGENT_IDS` rework | v2.0 |
| G30 | Add first-time-player guided company tour | Medium | M | `DialogueManager.ts` | v0.5 |
| G31 | Add a "quiet mode" toggle pausing ambient wander/dialogue randomness (screenshots/streaming) | Low | S | none | Backlog |
| G32 | Add per-room ambient population caps once the roster grows past ~10 agents | Medium | M | `RoomScene.ts` | v1.1 |
| G33 | Add a company-history scrubber (replay past days from `CompanyMemory`) | Low | L | `CompanyMemory` | Backlog |
| G34 | Add configurable per-room NPC wander boundaries (currently one radius constant) | Low | S | `AgentNPC.ts` | Backlog |

## UI (28)

| # | Task | Priority | Complexity | Dependencies | Milestone |
|---|---|---|---|---|---|
| U1 | Shared `useModalEscape`-style hook so every modal closes on `Escape` | High | S | `gameStore.ts` | v0.5 |
| U2 | Click-outside-to-close for every modal | Medium | S | all `ui/components/` modals | v0.5 |
| U3 | Colorblind-safe ▲/▼ supplement to bullish/bearish color | High | S | `BrainRoomHud.tsx`, Watchlist | v0.5 |
| U4 | Text-size accessibility setting | Medium | M | `SettingsMenu.tsx` | v0.5 |
| U5 | Key-remapping settings UI | Medium | M | `InputManager.ts`, `SettingsMenu.tsx` | v0.5 |
| U6 | Lobby minimap | Low | M | `LobbyScene.ts` | Backlog |
| U7 | Research Queue sort/filter controls | Medium | S | `BrainRoomHud.tsx` | v0.5 |
| U8 | Watchlist column sort | Medium | S | `BrainRoomHud.tsx` | v0.5 |
| U9 | Company Memory export (text/JSON download) | Low | S | `CompanyMemory.tsx` | Backlog |
| U10 | Newspaper archive (browse past editions) | Medium | M | `Newspaper.tsx` + backend history | v0.5 |
| U11 | Dark/light UI-chrome theme toggle | Low | M | `tailwind.config.js` | Backlog |
| U12 | Toast/alert chip system for rare urgent notices (Watchtower) | Medium | M | `EventBus.ts` | v0.9 |
| U13 | Loading-skeleton states before first WS message | Low | S | all modals | Backlog |
| U14 | Confirmation dialog before a destructive Load overwrite | Medium | S | `SaveManager.ts` | v0.5 |
| U15 | Keyboard-shortcut cheat-sheet overlay | Low | S | new component | Backlog |
| U16 | Player-adjustable camera zoom beyond auto cover-fit | Low | M | `CameraManager.ts` | Backlog |
| U17 | Agent portrait/avatar closeup in `DialogueBox` | Medium | M | `DialogueBox.tsx` | Backlog |
| U18 | Confidence-score historical sparkline (not just current %) | Medium | M | backend history tracking | v0.6 |
| U19 | Drag-resizable Brain Room HUD panel | Low | L | `BrainRoomHud.tsx` | Backlog |
| U20 | Mobile/touch control scheme | High | XL | `InputManager.ts` rework | v1.3 |
| U21 | Screen-reader ARIA pass across the React UI layer | Medium | L | all `ui/components/` | v1.0 |
| U22 | "Reduce motion" setting (disables non-essential tweens) | Medium | M | `CameraManager.ts`, `BrainRoomScene.ts` | v0.5 |
| U23 | Company Memory record expand/collapse detail view | Low | S | `CompanyMemory.tsx` | Backlog |
| U24 | Confirm-before-persist on Settings changes | Low | S | `SettingsManager.ts` | Backlog |
| U25 | Player-repositionable HUD panels | Low | L | `BrainRoomHud.tsx` | Backlog |
| U26 | Settings-level toggle for ambient camera/prop tween intensity | Low | S | `CameraManager.ts` | Backlog |
| U27 | Compact/expanded density toggle for the Brain Room HUD | Low | M | `BrainRoomHud.tsx` | Backlog |
| U28 | Tooltip system for truncated whiteboard/HUD text | Medium | M | `Whiteboard.ts`, `BrainRoomHud.tsx` | Backlog |

## AI (33)

| # | Task | Priority | Complexity | Dependencies | Milestone |
|---|---|---|---|---|---|
| A1 | Implement Coach (schema, schedule, dialogue, review flow) | Critical | L | `AGENT_IDS` extension | v0.5 |
| A2 | Implement Quant (schema, schedule, dialogue, backtest trigger) | High | L | Simulation Lab | v0.6 |
| A3 | Implement Pulse (schema, schedule, dialogue) | Medium | M | Real-time `MarketDataProvider` | Backlog |
| A4 | Implement Macro (schema, schedule, dialogue) | Medium | M | `economy`/`index` category use | Backlog |
| A5 | Implement Oracle (schema, schedule, dialogue, scenario modeling) | Medium | L | Simulation Lab | v0.6 |
| A6 | Implement Guardian (schema, schedule, dialogue, boundary checks) | High | M | Risk Engine scaffolding | v0.9 |
| A7 | Implement Hunter (schema, schedule, dialogue, proposal flow) | Medium | M | Watchlist proposal UI (G6) | Backlog |
| A8 | Implement Watchtower (schema, schedule, dialogue, anomaly detection) | Medium | M | Risk Engine scaffolding | v0.9 |
| A9 | Implement Lab (schema, schedule, dialogue, queue operator) | Medium | S | Simulation Lab | v0.6 |
| A10 | Implement Ledger (schema, schedule, dialogue, bookkeeping) | High | L | Paper Trading ledger | v0.7 |
| A11 | Real `MarketDataProvider` adapter (one live vendor) | High | L | `market_data.py` | Backlog |
| A12 | Historical `MarketDataProvider` adapter for Simulation Lab | High | L | `market_data.py` | v0.6 |
| A13 | Model-backed meeting discussion (replace `discussion.py` templates) | Medium | L | `discussion.py` | Backlog |
| A14 | Confidence-vs-outcome calibration tracking per agent | High | L | Coach, Paper Trading | v0.7 |
| A15 | Configurable per-agent research speed/weighting | Medium | M | `research.py` | v0.8 |
| A16 | Cross-agent citation in generated discussion | Medium | M | `discussion.py` | Backlog |
| A17 | Mood influenced by real outcomes, not just random drift | Medium | M | `nexus.py`, Paper Trading | v0.7 |
| A18 | Relevance-based meeting-attendee selection (not pure random) | Medium | M | `nexus.py` | Backlog |
| A19 | Research-queue rebalancing when a symbol is added mid-game | Medium | M | `research.py` | v0.8 |
| A20 | Agent "specialization drift" over long sessions | Low | L | `research.py` | Backlog |
| A21 | NEXUS decision audit log (why a meeting fired, why a break happened) | Medium | M | new `MemoryCategory` | v0.5 |
| A22 | Configurable meeting frequency/duration | Low | S | `config.py` | Backlog |
| A23 | Player-adjustable schedule editor | Low | L | `schedule.py`, save schema | v1.1 |
| A24 | Multi-symbol (macro-style) research items | Medium | M | `research.py`, Macro agent | Backlog |
| A25 | Research-priority auto-escalation on watchlist volatility | Medium | M | `watchlist.py`, `research.py` | v0.6 |
| A26 | Backtest result caching in Simulation Lab | Medium | M | Simulation Lab backend | v0.6 |
| A27 | Scenario-modeling data structures for Oracle | Medium | L | `schemas.py` extension | v0.6 |
| A28 | Guardian trade-boundary integration test | Critical | M | Paper Trading | v0.7 |
| A29 | Dialogue-tone consistency pass graded against personality | Low | M | `DialogueManager.ts` | Backlog |
| A30 | NEXUS tick profiling/instrumentation | Medium | S | `nexus.py`, `sim.py` | v0.9 |
| A31 | Per-agent "confidence style" tuning (some round up, some hedge) | Low | M | `research.py` | Backlog |
| A32 | Agent-initiated small talk when idle near another agent | Low | M | `AgentNPC.ts`, `DialogueManager.ts` | Backlog |
| A33 | NEXUS decision-replay debugging tool | Medium | M | `nexus.py` | Backlog |

## Infrastructure (22)

| # | Task | Priority | Complexity | Dependencies | Milestone |
|---|---|---|---|---|---|
| I1 | Add `pyproject.toml` with explicit ruff/mypy config | High | S | none | Backlog |
| I2 | Stand up `backend/tests/` + first `pytest` suite | High | M | `pytest` already a dev dependency | Backlog |
| I3 | Add a frontend Vitest test runner | High | M | `package.json` | Backlog |
| I4 | Add a CI pipeline (lint + typecheck + test on PR) | High | M | I2, I3 | Backlog |
| I5 | Add pre-commit hooks (ruff, eslint) | Medium | S | none | Backlog |
| I6 | Multi-company save support | Critical | XL | `persistence.py`, `state.py` rewrite | v1.2 |
| I7 | Database migration tooling (Alembic) | Medium | M | `db.py`, `models.py` | Backlog |
| I8 | Structured logging pass (replace ad hoc `logger` calls) | Medium | M | backend-wide | Backlog |
| I9 | Environment-based feature-flag system | Low | M | `config.py` | Backlog |
| I10 | Multi-process backend scaling investigation | Low | XL | `state.py` singleton rework | v2.0 |
| I11 | Staging/production Compose environment separation | Medium | M | `docker-compose.yml` | Backlog |
| I12 | Automated Docker image vulnerability scanning in CI | Medium | S | I4 | Backlog |
| I13 | Backup/restore tooling beyond the manual `docker run tar` command | Medium | M | `deploy/` | Backlog |
| I14 | REST endpoint rate limiting | Low | S | `routers/` | Backlog |
| I15 | Request logging/observability middleware | Low | M | `main.py` | Backlog |
| I16 | `.env.example` completeness check in CI | Low | S | I4 | Backlog |
| I17 | Typed OpenAPI client generation for the frontend | Low | M | `schemas.py`, `net/api.ts` | Backlog |
| I18 | Companion/mobile read-only API surface | Medium | L | new router | v1.3 |
| I19 | WebSocket reconnect telemetry | Low | S | `socket.ts` | Backlog |
| I20 | Branch-strategy migration to `main` + feature branches | Medium | M | process only, no code | Backlog (trigger-based — see `CODING_STANDARDS.md`) |
| I21 | Add a task-runner wrapper (make/just) for common dev commands | Low | S | none | Backlog |
| I22 | Add dependency-update automation (Dependabot/Renovate) | Low | S | none | Backlog |

## Performance (17)

| # | Task | Priority | Complexity | Dependencies | Milestone |
|---|---|---|---|---|---|
| P1 | Profile NEXUS tick duration at 15+ agents | High | M | `nexus.py` | v0.9+ |
| P2 | Investigate WS delta updates vs. full-snapshot broadcast | Medium | L | `ws_manager.py` | Backlog |
| P3 | React re-render audit on `gameStore.ts` consumers | Medium | M | `gameStore.ts`, components | Backlog |
| P4 | Phaser texture-atlas consolidation | Low | M | `AssetLoader.ts`, `generate-assets.mjs` | Backlog |
| P5 | Lazy-load non-active-scene assets | Medium | M | `PreloadScene.ts` | Backlog |
| P6 | SQLite → Postgres migration path for larger saves | Low | L | `db.py` | v1.2 |
| P7 | Memory-cap tuning once agent count grows (Pulse's write volume) | Medium | M | `memory.py` | Backlog |
| P8 | Confidence-bar animation frame-budget audit | Low | S | `BrainRoomHud.tsx` | Backlog |
| P9 | Reduce redundant `EventBus` emits per tick | Medium | M | `NexusManager.ts` | Backlog |
| P10 | Frontend bundle-size audit + code splitting | Low | M | `vite.config.ts` | Backlog |
| P11 | Tick-interval vs. game-minutes-per-tick pacing tuning pass | Low | S | `config.py` | Backlog |
| P12 | Server-side tick-timing metrics endpoint | Medium | S | `main.py`, `sim.py` | Backlog |
| P13 | Whiteboard text-truncation re-render optimization | Low | S | `nexus.py`, `Whiteboard.ts` | Backlog |
| P14 | Camera zoom-recalculation throttle on window resize | Low | S | `CameraManager.ts` | Backlog |
| P15 | Incremental (not full-rescan) asset manifest regeneration | Low | M | `generate-assets.mjs` | Backlog |
| P16 | Add a frontend performance budget check in CI | Low | M | I4 | Backlog |
| P17 | Investigate Phaser sprite object-pooling for larger rosters | Low | M | `AgentNPC.ts` | v1.1 |

## Networking (17)

| # | Task | Priority | Complexity | Dependencies | Milestone |
|---|---|---|---|---|---|
| N1 | WebSocket protocol-version field | Medium | M | `ws_manager.py`, `socket.ts` | Backlog |
| N2 | Graceful schema-migration handling for older connected clients | Medium | M | `schemas.py`, `ws.py` | Backlog |
| N3 | Reconnect state reconciliation (avoid full resync every time) | Medium | M | `socket.ts` | Backlog |
| N4 | WS heartbeat/ping-pong health check | Low | S | `ws_manager.py` | Backlog |
| N5 | Document multi-client save-conflict behavior (currently last-write-wins) | Medium | S | docs only | Backlog |
| N6 | REST search endpoint for `CompanyMemory` (`memory.search()` exists, unrouted) | Medium | S | `routers/`, `memory.py` | v0.5 |
| N7 | WS message compression | Low | M | `ws_manager.py` | Backlog |
| N8 | Authenticated session support (multi-company prep) | High | L | new auth module | v1.2 |
| N9 | CORS origin validation hardening | Low | S | `config.py` | Backlog |
| N10 | REST API rate limiting | Low | S | `routers/` | Backlog |
| N11 | WS subprotocol negotiation for future companion clients | Low | M | `ws.py` | v1.3 |
| N12 | Offline action queue-and-replay | Low | L | `socket.ts` | Backlog |
| N13 | Server-sent-events fallback for restrictive networks | Low | M | `routers/` | Backlog |
| N14 | Toggleable API request/response debug logging | Low | S | `main.py` | Backlog |
| N15 | WS connection-count metrics | Low | S | `ws_manager.py` | Backlog |
| N16 | Configurable WS broadcast throttling for low-bandwidth clients | Low | M | `ws_manager.py` | Backlog |
| N17 | REST fallback poll mode for WS-unfriendly networks | Low | M | `net/api.ts` | Backlog |

## Trading (22)

*Every task in this section is explicitly gated by `DESIGN_BIBLE.md`'s
"What TradeTown Is NOT" boundary — none of them authorize real-money
execution on their own, and several exist specifically to enforce that
boundary in code, not just in policy.*

| # | Task | Priority | Complexity | Dependencies | Milestone |
|---|---|---|---|---|---|
| T1 | Design the paper-trading ledger schema | Critical | M | `schemas.py` | v0.7 |
| T2 | Implement paper-trade execution flow (candidate → position) | Critical | L | Ledger agent | v0.7 |
| T3 | Implement paper P&L calculation | High | M | Watchlist price feed | v0.7 |
| T4 | Implement paper position-sizing rules | Medium | M | Risk Engine | v0.9 |
| T5 | Implement Guardian boundary-enforcement checks | Critical | M | Risk Engine | v0.9 |
| T6 | Design a brokerage execution-adapter interface (mirrors `MarketDataProvider`) | High | L | new module | v1.0 |
| T7 | Design the brokerage authorization/re-consent flow | Critical | M | Guardian | v1.0 |
| T8 | Implement paper-trade history view UI | Medium | M | new component | v0.7 |
| T9 | Implement risk-concentration calculation | High | M | Risk Engine | v0.9 |
| T10 | Implement confidence-vs-outcome calibration report | High | M | Coach, Paper Trading | v0.7 |
| T11 | Research spike: real-brokerage sandbox/testnet integration path | Medium | L | none | v1.0 |
| T12 | Implement paper-trade close/exit flow | High | M | Ledger agent | v0.7 |
| T13 | Implement simulated stop-loss/take-profit | Medium | M | Paper Trading | v0.7 |
| T14 | Design multi-strategy paper portfolio support | Medium | L | Strategy Marketplace | v0.8 |
| T15 | Implement trade-rationale audit trail (links back to source research) | High | M | `CompanyMemory` | v0.7 |
| T16 | Design a double-confirmation UX for any future real-money action | Critical | M | Guardian | v1.0 |
| T17 | Implement paper-trading fee/tax simulation for realism | Low | M | Ledger agent | Backlog |
| T18 | Research spike: brokerage credential storage security model | Critical | L | none | v1.0 |
| T19 | Implement a self-only, historical-only paper-performance view | Low | M | Ledger agent | Backlog |
| T20 | Implement a kill-switch/emergency-halt for any future live trading path | Critical | M | Guardian | v1.0 |
| T21 | Design a paper-trade dispute/correction flow (fat-finger simulation) | Low | M | Ledger agent | Backlog |
| T22 | Implement a cooling-off period between a flagged candidate and paper execution | Medium | S | Ledger agent | v0.7 |

## Testing (22)

*Starting from the honest current baseline of zero automated tests
(see `CODING_STANDARDS.md`'s Testing Requirements section).*

| # | Task | Priority | Complexity | Dependencies | Milestone |
|---|---|---|---|---|---|
| Q1 | `pytest` suite for `research.py`'s `tick_research()` | High | S | `backend/tests/` (I2) | Backlog |
| Q2 | `pytest` suite for `watchlist.py`'s `tick_watchlist()` | High | S | I2 | Backlog |
| Q3 | `pytest` suite for `nexus.py`'s `_tick_agent()` | High | M | I2 | Backlog |
| Q4 | `pytest` suite for `nexus.py`'s `_maybe_call_meeting()` | High | M | I2 | Backlog |
| Q5 | `pytest` suite for `scribe.py`'s `build_minutes()` | Medium | S | I2 | Backlog |
| Q6 | Regression test for every past `model_copy` alias bug | High | S | I2 | Backlog |
| Q7 | Vitest suite for `UpcomingEvents.ts` | Medium | S | Vitest runner (I3) | Backlog |
| Q8 | Vitest suite for `EventBus.ts` | Medium | S | I3 | Backlog |
| Q9 | Formalize the Playwright suite (currently ad hoc scratch scripts) | High | L | `frontend/e2e/` (new) | Backlog |
| Q10 | Playwright regression test for modal mutual-exclusion | Medium | S | Q9 | Backlog |
| Q11 | Load test: WS broadcast under 50+ simulated clients | Medium | M | none | Backlog |
| Q12 | Automated multi-hour soak-test script | Medium | M | none | Backlog |
| Q13 | Save/load round-trip regression test | High | S | I2 | Backlog |
| Q14 | Docker Compose smoke test in CI | High | M | I4 | Backlog |
| Q15 | Cross-browser Playwright matrix (Chromium/Firefox/WebKit) | Low | M | Q9 | Backlog |
| Q16 | Automated accessibility audit (axe-core) | Medium | M | Q9 | v1.0 |
| Q17 | Visual regression testing (screenshot diffing) | Low | L | Q9 | Backlog |
| Q18 | `MockMarketDataProvider` edge-case test suite | Medium | S | I2 | Backlog |
| Q19 | Schema-migration test suite (old save → default fallback) | High | M | I2 | Backlog |
| Q20 | Test-coverage reporting + minimum-threshold CI gate | Medium | M | I4 | Backlog |
| Q21 | Mutation-testing pass on core `nexus.py` pipeline functions | Low | L | I2 | Backlog |
| Q22 | Contract test verifying `schemas.py`/`types.ts` field parity | High | M | I3, I4 | Backlog |

## Art (22)

| # | Task | Priority | Complexity | Dependencies | Milestone |
|---|---|---|---|---|---|
| R1 | License audit refresh for the `cute-fantasy-rpg` pack | Low | S | none | Backlog |
| R2 | Simulation Lab room tileset/prop selection (existing pack only) | Medium | M | none | v0.6 |
| R3 | Coach's Office room tileset/prop selection (existing pack only) | Medium | S | none | v0.5 |
| R4 | Badge glyphs for planned agents once implemented | Medium | S | `AgentProfiles.ts` per agent | Backlog |
| R5 | Risk Engine HUD iconography (within pixel-art rules) | Medium | S | existing pack or procedural | v0.9 |
| R6 | Ledger/Finance nook prop set | Low | S | existing pack only | v0.7 |
| R7 | Cosmetic seasonal Lobby decoration variants | Low | M | `LobbyScene.ts` | Backlog |
| R8 | Paper-ledger UI visual treatment (parchment ledger book) | Medium | M | `UI_UX_BIBLE.md` palette | v0.7 |
| R9 | Company Memory record-type icons | Low | S | `CompanyMemory.tsx` | Backlog |
| R10 | Procedural newspaper section-header treatment (no new art) | Low | S | `Newspaper.tsx` | Backlog |
| R11 | Meeting Room seating variant for a larger future roster | Medium | M | `MeetingRoomScene.ts` | v1.1 |
| R12 | Break Room prop-variety pass | Low | S | `BreakRoomScene.ts` | Backlog |
| R13 | Player character recolor-only customization | Low | M | `PlayerController.ts` | Backlog |
| R14 | Subtle badge idle-bob animation | Low | S | `AgentNPC.ts` | Backlog |
| R15 | Holographic-core visual variants tied to company mood | Low | M | `BrainRoomScene.ts` | Backlog |
| R16 | Department-color-coded whiteboard variants | Low | S | `Whiteboard.ts` | Backlog |
| R17 | Boot-scene branding pass | Low | S | `BootScene.ts` | Backlog |
| R18 | Main-menu background parallax | Low | M | `MainMenuScene.ts` | Backlog |
| R19 | Milestone/achievement badge iconography | Low | S | new system (G12) | Backlog |
| R20 | Dark-mode-safe pixel-art contrast audit | Low | S | `UI_UX_BIBLE.md` | Backlog |
| R21 | Subtle per-agent shadow/lighting variation | Low | S | `AgentNPC.ts` | Backlog |
| R22 | Settings-level integer pixel-scale option for high-DPI displays | Medium | M | `CameraManager.ts` | Backlog |

## Audio (17)

*Every task in this section builds on a genuinely empty baseline — see
this document's opening note. Task AU1 and AU8 are the two highest-value
items precisely because nothing downstream can work until they exist.*

| # | Task | Priority | Complexity | Dependencies | Milestone |
|---|---|---|---|---|---|
| AU1 | Implement the base audio system (Phaser sound manager wiring) | Critical | L | `GameManager.ts` | Backlog |
| AU2 | Source/license an ambient office background music loop | High | M | asset licensing review | Backlog |
| AU3 | Footstep SFX tied to player movement | Medium | S | `PlayerController.ts` | Backlog |
| AU4 | Door-open/interact SFX | Medium | S | `RoomScene.ts` | Backlog |
| AU5 | UI click/hover SFX | Medium | S | `ui/components/` | Backlog |
| AU6 | Meeting start/end audio cue | Medium | S | `EventBus.ts` meeting events | Backlog |
| AU7 | Research-completion "discovery" chime | Medium | S | `EventBus.ts` research events | Backlog |
| AU8 | Wire `musicVolume`/`sfxVolume` settings to real audio (currently a no-op) | Critical | M | AU1 | Backlog |
| AU9 | Per-room ambient audio variation | Low | M | `RoomScene.ts` | Backlog |
| AU10 | Dialogue "typewriter" SFX | Low | S | `DialogueBox.tsx` | Backlog |
| AU11 | Notification/alert chime for Watchtower | Medium | S | v0.9 dependency | v0.9 |
| AU12 | Visual-only accessibility mode (captions for audio cues) | Medium | M | `UI_UX_BIBLE.md` accessibility | Backlog |
| AU13 | Mute-all hotkey | Low | S | `InputManager.ts` | Backlog |
| AU14 | Compose an original TradeTown main-menu theme | Low | L | asset licensing | Backlog |
| AU15 | Audio asset pipeline (mirrors `generate-assets.mjs` for sound) | Medium | M | `scripts/` | Backlog |
| AU16 | Dynamic music layering tied to company activity level | Low | L | AU1 | Backlog |
| AU17 | Spatial audio falloff for in-room ambient sources | Low | M | AU1 | Backlog |

## Documentation (17)

| # | Task | Priority | Complexity | Dependencies | Milestone |
|---|---|---|---|---|---|
| D1 | Keep the `docs/` suite in sync with every shipped change | High | S | all docs | ongoing |
| D2 | Add sequence diagrams to `NEXUS_ARCHITECTURE.md` | Low | M | none | Backlog |
| D3 | Write a "first hour" contributor onboarding guide | Medium | M | none | Backlog |
| D4 | Version `docs/API.md` as the schema evolves | Medium | S | ongoing | ongoing |
| D5 | Record short internal dev-reference walkthrough videos per version | Low | M | none | Backlog |
| D6 | Expand the troubleshooting FAQ | Low | S | `DeveloperGuide.md` | Backlog |
| D7 | Formally document Guardian's boundary-enforcement contract | Critical | M | `FUTURE_ARCHITECTURE.md` | v1.0 |
| D8 | Draft a data-retention/privacy policy ahead of any telemetry | Medium | S | new doc | v1.4 |
| D9 | Add a contributor code of conduct | Low | S | new doc | Backlog |
| D10 | Add a glossary cross-reference index across `docs/` | Low | M | none | Backlog |
| D11 | Document Simulation Lab historical-data licensing requirements | High | M | `FUTURE_ARCHITECTURE.md` | v0.6 |
| D12 | Document the Strategy Marketplace sharing-format spec | Medium | M | `FUTURE_ARCHITECTURE.md` | v0.8 |
| D13 | Automate changelog drafting from commit messages | Low | M | `scripts/` | Backlog |
| D14 | Document the mobile/companion API contract ahead of v1.3 | Medium | M | new doc | v1.3 |
| D15 | Re-score `ARCHITECTURE_REVIEW.md` every major version | Medium | S | process | ongoing |
| D16 | Start an architecture decision record (ADR) log for future major choices | Medium | S | none | Backlog |
| D17 | Add per-version doc-diff summaries alongside `CHANGELOG.md` | Low | S | none | Backlog |

## Optimization (17)

| # | Task | Priority | Complexity | Dependencies | Milestone |
|---|---|---|---|---|---|
| O1 | Backend duplicate-logic audit (post-v0.3 follow-up to the RC audit) | Medium | M | backend-wide | Backlog |
| O2 | Frontend duplicate-logic audit | Medium | M | frontend-wide | Backlog |
| O3 | Consolidate `_now_iso()` duplicated across four backend modules | Low | S | new shared util | Backlog |
| O4 | Extract a shared "capped accumulator list" helper (tasks/news/memory each reimplement trimming) | Medium | M | new shared util | Backlog |
| O5 | CI-enforced sync check between `AgentProfiles.ts` and `agents.py` | Medium | M | I4 | Backlog |
| O6 | Audit `EventBus` for event types that have gone unused | Low | S | `EventBus.ts` | Backlog |
| O7 | Bundle-analyze and trim unused Phaser features | Low | M | `vite.config.ts` | Backlog |
| O8 | Replace whiteboard-placement magic numbers with named constants | Low | S | scene files | Backlog |
| O9 | Generate `schedule.py`/`Schedule.ts` from one source instead of hand-mirroring | Medium | L | none | Backlog |
| O10 | Generate `agents.py`/`AgentProfiles.ts` from one source instead of hand-mirroring | Medium | L | none | Backlog |
| O11 | Consistency review of every `MAX_*` cap constant across the backend | Low | S | backend-wide | Backlog |
| O12 | Simplify the camera cover-fit zoom calculation for readability | Low | S | `CameraManager.ts` | Backlog |
| O13 | Break `BrainRoomHud.tsx` into smaller subcomponents | Low | M | `BrainRoomHud.tsx` | Backlog |
| O14 | Audit for unused Tailwind utility classes | Low | S | frontend-wide | Backlog |
| O15 | Dependency audit (unused npm/pip packages) | Low | S | `package.json`, `requirements.txt` | Backlog |
| O16 | Profile and trim `PreloadScene`'s asset-loading order | Low | S | `PreloadScene.ts` | Backlog |
| O17 | Review save-payload size growth over long play sessions | Medium | M | `SaveManager.ts` | Backlog |

---

**Total tracked tasks: 268** (Gameplay 34, UI 28, AI 33, Infrastructure
22, Performance 17, Networking 17, Trading 22, Testing 22, Art 22, Audio
17, Documentation 17, Optimization 17).

This backlog is expected to grow, not shrink to zero — new tasks
discovered during any version's build (bugs found via gameplay testing,
gaps found during a doc-sync pass) should be added here under the
matching category, following the same `Priority | Complexity |
Dependencies | Milestone` shape, rather than tracked only in a commit
message or a chat transcript.
