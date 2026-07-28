# Architecture

## Overview

TradeTown v0.6 is a client/server game:

- **Frontend** (`frontend/`): a React app that mounts a single Phaser 3
  game instance into a `<div>`. Phaser owns the world (tilemaps, player,
  agents, camera, collision); React owns the HUD/menus and reads game state
  through a small pub/sub bridge rather than reaching into Phaser directly.
- **Backend** (`backend/`): a FastAPI service that is the **authoritative**
  simulation of all nine agents — NEXUS (`backend/app/nexus.py`) advances
  every agent's schedule, task, mood, energy, meetings, breaks, research
  progress, paper trading, simulations, coaching, and (new in v0.6)
  market scanning, risk evaluation, decision voting, and order fills in a
  background asyncio loop even if no browser is connected, and pushes the
  result to connected clients over a WebSocket. It also persists the save
  to SQLite.

```
┌─────────────────────────┐        WebSocket (/ws)         ┌──────────────────────────┐
│  Frontend (Phaser+React)│ <── time + agents/tasks/news ── │  Backend (FastAPI)       │
│                          │                                 │                          │
│  EventBus ── gameStore   │ ───── REST (/api/save,/load) ─> │  GameState (in-memory)   │
│     │                    │                                 │      │                   │
│  Phaser scenes           │                                 │  SQLite (saves table)    │
└─────────────────────────┘                                 └──────────────────────────┘
```

## Why server-authoritative agents?

The brief calls for the office to "feel alive" — the team should be doing
research whether or not the CEO is watching. That only works if agent state
lives somewhere that keeps running independent of the browser tab, so the
tick loop (`backend/app/nexus.py`, driven by `backend/app/sim.py`) is the
single source of truth for every agent's `location`, `currentTask`,
`mood`, `energy`, and `override` (meeting/break), plus the shared task
list, whiteboards, meeting state, and news feed. The frontend has a
**local fallback** (`NPCManager.startOfflineFallback` /
`TimeManager.startLocalFallback`) that mirrors the same schedule
(`Schedule.ts` / `schedule.py`) so the game stays playable if the
WebSocket drops, but it defers to the server the instant a connection is
available again. Meetings and breaks are *not* mirrored offline — they're
a NEXUS-only embellishment on top of the schedule, so the offline fallback
just shows the plain scheduled location/task until reconnected.

The player's position, camera-relative facing, UI settings, and dialogue
history are **client-authoritative** — the backend just stores whatever the
client last reported on save.

## Frontend systems (`frontend/src/game/systems/`)

| System | Responsibility |
|---|---|
| `EventBus` | Typed pub/sub decoupling Phaser scenes, React UI, and the network layer. Every cross-cutting event (`time:tick`, `agent:updated`, `room:entered`/`room:left`, `task:assigned`/`task:completed`, `whiteboard:updated`, `meeting:started`/`meeting:ended`, `news:updated`, `dialogue:open`, `save:completed`, …) flows through here. |
| `AssetLoader` | The **only** place that reads `assets/manifest.generated.json`. Scenes/entities ask for an asset by id; nothing hardcodes a file path. |
| `GameManager` | Owns the single `Phaser.Game` instance and the cross-scene player transform (scenes are destroyed/recreated on transition, so "where is the player" has to live above any one scene). |
| `SceneManager` | Fade-transition helper between scenes with spawn-point handoff. |
| `CameraManager` | Consistent camera-follow (lerp, deadzone, zoom) across every scene. |
| `InputManager` | Normalizes WASD/arrows/E/Esc into a movement vector + discrete actions. One instance per scene. |
| `TimeManager` | Mirrors the server's clock; local fallback ticker when offline. |
| `AgentProfiles` | Static per-agent metadata (name, occupation, personality blurb, home location, sprite tint) for all nine agents — mirrors `backend/app/agents.py`. |
| `NPCManager` | Registry of every agent's live state (`AgentState`), keyed by `AgentId`. Applies server pushes; offline fallback. |
| `NexusManager` | Frontend mirror of NEXUS's shared state — tasks, whiteboards, meeting, news, research, watchlist, memory, meeting minutes, (v0.5) paper portfolio, strategies, backtest sessions, simulation results, hall of fame, coach reports, company score, performance snapshots, and (v0.6) risk limits, risk warnings, scanner alerts, trade decisions. Diffs previous vs. new server pushes to emit discrete `task:*`/`whiteboard:*`/`meeting:*`/`news:updated`/`research:*`/`watchlist:updated`/`memory:updated`/`portfolio:updated`/`simulation:*`/`hallOfFame:*`/`coach:*`/`companyScore:updated`/`riskLimits:updated`/`riskWarnings:updated`/`scannerAlerts:updated`/`scanner:alertDetected`/`decisions:updated`/`decision:made` events rather than just handing scenes a raw blob. |
| `UpcomingEvents` | Computes each agent's next deterministic schedule-block transition from `Schedule.ts` (meetings are excluded — NEXUS calls those at random, so there's nothing genuine to predict). Shared by `BrainRoomHud` and `Newspaper` so both "Upcoming Events" sections agree instead of each re-deriving it. |
| `DialogueManager` | Per-agent, per-task flavor lines plus mood/override fallbacks; opens the React `DialogueBox` and records dialogue history. |
| `SettingsManager` | localStorage-backed user preferences. |
| `SaveManager` | Builds a full state snapshot (player/settings/dialogue **and** a copy of the current agents/tasks/whiteboards/meeting/news/research/watchlist/memory/meetingMinutes/paperPortfolio/strategies/backtestSessions/simulationResults/hallOfFame/coachReports/companyScore/performanceSnapshots for instant restore), POSTs it to the backend (with a localStorage backup), autosave interval. |
| `TileWorld` | Small helpers for building a Phaser tilemap ground layer / perimeter walls / interaction zones from a manifest asset — used by every scene so tilemap setup isn't duplicated per room. |

React state (`frontend/src/state/gameStore.ts`) is a minimal
`useSyncExternalStore`-compatible store that just listens to `EventBus` and
exposes a plain snapshot object — deliberately not a full state-management
library, since the UI's needs here are "mirror a handful of events."

## Scenes (`frontend/src/game/scenes/`)

- `BootScene` → `PreloadScene` (loads every manifest asset, builds
  animations) → `MainMenuScene`.
- `LobbyScene`: the HQ courtyard. Nine buildings (Scout Office, CEO Office,
  Brain Room, Meeting Room, Break Room, Simulation Lab, Hall of Fame,
  Performance Center, and — new in v0.6 — Trading Floor), each an
  interactable door, plus a "TradeTown Daily" newspaper stand that opens
  the React `Newspaper` modal.
- `RoomScene` (abstract base): shared floor/walls/door/camera/agent-presence
  logic for every interior. Each concrete scene (`ScoutOfficeScene`,
  `CeoOfficeScene`, `BrainRoomScene`, `MeetingRoomScene`, `BreakRoomScene`,
  `SimulationLabScene`, `HallOfFameScene`, `PerformanceCenterScene`,
  `TradingFloorScene`) just declares its size, floor tile, room label,
  and which `AgentLocation` (if any) places agents there — the base class
  spawns/despawns *however many* agents currently match that location
  (via `refreshAgentPresence`), spreading them with an overridable
  `getAgentSpawnPoint` hook so a room-specific layout (e.g. Meeting
  Room's fixed seats around the table, or the v0.5/v0.6 rooms keeping
  agents clear of their central console/scoreboard/plaque/command-display
  prop) can replace the default even-spread. `BrainRoomScene`
  additionally builds the "Mission Control" holographic market core and
  monitor desks as procedural Phaser graphics/tweens (no new art assets —
  see "Use only supplied assets" below). The v0.5/v0.6 rooms use
  `RoomScene.addLiveText()` — a small helper that renders a Phaser text
  prop and keeps it in sync with a live `EventBus` event, the in-world
  equivalent of the React HUD's reactive readouts — for their
  simulation queue, hall of fame plaque, company scoreboard, and (v0.6)
  Trading Floor's market ticker/Central Command display, and register
  themselves for automatic cleanup on `shutdown()` the same way
  `addWhiteboard()` already did.

### Door and dialogue input — read `interactPressed` exactly once per frame

`Phaser.Input.Keyboard.JustDown()` consumes the "just pressed" state the
first time it's read; reading it a second time in the same frame always
sees it as already-consumed. `RoomScene.update()` reads
`this.player.interactPressed` into a single `interacted` local up front and
reuses that for both the "talk to nearest agent" check and the "exit
through the door" check — reintroducing a second direct call to the
`interactPressed` getter anywhere else in that method silently breaks
whichever check runs second (this exact bug shipped briefly during v0.2
development: pressing E to leave a room never worked, because the
agent-dialogue check above it had already consumed the flag).

The door-exit and start-a-new-dialogue branches are also **mutually
exclusive**, guarded by `!nearDoor` and `!dialogueOpen`: a room is small
enough that the player can be within both the door zone and an agent's
interact radius at once, and the React `DialogueBox` listens for `KeyE` on
`window` independently of Phaser's own key binding to advance/close an
open conversation. Without the guard, one E press could open a dialogue
and transition the scene in the same frame (leaving the dialogue box
permanently stuck on screen, since nothing left listening could close it),
or exiting mid-conversation could do the same. `RoomScene` checks
`gameStore.getSnapshot().dialogue.open` before acting on E at all, so a
dialogue always fully owns the key while it's open.

## Agents (`frontend/src/game/entities/`)

`AnimatedActor` is the shared base for anything rendered from the
directional Player.png-style sheet (idle/walk × 4 directions) —
`PlayerController` (input-driven) and `AgentNPC` (schedule/wander-driven)
both extend it so animation/direction handling isn't duplicated. `AgentNPC`
is parameterized by `AgentId` and used for all nine agents (Scout, Atlas,
Echo, Nova, Scribe, and — new in v0.5 — Coach, Performance & Improvement)
— the only per-agent differences are sprite tint/name (from
`AgentProfiles`) and which room the current server state spawns it into.
Adding Coach required zero scene code: it's just a sixth entry in
`AGENT_IDS` with a home location like everyone else — see "Adding a new
agent" in `DeveloperGuide.md` for the general pattern.

