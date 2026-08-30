# API

TradeTown's backend exposes three things: a health check, a save/load REST
pair, and a live WebSocket feed. There is no authentication — the app is
single-tenant (one company, one save slot) by design; see
`docs/Architecture.md`. All JSON is camelCase on the wire (Pydantic
`CamelModel` with `populate_by_name=True` — see
`backend/app/schemas.py`), regardless of the snake_case Python field names
used internally.

## `GET /api/health`

Liveness check used by Docker's healthcheck and load balancers.

```json
{ "status": "ok" }
```

## `GET /api/load`

v0.7 Save Architecture Redesign Phase 2 — returns a `GameSaveState`-shaped
object, but only the **core modules** are real (see
`backend/app/save_modules.py` for the module map: `meta`, `settings`,
`world`, `employees`, `company`, `research`, `training`, `founders`,
`derived`). The three **archive modules** — `trade_history` (decisions,
ceoDecisions, tradeProposals, debates, challengeReports,
gatekeeperRejections, executiveMeetingLog), `knowledge_archive` (caseStudies, questionArchive,
reasoningChallenges, reflectionSessions, disciplineReviews, hallOfFame,
memory, meetingMinutes, executiveReviews, talent, departmentSelfEvaluations,
marketIntelligenceReports, marketIntelligenceLearning), and `academy`
(academyProjects, academyCompletedProjects, agentKnowledge) — come back
as real empty arrays/dicts (the same defaults a fresh game legitimately
starts with), not fabricated data and not omitted fields, so the response
stays a structurally valid `GameSaveState` with no optional-field handling
needed client-side. This measurably shrinks the response (~840KB → ~250KB
against a real day-32 dev save) without changing its shape.

The excluded archive data is never actually missing for long: every
Command Center panel that displays it hydrates live from the WebSocket
`"state"` broadcast within moments of connecting anyway (see `WS /ws`
below, unchanged by this redesign) — so nothing is left showing stale or
empty data because of what this endpoint leaves out.

Always succeeds; a fresh deployment just returns sensible defaults (see
`state.default_state()`). See "GameSaveState fields" below for the full
shape.

## `GET /api/load/archive/{module}`

v0.7 Save Architecture Redesign Phase 2 — fetches one archive module's
real data on demand. `module` must be one of `trade_history`,
`knowledge_archive`, `academy` (a `404` otherwise). Returns a plain
alias-keyed (camelCase) object with just that module's fields, e.g.:

```json
{ "decisions": [...], "ceoDecisions": [...], "tradeProposals": [...], "debates": [...], "challengeReports": [...], "gatekeeperRejections": [...] }
```

## `POST /api/save`

v0.7 — Save Architecture Redesign. Body: a `ClientSaveRequest` —
**only** `player`, `settings`, and `dialogueHistory`, not a full
`GameSaveState`. These are the only fields the client has ever actually
owned (see `GameState.apply_client_save()`); every other field
(`agents`/`tasks`/`whiteboards`/`meeting`/`news`/`research`/`watchlist`/
`memory`/`meetingMinutes`/`paperPortfolio`/`strategies`/
`backtestSessions`/`simulationResults`/`hallOfFame`/`coachReports`/
`companyScore`/`performanceSnapshots`/`treasury`/`time`/...) is
server-authoritative, produced continuously by the NEXUS tick loop, and
was previously being sent by the client (as part of the full
`GameSaveState`) only to be silently discarded — a real, measured ~840KB
per autosave that had grown large enough to trip nginx's default 1MB
request-body limit (`413 Request Entity Too Large`) as simulation
history accumulated. `ClientSaveRequest` inherits `CamelModel`'s default
`extra="ignore"`, so an older client still sending a full `GameSaveState`
body remains accepted without error — the extra fields are simply
unused, exactly as they already were.

`settings.operatingMode` (`learning | assisted | executive`, v0.7
Feature 21 — see `app/schemas.py`'s `SettingsState`) is one client-owned
field NEXUS itself reads every tick, to decide whether to auto-resolve
trade proposals (see `nexus._apply_operating_mode()`).
`settings.companyPriority` (`balanced | learning | research |
risk_reduction`, v0.7 Feature 34) is the second — NEXUS reads it every
tick to bias exactly one real, already-existing lever per priority
(Academy knowledge-point awards, research confidence-gain speed, or
tightened trade-sizing risk limits — see `nexus._effective_risk_limits()`
and the comment above `PRIORITY_KNOWLEDGE_MULTIPLIER`); it never mutates
the player's own stored `RiskLimits`. `settings.workMode` (`work | rest`,
v0.7 Feature 37) is the third — NEXUS reads it every tick to pause new
research/Academy progress and new meeting starts while resting, and to
route every agent with no active meeting/break override to a real
off-hours task (see `nexus._rest_block()`); trading/risk systems never
read it at all.

Response:

```json
{
  "ok": true,
  "updatedAt": "2026-01-01T00:00:00.000000+00:00",
  "modules": [
    { "name": "settings", "ok": true, "bytesWritten": 252, "error": null },
    { "name": "world", "ok": true, "bytesWritten": 0, "error": null }
  ]
}
```

`modules` has one entry per module in `backend/app/save_modules.py`'s
module map (see `GET /api/load` above), reflecting what
`persistence.persist_modules()` actually did on the server for this save:

- `bytesWritten: 0` means that module's content was byte-for-byte
  identical to what's already stored (compared via a SHA-256 hash, not a
  full read-back) and was skipped entirely — this is the real "only save
  what changed" mechanism the redesign asked for. Most modules skip most
  saves; only `settings` (player/settings/dialogueHistory, the fields a
  save POST can actually change) reliably writes on every call.
- `ok: false` with a non-null `error` means that one module failed to
  persist — every other module in the same request still committed
  independently (see `persist_modules()`'s docstring for how the
  per-module SAVEPOINT isolation works).

**Client-side behavior (v0.7 Save Architecture Redesign Phase 3, see
`frontend/src/game/systems/SaveManager.ts`):**

- **Coalescing save queue**: `SaveManager.save()` is safe to call while a
  save is already in flight (autosave firing mid-manual-save, or two rapid
  clicks) — a second call sets a flag instead of firing a second request;
  once the in-flight request resolves, one trailing save runs with a
  freshly-built snapshot (never a stale one from when it was queued).
- **Size-guard instead of chunking**: before sending, the client checks
  the payload's real byte size against a 512KB ceiling — far above
  anything `player`/`settings`/`dialogueHistory` can legitimately reach.
  Exceeding it fails immediately with the real byte count in the error,
  rather than attempting a chunked-upload protocol for a payload that's
  supposed to be provably small.
- **Structured error reporting**: a save with any `modules[].ok === false`
  entries surfaces a specific message naming which modules failed and why
  (not a generic "Save Failed"), shown as a toast
  (`CyberNotifications.tsx`) — the one save-related notification the UI
  shows, since a successful save produces no toast (autosave fires every
  30-60s and a toast on every one would just be noise).

## `WS /ws`

On connect, the server immediately sends one `"state"` message with the
current snapshot, then pushes a new one on every simulation tick
(`TICK_INTERVAL_SECONDS`, default 2s — see `backend/app/config.py`). The
client sends nothing; the connection is read-only from the client's
perspective and exists purely to detect disconnects
(`routers/ws.py`).

### `"state"` message shape

