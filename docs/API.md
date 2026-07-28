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

Returns the full authoritative `GameSaveState` — always succeeds; a fresh
deployment just returns sensible defaults (see `state.default_state()`).
Same shape as a `"state"` WebSocket message plus the client-owned fields
(`player`, `settings`, `dialogueHistory`) and `version`/`updatedAt`. See
"GameSaveState fields" below for the full shape.

## `POST /api/save`

Body: a full `GameSaveState` (as returned by `GET /api/load` or received
over the WebSocket, with the client's own `player`/`settings`/
`dialogueHistory` filled in). `settings.operatingMode`
(`learning | assisted | executive`, v0.7 Feature 21 — see
`app/schemas.py`'s `SettingsState`) is the one client-owned field NEXUS
itself reads every tick, to decide whether to auto-resolve trade
proposals (see `nexus._apply_operating_mode()`). Only those three client-owned fields are
actually persisted from the payload — every other field
(`agents`/`tasks`/`whiteboards`/`meeting`/`news`/`research`/`watchlist`/
`memory`/`meetingMinutes`/`paperPortfolio`/`strategies`/
`backtestSessions`/`simulationResults`/`hallOfFame`/`coachReports`/
`companyScore`/`performanceSnapshots`/`time`) stays server-authoritative
and is overwritten with whatever NEXUS currently has, regardless of what
the client sent (see `GameState.apply_client_save()`).

Response:

```json
{ "ok": true, "updatedAt": "2026-01-01T00:00:00.000000+00:00" }
```

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
    "recommendations": ["Reputation is low (20/100) — worth attention."],
    "updatedAt": "..."
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
    // v0.7 Feature 25 — every agent's own real Knowledge Points/tier
    // (app/academy.py). "branch" is a fixed, occupation-linked theme;
    // points only ever grow from real completed work (a finished
    // ResearchItem, a finished AcademyProject, real meeting attendance).
    "echo": { "agentId": "echo", "branch": "Technical Analysis", "points": 18.5, "tier": 2 }
  },
  "academyState": {
    // Company-wide progression derived from agentKnowledge + real
    // completed-project count — level/label only, no new art per level
    // (see docs/Architecture.md's scope-cut note).
    "level": 3, "levelLabel": "Innovation Lab", "totalPoints": 142.0, "completedProjectCount": 18, "updatedAt": "..."
  },
  "performanceSnapshots": [
    { "period": "daily", "returnPct": 1.2, "winRate": 60.0, "maxDrawdownPct": 4.1, "sharpeRatio": 0.29, "sortinoRatio": 0.34, "avgHoldingMinutes": 210.0, "researchAccuracy": 71.0, "confidenceAccuracy": 68.0, "computedAt": "..." }
  ],
  "riskLimits": {
    "maxPositionPct": 10.0, "maxDailyLossPct": 5.0, "maxDrawdownPct": 20.0,
    "maxOpenPositions": 8, "maxSectorConcentrationPct": 30.0, "riskPerTradePct": 2.0
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

`GET /api/load` returns this same set of fields plus `version` (currently
`"0.6"`), `player` (`EntityTransform`), `settings` (`SettingsState`),
`dialogueHistory` (`DialogueHistoryEntry[]`), and `updatedAt`.

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

### Provider configuration

`MARKET_DATA_PROVIDER` (env var, default `mock`) selects the watchlist's
price source. Only `mock` is implemented as of v0.5 — see
`docs/Architecture.md`'s "Research & market intelligence (v0.3)" section
for the adapter pattern to add a real one; `simulation.py`'s placeholder
backtest math (see "Paper trading, simulation & coaching (v0.5)") would
also switch to a real historical data source through the same interface.