Each agent wanders gently within its current room. Rooms like Brain Room
and Meeting Room can legitimately hold all nine agents at once (that's the
intended "Mission Control"/meeting design), and their sprites sit closer
together than a name tag is wide; rather than fight that with
ever-increasing spacing, `RoomScene.update()` shows **at most one** name
tag per frame — whichever agent is nearest the player, within
`NAME_TAG_RADIUS` (36px) — the same convention used by Stardew-style
top-down games, so a crowded room reads as a crowd instead of a wall of
overlapping text. This decision deliberately lives in `RoomScene`, not on
each `AgentNPC` independently: an earlier version had every agent check
its own distance to the player, which mostly worked but still let two
agents that were merely near *each other* (not just near the player) both
pass the check and show overlapping tags at once. Interacting opens the
full React `DialogueBox` (owned by `DialogueManager`) — there is no
separate in-world speech bubble, to avoid two overlapping text UIs firing
off the same interact press.

## Sprite sheet notes

`Player.png` (`assets/cute-fantasy-rpg/characters/player/`) only has **6 real
movement rows** (0–5: idle-down, walk-down, idle-up, idle-left, walk-left,
walk-up), verified by pixel-level inspection of every row. Rows 6–8 are
attack/action poses (sword frames) and row 9 is a faint/death pose — not
walk cycles, despite occupying plausible-looking positions in the sheet.
There is **no dedicated right-facing row at all**. `walk-right`/`idle-right`
are produced by playing the `-left` animation with the sprite horizontally
flipped (`AnimatedActor.playAnim()` maps `facing === "right"` to the
`-left` animation key and calls `sprite.setFlipX(true)`), which is the
standard Phaser approach for asset packs that only ship one side
direction. `frontend/src/assets/animation-config.json`'s `characters/player/player`
entry documents the same thing inline. An earlier, incorrect 8-row mapping
(with fabricated `idle-right`/`walk-right` entries pointing at the
attack-pose rows) shipped briefly and produced a visible glitch — a sword
and a white crescent artifact flashing over the character whenever it
moved right — caught during gameplay testing, not code review, which is
why this is called out here rather than assumed obvious from the config
file alone.

## Backend (`backend/app/`)