```jsonc
{
  "type": "state",
  "time": { "day": 1, "hour": 8, "minute": 0 },
  "agents": {
    "scout": {
      "transform": { "scene": "ScoutOfficeScene", "x": 100, "y": 80, "facing": "down" },
      "location": "scout-office",
      "currentTask": "Scanning market news",
      "mood": 65,
      "energy": 80,
      "memory": [{ "id": "scout-1-8-0", "summary": "Started: Scanning market news", "day": 1, "hour": 8 }],
      "override": null // or { "location": "meeting-room", "reason": "meeting", "remainingMinutes": 20 }
    }
    // ...atlas, echo, nova, scribe, coach, sentinel, pulse, guardian
  },
  "tasks": [
    {
      "id": "task-scout-1-9-0",
      "owner": "scout",
      "category": "news_scan", // research | review | meeting | watchlist_update | news_scan | chart_analysis | documentation | coaching | simulation | paper_trading | analytics | risk_management | market_scanning | voting | trading
      "priority": "normal",    // low | normal | high
      "description": "Scanning market news",
      "status": "working",     // pending | working | completed | failed
      "createdAt": "2026-01-01T09:00:00+00:00",
      "completedAt": null
    }
  ],
  "whiteboards": {
    "scout-office": "Scanning news flow on Apple Inc.\nNormal priority · 42%",
    "meeting-room": "Meeting in progress",
    "ceo-office": "5/5 agents working\nScout wrapped up research on AAPL."
  },
  "meeting": {
    "active": false,
    "participants": [],
    "discussion": [] // [{ "id", "speaker": AgentId, "line", "timestamp" }, ...] while active
  },
  "news": [
    { "id": "news-...", "headline": "...", "category": "company", "timestamp": "..." } // company | discovery | market
  ],
  "research": [
    {
      "id": "research-scout-AAPL-...",
      "title": "Scanning news flow on Apple Inc.",
      "symbol": "AAPL",
      "category": "company", // stock | etf | index | economy | gold | bitcoin | company | sector
      "priority": "normal",
      "status": "in_progress", // queued | in_progress | completed
      "assignedAgent": "scout",
      "summary": "Scout is getting started on Apple Inc.",
      "confidence": 42.5, // 0-100
      "createdAt": "...",
      "updatedAt": "..."
    }
  ],
  "watchlist": [
    {
      "symbol": "AAPL",
      "name": "Apple Inc.",
      "lastPrice": 471.87,
      "dailyChangePct": 0.92,
      "status": "in_progress",
      "researchProgress": 42.5,
      "assignedAgent": "scout"
    }
  ],
  "memory": [
    { "id": "memory-research-...", "category": "research", "title": "...", "body": "...", "timestamp": "..." }
    // categories: research | meeting | whiteboard | event | discussion | discovery | future_trade |
    //             lesson | mistake | strategy | coach_review | simulation | paper_trade |
    //             alert | vote | decision | order
  ],
  "meetingMinutes": [
    {
      "id": "minutes-1-14-0",
      "day": 1, "hour": 14, "minute": 0,
      "participants": ["scout", "echo"],
      "summary": "2 attended: Scout, Echo. Discussed AAPL, MSFT.",
      "discussion": [{ "id", "speaker": "scout", "line": "...", "timestamp": "..." }]
    }
  ],
  "paperPortfolio": {
    "cashBalance": 98815.64,
    "startingBalance": 100000.0,
    "positions": [
      { "id": "pos-...", "symbol": "AAPL", "side": "buy", "quantity": 10.6, "entryPrice": 471.87, "currentPrice": 478.2, "unrealizedPnl": 67.1, "unrealizedPnlPct": 1.3, "openedBy": "scout", "confidence": 88.0, "openedAt": "...", "openedSimMinutes": 1560 }
    ],
    "orders": [
      { "id": "order-...", "symbol": "SPY", "side": "buy", "orderType": "market", "quantity": 9.4, "price": 207.27, "status": "open", "placedBy": "atlas", "reason": "...", "confidence": 92.0, "linkedPositionId": null, "filledPrice": null, "filledAt": null, "createdAt": "..." }
      // orderType: market | limit | stop | take_profit | stop_loss
      // status: open | filled | closed | cancelled
    ],
    "tradeHistory": [
      { "id": "trade-...", "symbol": "DXY", "side": "buy", "quantity": 41.4, "entryPrice": 120.54, "exitPrice": 122.05, "pnl": 55.55, "pnlPct": 1.3, "durationMinutes": 135, "confidence": 100.0, "reason": "...", "marketConditions": "...", "supportingAgents": ["nova"], "opposingAgents": [], "coachReview": "...", "lessonsLearned": "...", "decisionId": "decision-...", "screenshot": "Chart snapshot unavailable — TradeTown has no chart-rendering pipeline.", "openedAt": "...", "closedAt": "..." }
    ],
    "totalPnl": 55.55, "totalPnlPct": 0.06, "winCount": 6, "lossCount": 4
  },
  "strategies": [
    { "id": "strategy-momentum", "name": "Momentum Breakout", "description": "...", "createdBy": "echo", "focusCategory": "stock", "createdAt": "..." }
  ],
  "backtestSessions": [
    { "id": "sim-...", "strategyId": "strategy-momentum", "strategyName": "Momentum Breakout", "symbol": "AAPL", "status": "running", "progress": 42.0, "runBy": "scout", "queuedAt": "...", "startedAt": "..." }
  ],
  "simulationResults": [
    { "id": "result-...", "strategyId": "strategy-value", "strategyName": "Value Fundamentals", "symbol": "MSFT", "totalReturnPct": 28.6, "winRate": 61.0, "maxDrawdownPct": 9.4, "sharpeRatio": 3.04, "sortinoRatio": 3.52, "tradeCount": 34, "runBy": "nova", "completedAt": "..." }
  ],
  "hallOfFame": [
    { "id": "hof-...", "category": "winning_streak", "title": "5-trade winning streak", "description": "...", "agentId": null, "value": 5.0, "achievedAt": "..." }
  ],
  "coachReports": [
    {
      "id": "report-...", "period": "weekly", "companyScore": 66.2,
      "agentRankings": [{ "agentId": "nova", "score": 78.5, "researchAccuracy": 82.0, "confidenceCalibration": 74.0 }],
      "researchAccuracy": 71.0, "winRate": 60.0, "lossRate": 40.0, "averageConfidence": 68.5, "riskScore": 82.0,
      "commonMistakes": ["Held past the profit target on 2 trades"],
      "recommendations": ["Tighten exit discipline on momentum trades"],
      "createdAt": "..."
    }
  ],
  "companyScore": {
    "overall": 66.2, "researchQuality": 71.0, "decisionQuality": 60.0, "riskManagement": 82.0,
    "paperTradingPerformance": 52.0, "teamCoordination": 74.0, "knowledgeGrowth": 24.0, "simulationSuccess": 58.0,
    "updatedAt": "..."
  },
  "companyHealth": {
    // v0.7 Feature 23 — a second, deliberately independent scorecard from
    // companyScore above: same "no hidden weighting, plain mean" philosophy
    // (see app/company_health.py), but asking "is the company stable and
    // well-run?" rather than "is it winning?" Some underlying signals
    // overlap on purpose (e.g. employeeMorale and companyScore's
    // teamCoordination both read real agent mood) — they're computed
    // independently and answer different questions.
    "overall": 71.4, "tier": "good", // excellent | good | stable | needs_attention | critical
    "operationalStability": 88.0, "departmentEfficiency": 66.7, "employeeMorale": 74.0,
    "researchProgress": 60.0, "capitalHealth": 58.4, "resourceUsage": 82.0,
    "reputation": 20.0, "technologyLevel": 40.0, "marketCoverage": 25.0, "educationProgress": 15.0,
    // v0.7 Feature 43 — real support-vs-challenge ratio across the most
    // recent 20 AI Debates (app/company_health.py's _team_chemistry).
    "teamChemistry": 62.5,
    "recommendations": ["Reputation is low (20/100) — worth attention."],
    "updatedAt": "...",
    // v0.7 Feature 50 (Part 2/3) — the Company Health redesign. Eleven
    // more real Executive-tier dimensions, additive alongside the
    // eleven Operational ones above (never replacing them — see
    // app/company_health.py's module docstring). recommendations above
    // now also includes the weakest of these when below 70.
    // complianceHealth (CEO directive "Features 31-35," Feature 35) is
    // the newest — see this doc's Continuous Compliance Improvement
    // Loop section above.
    "decisionQuality": 82.4, "executiveAlignment": 66.7, "riskGovernance": 100.0,
    "simulationCoverage": 50.0, "departmentConsensus": 75.0, "selfEvaluationHealth": 68.1,
    "institutionalMemory": 71.2, "innovationVelocity": 20.0, "talentDevelopment": 12.5,
    "founderOversight": 40.0, "complianceHealth": 50.0,
    "executiveOverall": 58.7, "executiveTier": "stable",
    // The true redesigned headline number — an equal blend of `overall`
    // and `executiveOverall`, so neither tier silently outweighs the other.
    "combinedOverall": 65.1, "combinedTier": "stable"
  },
  "companyDna": {
    // v0.7 Feature 43 — app/company_dna.py. Five real, descriptive
    // behavioral traits read off the company's own historical decision/
    // trade record; each defaults to a neutral 50.0 with sampleSize 0
    // until there's enough real history to say anything real.
    "traits": [
      { "id": "risk_appetite", "name": "Risk Appetite", "score": 40.0, "detail": "2 of 5 executed trade(s) were taken on a moderate-or-weaker confidence reading." },
      { "id": "patience", "name": "Patience", "score": 75.0, "detail": "Average real hold time is 180 simulated minutes, against the Discipline Chamber's 240-minute patient-hold bar." },
      { "id": "contrarian_tendency", "name": "Contrarian Tendency", "score": 20.0, "detail": "The CEO overrode the AI's own recommendation on 1 of 5 resolved decision(s)." },
      { "id": "research_rigor", "name": "Research Rigor", "score": 78.0, "detail": "Average Decision Confidence Engine score across 5 decision(s): 78/100." },
      { "id": "collaboration_style", "name": "Collaboration Style", "score": 60.0, "detail": "3 of 5 decision(s) had at least two distinct real analyst positions on the table." }
    ],
    "summary": "This company's real track record reads highest on Research Rigor (78/100) and lowest on Contrarian Tendency (20/100).",
    // v0.7 Feature 48 — a pure, deterministic label read off the traits
    // above (app/company_dna.py's classify_identity()). "Not Yet
    // Established" until sampleSize is real.
    "identity": "Research Driven",
    "sampleSize": 5, "updatedAt": "..."
  },
  "dailyObjectiveStatus": {
    // v0.7 Feature 49 — a real-time readout of today's real trading
    // activity against riskLimits above, computed fresh every tick
    // (app/risk_engine.py's compute_daily_objective_status()). Reports
    // the same halt condition evaluate_sentinel_risk actually enforces
    // via the Gatekeeper — see "Daily Trading Objectives" below.
    "simDay": 4, "tradesToday": 2, "realizedPnlPctToday": 1.4,
    "profitTargetReached": false, "maxLossReached": false, "maxTradesReached": false,
    "tradingHalted": false, "haltReason": null, "updatedAt": "..."
  },
  "marketEnvironment": {
    // v0.7 Feature 22 — a 5-way regime classification computed every tick
    // from the real, already-fetched watchlist.dailyChangePct values (see
    // app/market_environment.py). "timeline" only grows on a real regime
    // change, not every tick.
    "current": "bull", "label": "BULL MARKET", // bull | bear | sideways | high_volatility | low_volatility
    "detail": "Aggregated over 8 tracked symbols — avg move +1.84%, avg |move| 2.10%.",
    "changedSimMinutes": 1560, "updatedAt": "...",
    "timeline": [
      { "id": "env-bull-1560", "regime": "bull", "label": "BULL MARKET", "detail": "...", "simMinutes": 1560, "createdAt": "..." }
    ]
  },
  "marketIntelligence": {
    // v0.7 Feature 51 — the Market Intelligence Department's always-current
    // "eyes," recomputed every tick from real (mock) OHLCV candle data
    // and real wall-clock time (app/market_intelligence.py). This is what
    // every new TradeProposal and the Trade Gatekeeper actually read —
    // never the once-daily report below, which can be up to a day stale.
    // See that module's own docstring for the full honesty boundary:
    // real technical analysis over real synthesized price data, named
    // proxies (institutionalActivity, newsRisk, the accumulation/
    // distribution regimes) where this codebase has no real order-flow/
    // economic-calendar source, nothing fabricated.
    "regime": "sideways_range", "regimeLabel": "Sideways Range", "regimeDetail": "...",
    "quality": { "tier": "good", "score": 78.8, "confidencePct": 88.0, "reasoning": "...", "evidence": ["..."], "historicalSimilarity": "This regime has occurred on 2 of the last 5 real recorded day(s)." },
    "volatility": { "currentPct": 1.2, "historicalAvgPct": 1.2, "sessionPct": 1.2, "percentile": 49.7, "expectedPct": 1.2, "detail": "..." },
    "session": { "current": "new_york", "label": "New York Session", "overlapsActive": [], "detail": "..." },
    "momentum": { "rocPct": 0.2, "strength": "decelerating", "detail": "..." },
    "institutionalActivity": { "volumePriceDivergenceScore": 18.0, "absorptionDetected": true, "symbolsFlagged": ["QQQ"], "detail": "..." },
    "newsRisk": { "activeMarketNewsCount": 0, "riskLevel": "low", "detail": "..." },
    "liquidity": [{ "symbol": "AAPL", "zones": [], "sweepDetected": false, "sweepDirection": "none", "liquidityScore": 0.0, "detail": "..." }],
    "structure": [{ "symbol": "AAPL", "swingHighs": [], "swingLows": [], "lastBreakOfStructure": "none", "structureState": "consolidation", "detail": "..." }],
    "updatedAt": "..."
  },
  "executiveReviews": [
    // v0.7 Feature 24 — the CIO's Monthly Executive Review
    // (app/executive_review.py). A fresh cumulative snapshot over each
    // already-capped recent-history list (research/decisions/debates/
    // news), same convention CoachReport already uses.
    // companyScoreChange is the one true period-over-period figure — a
    // real delta against the previous review's own stored score (0.0
    // for the first review).
    {
      "id": "review-30-20-0", "companyScore": 65.0, "companyScoreChange": 3.2, "companyHealthTier": "stable",
      "departmentActivity": [{ "agentId": "scout", "researchCompleted": 24, "decisionsInvolved": 45 }],
      "researchCompleted": 96, "knowledgeGained": 50, "lessonsCompleted": 4,
      "majorEvents": ["Atlas completed research on SPY: ..."],
      "conflictsDetected": 12,
      "flags": ["Nova's research on SPY remains low-confidence — may need a fresh angle."],
      "recommendations": ["Technology Level is low (0/100) — worth attention."],
      "longTermGoals": ["Hold max drawdown under 20%, the standing risk limit."],
      // v0.7 Feature 25.5 — real "this builds on that" callbacks, one per
      // research category / Academy topic with 2+ completed items, naming
      // the two real titles involved (app/executive_review.py's
      // _knowledge_connections). Empty when nothing yet has a real
      // predecessor to reference.
      "knowledgeConnections": ["This period's \"Reviewing MSFT momentum\" builds on earlier stock research, \"Studying AAPL trends\"."],
      "summary": "Company score stands at 65/100 (+3.2 since the last review)...",
      "createdAt": "..."
    }
  ],
  "academyProjects": [
    // v0.7 Feature 25 — the Academy's one active, company-wide knowledge
    // project (app/academy_research.py) — not one per agent, unlike
    // market research.py's queue. Cycles through a fixed six-topic
    // catalog and every non-CIO agent.
    { "id": "academy-market_history-...", "topic": "market_history", "title": "Studying the 1987 Crash and Black Monday",
      "assignedAgent": "scout", "status": "in_progress", "progress": 42.0,
      "summary": "Scout is getting started: a study of historical market panics and what triggered them.",
      "createdAt": "...", "updatedAt": "..." }
  ],
  "academyCompletedProjects": [
    // The permanent Company Knowledge Library — capped at
    // MAX_ACADEMY_LIBRARY (50), same shape as academyProjects above but status:"completed".
  ],
  "agentKnowledge": {
    // v0.7 Features 25/31 — every agent's own real Knowledge Points/tier
    // (app/academy.py). "branch" is a fixed, occupation-linked theme;
    // points only ever grow from real completed work (a finished
    // ResearchItem, a finished AcademyProject, real meeting attendance).
    // "tier" (0-6) and "level" are the same real number, two views:
    // level is tier's real Novice-through-Mentor name (v0.7 Feature 31).
    "echo": { "agentId": "echo", "branch": "Technical Analysis", "points": 18.5, "tier": 2, "level": "intermediate" }
  },
  "academyState": {
    // Company-wide progression derived from agentKnowledge + real
    // completed-project count — level/label only, no new art per level
    // (see docs/Architecture.md's scope-cut note).
    "level": 3, "levelLabel": "Innovation Lab", "totalPoints": 142.0, "completedProjectCount": 18, "updatedAt": "..."
  },
  "disciplineReviews": [
    // v0.7 Feature 26 — one DisciplineReview per closed paper trade
    // (app/discipline.py). `score`/`factors` never depend on `outcome`/
    // `tradePnlPct` — see the module docstring for how that's enforced
    // structurally, not just by convention.
    {
      "id": "discipline-trade-...", "decisionId": "decision-proposal-...", "symbol": "AAPL",
      "score": 84.0, "tier": "exemplary",
      "factors": [
        { "id": "research_depth", "name": "Research Depth", "score": 90.0, "weight": 0.20, "detail": "..." }
        // ... viewpoint_diversity, uncertainty_acknowledged, cross_examination, assumptions_challenged, position_sizing_discipline, patience
      ],
      "attendees": ["echo", "scout", "sentinel"],
      "summary": "Exemplary discipline (84/100) — the process was sound and the trade won (+3.5%): good decision, good outcome, aligned.",
      "postDecisionReview": {
        "whatWeDidWell": ["Research Depth: ..."], "mistakesMade": [], "informationOverlooked": [],
        "assumptionsIncorrect": [], "whatToRepeat": ["Research Depth"], "whatToNeverRepeat": [], "howToImprove": ["Raise Patience — ..."]
      },
      "outcome": "win", "tradePnlPct": 3.5, "holdDurationMinutes": 240, "simDay": 12, "createdAt": "..."
    }
  ],
  "caseStudies": [
    // v0.7 Feature 27 — filed for a real, specific process gap behind
    // an actual loss (app/mistakes.py, 6 categories) OR (v0.7 Feature 42)
    // a real process strength behind an actual win (app/successes.py,
    // 3 categories: disciplined_process/rigorous_cross_examination/
    // patient_execution) — both share this one schema/list rather than
    // duplicating it. See each module's docstring for exactly which real
    // signal backs each category.
    {
      "id": "case-trade-...-overconfidence", "category": "overconfidence", "title": "The Cost of Overconfidence", "symbol": "MSFT",
      "decisionId": "decision-proposal-...",
      "timeline": [{ "label": "Decision made", "timestamp": "..." }, { "label": "Position opened", "timestamp": "..." }, { "label": "Position closed", "timestamp": "..." }],
      "background": "...", "decisionProcess": "...",
      "departmentOpinions": ["Echo: ...", "Scout: ..."],
      "missedInformation": "...", "lessonsLearned": "...", "recommendedImprovements": "...",
      "relatedPrinciples": ["Decision Confidence must clear 55/100 before the Trade Gatekeeper approves a trade.", "..."],
      "tradePnlPct": -2.2, "simDay": 12, "createdAt": "..."
    }
  ],
  "reasoningChallenges": [
    // v0.7 Feature 29 — filed periodically from the company's most recent
    // real AI Debate + its linked TradeDecision (app/reasoning_lab.py).
    // No pnl or outcome is ever read here — see the module docstring for
    // exactly which real signal backs each of the seven categories.
    {
      "id": "reasoning-debate-...", "category": "evaluating_multiple_hypotheses", "title": "Evaluating Multiple Hypotheses", "symbol": "BTC-USD",
      "decisionId": "decision-proposal-...",
      "contributions": [
        { "agentId": "echo", "role": "technical", "stance": "opening", "contribution": "..." }
        // ... one entry per real Debate turn (opening/challenge/support)
      ],
      "solution": {
        "whatWeKnow": ["Multi-Agent Agreement: 5/6 analysts agree with BUY."],
        "whatWeDoNotKnow": [], "assumptions": ["..."],
        "whyReasonable": "...", "confidence": 85.5,
        "whatCouldChangeOurConclusion": "A material change in ... is the most likely thing to overturn this conclusion."
      },
      "reasoningLevel": 2, "simDay": 12, "createdAt": "..."
    }
  ],
  "reasoningLabState": {
    // Company-wide progression derived from the real completed-challenge
    // count — mirrors academyState's level/label-only convention exactly.
    "level": 2, "levelLabel": "Applied Reasoning", "completedChallengeCount": 7, "updatedAt": "..."
  },
  "reflectionSessions": [
    // v0.7 Feature 30 — one real ReflectionSession every in-game week and
    // month (app/wisdom.py). Every field is built from data already
    // computed elsewhere; wisdomScore is a snapshot of the company-wide
    // score at the moment this session closed, never re-derived from pnl.
    {
      "id": "reflection-weekly-7-20-0", "cadence": "weekly",
      "attendees": ["scout", "atlas", "echo", "nova", "scribe", "coach", "sentinel", "pulse", "guardian", "cio"],
      "questions": [
        { "question": "What surprised us?", "answer": "..." }
        // ... all nine of the brief's reflection questions, each a real answer
      ],
      "insights": [
        { "agentId": "nova", "insight": "..." }
        // ... real recent output from real agents, one per real source available
      ],
      "keyDiscoveries": ["..."], "lessonsLearned": ["..."],
      "importantQuestions": ["..."], "recommendedFutureProjects": ["..."],
      "wisdomScore": 71.2, "simDay": 7, "createdAt": "..."
    }
  ],
  "wisdomState": {
    // Never profit-based — a plain, unweighted mean of eight real factors
    // (see app/wisdom.py's module docstring). Recomputed only when a
    // ReflectionSession is generated, not every tick.
    "score": 71.2, "tier": "seasoned_wisdom", "tierLabel": "Seasoned Wisdom",
    "factors": [
      { "id": "learn_from_experience", "name": "Learning From Experience", "score": 50.8, "weight": 0.125, "detail": "..." }
      // ... all eight factors: share_knowledge, follow_principles, improve_communication,
      // document_lessons, avoid_repeating_mistakes, complete_research, support_collaboration
    ],
    "updatedAt": "..."
  },
  "questionArchive": [
    // v0.7 Feature 32 — one QuestionOfTheDay every in-game morning at
    // 8:00 (app/mentor.py), drawn deterministically from a small
    // hand-authored library (real curated content — no free-form
    // question generation exists in this codebase). relatedReference is
    // at most one honest pointer into already-existing real company
    // content sharing the question's category; null when nothing real
    // exists yet to point to. playerResponse/playerRespondedAt are set
    // via POST /api/mentor/qotd/respond below and never graded.
    {
      "id": "qotd-7", "category": "risk_awareness",
      "question": "What's the one thing that would hurt us most if we're wrong?",
      "relatedReference": "Sentinel flagged this recently: AAPL is 34.2% of the portfolio — above the 30% concentration limit.",
      "playerResponse": null, "playerRespondedAt": null,
      "simDay": 7, "createdAt": "..."
    }
  ],
  "thinkingProfiles": {
    // v0.7 Feature 32 — every real agent's purely-computed Thinking
    // Profile (app/mentor.py). Recomputed every tick like agentKnowledge
    // above; each trait reuses a distinct existing real signal — see the
    // module docstring for why "Patience" (Discipline Review's own
    // factor) and the brief's "Communication"/"Adaptability" (no real
    // per-agent signal exists) aren't traits here.
    "sage": {
      "agentId": "sage",
      "traits": [
        { "id": "curiosity", "name": "Curiosity", "score": 28.0, "detail": "8.4 Academy knowledge points earned in Critical Thinking." },
        { "id": "evidence_quality", "name": "Evidence Quality", "score": 50.0, "detail": "No Discipline Reviews attended yet — starts at a neutral baseline." }
        // ... open_mindedness, humility, reasoning, collaboration
      ],
      "updatedAt": "..."
    }
  },
  "mentorState": {
    // Company-wide progression derived from the real archive length —
    // mirrors reasoningLabState's level/label-only convention.
    "tier": 1, "tierLabel": "Taking Root", "questionsAsked": 9, "updatedAt": "..."
  },
  "foundationalMentorState": {
    // v0.7 Feature 49 (Phase 3, revised) — the Foundational Mentor
    // Program / Professional Academy. Real mutated progress, unlike
    // mentorState above — see docs/Architecture.md's "Professional
    // Academy — Feature 49 Revision" section. `progress` is now keyed
    // per real employee student (STUDENT_AGENT_IDS), then per mentor;
    // `ceoProgress` is the CEO's own entirely separate, optional bucket.
    "mentors": [
      { "id": "tjr", "name": "TJR", "trackLabel": "TJR Track", "focusAreas": ["Trading Psychology", "Discipline", "Daily Routine", "Liquidity", "Market Structure", "Patience", "Risk Management", "Journaling", "Trade Planning", "High Quality Trade Selection"],
        "contentNote": "This track's name credits a real, respected trading educator...", "status": "active", "companyGraduatedSimDay": null,
        "lessons": [ { "id": "tjr-psychology", "order": 1, "title": "Trading Psychology: Process Over Outcome", "simpleExplanation": "...", "deeperExplanation": "...", "quizQuestion": "...", "quizOptions": ["...", "...", "...", "..."] } ],
        "resources": [] }
      // ... al_brooks, linda_raschke, mark_douglas, tom_hougaard, mike_bellafiore — all "status": "planned", "lessons": []
    ],
    "progress": {
      "scout": { "tjr": { "mentorId": "tjr", "viewedLessonIds": ["tjr-psychology"], "completedLessonIds": [], "currentLessonStudyPct": 26.9, "quizAttempts": 0, "correctQuizAttempts": 0, "consecutiveQuizFailures": 0, "graduationStatus": "in_progress", "graduatedSimDay": null } }
      // ... atlas, echo, nova, scribe, sentinel, pulse, guardian — the real 8-agent student roster, never coach/sage/cio/quant
    },
    "ceoProgress": {},
    "activeMentorId": "tjr", "updatedAt": "..."
  },
  "performanceSnapshots": [
    { "period": "daily", "returnPct": 1.2, "winRate": 60.0, "maxDrawdownPct": 4.1, "sharpeRatio": 0.29, "sortinoRatio": 0.34, "avgHoldingMinutes": 210.0, "researchAccuracy": 71.0, "confidenceAccuracy": 68.0, "computedAt": "..." }
  ],
  "riskLimits": {
    "maxPositionPct": 10.0, "maxDailyLossPct": 5.0, "maxDrawdownPct": 20.0,
    "maxOpenPositions": 8, "maxSectorConcentrationPct": 30.0, "riskPerTradePct": 2.0,
    // v0.7 Feature 49 — Daily Trading Objectives. maxDailyLossPct above
    // already existed but was never enforced before this feature; both
    // of these are new. CEO-configurable via POST /api/risk-limits (see
    // "Daily Trading Objectives" below) — the first real write path
    // RiskLimits has ever had.
    "dailyProfitTargetPct": 3.0, "maxTradesPerDay": 6,
    // Design Bible Chapter 67 (TTOS) Safety Settings — the second and
    // third real circuit breakers, enforced the same way as
    // maxDailyLossPct above (app/risk_engine.py's evaluate_sentinel_risk),
    // just scoped to the current sim week/month. Defaults sit between
    // the daily (5%) and lifetime drawdown (20%) limits.
    "maxWeeklyLossPct": 10.0, "maxMonthlyLossPct": 15.0,
    // v0.7 Chapter 57 — Institutional Position Sizing & Capital
    // Deployment Engine (backend/app/position_sizing.py). All six new
    // real inputs that engine reads. portfolioHeatCapPct null = no hard
    // cap (today's behavior unchanged — Portfolio Heat stays a pure
    // reading). scalingAggressivenessPct/emergencyReductionHeatPct are
    // stored but have no real consumer yet — Position Scaling/Reduction
    // on already-open positions isn't built (see the engine's own
    // honesty boundary) — so they're deliberately not exposed as a CEO
    // control in the Command Center yet, only readable/writable via this
    // endpoint for forward compatibility.
    "maxWeeklyDeploymentPct": 15.0, "portfolioHeatCapPct": null,
    "cashReservePct": 10.0,
    "tierAllocation": { "tier1Pct": 2.0, "tier2Pct": 5.0, "tier3Pct": 8.0, "tier4Pct": 10.0 },
    "scalingAggressivenessPct": 100.0, "emergencyReductionHeatPct": 75.0,
    // v0.7 Chapter 58 — Institutional Trade Filter & Opportunity
    // Gatekeeper (backend/app/opportunity_gatekeeper.py). Two new real
    // CEO controls that engine reads. minTradeQualityScore's default
    // (70.0) matches war_room.py's own fixed DECISION_SCORE_THRESHOLD
    // value, but is a genuinely separate, independently-adjustable
    // field — changing one never changes the other.
    "minTradeQualityScore": 70.0, "minExpectedValuePct": 0.0
  },
  "riskWarnings": [
    // Guardian's *current* standing watch — refreshed every tick from
    // scratch (see risk_engine.monitor_portfolio()), not an accumulating
    // log. Empty when the portfolio is within all configured limits.
    { "id": "guardian-concentration-AAPL-...", "symbol": "AAPL", "severity": "warning", "message": "AAPL is 34.2% of the portfolio — above the 30% concentration limit.", "createdAt": "..." }
    // severity: info | warning | critical
  ],
  "scannerAlerts": [
    { "id": "alert-BTC-USD-volume_spike-...", "symbol": "BTC-USD", "alertType": "volume_spike", "message": "BTC-USD volume spiked well above its normal range with no clear price move yet.", "detectedBy": "pulse", "createdAt": "..." }
    // alertType: gap_up | gap_down | breakout | volume_spike | high_volatility
  ],
  "decisions": [
    {
      "id": "decision-research-echo-AAPL-...", "symbol": "AAPL", "outcome": "trade", // trade | no_trade
      "votes": [
        { "agentId": "scout", "choice": "sell", "reason": "..." },
        { "agentId": "sentinel", "choice": "buy", "reason": "AAPL is within configured risk limits." }
        // choice: buy | sell | hold | risk_too_high | position_too_large
      ],
      "researchSummary": "...", "technicalSummary": "...", "fundamentalSummary": "...", "riskSummary": "...",
      "supportingAgents": ["atlas", "echo", "nova"], "opposingAgents": ["scout"],
      "confidence": 100.0, "finalReasoning": "3 of 5 votes in favor — Atlas approves the trade on AAPL.",
      "orderId": "order-research-echo-AAPL-...", "createdAt": "...",
      // v0.7 Feature 20 — set only when the CEO chose buy/sell (a WAIT
      // never reaches the gatekeeper); null for decisions predating this
      // field. A rejected verdict here is exactly what makes `orderId`
      // null even though the linked CeoDecisionRecord's `ceoDecision`
      // was buy/sell, not wait.
      "gatekeeperVerdict": null
    }
  ],
  "tradeProposals": [
    // v0.6.3 Feature 12 — a research candidate crossing the trade-
    // confidence threshold no longer executes automatically; it becomes
    // a proposal awaiting the CEO's (the player's) own decision. Resolved
    // via POST /api/executive/decide. Capped at MAX_PENDING_PROPOSALS (5)
    // and auto-expires after 3 in-game days unactioned (resolved as WAIT).
    {
      "id": "proposal-research-echo-AAPL-...", "symbol": "AAPL", "category": "stock",
      "quantity": 10.6, "price": 471.87, "confidence": 92.0,
      "analystVotes": [
        { "role": "technical", "agentId": "echo", "choice": "buy", "reasoning": "AAPL is in a real uptrend (+4.2% over the sample) relative to its own volatility.", "evidence": ["Trend: +4.2% over the last 30 1h bars.", "Volatility: 1.1% average bar range."] }
        // role: technical | news | macro | risk | sentiment | execution
        // choice: buy | sell | wait
      ],
      "overallRecommendation": "buy", "researchSummary": "...", "riskSummary": "...",
      // v0.7 Feature 51 — a real one-line citation of the Market
      // Intelligence Department's regime/quality read at the moment this
      // proposal was generated (app/market_intelligence.py). null only
      // for proposals that predate this feature.
      "marketIntelligenceSummary": "Weak Uptrend — Market Quality good (79/100, 88% confidence).",
      "createdAt": "...", "createdSimMinutes": 1560
    }
  ],
  "ceoDecisions": [
    // The permanent record of one CEO decision. `outcome` only ever
    // resolves to correct/incorrect once a real trade the CEO's own
    // choice caused has closed; a plain WAIT or any override (ceoDecision
    // != aiRecommendation) stays "undecidable" — an override's real trade
    // tells us whether the CEO's own call worked, never whether the AI's
    // original (never-taken) direction would have.
    {
      "id": "ceo-proposal-research-echo-AAPL-...", "proposalId": "proposal-research-echo-AAPL-...",
      "symbol": "AAPL", "category": "stock", "aiRecommendation": "buy", "ceoDecision": "buy",
      "agreedWithAi": true, "decisionId": "decision-proposal-research-echo-AAPL-...",
      "outcome": "pending", // pending | correct | incorrect | undecidable
      // v0.7 Feature 21 — "ceo" is a real player click; "auto" is a
      // Company Operating Mode (Assisted/Executive) auto-resolution or a
      // stale-proposal expiry, never presented as a real player decision.
      // Defaults to "ceo" for records predating this field.
      "resolvedBy": "ceo", // ceo | auto
      "createdAt": "...", "resolvedAt": null
    }
  ],
  "debates": [
    // v0.7 Feature 17 — one Debate generated automatically the moment its
    // TradeProposal is created (see nexus.py), plus one more per
    // POST /api/executive/debate/regenerate call for the same proposal
    // (appended, not replacing — every debate stays reviewable). Every
    // turn's text is a real AnalystVote's own reasoning; only the
    // opening/challenge/support framing is generated.
    {
      "id": "debate-proposal-research-echo-AAPL-...-1234567890-4821", "proposalId": "proposal-research-echo-AAPL-...",
      "symbol": "AAPL",
      "turns": [
        { "agentId": "echo", "role": "technical", "stance": "opening", "respondingTo": null, "text": "AAPL is in a real uptrend (+4.2% over the sample) relative to its own volatility. (Trend: +4.2% over the last 30 1h bars.; Volatility: 1.1% average bar range.)" },
        { "agentId": "sentinel", "role": "risk", "stance": "challenge", "respondingTo": "scout", "text": "Not so fast — the News Analyst may be missing something: AAPL is within all configured risk limits." }
        // stance: opening | challenge | support
      ],
      "finalRecommendation": "buy",
      "finalSummary": "After 6 independent reads, the desk recommends BUY on AAPL. Strong Setup (88/100) — strongest: Multi-Agent Agreement (100), weakest: Portfolio Exposure (60).",
      "createdAt": "..."
    }
  ],
  "gatekeeperRejections": [
    // v0.7 Feature 20 — every trade the Trade Gatekeeper vetoed after the
    // CEO chose buy/sell (see app/gatekeeper.py). No order was ever
    // placed, so `outcome` starts "pending" and only resolves once
    // GATEKEEPER_EVAL_WINDOW_MINUTES (4 simulated hours) have passed,
    // purely from the symbol's own real subsequent watchlist price move
    // — never a fabricated P&L. v0.7 Feature 51 added an 8th real check
    // ("market_intelligence"): a trade cannot pass while the Market
    // Intelligence Department's real, current Market Quality Score reads
    // "avoid_trading" — the same mechanical enforcement of the brief's
    // "no trade without explaining the current market environment" rule.
    {
      "id": "gkreject-decision-proposal-research-echo-AAPL-...", "proposalId": "proposal-research-echo-AAPL-...",
      "symbol": "AAPL", "ceoChoice": "buy",
      "reasons": ["Decision Confidence: 42/100 — below the required 55 minimum."],
      "priceAtRejection": 471.87, "rejectedSimMinutes": 1560,
      "outcome": "pending", // pending | would_have_won | would_have_lost
      "resolvedPriceChangePct": null, "createdAt": "...", "resolvedAt": null
    }
  ],
  "opportunityRejections": [
    // v0.7 Chapter 58 — every candidate the Opportunity Gatekeeper
    // rejected BEFORE it ever became a real TradeProposal (see
    // app/opportunity_gatekeeper.py) — a distinct, EARLIER-stage
    // sibling to gatekeeperRejections above, not a replacement for it.
    // No CEO ever saw this candidate, so there is no ceoChoice —
    // wouldHaveRecommended is the six-agent desk's own
    // overallRecommendation instead. Graded the same honest way, except
    // a "wait" recommendation has no real direction to grade against
    // and stays "pending" forever.
    {
      "id": "oppreject-proposal-research-echo-QQQ-...", "symbol": "QQQ",
      "wouldHaveRecommended": "buy",
      "reasons": ["Expected Value -1.27% is below the required +0.00% minimum.", "Trade Quality Score 60/100 is below the required 70 minimum."],
      "decisionScoreAtRejection": 59.7, "expectedValueAtRejectionPct": -1.27,
      "priceAtRejection": 240.19, "rejectedSimMinutes": 2025,
      "outcome": "pending", // pending | would_have_won | would_have_lost
      "resolvedPriceChangePct": null, "createdAt": "...", "resolvedAt": null
    }
  ]
}
```

### `POST /api/executive/decide`

Feature 12 — the CEO's real buy/sell/wait call on a pending
`TradeProposal`. Body: `{ "proposalId": "...", "choice": "buy" }`
(`choice`: `buy` | `sell` | `wait`). A buy/sell still passes through the
v0.7 Feature 20 Trade Gatekeeper before it executes (see
`app/gatekeeper.py`) — a rejected verdict lands on the returned
decision's `gatekeeperVerdict` and a new entry appears in
`gatekeeperRejections`, while `orderId` stays null and no position
opens. Returns the updated `tradeProposals`, `ceoDecisions`,
`decisions`, `paperPortfolio`, and `gatekeeperRejections`. `400` if the
proposal id isn't found (already resolved or expired), or if
`strategyId` (below) doesn't match a real strategy.

CEO directive "Live Trade → Strategy Provenance" — the body may also
carry an optional real `strategyId`: `{ "proposalId": "...", "choice":
"buy", "strategyId": "50-ema-breakout-pullback-long" }`. The one real,
non-fabricated way a live trade can be linked back to a Strategy Lab
strategy — validated against the real strategy roster and stored on the
resulting `CeoDecisionRecord.strategyId` only for `buy`/`sell` (ignored
on `wait`, since no trade exists to attribute). See
`TradeAttributionRecord.strategyProvenanceState`/`TradeReportCard.
strategyProvenanceState` for how this reads back downstream.

### `POST /api/executive/debate/regenerate`

v0.7 Feature 17 — "request another debate" on a still-pending proposal.
Body: `{ "proposalId": "..." }`. Returns the updated `debates` list (the
new one appended). `400` if the proposal id isn't found.

### `GET /api/executive/whatif?symbol=AAPL`

v0.7 Feature 16 — the What-If Simulation Lab. Read-only, stateless, and
computed fresh on every call (never part of `GameSaveState`/the WS
broadcast — see `app/whatif.py`'s module docstring for why). Returns a
`WhatIfSimulation`:

```json
{
  "symbol": "AAPL", "holdBars": 20,
  "scenarios": [
    {
      "scenarioType": "bullish_continuation", // one of 12 — see whatif.py's ScenarioType
      "label": "Strong Bullish Continuation",
      "rewardRangeLowPct": 0.3, "rewardRangeHighPct": 21.0, "mostLikelyPct": 13.4,
      "typicalDrawdownPct": -5.5, "maxRiskPct": -17.2, "probabilityOfProfitPct": 90.0,
      "invalidation": "A close back below the sample's starting price invalidates this thesis."
    }
    // ... 11 more scenarios
  ],
  "baseline": { "scenarioType": "bullish_continuation", "label": "Baseline (No Scenario Bias)", "...": "same shape as above, no scenario bias applied" },
  "bestCaseScenario": "breakout_confirmation", "worstCaseScenario": "high_volatility"
}
```

`400` for an unsupported timeframe (shouldn't happen — this endpoint
always requests the same `PROPOSAL_TIMEFRAME`/`PROPOSAL_CANDLE_COUNT`
the technical analyst vote itself uses, so both readings stay grounded
in the same real candle sample).

### `GET /api/executive/intelligence?proposalId=...`

v0.7 Feature 50 — the Executive Intelligence Network's live, per-proposal
synthesis panel. Read-only,
stateless, and computed fresh on every call (see
`app/executive_intelligence.py`'s module docstring for why: every input
already lives somewhere permanent — the proposal, its `ChallengeReport`
if one exists, the latest `CoachReport` — so this is a synthesis, not a
second source of truth). Returns an `ExecutiveRecommendation`:

```json
{
  "proposalId": "proposal-42",
  "action": "trade_normally", // one of: trade_normally | reduce_risk | wait | research_more | pause_trading | focus_on_simulation
  "confidencePct": 78.5,
  "reason": "No department raised a real concern serious enough to change course.",
  "supporting": ["research", "quant", "decision_intelligence"],
  "opposing": [],
  "opinions": [
    {
      "role": "simulation", // one of the 8 departments — see the table in docs/Architecture.md's Feature 50 section
      "departmentLabel": "Simulation",
      "agentId": "atlas",
      "stance": "agree", // agree | disagree | request_more_research | recommend_waiting | recommend_position_change | recommend_rejecting
      "summary": "Worst case simulated: Flash crash wipes out 8% in one bar.",
      "confidencePct": 80.0
    }
    // ... 7 more, one per department
  ],
  "generatedAt": "2026-07-30T12:00:00Z"
}
```

`404` if `proposalId` doesn't match a currently-pending `TradeProposal`
(already resolved or never existed). Every department opinion is a real
read off an existing system (see the mapping table in
`docs/Architecture.md`) — Simulation and Devil's Advocate honestly report
"not yet stress-tested"/"not yet challenged" when no `ChallengeReport`
exists for the proposal yet, rather than fabricating one.

### `GET /api/executive/confluence?proposalId=...`

CEO directive "Professional Trading Firm — Market-Analysis Knowledge +
Session Intelligence Expansion," Phase 6 — the Confluence Engine's
real-time read for one pending `TradeProposal`. Read-only, stateless,
computed fresh from the proposal's own `analystVotes`
(`app/signal_correlation.py::assess_confluence()`). Never gates, vetoes,
or adjusts the Gatekeeper/Risk/Model Validation pipeline — purely
informational. Returns a `ConfluenceRead`:

```json
{
  "naiveConfirmationCount": 3,
  "independentEvidenceCount": 2,
  "correlatedPairs": [
    {
      "roleA": "news",
      "roleB": "macro",
      "reason": "Both news and macro votes are driven by the same underlying ResearchItem.confidence value via the same probabilistic mechanism (app/voting.py's researcher_vote()) — the same evidence, expressed twice, not two independent reads."
    }
  ],
  "detail": "3 vote(s) agree with BUY, but only 2 real independent evidence source(s) back it — see correlatedPairs for which votes share an underlying signal or contribute no new evidence."
}
```

`404` if `proposalId` doesn't match a currently-pending `TradeProposal`.
The correlation map is grounded in a real audit of the six analyst
votes' actual mechanisms (`app/executive.py::generate_analyst_votes()`,
`app/voting.py::researcher_vote()`) — never an arbitrary discount.
`news`/`macro` share the same underlying `ResearchItem.confidence`
random-roll; `execution` is a pure majority synthesis of the other five
and is excluded from both counts entirely (never independent evidence).
`technical`, `risk`, and `sentiment` are real, independent reads and are
never discounted.

