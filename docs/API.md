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
`dialogueHistory` filled in). Only those three client-owned fields are
actually persisted from the payload — every other field
(`agents`/`tasks`/`whiteboards`/`meeting`/`news`/`research`/`watchlist`/
`memory`/`meetingMinutes`/`time`) stays server-authoritative and is
overwritten with whatever NEXUS currently has, regardless of what the
client sent (see `GameState.apply_client_save()`).

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
    // ...atlas, echo, nova, scribe
  },
  "tasks": [
    {
      "id": "task-scout-1-9-0",
      "owner": "scout",
      "category": "news_scan", // research | review | meeting | watchlist_update | news_scan | chart_analysis | documentation
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
    // categories: research | meeting | whiteboard | event | discussion | discovery | future_trade
  ],
  "meetingMinutes": [
    {
      "id": "minutes-1-14-0",
      "day": 1, "hour": 14, "minute": 0,
      "participants": ["scout", "echo"],
      "summary": "2 attended: Scout, Echo. Discussed AAPL, MSFT.",
      "discussion": [{ "id", "speaker": "scout", "line": "...", "timestamp": "..." }]
    }
  ]
}
```

`GET /api/load` returns this same set of fields plus `version` (currently
`"0.3"`), `player` (`EntityTransform`), `settings` (`SettingsState`),
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

### Provider configuration

`MARKET_DATA_PROVIDER` (env var, default `mock`) selects the watchlist's
price source. Only `mock` is implemented in v0.3 — see
`docs/Architecture.md`'s "Research & market intelligence (v0.3)" section
for the adapter pattern to add a real one.