| Module | Responsibility |
|---|---|
| `state.py` | The single in-memory `GameState` (async-lock guarded) and its `tick()` method — advances the clock and delegates all per-agent/task/meeting/research logic to `nexus.tick()`. |
| `agents.py` | Static per-agent profile data (name, occupation, personality, home location, tint) and the `AgentLocation` → `SceneId` mapping — the single source of truth mirrored by `frontend/src/game/systems/AgentProfiles.ts`. |
| `schedule.py` | Every agent's daily routine (authoritative copy; `frontend/src/game/systems/Schedule.ts` is the offline mirror). A schedule block only describes an agent's *default* behavior — meetings and breaks are event-driven overrides NEXUS layers on top, not schedule entries. |
| `market_data.py` | The `MarketDataProvider` interface and the v0.3 `MockMarketDataProvider` implementation. See "Research & market intelligence (v0.3)" below. |
| `watchlist.py` | `WatchlistManager` — the tracked-symbol list, refreshed from `market_data.py` every tick. |
| `research.py` | `ResearchManager` — the rotating research queue (one active item per research-capable agent). |
| `discussion.py` | `DiscussionManager` — generates a meeting's discussion transcript from participants' current research focus when a meeting starts. |
| `memory.py` | `CompanyMemory` — the capped, categorized, searchable long-term log every other v0.3 manager appends to. |
| `scribe.py` | `ScribeManager` — turns research completions, meeting transcripts, and (v0.5) closed paper trades, simulation results, coach reports, and Hall of Fame entries into `CompanyMemory` records and `MeetingMinutes`; the sole writer of `CompanyMemory`, so every new v0.5 module hands Scribe the record instead of calling `memory.record()` directly. |
| `portfolio.py` | `PortfolioManager` — pure paper-portfolio bookkeeping: open/mark-to-market/close a `PaperPosition`, capped trade history. Entirely simulated; no brokerage SDK import exists anywhere in this module. |
| `paper_trading.py` | `PaperTradingManager` — decides when to open a position (from high-confidence completed research) and when to close one (past a minimum simulated hold, on a per-tick chance roll). Hold duration is tracked in simulated-clock minutes (`opened_sim_minutes`), not wall-clock time. |
| `simulation.py` | `SimulationManager` + `StrategyRunner` — the Simulation Lab's engine: queues `BacktestSession`s against seeded `Strategy` objects, advances progress each tick, and archives completed runs as `SimulationResult`s with explicitly placeholder backtest metrics (see the module docstring). |
| `analytics.py` | `AnalyticsManager` — shared metric helpers (`research_accuracy`, `win_rate`, `confidence_accuracy`, `average_confidence`) reused by `coach.py` and `company_score.py` so there's exactly one "win rate" formula, plus daily/weekly/monthly/all-time `PerformanceSnapshot` recording. |
| `company_score.py` | `PerformanceManager` — computes the seven-metric `CompanyScore` (Research Quality, Decision Quality, Risk Management, Paper Trading Performance, Team Coordination, Knowledge Growth, Simulation Success) every tick. |
| `coach.py` | `CoachManager` — Coach's reporting logic: builds a `CoachReport` (agent rankings, common mistakes, recommendations) on the weekly/monthly cadence. Coach only ever evaluates; nothing in this module places or closes a trade. |
| `hall_of_fame.py` | `HallOfFameManager` — evaluates completed research/simulations/trades/coach reports each tick and appends a `HallOfFameEntry` only when a genuinely new record is set (before/after length diffing on the caller's side). |
| `knowledge.py` | `KnowledgeManager` — derives a `lesson` (win) or `mistake` (loss) from a closed `PaperTrade`, and implements the searchable-knowledge filter contract (`search_knowledge()`) that Company Memory's six new v0.5 categories are queried through. |
| `nexus.py` | NEXUS: the orchestrator, tying every manager above together each tick. Per agent: resolves any active override (meeting/break) or falls back to the schedule block for the current hour, updates mood/energy, and creates/completes `Task`s when the schedule-driven task label changes (task lifecycle piggybacks on the same "did the block change" check schedule-following already needed, rather than a parallel system). Separately: advances the research queue, refreshes watchlist prices, ticks paper trading and the Simulation Lab, recomputes the company score, occasionally calls a meeting (`_maybe_call_meeting`) or sends a low-energy agent on a break — meetings and breaks are both the *same* `AgentOverride` mechanism (`location` + `reason` + `remainingMinutes`) rather than two bespoke state machines. On the evening/weekly/monthly/daily cadences, generates Coach reports, records performance snapshots, and evaluates the Hall of Fame. Also regenerates the whiteboard text for each office. |
| `sim.py` | The background loop: sleep → tick → broadcast over WebSocket → periodically persist to SQLite. |
| `ws_manager.py` | Tracks connected WebSocket clients; `build_state_message()` is the single place that shapes an outbound `GameSaveState` into the broadcast JSON, shared by both the sim loop and a client's initial `/ws` snapshot so the two never drift out of sync. |
| `persistence.py` | Reads/writes the single save row (`slot="default"`) as a JSON blob. Guards `GameSaveState.model_validate_json()` with a `try`/`except ValidationError` — an old-schema save fails validation and is treated as "no save" (fresh state, logged as a warning) rather than crashing the app on startup. |
| `routers/save.py` | `GET /api/load`, `POST /api/save` — merges client-owned fields (player, settings, dialogue) onto server-owned fields (agents, tasks, whiteboards, meeting, news, research, watchlist, memory, meetingMinutes, paperPortfolio, strategies, backtestSessions, simulationResults, hallOfFame, coachReports, companyScore, performanceSnapshots, time). |
| `routers/ws.py` | `/ws` — sends the current snapshot on connect, then just watches for disconnects (the sim loop drives all outbound messages). |

SQLite is deliberately a single JSON-blob row rather than a fully
normalized schema — v0.2 still has exactly one save slot and one company,
so normalizing further would be speculative. The `DATABASE_URL` env var is
already SQLAlchemy-driven, so swapping to Postgres later is a
connection-string change, not a rewrite (see "Future-ready" below).

## Tasks, NEXUS, meetings, and whiteboards

- **Task** (`Task` in `schemas.py`/`types.ts`): `id`, `owner` (`AgentId`),
  `priority`, `description`, `status` (`pending` / `working` / `completed`
  / `failed`), `createdAt`, `completedAt`. A task is created when an
  agent's schedule-driven task label changes and marked `completed` the
  next time it changes again — there's no separate "task generator";
  the schedule *is* the task source, and NEXUS just materializes each
  block transition as a `Task` record so the frontend has something
  concrete to list in the Brain Room HUD and newspaper.
- **AgentOverride**: `{ location, reason, remainingMinutes }`. The single
  mechanism behind both meetings (`reason: "meeting"`) and breaks
  (`reason: "break"`) — an override always wins over the schedule block
  for as long as `remainingMinutes` is positive, then the agent reverts to
  whatever the schedule says next. Using one shape for both means the
  frontend's dialogue fallback lines, whiteboard text, and location
  resolution only need to branch on `reason`, not maintain two parallel
  "why is this agent not where the schedule says" code paths.
- **Meetings**: each tick, NEXUS rolls `MEETING_CHANCE_PER_TICK` against
  every agent currently free (not already overridden); if enough agents
  (`MEETING_MIN_ATTENDEES`) are pulled in, they all get a `meeting`
  override pointing at `meeting-room` for `MEETING_DURATION_MINUTES`. The
  shared `MeetingState` (`active`, `participants`) drives the "Meeting in
  progress" badge in `TopStatusBar`. Dialogue during a meeting is
  placeholder flavor text (`OVERRIDE_LINES["In a meeting"]`) — the
  override/task architecture is what a future version would hang real
  AI-generated meeting discussion off of, not something v0.2 attempts.
- **Breaks**: any agent whose `energy` drops under
  `BREAK_ENERGY_THRESHOLD` has a `BREAK_CHANCE_PER_TICK` chance per tick
  of getting a `break` override to `break-room` for
  `BREAK_DURATION_MINUTES`, after which `BREAK_ENERGY_BONUS` energy is
  restored.
- **Whiteboards**: keyed by room id (`"scout-office"`, `"meeting-room"`,
  `"ceo-office"`), regenerated by `_update_whiteboards()` every tick from
  current agent/task/research state and pushed as plain strings. The
  frontend's `Whiteboard` entity is a dumb renderer — it just subscribes to
  `whiteboard:updated` filtered by its own `boardId` and displays whatever
  text arrives, so a future room only needs a new whiteboard key on the
  backend to get one. The in-world prop is a small fixed-size rectangle
  (`Whiteboard.ts`), and Phaser's `wordWrap` only wraps by width, not
  height — a v0.3 whiteboard showing a full research title plus priority
  plus confidence on three lines overflowed the board badly before
  `_truncate()` (nexus.py) capped each line's length server-side and the
  board itself was enlarged to comfortably fit two short lines. If a
  future board needs more content than two ~26-character lines, grow the
  board *and* the cap together rather than just one.
- **News** (`NewsItem`): `category` is `"company"` | `"discovery"` |
  `"market"`. `discovery` items are generated by NEXUS when an agent
  completes a task; `market` items are drawn from a fixed placeholder
  headline pool on a flat per-tick chance (no live feed yet, by design —
  see NEXUS above); `company` is reserved for future company-level
  events. The Lobby newspaper stand and Brain Room HUD both read the same
  feed, grouped by category. The persisted list is trimmed to the most
  recent `MAX_NEWS_PER_CATEGORY` items **per category**, not one shared
  cap on the combined list — discovery news fires far more often than
  market or company news (it's tied to every task-changing event across
  four agents, not a flat roll), so a single shared cap would eventually
  let discovery news evict every market headline during normal play,
  leaving the Market Status panel permanently empty. The WS broadcast
  (`ws_manager.build_state_message()`) sends that already-bounded list
  as-is; re-slicing it again there (e.g. to a flat "last 10") would
  silently undo the per-category balance the same way, which is exactly
  what shipped briefly and had to be fixed in both places at once.

## Research & market intelligence (v0.3)

TradeTown v0.3 gives every agent except Scribe a rotating research focus
and puts the results in front of the player (Brain Room HUD, newspaper,
whiteboards, Company Memory). None of it is real market data and none of
it places a trade — see the "STOP CONDITION" the v0.3 brief was built
against.

- **`MarketDataProvider`** (`market_data.py`): an `ABC` with `get_quote`/
  `get_quotes`. The only implementation shipped is `MockMarketDataProvider`
  — a per-symbol seeded random walk, no network calls. `_select_provider()`
  reads `MARKET_DATA_PROVIDER` from the environment; any value other than
  `"mock"` (or unset) logs a warning and falls back to mock, since no real
  adapter exists yet and this repo holds no API keys. **To add a real
  provider later**: implement the interface (wrap that vendor's HTTP
  client), register it in `_select_provider()`, done — `watchlist.py` only
  ever calls `get_quotes()`, so nothing downstream changes.
- **Watchlist** (`watchlist.py` / `WatchlistEntry`): a fixed 8-symbol seed
  list (`SEED_SYMBOLS`), one per `ResearchCategory` in the brief (stock,
  ETF, index, economy, gold, bitcoin, company, sector). Prices refresh
  from the configured provider every tick; `status`/`researchProgress`/
  `assignedAgent` are synced from whichever `ResearchItem` (if any)
  currently targets that symbol.
- **Research queue** (`research.py` / `ResearchItem`): every
  research-capable agent (`scout`, `atlas`, `echo`, `nova` — not `scribe`,
  who records rather than researches) always has exactly one item
  `"in_progress"`. Confidence climbs by a random amount each tick; on
  reaching 100 the item is marked `"completed"`, the agent immediately
  rotates onto a new symbol (preferring one nobody else is currently on),
  and `tick_research()` returns the just-completed item in a separate list
  so the caller can react without this module needing to know about
  news/memory schemas. Completed history is capped per agent
  (`MAX_RESEARCH_HISTORY_PER_AGENT`) so the queue stays bounded instead of
  growing forever.
- **Discussion & minutes** (`discussion.py`, `scribe.py` /
  `MeetingMinutes`): when `_maybe_call_meeting()` starts a meeting,
  `generate_discussion()` builds one templated line per attendee from
  their *current* research focus (Scout reports news, Echo comments on
  technicals, Nova on fundamentals, Atlas summarizes/decides, Scribe notes
  it for the record) and stores it on `MeetingState.discussion`. Lines are
  templated, not model-generated — the brief is explicit that placeholder
  text is fine here, what matters is that the discussion is driven by real
  research state. When the meeting ends, `scribe.build_minutes()` turns
  that transcript plus the participant list into a `MeetingMinutes`
  record, and `scribe.record_meeting()` logs it into `CompanyMemory`. Note
  `build_minutes()` only cites each participant's **current** (`
  in_progress`) research item, not their full history on that agent —
  research also holds completed items, and citing all of them would claim
  the meeting covered everything an attendee has ever researched instead
  of what was actually discussed that time.
- **CompanyMemory** (`memory.py` / `MemoryRecord`): a single capped,
  categorized log (`research` / `meeting` / `whiteboard` / `event` /
  `discussion` / `discovery` / `future_trade`) that every other v0.3
  manager appends to via `record()` rather than constructing
  `MemoryRecord`s itself, so the id format and the `MAX_MEMORY_RECORDS`
  cap live in exactly one place. `search()` filters an in-memory list by
  category/substring; the frontend's `CompanyMemory.tsx` viewer currently
  filters the already-WS-synced list client-side rather than round-
  tripping a query, so `search()` mostly documents the filter contract a
  future REST search endpoint would reuse.
- **"Future trade" flags**: when a completed research item's confidence
  crosses `FUTURE_TRADE_CONFIDENCE_THRESHOLD` (85%), `scribe.py` logs a
  `future_trade`-category memory record explicitly stating no trade was
  placed. This is the entire "future trades" surface in v0.3 — a
  human-readable flag for later, not a queued or simulated order.

## Paper trading, simulation & coaching (v0.5)

TradeTown v0.5 adds a fully simulated trading loop on top of v0.3's
research pipeline, plus a Coach agent that evaluates it. None of it
connects to a real brokerage or places a real trade — see the "STOP
CONDITION" the v0.5 brief was built against.

- **Paper Trading** (`portfolio.py` + `paper_trading.py`): a single
  `PaperPortfolio` starts at $100,000. When a research item completes
  above `FUTURE_TRADE_CONFIDENCE_THRESHOLD` (the same 85% threshold that
  already flagged "future trade candidates" in v0.3), `paper_trading.py`
  may open a `PaperPosition` sized as a fraction of cash. Positions
  mark-to-market every tick from the watchlist's current price; after a
  minimum simulated hold (`MIN_HOLD_MINUTES`, tracked via
  `opened_sim_minutes` — the same sim-time-not-wall-clock convention
  research confidence already uses), a per-tick chance roll closes the
  position into a `PaperTrade` with PnL, duration, and supporting/opposing
  agents. `portfolio.py`'s module docstring is explicit: no brokerage SDK
  import exists anywhere in this codebase.
- **Simulation Lab** (`simulation.py`): four seed `Strategy` objects
  (one per researcher agent) can be queued into a `BacktestSession`
  against a random watchlist symbol, advance through `queued` → `running`
  → `completed`, and archive as a `SimulationResult`. The backtest metrics
  are explicitly placeholder math (see the module's docstring) — v0.5 has
  no real historical `MarketDataProvider`, only the live-quote mock from
  v0.3. The module is structured so a real historical provider, a Monte
  Carlo variant (many placeholder runs per session), or a parameter
  optimizer can all be added later as new functions that still produce a
  `SimulationResult`, without touching the queueing/progress/archiving
  pipeline — see `docs/FUTURE_ARCHITECTURE.md`.
- **Learning System** (`knowledge.py`): every closed `PaperTrade` is fed
  to `derive_lesson()`, which returns a `(category, title, body)` tuple —
  `lesson` on a win, `mistake` on a loss — that `scribe.py` records into
  Company Memory. This is TradeTown's training-data record: reason, market
  conditions, confidence, entry/exit, PnL, duration, and supporting/
  opposing agents all live on the one `PaperTrade` model, so nothing
  downstream needs a second "trade history" shape.
- **Company Score** (`company_score.py`): a mean of six sub-scores
  (research quality via `analytics.research_accuracy()`, decision
  quality, risk management from portfolio drawdown/concentration, paper
  trading performance, team coordination from average agent mood,
  knowledge growth from lesson/mistake/strategy memory counts) plus
  simulation success (average win rate of the last 10 results), recomputed
  every tick. All new scoring functions default to `50.0` — the neutral
  midpoint — rather than `0.0` when there's no data yet, so a fresh
  company doesn't look like it's failing on day one.
- **Coach** (`coach.py`): builds a `CoachReport` — company score, agent
  rankings (via `AgentScore`, one row per researcher, sorted by score
  descending), research/confidence accuracy, win/loss rate, risk score,
  common mistakes, and recommendations — on a weekly (every 7th day) and
  monthly (every 30th day) cadence, both triggered at the 20:00 evening
  review. Coach only ever evaluates; `coach.py` never calls into
  `portfolio.py` or `paper_trading.py` to place or close anything.
- **Hall of Fame** (`hall_of_fame.py`): every tick, `evaluate_hall_of_fame()`
  checks eight categories (best research, best strategy, best simulation,
  lowest drawdown, longest winning streak, highest confidence accuracy,
  best monthly performance — monthly reports only, weekly reports skip
  this one — and top agent) and appends a `HallOfFameEntry` only when the
  new value actually beats the previous best (`_maybe_file()`'s
  append-only, before/after-length-diffing pattern — `nexus.py` uses the
  same trick to know which entries are new *this* tick, so it only logs
  what actually changed to Company Memory rather than re-logging the
  entire archive every tick).
- **Restart-safe daily/weekly/monthly triggers**: `nexus.py` checks
  `new_time.hour == 20 and new_time.minute == 0` for the evening review,
  `new_time.day % 7 == 0` for weekly, and `% 30 == 0` for monthly —
  stateless checks against the current tick's time rather than diffing
  against the previous tick. `GAME_MINUTES_PER_TICK` always divides 60
  evenly, so every day passes through exactly that hour/minute
  combination once regardless of backend restart timing, which a
  diff-against-previous-tick approach couldn't guarantee.

## Paper trading operations (v0.6)

v0.6 keeps v0.5's mark-to-market/hold-duration closing logic in
`paper_trading.py` exactly as it shipped, but moves *opening* a position
behind a full decision pipeline. Nothing below connects to a real
brokerage — see each module's own docstring for the enforcement
boundary, same convention as every earlier version.

- **Order of operations, per tick** (`nexus.py`'s `tick()`): Pulse's
  scanner runs first off the freshest watchlist prices
  (`scanner.tick_scanner()`); then `broker.tick_broker()` fills any
  orders placed on *earlier* ticks (guaranteeing at least one tick of
  latency between an order being placed and it being eligible to fill);
  then Guardian's standing risk watch refreshes
  (`risk_engine.monitor_portfolio()`); then this tick's freshly completed
  research items become **trade proposals** awaiting the CEO's decision
  (`nexus._generate_trade_proposals()` — see "Executive Voting" below,
  not an automatic vote-and-execute step since v0.6.3); any proposal left
  unactioned past its expiry window auto-resolves as WAIT
  (`executive.expire_stale_proposals()`); then v0.5's hold-duration
  closing logic runs (`paper_trading.tick_paper_trading()`); then every
  trade that closed this tick (from either the broker or the
  hold-duration closer) gets journal-stamped
  (`nexus._journal_closed_trades()`); then any `CeoDecisionRecord` still
  `"pending"` is graded against that fresh trade history
  (`executive.grade_ceo_decisions()`).
- **Decision Voting, pre-v0.6.3** (`voting.py` + `decision.py`, superseded
  below): a trade candidate collected one vote from each of the four
  researcher agents plus Sentinel's and Guardian's risk-derived votes,
  and `decision.decide_trade()` turned the vote set into an
  automatic trade/no-trade outcome (a hard risk veto, else majority
  `buy`). `voting.researcher_vote()` (the per-researcher-agent vote
  template) is still reused by Executive Voting's news/macro seats below;
  `decision.decide_trade()` itself is no longer called anywhere.
- **Executive Voting (v0.6.3, `executive.py`)**: the player is TradeTown's
  CEO — a trade candidate no longer executes automatically. It becomes a
  `TradeProposal` with six independent, evidence-backed analyst votes
  (`generate_analyst_votes()`): technical (Echo) reads real trend/
  volatility off the symbol's own candles; news/macro (Scout/Nova) reuse
  `voting.researcher_vote()`'s existing template; risk (Sentinel) reuses
  a real `RiskWarning` if one exists; sentiment (Pulse) reuses a real
  `ScannerAlert` if one exists; execution (Atlas) is the desk's own
  majority, not a seventh independent signal. `POST /api/executive/decide`
  (`state.py`'s `submit_ceo_decision()`) resolves a proposal against the
  player's real buy/sell/wait call (`resolve_proposal()`): buy/sell that
  clears the v0.7 Feature 20 Trade Gatekeeper below opens a real position
  immediately (a live player action, not tick-driven — unlike broker
  orders, no extra latency tick), producing a permanent `TradeDecision`
  (same shape every existing consumer — DecisionsPanel, DecisionDetail,
  Player vs AI — already depends on) plus a `CeoDecisionRecord` tracking
  CEO/AI accuracy, agreement, and successful/failed overrides.
  `CeoDecisionRecord.outcome` and `TradeDecision.outcome` are both keyed
  off `order_id is not None` — the real signal of whether a position
  actually opened — not off `ceoDecision` being buy/sell, since a
  Gatekeeper-rejected trade keeps the CEO's real original buy/sell choice
  on record without a position ever opening.
  `CeoDecisionRecord.outcome` only ever resolves to `correct`/`incorrect`
  once a real trade the decision caused has actually closed; a plain wait,
  a Gatekeeper rejection, or an override all stay `"undecidable"` — an
  override's real trade tells us whether the CEO's own call worked, never
  whether the AI's original (never-taken) direction would have, so that's
  never guessed at.
- **Trade Gatekeeper (v0.7 Feature 20, `gatekeeper.py`)**: sits between
  the CEO's real buy/sell call and `open_position()` — `resolve_proposal()`
  calls `evaluate_gatekeeper()` and only opens the position if the
  returned `GatekeeperVerdict.approved` is true, so even the player's own
  choice can be vetoed (the v0.6.3 "the CEO's choice is unconditionally
  final" model no longer holds). Seven checks, each reading real state
  computed elsewhere: Decision Confidence Engine score vs. `MIN_CONFIDENCE`
  (Feature 15), Sentinel's risk-vote alignment, multi-agent majority
  agreement, the AI Debate's `finalRecommendation` (Feature 17, passed in
  by `state.py` from the most recent `Debate` for the proposal), portfolio
  exposure vs. `RiskLimits.maxOpenPositions`, correlated open positions
  sharing the proposal's `SYMBOL_CATEGORY` lookup (capped at
  `MAX_CORRELATED_POSITIONS`), and any active *critical* Sentinel/Guardian
  `RiskWarning` for the symbol. The brief's longer checklist (multi-
  timeframe confirmation, support/resistance, volume confirmation,
  liquidity, news *timing*, reward-to-risk, stop-loss placement, strategy
  match, historical similar-setup performance) has no real data source in
  this codebase and is deliberately not computed — see the module
  docstring. A rejected trade never executes, so there's no real P&L to
  grade: `GatekeeperRejection` instead records the symbol's real price at
  rejection and `grade_gatekeeper_rejections()` (called every `nexus.tick()`)
  resolves `would_have_won`/`would_have_lost` once
  `GATEKEEPER_EVAL_WINDOW_MINUTES` of simulated time have passed, purely
  from the symbol's own real subsequent watchlist price — the same
  "wait for real time, check real data" shape `grade_ceo_decisions()`
  already uses for placed trades, just against watchlist price instead of
  a closed `PaperTrade`.
- **RiskEngine** (`risk_engine.py`): pure evaluation, no side effects.
  `evaluate_sentinel_risk()` is the hard trade-approval gate (equity ≤ 0,
  drawdown past `maxDrawdownPct`, open-position count past
  `maxOpenPositions`, or position size past `maxPositionPct` — checked in
  that order, first violation wins). `evaluate_guardian_exposure()` is
  the softer per-candidate concentration check; `monitor_portfolio()` is
  Guardian's every-tick standing watch, independent of any new candidate.
  TradeTown has no real sector taxonomy (`ResearchCategory` isn't one),
  so "sector concentration" is implemented as per-symbol concentration of
  portfolio equity — an intentional, documented simplification, not a
  missed requirement.
- **PaperBroker** (`broker.py`): owns the order book.
  `place_order()` appends an `open` `PaperOrder`; `tick_broker()`
  evaluates every open order against current watchlist prices and fills
  it if its trigger condition is met. `market` fills at the current
  quote; `limit`/`take_profit` share one fill direction (buy at-or-below,
  sell at-or-above the target); `stop`/`stop_loss` share the opposite
  direction (buy at-or-above, sell at-or-below the trigger) — unified
  into one `_fill_price()` rather than four near-duplicate branches. An
  order with a `linkedPositionId` is an exit order against an existing
  position (closes it via `portfolio.close_position()`); one without is
  an entry order that opens a new position on fill
  (`portfolio.open_position()`, now accepting an explicit `quantity` so
  the broker can size from `risk_engine.recommended_quantity()` instead
  of `portfolio.py`'s v0.5 flat-fraction default).
- **ScannerManager** (`scanner.py`): reads quotes from the same
  `MarketDataProvider` watchlist uses, classifies each symbol against
  gap up/down, breakout (a large move plus a volume spike in the same
  tick), volume spike, and high-volatility thresholds, and rolls a
  per-tick chance to alert so a symbol sitting past a threshold doesn't
  spam an alert every single tick. Detection is threshold-based against
  the current quote only — no rolling price history is persisted yet, so
  "breakout" here isn't a true multi-period range breakout; see the
  module docstring and `docs/VersionHistory.md`'s v0.7 candidates.
- **TradeJournal** (`journal.py`): stamps a closed `PaperTrade` with
  `coachReview`/`lessonsLearned` (reusing `knowledge.derive_lesson()`'s
  exact judgment rather than writing a second, possibly-diverging
  version), a best-effort `decisionId` (most recent `trade`-outcome
  `TradeDecision` for the same symbol — neither `PaperOrder` nor
  `PaperPosition` carries a decision id through to the eventual trade,
  so this is attribution by recency, not a guaranteed exact link), and a
  fixed `screenshot` placeholder string (TradeTown has no
  chart-rendering pipeline to capture a real one from). This also closes
  a v0.5 gap: `coachReview`/`lessonsLearned` existed in the schema since
  v0.5 but nothing had ever populated them before v0.6.
- **Trading Floor** (`frontend/src/game/scenes/TradingFloorScene.ts`):
  home to Sentinel, Pulse, and Guardian. Its market ticker and Central
  Command display read live off `NexusManager` the same way the Brain
  Room's holographic core and Performance Center's scoreboard already
  do — in-world text for at-a-glance state, the Brain Room HUD React
  overlay for full detail — rather than duplicating the HUD's detail
  in-world.

### Gotcha: `model_copy(update=...)` uses field names, not wire aliases

Every `CamelModel` field with a camelCase wire alias (e.g.
`meeting_minutes` aliased to `"meetingMinutes"`) is constructed and
*validated* with either name, because `populate_by_name=True`. But
`BaseModel.model_copy(update={...})` bypasses validation entirely and
writes straight into the model's `__dict__` — which is keyed by the
Python field name, never the alias. Passing the alias as an update key
doesn't raise; it silently creates an unused phantom entry and the real
field keeps its old value forever. This shipped briefly in `nexus.tick()`
(`"meetingMinutes"` and `"updatedAt"` instead of `"meeting_minutes"` and
`"updated_at"`) and meant meeting minutes/memory records from a completed
meeting never actually got attached to the returned state, despite every
manager function along the way executing correctly — the bug was invisible
in unit-style testing of each function and only showed up as "meetings
start and end but nothing is ever recorded" under an end-to-end soak test.
**Always use the Python field name in a `model_copy(update=...)` dict,
never the alias**, regardless of what key format `model_dump(by_alias=True)`
or the constructor accepts elsewhere in the same file.

This exact bug recurred once, in a different function, before it was
fully stamped out: `_tick_agent()`'s and `_maybe_call_meeting()`'s
`AgentState.model_copy(update={"currentTask": ...})` calls both used the
alias instead of `current_task`, so every agent's task text froze
forever at whatever `_default_agent_state()` set it to, while `location`
(no alias, so unaffected) kept updating normally right next to it in the
same dict — invisible unless you're actually reading the task text, since
the location alone still looked correct. Caught by walking into a room
and noticing an agent's location and task belonged to two different
schedule blocks. When adding a new `model_copy(update=...)` call
anywhere in this codebase, grep `backend/app/schemas.py` for
`Field(alias=` and check every key in the update dict against that list
first — there are enough aliased fields by now that guessing wrong is
the likely outcome, not the exception.

## Asset pipeline

`scripts/generate-assets.mjs` walks `assets/cute-fantasy-rpg/` (the single
source of truth for art), wipes and rebuilds a mirror of it under
`frontend/public/assets/` (a full re-sync, not an additive copy — a
renamed or removed source file doesn't leave an orphaned stale copy
behind), reads each file's real dimensions from its PNG header, and writes
`frontend/src/assets/manifest.generated.json`. Frame-layout metadata that
can't be inferred from pixel data (which row is "walk-down", tile grid
size, …) lives in the hand-authored
`frontend/src/assets/animation-config.json` and is merged in by id. Nothing
in game code ever references a file path — everything goes through
`AssetLoader.get(id)`, where the id mirrors the source folder path (e.g.
`props/buildings/windmill`, `characters/player/player`). Adding a new
sprite to the pack and re-running `npm run assets:sync` (wired into
`predev`/`prebuild`) makes it available with zero code changes; only
*animating* it requires an entry in `animation-config.json`.

Art is organized into five top-level folders, each mapped to a manifest
category by `categoryFromRelPath()`: `tilesets/` (ground tile sheets),
`characters/{player,enemies,animals}/` (anything with a movement/pose
sheet), `props/` (static world objects, including `buildings/`),
`animations/` (small looping decorative sprites — pond life, swaying
grass), and `ui/` (icon sheets, currently staged for future use rather
than drawn anywhere). Curated deliberately, not dumped wholesale — the
premium Cute Fantasy pack ships hundreds of files (mounts, crops, cave
tiles, weather effects, …) that don't fit TradeTown's office-simulation
setting; only pieces that are actually used or clearly reusable get
imported, keeping the served bundle from bloating with dead weight.

## Production hardening notes

A few deployment details that are easy to get subtly wrong, documented
here so they don't get "fixed" back into a broken state later:

- **The backend must stay single-process.** `GameState` (`backend/app/state.py`)
  is an in-memory singleton, and `sim.py` runs one background tick loop.
  Adding `--workers N` to the backend's uvicorn command (or otherwise
  running multiple backend replicas) would give each process its own
  disconnected copy of the simulation and let their SQLite writes race —
  don't do that without first moving shared state into the database or a
  shared store.
- **`backend/Dockerfile` runs as a non-root `app` user.** The `chown` on
  `/app/data` happens *before* `USER app` and *before* the `VOLUME`
  declaration, which matters — a named volume created on first run inherits
  the image's permissions at that path, so getting the order right is what
  makes the mounted volume writable by a non-root process instead of
  root-owned.
- **`frontend/deploy/nginx.conf`'s `proxy_pass` targets go through a `set
  $backend ...` variable**, not a literal `http://backend:8000/api/`. This
  is required for nginx to re-resolve the `backend` hostname periodically
  (via the `resolver 127.0.0.11` directive, Docker's embedded DNS) instead
  of caching it for the life of the nginx process — otherwise recreating
  the backend container (any `docker compose up -d --build` that changes
  it) can leave nginx pointing at a stale, now-dead IP. The tradeoff:
  nginx's usual "replace the location prefix with the proxy_pass path"
  rewriting only happens for *literal* proxy_pass targets, not variable
  ones — with a variable, the original request URI is passed through
  unmodified instead. That happens to be exactly what's wanted here (the
  backend's own routes already expect the `/api/` prefix), but it's a real
  nginx gotcha worth knowing about before "simplifying" this back to a
  literal URL.
- **`.dockerignore` (repo root) and `backend/.dockerignore` matter more than
  they look.** `frontend/Dockerfile`'s builder stage does `COPY frontend ./`
  *after* running `npm ci`, specifically so Docker's layer cache can reuse
  the `npm ci` step when only source files change. If a local
  `frontend/node_modules` exists on whatever machine runs `docker build`
  (e.g. a dev checkout that's had `npm install` run locally) and isn't
  excluded, that `COPY` would silently overwrite the image's freshly
  installed `node_modules` with the host's — usually version-inconsistent,
  sometimes architecture-inconsistent. The `.dockerignore` files are what
  prevent that class of "works on my machine, breaks in Docker" bug.

## Version 0.1 scope (for reference)

Built: main menu, HQ lobby + 3 interior rooms, camera-follow smooth
movement with collision, one NPC (Scout) with schedule/mood/energy/memory/
dialogue, top status bar + toolbar + settings + pause UI, save/load
(autosave + manual, backend-persisted with a localStorage fallback), a live
WebSocket simulation feed, Docker Compose deployment with an nginx reverse
proxy, and day/night architecture (`TimeManager.isDay` /
`isDaytime()` are wired through, though only a status-bar/clock consumes it
today — a visual day/night tint remains a natural future addition, not
built yet to avoid speculative rendering work). Weather is likewise
architected for (the clock/tick model has room for it) but not implemented.

## Version 0.2 scope

Built on top of v0.1 without touching its stable systems more than
necessary: three new agents (Atlas, Echo, Nova) each with a distinct
personality/daily schedule/home room, two
new interior rooms (Meeting Room, Break Room) plus an upgraded Brain Room
("Mission Control" — animated holographic market core, monitor desks, and
a React `BrainRoomHud` overlay panel), a fifth Lobby door and a newspaper
stand, a reusable server-authoritative `Task` system, the NEXUS
orchestrator (task assignment, meetings, breaks, whiteboards, discovery
news — see above), whiteboards in every office, an extended save schema
covering every agent's location/mood/task/override plus tasks/whiteboards/
meeting/news/time, and per-agent personality-flavored dialogue.

Explicitly **not** in v0.2 (by design, not oversight): any real market
data connection (NEXUS is wired to *look* connected — Task/News/whiteboard
plumbing all exist — but "Market Status" is placeholder copy throughout),
AI-generated meeting discussion (meetings run on the same
override/dialogue-fallback mechanism as breaks, with placeholder lines,
not a model call), combat/enemies (still discovered/manifest-registered,
still unused), broker API integration, Postgres/Redis, multiplayer, and
any monetization.

## Version 0.3 scope

Built on top of v0.2 without touching its stable systems more than
necessary: a fifth agent (Scribe, the company historian — home location
Brain Room, no new room required), the `MarketDataProvider` interface +
mock adapter, a `Watchlist` of 8 seed symbols, a rotating `ResearchItem`
queue with per-agent confidence, meeting discussions/minutes recorded by
Scribe, a searchable `CompanyMemory` log with a dedicated viewer
(`CompanyMemory.tsx`, opened from the toolbar), an upgraded Brain Room HUD
(Market Clock, Research Queue, Watchlist, Upcoming Events, animated
confidence/progress bars), an upgraded newspaper (Research Updates, Agent
Activity, Upcoming Events sections), richer whiteboard text, extended
`Task` categories (`research`/`review`/`meeting`/`watchlist_update`/
`news_scan`/`chart_analysis`/`documentation`), and an extended save schema
covering research/watchlist/memory/meetingMinutes.

Explicitly **not** in v0.3 (per the brief's STOP CONDITION, not oversight):
paper trading, brokerage connections, live trading of any kind, or a real
market data API call (`MockMarketDataProvider` is the only implementation
shipped — see "Research & market intelligence (v0.3)" above for the
adapter pattern a future version would use to add one). "Future trade"
flags are a logged note for a human, never a queued or simulated order.

## Version 0.4 scope

Documentation only — see `docs/VersionHistory.md`'s "v0.4 — Design &
Architecture Foundation" entry. No application code changed; v0.3
continued running exactly as it did before this version, and the save
schema's `version` field stayed `"0.3"`.

## Version 0.5 scope

Built on top of v0.3 (v0.4 made no code changes) without touching its
stable systems more than necessary: a sixth agent (Coach — home location
Performance Center, a new room), the Paper Trading engine (`portfolio.py`
+ `paper_trading.py`), the Simulation Lab (`simulation.py`, a new room),
Company Score (`company_score.py`), Coach reports and the Coach Dashboard
(`coach.py`), the Hall of Fame (`hall_of_fame.py`, a new room), the
Learning System (`knowledge.py`), performance analytics
(`analytics.py`), six new Company Memory categories, an expanded Brain
Room HUD (Company Rating, Paper Portfolio, Simulation Queue, Agent
Performance, Learning Progress sections), an eight-door Lobby, and an
extended save schema covering paperPortfolio/strategies/
backtestSessions/simulationResults/hallOfFame/coachReports/companyScore/
performanceSnapshots.

Explicitly **not** in v0.5 (per the brief's STOP CONDITION, not
oversight): live brokerage support, a connection to Charles Schwab or any
other broker, or execution of a single real trade. Every `PaperOrder`,
`PaperPosition`, and `PaperTrade` is simulated bookkeeping only — see
"Paper trading, simulation & coaching (v0.5)" above for the enforcement
boundary.

## Version 0.6 scope

Built on top of v0.5 without touching its stable systems more than
necessary: three new agents (Sentinel, Pulse, Guardian — home location
Trading Floor, a new room), the Decision Voting pipeline (`voting.py` +
`decision.py`), the Risk Engine (`risk_engine.py`), the Market Scanner
(`scanner.py`), the order-book PaperBroker (`broker.py`), the Trading
Journal (`journal.py`), an expanded Brain Room HUD (Open Positions,
Pending Orders, Risk Management, Latest Decision & Votes, Scanner Alerts
sections), an expanded newspaper (Today's Trades, Top Opportunities,
Performance, Coach's Review, Scanner Alerts, Company Rating sections), a
nine-door Lobby, and an extended save schema covering
riskLimits/riskWarnings/scannerAlerts/decisions plus new fields on
`PaperOrder` (orderType/linkedPositionId/filledPrice/filledAt) and
`PaperTrade` (decisionId/screenshot). v0.5's paper-trading *closing*
logic (`paper_trading.py`) is unchanged — only *opening* a position moved
behind the new voting/risk/broker pipeline; see "Paper trading operations
(v0.6)" above for the exact per-tick order of operations.

Explicitly **not** in v0.6 (per the brief's STOP CONDITION, not
oversight): live brokerage support, a connection to Charles Schwab or any
other broker, or execution of a single real trade. Every `PaperOrder`,
`PaperPosition`, and `PaperTrade` is simulated bookkeeping only —
`broker.py`'s module docstring is explicit that no brokerage SDK import
exists anywhere in this codebase, though its `place_order()`/
`tick_broker()` shape is deliberately adapter-friendly for a future
version.

## Version 0.7 scope

Six intelligence/decision systems layered onto v0.6.3's Executive
Voting rather than replacing it — every new module reuses the six real
analyst votes (`app/executive.py`'s `generate_analyst_votes`) or the
real candle series it already fetches, never a second parallel data
source:

- `app/confidence.py` — the Decision Confidence Engine (Feature 15):
  formalizes v0.6.3's client-side "Trade Quality Score" into a real,
  persisted, six-factor score computed once at proposal time and carried
  onto the resulting `TradeDecision`.
- `app/whatif.py` — the What-If Simulation Lab (Feature 16): a bootstrap
  Monte Carlo over the symbol's own real recent bar-to-bar returns,
  stress-tested against 12 named scenarios. Deliberately not part of
  `GameSaveState` — computed fresh via `GET /api/executive/whatif` on
  every request instead (see the module's own docstring for why).
- `app/debate.py` — the AI Debate Room (Feature 17): generates one
  `Debate` per `TradeProposal` (opening statement + real cross-
  examination per analyst), stored permanently and capped at
  `MAX_DEBATES` (60) the same way `ceo_decisions` is capped.
- `app/coach.py` extensions — the Decision Journal & Mistake Tracker
  (Feature 18): two new recurring-mistake patterns (`_override_mistakes`,
  joining `CeoDecisionRecord` against the `TradeDecision` that produced
  it) and a new `_strengths` function, both folded into the existing
  weekly/monthly `CoachReport` pipeline rather than a parallel journal
  system.
- `frontend/src/ui/components/TradeOutcomeBanner.tsx` — the Premium
  Trade Outcome Banner (Feature 19): replaces the old blocking
  `TradeOutcomePopup.tsx` (deleted) with a non-blocking, top-center,
  queued banner. Purely a frontend/presentation change — no new backend
  module.
- `app/gatekeeper.py` — the Trade Gatekeeper (Feature 20): a final-
  approval veto between the CEO's real buy/sell call and
  `open_position()` (see the "Trade Gatekeeper" bullet above), plus
  `grade_gatekeeper_rejections()`'s self-evaluation grading, called every
  `nexus.tick()` right after `grade_ceo_decisions()`.

`GameSaveState` gained two new fields for this pass: `debates` and
`gatekeeperRejections` (both capped, broadcast over the WS state message
and `/api/load`, same pattern as `ceoDecisions`). `TradeDecision` also
gained `gatekeeperVerdict` (null for decisions predating Feature 20).
`WhatIfSimulation`/`ScenarioResult` are real Pydantic models but
intentionally never touch `GameSaveState` — see `app/whatif.py`'s module
docstring.

## Version 0.7 scope, continued — AI Company Management (Features 21-23)

Three more systems, shifting focus from individual trades to the company
as a whole:

- **Company Operating Modes (Feature 21)**. `settings.operatingMode`
  (`learning | assisted | executive`) is a client-authoritative field —
  same mechanism as `showFps`/`musicVolume` — that NEXUS itself reads
  every tick via a new `nexus._apply_operating_mode()` sweep. Learning
  Mode (the default) is a no-op: every `TradeProposal` still waits for a
  real `POST /api/executive/decide` call. Assisted/Executive Mode call
  the exact same `resolve_proposal()` a real CEO click would (Gatekeeper
  included), just with a new `resolved_by: "auto"` tag on the resulting
  `CeoDecisionRecord` — this is the honest-provenance mechanism that lets
  the UI never claim an auto-resolved decision was the player's own.
  `app/executive.py`'s new `is_significant_proposal()` decides what
  Assisted Mode still surfaces to the player, reusing
  `gatekeeper.MIN_CONFIDENCE` and `RiskLimits.maxPositionPct` rather than
  adding new thresholds. The sweep re-processes the *entire* current
  `trade_proposals` list every tick (not just new arrivals), so switching
  modes mid-game immediately takes effect on the existing backlog.
- **Market Environment Simulation (Feature 22)**. `app/market_environment.py`
  classifies the whole watchlist into one of five regimes every tick from
  the same `WatchlistEntry.dailyChangePct` values the old client-side
  `marketRegimeHeuristic` (now removed) used — no new data fetch. A
  persisted `MarketEnvironmentState.timeline` only grows on a real regime
  change (capped at `MAX_MARKET_ENVIRONMENT_HISTORY`), and each real
  change publishes a real `NewsItem`. `nexus.py`'s existing random-
  headline roll now draws from `MARKET_HEADLINES_BY_REGIME[current]`
  instead of one shared pool — the one real "department reacts to
  conditions" hookup implemented; the brief's deeper researcher-workload/
  NPC-dialogue/discrete-event mechanics have no real trigger source in
  this codebase and are documented as not computed, not faked, in the
  module's own docstring.
- **Company Health & Stability System (Feature 23)**. `app/company_health.py`
  computes a second, independent scorecard from `company_score.py`'s
  `CompanyScore` — deliberately overlapping in a couple of underlying
  signals (e.g. `employeeMorale` reads the same real agent-mood average
  `teamCoordination` does) but answering "is the company stable?" rather
  than "is it winning?". All ten sub-metrics read data already tracked
  elsewhere (risk warnings, agent locations/mood, research completion,
  portfolio P&L, agent energy, hall-of-fame count, signal-calibration
  level, extra watchlist symbols, completed lessons) — no new simulation
  state was introduced to feed it. `overall` is a plain mean (no hidden
  weighting, matching `CompanyScore`'s own convention); recommendations
  name the two lowest metrics and only appear once one actually falls
  below 70.

`GameSaveState` gained `marketEnvironment` and `companyHealth` (both
required fields, following `companyScore`'s own convention — old saves
get them backfilled from `default_state()` by the existing generic
deep-merge migration in `persistence.py`, no special-case migration
code needed). `CeoDecisionRecord` gained `resolvedBy`. `SettingsState`
gained `operatingMode`.

Explicit scope cuts for this pass: "Executive Reports" reuses the
existing Coach weekly/monthly report pipeline (Feature 18) rather than a
second report engine; "NPC Interactions" (remembering conversations,
building relationships) has no new relationship/memory system — the
existing dialogue/`CompanyMemory` infrastructure is the honest ceiling
given no new persisted-relationship state was added.

## Version 0.7 scope, continued — Executive AI & Academy (Features 24-25)

A tenth agent and a company-wide learning system.

- **Chief Investment Officer (Feature 24)**. Meridian is added exactly
  the way every prior agent was: `AgentId`/`AGENT_IDS` gain `"cio"`,
  `AgentLocation`/`SceneId` gain `executive-boardroom`/
  `ExecutiveBoardroomScene`, `agents.py` gets a real `AgentProfile`
  entry, `schedule.py` gets a real 8-block daily routine, and the
  frontend mirrors all of it (`AgentProfiles.ts`, `Schedule.ts`,
  `DialogueManager.ts`). The one genuinely new piece is
  `app/executive_review.py`'s `generate_executive_review()`, wired into
  `nexus.tick()` on the exact same monthly cadence as
  `generate_coach_report("monthly", ...)` (see `MONTHLY_INTERVAL_DAYS`).
  Like `CoachReport`, it's a fresh cumulative snapshot over each
  already-capped recent-history list (`research`, `decisions`,
  `debates`, `news`) rather than a precisely period-windowed query —
  the same convention this codebase already uses everywhere (see
  `docs/API.md`'s bounding table). `companyScoreChange` is the one true
  period-over-period figure: a real delta against the previous review's
  own stored `companyScore`. The CIO deliberately has no vote-generation
  or trading logic of its own — `is_significant_proposal`/
  `_apply_operating_mode` never reference it.
  - The CIO's sprite (`Player_Meridian.png`) required inventing a
    process the codebase's own comment on the original nine
    (`animation-config.json`'s `_comment_agent_variants`) didn't fully
    specify — "hue-shifted," but not which pixels. Comparing the base
    sheet against all nine existing variants pixel-by-pixel showed
    exactly which of the sheet's colors are always recolored (hair,
    shirt, pants — 7 distinct color slots) vs. always preserved (skin,
    outline, shadow — 8 slots), then a slate-grey/gold/charcoal palette
    was hand-picked for those 7 slots for an executive read, distinct
    from all nine existing tints.
  - `ExecutiveBoardroomScene.ts` is sized 34×22 tiles — larger than
    every other room (Trading Floor, the next-largest, is 22×15) — after
    a first pass at Trading-Floor scale produced overlapping, edge-
    clipped panels once real content was on screen. Six live readouts
    (`addLiveText`-driven, same pattern as Trading Floor's ticker/
    central command) share the room: world market display, department
    performance overview, department status wall (row 1), a decorative
    strategy table (row 2), and the executive briefing screen plus a
    stacked timeline/objectives column (row 3). No new Command Center
    tab duplicates these — the brief specifically asks that "the player
    can enter the room at any time" to read them, so the room itself is
    the one place they live, the same design choice the Market
    Observatory made for its own in-world-only detail view.
  - The door reuses CEO Office's `Inn_Black` building sprite a second
    time (no dedicated boardroom sprite exists in the Cute Fantasy
    pack), with a gold pulsing ring at the roofline — the same
    "no purpose-built sprite exists, so a colored ring signals distinct
    tech inside" pattern the Market Observatory's cyan ring already
    established. Placed in the gap between Simulation Lab and Hall of
    Fame on the Lobby's front row (narrower than its neighbors,
    `targetWidth: 110`) — the more obvious-looking gap between Hall of
    Fame and Trading Floor turned out to be the town square itself
    (`PLAZA_COLS` spans x 736-1024), not free building space.
- **AI Academy & Knowledge Network (Feature 25)**. `app/academy.py`
  gives every agent (the CIO included) one real Knowledge Branch
  (`KNOWLEDGE_BRANCH`, occupation-linked) and a real Knowledge Points
  total, mirroring `signal_calibration.py`'s single-number progression
  pattern but per-agent and cumulative (not streak-gated — every point
  already came from real completed work, so cumulative is honest on its
  own). Three real sources feed it: a finished `ResearchItem`
  (+1, hooked into `tick_research`'s existing `completed` return value),
  a finished `AcademyProject` (+2), and real meeting attendance (+0.5
  per participant, hooked into `_maybe_call_meeting`'s existing
  `meeting_minutes` append). `app/academy_research.py` runs the
  Academy's own non-market research queue — mechanically
  `research.py`'s own progress-climbs-then-completes-and-rotates shape,
  but keyed to a fixed six-topic catalog (`_TOPIC_CATALOG`) instead of a
  ticker symbol, since these projects have no natural watchlist symbol.
  Both the assigned-agent and topic rotations are derived from
  `len(academy_completed_projects)` rather than a separate persisted
  counter. Every completed project is permanently stored (capped at
  `MAX_ACADEMY_LIBRARY`) as the Company Knowledge Library. A company-
  wide `AcademyState.level` (1-5, `compute_academy_state`) blends real
  total points with real completed-project count against fixed
  thresholds — deliberately not five new physical rooms (no new art was
  produced for this pass); the level and its named tier
  ("Training Room" through "Executive Institute") are the whole
  deliverable.
  - Surfaced on a new **KNOWLEDGE** tab (`AcademyPanel.tsx`) —
    deliberately not named "ACADEMY", since that tab name was already
    taken by the pre-existing v0.6.2 Trading Academy (`EducationPanel`,
    a lesson/quiz curriculum, a completely different system). The
    collision was only caught by `tsc` failing on the `FullCommandCenter`
    tab union after both were wired in.
  - **Mentorship** (`maybe_run_mentorship`) is this pass's most
    deliberate scope decision: this codebase has zero seniority/
    relationship data anywhere (confirmed by grepping the whole backend
    and frontend for "senior"/"junior"/"mentor"/"relationship"/"tenure"
    before writing a line of this feature). Rather than inventing a
    fabricated status label to satisfy the brief's "senior employees
    mentor junior employees," "seniority" here is the one real number
    that legitimately reflects it — an agent's own earned Knowledge
    Points. When the real gap between the highest- and lowest-points
    agent crosses `MENTORSHIP_GAP_THRESHOLD`, a real session transfers a
    small real bonus to the lower agent (logged with both agents' own
    real point totals), checked on a 3-day cadence
    (`MENTORSHIP_CHECK_INTERVAL_DAYS`) rather than every tick, since a
    real points gap moves slowly and checking every tick would either
    never fire or fire every tick once crossed. A full mentor/mentee
    relationship graph and visible in-world mentoring animations are
    explicit scope cuts, not built.

`GameSaveState` gained `executiveReviews`, `academyProjects`,
`academyCompletedProjects`, `agentKnowledge`, and `academyState` (all
required except the first three lists, following `companyHealth`'s own
convention — backfilled from `default_state()` by the existing generic
deep-merge migration, no special-case migration code needed; verified
against a real pre-Feature-24/25 save on a fresh backend start).
`MemoryCategory` gained `academy`, `mentorship`, and `executive`.

### Company Knowledge Graph (Feature 25.5)

`app/knowledge_graph.py` connects every already-real, already-persisted
record Feature 24/25 produces — completed `ResearchItem`s, completed
`AcademyProject`s, each agent's own real Knowledge Branch,
`ExecutiveReview`s, `CoachReport`s, and `HallOfFameEntry`s — into one
node-edge graph, following the exact "computed fresh on every request,
never persisted" convention `app/whatif.py` established for
`GET /api/executive/whatif`: the underlying six sources are already
persisted and capped elsewhere, so re-deriving the graph's structure from
them on demand is a view, not a second, possibly-stale store of the same
data. `GET /api/knowledge-graph` (`app/routers/knowledge_graph.py`) is
the one new endpoint; `GameSaveState` gained nothing for this feature
except `ExecutiveReview.knowledgeConnections` (below).

Every `KnowledgeEdge` traces to a real, checkable shared attribute — a
research item's own `assigned_agent` (`researched`), two research items
sharing a real `category` or two Academy projects sharing a real `topic`,
chained by their own real `updated_at` into a `builds_on` relationship,
an agent's own real Knowledge Branch (`has_branch`), an agent's real
appearance in an `ExecutiveReview`'s `department_activity`
(`featured_in`), a `CoachReport`'s real top-ranked agent
(`ranked_top_agent`), or a `HallOfFameEntry`'s real `agent_id`
(`achieved`). None of this is invented — `_builds_on_chain`'s grouping
key is always a real shared field, never a heuristic guess at semantic
similarity.

`app/executive_review.py` gained `_knowledge_connections()`, wired into
`generate_executive_review()`: for every real research category / Academy
topic with two or more completed items, it names the two most recent real
titles (ordered by their own real `updated_at`) as a real "this builds on
that" sentence, appended to `ExecutiveReview.knowledgeConnections` and
referenced from the review's own `summary` when non-empty. It
deliberately never claims a specific elapsed time (the brief's own
example, "four months ago") — `ResearchItem`/`AcademyProject` only carry
real wall-clock ISO timestamps, not a sim-time span guaranteed to read as
meaningful within one play session, so the callback only asserts the
real title-level relationship, not a fabricated duration.

On the frontend, `KnowledgeGraphView.tsx` (launched from a new card on
the KNOWLEDGE tab) is a hand-rolled `<canvas>` force-directed graph — no
charting/graph-library dependency, matching `CandlestickChart.tsx`'s
existing hand-rolled-canvas convention. `computeLayout()` uses velocity +
damping (not a temperature-capped direct move) specifically because an
earlier temperature-capped pass collapsed under this graph's real
hub-and-spoke shape (many research nodes sharing one `agent`/`branch`
hub) — velocity + damping settles into an even spread instead. Node
*positions* are the one purely-visual invention in this feature: a
client-side layout computed to make the real graph legible, never a
second source of truth about the data itself, and recomputed (not
persisted) on every fetch. Agent nodes reuse each agent's own real sprite
tint (`AGENT_PROFILES[id].tint`) as their color — real department colors,
not invented ones. `useKnowledgeGraph.ts` mirrors `useCandles.ts`'s
fetch-with-light-refresh pattern (30s), only polling while the view is
open.

**Explicit scope cuts**, matching this session's honesty convention: the
brief's "Academy Integration" request to auto-generate interactive
lessons/seminars/training sessions/quizzes/museum exhibits/company
presentations/new dialogue/knowledge challenges from completed research
is not built — this codebase has no content-generation capability of any
kind. The pre-existing v0.6.2 Education curriculum (`education.py`'s ten
fixed lessons, all technical trading mechanics — candlesticks, stop-loss,
position sizing) was checked directly against the six Academy topics
(market history, psychology, economics — a different subject area
entirely) and confirmed to have no real thematic overlap, so no
Academy-project-to-Education-lesson edge or generated lesson content is
fabricated either. "NPCs begin discussing it" is scoped to one honest
addition in `DialogueManager.ts`: roughly one conversation in three, an
agent with at least one real completed Academy project of their own
recalls its real title — never a fabricated memory, never another
agent's project, and not a full conversational-memory system tracking
who told whom what.

### The Discipline Chamber & The Library of Mistakes (Features 26-27)

`app/discipline.py` files a real `DisciplineReview` for every trade that
closes (wired into `nexus.tick()` right after `_journal_closed_trades`,
the same point `grade_ceo_decisions` already reads from), scoring the
decision PROCESS — never the outcome. This is enforced structurally, not
just by convention: `compute_discipline_score(decision, debate,
hold_duration_minutes)`'s own signature can only ever read a real hold
duration (a behavior signal known once a trade closes, but never the
result itself), the original `TradeDecision`, and its linked `Debate` —
it never receives the trade or its pnl at all, so an identical process
provably scores identically regardless of win or loss (see
`test_discipline.py`'s `test_never_reads_outcome_...`).

Two structural traps were found and avoided while choosing the seven real
factors. `TradeDecision.votes` always contains all six real analyst
votes (`resolve_proposal` always maps every `proposal.analyst_votes`
entry) — so "were multiple viewpoints gathered" is a constant, not a real
discriminator; the codebase's real varying signal is *how many distinct
choices* those six votes actually held (`viewpoint_diversity`, 1-3
distinct choices mapped to 35/65/100). Separately, `gatekeeper_verdict`
is only ever populated (and only ever `approved`) for a decision that
actually reached this module, because a rejected verdict means `order_id`
stays `None` and no `PaperTrade` ever exists to close — so "did it pass
the Gatekeeper" is also a structural constant for the reviewed
population; `position_sizing_discipline` reuses the Decision Confidence
Engine's own real, still-varying "Portfolio Exposure" factor instead
(pulled by name from `decision.confidence_engine.factors`, not
recomputed). `_summary()` explicitly calls out a good-process/bad-outcome
or weak-process/lucky-win mismatch — the whole pedagogical point of the
feature — and `_post_decision_review()`'s `assumptionsIncorrect` only
fires on a real loss, naming the specific real dissenting analyst (Echo
or Scout — never Sentinel, whose real vote the Trade Gatekeeper's
`risk_manager_check` hard-requires to match the CEO's choice before a
trade can even open, so Sentinel dissent on an executed trade cannot
occur) whose overridden vote turned out right.

`app/mistakes.py` files a permanent `CaseStudy` only when a closed,
*losing* trade's own `DisciplineReview` shows a specific real process
gap — never merely "the trade lost" (a well-disciplined process losing to
real market variance is what the Discipline Chamber exists to protect,
not punish). Six categories, each a real, checkable signal:
`overconfidence` (Confidence Engine score ≥80 at decision time),
`incomplete_research` (the Research Confidence factor <50),
`unchallenged_assumptions` (zero real "challenge"-stance Debate turns),
`acted_too_quickly` (closed inside `QUICK_CLOSE_MINUTES`, the exact
threshold `app/coach.py`'s own `quick_losses` pattern already uses),
`ignored_dissent` (the Debate's own real `final_recommendation` disagreed
with the trade's real executed `side`), and `confirmation_bias` (a real
`overridden_dissent()` hit — the same shared helper `discipline.py`
exports and both modules read, so the two never define "real dissent"
differently). A single trade can trigger more than one category; each
becomes its own `CaseStudy`, matching the brief's own framing of these as
distinct, separately-filed examples rather than one bundled report.
Every field (Timeline, Background, Decision Process, Department
Opinions, Missed Information, Lessons Learned, Recommended Improvements,
Related Company Principles) is built from real structured data — the
linked `TradeDecision`'s own real vote reasoning, real `Debate` turns,
real `RiskLimits`/Gatekeeper thresholds, real timestamps — filled into a
fixed template, never a fabricated narrative, the same convention
`app/executive_review.py` and `app/academy_research.py` already
established.

Both `DisciplineReview` and `CaseStudy` carry a real `simDay`
(`TimeState.day` at generation time, threaded through from
`nexus.tick()`'s own `new_time`) alongside the usual real ISO
`createdAt` — added specifically so `DialogueManager.ts` could reference
"on Day X" the way the brief's own example ("the Confirmation Bias case
study from Day 47") asks for, rather than only a real wall-clock
timestamp with no honest in-game-calendar framing. `DialogueManager`'s
`recallLine()` now tries two independent real sources (an academy-project
recall and a new case-study recall, the latter cross-referencing
`DisciplineReview.attendees` by `decisionId` to confirm the speaking
agent was a real party to that specific decision) and picks at random
from whichever actually returned real content, rather than a single
coin-flip that could silently waste the one-in-three chance on an empty
source.

A new **DISCIPLINE** Command Center tab (`DisciplinePanel.tsx`) surfaces
both systems in one place: an aggregate average score, the two counts
that make "process, not outcome" concrete client-side (real
`score >= 70 && outcome === "loss"` and real `score < 55 && outcome ===
"win"` filters over `disciplineReviews`), an accordion list of Discipline
Reviews (full factor breakdown + post-decision review on expand), and a
category-filterable Library of Mistakes browser (full case study detail
on expand) — the same expand-in-place accordion pattern already used
elsewhere in the Command Center, not a new interaction model.

**Explicit scope cuts**, matching this session's honesty convention: two
of the brief's ten named discipline qualities have no real discriminating
signal in this codebase. "Was proper documentation created" is never
scored — every decision's summaries/reasoning are unconditionally
auto-populated by `resolve_proposal`, so it would be fake precision on an
invariant, not a real measurement. "Did departments communicate
effectively" beyond real cross-examination has no distinct second signal
either, so it's folded into the `cross_examination` factor rather than
invented as a redundant duplicate. Discipline Reviews are also only ever
generated for closed trades — research projects, executive decisions, and
"major company events" have no comparable rich per-item process trail in
this codebase (no per-item "were multiple viewpoints considered" signal
exists for a single research item or a company milestone), so a
discipline score for those would mean inventing numbers with no real
backing; the existing `ExecutiveReview` and `CompanyMemory` systems
remain the honest record for those instead.

### The Reasoning Lab (Feature 29)

`app/reasoning_lab.py` files a real `ReasoningChallenge` periodically
from the company's most recent real `Debate` plus its linked
`TradeDecision` (wired into `nexus.tick()` on a fixed evening cadence,
`REASONING_CHALLENGE_INTERVAL_DAYS = 2`, alongside the mentorship check).
Like `discipline.py`, this is a structural guarantee, not a convention:
no function in this module ever receives a trade's pnl or a decision's
realized outcome — `generate_challenge()`'s signature only takes the
`TradeDecision`, its `Debate`, an `unlocked_level`, and timestamps.

Seven honest categories out of the brief's nine, each a real, checkable
signal on the linked Debate/TradeDecision, checked in priority order by
`_detect_category()` (first real match wins): `comparing_competing_explanations`
(two or more distinct analysts each filed a real "support" turn),
`recognizing_contradictory_data` (the six votes split three ways),
`separating_facts_from_assumptions` (at least one real "challenge" turn
occurred), `identifying_weak_evidence` (a real opening turn's text
carries no real backing evidence — reusing the same indirect `"(" in
turn.text` proxy `discipline.py`'s own cross-examination check relies on,
since `AnalystVote.evidence` itself isn't persisted onto `TradeDecision`),
`finding_missing_information` (the Research Confidence factor is below
`app/mistakes.py`'s own `INCOMPLETE_RESEARCH_THRESHOLD`, imported rather
than redefined), and `evaluating_multiple_hypotheses` (the votes split
exactly two ways). `improving_communication` is the unconditional
fallback once every other check fails — including when no real `Debate`
exists at all, which is itself an honest communication gap, not a
missing-data placeholder. `detecting_logical_fallacies` and
`building_better_questions` have no real, checkable signal anywhere in
this codebase (neither a fallacy detector nor a question-quality scorer
exists) and are deliberately not built.

Reasoning Level gates which categories can actually be selected:
`_LEVEL_FOR_CATEGORY` requires level 1 for the three foundational
categories and levels 2-3 for the four covering less-common real debate
shapes; `_detect_category()` skips any real-but-locked match and falls
through to the next candidate, so an advanced category is never faked
early — it's genuinely absent from a challenge filed before the company
has practiced the basics. `compute_reasoning_lab_state()` mirrors
`compute_academy_state()`'s exact level/label-threshold convention
(`_REASONING_LEVEL_THRESHOLDS`, a real monotonic completed-challenge
count crossing fixed thresholds), the same "a real number and label, not
new art per level" boundary `AcademyState` already drew.

`ReasoningContribution` reframes the underlying `Debate`'s own real
opening/challenge/support turns as the brief's "departments collaborate"
record (Research asks Risk, News challenges assumptions, and so on) —
never invented dialogue between fixed department roles that don't exist
in this codebase; each turn's real `agent_id`/`role`/`stance`/`text` is
copied directly. `ReasoningSolution` answers the brief's six "Explain
Your Thinking" questions from the linked decision's own real Decision
Confidence Engine factors (strong factors → `whatWeKnow`, weak factors →
`whatWeDoNotKnow`), real opposing-vote reasoning (→ `assumptions`, with
an honest fallback sentence when no analyst dissented), and the real
`final_reasoning`/`confidence_engine.score` — never invented commentary.

The evening-cadence check in `nexus.tick()` looks up the linked
`TradeDecision` for `debates[-1]` (`decision.id ==
f"decision-{latest_debate.proposal_id}"`, the same lookup convention the
Discipline Chamber's own wiring uses in reverse) and skips generating a
new challenge entirely when either no real Debate exists yet, or the
most recent Debate was already used for the previous challenge filed
(`reasoning_challenges[-1].decision_id == linked_decision.id`) — this
module never re-practices the exact same already-reasoned-through case
just to hit the cadence.

A new **REASONING** Command Center tab (`ReasoningLabPanel.tsx`) shows
the company's current Reasoning Level/progress and a category-filterable,
expandable Reasoning History (real collaborative contributions +
full six-field solution detail on expand) — the same expand-in-place
accordion pattern the Discipline Chamber and Library of Mistakes already
use. `DialogueManager.recallLine()` gained a third real source
(`reasoningRecall()`, alongside the academy-project and case-study
recalls) that fires only for an agent who actually contributed a real
`Debate` turn to a filed challenge, referencing its real title, symbol,
and `simDay`.

**Explicit scope cuts**, matching this session's honesty convention: new
seminar content, an interactive-seminar UI, and richer per-level
collaboration animations have no real data source in this codebase and
are not built — the same "a real number/label, not new content per
level" boundary `AcademyState` already established. Challenges are only
ever generated from the company's most recent real Debate on a fixed
cadence, never backfilled for every historical Debate at once — the
Reasoning Lab, like the Discipline Chamber, is a going-forward practice
system, not a retroactive audit of every past decision.

## Save format compatibility

The save schema's `version` field has changed with every code-bearing
version so far — `"0.1"` → `"0.2"` → `"0.3"` → `"0.5"` → `"0.6"` (v0.4
made no code changes, so the schema stayed `"0.3"` through it) — and the
shape changed non-trivially each time (`0.1→0.2`: `scout: ScoutState` →
`agents: Record<AgentId, AgentState>`, plus new `tasks`/`whiteboards`/
`meeting`/`news` fields; `0.2→0.3`: `AgentId` gained `"scribe"`, `Task`
gained `category`, `MeetingState` gained `discussion`, and `research`/
`watchlist`/`memory`/`meetingMinutes` were added; `0.3→0.5`: `AgentId`
gained `"coach"`, and `paperPortfolio`/`strategies`/`backtestSessions`/
`simulationResults`/`hallOfFame`/`coachReports`/`companyScore`/
`performanceSnapshots` were added; `0.5→0.6`: `AgentId` gained
`"sentinel"`/`"pulse"`/`"guardian"`, and `riskLimits`/`riskWarnings`/
`scannerAlerts`/`decisions` were added, plus new fields on `PaperOrder`
and `PaperTrade` — see "Version 0.6 scope" above). An older save fails
Pydantic validation on load; `persistence.py` catches that failure, logs
a warning, and starts a fresh default state for the current version
rather than crashing — there is no migration path between versions, by
design, since none of v0.1 through v0.6 was a public release.