### `GET /api/executive/accuracy`

Design Bible Chapter 70 Part 2 — the Executive Accuracy Score.
`compute_executive_accuracy_scores()`, real and computed fresh every
request off `CeoDecisionRecord.outcome` (closed-trade-only, never a
counterfactual). Returns one `ExecutiveAccuracyScore` per department:

```json
{
  "role": "research",
  "departmentLabel": "Research",
  "decisionsTracked": 0,
  "correctCount": 0,
  "accuracyPct": null,
  "evaluationState": "not_enough_evidence"
}
```

**CEO directive "Features 31-35," Feature 33** — `accuracyPct` is
`null`, never a fabricated `0.0`, whenever `decisionsTracked` is below
the disclosed floor (`MIN_ACCURACY_SAMPLE_FOR_VERDICT = 3`, in
`app/executive_intelligence.py`). `evaluationState`
(`pass`/`fail`/`inconclusive`/`not_enough_evidence`) is published
alongside the raw percentage: `pass` at `accuracyPct >= 60`, `fail`
below `40`, `inconclusive` between — thresholds reused verbatim from
this codebase's own existing Command Center UI convention, not invented
for this feature. Reused unchanged by `GET /api/audit/overview`'s
`executiveAccuracy` field and by `compute_accuracy_multiplier()`
(`app/weighted_decisions.py`), which already treats `decisionsTracked
== 0` as the neutral `1.0×` (never a penalty for a track record that
doesn't exist yet) and now also guards the nullable `accuracyPct`
before dividing.

### `GET /api/executive/agent-accuracy`

CEO directive "Professional Quant Trading Core," Phase B's per-agent
learning follow-up. `compute_agent_vote_accuracy()`
(`app/executive_intelligence.py`), real and computed fresh every
request off `state.decisions`/`state.ceo_decisions` — the exact same
directional-accuracy methodology as `/accuracy` above, applied per
individual named agent instead of per department. Returns one
`AgentVoteAccuracyScore` for every `AgentId` (15 entries):

```json
{
  "agentId": "echo",
  "decisionsTracked": 0,
  "correctCount": 0,
  "accuracyPct": null,
  "evaluationState": "not_enough_evidence"
}
```

Reuses `TradeDecision.supportingAgents`/`opposingAgents` — the real,
already-established per-agent split `resolve_proposal()` already
computes (an agent supports a decision if their own `AnalystVote.choice`
matched the CEO's actual choice, opposes otherwise) — never a
fabricated P&L credit split across agents (see
`app/performance_attribution.py`'s own module docstring for why that
specific thing is never invented anywhere in this codebase). Only the
six agents who ever actually cast a real `AnalystVote` (`echo`,
`scout`, `nova`, `sentinel`, `pulse`, `atlas` —
`generate_analyst_votes()`'s fixed role→agent map) ever carry real
tracked evidence; the other nine `AgentId`s structurally never vote on
a trade candidate and honestly read `NOT_ENOUGH_EVIDENCE` forever, not
a fabricated score.

**The live feedback loop** (the "learning" half, not just a report):
`app/confidence.py`'s "Multi-Agent Agreement" `ConfidenceFactor` — one
of the seven factors on every `TradeProposal`'s `confidenceEngine` —
now weights each of the six analyst votes by that voting agent's own
real trailing accuracy multiplier (`compute_agent_accuracy_multiplier()`,
the identical 0.5-1.5 formula `app/weighted_decisions.py`'s
department-level multiplier already uses) instead of counting every
vote equally. `app/nexus.py`'s `tick()` computes this once per tick
from every already-resolved decision so far — never this tick's own
still-unresolved proposals, so a decision's own outcome can never leak
into its own weight, the same causal ordering the department-level
multiplier already relies on. With zero tracked history for every
agent (a fresh game) every multiplier is the neutral `1.0` and the
factor's score is numerically identical to a flat vote count — no
behavior change until real evidence accumulates.

### `GET /api/board/roster`

Design Bible Chapter 70 Part 1 — Executive Board & CEO Intelligence
System. Returns the real 11-seat `BoardRoster` (`app/board.py::
compute_board_roster()`) — 4 seats filled by real agents (their own real
`AGENT_PROFILES` occupation string, e.g. "Chief Investment Officer"),
the other 7 real, named-but-vacant seats copied verbatim from this
chapter's own source brief. Computed fresh per request, same on-demand
convention `GET /api/audit/overview` already established — nothing here
changes often enough to justify a WS-broadcast field. The brief's own
claimed 12th seat is never named anywhere in the source document and is
deliberately not represented (never a fabricated placeholder row).

### `GET /api/board/reports`

The real, permanent, capped (`MAX_BOARD_REPORTS`, 60) history of
`BoardReport` records generated by `app/nexus.py`/`app/state.py` on
three real cadences — `"daily"` (every real evening), `"quarterly"`
(every 90 sim-days), and `"emergency"` (fired once on a real
edge-crossing: an Emergency Stop activation from any source, or a Black
Swan tier crossing into red/critical — never every tick while the
condition holds). Each report composes 7 already-real signals
(Department Health, Problems, Recommendations, a narrative summary,
Risk Assessment, Confidence Level, Required CEO Decisions) rather than
recomputing any of them a second way. In the WS `"state"` broadcast as
`boardReports`.

### `GET /api/self-improvement/proposals`

Design Bible Chapter 74 Part 1 — Continuous Learning & Self-Improvement
System. Returns the real, permanent, capped
(`MAX_SELF_IMPROVEMENT_PROPOSALS`, 40) history of `SelfImprovementProposal`
records. Two real, evidence-gated generators feed this list — a
recurring `CaseStudy` mistake pattern (`app/mistakes.py`), checked once
per closed loss in `app/nexus.py`'s tick loop, and a Strategy Retirement
Cluster (`app/strategy_lab.py`), checked at the one real place a
retirement happens (`GameState.retire_strategy()` in `app/state.py`,
never tick-driven). The other six of the brief's eight named categories
have no real generator yet — see the Design Bible chapter's own
Deferred Features section. In the WS `"state"` broadcast as
`selfImprovementProposals`.

### `POST /api/self-improvement/proposals/decide`

CEO-manual approve/reject on a pending proposal — never
automation-eligible, the same restraint `POST /api/constitution/decide`
already holds itself to. Body: `{"proposalId": string, "approve":
boolean, "ceoNote": string | null}`. Returns the full, updated proposal
list. 400 if the proposal id doesn't exist or has already been decided.

### `GET /api/self-improvement/executive-learning/{agentId}`

The Executive Learning Summary — a real, on-demand aggregation of four
already-real per-agent systems (`app/coach.py`'s latest `AgentScore`,
`app/mentor.py`'s `ThinkingProfile`, `app/academy.py`'s
`AgentKnowledgeState`, `app/foundational_mentors.py`'s per-track
progress). Computed fresh per request, same convention
`GET /api/board/roster` already established; no new number is computed,
only composed.

### `GET /api/self-improvement/evolution-reports`

Design Bible Chapter 74 Part 2 — the Institutional Evolution Engine.
Returns the real, permanent, capped (`MAX_EVOLUTION_REPORTS`, 20)
history of `InstitutionalEvolutionReport` records, generated once per
real sim-month in `app/nexus.py` right after the existing monthly
Strategic Review Cycle. Each report composes — never recomputes — that
same month's real `StrategicReview`/`ExecutiveReview`/`CoachReport` by
id reference, plus the period's top 3 loss/win `CaseStudy` records and
its own `CompanyEvolutionScore`. In the WS `"state"` broadcast as
`evolutionReports`.

### `GET /api/self-improvement/evolution-score/{window}`

The Company Evolution Score for a given window — `monthly`, `quarterly`,
or `yearly` (400 for anything else). A disclosed, unweighted mean of
five real, period-scoped counts/deltas (Learning Volume, Proposal
Execution, Knowledge Growth, Strategy Maturation, Governance
Evolution) — deliberately disjoint from `CompanyHealth`'s 21 sub-scores
and `CompanyScore`'s 7-metric mean, never a re-read of either (see the
Design Bible chapter's own Ownership table for why that would be
duplication).

### `GET /api/vision-board`

Design Bible Chapter 74.5 — the CEO Vision Board & Strategic Alignment
Engine. Returns the real, permanent, CEO-mutated `VisionBoardState`
(`mission`, `priorities`, `objectives`, `identityNote`) — the same shape
as `RiskLimits`/`ConstitutionState`, not a growing log. In the WS
`"state"` broadcast as `visionBoard`.

### `POST /api/vision-board/mission`

CEO-manual only. Body: `{"mission": string | null}`. Returns the updated
`VisionBoardState`.

### `POST /api/vision-board/identity-note`

CEO-manual only. Body: `{"identityNote": string | null}` — an optional
annotation displayed next to `app/company_dna.py`'s real derived
identity classification, never a competing re-classification of it.
Returns the updated `VisionBoardState`.

### `POST /api/vision-board/priorities`

CEO-manual only. Body: `{"priorities": string[]}` — a ranked ordering
(index 0 = rank 1) over the fixed 6-value `VisionPriorityCategory` set
(`growth`, `risk`, `research`, `trading`, `operations`, `governance`).
400 if a category repeats or isn't one of the 6 real values. Returns the
updated `VisionBoardState`.

### `POST /api/vision-board/objectives`

CEO-manual only. Body: `{"text": string, "category": string}` — category
must be one of `trading_style`, `expansion`, `research_priority`,
`technology`, `lifestyle`, `other`. No progress percentage or target
value — the same honesty boundary `app/goals.py`'s own 4-metric limit
drew for itself. Capped (`MAX_VISION_BOARD_OBJECTIVES`, 20). Returns the
updated `VisionBoardState`.

### `DELETE /api/vision-board/objectives/{objectiveId}`

CEO-manual only. Returns the updated `VisionBoardState`.

### `GET /api/vision-board/alignment/goal/{goalId}`

The Vision Alignment Engine's real, disclosed, rank-based score for a
real `Goal` — `Goal.category` maps directly to a `VisionPriorityCategory`.
Computed fresh per request, never persisted. 404 if the goal doesn't
exist.

### `GET /api/vision-board/alignment/constitution-amendment/{amendmentId}`

The same Vision Alignment Engine score for a real `ConstitutionAmendment`
— always mapped to the `governance` category. Computed fresh per
request, never persisted. 404 if the amendment doesn't exist.

### `GET /api/vision-board/self-correction`

The one real, narrow Self-Correction check: the CEO's own rank-1
priority is `risk` and the real Daily Circuit Breaker tier
(`app/trading_modes.py`) is `tier2` or worse. Computed on-demand, never
persisted — same convention Chapter 72's Early Warning Score uses for a
live read with no history to keep.

#### `executiveMeetingLog` / `departmentSelfEvaluations` (WS + archive state, no dedicated endpoint)

v0.7 Feature 50 (Part 2/3) — the permanent record the intelligence
endpoint above never kept. Both broadcast on every WS `state` tick and
live in the `trade_history`/`knowledge_archive` archive modules
respectively (`GET /api/load/archive/trade_history` and
`GET /api/load/archive/knowledge_archive` — see `docs/API.md`'s Save
Architecture section below), same as `decisions`/`reflectionSessions`.

`executiveMeetingLog` — one real `ExecutiveMeetingLogEntry` per actual
`resolve_proposal()` call (CEO-driven, auto-resolved, or stale-expired),
capped at `MAX_MEETING_LOG_ENTRIES` (200):

```json
{
  "id": "meeting-proposal-42", "proposalId": "proposal-42", "symbol": "AAPL", "simDay": 12,
  "opinions": [ /* the same 9 DepartmentOpinion entries as the intelligence endpoint above (v0.7 Feature 51 added "market_intelligence" as the 9th) */ ],
  "recommendedAction": "trade_normally", "recommendationReason": "...",
  "ceoDecision": "buy", "networkAgreed": true,
  "decisionGrade": "A-", "decisionGradeScore": 91.2, // see below
  "resolvedBy": "ceo", "createdAt": "..."
}
```

`departmentSelfEvaluations` — one real `DepartmentSelfEvaluation` per
department per in-game week (same weekly cadence as `reflectionSessions`
above), built entirely from that department's own real opinions logged
to `executiveMeetingLog` over the trailing 7 sim days, capped at
`MAX_SELF_EVAL_HISTORY` (250):

```json
{
  "id": "selfeval-risk-14", "role": "risk", "departmentLabel": "Risk",
  "weekEndingSimDay": 14, "decisionsReviewed": 6, "score": 71.3,
  "summary": "6 real decision(s) reviewed this week; 71/100 average confidence.",
  "strengths": ["Weighed in on 6 real decision(s) this week, averaging 71/100 confidence.", "Agreed with the desk's overall call on 4/6 decisions."],
  "improvementAreas": ["Raised a real concern on 2/6 decisions — worth revisiting whether those calls held up."],
  "createdAt": "..."
}
```

**Decision Grade** — a real A+-to-F letter grade (`decisionGrade` on
both the entry above and on every `TradeDecision` from here forward —
`decisionGradeScore` is the 0-100 composite behind it) on the
decision-making PROCESS at the moment it's made: 50% the real Decision
Confidence Engine score, 25% the real multi-agent analyst agreement
rate, 25% whether the Trade Gatekeeper actually approved the trade.
Never reads the trade's own P&L (see `app/executive.py`'s
`compute_decision_grade`) — same "process over outcome" convention
`app/discipline.py`'s Discipline Score already established. `null` on
`TradeDecision` records that predate this field.

#### `marketIntelligenceReports` / `marketIntelligenceLearning` (WS + archive state, no dedicated endpoint)

v0.7 Feature 51 — the Market Intelligence Department's permanent daily
record, on the same "broadcast every WS tick + archived in
`knowledge_archive`" pattern as `executiveMeetingLog`/
`departmentSelfEvaluations` above (`GET /api/load/archive/knowledge_archive`).

`marketIntelligenceReports` — one real Executive Market Brief per real
in-game evening (`app/nexus.py`'s `EVENING_REVIEW_HOUR`, every day, not
gated by a weekly/monthly modulo), snapshotting that day's
`marketIntelligence` state plus a fresh 5-specialist Market Debate and a
Strategy Match, capped at `MAX_MARKET_INTELLIGENCE_REPORTS` (60):

```json
{
  "id": "mireport-12", "simDay": 12,
  "snapshot": { /* the same MarketIntelligenceState shape as the top-level marketIntelligence field above */ },
  "debate": {
    "id": "midebate-12",
    "turns": [
      { "specialist": "liquidity", "label": "Liquidity Specialist", "observation": "...", "confidencePct": 62.0, "evidence": ["..."], "risks": ["..."], "opportunities": ["..."] }
      /* price_action, momentum, quant, risk — 5 total, see app/market_debate.py */
    ],
    "summary": "5 independent specialist read(s) on today's Weak Uptrend — average confidence 57/100. Market Quality: good (79/100).",
    "createdAt": "..."
  },
  "strategyMatch": { "recommendedStrategyIds": [], "avoidedStrategyIds": [], "recommendedRiskLevel": "normal", "detail": "No strategy has been tested under today's specific conditions yet — no real match either way." },
  "tradeRecommendation": "trade_normally", "confidencePct": 88.0, "evidence": ["..."],
  "createdAt": "..."
}
```

`marketIntelligenceLearning` — the Learning Loop, generated the day
AFTER `forSimDay` once that day's real outcomes exist to compare
against, capped at `MAX_MARKET_INTELLIGENCE_LEARNING` (60):

```json
{
  "id": "mi-learning-12", "forSimDay": 12,
  "predictedRegime": "weak_uptrend", "predictedQualityTier": "good",
  "actualEnvironmentRegime": "bull", "regimeConsistent": true,
  "tradesClosedThatDay": 3, "tradesWinRatePct": 66.7,
  "lesson": "The read held up against what actually happened that day.",
  "createdAt": "..."
}
```

`regimeConsistent` compares the day's prediction against the real regime
`app/market_environment.py`'s own timeline recorded for that day via a
documented direction-only mapping (`app/market_intelligence.py`'s
`_REGIME_CONSISTENCY_MAP`) — `null` when nothing real exists yet to
compare against (no regime change or closed trade that day), never a
fabricated accuracy percentage. See `app/market_intelligence.py`'s module
docstring for the full real-vs-proxy honesty boundary behind every field
above (real technical analysis over real mock OHLCV data; institutional
activity/news risk are explicitly named proxies, never real order-flow
or economic-calendar data).

### `GET /api/knowledge-graph`

v0.7 Feature 25.5 — the Company Knowledge Graph. Read-only, stateless,
and computed fresh on every call (never part of `GameSaveState`/the WS
broadcast — same convention as `GET /api/executive/whatif` above; see
`app/knowledge_graph.py`'s module docstring). Builds a node-edge graph
from six already-real, already-persisted sources: completed
`ResearchItem`s, completed `AcademyProject`s, `agentKnowledge` (one
Knowledge Branch node per distinct branch), `executiveReviews`,
`coachReports`, and `hallOfFame`. Returns a `KnowledgeGraph`:

```json
{
  "nodes": [
    { "id": "agent-scout", "type": "agent", "label": "Scout", "subtitle": "Research Analyst", "timestamp": null },
    { "id": "research-r-scout-AAPL-...", "type": "research", "label": "Research on AAPL", "subtitle": "AAPL · 82% confidence", "timestamp": "2026-07-20T14:00:00+00:00" }
    // ... branch / academy_project / executive_review / coach_report / hall_of_fame nodes
  ],
  "edges": [
    { "source": "agent-scout", "target": "research-r-scout-AAPL-...", "relation": "researched", "label": "researched" },
    { "source": "research-r-scout-MSFT-...", "target": "research-r-scout-AAPL-...", "relation": "builds_on", "label": "builds on" }
    // ... has_branch / completed / featured_in / ranked_top_agent / achieved edges
  ],
  "generatedAt": "2026-07-28T18:04:11+00:00"
}
```

Every edge traces to a real, checkable shared attribute — never a
fabricated connection. See `app/knowledge_graph.py`'s module docstring
for the exact rule behind each `relation` type, and its docstring's
explicit scope note on why no Academy-project-to-Education-lesson edge
is generated (the two topic sets have no real thematic overlap).

CEO directive "Quant Research Factory / Strategy Discovery Engine,"
Phase 15 adds a `"research_experiment"` node per persisted
`QuantResearchExperiment` (real label = the strategy name tested; real
subtitle = outcome + hypothesis), linked to its real researcher agent
(`"researched"`) and, when a real match exists, to any `"strategy"`
node sharing the same real compiled definition id (`"tested"`).

### `POST /api/mentor/qotd/respond`

v0.7 Feature 32 — the player's answer to today's `QuestionOfTheDay`.
Body: `{ "questionId": "qotd-7", "response": "..." }`. Stores the
response verbatim on the matching archive entry — never graded (see
`app/mentor.py`'s module docstring for why: this codebase has no honest
mechanism to grade open-ended free text). Returns the updated
`QuestionOfTheDay`:

```json
{ "question": { "id": "qotd-7", "category": "risk_awareness", "question": "...", "relatedReference": "...", "playerResponse": "...", "playerRespondedAt": "...", "simDay": 7, "createdAt": "..." } }
```

`400` if `response` is empty/whitespace-only, or if `questionId` doesn't
match any archived entry.

`GET /api/load` returns this same set of fields plus `version` (currently
`"0.6"`), `player` (`EntityTransform`), `settings` (`SettingsState`),
`dialogueHistory` (`DialogueHistoryEntry[]`), and `updatedAt` — except the
fields belonging to the three archive modules, which come back empty (see
`GET /api/load`'s own section above for why).

### `POST /api/treasury/deposit` / `POST /api/treasury/withdraw`

v0.7 Feature 33 — the CEO Treasury. Body: `{ "amount": 1000 }`. Moves real
cash between `paperPortfolio.cashBalance` (Operating Capital) and
`treasury.balance` (the Treasury) — a deposit takes cash away from
Operating Capital and adds it to the Treasury, a withdrawal reverses it.
Both are explicit, CEO-initiated transfers; no automatic system in this
codebase ever calls either (see `app/treasury.py`'s module docstring for
the full structural isolation guarantee). Returns the updated pair:

```json
{ "treasury": { "balance": 1000.0, "lifetimeDeposits": 1000.0, "...": "..." }, "paperPortfolio": { "cashBalance": 99000.0, "...": "..." } }
```

`400` if `amount` isn't positive, if a deposit exceeds Operating
Capital's real cash balance, or if a withdrawal exceeds the Treasury's
real balance.

### `POST /api/treasury/rules/create`

Creates a Smart Savings Rule. Body: `{ "ruleType": "percent_of_monthly_profit", "percent": 10, "reserveTarget": null }`
or `{ "ruleType": "excess_above_reserve", "percent": 0, "reserveTarget": 50000 }`.
The brief's "save 5% of monthly profit" and "save 10% after profitable
months" collapse into the one `percent_of_monthly_profit` rule type here
— they're mechanically identical (saving a percent of profit only ever
fires when profit is positive), so there's no second, redundant rule
type. Applied automatically once a month, alongside the real monthly
`TreasuryMonthlyReport` (see `app/treasury.py`'s
`apply_monthly_savings_rules()`). Returns `{ "treasury": { ... } }`. `400`
for an out-of-range percent, or a missing/negative reserve target.

### `POST /api/treasury/rules/toggle` / `POST /api/treasury/rules/pause-all`

`{ "ruleId": "treasury-rule-...", "active": false }` toggles one rule;
pause-all (empty body) deactivates every rule at once — the brief's
"Pause all automatic transfers." Both return `{ "treasury": { ... } }`.
`400` from toggle if `ruleId` doesn't match any existing rule.

### `POST /api/time/advance`

v0.7 Feature 34 — CEO time controls (End Workday/Week/Month, or a bounded
custom fast-forward). Body: `{ "target": "workday_end" }` (also
`"week_end"` / `"month_end"`), or `{ "target": "hours", "hours": 6 }`
(1-72). Rather than jumping the clock directly to the target, this loops
the same real per-tick orchestration step (`GameState._advance_once()`)
under one lock acquisition until it lands there — every exact-minute
cadence check along the way (evening reports, the morning Question of the
Day, Treasury's monthly savings rules, ...) fires exactly as it would if
that much real time had actually passed. Calling it exactly at the
target minute still advances to the *next* occurrence, never a no-op.
Because a multi-hour fast-forward can touch nearly everything NEXUS
touches, this returns the full `GameSaveState` (same shape as `GET
/api/load`) rather than just the new `time`, so the client can apply it
in one shot instead of waiting on the next WS broadcast:

```json
{ "time": { "day": 4, "hour": 20, "minute": 0 }, "treasury": { "...": "..." }, "...": "..." }
```

`400` if `target` is `"hours"` and `hours` is missing, non-positive, or
over 72.

### `POST /api/calendar/events/create` / `POST /api/calendar/events/delete`

v0.7 Feature 36 — the CEO Calendar's player-created custom events.
`create` body: `{ "category": "town_hall", "title": "All-hands on risk limits", "day": 12, "hour": 15, "minute": 0 }`
— `category` is one of `emergency_meeting | company_holiday |
extra_training_day | research_marathon | hackathon | strategy_day |
celebration | town_hall | other` (the brief's own eight named examples
plus a free-form `other`). `delete` body: `{ "eventId": "calendar-player-..." }`.
Both return `{ "calendar": { "systemEvents": [...], "playerEvents": [...], "updatedAt": "..." } }`.
These are informational only — creating one never changes department
behavior (no real payroll/attendance/training-boost system exists
anywhere in this codebase to attach one to honestly — see
`app/calendar.py`'s module docstring). `400` on an empty/over-140-char
title, an out-of-range hour/minute, or a day/time already in the past.

`systemEvents` (the real, computable cadence events — Weekly/Monthly
reports, the daily Question of the Day, honest ESTIMATED research
completion dates, ...) is never fetched separately — it's recomputed
fresh every tick and part of every `GameSaveState`/`"state"` WS message,
the same way `companyHealth`/`academyState` already are.

### `POST /api/black-box/fund` / `pause` / `resume` / `cancel` / `priority` / `notes` / `reassign`

v0.7 — the Advanced Quantitative Research Division's CEO Research
Dashboard. All seven mutate the one active `BlackBoxProject` and return
`{ "blackBox": { "active": {...}, "archive": [...], "reviews": [...], "viewedBreakthroughIds": [...], "updatedAt": "..." } }`.
`400` if no project is currently active (all of these), plus per-action:

- `fund`: body `{ "amount": 500 }`. Adds directly to the project's own
  `budget` — **not** drawn from `treasury.balance` (see
  `app/black_box.py`'s module docstring for why this doesn't touch the
  Treasury's own structurally-isolated balance). `400` if `amount` isn't
  positive or exceeds the per-call cap (`MAX_BLACK_BOX_FUNDING_PER_CALL`,
  $5,000).
- `pause` / `resume`: no body. `400` if the project is already
  `under_review`/`completed`/`failed`.
- `cancel`: no body. Archives the project immediately with
  `status: "failed"` and a real cancellation note.
- `priority`: body `{ "priority": "high" }` (`low | normal | high`) —
  a real lever: higher priority scales the daily progress gain up and
  the daily budget burn up together.
- `notes`: body `{ "note": "Check the volume-weighted variant too" }` —
  a real CEO-authored research idea, appended to `researchNotes` (capped
  at `MAX_BLACK_BOX_NOTES`, 20). `400` if empty/whitespace-only.
- `reassign`: body `{ "agentId": "echo", "newAgentId": "atlas" }` —
  swaps one non-leader team seat for a different agent not already on
  the team. `400` if `agentId` isn't a current team member, or if
  `agentId` is `"quant"` (the leader seat is fixed).

### `POST /api/black-box/ack-breakthrough`

Body: `{ "reviewId": "breakthrough-blackbox-..." }`. Marks one Eureka!
Breakthrough cinematic as shown/dismissed — the same real "seen"
tracking pattern `POST /api/trades/ack` already established, so a
refresh or restart never re-shows a breakthrough moment the player
already saw. Returns `{ "viewedBreakthroughIds": [...] }`.

### `POST /api/talent/ack-report`

v0.7 Feature 44 — the Talent Discovery System. Body:
`{ "reportId": "talent-echo-reasoning" }`. Marks one `TalentReport` as
seen — the same real "seen" tracking pattern
`POST /api/black-box/ack-breakthrough` already established. Returns
`{ "viewedReportIds": [...] }`.

### `POST /api/sandbox/backtest` / `begin-paper-trial` / `begin-limited-live` / `request-review` / `decide`

v0.7 Feature 45 — the Research Sandbox. All five return
`{ "strategies": [...] }` and/or `{ "strategyReviews": [...] }`
(`backtest` also returns `{ "backtestSessions": [...] }`). `400` on any
real stage-gate violation, with the exact required stage in the message.

- `backtest`: body `{ "strategyId": "...", "scenario": "bull", "customReturnBiasPct": 0, "customVolatilityBias": 1 }`.
  Queues a real `BacktestSession` for that strategy under the chosen
  Testing Environment. `customReturnBiasPct`/`customVolatilityBias` only
  matter when `scenario` is `"custom"`. `400` if the Sandbox is already
  at `MAX_CONCURRENT_SESSIONS` or the watchlist is empty.
- `begin-paper-trial`: body `{ "strategyId": "..." }`. Requires the
  strategy's stage to already be `"market_simulation"`.
- `begin-limited-live`: body `{ "strategyId": "...", "amount": 500 }`.
  Requires stage `"paper_trading"` and at least `MIN_PAPER_TRIAL_SIM_DAYS`
  (1) full in-game day since the trial began. `400` if `amount` isn't
  positive or exceeds `MAX_LIMITED_LIVE_CAPITAL` ($2,000).
- `request-review`: body `{ "strategyId": "..." }`. Requires stage
  `"limited_live_capital"`; generates a real `StrategyReview` (five
  reviewer verdicts) and advances the strategy to `"company_review"` in
  one call. Also returns `{ "strategyModelValidation": {...} | null }` —
  Meridian/CIO's independent, advisory-only `ModelValidationReport`
  (Quantitative Research & Intelligence System, Piece 4; see
  `docs/DesignBible/volumes/09-departments/chapter-62-innovation-lab-continuous-improvement.md`'s
  addendum). Advisory only: never affects the stage transition above.
- `decide`: body `{ "reviewId": "...", "approve": true }`. The Company
  Review stage's real manual CEO call — Learning Mode always requires
  this; Assisted/Executive Mode auto-resolve instead (see
  `docs/Architecture.md`'s "Research Sandbox" section). `400` if the
  review was already decided.

### `GET /api/sandbox/model-validation?strategyId=`

Piece 4 (Quantitative Research & Intelligence System) — Meridian/CIO's
most recent `ModelValidationReport` for this strategy, or `null` if it
has never been through Company Review yet. Read-only, computed from
already-persisted state (no recomputation), same pattern as
`GET /api/sandbox/certification`.

### `GET /api/sandbox/agent-survival`

CEO directive "Professional Quant Portfolio Intelligence + Alpha
Research Engine," Phase 6 (Agent Talent System) — mirrors
`GET /api/executive/agent-accuracy`'s own real per-agent
evidence-floor convention one level up, over real Strategy outcomes
instead of trade votes. `compute_agent_strategy_survival()`
(`app/strategy_lab.py`), computed fresh every request off
`state.strategies`/`state.strategy_hall_of_fame`/
`state.strategy_failed_archive`. Returns one `AgentStrategySurvivalScore`
for every `AgentId` (15 entries):

```json
{
  "agentId": "echo",
  "strategiesCreated": 0,
  "resolvedCount": 0,
  "survivedCount": 0,
  "failedCount": 0,
  "survivalRatePct": null,
  "evaluationState": "not_enough_evidence"
}
```

Reuses `Strategy.createdBy` and the real `createdBy` already stamped
on every `StrategyHallOfFameEntry`/`FailedStrategyArchiveEntry` at the
moment of retirement (`generate_strategy_retirement_outcome()`) — no
join needed, no fabricated attribution. A strategy still active at any
pre-`"retired"` stage counts toward `strategiesCreated` but is honestly
excluded from `resolvedCount` until it actually reaches one of those
two real terminal archives.

### `GET /api/sandbox/live-strategy-eligibility`

CEO directive "Strategy Intelligence + Live Strategy Attribution,"
Phase 11 — "TODAY: strategies currently eligible / strategies currently
blocked." Runs the same real `compute_strategy_match()` behind
`MarketIntelligenceReport.strategyMatch` fresh, against the
always-current live regime (`state.marketIntelligence.regime`) rather
than that report's own once-per-sim-day, up-to-a-day-stale copy.
Returns a `StrategyMatch`: `{ recommendedStrategyIds: string[],
avoidedStrategyIds: string[], recommendedRiskLevel: "minimal" |
"reduced" | "normal" | "elevated", detail: string }`. Read-only,
computed fresh every call, nothing persisted.

### `GET /api/sandbox/ema-pullback-research?timeframe=1h&candlesPerSymbol=6000`

CEO directive "Professional Trading Firm — Market-Analysis Knowledge +
Session Intelligence Expansion," Phase 15 — the 50 EMA breakout +
pullback strategy converted into a formal, reproducible research
hypothesis and independently backtested against this codebase's own
real (mock) candle history (`app/ema_pullback_research.py`). Read-only,
computed fresh every call — nothing here is persisted, and no agent or
live trading decision is ever wired to this endpoint's result. Returns
an `EmaPullbackResearchResult`:

```json
{
  "hypothesis": "After a sustained period below/above the 50 EMA, ...",
  "symbolsTested": ["AAPL", "MSFT", "SPY", "QQQ", "GLD", "BTC-USD", "XLF", "DXY"],
  "referenceRMultiple": 2.0,
  "rMultipleSweep": [ { "label": "1R", "tradeCount": 40, "winRatePct": 84.2, "expectancyR": 0.68, "verdict": "enough_evidence", "...": "..." } ],
  "sessionBreakdown": [ { "label": "london", "tradeCount": 5, "winRatePct": 60.0, "...": "..." } ],
  "regimeTrendBreakdown": [ "..." ],
  "regimeVolatilityBreakdown": [ "..." ],
  "instrumentBreakdown": [ "..." ],
  "breakoutSizeBreakdown": [ { "label": "extended (range >= 2x recent avg)", "...": "..." }, { "label": "normal", "...": "..." } ],
  "confirmedVsNaiveBaseline": [ { "label": "confirmed (pullback + breakout)", "...": "..." }, { "label": "naive (EMA cross only, no confirmation)", "...": "..." } ],
  "sourceClaimComparison": {
    "sourceClaimTradeCount": 32, "sourceClaimWinners": 21, "sourceClaimWinRatePct": 65.6,
    "tradetownTradeCount": 40, "tradetownWinRatePct": 84.2,
    "detail": "... This is a SOURCE CLAIM, not TradeTown-validated evidence ..."
  },
  "modelValidation": { "verdict": "needs_more_evidence", "...": "..." },
  "monteCarlo": { "probabilityOfProfitPct": 99.5, "...": "..." },
  "dataHonestyNote": "Every candle in this run is app/market_data.py's own real, procedurally-generated (seeded, reproducible) mock OHLCV series — never real historical market data. ..."
}
```

Every rule (EMA cross + close confirmation, the real 2+-candle pullback,
the body-close breakout of the pre-pullback swing level, Invalidation A
— a real close back through the 50 EMA before confirmation discards the
setup, Invalidation B — extended breakout candles are TAGGED and their
own real expectancy reported, never silently filtered out) is precisely
defined and reproducible — see the module's own docstring. The Chandelier
Stop uses the methodology's own standard published defaults (22-period
ATR, 3.0x multiplier), never a TradeTown-fitted number. `sourceClaim
Comparison` exists so the CEO-supplied source material's own reported
65.6% win rate is always shown ALONGSIDE TradeTown's real, independently
-computed number — never substituted for it, and never used as an input
to any calculation. `modelValidation`/`monteCarlo` reuse the existing
Model Validator and Monte Carlo bootstrap unchanged (an ad hoc, non-
persisted `Strategy`/`SimulationResult` pair built from this run's own
real numbers is the only way they are invoked) — never a second,
parallel validation or risk engine, and this endpoint never gates the
Gatekeeper, Risk Authority, or any live trading decision.

### `POST /api/sandbox/compile-strategy`

CEO directive "Professional Quant Trading Firm — Quant Intelligence +
Market Analysis Completion Phase," Phase F. Body:
`{ "name": "...", "sourceText": "...", "timeframe": "1h", "previousVersion": null }`.
Runs the English strategy description through `app/strategy_compiler.py`'s
deterministic, disclosed-vocabulary pattern-matcher (never an LLM call —
this endpoint, like the rest of this codebase, makes no live LLM calls at
runtime) and returns a `CompiledStrategyDefinition`:

```json
{
  "id": "compiled-...", "name": "50 EMA Pullback", "sourceText": "...",
  "version": 1, "createdBy": "quant", "timeframe": "1h",
  "sequence": [ { "id": "...", "stepType": "trigger", "condition": {"...": "..."}, "detail": "..." } ],
  "stop": { "method": "chandelier", "atrPeriod": 22, "atrMultiplier": 3.0, "percent": null },
  "target": { "method": "r_multiple", "value": 2.0 },
  "ambiguities": [],
  "status": "compiled",
  "detail": "..."
}
```

`status` is `"compiled"` only when every required piece (trigger, entry,
stop, target) was recognized with zero ambiguities. Vague phrasing
("strong breakout," "significant volume," "near support," "clean
pullback," etc.) is matched against an explicit banned-phrase list and
reported in `ambiguities` (with a `suggestedResolution` where one exists)
rather than being silently converted into an invented threshold; text
outside the compiler's recognized vocabulary yields `status="invalid"`
with an empty `sequence`, `stop: null`, `target: null` — never a guess.
Stateless: nothing compiled here is persisted; `version` is always `1`
unless a caller supplies `previousVersion` for its own bookkeeping.
The recognized trigger vocabulary (CEO directive "...Quant Intelligence
+ Market Analysis Completion Phase (Next Research + Validation Pass)")
now also includes real RSI/Stochastic threshold triggers ("RSI above
70," "the 14 Stochastic is below 20" — period optional, defaults to 14)
and a real MACD line/signal-line crossover ("MACD crosses above the
signal line," always the standard 12/26/9 defaults). "Above N" always
compiles to a real long-biased trigger, "below N" to short — the
MOMENTUM reading, not mean-reversion (a mean-reversion-phrased strategy
like "RSI below 30, buy the bounce" is correctly refused as a real
trigger/entry direction contradiction — see `app/strategy_compiler.py`'s
own module docstring). At most one trigger is recognized per strategy.

### `POST /api/sandbox/backtest-compiled-strategy?candlesPerSymbol=6000`

Body: a `CompiledStrategyDefinition` (typically one just returned by
`compile-strategy`). Runs `app/strategy_engine.py`'s generic backtest
runner — a bar-by-bar state machine driven entirely by the compiled
definition's own trigger/requirement/entry sequence and stop/target
specs — against real (mock) candle history, through the same Monte Carlo
bootstrap and Model Validator pipeline `ema-pullback-research` uses.
Returns a `CompiledStrategyBacktestResult` (`overall`/`sessionBreakdown`/
`instrumentBreakdown`/`regimeTrendBreakdown`/`regimeVolatilityBreakdown`
buckets, `modelValidation`, `monteCarlo`, `dataHonestyNote`) shaped like
the EMA pullback result above. `400` if
`definition.status !== "compiled"` or the definition references an
indicator outside the engine's current `price_close/open/high/low`,
`ema`, `sma`, `rsi`, `macd_line`/`macd_signal`/`macd_histogram`,
`stochastic_percent_k`/`stochastic_percent_d` vocabulary — the engine
refuses to guess rather than silently skipping unsupported conditions.
Read-only, computed fresh every call; never wired into any agent or live
trading decision.

### `POST /api/sandbox/walk-forward-validation?candlesPerSymbol=6000&windowBars=1000`

CEO directive "...Quant Intelligence + Market Analysis Completion Phase
(Next Research + Validation Pass)," item 4. Body: a
`CompiledStrategyDefinition`. Splits each symbol's own real candle
series into consecutive, non-overlapping `windowBars`-bar windows and
independently backtests the SAME fixed definition against each — a
real, disjoint chronological walk-forward, never a claim of parameter
re-optimization per window (see `app/walk_forward.py`'s own module
docstring). Returns a `WalkForwardValidationResult`:

```json
{
  "id": "walk-forward-...", "definitionId": "...", "definitionVersion": 1, "windowBars": 1000,
  "symbols": [ { "symbol": "AAPL", "windows": [ { "windowIndex": 1, "startTimestamp": "...", "endTimestamp": "...", "bucket": {"...": "..."} } ], "positiveWindowCount": 3, "negativeWindowCount": 1, "evaluatedWindowCount": 4, "detail": "..." } ],
  "verdict": "stable", "detail": "...", "dataHonestyNote": "...", "generatedAt": "..."
}
```

`verdict` (`stable`/`unstable`/`insufficient_data`) reads real sign-
agreement of expectancy across every window with enough closed trades
for its own bucket-level verdict — `insufficient_data` below 3 such
evaluated windows, never a forced call. Same `400` refusal conditions as
`backtest-compiled-strategy`.

### `POST /api/sandbox/parameter-sensitivity?candlesPerSymbol=6000`

Same directive, item 5. Body: a `CompiledStrategyDefinition`. Sweeps the
definition's own real stop and target values independently (one-
parameter-at-a-time, never a full grid search) across five real
neighboring points each. Returns a `ParameterSensitivityResult`
(`stopAxis`/`targetAxis`, each `{ parameter, sweepable, baseValue,
points: [{ label, value, bucket }], detail }`, plus `verdict`
(`robust`/`fragile`/`insufficient_data`) and a `multipleTestingNote`
disclosing the real trial count). A `swing_level` stop has no free
numeric parameter — reported as `sweepable: false` with an empty
`points` list, never a fabricated sweep. This schema has no "best
combination" field by design.

### `POST /api/sandbox/cost-sensitivity?candlesPerSymbol=6000`

Same directive, item 6. Body: a `CompiledStrategyDefinition`. Re-uses
the exact real, already-closed trades a zero-friction backtest produced
and deducts a real round-trip basis-point cost from each trade's own
realized R-multiple, across a base/low/moderate/high/stressed scenario
ladder built from this codebase's own existing real
`TRANSACTION_COST_BPS`/`BASE_SLIPPAGE_BPS`/`MAX_SLIPPAGE_BPS` constants
(never a second, invented cost model). Returns a `CostSensitivityResult`
(`scenarios: [{ label, costBpsPerLeg, bucket }]`, `verdict`
(`cost_resilient`/`cost_sensitive`/`insufficient_data`)).

### `POST /api/sandbox/look-ahead-audit?candlesPerSymbol=6000`

Same directive, item 7. Body: a `CompiledStrategyDefinition`. For every
real setup the definition's own detector finds against the full candle
series, independently re-detects it against the series truncated to end
exactly at that setup's own entry bar — a real, structural proof (not a
code-review claim) that detection never depended on a future candle.
Returns a `LookAheadAuditResult` (`setupsChecked`, `violations: [{
entryIndex, entryTimestamp, direction, detail }]`, `verdict`
(`clean`/`violations_found`/`insufficient_data`)).

### `POST /api/sandbox/complexity-score`

CEO directive "TradeTown — 11/10 Strategy Factory + Ruthless
Backtesting Engine," Section 13 (Simplicity/Complexity Score). Body: a
`CompiledStrategyDefinition`. Needs no market data — a pure structural
count over the definition's own real rule sequence
(`app/strategy_complexity.py::compute_strategy_complexity()`). Returns
a `StrategyComplexityScore`:

```json
{
  "definitionId": "...",
  "definitionVersion": 1,
  "stepCount": 3,
  "conditionCount": 1,
  "distinctIndicatorCount": 2,
  "parameterCount": 5,
  "complexityScore": 11,
  "band": "moderate",
  "detail": "...",
  "generatedAt": "..."
}
```

`distinctIndicatorCount` deduplicates by indicator TYPE only (two
differently-parametrized EMAs still count as one) — period variation
is counted separately via `parameterCount`. `band`
(`simple`/`moderate`/`complex`) uses real, disclosed threshold
constants, one convention among several valid ones. Advisory only:
never wired into any promotion gate, the Gatekeeper, or
`strategy_tournament.py`'s ranking. The identical real number is also
packaged as `ResearchExperimentRecord.complexity` by
`POST /api/sandbox/research-experiment` below — same computation, not
a second one.

### `GET /api/sandbox/survivorship-bias?symbol=...`

Same directive, item 8. Read-only. Always returns
`{ "symbol": "...", "status": "unavailable", "detail": "..." }` — a
real, disclosed data-availability interface, never a fabricated check.
This codebase's research universe (`app/watchlist.py`'s `SEED_SYMBOLS`/
`EXTRA_SYMBOL_POOL`) is a fixed, static, always-present pool with no
historical constituent/delisting data source behind it.

### `POST /api/sandbox/research-experiment?candlesPerSymbol=6000`

Same directive, item 11 — the Research Desk's one reproducible
experiment record. Body: a `CompiledStrategyDefinition`. Bundles
real results from `backtest-compiled-strategy`,
`walk-forward-validation`, `parameter-sensitivity`, `cost-sensitivity`,
and `look-ahead-audit` for the SAME definition into one
`ResearchExperimentRecord`, plus a `conclusion` string synthesized by a
real, disclosed, deterministic rule over those five verdicts (see
`app/research_experiment.py`'s own module docstring for the exact
priority order — a look-ahead violation or a rejected Model Validation
verdict always overrides everything else; any missing evidence anywhere
reads "insufficient evidence," never a silent pass). Read-only, computed
fresh every call (several real backtests run in sequence — budget a few
seconds); nothing here is persisted.

`ResearchExperimentRecord` also carries `overfittingDiagnosis`
(CEO directive "Professional Quant Firm Phase," Feature 39) — the same
five verdicts above relabeled into a real, deterministic
`robust`/`fragile`/`insufficient_data`/`overfit_suspected`/
`oos_failure`/`pending_validation` classification (see
`app/overfitting_diagnostics.py`'s own module docstring for the exact
priority rule). Alongside `conclusion`, not a replacement for it.

`ResearchExperimentRecord.complexity` (CEO directive "TradeTown —
11/10 Strategy Factory + Ruthless Backtesting Engine," Section 13) —
the same real `StrategyComplexityScore`
`POST /api/sandbox/complexity-score` above returns, packaged alongside
the other five axes. Advisory only, never wired into `conclusion`.

`ResearchExperimentRecord.buyAndHoldBaseline` (CEO directive "Quant
Research Factory / Strategy Discovery Engine," Phase 5) — one
`BuyAndHoldBaseline` per symbol tested (`symbol`, `startPrice`,
`endPrice`, `returnPct`, `candleCount`), the real percent price return
from the same candle window's first close to its last close, computed
by `app/baseline_comparison.py`. Deliberately never blended with the
backtest's own R-multiple-based stats into a single "beat the market"
figure — different units — and exists purely as real regime context
(was the underlying market itself strongly trending during the tested
window).

### `POST /api/sandbox/register-strategy-version`

CEO directive "Professional Quant Firm Phase," Feature 37 — real,
persisted `CompiledStrategyDefinition` version history. Body:
`{ "name": "...", "sourceText": "...", "timeframe": "1h", "createdBy": "quant" }`.
Unlike `POST /compile-strategy` (stateless preview, unchanged), this
computes the REAL next version from this strategy name's own persisted
history (`GameSaveState.compiledStrategyVersions`, keyed by the same
real slug `compile-strategy` already derives from `name`) rather than
trusting a caller-supplied number, and permanently appends it — prior
versions are never overwritten. Returns the new
`CompiledStrategyDefinition`.

### `GET /api/sandbox/strategy-versions?name=...`

Same directive, Feature 37 — the full, real, persisted version history
for one strategy name (oldest first). Returns
`CompiledStrategyDefinition[]`; empty if this name has never been
registered via the endpoint above (a stateless `/compile-strategy`
preview alone never appears here).

### `POST /api/sandbox/champion-challenger/compare`

CEO directive "TradeTown — 11/10 Self-Improving Quant Agent System,"
Section 1 (Champion vs Challenger). Body: `{ "championDefinition":
CompiledStrategyDefinition, "challengerDefinition":
CompiledStrategyDefinition, "strategyFamily": "...", "hypothesis": "...",
"proposedBy": "quant", "symbols": [...], "timeframe": "...",
"candlesPerSymbol": 6000 }` (`symbols`/`timeframe`/`candlesPerSymbol`
optional). Runs BOTH definitions through the real
`run_research_experiment()` pipeline over the IDENTICAL real
symbols/timeframe/candle window, then applies a real, disclosed
ECONOMIC tradeoff rule (see `app/champion_challenger.py`'s own module
docstring for exactly why this is not a statistical-significance test).
Returns and permanently persists a `ChallengerComparison`:
`championExpectancyR`/`challengerExpectancyR`/
`championProfitFactor`/`challengerProfitFactor`/
`championMaxDrawdownR`/`challengerMaxDrawdownR` (all real, direct reads
from each side's own `EmaPullbackStatsBucket`, R-multiple based),
`championConclusion`/`challengerConclusion` (each side's own real
research conclusion), and `verdict`
(`challenger_recommended`/`champion_retained`/`insufficient_evidence`)
with a real, disclosed `reasoning` string. Never deleted, even a
retained-champion or insufficient-evidence outcome.

CEO directive "TradeTown — Research Engine Hardening +
Self-Improvement Implementation Pass," Phase 7 — `verdict` now also
applies a real, disclosed profit-factor non-regression guard
(`MAX_PROFIT_FACTOR_REGRESSION_PCT = 20.0`) layered on top of the
existing expectancy/drawdown tradeoff paths: a meaningful profit-factor
regression blocks a promotion either path would otherwise recommend,
named explicitly in `reasoning`. Phase 8 — `statisticalComparison.evidenceState`
can now also read `invalid_evidence` (a real, distinct state from
`insufficient_evidence`) whenever either side's real trade sample
contains a non-finite value; every numeric field on
`BootstrapComparisonResult` reads `null` in that case, and
`classification` reads `invalid_evidence` too — never a fabricated
confidence interval.

### `POST /api/sandbox/champion-challenger/promote`

Same directive — the one real, explicit action that changes the
current champion for a strategy family. Body: `{ "comparisonId": "...",
"promotedBy": "quant", "reasoning": "..." }`. Returns a new
`ChampionRecord`, permanently appended. `400` when the named comparison
doesn't exist, or its own real `verdict` was not
`"challenger_recommended"` — a champion-retained or
insufficient-evidence comparison can never justify a promotion.

### `GET /api/sandbox/champion-challenger/{strategyFamily}`

Same directive — the real, full picture for one strategy family:
`current` (the most recent real `ChampionRecord` for this family, or
`null` if none has ever been promoted — no separate, driftable
"current pointer" exists), `history` (every real promotion, oldest
first, never deleted), and `comparisons` (every real
`ChallengerComparison` ever run for this family, including ones that
retained the champion). Read-only, computed fresh every call.

### `POST /api/sandbox/research-loop/run`

CEO directive "TradeTown — Next Major Implementation Pass, Phase 4-6:
Self-Improving Strategy Factory + Validation Funnel." Body:
`{ "hypothesis": StrategyHypothesis, "definition": CompiledStrategyDefinition,
"symbols": [...], "timeframe": "...", "candlesPerSymbol": 6000 }`
(`symbols`/`timeframe`/`candlesPerSymbol` optional). Runs the real
funnel over the real Research Desk pipeline (see
`app/research_loop.py`'s own module docstring) — no duplicate backtest
math — and permanently persists both a `ResearchLoopIterationRecord`
and a real, templated `ResearchLessonRecord`. Returns the full
`ResearchLoopIterationRecord`: the wrapped `ResearchExperimentRecord`,
a transparent `StrategyScorecard` (every dimension real or `null` —
rendered "NOT VERIFIED"), `benchmarkComparisons` (a real, disclosed
approximation — see `BenchmarkComparison.approximationNote` on every
instance), `failureCodes`, the real `candidacy` binning
(`accepted`/`promising`/`fragile`/`rejected`/`duplicate`/
`insufficient_evidence`/`overfit`/`benchmark_failed`/`risk_failed`)
with its real `candidacyReason`, `similarExperiments`/
`similarFailedStrategies`/`researchRelationship` (real memory
consultation, never blocking), an optional `mutation` (a real,
persisted recommendation — never an auto-applied strategy rewrite; see
that module's own docstring), and `budget` (real, bounded research
budget status). Purely informational triage — never gates or feeds
Certification/Hall-of-Fame/Champion-Challenger, which stay the sole,
unmodified, authoritative promotion path.

### `GET /api/sandbox/research-loop/iterations`

Same directive — the full, real, permanent iteration history, never
overwritten. Optional `?strategyFamily=...` and `?candidacy=...`
filters (the latter added by CEO directive "TradeTown — Phase 7:
Autonomous Strategy Evolution Engine," Section 18 — the real, reused
way to "inspect rejected candidates"/"inspect survivors," e.g.
`?candidacy=accepted`, without a second, duplicate endpoint). Returns
`ResearchLoopIterationRecord[]`.

### `GET /api/sandbox/research-loop/lessons`

Same directive, Section 9 — the real, permanent self-improvement
memory. Optional `?strategyFamily=...` filter. Returns
`ResearchLessonRecord[]`.

### `GET /api/sandbox/research-loop/lessons/evidence`

CEO directive "TradeTown — Phase 7: Autonomous Strategy Evolution
Engine," Section 12 — "memory is evidence, not truth." Optional
`?strategyFamily=...` filter. Returns `LessonEvidenceSummary[]`, computed
fresh (never stored on `ResearchLessonRecord` itself): for each lesson,
how many other real lessons for the SAME strategy family landed in the
same real candidacy bucket (accepted/promising = "favorable," everything
else "unfavorable") as this one, versus the opposite bucket — a real,
disclosed, simple proxy, never a fabricated statistical confidence
measure.

### `POST /api/sandbox/research-factory/run`

CEO directive "TradeTown — Phase 7: Autonomous Strategy Evolution
Engine" — the one real entry point for the full, bounded,
multi-generation OBSERVE→GENERATE→MUTATE→COMPILE→BACKTEST→VALIDATE→
STRESS→COMPARE→ACCEPT-OR-BIN→LEARN loop (see `app/research_factory.py`'s
own module docstring for the complete real architecture). Body:
`{ "hypothesis": StrategyHypothesis, "definition": CompiledStrategyDefinition,
"maxGenerations": 5, "maxTotalBacktests": 10, "symbols": [...],
"timeframe": "...", "candlesPerSymbol": 6000 }` (all but `hypothesis`/
`definition` optional). Every generation reuses the exact same real
funnel `POST /research-loop/run` already uses — this endpoint's only new
behavior is automatically compiling and re-testing each real, bounded,
deterministic mutation via `app/strategy_registry.py`'s own unmodified
`register_strategy_version()`. Returns the full `FactoryRunRecord`: every
`FactoryCandidateRecord` (real lineage via `parentCandidateId`, real
lifecycle stage, the wrapped `ResearchLoopIterationRecord` when a real
backtest ran, an optional `MutationCandidate` with its own real
`mutatedSourceText` or a disclosed `null`), real decomposable summary
counts, `topRejectionReasons`/`topLessons`, a real disclosed
`stopReason`, and the current champion (if any) for context. Never calls
Champion/Challenger or any promotion path — a real survivor is only ever
LABELED eligible; a separate, explicit, unmodified
`POST /champion-challenger/compare` call is still required. Permanently
persists the run plus every generation's own real
`ResearchLoopIterationRecord`/`ResearchLessonRecord` (appended into the
same `researchIterations`/`researchLessons` lists Phase 4-6 already
uses, never stored twice).

### `GET /api/sandbox/research-factory/runs`

Same directive — the full, real, permanent factory-run history, never
overwritten. Optional `?strategyFamily=...` filter. Returns
`FactoryRunRecord[]`.

### `GET /api/sandbox/research-factory/runs/{run_id}`

Same directive, Section 18 — one real factory run's full detail. `404`
when no run with this id exists. Returns `FactoryRunRecord`.

### `GET /api/sandbox/research-factory/lineage/{strategy_family}`

Same directive, Section 18 — "inspect strategy lineage." Reuses the
already-real, already-persisted `research_iterations` (every factory
generation's own real `ResearchLoopIterationRecord` is appended there,
never stored twice) rather than a second lineage store. Returns
`ResearchLoopIterationRecord[]`, oldest first.

### `GET /api/sandbox/research-factory/stats`

Same directive, Section 20 — real, decomposable, factory-wide
observability across every persisted `FactoryRunRecord`. Never a
fabricated "AI quality score." Returns `FactoryStatsRead`.

### `GET /api/sandbox/failure-modes`

CEO directive "TradeTown — Statistical Validation + Research Failure
Taxonomy," Part 2. Returns `FailureModeCount[]` — a real, computed-fresh
clustering of `code`/`category`/`severity`/`occurrenceCount`/
`exampleStrategyNames` across every real `FailureCodeEntry` on every
`FailedStrategyArchiveEntry` in `state.strategy_failed_archive`, sorted
by real occurrence count descending. Empty when the archive holds no
entries or none carry any `failureCodes` yet (entries filed before this
taxonomy existed carry an honest empty list, never backfilled).

Each `ChallengerComparison` returned by the champion-challenger
endpoints above also now carries `statisticalComparison`
(`BootstrapComparisonResult | null` — a real IID percentile bootstrap
over each side's own closed-trade R-multiples: `evidenceState`
[`sufficient_evidence`/`insufficient_evidence`], `differenceCiLow`/
`differenceCiHigh`, `probabilityChallengerBetterPct`, `method`,
`resamples`, `limitationNote`; `null`/`insufficient_evidence` whenever
either side has fewer than 20 real closed trades — never a fabricated
CI), `classification`
(`both`/`statistically_supported_only`/`economically_meaningful_only`/
`neither`/`insufficient_sample` — purely informational, derived from
`statisticalComparison` plus the pre-existing real economic `verdict`;
never fed back into `verdict` itself or into `promote_challenger()`'s
refusal logic), and `researchFamilyExperimentCount`/
`multipleTestingRisk`/`challengerTuningVersion`/`highTuningExposure`
(also informational — multiple-testing exposure reuses the already-real
`OVERTESTED_FAMILY_THRESHOLD` from the Multiple-Testing Penalty pass;
tuning exposure flags a challenger at version 5+ of the same strategy
family).

### `POST /api/sandbox/register-researchable-strategy`

CEO directive "Strategy Intelligence + Live Strategy Attribution,"
Phase 1 — the real Strategy Lab ↔ `CompiledStrategyDefinition` identity
bridge. Body: `{ "name": "...", "description": "...", "sourceText": "...",
"timeframe": "1h", "createdBy": "quant", "focusCategory": "stock" }`.
Unlike `POST /register-strategy-version` (persists compiled rules
only), this also creates a real, new Strategy Lab `Strategy` — but only
when `sourceText` actually compiled (`status == "compiled"`); an
ambiguous/invalid text still returns its own real `definition` (with
real `ambiguities`/`detail` explaining why) and a `null` `strategy`,
never a fabricated link. Returns
`{ "definition": CompiledStrategyDefinition, "strategy": Strategy | null }`.
400 if a Strategy with this exact real name/slug already exists — this
endpoint is for genuinely new strategies; register a new version of an
existing strategy's rules via `POST /register-strategy-version` instead,
which stays linked to the same `Strategy.compiledDefinitionId`.

### `POST /api/sandbox/quant-research-lab/experiments`

CEO directive "Professional Quant Firm Phase," Feature 36 — files a
real, hypothesis-driven experiment into the permanent Quant Research
Lab archive. Body: `{ "definition": CompiledStrategyDefinition,
"hypothesis": "...", "researcherAgentId": "quant", "symbols": [...],
"timeframe": "...", "candlesPerSymbol": 6000 }` (`symbols`/`timeframe`/
`candlesPerSymbol` optional). Runs the same real
`run_research_experiment()` pipeline `POST /research-experiment` uses
(no duplicate backtest math), then permanently persists the result to
`GameSaveState.quantResearchExperiments` — a deliberate, disclosed
departure from this directive family's usual compute-fresh-never-persist
convention (see `QuantResearchExperiment`'s own docstring in
`app/schemas.py`). Returns `{ "experiment": QuantResearchExperiment,
"similarExperiments": QuantResearchExperimentSimilarity[],
"similarFailedStrategies": SimilarFailedStrategyMatch[],
"researchRelationship": ResearchRelationship }` —
`similarExperiments` surfaces any real near-duplicate already on file
(same compiled definition + timeframe, or overlapping hypothesis
wording) without blocking the new filing.

CEO directive "TradeTown — Research Engine Hardening +
Self-Improvement Implementation Pass," Phase 3 —
`similarFailedStrategies` extends that same real memory consultation
to the PERMANENT Failed Strategy Archive (previously never searched at
all): a real word-overlap match against each archived entry's own
`strategyName`/`whatFailed` text, carrying that entry's own real
`failureCodes`/evidence. `researchRelationship`
(`novel`/`similar_success`/`similar_failure`/`near_duplicate`/
`contradictory_evidence`) is a real, disclosed combination of both
similarity searches — purely informational, never blocks the filing
above, per the directive's own explicit "do NOT automatically reject a
strategy merely because something similar failed."

`QuantResearchExperiment.researchIntegrityFlag` (CEO directive
"TradeTown — 11/10 Strategy Factory + Ruthless Backtesting Engine,"
Section 12) — a real `normal`/`overtested` flag derived from
`familyExperimentCount` at `app/quant_research_lab.py`'s
`OVERTESTED_FAMILY_THRESHOLD` (5). `null` whenever
`familyExperimentCount` is itself `null`. Advisory only, never wired
into `outcome`.

### `GET /api/sandbox/quant-research-lab/experiments`

Same directive, Feature 36 — real search over every permanently-
persisted experiment (most recent first). Optional query params:
`symbol`, `definitionId`, `timeframe`, `agentId`, `outcome`
(`promising`/`rejected`/`inconclusive`). Returns
`QuantResearchExperiment[]`; an empty result is itself a real, honest
answer, never fabricated evidence.

### `GET /api/sandbox/quant-research-lab/similar?hypothesis=...&definitionId=...&timeframe=...`

Same directive, Feature 36 — a real, standalone duplicate check a
CEO/agent can run BEFORE spending compute on the `POST .../experiments`
endpoint above (which also runs this same check internally). Returns
`QuantResearchExperimentSimilarity[]`.

### `POST /api/sandbox/strategy-tournament`

CEO directive "Professional Quant Firm Phase," Feature 40 — the Quant
Strategy Tournament. Body: `{ "definitions": CompiledStrategyDefinition[],
"symbols": [...], "timeframe": "...", "candlesPerSymbol": 6000 }`
(at least 2 definitions required, `400` otherwise). Runs every candidate
through the same real `run_research_experiment()` pipeline once each,
then compares real results via named-slot superlatives
(`highestExpectancy`/`highestProfitFactor`/`highestSharpeRatio`/
`lowestMaxDrawdown`/`mostWalkForwardStable` — never a fabricated
composite score) and 9 staged elimination rounds (see
`app/strategy_tournament.py`'s own module docstring for the exact,
disclosed round-by-round rule — Round 7 "Portfolio interaction" is
still explicitly disclosed as partially blocked, since this codebase has
no cross-strategy portfolio-level backtest (shared capital, combined
position sizing, simultaneous drawdown), but now also returns
`pairCorrelations` — a real Pearson correlation between each candidate
pair's own walk-forward window expectancy sequences, per shared symbol
(reusing `app/portfolio_intelligence.py`'s `pearson_correlation()`);
`correlation` is `null` below 3 real paired windows, never a fabricated
`0.0`. CEO directive "Professional Quant Firm Phase 41-45," Feature 43
added Round 9 "Regime stability," reusing each candidate's own real
`regimeTrendBreakdown`/`regimeVolatilityBreakdown` (already computed by
the backtest, not re-derived) to eliminate only a confirmed
`no_validated_regime` `StrategyTournamentEntry.regimeStabilityVerdict`
— every real regime bucket that reached its own `enough_evidence`
sample-size bar showed zero or negative expectancy. `insufficient_data`
(no bucket ever reached that bar) survives — missing regime evidence is
never treated as a negative finding. This is evidence-based selection
within the Tournament itself, not a live "what regime is the market in
right now" gate on the trading pipeline — `TradeProposal` has no field
linking it back to a `CompiledStrategyDefinition`, so a live regime-
alignment check on actual trade decisions remains a disclosed
architectural gap this round does not close). Returns a
`StrategyTournamentResult`; `productionCandidates` is a real, cited
LABEL for CEO visibility only — never an autonomous production
promotion, never a bypass of this codebase's separate risk/governance
approval flow. Read-only, computed fresh every call (runs the full
research pipeline once per candidate — budget several seconds per
strategy); nothing here is persisted.

### `POST /api/constitution/propose` / `advance` / `decide`

v0.7 Feature 46 — the Company Constitution. All three return
`{ "constitution": { "articles": [...], "citations": [...], "amendments": [...] } }`.
`400` on any real precondition violation.

- `propose`: body `{ "title": "...", "text": "..." }`. Creates a real
  `ConstitutionAmendment` in `status: "proposed"`. `400` if either field
  is empty/whitespace-only, or another amendment with the same title is
  already pending.
- `advance`: body `{ "amendmentId": "..." }`. Requires `status ==
  "proposed"`. Runs the Founder debate, Coach evaluation, and the
  11-agent employee vote in one real step, setting `status: "voted"`.
- `decide`: body `{ "amendmentId": "...", "approve": true }`. Requires
  `status == "voted"`. The CEO's own real, manual, final call —
  deliberately never auto-resolved by Automation Mode (see
  `docs/Architecture.md`'s "Company Constitution" section). On approval,
  appends a real new `ConstitutionArticle` (next Roman numeral) to the
  permanent Articles list.

### `POST /api/risk-limits`

v0.7 Feature 49 — the first real CEO write path for `RiskLimits`
(previously display-only, with no endpoint at all); extended by v0.7
Chapter 57 with four of the Position Sizing engine's six new controls,
by v0.7 Chapter 58 with the Opportunity Gatekeeper's two new controls,
and by Design Bible Chapter 67 (TTOS) with the Safety Settings'
weekly/monthly loss limits. Body: any subset of `{ "dailyProfitTargetPct": 3.0,
"maxDailyLossPct": 5.0, "maxWeeklyLossPct": 10.0, "maxMonthlyLossPct": 15.0,
"maxTradesPerDay": 6, "riskPerTradePct": 2.0,
"maxOpenPositions": 8, "maxWeeklyDeploymentPct": 15.0,
"portfolioHeatCapPct": 40.0, "clearPortfolioHeatCap": false,
"cashReservePct": 10.0,
"tierAllocation": { "tier1Pct": 2.0, "tier2Pct": 5.0, "tier3Pct": 8.0, "tier4Pct": 10.0 },
"minTradeQualityScore": 70.0, "minExpectedValuePct": 0.0 }`
— every field optional, so a single call can update just one limit.
Returns `{ "riskLimits": { ... } }` with the full, current `RiskLimits`.
`400` if a provided value fails validation (most fields must be
positive, including `maxWeeklyLossPct`/`maxMonthlyLossPct`;
`cashReservePct` must be `>= 0` and `< 100`;
`minTradeQualityScore` must be `>= 0` and `<= 100`;
`minExpectedValuePct` has no range check — a CEO can legitimately set
it negative to relax the gate below "merely positive"; every
`tierAllocation` tier must be positive), or if no fields were provided
at all. `portfolioHeatCapPct` alone can't distinguish "field omitted"
from "CEO wants to disable the cap" (both look like `null`/absent), so
`clearPortfolioHeatCap: true` is the explicit way to set it back to
`null`; it wins even if `portfolioHeatCapPct` is also present in the
same body. `scalingAggressivenessPct`/`emergencyReductionHeatPct` are
not writable here — see `RiskLimits`' own note above for why. Takes
effect on the very next generated `TradeProposal` — see
`app/risk_engine.py`'s `evaluate_sentinel_risk`,
`app/position_sizing.py`'s `build_position_sizing`,
`app/opportunity_gatekeeper.py`'s `evaluate_opportunity`, and
`docs/Architecture.md`'s "Daily Trading Objectives" / "Institutional
Position Sizing" / "Institutional Trade Filter" sections for exactly
how each limit is enforced.

Design Bible Chapters 61/62/63 each added further optional fields to
this same endpoint's body (not all listed in the example above):
`minSimilarMatches`, `mistakeWarningSharePct`, `maxDecisionVaultEntries`,
`maxMemoryRecords`, `maxLimitedLiveCapital` (Chapters 61/62), and
`companyHealthExcellentThreshold`/`GoodThreshold`/`StableThreshold`/
`NeedsAttentionThreshold` (Chapter 63 — see
`app/company_health.py`'s `compute_company_health()`). The four Company
Health thresholds are validated together against the fully-merged
candidate (not just the fields a given call touches) to always stay
strictly descending; `400` with `"Company Health tier thresholds must
stay in strictly descending order..."` otherwise.

### `GET /api/risk-limits/portfolio-snapshot` / `GET /api/risk-limits/pretrade-decision` / `GET /api/risk-limits/portfolio-monte-carlo` / `GET /api/risk-limits/recovery-factor`

CEO directive "Portfolio Risk Engine + Firm-Wide Risk Governance" and
its follow-ups — four read-only, no-body composition reads over
already-real state (`app/portfolio_risk.py`, `app/portfolio_monte_
carlo.py`, `app/analytics.py`). None of the four mutate the save.

`portfolio-snapshot` returns one canonical, timestamped
`PortfolioRiskSnapshot`: equity/cash/exposure/leverage, the real
peak-to-trough drawdown, daily P&L, real correlated-exposure clusters,
the real daily circuit breaker tier, the real Emergency Stop flag, and a
derived `riskState` (`normal`/`warning`/`restricted`/`halted`) with
real, inspectable `riskStateReasons` — never a bare number with no
explanation.

`pretrade-decision` (query params `symbol`, `proposedValue`, both
required) returns one `PretradeRiskDecision`
(`verdict`: `approved`/`approved_with_reduction`/`rejected`/`halted`)
for a hypothetical candidate trade, composing every real Sentinel/
Guardian violation into a real `reasons`/`reasonCodes` list. Advisory
only — the real enforcement path (`app/gatekeeper.py`'s vote pipeline)
is the sole authority over whether a trade actually happens.

`portfolio-monte-carlo` returns `PortfolioMonteCarloResult | null` — a
real historical bootstrap over the account's own `PaperPortfolio.
trade_history` (see `app/portfolio_monte_carlo.py`'s module docstring
for the full methodology and why it's a different bootstrap than the
per-strategy one in `app/strategy_lab.py`). `null` when fewer than
`MIN_TRADES_FOR_PORTFOLIO_MONTE_CARLO` (10) real closed trades exist —
never a bootstrap from too thin a sample. The result's
`probabilityOfRuinPct`/`capitalSurvivalPct` are measured against the
CEO's own real, currently-configured `RiskLimits.maxDrawdownPct`
(disclosed as `ruinThresholdPct` on the result, never a hidden or
fabricated bar); `medianReturnPct`/`returnRangeLowPct`/
`returnRangeHighPct`/`medianMaxDrawdownPct`/`worstCaseDrawdownPct`/
`probabilityOfProfitPct`/`valueAtRisk95Pct`/`valueAtRisk99Pct`/
`conditionalValueAtRisk95Pct`/`conditionalValueAtRisk99Pct` mirror the
same real percentile/tail-mean reads `StrategyMonteCarloResult` already
exposes, off this bootstrap's own sorted final-return array. Computed
fresh on every call (the same CAGS convention `PortfolioIntelligence`
already uses) — no new `GameSaveState` field, deterministically seeded
so identical real trade history always reproduces an identical result.

`recovery-factor` (CEO directive "Professional Quant Trading Core,"
Phase B P2 item) returns a `RecoveryFactorRead` — a real, standard quant
performance ratio (the same real family as the Calmar ratio): real net
profit divided by the account's own worst real peak-to-trough drawdown,
in dollars, both measured against today's real live equity (see
`app/analytics.py::compute_recovery_factor()`). Fields:
`startingBalance`, `currentEquity`, `netProfitUsd`, `maxDrawdownUsd`,
`maxDrawdownPct`, `recoveryFactor` (`null` — a real "undefined," never
a fabricated infinity — when the account has never drawn down),
`summary`, `computedAt`.

### `POST /api/goals/create` / `POST /api/goals/cancel`

Design Bible Chapter 64 — the CEO's Goal write path (`app/goals.py`).
`create`'s body: `{ "title": "Reach elite Company Score", "category":
"growth", "targetMetric": "company_score_overall", "targetValue": 85.0,
"deadlineSimDay": null }`. `category` is one of `growth`/`risk`/
`research`/`trading`/`operations`; `targetMetric` is one of
`company_health_combined`/`company_score_overall`/`portfolio_return_pct`/
`academy_level` — each maps to one real, already-computed number (see
`app/goals.py`'s `resolve_metric_value()`). `400` for an empty/too-long
title, a non-positive target, a target above that metric's own real
ceiling (100 for the two composite scores, 5 for Academy level,
uncapped for portfolio return), or a deadline that isn't a future sim
day. Both endpoints return `{ "goals": [ ... ] }`, the full current list.
`cancel`'s body: `{ "goalId": "goal-12-14-0-3" }`; `400` for an unknown
id or a goal that isn't currently `active`. Real progress is never sent
by the client — `app/nexus.py`'s `tick()` recomputes every active
goal's `currentValue`/`progressPct`/`status` every tick via
`tick_goals()`, transitioning it to `completed` (target reached) or
`expired` (deadline passed unmet), both permanent per
`app/hall_of_fame.py`'s "a crossed milestone stays crossed" convention.
Capped at `MAX_GOALS = 20`, oldest evicted first, same as every other
real CEO-authored list in this codebase.

### `GET /api/goals/priorities`

Design Bible Chapter 64's Executive Priority Engine — read-only, no
body. Returns `[{ "goalId": "goal-12-14-0-3", "score": 84.2,
"remainingPct": 42.1, "daysRemaining": 2 }, ...]`, one `GoalPriority`
per ACTIVE goal (non-active goals are excluded entirely), highest score
first. `daysRemaining` is `null` for a goal with no real deadline —
scored purely by `remainingPct` in that case. Computed fresh per
request from the current real goals and sim day
(`app/goals.py`'s `rank_goals_by_priority()`/`compute_goal_priority()`)
— never a second persisted copy, the same convention as
`GET /api/decision-vault/quality-score`.

### `GET /api/goals/allocations`

Design Bible Chapter 64's Resource Allocation (fourth pass) —
read-only, no body. Returns `[{ "goalId": "goal-12-14-0-3", "score":
84.2, "allocationPct": 63.4 }, ...]`, one `GoalAllocation` per ACTIVE
goal, same order as `GET /api/goals/priorities` (score descending).
`allocationPct` is each goal's real `score` normalized against the sum
of every active goal's score, so the full list always sums to ~100%
(falls back to an even split across goals only if every active goal's
score is 0). This is a recommend-only share of executive ATTENTION, not
a claim about real capital — a `Goal` tracks a company-wide metric, not
a capital pool, so nothing here moves money or reads/writes
`PaperPortfolio`/`PaperBroker`. Computed fresh per request from the
current real goals and sim day (`app/goals.py`'s
`compute_resource_allocation()`, itself built directly on
`rank_goals_by_priority()`) — never a second persisted copy.

### `GET /api/institutional-memory/retrieve`

CEO directive "Features 26-30: Agent Intelligence, Learning &
Institutional Memory System," Feature 26 — read-only, no body. Query
params `source` (`InstitutionalMemorySource`, optional) and
`marketRegime` (`MarketEnvironmentRegime`, optional) narrow the search.
Returns the single most relevant+corroborated *active*
`InstitutionalMemoryEntry` matching the query, or `null` — honestly NOT
ENOUGH EVIDENCE — when nothing on file matches, or when the single best
match's relevance has decayed too far to responsibly surface. Confidence
and relevance are recomputed fresh against the full current memory list
on every call (`app/institutional_memory.py`'s
`retrieve_relevant_memory()`), never trusted stale from whatever was
stamped when the entry was written. The full list is also broadcast on
every WS tick (`institutionalMemory`) — this endpoint is the one query
that broadcast can't offer.

### `GET /api/performance-reviews/{agent_id}/latest`

CEO directive "Features 26-30: Agent Intelligence, Learning &
Institutional Memory System," Feature 27 — read-only, no body. Returns
the most recent real `AgentPerformanceReview` on file for `agent_id`, or
`null` if none has been generated yet (reviews are only generated
weekly — see `app/nexus.py`'s tick). The full list is also broadcast on
every WS tick (`agentPerformanceReviews`) — this endpoint is a
convenience for fetching one agent's latest review directly.

### `GET /api/performance-reviews/{agent_id}/history`

CEO directive "Professional Quant Firm Phase 41-45," Feature 44 —
read-only, no body. Returns every stored `AgentPerformanceReview` for
`agent_id` (oldest first), each paired with a real, freshly computed
`AgentReviewDataSplit` (`training`/`validation`/`test`/`live_paper`) as
an `AgentPerformanceReviewHistoryEntry`. The split is a real,
deterministic, chronological classification (`app/performance_
review.py`'s `classify_review_data_splits()`) — never randomly
shuffled, mirroring `app/walk_forward.py`'s own window discipline
applied to agent-level evidence: the single most recent review reads
`live_paper` (a fresh, unconfirmed observation), the review it
superseded reads `test`, the next two read `validation`, everything
older reads `training`. Recomputed fresh from the full history on every
call — never stored on the review itself — so a review's label
correctly ages as later reviews accumulate. A deliberately preventive
read: nothing in this codebase today feeds `AgentPerformanceReview`
back into any live weighting or promotion decision, so this exists to
give a future evidence-based promotion system a real way to require
evidence to have aged past `live_paper` before citing it, closing the
leakage risk before it can be introduced.

### `GET /api/agents/trading-status`

CEO directive "Command Center + Professional Quant Trading Firm
Upgrade," Phase 2 (AI Desk / Agent Decision Explainability) —
read-only, no body. Returns an `AgentTradingStatusRead[]`, one per real
agent (`AGENT_IDS`, all 15), computed fresh every call by `app/
agent_trading_status.py`'s `compute_agent_trading_status()`. Every
field is grounded in a real, already-existing signal, checked in this
priority order: Emergency Stop active → `status: "risk_blocked"`
(company-wide, every agent); a real `AnalystVote` this agent cast
sitting on a currently pending `TradeProposal` → `"waiting"`, `detail`
is that vote's own real `reasoning` text verbatim; a real
`ResearchItem` assigned to this agent (`app/research.py`'s
`RESEARCHER_IDS`) queued or in progress → `"scanning"`, `detail` is
that item's own real `summary`; one of the six agents `app/
executive.py`'s vote generation can ever attribute a vote to
(scout/atlas/echo/nova/sentinel/pulse) with nothing real active →
`"idle"`; every other agent → `"not_trading_role"`, `detail` cites
their own real `AGENT_PROFILES` `occupation` string. No "next
condition required" field exists — this codebase has no live
per-symbol forecasting mechanism to back one honestly; the real
existing "wait" vote reasoning already tends to name what's currently
missing, surfaced as `detail` instead. Not persisted, not
WS-broadcast — an on-demand read, same convention `GET /api/
performance-reviews/{agent_id}/history` above uses.

### `GET /api/skill-profiles/{agent_id}/latest`

CEO directive "Features 26-30: Agent Intelligence, Learning &
Institutional Memory System," Feature 28 — read-only, no body. Returns
the most recent real `AgentSkillProfile` on file for `agent_id`, or
`null` if none has been generated yet (profiles are only generated
weekly — see `app/nexus.py`'s tick, immediately after the Agent
Performance Review loop). The full list is also broadcast on every WS
tick (`agentSkillProfiles`) — this endpoint is a convenience for
fetching one agent's latest profile directly. Note: `GET /api/load`
deliberately returns this field empty (it's an archive module — see
that endpoint's own docstring); use this endpoint, the WS broadcast, or
`GET /api/load/archive/knowledge_archive` for real data.

### `GET /api/predictions/{agent_id}`

CEO directive "Features 26-30: Agent Intelligence, Learning &
Institutional Memory System," Feature 29 — read-only, no body. Returns
every real `PredictionRecord` this agent is a real supporting agent on
(pending and resolved both included), oldest first. Note: `app/
reasoning_lab.py` carries an unrelated older "v0.7 Feature 29" tag (a
disclosed naming collision, see that module's own docstring) — this
endpoint is the CEO-directive Feature 29. The full list is also
broadcast on every WS tick (`predictionRecords`). Note: `GET /api/load`
deliberately returns this field empty (it's an archive module — see
that endpoint's own docstring); use this endpoint, the WS broadcast, or
`GET /api/load/archive/knowledge_archive` for real data.

### `GET /api/predictions/calibration/brier`

CEO directive "Professional Quant Trading Core," Phase B P2 item — a
real Brier-score calibration read (`app/prediction_tracking.py::
compute_brier_calibration()`) over the same Prediction Records ledger
above, computed fresh per request. Returns a `BrierCalibrationSummary`:
`resolvedPredictionCount`, `brierScore` (`null` below
`MIN_PREDICTIONS_FOR_BRIER_VERDICT` (10) real resolved predictions —
0.0 = perfect calibration, ~0.25 = a coin-flip forecaster, 1.0 = worst
possible), `evidenceState` (`"sufficient_evidence"` /
`"not_enough_data"`), `buckets` (a real reliability-diagram breakdown
by stated-confidence range — `rangeLowPct`/`rangeHighPct`/
`predictedCount`/`realAccuracyPct` (`null` below
`MIN_PREDICTIONS_FOR_BUCKET_VERDICT` (3) real observations in that
bucket)/`avgStatedConfidencePct`), a plain-language `summary`, and
`updatedAt`. No new `GameSaveState` field, no gate, no automatic action.

### `GET /api/predictions/calibration/brier/by-agent`

CEO directive "Professional Quant Portfolio Intelligence + Alpha
Research Engine," Phase 7 (Agent Calibration) — the same real Brier
calibration above (`app/prediction_tracking.py::
compute_agent_brier_calibration()`), broken out per real named agent.
Returns `list[AgentBrierCalibration]`, one entry per `AGENT_IDS` value:
`agentId` plus a `calibration: BrierCalibrationSummary` computed only
over the real predictions that agent is an actual `attributedAgents`
member of (a jointly-attributed prediction counts toward every agent
who backed it). Same `evidenceState`/`MIN_PREDICTIONS_FOR_BRIER_VERDICT`
floor as the desk-wide endpoint, evaluated independently per agent.
Computed fresh per request, no new `GameSaveState` field.

### `GET /api/failures/{agent_id}`

CEO directive "Features 26-30: Agent Intelligence, Learning &
Institutional Memory System," Feature 30 — read-only, no body. Returns
every real `FailureClassification` this agent is a real supporting
agent on, oldest first. The full list is also broadcast on every WS
tick (`failureClassifications`). Note: `GET /api/load` deliberately
returns this field empty (it's an archive module — see that endpoint's
own docstring); use this endpoint, the WS broadcast, or
`GET /api/load/archive/knowledge_archive` for real data.

### `GET /api/trades/exit-efficiency`

CEO directive "Professional Trading Firm Transformation" — Post-Trade
Review, Exit Efficiency (`app/exit_efficiency.py`). Read-only, computed
fresh per request over the already-real `trade_history` — no new
`GameSaveState` field. Returns an `ExitEfficiencySummary`: `reads:
TradeExitEfficiency[]`, one per closed `PaperTrade`, each with
`pnlPct`/`maePct`/`mfePct` (mirrored verbatim) and `capturePct` — a
real, continuous "Edge Ratio": `(pnlPct − maePct) / (mfePct − maePct) ×
100`, honestly covering wins and losses alike (100 = closed at the best
point the trade's own real observed range ever reached, 0 = the
worst). The effective range is widened to also include `pnlPct` itself
(`min(maePct, pnlPct)`..`max(mfePct, pnlPct)`) since the real close
price can land slightly beyond the last `mark_to_market()`-tracked
watermark — confirmed live, not hypothetical. `evidenceState`
(`efficient_exit`/`average_exit`/`poor_exit`/`not_enough_data` —
`not_enough_data` only when the RAW `maePct == mfePct == 0.0`, genuinely
ambiguous between "never moved" and "never tracked," never guessed at
either way). Summary counts (`avgCapturePct`, `efficientExitCount`,
`averageExitCount`, `poorExitCount`, `notEnoughDataCount`, `updatedAt`)
are pure tallies over `reads`. This is a genuinely new, third
post-trade review axis — distinct from and never touching Discipline's
outcome-blind process score (`GET` via the WS `discipline_reviews`
broadcast) or `GET /api/failures/{agent_id}`'s WHY-the-thesis-failed
classification above.

### `GET /api/trades/performance-by-strategy`

CEO directive "Live Trade → Strategy Provenance," Phase 4 — the
Strategy Exposure view (`app/performance_attribution.py`'s
`compute_strategy_performance()`). Read-only, computed fresh per
request over `state.paper_portfolio.trade_history` joined against
`state.decision_vault` — no new `GameSaveState` field. Returns a
`StrategyPerformanceSummary`: `reads: StrategyPerformanceRead[]`, one
per real strategy id the CEO has actually selected via `POST
/api/executive/decide`'s `strategyId` field at least once (12-metric
shape shared with `SymbolPerformanceRead`/`SessionPerformanceRead`/
`RegimePerformanceRead` — win rate, expectancy, profit factor, avg
winner/loser, avg MAE/MFE, best/worst trade, `evidenceState`), sorted
by `totalPnl` descending.

Only trades whose Decision Vault entry carries a real, CEO-selected
`strategyId` (`strategyProvenanceState == "known"`, see `app/
trade_attribution.py`) are ever grouped. Every other trade is excluded
and counted under one of two distinct, honestly-separate reasons —
never silently dropped, never folded together, never fabricated into a
strategy it wasn't actually attributed to: `tradesExcludedNoStrategy
Selected` (a real Decision Vault entry exists, but the CEO never picked
a strategy — the honest majority of trades, especially any trade
closed before this feature existed) and `tradesExcludedNoVaultEntry`
(no matching vault entry at all — the same disclosed eviction edge
case every other `performance-by-*` endpoint already reports).

### `GET /api/trades/{trade_id}/strategy-rule-snapshot`

CEO directive "Complete Trade Provenance," Part 1 + Part 2 — resolves
one real closed trade's strategy-rule snapshot back into the exact
immutable `CompiledStrategyDefinition` (rules, stop, target, timeframe)
that was active the instant the CEO picked that strategy at decision
time (`app/trade_attribution.py`'s `resolve_trade_strategy_rule_
snapshot()`). Returns a `TradeStrategyRuleSnapshot`: `tradeId`,
`strategyId`, `strategyProvenanceState` (`known`/`unknown`/
`unavailable`, same three-state meaning as every other strategy-
provenance field in this API), `compiledDefinition` — `null` whenever
`strategyProvenanceState != "known"`, or the picked Strategy had no
compiled rules yet, never fabricated. 404 only when `trade_id` doesn't
match any real trade in `trade_history` — a real trade with no strategy
attribution still returns 200 with an honest null `compiledDefinition`.
Because `compiled_strategy_versions` is real and append-only, a later
edit to the same strategy never changes what an already-decided trade's
snapshot resolves to. Computed fresh per request; no new `GameSaveState`
field.

CEO directive "Professional Quant Trading Core," Phase B P2 item
(strategy-compliance-at-execution wiring) added a `compliance` field —
`null` under the exact same conditions `compiledDefinition` is `null`.
When present, a `StrategyComplianceRead`: `verdict`
(`"compliant"`/`"stop_violated"`/`"not_checkable"`), `stopCheckDetail`,
`targetCheckDetail` (purely informational — reaching/not reaching a
target is never itself a violation). Real and checkable ONLY when the
strategy's stop is `fixed_percent` — `chandelier`/`swing_level` stops
honestly return `"not_checkable"`, since this paper broker never places
a real stop-loss order and this codebase's mock candle data cannot
reliably reconstruct a past historical stop level after the fact. See
`app/trade_attribution.py`'s `evaluate_strategy_compliance()` for the
full real methodology.

### `GET /api/trades/performance-by-strategy-session`

CEO directive "Live Trade → Strategy Provenance," Phase 6 — the one
real strategy×session axis that didn't exist yet
(`compute_strategy_session_performance()`). Same real Decision Vault
join as `performance-by-strategy` above, grouped on the
`(strategyId, session)` pair instead. Returns a
`StrategySessionPerformanceSummary`: `reads:
StrategySessionPerformanceRead[]` (same 12-metric shape, plus
`strategyId`/`session`), sorted by `totalPnl` descending, with the same
two distinct `tradesExcludedNoStrategySelected`/
`tradesExcludedNoVaultEntry` counts. Computed fresh per request; no new
`GameSaveState` field.

### `GET /api/trades/performance-by-strategy-regime`

CEO directive "Complete Trade Provenance," Part 12 — the regime
counterpart to `performance-by-strategy-session` above
(`compute_strategy_regime_performance()`). Same real Decision Vault
join, grouped on the `(strategyId, regime)` pair instead. Returns a
`StrategyRegimePerformanceSummary`: `reads:
StrategyRegimePerformanceRead[]` (same 12-metric shape, plus
`strategyId`/`regime`), sorted by `totalPnl` descending, with the same
two distinct `tradesExcludedNoStrategySelected`/
`tradesExcludedNoVaultEntry` counts. Computed fresh per request; no new
`GameSaveState` field.

### `GET /api/trades/strategy-live-correlation`

CEO directive "Complete Trade Provenance," Part 14 — real strategy-pair
correlation over LIVE trade returns (`compute_strategy_live_
correlation()`), the live counterpart to `app/strategy_tournament.py`'s
backtest-only `StrategyPairCorrelation`. Aggregates each strategy's own
real, CEO-selected trades to one average `pnlPct` per real in-game sim
day it had a closed trade, then correlates two strategies' daily-return
series over shared days only via the same `pearson_correlation()` the
backtest version reuses. Returns a `StrategyLiveCorrelationSummary`:
`reads: StrategyLiveCorrelationRead[]` (`strategyIdA`/`strategyIdB`/
`correlation`/`pairedDays`/`detail`) for every pair of strategies with
at least one live trade each — `correlation` is `null` (never a
fabricated `0.0`) below 3 real paired days. Computed fresh per request;
no new `GameSaveState` field.

### `GET /api/trades/unattributed-monitor`

CEO directive "Complete Trade Provenance," Part 17 — a dedicated,
visible data-quality diagnostic (`compute_unattributed_trade_
monitor()`). Returns an `UnattributedTradeMonitor`: `totalTrades`,
`unattributedCount`/`unattributedPct`, `unknownCount` (a real decision
on record, no strategy picked) and `unavailableCount` (no matching
decision at all) counted separately — never folded together —
`trend` (`improving`/`worsening`/`stable`/`not_enough_data`, a real
comparison of the attribution rate between the first and second half
of trade history by real `closedSimMinutes` order), and a `detail`
string summarizing all of the above in one sentence. Computed fresh
per request; no new `GameSaveState` field.

### `GET /api/trades/data-quality-monitor`

CEO directive "Complete Trade Provenance," Part 18 —
(`compute_data_quality_monitor()`) covers 4 of the directive's 9 named
categories; the other 5 are already surfaced elsewhere (3 by
`TradeAttributionRecord.evidenceState`/`TradeExitEfficiency.
evidenceState`) or don't apply to this codebase's actual data shape —
see `app/data_quality_monitor.py`'s own module docstring for the full
reasoning. Reports only, never repairs or backfills. Returns a
`DataQualityMonitor`: `issues: DataQualityIssue[]` (one per
non-empty category — `category`/`count`/`detail`/`exampleIds`, capped
at 5 real record ids per category), `totalIssueCount` (the true sum
across categories, never capped), and a `detail` summary string. The
four categories checked: `impossible_timestamps` (a closed trade whose
`closedSimMinutes` precedes its own `openedSimMinutes`),
`dangling_strategy_reference` (a `CeoDecisionRecord.strategyId` with no
matching real `Strategy`), `missing_decision_time_context` (a real
buy/sell decision with no `decisionSession`, expected only pre-Part-8),
`missing_strategy_rule_snapshot` (a decision with a `strategyId` but no
`strategyCompiledDefinitionId`). One real record can honestly trip more
than one category at once — both are counted, never collapsed.
Computed fresh per request; no new `GameSaveState` field.

### `GET /api/trades/strategy-live-vs-backtest`

CEO directive "Live Trade → Strategy Provenance," Phase 5 — does a
strategy's real live performance match what its own real backtest
evidence claimed? `compute_strategy_live_vs_backtest()` joins the
already-real `compute_strategy_performance()` output against the
strategy's own latest `StrategyHealthAssessment` (Feature 52 Part 2) —
computes no new trade-level statistics. Returns a
`StrategyLiveVsBacktestSummary`: `reads:
StrategyLiveVsBacktestRead[]`, one per strategy with at least one real
live (known-provenance) trade. Compares `winRatePct` only — the one
metric both sides express on the same real 0-100 scale (expectancy is
deliberately never compared: live is in percent, backtest is in
R-multiples — different units). `verdict` is one of
`consistent_with_backtest` / `diverging_from_backtest` (gap ≥ 15
percentage points, a disclosed, arbitrary threshold — see the module's
own `WIN_RATE_DIVERGENCE_THRESHOLD_PCT`) / `not_enough_live_data` (fewer
than 3 live trades) / `no_backtest_health_on_record` (the strategy has
never completed a Market Simulation run). Computed fresh per request;
no new `GameSaveState` field.

### `GET /api/trades/strategy-trading-diagnostics`

CEO directive "Live Trade → Strategy Provenance," Phase 9 — "why isn't
this strategy trading live?" answered per strategy
(`compute_strategy_trading_diagnostics()`), the one real gap
`pipeline-health` below never covers (confirmed: zero references to
"strategy" anywhere in that module before this endpoint). Returns a
`StrategyTradingDiagnosticSummary`: `reads:
StrategyTradingDiagnosticRead[]`, exactly one per real strategy, each
with a `reason` — `trading_live` (has a real live trade already),
`blocked_by_regime_today` (in `StrategyMatch`'s own
`avoidedStrategyIds` for today's real regime), `eligible_but_never_
selected` (in `recommendedStrategyIds`, zero live trades), or
`no_backtest_evidence_yet` (no `StrategyReport` on file at all). Built
entirely from two already-real, already-computed sources
(`compute_strategy_match()` and `compute_strategy_performance()`) —
diagnostic only, feeds no score, gates nothing. Computed fresh per
request; no new `GameSaveState` field.

### `GET /api/trades/pipeline-health`

CEO directive "Professional Quant Firm Phase 41-45," Critical Task
#0 — real, diagnostic-only funnel telemetry (`app/trade_pipeline_
health.py`), computed fresh per request from already-persisted state.
No new `GameSaveState` field, and it feeds no scoring formula anywhere
— it exists purely to make the real trade-flow funnel visible, and to
distinguish "no valid trade existed" from "the system failed to
execute a valid trade." Returns a `TradePipelineHealthSnapshot`:
`completedResearchSignals`/`pendingProposals`/`resolvedDecisions`/
`tradesExecuted`/`noTradeDecisions` funnel counts, real
`opportunityRejections`/`gatekeeperRejections` totals, a real tally of
`NoTradeReasonCode` occurrences across both rejection lists
(`reasonCodeBreakdown`), and a `dataHonestyNote` disclosing which
counts (research history, decision history, opportunity/gatekeeper
rejection logs) are capped rolling windows rather than full-lifetime
totals — never a fabricated whole-game total from a source list this
codebase only keeps a recent slice of.

Every `RiskWarning`, `GatekeeperCheck`, `GatekeeperRejection`, and
`OpportunityRejection` this endpoint's underlying data draws on also
now carries a real `code`/`reasonCodes` field from the same
directive's `NoTradeReasonCode` taxonomy (41 values as of CEO directive
"Portfolio Construction, Capital Allocation & Execution Realism," `app/
schemas.py` — most recently `correlated_exposure_too_high`, Phase 4's
real pre-proposal Pearson correlation gate; a prior value,
`session_regime_unfavorable_evidence`, was added by CEO directive
"Command Center + Professional Quant Trading Firm Upgrade" to close the
taxonomy's own previously-disclosed SESSION_FILTER gap with a real
evidence-based check; see `app/opportunity_gatekeeper.py`'s module
docstring) — each grounded in an exact, cited line of the real
rejection logic that produced it (`app/risk_engine.py`, `app/
gatekeeper.py`, `app/opportunity_gatekeeper.py`), never invented.
`GatekeeperCheck.code` is
optional because a handful of existing tests construct synthetic
`GatekeeperCheck` fixtures (arbitrary IDs, for unrelated
control-effectiveness/process-adherence scoring tests) that have no
real taxonomy code to cite.

### `GET /api/trades/opportunity-feed`

CEO directive "Professional Quant Trading Core," Rule 25/26 — the CEO
Opportunity Feed (`app/opportunity_feed.py`), computed fresh per
request. A Phase A audit found the scoring/evidence a feed like this
needs already computed live every tick with zero UI/API surface
anywhere (`OpportunityRejection`'s own real fields, `TradeProposal`'s
already-ranked Priority Score) — this endpoint adds no new scoring, no
new gate, and no new `GameSaveState` field, it only ranks and surfaces
what already exists. Returns an `OpportunityFeed`: `bestOpportunities`
(the CEO's pending `TradeProposal` queue, already ranked by real
Priority Score, each carrying its real `decisionScore`/
`expectedValuePct` when a linked `WarRoomSession` exists, `status:
"eligible"` since every one already cleared `evaluate_opportunity()`'s
real gate), `watchlist` (research still `in_progress`, `status:
"insufficient_evidence"`, no score attached since none exists yet),
`avoid` (the most recent real `OpportunityRejection`s, `status:
"not_eligible"`, each with its own real reasons/decision score/EV at
rejection time), and a `dataHonestyNote` disclosing the honest scope
boundary: this is NOT a whole-universe proactive scanner — a symbol
with no real candidate, rejection, or in-progress research record
simply isn't listed, never fabricated as if it had been evaluated.

### `GET /api/trades/watchlist-eligibility`

CEO directive "Professional Quant Trading Core," Phase B P2 item — a
formal, standing per-symbol Watchlist Eligibility Tier
(`app/watchlist_eligibility.py`), computed fresh per request. Distinct
from the Opportunity Feed above's per-candidate status: this is a real
classification over a symbol's WHOLE trade history, reusing
`app/performance_attribution.py`'s own real per-symbol win-rate/
expectancy/profit-factor. Returns a `WatchlistEligibilitySummary`:
`reads` (one `WatchlistEligibilityRead` per symbol currently on the
watchlist — `symbol`, `tier` (`"proven"`/`"developing"`/`"unproven"`/
`"cautionary"`), `tradeCount`, `winRatePct`/`expectancyPct`/
`profitFactor` (all `null` for a symbol with zero real trades),
`rejectionCount` (real `OpportunityRejection` count, informational
only), `detail` (a real, disclosed sentence)) and `updatedAt`. `proven`
requires ≥3 real trades, ≥55% win rate, and positive expectancy;
`cautionary` requires the same ≥3-trade minimum with <40% win rate or
negative expectancy; `unproven` is zero real trades; everything else is
`developing`. No new `GameSaveState` field, no gate, no automatic
action — purely a read.

### `GET /api/market/technical-analysis?symbol=...&timeframe=1h&limit=100`

CEO directive "Professional Trading Firm — Market-Analysis Knowledge +
Session Intelligence Expansion," Phases 1-3 — one bundled real
"technical desk briefing" for a symbol (`app/technical_analysis.py`).
Computed fresh per request over the same real (mock) candle series `GET
/api/market/candles` returns for the same `symbol`/`timeframe`/`limit`.
`400` for an unsupported timeframe or unknown symbol, same as
`/candles`. Returns a `TechnicalAnalysisRead`:

```json
{
  "symbol": "NEXA",
  "indicators": {
    "symbol": "NEXA",
    "sma20": 101.4,
    "ema20": 101.9,
    "rsi14": 62.3,
    "macdLine": 0.8,
    "macdSignal": 0.5,
    "macdHistogram": 0.3,
    "stochasticPercentK": 74.0,
    "stochasticPercentD": 68.0,
    "atr14": 1.2,
    "vwap": 101.1,
    "parabolicSar": 99.8,
    "parabolicSarTrend": "up",
    "supertrend": 100.2,
    "supertrendTrend": "up",
    "detail": "3 of 3 headline indicators computable from 100 real candle(s) on file."
  },
  "swingStructure": { "symbol": "NEXA", "labels": ["higher_low", "higher_high"], "detail": "..." },
  "fairValueGaps": { "symbol": "NEXA", "gaps": [], "detail": "..." },
  "candlestickPatterns": { "symbol": "NEXA", "patterns": [], "detail": "..." },
  "fibonacci": { "symbol": "NEXA", "swingHigh": 105.0, "swingLow": 98.0, "levels": [{"ratio": 0.618, "price": 100.7}], "detail": "..." },
  "orderBlock": { "symbol": "NEXA", "direction": "none", "priceHigh": null, "priceLow": null, "timestamp": null, "detail": "..." },
  "supportResistance": { "symbol": "NEXA", "levels": [{"price": 99.0, "touches": 3, "role": "support"}], "detail": "..." },
  "chartPatterns": { "symbol": "NEXA", "timeframe": "1h", "patterns": [], "detail": "..." }
}
```

Every indicator/pattern field is `None`/empty (never a fabricated
value) below that concept's own real minimum bar count — see
`app/technical_indicators.py` and `app/technical_patterns.py`'s own
module docstrings for each concept's exact real definition. None of
these values are wired into `app/research.py`'s confidence gauge or any
live trade decision — informational only. `supportResistance` (CEO
directive "Professional Quant Trading Firm — Quant Intelligence + Market
Analysis Completion Phase," Phase B) clusters the same real swing-high/
low series `swingStructure` already computes into price bands (≥2
touches within 0.5% of the cluster's own running mean, capped at 8
levels), classifying each as `support`/`resistance` against the current
close — never a second swing detector. `parabolicSar`/`supertrend`
(that same directive's "Next Research + Validation Pass") are real,
deterministic, unit-tested indicator values — deliberately grouped into
the SAME `trend` evidence family as EMA/SMA by `GET
/api/market/evidence-confluence` below, never counted as new
independent evidence. `chartPatterns` is real double top/bottom and
trendline-break detection (`app/technical_patterns.py::
detect_chart_patterns()`) — only ever populated once a real neckline/
trendline break has already been confirmed by a later real close, never
a still-forming shape; head & shoulders/triangles/wedges/rectangles/
channels remain a disclosed, real gap.

### `GET /api/market/evidence-confluence?symbol=...&timeframe=1h&limit=100`

CEO directive "Professional Quant Trading Firm — Quant Intelligence +
Market Analysis Completion Phase," Phase D (`app/evidence_confluence.py`).
Groups the same real indicator/pattern signals `technical-analysis`
computes into evidence families (`trend`/`momentum`/`volume`/
`liquidity`/`price_structure`/`pattern`) and distinguishes the RAW signal
count from the count of INDEPENDENT families agreeing — deliberately one
layer below `app/signal_correlation.py`, which already covers redundancy
across the six analyst votes, not the raw indicator layer. Returns an
`EvidenceConfluenceRead`:

```json
{
  "symbol": "NEXA",
  "families": [
    { "family": "trend", "signals": [{"name": "price_vs_ema20", "family": "trend", "direction": "bullish", "detail": "..."}], "netDirection": "bullish", "detail": "..." }
  ],
  "rawSignalCount": 7,
  "independentFamilyCount": 3,
  "majorityDirection": "bullish",
  "agreeingFamilies": ["trend", "momentum", "volume"],
  "detail": "..."
}
```

`netDirection` per family is `"bullish"`/`"bearish"` only when every
directional signal in that family agrees; any real internal
disagreement reads `"neutral"` rather than being silently resolved
toward the majority. `rawSignalCount` counts only signals whose own
direction matches `majorityDirection` (mirroring
`signal_correlation.py`'s `naiveConfirmationCount` semantics); a raw
count well above `independentFamilyCount` is the whole point of this
endpoint — it means several of those "confirmations" are really the
same underlying evidence read more than once. Never wired into any
live trade decision — informational only.

### `GET /api/market/session-range?symbol=...&session=asian&timeframe=1h&limit=100`

Phase 4 of the same directive — a symbol's real high/low and retest
status for one trading session (`asian`/`london`/`london_ny_overlap`/
`new_york`/`ny_lunch_hour`/`market_open`/`market_close`/`closed`),
computed only from that session's own real candles
(`app/technical_patterns.py::compute_session_range()`, which reuses
`app/market_intelligence.py`'s existing session-boundary detection —
never a second session engine). Returns a `SessionRangeRead`:

```json
{
  "symbol": "NEXA",
  "session": "asian",
  "rangeHigh": 105.0,
  "rangeLow": 98.0,
  "retested": true,
  "detail": "Asian session real range: 98.0000 - 105.0000 across 12 real candle(s). A later candle traded back into this range."
}
```

`rangeHigh`/`rangeLow` both read `0.0` (never a fabricated range) when
no real candle in the fetched window falls inside that session's UTC
hours.

### `GET /api/market/regime-reconciliation`

Design Bible Chapter 65's Regime Reconciliation — read-only, no body.
Returns one `RegimeReconciliation`: `environmentRegime`/`environmentLabel`
(from `app/market_environment.py`'s 5-way classifier),
`intelligenceRegime`/`intelligenceLabel`/`qualityTier`/`confidencePct`
(from `app/market_intelligence.py`'s 13-way classifier and its
`MarketQualityScore`), `agreement` (`"aligned"` or `"diverging"` — is
the intelligence engine's live regime a real member of the environment
regime's bucket in `REGIME_CONSISTENCY_MAP`), `posture`
(`"cautious"`/`"normal"`/`"opportunistic"`, a read-only recommendation
derived from `qualityTier` + `confidencePct` — never written to
`RiskLimits`), and a plain-language `rationale`. Computed fresh per
request from the current real `MarketEnvironmentState`/
`MarketIntelligenceState` (`app/regime_reconciliation.py`'s
`compute_regime_reconciliation()`) — never a second persisted copy, the
same convention as `GET /api/goals/priorities`.

### `GET /api/market/session-evidence`

CEO directive "Session Trading Education & Agent Training" — real,
computed-fresh SESSION x REGIME evidence over this company's own closed
trades (`app/session_evidence.py`), never a second persisted copy.
Returns a `SessionRegimeEvidenceSummary`: `buckets:
SessionRegimeEvidence[]`, one per (`session`, `regime`) pairing this
company has ever actually closed a real trade under (a pairing never
seen simply never appears — no fabricated zero-evidence row), each with
`sampleSize`/`winCount`/`lossCount`/`winRatePct`/`avgPnlPct` and
`evidenceState` (`favorable`/`unfavorable`/`mixed`/`not_enough_evidence`
— `not_enough_evidence` below `minSampleSize`, a real disclosed floor of
5). Deliberately a two-axis read, not the five-axis "session x regime x
strategy x setup x outcome" the original brief described — `DecisionVaultEntry.strategyId`
is `None` on every real entry today and no "setup" taxonomy exists
anywhere in this codebase, so those two axes aren't honestly buildable
from real data yet (see the module's own docstring for the full
disclosure). This same evidence is also cited directly in the
`market_intelligence` department opinion on every real trade proposal
(`GET /api/executive/intelligence` and the Executive Meeting Log) —
informational only, never read by the Trade Gatekeeper or `RiskLimits`.

### `GET /api/market/economic-intelligence` / `GET /api/market/economic-intelligence/reports`

Design Bible Chapter 71 — the Economic Intelligence Center. Read-only, no
body on either call. `/economic-intelligence` returns the always-current
`EconomicIntelligenceState`: `regime`/`regimeLabel` (Market Environment,
Chapter 65), `marketQualityTier` (Market Intelligence), `health`
(`EconomicHealthScore` — `overall` 0-100, `tier`, and `factors`: five
named `EconomicSignalFactor` entries — Regime Favorability, Market
Quality, News Risk, Correlation Clustering, Concentration — each its own
score/weight/detail, never a black-box blend), `confidence`
(`EconomicConfidenceRead` — `confidencePct`, `evidenceQuality`,
`supportingEvidence`/`contradictingEvidence`, `keyAssumptions`,
`alternativeOutcome`), plus the current `correlationPairs`/
`categoryExposure`/`newsRisk` (all reused directly from Portfolio/Market
Intelligence, never recomputed). `/economic-intelligence/reports` returns
the permanent daily `EconomicIntelligenceReport[]` history (oldest first,
capped at `MAX_ECONOMIC_INTELLIGENCE_REPORTS = 60`), each embedding that
day's `snapshot` plus a real, evidence-cited `narrative`
(`MarketNarrativeEntry`) diffed against the previous day's report. Both
already computed on the game state (never a second copy computed by the
endpoint) — see `app/economic_intelligence.py`'s module docstring for the
full honesty boundary: this is a synthesis of already-real trading
signals, never a real macroeconomic data feed (this codebase has none).

### `GET /api/market/asset-discovery?timeframe=1d&limit=200&method=endpoint_slope&topN=10`

CEO directive "Professional Quant Trading Core," Phase B — the Asset
Discovery Engine (`app/asset_discovery.py`), the last item on that
directive's original P2 deferred list. Real cross-sectional trend
evidence — the exact same `rank_symbols_by_trend()`
(`app/trend_engine.py`) the existing `GET /api/market/trend-engine/
cross-sectional` endpoint already uses, zero new scoring logic — over
`DISCOVERY_SYMBOL_POOL` (13 real, well-known tickers spanning every one
of the 8 `ResearchCategory` values, not currently in `app/watchlist.py`'s
`SEED_SYMBOLS`/`EXTRA_SYMBOL_POOL`) minus whatever the CEO has already
added to the watchlist, so a symbol is never "discovered" twice.
Returns `list[SymbolTrendRanking]` — the identical schema the existing
cross-sectional endpoint already returns — sorted by real composite
score descending, capped to `topN` (default 10, max 50).

**Never an automatic trade or an automatic add** — the same disclosed
boundary the existing cross-sectional endpoint's own docstring already
carries. There is no symbol-specific "add to watchlist" action wired to
this read: the existing `watch_symbol` Agent Energy action
(`app/nexus.py::apply_energy_action`) takes no symbol argument and
always pulls the next entry from the fixed `EXTRA_SYMBOL_POOL` —
extending that dispatcher to accept a chosen symbol is a real, separate
follow-up, not part of what this endpoint closes.

### `GET /api/market/volume-confirmation?symbol=AAPL&timeframe=1h&limit=100&period=20`

CEO directive "AHL-Inspired Systematic Trend & Momentum Research
Engine," Phase 7 — the Volume Confirmation Engine
(`app/volume_analysis.py`). Combines real relative volume (current
bar's own volume vs. its trailing `period`-bar volume moving average)
with the same bar's real ATR-normalized price move into one categorical
`VolumeConfirmationRead`:

```json
{
  "symbol": "AAPL",
  "relativeVolume": 0.5,
  "volumeState": "weak",
  "priceMoveAtr": -0.43,
  "confirmationState": "normal",
  "detail": "Price moved -0.43 ATR on 0.50x average volume — nothing notable by this module's own disclosed thresholds."
}
```

`confirmationState` is a plain LABEL of the two real numbers above it —
`confirmed_move` (a real expansion-sized move with elevated/climax
volume alongside it), `unconfirmed_move` (the same real move with only
normal/weak volume — a real, checkable divergence, never itself a
"manipulation" or reversal claim), `abnormal_volume_quiet_price`
(climax volume, no real expansion move), or `normal`. Returns `null`
below the minimum real candle history for either the relative-volume or
ATR read, never a fabricated partial answer. Never wired into any live
trading decision.

### `GET /api/black-swan/intelligence` / `GET /api/black-swan/reports`

Design Bible Chapter 72 — the Black Swan Intelligence & Resilience
System (BSIRS). Read-only, no body on either call. `/intelligence`
returns the always-current `BlackSwanIntelligenceState`: `warning`
(`EarlyWarningScore` — `overall` 0-100, `tier`
(`green`/`yellow`/`orange`/`red`/`critical`), and `factors`: eight named
`BlackSwanSignalFactor` entries — Active Risk Warnings, Market Stress,
Volatility, Liquidity, Correlation Breakdown, Regime Divergence, News
Severity, Macro Instability, each its own score/weight/detail, higher
score meaning more stress — and `confidence` (`BlackSwanConfidenceRead`,
same shape as the Economic Confidence Engine above). `/reports` returns
the permanent daily `BlackSwanReport[]` history (oldest first, capped at
`MAX_BLACK_SWAN_REPORTS = 60`), each embedding that day's `snapshot`
plus a real, evidence-cited `narrative` diffed against the previous
day's report. Both already computed on the game state every tick — see
`app/black_swan.py`'s module docstring for the full honesty boundary:
this codebase has no historical black-swan dataset, so the Risk Level is
a real-time stress reading, never a calibrated probability.

### `GET /api/black-swan/survival-score`

Design Bible Chapter 72 Part 2 — the always-current
`InstitutionalSurvivalScore`: `overall` (0-100), `grade`
(`a_plus`/`a`/`b`/`c`/`d`/`f`), nine named `SurvivalScoreFactor` entries
(Cash Reserves, Diversification, Concentration Risk, Liquidity, Drawdown
Exposure, Rule Compliance, Black Swan Readiness, Stress Test Survival,
Broker Health — three reused directly from the Early Warning Score's own
factors, inverted), `primaryStrengths`/`primaryWeaknesses` (top/bottom 3
factors), and `topImprovements` (the 5 weakest factors' own real detail
text). No "Leverage," "Counterparty Risk," or "Estimated Survival
Probability" field exists anywhere on this response — see
`app/black_swan.py`'s module docstring for why.

### `POST /api/black-swan/stress-test`

Body: `{ "accountId"?: string | null }` (omit or `null` for the primary
portfolio; pass a real Account id to stress-test that account instead —
see Chapter 69). Runs the brief's own -10/-20/-35/-50/-70% shock ladder
against that portfolio's real current positions, returning a
`PortfolioStressTestResult`: `startingEquity`,
`heldPositionLiquidityScore`, and `levels[]` (per shock: resulting
equity, drawdown %, whether `RiskLimits.maxDrawdownPct` would be
breached, whether capital survives above zero, and an honestly-capped
`recoveryDaysEstimate`/`recoveryNote` — `null`/"N/A" when there's no
positive trailing realized performance to project a recovery from,
never a fabricated ETA). Computed fresh per request, never persisted.
404s if `accountId` doesn't match a real account.

### `POST /api/black-swan/scenario`

Body: `{ "scenarioType": "flash_crash" | "severe_selloff" |
"liquidity_freeze" | "correlation_breakdown", "accountId"?: string |
null }`. Applies an instantaneous, portfolio-wide equity shock — each
scenario a disclosed multiple of the affected symbol(s)' own real
measured volatility, reusing `app/whatif.py`'s own shock convention —
and returns a `PortfolioScenarioResult` (`startingEquity`,
`shockedEquity`, `impactPct`/`impactAmount`, `categoryImpact[]`,
`breachesMaxDrawdown`, `capitalSurvives`, a real `detail` string). No
scenario is named after a real historical event (2008/2020/1987/
Dot-Com) — see `app/black_swan.py`'s module docstring for why.

### `POST /api/black-swan/defensive-mode/activate` / `.../deactivate` / `.../configure`

Design Bible Chapter 72 — CEO-controlled Defensive Mode. `/activate`
(body: `{ "reason"?: string }`) tightens the CEO's real `RiskLimits`
(halves `maxPositionPct`/`maxDailyLossPct`/`riskPerTradePct`, halves
`maxOpenPositions`) and pauses new AI-generated trade proposal
generation — errors 400 if already active. `/deactivate` restores the
exact prior `RiskLimits` (from a real snapshot taken at activation) and
writes one permanent `BlackSwanEventRecord` (Post-Event Analysis) to
Company Memory and the Knowledge Graph — errors 400 if not active.
`/configure` (body: `{ "triggerTier"?: BlackSwanRiskTier,
"autoTriggerEnabled"?: boolean }`) sets which Risk Level auto-activates
Defensive Mode and whether auto-trigger is on at all (default off — the
brief's own "CEO may choose automatic or manual activation"). All three
return `{ "defensiveMode": DefensiveModeState, "riskLimits": RiskLimits
}`. Closing an open position is never automatic here, at any tier — see
`app/black_swan.py`'s module docstring.

### `GET /api/black-swan/playbook` / `GET /api/black-swan/broker-resilience` / `GET /api/black-swan/events`

`/playbook` returns the one real, generically-named
`BlackSwanPlaybook` ("Elevated Risk Response Playbook"), live-populated
with today's actual Defensive Mode recommendations — never one of eight
fabricated event-specific documents. `/broker-resilience` returns a
static `BrokerResilienceRead` (`status: "simulated"`) — this codebase
has no real broker connection to monitor, so this is an honest read, not
a live health score. `/events` returns the permanent
`BlackSwanEventRecord[]` Post-Event Analysis history (oldest first,
capped at `MAX_BLACK_SWAN_EVENTS = 40`).

### `GET /api/audit/log`

Design Bible Chapter 73 — the Compliance, Audit & Governance System
(CAGS). Query params: `category` (one of `AuditEventCategory`),
`severity` (`info`/`warning`/`critical`), `search` (keyword, matched
against summary/detail/department), `limit` (default 200, max 500). The
unified, real, searchable Audit Log — every real event this company
already produces (CEO decisions including real overrides, Gatekeeper/
Opportunity rejections, critical Risk Warnings, weak/reckless Discipline
Reviews, Emergency Stop, Defensive Mode, Crisis Briefings, failed Rule
Engine checks), newest first. Computed fresh per request from state
already on the game state — never a second, persisted logging system.
See `app/audit_log.py`'s module docstring for the full honesty boundary:
no per-event Broker/User/Software-Version field (this codebase has one
simulated broker, one player, no historical version tag).

### `GET /api/audit/incidents`

The same Audit Log, filtered to `warning`/`critical` severity only — a
pure filter, never a second, independently-built list that could drift
from `/api/audit/log`.

### `GET /api/audit/governance`

The real, disclosed order `app/gatekeeper.py::evaluate_gatekeeper()`
checks a trade candidate in (13 named `GovernanceLayer` entries,
`order`/`name`/`module`/`description`/`wired`), plus the Institutional
Rule Engine's real position — `wired: false`, since Chapter 69 Part 3's
Custom Rules are not yet routed into live trade execution for
non-primary accounts. Never a new authority chain; this endpoint
describes, never enforces.

### `GET /api/audit/overview`

The Compliance Dashboard's real aggregate: `complianceScore` (a
disclosed formula — `100 - min(60, 5 × open incident count)`, floored at
40), `openIncidentCount`/`criticalIncidentCount`/`totalAuditEntries`,
`ceoOverrideCount`/`ceoOverrideRatePct` (real, off `CeoDecisionRecord.
agreedWithAi`), `defensiveModeActive`/`emergencyStopActive` (reused
verbatim from Chapters 72/67), and `executiveAccuracy` (reused verbatim
from Chapter 70 Part 2's `compute_executive_accuracy_scores()`, never
recomputed here).

### `GET /api/audit/overrides`

Every real `CeoOverrideRecord` — a CEO decision where `agreedWithAi` is
false, with its real `outcome` once graded. Sourced directly from
`CeoDecisionRecord`, the same real field Chapter 70 Part 2 already
tracks for CEO Accuracy.

### Incident Resolution Engine — CEO directive "Features 31-35," Feature 31

The one real, persisted, mutable slice of CAGS (`app/compliance_incidents.py`)
— distinct from and additive to the five endpoints above, which stay
byte-for-byte unchanged. See
`docs/DesignBible/volumes/09-departments/chapter-73-compliance-audit-governance-system.md`
for the full lifecycle diagram and honesty reasoning.

**`GET /api/audit/incidents/cases`** — the real, persisted
`ComplianceIncident[]` backlog, distinct from the ephemeral
`/api/audit/incidents` filter above; these are stateful records
`app/nexus.py`'s `tick()` syncs from the real Audit Log and the POST
endpoints below mutate. Fields: `id`, `sourceEntryId` (the one real link
back to the originating `AuditEntry`), `category`, `severity`,
`department`, `summary`, `detail`, `relatedId`, `createdAt`/`simDay`
(the source entry's own real values, never today's date), `status`
(`open`/`investigating`/`remediation`/`awaiting_verification`/
`resolved`/`reopened`), `owner`, `evidence: string[]`,
`remediationPlan`, `deadlineSimDay`, `resolvedAt`, `resolutionSimDay`,
`verificationStatus` (`not_verified`/`verified`/`verification_failed`),
`verifier`, `rootCause` (8 categories including `unknown`, `null` until
resolved), `correctiveAction`, `reopenedCount`, `updatedAt`.

**`GET /api/audit/incidents/summary`** — the real `ComplianceIncidentSummary`
aggregate: `totalCount`/`openCount`/`resolvedCount`/`overdueCount`/
`reopenedIncidentCount`, `severityWeightedBacklog` (reuses
`app/company_health.py`'s own `_SEVERITY_PENALTY` table), and
`averageResolutionSimDays` — `null`, never a fabricated `0`, when
nothing has ever actually resolved.

**`POST /api/audit/incidents/{id}/investigate`** — body `{ owner:
AgentId }`. Valid only from `open`/`reopened`; sets `status:
"investigating"`.

**`POST /api/audit/incidents/{id}/remediate`** — body `{
remediationPlan: string, deadlineSimDay: int }`. Valid only from
`investigating`; sets `status: "remediation"` and stamps the real SLA
deadline (never guessed earlier).

**`POST /api/audit/incidents/{id}/evidence`** — body `{ note: string }`.
Valid at any status; appends to the permanent `evidence` trail without
changing `status`.

**`POST /api/audit/incidents/{id}/submit-verification`** — no body.
Valid only from `remediation`; sets `status: "awaiting_verification"`.

**`POST /api/audit/incidents/{id}/fail-verification`** — body `{ note:
string }`. Valid only from `awaiting_verification`; bounces back to
`status: "remediation"` (never a forced resolution) and sets
`verificationStatus: "verification_failed"`.

**`POST /api/audit/incidents/{id}/resolve`** — body `{ verifier:
AgentId, rootCause: IncidentRootCause, correctiveAction: string }`.
Valid only from `awaiting_verification`; the *only* endpoint that ever
sets `resolvedAt`/`resolutionSimDay`/`rootCause`/`correctiveAction` —
together, atomically. `rootCause: "unknown"` is always a valid, honest
answer.

**`POST /api/audit/incidents/{id}/reopen`** — body `{ note: string }`.
Valid only from `resolved`; sets `status: "reopened"` and increments
`reopenedCount`, preserving the prior resolution's `resolvedAt`/
`rootCause`/`correctiveAction` as real, unwritten history.

Every mutation endpoint above returns `400` with a real, specific reason
string (never a silent no-op) if the incident's *current* status doesn't
allow that transition — e.g. calling `/resolve` on an `open` incident.
None of these nine endpoints are on the WS broadcast — the Compliance
panel fetches this data on demand, the same convention the original five
CAGS endpoints already established.

### CEO Override Governance — CEO directive "Features 31-35," Feature 32

`app/override_governance.py`. Real, persisted, additive to `/overrides`
above (untouched).

**`GET /api/audit/overrides/evaluations`** — the real, persisted
`CeoOverrideEvaluation[]` backlog, synced/refreshed every tick. Fields:
`id`, `decisionId`, `proposalId`, `symbol`, `createdAt`, `simDay`,
`originalRecommendation`, `recommendationSource` (always
`"executive_network"` today — the real source of the AI recommendation
the CEO overrode), `ceoDecision`, `overrideReason` (`null` unless the
CEO typed one), `originalConfidencePct`/`originalDecisionGrade`/
`originalDecisionGradeScore` (the average real department confidence
and the real proposal-quality grade/score at decision time — all `null`
together when no `ExecutiveMeetingLogEntry` exists for the proposal),
`riskDepartmentStance`, `departmentAgreementPct`, `agreeingDepartments`
(the real department roles whose `agree` stance this override went
against), `evidenceAtDecisionTime` (real dissenting departments'
`evidence`/`concerns`), `processQuality`
(`justified`/`unjustified`/`mixed`/`not_enough_evidence` — see the
Design Bible chapter's Decision Logic for the exact heuristic),
`outcome` (mirrored verbatim from `CeoDecisionRecord.outcome`, never
re-derived), `reviewer`/`reviewNote`/`reviewedAt` (`null` until a real
review is recorded), `updatedAt`.

**`GET /api/audit/overrides/summary`** — the real
`CeoOverrideGovernanceSummary` aggregate: `totalOverrideCount`/
`totalDecisionCount`, `overrideRatePct` (`null`, never a fabricated 0%,
when `totalDecisionCount` is 0), `justifiedCount`/`unjustifiedCount`/
`mixedCount`/`notEnoughEvidenceCount`, `outcomeCorrectCount`/
`outcomeIncorrectCount`/`outcomePendingCount`/`outcomeUndecidableCount`,
`departmentOverrideImpact` (a real `role -> count` map), and
`sampleSizeSufficient` (a disclosed floor, `MIN_OVERRIDE_SAMPLE_FOR_TREND
= 5`, gating whether the counts above should be read as a meaningful
trend).

**`POST /api/audit/overrides/{id}/review`** — body `{ reviewer:
AgentId, note: string }`. Records a real reviewer note; never changes
`processQuality` or `outcome`.

**`POST /api/executive/decide`** also gained an optional `overrideReason`
field on the request body — stored on the resulting `CeoDecisionRecord`
only when the decision is actually an override (`choice !=
proposal.overallRecommendation`); silently ignored otherwise.

### Compliance Control Effectiveness — CEO directive "Features 31-35," Feature 34

`app/control_effectiveness.py`. Read-only, computed fresh per request —
no new `GameSaveState` field, the same original CAGS convention as the
five original `/api/audit/*` endpoints (untouched).

**`GET /api/audit/controls/effectiveness`** — the real
`ControlEffectivenessSummary` over all 12 real Gatekeeper checks.
`controls: ControlEffectivenessRecord[]`, one per check, each with:
`controlId`/`controlLabel`/`purpose`/`owner` (the check's own real,
disclosed behavior and owning module — never invented); `triggeredCount`
(every real decision this check was evaluated for) /`passedCount`/
`failedCount`; `soleReasonRejectionCount` (rejections where this was the
*only* failing check — the only case an outcome can be unambiguously
attributed to it); `confirmedPreventedCount`/`confirmedFalsePositiveCount`
(from the matching `GatekeeperRejection.outcome`,
`would_have_lost`/`would_have_won`); `pendingEvaluationCount` (still
`pending`, or the matching rejection record was evicted by
`MAX_GATEKEEPER_REJECTIONS` — either way, not yet confirmed);
`ambiguousAttributionCount` (rejections where this check failed
alongside at least one other — the outcome cannot be honestly credited
to any single one of them); `effectivenessState`
(`effective`/`ineffective`/`mixed`/`insufficient_data`/`not_yet_tested`
— see the Design Bible chapter's Decision Logic for the exact
thresholds); `controlRegression` (`true` only when a real
earlier/later split of this control's own confirmed history reads
`effective` then `ineffective`); `lastTriggeredAt`/`lastEvaluatedAt`.
Summary counts (`totalControls`, `effectiveCount`, `ineffectiveCount`,
`mixedCount`, `insufficientDataCount`, `notYetTestedCount`,
`regressedControlCount`, `updatedAt`) are pure tallies over `controls`,
never a second independently-computed number.

### Continuous Compliance Improvement Loop — CEO directive "Features 31-35," Feature 35

`app/continuous_improvement.py`. Read-only, computed fresh per request
over `state.compliance_incidents` (already persisted by Feature 31) —
no new `GameSaveState` field, the same original CAGS convention as
Feature 34.

**`GET /api/audit/continuous-improvement`** — the real
`ContinuousImprovementSummary`. `remediations:
RemediationEffectivenessRecord[]`, one per incident that has ever been
resolved at least once, each with: `incidentId`/`rootCause`/
`correctiveAction`/`category`/`department`/`resolvedAt`/
`resolutionSimDay` (mirrored from the real `ComplianceIncident`);
`reopenedCount` (a real, CEO-driven `reopen()` — the strongest possible
evidence a fix failed); `recurrenceCount` (other real incidents sharing
this one's exact `rootCause`/`category`/`department` signature that
opened after this incident's own resolution); `effectivenessState`
(`effective`/`partially_effective`/`ineffective`/`not_enough_evidence`
— `ineffective` whenever `reopenedCount > 0`, `not_enough_evidence`
before `REMEDIATION_EVAL_WINDOW_SIM_DAYS = 5` real sim-days have passed
since resolution, `effective` once that window has passed with zero
recurrence, `partially_effective` once it has passed with at least one
same-signature recurrence — see the Design Bible chapter's Decision
Logic for the full reasoning). `rootCauseRecurrences:
RootCauseRecurrence[]`, one per distinct real `rootCause` ever recorded,
with `incidentCount`/`recurringFailure` (`true` once
`RECURRING_FAILURE_MIN_COUNT = 2` real incidents share it)/
`firstOccurredAt`/`lastOccurredAt`/`incidentIds`. Summary counts
(`effectiveCount`, `partiallyEffectiveCount`, `ineffectiveCount`,
`notEnoughEvidenceCount`, `recurringFailureCount`, `updatedAt`) are pure
tallies, never a second independently-computed number.

This feature also adds `complianceHealth` to `CompanyHealth` (see the
`GET /api/load`/WS `"state"` message's existing `companyHealth` field)
— a new, additive Executive-tier dimension blending real incident
resolution, the remediation-effectiveness distribution above, and
Feature 34's control-effectiveness distribution. It does **not** change
`GET /api/audit/overview`'s `complianceScore` field — that formula
(`app/audit_log.py::compute_compliance_score()`) is deliberately
untouched; see the Design Bible chapter's "Compliance Score formula —
the documented limitation" note for why.

### `GET /api/situation-room`

Design Bible Chapter 73.5 — Mobile Command Center & Remote Operations.
Returns the real `SituationRoomState`: 13 named `SituationRoomField`s
(label/value/severity band/detail) — Company Health, Portfolio Health,
Cash Position, Open Risk, Market Regime, Trading Mode, Economic Health,
Black Swan Risk, Executive Consensus, Pending CEO Decisions, Broker
Status, Automation Status, Emergency Alerts — plus a ranked
`priorities: PriorityItem[]` (CEO Priority Engine, critical-first).
Eleven of the thirteen fields reuse an already-real single computed
source verbatim (`app/situation_room.py::compute_situation_room()`);
only Pending CEO Decisions and Executive Consensus are computed fresh.
Computed per request, same on-demand convention as
`GET /api/audit/overview` — no dedicated WS-broadcast field.

### `GET /api/travel-mode` / `POST /api/travel-mode/activate` / `POST /api/travel-mode/deactivate` / `PATCH /api/travel-mode/settings`

Design Bible Chapter 73.5's Travel Mode — a real CEO-configurable
conservative posture, persisted as `TravelModeState` and broadcast over
the WS `"state"` message (`travelMode`, `travelModeBriefings`). `GET`
returns the current state. `POST /activate` sets `active: true`
(`activationSource: "manual"`); the same activation can also happen
automatically (`"auto_inactivity"`) from `app/nexus.py`'s tick loop once
`should_auto_activate()` trips, if the CEO has enabled it in settings.
`POST /deactivate` clears `active`, generates a real
`TravelModeBriefing` from records in the exact activation window
(CEO decisions resolved, Gatekeeper rejections, critical Risk Warnings,
Circuit Breaker tier changes, realized P&L), appends it to the capped
`travelModeBriefings` history, and returns that briefing. `PATCH
/settings` body: any subset of `{ "positionSizeCapPct", "dailyRiskCapPct",
"notificationSensitivity", "autoActivateEnabled",
"autoActivateAfterMinutes" }` — percentages clamp to 25–75, the
inactivity threshold clamps to 15–240 simulated minutes
(`app/travel_mode.py::_clamp_settings()`). While active, Travel Mode's
caps compose with — never replace — the same derived,
non-persisted tightening seam Company Priority and Chapter 75's Daily
Circuit Breaker already use (`apply_travel_mode_tightening()`,
layered onto `_effective_risk_limits()` via `max()`, confirmed one of
exactly three such patterns in this codebase). Records a real, permanent
`MemoryRecord` (`category: "alert"`, title prefixed `"Travel Mode"`),
picked up by Chapter 73's Audit Log via the new `travel_mode_change`
category.

### `GET /api/trading-modes/state` / `POST /api/trading-modes/set`

Design Bible Chapter 75 — Company Trading Modes & Institutional Capital
Protection. `GET` returns the real, persisted `TradingModeState`
(`mode`: `day_trading`/`swing_trading`/`hybrid`, `hybridDayAllocationPct`,
`changedAt`, `previousMode`, `changeReason`, plus the CEO's Circuit
Breaker/Losing Streak thresholds and internal rotation/acknowledgment
bookkeeping). `POST` body: `{ "mode": TradingMode, "hybridDayAllocationPct"?: number }`
— errors 400 while Emergency Stop is active. Records a real, permanent
`MemoryRecord` (`category: "alert"`), picked up by Chapter 73's Audit
Log via the new `trading_mode_change` category.

### `GET /api/trading-modes/circuit-breaker`

The real Daily Circuit Breaker read (`tier`: `none`/`tier1`/`tier2`/
`tier3`/`tier4`, `dailyPnlPct`, `tier1Pct`/`tier2Pct`/`tier3Pct` — CEO-
configurable, `tier4Pct` — mirrors `RiskLimits.maxDailyLossPct`
verbatim, never a separate field). Recomputed every tick from the same
real daily P&L% `evaluate_sentinel_risk()` already tracks.

### `GET /api/trading-modes/losing-streak` / `POST /api/trading-modes/losing-streak/acknowledge`

`GET` returns the real `LosingStreakRead` (`consecutiveLosses`,
`pauseActive`, `pauseThreshold`/`suspendThreshold` — CEO-configurable).
`POST` is the CEO's real, explicit clear of an active pause — errors 400
if no pause is currently active. The clear auto-re-arms the moment a
fresh losing streak reaches the threshold again (see
`app/trading_modes.py`'s `compute_losing_streak()` for the exact
auto-reset-on-win rule).

### `GET /api/trading-modes/performance`

A real win-rate/P&L split (`TradingStylePerformance[]`) over
`PaperPortfolio.tradeHistory`, grouped by the real `"day"`/`"swing"` tag
assigned at proposal time. Computed fresh per request. Never claims
independent capital pools per style — see the Design Bible chapter's own
Ownership section for why that's out of scope.

### `GET /api/trading-modes/health`

A real Trading Mode Health read (`TradingModeHealthAssessment[]`),
mirroring `app/strategy_lab.py`'s own `StrategyHealthStatus`/
`StrategyHealthTrend` vocabulary and threshold shape, computed over each
trading style's own real closed-trade history instead of a backtested
Strategy's `SimulationResult` history.

### `GET /api/trading-modes/adaptive-recommendation`

Design Bible Chapter 75's Adaptive Mode — read-only, exactly like
Chapter 65's own `posture` field, never applied automatically. Reads the
real `RegimeReconciliation` (Chapter 65) and maps it to a recommended
`TradingMode` (or `null`) off a disclosed decision table — see
`app/trading_modes.py`'s `compute_adaptive_mode_recommendation()`.
Extreme/avoid-trading conditions never recommend a trading-style change;
`note` points the CEO at Chapter 72's Defensive Mode instead.

### `GET /api/trading-modes/recovery-briefings`

The permanent, capped history of `RecoveryBriefing` records — generated
only when Emergency Stop activates because of this chapter's own Tier 4
Circuit Breaker or a losing-streak suspension, never for a CEO-manual
stop. Real recent stats (win rate, average loss, largest loss, days
since the last profitable day) plus links to the real Discipline Chamber
reviews for the trades involved.

### `POST /api/emergency-stop/activate` / `POST /api/emergency-stop/resume`

Design Bible Chapter 67 (TTOS) Part 3 — the real Global Emergency Stop.
No body on either call. Returns `{ "emergencyStop": EmergencyStopState }`
(`active: bool`, `activatedAt: string | null`). `/activate` errors 400
if already active; `/resume` errors 400 if not active. Activating
blocks new trade proposal generation entirely, keeps every pending
proposal frozen through `_apply_operating_mode()` regardless of
Operating Mode, and rejects the CEO's own manual buy/sell call via
`POST /api/executive/decide` (only a `"wait"` choice is still allowed).
Already-pending proposals are never auto-cancelled and already-placed
broker orders are never force-closed — see `app/emergency_stop.py`'s
module docstring for the exact enforcement boundary. Both calls write a
real, permanent Company Memory entry (category `"emergency"`) — this is
the feature's own "incident report," not a second parallel record.

### `GET /api/trading-restrictions` / `POST /api/trading-restrictions/activate` / `POST /api/trading-restrictions/{id}/lift`

CEO directive "Layered Kill Switches" — the scoped granularity layer
below the firm-wide Emergency Stop above. See `app/trading_restrictions.py`'s
module docstring for why symbol/category is the one real layer built
here (strategy already has `app/sandbox.py::retire_strategy()`; agent
was explicitly not built — see that docstring's reasoning). All three
return `{ "tradingRestrictions": TradingRestriction[] }`, the full
permanent history (past + currently active), each entry:
`id`, `scope` (`"symbol" | "category"`), `target` (a symbol string or a
`ResearchCategory` value), `reason`, `active: bool`, `activatedAt`,
`liftedAt: string | null`, `liftedReason: string | null`.

`GET` takes no body. `POST /activate` body: `{ "scope", "target",
"reason" }` — errors 400 on a blank reason or a duplicate active
restriction on the same `(scope, target)`. `POST /{id}/lift` body:
`{ "reason": string }` (optional, defaults to `""`) — errors 400 on an
unknown id or an already-lifted restriction.

An active restriction halts new position-opening (buy AND sell) for its
target — never a partial halt, matching Emergency Stop's own "no
ambiguity" choice — via two real enforcement points: `app/nexus.py`'s
`_generate_trade_proposals()` (the CEO never sees a new proposal for a
restricted symbol/category) and the Trade Gatekeeper's 13th check,
`_trading_restriction_check` (defense in depth for a proposal already
pending when a restriction activates). Already-open positions are never
force-closed. Both activate/lift write a real, permanent Company Memory
entry (category `"alert"`, title `"Trading Restriction activated"` /
`"lifted"`), which also feeds the Compliance Incidents pipeline via a
new `"trading_restriction"` `AuditEventCategory`.

CEO directive "Session Trading Education & Agent Training" extended the
`market_intelligence` track's `FoundationalMentorState.mentors[].lessons`
(carried on `GET /api/load`/the WS `"state"` message, not a dedicated
GET endpoint) from 8 to 15 real lessons — a 7-lesson session-intelligence
sub-module (`mi-session-foundations` through `mi-session-decision-process`)
on top of the existing `mi-session` lesson — using the exact same
`FoundationalMentorLesson` shape and endpoints below. Note: existing
saves keep whatever lesson count they were created with (no
lesson-content sync-on-load exists in this codebase); only a new game
gets the extended curriculum immediately.

### `POST /api/foundational-mentors/*`

v0.7 Feature 49 (Phase 3, revised) — the Foundational Mentor Program /
Professional Academy (see `docs/Architecture.md`'s "Professional
Academy — Feature 49 Revision" section for the full "employees are the
students" rationale and content-attribution boundary). Real employee
students never call these endpoints — they advance automatically every
backend tick. All endpoints below return
`{ "foundationalMentorState": { ... } }` with the full, current
`FoundationalMentorState` (now keyed per-employee — see below), and call
`persist_modules()` before returning.

**Real CEO management actions (the real employee cohort):**

- `POST /api/foundational-mentors/approve-graduation` — body
  `{ "agentId": "scout", "mentorId": "tjr" }`. The Graduation Queue's
  real Approve action — advances that employee's `graduationStatus`
  from `"pending_approval"` to `"graduated"`. Also returns
  `{ "companyGraduated": true }` if every real student now has an
  approved graduation on that track (which also unlocks the next
  roadmap mentor). `400` if that employee has no pending graduation on
  that track, or isn't a real student (`STUDENT_AGENT_IDS`).
- `POST /api/foundational-mentors/revoke-graduation` — body
  `{ "agentId": "scout", "mentorId": "tjr" }`. The Executive Action
  "Revoke Graduation" — the mirror image of `/approve-graduation`.
  Reverts that employee's `graduationStatus` from `"graduated"` back to
  `"in_progress"`, resets their lesson/quiz progress on that track to a
  real fresh start (they genuinely repeat it — real auto-progression
  picks it back up next tick), and sets a real Coach improvement-plan
  note (`coachNote`, cleared automatically on real re-approval). Never
  touches the mentor track's own company-wide status/roadmap position or
  any other employee's progress. `400` if that employee has no real
  graduation on that track to revoke, or isn't a real student.
- `POST /api/foundational-mentors/pause` / `/resume` — no body. Pauses
  or resumes the whole company's training on the currently-active
  mentor. `400` if the track isn't in the required starting status
  (`"active"` to pause, `"paused"` to resume).
- `POST /api/foundational-mentors/skip` — no body. CEO manual override:
  pauses the current track (every employee's progress preserved) and
  activates the next roadmap entry for the whole company. `400` if the
  track is already the last roadmap entry.
- `POST /api/foundational-mentors/repeat` — body `{ "mentorId": "tjr" }`.
  Resets every real student's progress on a graduated track and puts
  the whole company back through it. `400` if the track isn't
  `"graduated"`.
- `POST /api/foundational-mentors/resource` — body
  `{ "mentorId": "tjr", "title": "...", "url": "https://...",
  "resourceType": "video" }` (`url` optional). Adds a CEO-provided
  bookmark, company-wide per mentor track — TradeTown never fetches,
  parses, or grades it. `400` on an empty title, an unknown mentor, or
  once a track hits `MAX_RESOURCES_PER_MENTOR` (20).

**The CEO's own, entirely optional personal learning (never required,
never touches real employee progress):**

- `POST /api/foundational-mentors/ceo/view` — body
  `{ "mentorId": "tjr", "lessonId": "tjr-psychology" }`. Marks the
  lesson viewed in the CEO's own separate `ceoProgress` bucket
  (idempotent). Unknown mentor/lesson is a silent no-op.
- `POST /api/foundational-mentors/ceo/quiz` — body
  `{ "mentorId": "tjr", "lessonId": "tjr-psychology", "selectedIndex": 0 }`.
  Returns the state plus `{ "correct": true, "correctIndex": 0,
  "correctOption": "..." }`, graded against the real hidden answer key
  exactly as a human player would be. `404` if the mentor or lesson id
  doesn't exist.

**Mentor Lab — real CEO custom-mentor/lesson authoring** (Command
Center UI Revision; see `docs/Architecture.md`'s "Mentor Lab" section):

- `POST /api/foundational-mentors/add-mentor` — body `{ "name": "...",
  "trackLabel": "...", "focusAreas": ["..."] }`. Appends a real new
  mentor track to the roster and to the end of the persisted roadmap
  order. Returns `{ "foundationalMentorState": { ... }, "mentorId":
  "..." }`. `400` on an empty name/focus areas, or once
  `MAX_CUSTOM_MENTORS` (20) is reached.
- `POST /api/foundational-mentors/add-lesson` — body `{ "mentorId":
  "...", "title": "...", "simpleExplanation": "...",
  "deeperExplanation": "...", "quizQuestion": "...", "quizOptions":
  ["...", "...", "...", "..."], "correctIndex": 0 }`. Appends a real
  lesson to that mentor's curriculum; the correct answer is stored
  server-side only (`custom_lesson_answers`), never sent to the client.
  `400` on an unknown mentor, a malformed quiz shape, or once
  `MAX_LESSONS_PER_MENTOR` (30) is reached.
- `POST /api/foundational-mentors/set-active` — body `{ "mentorId":
  "..." }`. CEO override: makes any mentor with at least one lesson the
  active company-wide track, pausing whatever was previously active
  (progress preserved, not discarded). `400` if the mentor has no
  lessons yet, is unknown, or is already the active track.

### Bounding / trimming

Every list above is capped server-side before it's ever sent — the client
never needs to trim anything itself:

| Field | Cap | Why |
|---|---|---|
| `tasks` | last 20 (of an internally-kept 60) | recent-activity feed, not full history |
| `news` | last 8 **per category** | a shared flat cap let frequent `discovery` news evict rare `market`/`company` items entirely — see Architecture.md |
| `research` | 1 active + last 24 completed **per agent** | one active item per research-capable agent by design; history is a rolling window |
| `memory` | last 200 total | `CompanyMemory`'s cap across all categories |
| `meetingMinutes` | last 20 | one per completed meeting |
| `paperPortfolio.tradeHistory` | last 50 | `MAX_TRADE_HISTORY` — recent-trades feed, not full lifetime history |
| `backtestSessions` | uncapped, but at most 2 concurrent (`MAX_CONCURRENT_SESSIONS`) | queued/running sessions clear into `simulationResults` on completion |
| `simulationResults` | last 30 | `MAX_SIMULATION_RESULTS` |
| `hallOfFame` | last 40 | `MAX_HALL_OF_FAME` |
| `coachReports` | last 20 | `MAX_COACH_REPORTS` |
| `performanceSnapshots` | last 60 | `MAX_PERFORMANCE_SNAPSHOTS` |
| `paperPortfolio.orders` | last 40 resolved (`MAX_ORDER_LOG`) + all currently open | order history, not full lifetime log |
| `riskWarnings` | uncapped, but replaced wholesale every tick | current standing watch, not a log — see `risk_engine.monitor_portfolio()` |
| `scannerAlerts` | last 30 (`MAX_ALERTS`) | rolling alert feed |
| `decisions` | uncapped | the v0.6 brief's Explainable AI requirement is "store every report permanently" |
| `debates` | last 60 (`MAX_DEBATES`) | one per proposal plus any "request another debate" calls — v0.7 Feature 17 |
| `gatekeeperRejections` | last 100 (`MAX_GATEKEEPER_REJECTIONS`) | one per trade the Trade Gatekeeper vetoed — v0.7 Feature 20 |
| `marketEnvironment.timeline` | last 100 (`MAX_MARKET_ENVIRONMENT_HISTORY`) | only grows on a real regime change, not every tick — v0.7 Feature 22 |
| `executiveReviews` | last 20 (`MAX_EXECUTIVE_REVIEWS`) | the CIO's Monthly Executive Review — v0.7 Feature 24 |
| `academyProjects` | uncapped, but always exactly one active | the Academy's one company-wide knowledge project — v0.7 Feature 25 |
| `academyCompletedProjects` | last 50 (`MAX_ACADEMY_LIBRARY`) | the permanent Company Knowledge Library — v0.7 Feature 25 |
| `goals` | last 20 (`MAX_GOALS`) | CEO-authored company goals, oldest evicted first regardless of status — Design Bible Chapter 64 |
| `strategicReviews` | last 20 (`MAX_STRATEGIC_REVIEWS`) | one real `StrategicReview` per monthly cycle, over CEO-authored goal progress — Design Bible Chapter 64 (fifth pass) |
| `disciplineReviews` | last 60 (`MAX_DISCIPLINE_REVIEWS`) | one per closed trade — v0.7 Feature 26 |
| `caseStudies` | last 60 (`MAX_CASE_STUDIES`) | one per detected real process-gap mistake — v0.7 Feature 27 |
| `institutionalMemory` | last 200 (`MAX_INSTITUTIONAL_MEMORY`) | one promoted, reusable lesson per real case study/failed strategy/Hall of Fame induction/Model Validation finding/critical risk warning/regime shift — CEO directive "Features 26-30," Feature 26 |
| `agentPerformanceReviews` | last 150 (`MAX_AGENT_PERFORMANCE_REVIEWS`) | one real, 8-dimension review per agent per real week — CEO directive "Features 26-30," Feature 27 |
| `agentSkillProfiles` | last 150 (`MAX_AGENT_SKILL_PROFILES`) | one real, 11-domain skill snapshot per agent per real week — CEO directive "Features 26-30," Feature 28 |
| `predictionRecords` | last 150 (`MAX_PREDICTION_RECORDS`) | one real trade-direction prediction per real trade-causing decision, staked before its outcome was known — CEO directive "Features 26-30," Feature 29 |
| `failureClassifications` | last 60 (`MAX_FAILURE_CLASSIFICATIONS`) | one real thesis-failure classification per real closed, losing trade — CEO directive "Features 26-30," Feature 30 |
| `reasoningChallenges` | last 60 (`MAX_REASONING_CHALLENGES`) | one per real AI Debate practiced, on a fixed cadence — v0.7 Feature 29 |
| `reflectionSessions` | last 80 (`MAX_REFLECTION_SESSIONS`) | one per real weekly/monthly cycle — v0.7 Feature 30 |
| `questionArchive` | last 120 (`MAX_QUESTION_ARCHIVE`) | one `QuestionOfTheDay` per real in-game morning — v0.7 Feature 32 |
| `blackBox.archive` | last 30 (`MAX_ARCHIVE`) | completed + failed Black Box Projects — Museum of Discoveries entries and Research Archives both live here |
| `blackBox.reviews` | last 30 (`MAX_REVIEWS`) | one Founder Council `BreakthroughReview` per project that reached review |
| `talent.reports` | last 30 (`MAX_TALENT_REPORTS`) | one `TalentReport` per agent/trait pair that ever cleared both real thresholds — v0.7 Feature 44 |
| `strategyReports` | last 60 (`MAX_STRATEGY_REPORTS`) | one per completed `SimulationResult` — v0.7 Feature 45 |
| `strategyReviews` | last 30 (`MAX_STRATEGY_REVIEWS`) | one per Company Review requested — v0.7 Feature 45 |
| `constitution.citations` | last 120 (`MAX_CONSTITUTION_CITATIONS`) | one per real "Live Enforcement" event across 6 real hooks — v0.7 Feature 46 |
| `executiveMeetingLog` | last 200 (`MAX_MEETING_LOG_ENTRIES`) | one per real `resolve_proposal()` call — v0.7 Feature 50 (Part 2/3) |
| `departmentSelfEvaluations` | last 250 (`MAX_SELF_EVAL_HISTORY`) | one per department per real in-game week — v0.7 Feature 50 (Part 2/3) |
| `marketIntelligenceReports` | last 60 (`MAX_MARKET_INTELLIGENCE_REPORTS`) | one Executive Market Brief per real in-game evening — v0.7 Feature 51 |
| `marketIntelligenceLearning` | last 60 (`MAX_MARKET_INTELLIGENCE_LEARNING`) | one Learning Loop entry per real in-game evening, graded the day after — v0.7 Feature 51 |

### Provider configuration

`MARKET_DATA_PROVIDER` (env var, default `mock`) selects the watchlist's
price source. Only `mock` is implemented as of v0.5 — see
`docs/Architecture.md`'s "Research & market intelligence (v0.3)" section
for the adapter pattern to add a real one; `simulation.py`'s placeholder
backtest math (see "Paper trading, simulation & coaching (v0.5)") would
also switch to a real historical data source through the same interface.
