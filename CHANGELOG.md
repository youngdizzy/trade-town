# Changelog

All notable changes to TradeTown are documented here. Versions are
development milestones, not semver releases.

## Unreleased

### Added

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
