# Changelog

All notable changes to TradeTown are documented here. Versions are
development milestones, not semver releases.

## Unreleased

### Added

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
