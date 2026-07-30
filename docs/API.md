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
gatekeeperRejections), `knowledge_archive` (caseStudies, questionArchive,
reasoningChallenges, reflectionSessions, disciplineReviews, hallOfFame,
memory, meetingMinutes, executiveReviews, talent), and `academy`
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
    "reputation": 20.0, "technologyLevel": 40.0, "officeExpansion": 25.0, "educationProgress": 15.0,
    // v0.7 Feature 43 — real support-vs-challenge ratio across the most
    // recent 20 AI Debates (app/company_health.py's _team_chemistry).
    "teamChemistry": 62.5,
    "recommendations": ["Reputation is low (20/100) — worth attention."],
    "updatedAt": "..."
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
    // v0.7 Feature 49 (Phase 3) — the Foundational Mentor Program. Real
    // mutated progress, unlike mentorState above — see
    // docs/Architecture.md's "Foundational Mentor Program" section.
    "mentors": [
      { "id": "tjr", "name": "TJR", "trackLabel": "TJR Track", "focusAreas": ["Trading Psychology", "Discipline", "Daily Routines", "Patience", "Trade Planning", "Journaling"],
        "contentNote": "This track's name credits a real, respected trading educator...", "status": "active",
        "lessons": [ { "id": "tjr-psychology", "order": 1, "title": "Trading Psychology: Process Over Outcome", "simpleExplanation": "...", "deeperExplanation": "...", "quizQuestion": "...", "quizOptions": ["...", "...", "...", "..."] } ],
        "resources": [] }
      // ... al_brooks, linda_raschke, mark_douglas, tom_hougaard, mike_bellafiore — all "status": "planned", "lessons": []
    ],
    "progress": { "tjr": { "mentorId": "tjr", "viewedLessonIds": ["tjr-psychology"], "completedLessonIds": [], "quizAttempts": 0, "correctQuizAttempts": 0, "graduatedSimDay": null } },
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
    "dailyProfitTargetPct": 3.0, "maxTradesPerDay": 6
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
    // — never a fabricated P&L.
    {
      "id": "gkreject-decision-proposal-research-echo-AAPL-...", "proposalId": "proposal-research-echo-AAPL-...",
      "symbol": "AAPL", "ceoChoice": "buy",
      "reasons": ["Decision Confidence: 42/100 — below the required 55 minimum."],
      "priceAtRejection": 471.87, "rejectedSimMinutes": 1560,
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
proposal id isn't found (already resolved or expired).

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
  one call.
- `decide`: body `{ "reviewId": "...", "approve": true }`. The Company
  Review stage's real manual CEO call — Learning Mode always requires
  this; Assisted/Executive Mode auto-resolve instead (see
  `docs/Architecture.md`'s "Research Sandbox" section). `400` if the
  review was already decided.

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
(previously display-only, with no endpoint at all). Body: any subset of
`{ "dailyProfitTargetPct": 3.0, "maxDailyLossPct": 5.0, "maxTradesPerDay": 6,
"riskPerTradePct": 2.0, "maxOpenPositions": 8 }` — every field optional,
so a single call can update just one limit. Returns
`{ "riskLimits": { ... } }` with the full, current `RiskLimits`. `400`
if a provided value isn't positive, or if no fields were provided at
all. Takes effect on the very next generated `TradeProposal` — see
`app/risk_engine.py`'s `evaluate_sentinel_risk` and
`docs/Architecture.md`'s "Daily Trading Objectives" section for exactly
how each limit is enforced.

### `POST /api/foundational-mentors/*`

v0.7 Feature 49 (Phase 3) — the Foundational Mentor Program (see
`docs/Architecture.md`'s "Foundational Mentor Program" section for the
full content-attribution rationale). All 7 endpoints return
`{ "foundationalMentorState": { ... } }` with the full, current
`FoundationalMentorState`, and call `persist_modules()` before
returning.

- `POST /api/foundational-mentors/view` — body
  `{ "mentorId": "tjr", "lessonId": "tjr-psychology" }`. Marks the
  lesson viewed (idempotent). Unknown mentor/lesson is a silent no-op.
- `POST /api/foundational-mentors/quiz` — body
  `{ "mentorId": "tjr", "lessonId": "tjr-psychology", "selectedIndex": 0 }`.
  Returns the state plus `{ "correct": true, "correctIndex": 0,
  "correctOption": "..." }`. A correct answer marks the lesson complete;
  completing every lesson in a track graduates it and, if the next
  roadmap entry is still `"planned"`, flips it to `"active"`. `404` if
  the mentor or lesson id doesn't exist.
- `POST /api/foundational-mentors/pause` / `/resume` — body
  `{ "mentorId": "tjr" }`. `400` if the track isn't in the required
  starting status (`"active"` to pause, `"paused"` to resume).
- `POST /api/foundational-mentors/skip` — body `{ "mentorId": "tjr" }`.
  CEO manual override: pauses the current track (progress preserved)
  and activates the next roadmap entry. `400` if the track is already
  the last roadmap entry.
- `POST /api/foundational-mentors/repeat` — body `{ "mentorId": "tjr" }`.
  Resets a graduated track's progress and reactivates it. `400` if the
  track isn't `"graduated"`.
- `POST /api/foundational-mentors/resource` — body
  `{ "mentorId": "tjr", "title": "...", "url": "https://...",
  "resourceType": "video" }` (`url` optional). Adds a CEO-provided
  bookmark — TradeTown never fetches, parses, or grades it. `400` on an
  empty title, an unknown mentor, or once a track hits
  `MAX_RESOURCES_PER_MENTOR` (20).

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
| `disciplineReviews` | last 60 (`MAX_DISCIPLINE_REVIEWS`) | one per closed trade — v0.7 Feature 26 |
| `caseStudies` | last 60 (`MAX_CASE_STUDIES`) | one per detected real process-gap mistake — v0.7 Feature 27 |
| `reasoningChallenges` | last 60 (`MAX_REASONING_CHALLENGES`) | one per real AI Debate practiced, on a fixed cadence — v0.7 Feature 29 |
| `reflectionSessions` | last 80 (`MAX_REFLECTION_SESSIONS`) | one per real weekly/monthly cycle — v0.7 Feature 30 |
| `questionArchive` | last 120 (`MAX_QUESTION_ARCHIVE`) | one `QuestionOfTheDay` per real in-game morning — v0.7 Feature 32 |
| `blackBox.archive` | last 30 (`MAX_ARCHIVE`) | completed + failed Black Box Projects — Museum of Discoveries entries and Research Archives both live here |
| `blackBox.reviews` | last 30 (`MAX_REVIEWS`) | one Founder Council `BreakthroughReview` per project that reached review |
| `talent.reports` | last 30 (`MAX_TALENT_REPORTS`) | one `TalentReport` per agent/trait pair that ever cleared both real thresholds — v0.7 Feature 44 |
| `strategyReports` | last 60 (`MAX_STRATEGY_REPORTS`) | one per completed `SimulationResult` — v0.7 Feature 45 |
| `strategyReviews` | last 30 (`MAX_STRATEGY_REVIEWS`) | one per Company Review requested — v0.7 Feature 45 |
| `constitution.citations` | last 120 (`MAX_CONSTITUTION_CITATIONS`) | one per real "Live Enforcement" event across 6 real hooks — v0.7 Feature 46 |

### Provider configuration

`MARKET_DATA_PROVIDER` (env var, default `mock`) selects the watchlist's
price source. Only `mock` is implemented as of v0.5 — see
`docs/Architecture.md`'s "Research & market intelligence (v0.3)" section
for the adapter pattern to add a real one; `simulation.py`'s placeholder
backtest math (see "Paper trading, simulation & coaching (v0.5)") would
also switch to a real historical data source through the same interface.
