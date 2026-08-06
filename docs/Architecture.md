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

### The Reflection Chamber (Feature 30)

`app/wisdom.py` files a real `ReflectionSession` on the same weekly/
monthly evening cadence Coach's `CoachReport`/the CIO's
`ExecutiveReview` already use (`WEEKLY_INTERVAL_DAYS`/
`MONTHLY_INTERVAL_DAYS`, wired into `nexus.tick()` right after the
Reasoning Lab check), answering the brief's nine reflection questions
purely from data this codebase already computes elsewhere. `_questions()`
maps each one onto a real signal: "what surprised us" reads the most
recent `DisciplineReview` whose `score`/`outcome` pairing is a genuine
mismatch (reusing the exact same real predicate `DisciplinePanel.tsx`'s
own stats card already computes); "what assumptions turned out to be
wrong" reads the most recent `confirmation_bias` `CaseStudy`; "what
patterns are repeating" / "what should we stop doing" both read the same
`Counter`-most-common `CaseStudyCategory` (via `mistakes.py`'s own
`CATEGORY_TITLES`, renamed public from `_TITLES` specifically for this
reuse); "what are we doing well" / "what should we continue doing" both
read the `DisciplineFactor` name with the highest real average score
across recent reviews, and "what knowledge are we missing" reads the
same average's lowest scorer — the same "one real list, both ends"
convention `discipline.py`'s own `_post_decision_review()` already
established, not fabricated as four independent measurements. "Where are
we becoming overconfident" counts real `overconfidence` case studies;
"what new questions to investigate" prefers the most recent real
`ReasoningChallenge`'s title, falling back to a real research item still
below `mistakes.py`'s own `INCOMPLETE_RESEARCH_THRESHOLD`.

Cross-department sharing (`_insights()`) is the honest version of the
brief's "Research explains a discovery, Risk explains concerns" —
real recent output from real existing agents (the latest completed
`ResearchItem`'s own title/summary, the latest real `NewsItem` headline,
the latest real `RiskWarning` or `GatekeeperRejection` reason, the
latest real `ExecutiveReview` summary), never invented dialogue between
department roles this codebase doesn't have ("Education" has no
distinct agent or per-discovery lesson-generation capability — see
`app/education.py`'s own static curriculum).

Company Wisdom (`compute_wisdom_score()`) is a plain, unweighted mean of
eight real factors — the same "plain mean, no hidden weighting"
convention `company_score.py` already established — each traced to a
real, already-computed signal: `learn_from_experience` compares the
average `DisciplineReview.score` across the earlier vs. later half of
the recent window; `share_knowledge` counts real `"mentorship"`
`MemoryRecord`s; `follow_principles` is the real share of trades that
reached `PaperPortfolio.trade_history` without a `GatekeeperRejection`;
`improve_communication`/`support_collaboration` are the real average
`cross_examination`/`viewpoint_diversity` `DisciplineFactor` scores
(two different, already-real factors — not a redundant re-measurement);
`document_lessons` is the real combined count of Discipline Reviews/
Case Studies/Reasoning Challenges on record; `avoid_repeating_mistakes`
is 100 minus the real dominant `CaseStudyCategory`'s share of the
window; `complete_research` is the real completed/total `ResearchItem`
ratio. `compute_wisdom_score()`'s own signature never receives a trade's
pnl or any `PaperTrade`, only `PaperPortfolio.trade_history`'s length
for the `follow_principles` ratio — the same structural "never reads the
outcome" guarantee `compute_discipline_score()` established, verified by
a dedicated test asserting identical scores for identical process
regardless of the linked trade's real win/loss. `WisdomState` is
recomputed only inside the same `if` block that generates a
`ReflectionSession` (weekly/monthly), never every tick — a deliberate
choice so the score reads as genuinely slow-moving, not a performance
shortcut.

A new **REFLECTION** Command Center tab (`ReflectionPanel.tsx`) shows
the current Wisdom Score/tier/factor breakdown and an expandable
Reflection Journal (all nine Q&A, department insights, key discoveries,
lessons learned, important questions, recommended future projects) per
session — the same expand-in-place accordion pattern already used
elsewhere. `DialogueManager.recallChance()` scales the existing
institutional-memory recall chance (see Feature 25.5/27/29 above) up
with the company's own real `wisdomState.tier` — the honest, checkable
version of "historical knowledge is referenced more often" as the
company grows wiser, never a fabricated dialogue-quality upgrade.

**Explicit scope cuts**: no new physical Reflection Chamber room was
built — a circular holographic table, an animated constellation
Knowledge Graph floating above it, and "NPCs gather naturally around the
table" all have no real gameplay-data hook to back them in this 2D,
tile-based codebase, the same boundary Academy/Discipline/Mistakes/
Reasoning Lab already drew (only Feature 24's Executive Boardroom got a
physical scene, tied to a genuinely new NPC-hosted location — Reflection
has neither).

### Knowledge Levels (Feature 31)

Feature 31's brief asks for a Learning Center with a real Novice-through-
Mentor progression, structured lesson pipeline, and player-provided
learning materials. Most of this ground is already covered by the
shipped AI Academy (Feature 25) — building a second, parallel
points/project/mentorship system under a new name would mean either
duplicating `academy.py`'s real mechanics or fabricating a shadow
system with no real backing. Instead, `academy.py` itself was extended:
`TIER_THRESHOLDS` widened from three real point thresholds (four tiers)
to six (seven tiers), and each tier now also carries a real
`KnowledgeLevel` name (`_KNOWLEDGE_LEVELS`) — `novice` through `mentor`,
the same real points, a richer label. `AgentKnowledgeState.tier` (int)
is kept unchanged in shape so existing threshold/test code didn't need
restructuring; `level` is the same value's honest name, derived via
`_level_for_tier()`.

`is_mentor_level()` is the real, checkable gate the brief's "Teaching
System" needs ("agents who master a subject may become instructors"):
`maybe_run_mentorship()`'s existing mechanism (the real points-gap
trigger between the most- and least-experienced agent — see Feature 25
above) is unchanged, but `scribe.py`'s `record_mentorship_session()` now
phrases the resulting memory entry as real teaching ("teaches"/"hosted a
real teaching session for") rather than generic mentoring
("mentors"/"spent time coaching") the moment the mentor has actually
reached the top `mentor` level — no separate teaching subsystem, since
the same points-gap mechanism already is the real trigger for "a more
experienced agent helps a less experienced one."

`DialogueManager.knowledgeDepthLine()` is the honest, template-based
version of the brief's "explanation matches knowledge level" — no
free-form NLG exists in this codebase to actually vary explanation depth
per topic on demand, so once an agent's own real `tier` reaches 3
(`advanced`) or higher, their greeting includes one extra real line at
that depth, keyed off their own real `level`/`branch`. A
novice/beginner/intermediate agent has nothing extra to say here yet,
honestly.

**Explicit scope cuts**, matching this session's honesty convention: the
Learning Center building (Lecture Hall, Digital Library, Interactive
Classrooms, Presentation Stage, Knowledge Archive, Simulation Classroom,
Study Lounge, AI Training Pods — ten named physical spaces) is not
built — the same "Command-Center-tab, not new art" boundary every recent
feature has drawn. Player Knowledge Import (PDFs, guides, books, videos
the player provides) is not built at all: this codebase has no
content-ingestion or document-parsing capability anywhere, and
fabricating lesson content "from" an uploaded file the system never
actually reads would be dishonest by this session's own standard. The
brief's explicit 8-stage learning pipeline (Study → Summarize → Discuss
→ Ask Questions → Challenge Assumptions → Practice → Teach → Archive)
and per-lesson Knowledge Summaries (key concepts, definitions, open
questions, weaknesses, related topics, recommended follow-up) are not
separately modeled either — `academy_research.py`'s existing
`AcademyProject` pipeline and `education.py`'s existing quiz-graded
lessons already cover real study/practice/understanding-check activity
at an honest, coarser granularity; inventing eight distinct per-stage
signals with no real data behind them would be fake precision. Live
Classrooms (a physical room players walk into) and an open-ended "Ask
Any Agent, explain this topic" free-text system are both cut for the
same reason as Player Knowledge Import — no real dynamic
content-generation capability exists in this codebase to back either
one honestly.

### Sage, the Socratic Mentor (Feature 32)

Sage is added exactly the way Meridian (Feature 24) was — a real
eleventh `AgentId` that never votes, trades, or generates a research
signal (see `agents.py`'s own comment on `AgentId`). Its home location
reuses `brain-room` rather than introducing a new scene, the same
"Command-Center-tab, not new art" boundary every recent feature has
drawn (Academy/Discipline/Reasoning Lab/Reflection Chamber; only
Feature 24's Executive Boardroom got a physical scene, tied to a
genuinely new NPC-hosted location). Its sprite is generated the same
real, deterministic way as all ten existing agents': the exact 7-color
remap table (2 hair colors, 5 shirt/pants-ramp colors) was recovered by
pixel-diffing `Player.png` against `Player_Scout.png`/`Player_Meridian.png`
with PIL, then applied over a fresh copy of the base sheet with a new
deep indigo/violet target palette — not a hand-drawn or copied asset.

`app/mentor.py` builds the one concrete artifact the brief actually asks
for that this codebase can back honestly: a `QuestionOfTheDay`. Every
in-game morning at 8:00 (`MORNING_QOTD_HOUR`, the same exact-minute
trigger shape as `EVENING_REVIEW_HOUR`, wired into `nexus.tick()` right
after the Reflection Chamber check), `generate_question_of_the_day()`
picks `QUESTION_LIBRARY[sim_day % len(QUESTION_LIBRARY)]` — a small,
hand-authored bank of 20 questions across 10 categories. This is real,
curated content, the same convention `DialogueManager`'s own flavor
lines already use — there is no free-form question-generation capability
anywhere in this codebase, so nothing here claims Sage is "writing" a
new question each morning. `_related_reference()` attaches at most one
honest pointer into content this codebase already has for real (the
latest `ReasoningChallenge` title for critical-thinking/logic questions,
the latest `CaseStudy` title for psychology/decision-making, the latest
`RiskWarning` message for risk-awareness, a completed `ResearchItem`
title for research, a `ReflectionSession`'s own lesson/insight/attendee
count for reflection/communication/teamwork, an `ExecutiveReview`'s
flagged event for leadership) — never a fabricated per-department
"answer," and `None` when nothing real exists yet to point to. Every
entry is permanently archived (`record_question`, capped at
`MAX_QUESTION_ARCHIVE` = 120, roughly four in-game months); the player's
free-text answer (`POST /api/mentor/qotd/respond` → `GameState.
submit_qotd_response()` → `mentor.submit_response()`) is stored verbatim
and never graded — the same constraint that already kept Reflection
Journal entries ungraded in Feature 30.

`ThinkingProfile` (`compute_thinking_profiles()`) is a purely-computed,
per-agent readout built entirely from signals this codebase already
tracks: `curiosity` reads the agent's real Academy knowledge points
(`AgentKnowledgeState.points`, normalized against the same 30-point scale
`academy.py`'s own tier thresholds use); `evidence_quality`/
`open_mindedness`/`humility`/`reasoning` average the real
`research_depth`/`viewpoint_diversity`/`uncertainty_acknowledged`/
(`assumptions_challenged`+`cross_examination`)/2 `DisciplineFactor`
scores across every `DisciplineReview` the agent actually attended
(neutral 50 default when an agent — Scribe, Coach, Meridian, Sage itself
— has never attended one, since only the six analyst roles ever appear
in `DisciplineReview.attendees`); `collaboration` counts real Reasoning
Lab contributions plus real Reflection Chamber insights. "Patience" is
deliberately not a trait here — `DisciplineReview` already scores it
directly under that exact name, and re-surfacing the identical real
number under a new label here would be the "redundant re-measurement"
trap this session's other features have consistently avoided (see
Feature 30's own note on `improve_communication`/`support_collaboration`
being two *different* real factors, not one factor counted twice); the
brief's "Communication" and "Adaptability" have no real, per-agent
discriminating signal anywhere in this codebase and are cut for the same
reason Feature 30 cut its own ungrounded factors. `ThinkingProfile` is
recomputed fresh every tick, the same "cheap, only re-scans already-
capped lists" reasoning `academy_state`/`reasoning_lab_state` already
established — not throttled like `WisdomState`, since none of its inputs
are themselves throttled.

`MentorState` mirrors `ReasoningLabState`'s level/label-only shape: a
real, monotonic `questionArchive` length gates a `tier` (0-3) and label
("New Tradition" → "Taking Root" → "Established Ritual" → "Defining
Tradition") at the real calendar rhythm the brief itself describes — a
week, a month, and a full season of daily questions.

A new **MENTOR** Command Center tab (`MentorPanel.tsx`) shows today's
question with its category/related-reference and an answer box (or the
player's already-submitted answer), the full Question Archive as an
expand-in-place accordion (the same pattern `ReflectionPanel.tsx`
already uses), a static Question Library summary, and every agent's
`ThinkingProfile` rendered as trait meters, grouped per agent the same
way `AcademyPanel.tsx`'s Knowledge Trees are grouped.

**Explicit scope cuts**, matching this session's honesty convention: a
separate weekly "Mentor Session" was not built — `wisdom.py`'s
already-shipped `ReflectionSession` already IS a real weekly/monthly
company-wide gathering built around real, Socratic-style questions (see
Feature 30 above); building a second, parallel system would just
re-package the same real signals under a new name, the exact
"redundant re-measurement" trap this session has repeatedly checked for
and avoided. "Thinking Exercises" are likewise not duplicated —
`reasoning_lab.py`'s `ReasoningChallenge` (Feature 29) already covers 7
of the brief's 10 named exercise types with a real, checkable signal
each. Personal Coaching (per-employee improvement areas distinct from
`ThinkingProfile`'s own traits) has no real signal to back a separate
list and is cut. A graded "Daily Thinking Bonus" is cut for the same
reason Reflection Journal entries stayed ungraded — no honest mechanism
exists in this codebase to grade open-ended free text. "Connected
Constitution Articles" is cut because no Company Constitution system
exists anywhere in this codebase (checked directly via a repo-wide
search before writing `mentor.py`). The Question Library being usable
live by departments during meetings is cut — `scribe.py`'s discussion
generator has no hook to pull from an external question bank without
fabricating dialogue; the Library is real, authored content the player
can browse, not something NPCs consume. A dedicated physical "Mentor
Chamber" room (floating holographic books, a meditation garden, a
question tree) was not built, the same boundary every recent feature has
drawn.

Incidental fix made while wiring Sage into the world: `BrainRoomHud.tsx`'s
`AGENT_ORDER` constant (backing "N of M agents actively working" and the
Agent Status list) had never actually included Meridian since Feature 24
added her — a pre-existing gap, not something Feature 32 introduced, but
trivial and safe to fix once noticed. Now includes both `cio` and `sage`.

### CEO Treasury, Company Priorities & Time Controls, Living World Schedules (Features 33-35)

**CEO Treasury (Feature 33).** `app/treasury.py`'s `TreasuryState` is a
second account, structurally isolated from `PaperPortfolio.cash_balance`
("Operating Capital"). Every balance-changing function
(`deposit`/`withdraw`/`apply_monthly_savings_rules`) takes the amount as
an explicit parameter — there is no code path anywhere that derives it
from anything else. The three `GameState` methods that call them
(`deposit_treasury`/`withdraw_treasury`/the monthly-cadence call inside
`nexus.tick()`) are the only callers in the whole codebase; grepping for
`treasury` outside `treasury.py`, `state.py`, `nexus.py`, and the router
turns up nothing. That is the same structural guarantee `discipline.py`
already established for "never receives pnl" — checked, not just
documented by convention.

Smart Savings Rules are the one deliberate exception, gated on the CEO's
own prior configuration. Two rule types are offered, not the brief's
three: "save 5% of monthly profit" and "save 10% after profitable
months" are the same mechanic wearing two labels — saving a percent of
monthly profit only ever fires when that profit is positive — so
`percent_of_monthly_profit` is the one real type; a second,
mechanically-identical type would just be the "redundant re-measurement"
trap this session has repeatedly checked for elsewhere (Feature 30's
`improve_communication`/`support_collaboration` note, Feature 32's cut
"Patience" trait). `excess_above_reserve` (move operating cash above a
chosen dollar reserve) is genuinely distinct behavior and kept separate.
Both rules, when active, run once a month inside `nexus.tick()`'s
existing monthly cadence block, immediately followed by a real
`TreasuryMonthlyReport` filtered from the same `treasury.transactions`
log (`record_monthly_report()`) — the Savings Growth Timeline and the
Monthly Savings Report both read this one log; neither maintains its own
derived series. The monthly profit figure itself comes from a new
`analytics.period_profit_dollars()`, which reuses
`_period_start_sim_minutes()` — the exact same window-filtering logic
`compute_performance_snapshot()`'s own `returnPct` already uses — rather
than a second, possibly-drifting profit calculation.

A new **TREASURY** Command Center tab (`TreasuryPanel.tsx`) is the room:
Operating Capital / CEO Treasury / Reserve Percentage cards, Lifetime
Deposits / Largest Balance / Transactions / Active Rules stats, a
deposit/withdraw form, Smart Savings Rule creation with a per-rule
pause/resume toggle and a Pause All button, the Savings Growth Timeline,
and the Monthly Savings Report — no new physical vault-door scene was
built, the same Command-Center-tab precedent every recent v0.7 feature
has followed. The brief's CEO Benefits (Company Expansion, Emergency
Funding, Building New Departments, Buying Headquarters Upgrades, Special
Story Events) are not built — none of those systems exist anywhere in
this codebase to honestly spend a real Treasury dollar into. Withdrawal
itself (CEO-approved funds moving back to Operating Capital, from which
the player can already open paper positions) is the real, honest piece
that ships instead.

**Company Priorities & Time Controls (Feature 34).** `settings
.companyPriority` (`CompanyPriority = Literal["balanced", "learning",
"research", "risk_reduction"]`, defined in `schemas.py` next to
`OperatingMode` to avoid a forward-reference resolution risk under this
file's `from __future__ import annotations`) is client-authoritative and
round-trips through the same generic `apply_client_save` merge
`operatingMode` already uses — no dedicated endpoint needed. `nexus.tick()`
reads it once per tick and biases exactly one real, already-existing
lever per option: `learning` multiplies every `award_points()` call's
amount by `PRIORITY_KNOWLEDGE_MULTIPLIER` (1.5x); `research` passes
`PRIORITY_RESEARCH_SPEED_MULTIPLIER` (1.5x) into `tick_research()`'s new
`speed_multiplier` parameter; `risk_reduction` sizes and vets new trade
proposals against `_effective_risk_limits()` — a `.model_copy(update=
{...})`'d, tightened-by-`PRIORITY_RISK_TIGHTEN_FACTOR` (0.8x) *derived*
copy of the player's own `RiskLimits`, used only at the specific call
site that needs it. The player's actual stored `RiskLimits` (and
everything else derived from it — Guardian's ambient risk warnings, the
Risk tab's own display) is never touched, the same "effective, non-
mutating derived config" pattern this session established rather than
silently overloading the player's real configuration. The brief's
"Expansion," "Efficiency," and "Innovation" priorities are not offered:
no real, distinct lever exists in this codebase for any of them, and
attaching one of the three real levers to a fourth label would
misattribute its actual effect.

`POST /api/time/advance` (`GameState.advance_time()`) drives End
Workday/Week/Month and a bounded 1-72 hour custom fast-forward
(`MAX_FAST_FORWARD_HOURS`). The naive approach — jump the clock's
`hour`/`minute` fields directly to the target — was rejected because it
can land off the exact minute `nexus.tick()`'s own cadence checks
require (`EVENING_REVIEW_HOUR`/`MORNING_QOTD_HOUR`, both exploiting that
`GAME_MINUTES_PER_TICK` always divides 60 evenly), silently skipping a
report, Question of the Day, or Treasury rule evaluation that should
have fired along the way. Instead, `tick()`'s own lock-assumed inner step
was extracted into `_advance_once(minutes)` (no lock of its own), and
`advance_time()` loops it in real `GAME_MINUTES_PER_TICK`-sized steps
under one lock acquisition until a stop predicate matches — structurally
identical to time actually passing faster, not a fake jump. Both
`tick()` and `advance_time()` acquire `self.lock` exactly once each at
their own top level (calling `tick()` in a loop from inside
`advance_time()`'s own lock would deadlock — this is why the split
exists). A do-while shape means calling this exactly at the target
minute (clicking "End Workday" right at 20:00) still advances to the
*next* occurrence rather than no-op-ing. Because a multi-hour
fast-forward can touch nearly everything `nexus.tick()` touches (agents,
research, trades, Treasury, reports, ...), the endpoint returns the full
`GameSaveState` — the same shape as `GET /api/load` — rather than just
the new `time`, so the client applies it in one shot via
`SaveManager.applyState()` instead of visibly lagging until the next ~2s
WS broadcast.

`CompanyPanel.tsx` gained a Company Priority section (a 4-button grid
mirroring Operating Mode's own visual style) and a Time Controls section
(three cadence presets plus a custom-hours input, capped client-side at
72 to match the server). `FullCommandCenter.tsx` gained a number-key
(1-9) tab-switch shortcut, checking `e.target.tagName` against
`INPUT`/`TEXTAREA`/`SELECT` so it never fights a focused form field
(Treasury's amount input, the fast-forward hours field, ...).

**Living World Schedules (Feature 35).** The brief's Employee Residence,
City Life locations, and hour-by-hour after-work activity list were
scoped down to their real underlying goal — agents feeling like
coworkers with real off-hours routines the player can witness, not NPCs
that vanish after work — deliverable with zero new art. Two concrete
facts ruled out new scenes: the fantasy-village asset pack has no
indoor-furniture sprites (bed, sofa, kitchen counter, bookshelf, ...) to
build Bedrooms/Kitchen/Game Room/etc. from, and the Lobby's existing
11-door layout is already a tightly pixel-tuned, heavily
collision-comment-annotated arrangement in which all 9 building sprites
are already reused at least once — adding a 12th door for a Residence (or
doors for Coffee Shop/Park/Library/... on top of that) is high-risk,
high-effort relative to the goal. Instead, every one of the 11 agents'
`AGENT_SCHEDULES` (`app/schedule.py`, mirrored exactly in
`Schedule.ts`/`DialogueManager.ts`) now runs a real off-hours block from
20:00 to 6:00 in the existing `break-room` location: a personality-
flavored wind-down task (20:00-22:00), a distinct evening activity
(22:00-24:00), then Sleeping (00:00-6:00) — 22 new task labels total,
each genuinely per-agent (Coach exercises to clear his mind then watches
game film "for fun this time"; Sentinel finally lets the guard down;
Sage sits quietly with today's question, off the clock; ...), each
paired with its own new `DialogueManager` flavor line so a player who
walks into the Break Room after hours hears something real and specific,
not a generic idle line. Normalizing every agent's schedule to the same
`0-6` Sleeping block incidentally surfaced and fixed a genuine
pre-existing gap: Nova's day had started at hour 7 (every other agent's
at hour 6), which would have left hour 6 silently mislabeled by
`block_for_hour()`'s own fallback to the agent's first schedule block.

Verification: full backend (mypy/ruff/pytest, 378/378 — 42 new tests
across `test_treasury.py`, `test_company_priority.py`, and
`test_time_advance.py`) and frontend (tsc/eslint/build) clean. Manually
verified in the running app (Playwright, 20/21 passing — 1 skipped for
the same real-trade-timing reason every run of this suite already
tolerates — including new tests for a real deposit/withdraw round trip
with a rejected over-withdrawal, Company Priority selection persisting
across a reload, a real End Workday clock jump via `POST
/api/time/advance`, and the number-key shortcut correctly ignoring a
focused form field).

### CEO Calendar & Company Schedule (Feature 36)

`app/calendar.py`'s `compute_system_events()` builds one dated event list
from real, already-computable sources rather than the brief's fixed
"8:00 Morning Briefing, 8:30 department assignments, 10:00 Research
Sessions, ..." company-wide timetable — that exact synchronized
choreography doesn't exist here: each of the 11 agents already runs its
own believable, personality-distinct schedule (Feature 35's
`AGENT_SCHEDULES`), never a single shared company-wide slot system, so
reproducing the brief's Example Day would misrepresent what actually
happens tick to tick.

What the calendar surfaces instead: the fixed evening/monthly/weekly
cadence checkpoints `nexus.tick()` already runs on (Weekly/Monthly Coach
Reports, the Monthly Executive Review, the Monthly Treasury Savings
Report, Weekly/Monthly Reflection Sessions, Sage's daily Question of the
Day) — walked forward day-by-day across a 35-day horizon
(`CALENDAR_HORIZON_DAYS`), checking each real `day % interval_days == 0`
gate exactly the way `nexus.tick()` itself does. The two *conditional*
cadences nexus.tick() already gates on — the Reasoning Lab challenge
(needs a new, unused real AI Debate) and the Academy mentorship check
(needs the real knowledge-points gap to cross `MENTORSHIP_GAP_THRESHOLD`)
— get a live `eligible` flag on their nearest upcoming occurrence only,
computed by `_reasoning_challenge_eligible()`/`_mentorship_eligible()`,
pure non-mutating reads that mirror `nexus.tick()`'s own gate logic
exactly (so the flag can never drift from the real thing that decides
whether either actually fires). Occurrences further out than the nearest
one carry no `eligible` value at all — this codebase has no way to
predict whether a *future* day's debate/points-gap condition will hold,
so it doesn't pretend to.

Active research items get an honest ESTIMATED completion date, computed
from the real current confidence gap divided by the real average
per-tick confidence-gain rate (`research.py`'s `CONFIDENCE_GAIN_RANGE`,
averaged, scaled by Feature 34's `research_speed_multiplier` when the
"research" Company Priority is active) times `settings.game_minutes_per_tick`
— labeled ESTIMATED in its own title string, the same "never claim more
certainty than the data supports" convention the WhatIf Simulation Lab's
"SIMULATED" badge already established. A "Company Anniversary" milestone
appears every real 365 days from Day 1 — an honestly-arbitrary-but-fixed,
disclosed convention on the same footing as `analytics.py`'s own 30-day
"month" (TradeTown's clock has no real calendar year either, so this
module picks one, states it plainly in its own docstring, and applies it
consistently rather than hiding the choice).

Player-created custom events (`create_player_event()`/
`delete_player_event()`, `POST /api/calendar/events/create`/`/delete`)
are the one genuinely new piece of state Feature 36 adds — validated
(non-empty title ≤140 chars, real hour/minute range, can't schedule in
the past) and capped at `MAX_PLAYER_CALENDAR_EVENTS` (60), the same
list-capping convention every other feature's history list already
follows. They are deliberately informational only: no mechanical effect
is wired to any category. Giving "Company Holiday" a real effect (pausing
research/trading) or "Extra Training Day" a real Academy-points boost
would mean either duplicating Feature 34's Company Priority lever under a
new name, or fabricating a payroll/attendance/training-boost system this
codebase has no other trace of — the same reasoning that cut Feature 33's
CEO Benefits list.

A new **CALENDAR** Command Center tab (`CalendarPanel.tsx`) presents
Today's/Tomorrow's Schedule, a Weekly Agenda, Monthly Company Events, an
Executive View (current/next event, real department working/idle counts
derived the same way `AgentsPanel.tsx`'s own idle heuristic already does,
today's real meeting count from the existing `meetingMinutes` log, and
the real current `settings.companyPriority`), the custom-event creation
form, and a **Live Schedule** section: selecting any of the 11 agents
shows their real current activity/room/mood (`AgentState`), Knowledge
Level (`AgentKnowledgeState.level`), active research, and their complete
real daily schedule block-by-block — reusing the already-shipped
client-side `Schedule.ts` mirror directly, so no new backend endpoint was
needed to expose it.

**Explicit scope cuts** (matching this session's honesty convention):
"Academy Classes" gets no fixed calendar slot or ETA — unlike research's
steady per-tick confidence gain, Academy project progress moves in
irregular real bursts (a research completion, a meeting attendance) with
nothing steady to project an honest ETA from. "Department Meetings" gets
no fixed slot either — `MEETING_CHANCE_PER_TICK` in nexus.py means
meetings are called spontaneously, never on a schedule; the panel
surfaces today's real count instead of a fabricated future slot.
"Employee Birthdays" (marked optional in the brief) is cut outright — no
agent has a birth date anywhere in this codebase. "Missed Meetings" (an
Executive View field the brief itself asks for) is cut — meetings pick
their attendees from whoever's `available` at call time; no agent is ever
"invited" in a way that could later be tracked as missed. Guest Lecturer,
Academy Exam, Innovation Day, Department Workshop, Knowledge Fair,
Reflection Conference, Celebration Party, and Research Presentation have
no real system behind them anywhere in this codebase and are not
fabricated.

Verification: full backend (mypy/ruff/pytest, 404/404 — 26 new tests in
`test_calendar.py`, covering cadence math, both conditional-eligibility
gates in both states, the ESTIMATED research-deadline formula, and
player-event validation) and frontend (tsc/eslint/build) clean. Manually
verified in the running app (Playwright, 27/27 counting the same
tolerated real-trade-timing skip every run of this suite already has —
a new CALENDAR-tab test confirms the real system-event lists, the
per-agent Live Schedule, and a full custom-event create/delete round trip
against the live backend).

### Work Mode System (Feature 37)

The brief asks to "replace the Stop for the Day button" — no such button
exists anywhere in this codebase (checked directly; the game has always
run continuously). What's real and worth building instead is the actual
toggle: `settings.work_mode` (`"work" | "rest"`, `WorkMode` in
schemas.py) joins `operating_mode`/`company_priority` as the third
client-authoritative settings field `nexus.tick()` reads every tick,
merged the same way via `apply_client_save`. "work" (the default) is
exactly today's unchanged behavior — indefinite, continuous operation,
no automatic stopping.

"rest" gates three things inside `tick()`:
- `tick_research()` and `tick_academy_projects()` are skipped entirely
  (`research, completed = (research, []) if resting else tick_research(...)`
  and the equivalent for Academy) — "employees stop starting new work."
- `_maybe_call_meeting()` takes a new `resting` parameter that only ever
  short-circuits the function's own "maybe start a *new* meeting" branch
  (the `else` half, reached only once `meeting.active` is already
  `False`) — the `if meeting.active:` branch above it, which wraps up an
  in-progress meeting once its participants' overrides actually expire,
  is completely unaffected by `resting`. This is a natural consequence of
  the function's existing structure (see its own module comment on why
  meetings/breaks share one `AgentOverride` mechanism), not new branching
  logic — a meeting already under way simply finishes exactly as it
  always would.
- Every agent whose `override` is `None` (or has just expired) routes
  through a new `_effective_block()` → `_rest_block()` instead of the
  normal `block_for_hour()`. `_rest_block()` maps the real current
  hour:minute onto the same real 10-hour off-hours span Feature 35
  already authored per agent (20:00-24:00 wind-down/evening activity,
  0:00-6:00 sleep) via `cycle_minute = minute_of_day % 600`, so a
  CEO-triggered rest period cycles through wind-down → evening activity →
  sleep → wind-down again, repeating every 10 in-game hours — genuine
  variety from only real, already-written per-agent content. This is
  deliberately a pure function of the real clock rather than new
  per-agent state: no field tracks "how long has this agent been
  resting," since the mapping itself already repeats on its own.

Trading and risk systems — `paper_trading.py`, `broker.py`,
`risk_engine.py`, `scanner.py`, `gatekeeper.py` — are never touched by
`work_mode` anywhere in `tick()`; they're structurally unaware the
setting exists. This is exactly how the brief's "open trades continue to
be managed safely according to Automation Mode and risk rules — they do
not abandon positions" is satisfied: not by special-casing trading logic
around Rest Mode, but by simply never gating it in the first place.
Cadence-driven company record-keeping (Weekly/Monthly Coach Reports, the
Monthly Executive Review, Treasury's monthly rules, Reflection Sessions,
the daily Question of the Day, the Reasoning Lab challenge, the Academy
mentorship check) is likewise left ungated — these represent the company
looking back at what already happened rather than new agent-initiated
work, so pausing them mid-cycle would create odd half-finished
retrospectives for no real benefit.

A new always-visible toggle lives in `BottomToolbar.tsx` (🟢 WORK MODE
ACTIVE / 🌙 REST MODE ACTIVE) — the same toolbar that already hosts
Save/Load/Pause/Settings, satisfying the brief's "the current mode should
always be visible" from anywhere in the game, not just inside the
Command Center. A fuller Work Mode section (with the same visual
language as Operating Mode/Company Priority) was also added to
`CompanyPanel.tsx`, spelling out exactly what each mode does.

### Company Campus Map (Feature 38)

The brief calls this "Feature 37," colliding with the Work Mode System
above (also numbered 37 by the brief); tracked internally as Feature 38.
It's a pure-frontend overlay — no backend changes — that reads the exact
same `gameStore` data every other Command Center panel already reads,
plus a new small data layer describing where each real building sits and
what it does.

**Reusing the real Lobby layout instead of a second copy.**
`LobbyScene.ts`'s `DoorDef` interface, `DOORS` array, and `WIDTH_PX`/
`HEIGHT_PX` are now exported. A new `frontend/src/ui/components/
CampusMap/buildings.ts` imports them directly and builds `CAMPUS_BUILDINGS`
(the Lobby node plus all 11 real doors) from that array — the map's
layout can never drift from the real in-game layout because it's the same
data, not a hand-authored second set of coordinates.

**11 real buildings, not the brief's fictional 17-building blueprint.**
This codebase has exactly 11 real doors (`ScoutOfficeScene`,
`BrainRoomScene`, `CeoOfficeScene`, `MeetingRoomScene`, `BreakRoomScene`,
`SimulationLabScene`, `HallOfFameScene`, `ExecutiveBoardroomScene`,
`TradingFloorScene`, `PerformanceCenterScene`, `MarketObservatoryScene`)
plus the Lobby courtyard. The brief's Think Tank/Library/standalone
Reasoning Lab/Treasury/Headquarters/Cafe/Garden/Gym/Employee Residence/
Park/Museum/Dock have no physical scene anywhere in this codebase —
several were already established as Command Center tabs rather than
physical rooms by earlier features (Academy, Reasoning Lab, Reflection
Chamber, Treasury all made that call first). Only real buildings appear.

**Status derivation uses only real signals.** `buildingStatus()` in
`CampusMap.tsx` returns `meeting` only for the Meeting Room while
`meeting.active` is true; `attention` only for the Trading Floor when a
real `RiskWarning` with `severity === "critical"` exists (the closest
honest per-building proxy available, since `RiskWarning` carries no
location field); `busy` when 3+ agents are physically present
(`AgentState.location`); `idle` at zero; `normal` otherwise. The brief's
🔵 Training and 🟠 Construction statuses are cut — no per-building signal
for either exists anywhere in this codebase.

**One real metric per building, or none.** `buildingMetric()` surfaces
exactly one already-existing real number per building where a genuine
mapping exists (Brain Room → in-progress research count, Simulation Lab →
`simulationResults.length`, Hall of Fame → `hallOfFame.length`, Trading
Floor → win+loss count, Performance Center → `performanceSnapshots.length`,
Executive Boardroom → `executiveReviews.length`, Meeting Room → today's
real meeting count, Market Observatory → `watchlist.length`, Scout Office →
`news.length`) and `null` (nothing shown) everywhere else, rather than
fabricating the brief's nine generic per-building statistics (Lifetime
Visitors, Most Active Employee, Daily Operating Cost, Power Status,
Building Health, Monthly Performance — none of which this codebase tracks
per building anywhere).

**Employee Destination/ETA reuses real override and schedule data.**
`Schedule.ts` gained `nextScheduleBlock(agentId, hour)` — every agent's
blocks already cover all 24 hours with no gaps, so "next block" is always
exactly the block whose `startHour` equals the current block's
`endHour % 24`. The Employee panel checks the agent's live
`AgentOverride` first (if mid-meeting/break, Destination/ETA come from
the override's own real `location`/`remainingMinutes`/`reason`); falls
back to `nextScheduleBlock()` otherwise. `Schedule.ts` also gained
`LOCATIONS_TO_AGENTS`, a module-load-time inversion of every agent's real
`AGENT_SCHEDULES` blocks into `location -> AgentId[]`, powering "Related
Departments" without any new authored data.

**Fast travel is the real fade transition, not a fabricated camera pan.**
TradeTown is multi-scene, not one continuous open world, so double-
clicking a building calls the same `SceneManager.goTo(currentScene,
targetSceneId, {fromScene})` fade every door already uses (falling back
to `GameManager.applyLoadedTransform()` if no live scene reference is
available) — never a fabricated continuous pan across scenes that were
never built to be traversed that way.

**Cut entirely, and why:** the brief's 7-stage Building Upgrade/
Construction system (Empty Lot → ... → Landmark, scaffolding, cranes,
construction sounds) — no per-building progression is tracked anywhere;
`CompanyHealth.officeExpansion` is one company-wide 0-100 score, not 11
independent per-building tracks, and reusing it under 11 fake per-building
labels would misattribute a company-wide number the same way earlier
features' "misattribution trap" was avoided (see Feature 34's
`_effective_risk_limits`). Per-building Daily Operating Cost/Power
Status/Building Health/Lifetime Visitors/Most Active Employee/Monthly
Performance — no such data exists per building. "Current Weather" — no
weather system exists anywhere in this codebase.

**Wiring.** `campusMapOpen` joins `gameStore.ts`'s existing `OVERLAY_KEYS`
and shared `setOverlay()` helper, giving it the same mutual-exclusion-
with-every-other-overlay and `world:overlayOpen`-broadcast behavior every
other full-screen panel already has (freezes local player input while
open; never touches the backend tick loop). Opens via a global `M`-key
listener in `CampusMap.tsx` (mirrors `CommandCenter.tsx`'s always-mounted
Tab-key listener — registered before any early return so it keeps
listening even while the overlay's own JSX renders `null`), a new 🗺
CAMPUS button in both `QuickView.tsx` and `FullCommandCenter.tsx`, and a
new "Campus Map" entry in `PauseMenu.tsx`.

**Addendum — HQ Expansion visual.** The user separately supplied a legacy
Cute Fantasy sprite pack (`Old_Sprites.zip`, not part of the repo) and
asked for its building-under-construction art to be used on the Campus
Map. Five frames were hand-sliced from its `Houses_Building_Stages_OLD/
House_1_Stone_Stages.png` sheet (each 48x112, equal-width slices) into
`assets/cute-fantasy-rpg/props/buildings/hq-expansion/stage-{1-5}.png`,
picked up automatically by `scripts/generate-assets.mjs` like every other
asset. `CampusMap.tsx`'s new `HQExpansionVisual` component maps the one
real company-wide `CompanyHealth.officeExpansion` score (0-100) onto
whichever of the 5 stage frames it falls into
(`Math.floor((officeExpansion / 100) * 5)`, clamped) and renders it next
to the Campus Overview stats via `AssetLoader.get(id).url` — the same
manifest-lookup convention every asset access in this codebase already
uses, even though this is React UI code rather than a Phaser scene. This
is deliberately still just one visual bound to one already-real number,
not the per-building construction system this file's Campus Map section
above explicitly cut.

### The Original Founders (Feature 39)

The brief describes two Founders whose teaching style ("teaches through
questions, case studies, and reviewing mistakes... rarely gives direct
answers... guides employees toward discovering the correct reasoning
themselves") is near-identical, in both cases, to Sage's already-shipped
Socratic Mentor mechanic (`app/mentor.py`, Feature 32). Building a
second, independent daily-teaching/grading system under new names would
be exactly the "redundant re-measurement under a new name" trap
`mentor.py`'s own module docstring already checked for once (its cut
"Thinking Session"). It is not repeated here.

**Design resolution.** Keystone (Chief Risk Architect) and Compass
(Chief Learning Architect) are framed as the spiritual originators of
two already-real system clusters this codebase built across earlier
features — Keystone for the Discipline Chamber / Library of Mistakes /
Risk Engine (`app/discipline.py`, `app/mistakes.py`, Sentinel/Guardian's
real `RiskWarning`s), Compass for the Academy / Reasoning Lab /
Reflection Chamber (`app/reasoning_lab.py`, `app/wisdom.py`, Sage's own
domain). Sage remains the one who actively runs the daily Socratic
mentoring mechanic; the Founders provide an identity/personality layer
on top — real, hand-authored philosophy/specialty/quote content taken
directly from the brief — plus a real reaction to whichever event most
recently landed in their own domain, using `mentor.py`'s own
`_related_reference`-style templated-framing-over-real-state pattern
(see `app/founders.py`'s `_keystone_reference`/`_compass_reference`).

**Added as real agents, not a parallel system.** `"keystone"`/`"compass"`
join `AGENT_IDS` (11 → 13) the same proven way `"cio"`/`"sage"` were
added in Features 24/32: a real `AgentProfile` entry (`app/agents.py`),
a real `AGENT_SCHEDULES` entry (`app/schedule.py`) routing them through
real locations (`trading-floor`/`executive-boardroom`/`meeting-room`/
`lobby` for Keystone; `brain-room`/`meeting-room`/`hall-of-fame`/`lobby`
for Compass), and automatic participation in every generic
`all_agent_ids()`-driven system (mood/energy, default agent state,
`register_agents()`'s self-healing migration for old saves). Neither
ever routes through a trading task or earns Academy Knowledge Points —
`academy.py`'s `KNOWLEDGE_BRANCH` deliberately has no entry for either,
a documented exception (see `test_academy.py`), since they're the
spiritual originators of that system, not students inside it.

**Founder Log** (`FounderLogEntry`, `app/founders.py`): one real dialogue
line per in-game day, alternating Keystone/Compass by day parity, at a
distinct hour (`FOUNDER_LOG_HOUR = 10`, separate from Sage's own
`MORNING_QOTD_HOUR` so neither mechanic is ever confused with the
other). `_keystone_reference()`/`_compass_reference()` point at whichever
real event — a `DisciplineReview`/`CaseStudy` for Keystone, a
`ReasoningChallenge`/`ReflectionSession` for Compass — most recently
landed in that Founder's domain, and return `None` (no entry recorded)
when that Founder's domain genuinely has nothing real yet, an honest
empty state never papered over. The line pairs a real, verbatim-from-
the-brief quote (`FOUNDER_QUOTES`, cycled deterministically by
`sim_day % len(quotes)`, the same convention `mentor.py`'s own
`QUESTION_LIBRARY` already established) with the real reference.

**Founder Council** (`FounderCouncilSession`): generated on the same
monthly cadence as the existing `CoachReport` (`nexus.py`'s
`is_evening and new_time.day % MONTHLY_INTERVAL_DAYS == 0` block),
summarizing the just-generated monthly report's own real
`strengths[0]`/`recommendations[0]` alongside each Founder's own latest
real domain reference — never a fabricated meeting transcript.

**Legendary Status.** `FounderState.retired` (`compute_founder_state()`)
flips permanently to `True` the first time `CompanyHealth.tier` reaches
`"excellent"` — the single most comprehensive real milestone this
codebase already computes (a genuine average across ten real
sub-scores) — and never reverts once true, the same "a crossed milestone
stays crossed" convention `app/hall_of_fame.py` already established for
its own permanent records. Retirement doesn't change either Founder's
schedule, personality, or dialogue in any way — it only unlocks the Hall
of Founders view in the Command Center's `FOUNDERS` tab.

**Cut entirely, and why:** unique portraits/animations — reuses the
exact same palette-swapped sprite convention every other agent already
has (two new tint colors, `0x8C7A5C` for Keystone, `0x3FBFA0` for
Compass); no new art pipeline exists. Voice acting — the brief itself
calls this optional ("if voice acting is added later"); no audio/TTS
system exists anywhere in this codebase. Onboarding for new employees —
this codebase has a fixed 13-agent roster; no new-hire system, no
employee ever joins the company after the game starts, so there is
nothing to onboard. Employees "speaking about them with respect" in
meetings — would require editing `app/discussion.py`'s real,
already-tested meeting-dialogue generator to inject Founder references;
left as a clean follow-up rather than risking a working system in this
pass.

**Frontend.** A new `FOUNDERS` tab in the Full Command Center
(`FoundersPanel.tsx`) shows both Founders' real identity (badge, title,
philosophy, personality, specialties, quotes, teaching style — mirrored
as static content in a new `frontend/src/game/systems/founders.ts`, the
same "real content mirrored client-side" convention `Schedule.ts`
already established), Legendary Status, the real Founder Log, and real
Founder Council history. Because the Campus Map (Feature 38) already
iterates `AGENT_IDS` generically, Keystone and Compass appear on it
automatically with no Campus Map code changes needed.

**Verification.** 15 new backend tests (`test_founders.py`) covering log
generation (both founders, honest-empty-state, quote cycling, domain
preference), Founder Council generation (empty vs. real content), and
retirement (stays active, flips permanently, never un-retires) — full
backend suite 432/432 passing (417 pre-existing + 15 new), mypy/ruff
clean. Two pre-existing tests (`test_academy.py`,
`test_wisdom.py`) needed updates for the roster growing from 11 to 13 —
both are genuine, correct behavior changes (Founders deliberately excluded
from Academy Knowledge; Founders genuinely attend the Reflection Chamber),
not regressions. Frontend `tsc -b`/eslint/build clean. Playwright
regression re-verified across `commandCenter.spec.ts` (new FOUNDERS tab
test; updated tab count/list), `campusMap.spec.ts` (updated Employee
Count assertion), `executiveVoting.spec.ts`, `marketObservatory.spec.ts`.
Also manually confirmed a real schema-migration round trip against a
genuine pre-Feature-39 save already on disk — the backend's existing
`register_agents()`/`_migrate_dict()` self-healed the roster and added
the missing `founder_state` field with no data loss, no special-casing
needed for this feature.

### Expert Consultation & Career Levels (Feature 40/40.5)

The brief bundled three sections — "Content Review & Validation System,"
"Learning Paths & Specializations," and "Expert Consultation System" —
that, on inspection, are ~85-90% already-shipped functionality wearing
different names. Rather than either refuse the whole spec or build a
bloated duplicate system, this feature keeps the already-real systems as
they are and adds only the one genuinely new mechanic underneath.

**Cut entirely — the Content Review pipeline.** The brief's 8-stage
Educational Review Pipeline (CEO Assignment → Coach Review → Founder
Council Review → Research Validation → Academy Decision → Learning
Output → Knowledge Debate → CEO Feedback) requires ingesting player-
supplied content to review. This codebase has zero HTTP client (not even
`requests`/`httpx` in `requirements.txt`), no PDF/video parsing, and no
free-form NLG/LLM call anywhere. This is the exact same gap "Player
Knowledge Import" was already cut for above (Feature 25/31's section) —
restating that precedent rather than re-litigating it.

**Already real — Learning Paths & Specializations.** `app/academy.py`'s
existing `KnowledgeLevel` (7 tiers, `novice`→`mentor`, added in Feature
31) already *is* the brief's Student→Junior→Professional→Senior→Expert→
Master→Legend ladder — same seven rungs, same one real monotonically-
growing number driving them. `KNOWLEDGE_BRANCH` already assigns every
original agent one fixed, real specialization (Echo = Technical
Analysis, Sentinel = Risk Management, and so on). Building a second
parallel progression system for the same real signal would be the
duplication this session's convention exists to avoid — so the frontend
just relabels what's already there. A new `frontend/src/game/systems/
careerLevels.ts` maps `KnowledgeLevel` to a "Career Level" name
(`careerLevelLabel()`) and derives a "Company Major" (`companyMajor()`,
`Bachelor of {branch}`) — but only once an agent's real `tier` has
actually reached 3 (`advanced`/"Senior"); below that it returns `null`,
an honest empty state rather than a fabricated major from day one. Shown
per-agent in the Command Center's `KNOWLEDGE` tab, under each agent's
existing Knowledge Trees row.

**Already real — the Expert Consultation System.** Executive Voting
(Feature 12) already implements nearly the entire brief section under
different names: `AnalystVote{role, agentId, choice, reasoning,
evidence}` is the per-specialist review; `TradeProposal` is the Lead
Analyst's proposal; `DecisionConfidence` (Feature 15) is the weighted
Consensus Report; `Debate`'s (Feature 17) cross-examination is "healthy
disagreement"; `OperatingMode` (`"learning"`/`"assisted"`/`"executive"`)
is the brief's three automation modes; a resolved `TradeDecision`/
`CaseStudy` is the permanent consultation record. The one genuinely new
piece is **"Request More Research" / "Delay Decision"** — two real CEO
actions distinct from buy/sell/wait, for when the desk isn't ready to
call it yet. Both do the exact same real thing under the hood: reset the
proposal's own existing expiry clock (`TradeProposal.created_sim_minutes`
— the same field `app/executive.py`'s `expire_stale_proposals()` already
reads) via a new `hold_proposal()`, rather than inventing a second timer
or a fake "research in progress" status with no real signal behind it.
A new `hold_count` field caps each proposal at `MAX_PROPOSAL_HOLDS` (2)
— once exhausted, the CEO must actually decide or let the proposal
expire the normal way. A hold never produces a `TradeDecision` or
`CeoDecisionRecord`: nothing has actually been decided, so the proposal
simply stays pending. Every hold is still logged to Company Memory
(`app/scribe.py`'s `record_proposal_hold()`) as a real, permanent record
of when and why the desk was asked to wait. New `POST /api/executive/
hold` endpoint backed by `GameState.hold_trade_proposal()`
(`app/state.py`). Two new buttons ("Request More Research" / "Delay
Decision") in the Executive Voting popup, showing the real
`holdCount`/`MAX_PROPOSAL_HOLDS` progress and disabling once the cap is
reached.

**Verification.** 5 new backend tests (`TestHoldProposal` in
`test_executive.py`, covering expiry-clock reset, hold-count increment,
never-resolves-to-a-decision, cap enforcement, and exactly-at-cap
behavior) — full backend suite 437/437 passing (432 pre-existing + 5
new), mypy/ruff clean. Frontend `tsc -b`/eslint/build clean. Playwright
regression re-verified across `executiveVoting.spec.ts` (new test
holding a proposal to its cap and confirming it never resolves) and
`commandCenter.spec.ts` (new Career Level assertion on the `KNOWLEDGE`
tab) — 35/35 passing, plus the same tolerated real-trade-timing skip
every run of this suite already carries.

### Intelligent Devil's Advocate & Innovation Points (Feature 41)

The brief's Devil's Advocate System and Innovation Points, checked
against four already-real systems before writing anything: the AI
Debate Room (Feature 17), the Library of Mistakes' `CaseStudy` (Feature
27), the What-If Simulation Lab (Feature 16), and Hall of Fame (Feature
24).

**Challenge Report, not a second Debate Room.** Feature 17's AI Debate
Room already has every analyst who genuinely disagrees challenge the
proposal in real time — building a second, parallel "devil's advocate
challenges the proposal" mechanic on top of that would be exactly the
duplication this session's convention exists to avoid. Instead
`app/devils_advocate.py`'s `generate_challenge_report()` produces a
single structured artifact per proposal, built entirely from real
signals already computed elsewhere:

- **Bull/bear case** — the real `AnalystVote.reasoning` of whichever
  analysts agreed/disagreed with the desk's overall recommendation.
- **Hidden risks** — the proposal's own real `risk_summary` (already
  carries the real Sentinel/Guardian warning message when one exists).
- **Weak assumptions** — any real `DecisionConfidence` factor scoring
  below `WEAK_FACTOR_THRESHOLD` (50).
- **Missing evidence** — any real `AnalystVote` with an empty evidence
  list.
- **Historical comparisons** — real past `CaseStudy` (Library of
  Mistakes) titles for this same symbol; an honest empty list if none
  exist, never a fabricated "similar situation."
- **Worst case scenario** — one line drawn from the What-If Simulation
  Lab's own real worst named scenario (`app/whatif.py`). Only that one
  line is persisted — never the full `WhatIfSimulation`, which this
  codebase has already been bitten once by persisting unbounded computed
  data (see `nexus.py`'s `MAX_DECISIONS` history above).

`severity` (`none_found`/`minor`/`major`) is a real, checkable count of
how many of those concern categories — plus real analyst dissent —
actually found something; it is never a fabricated judgment call, and
"no significant weaknesses found" is a genuinely earned Outcome 1, not a
default. The assigned employee rotates deterministically through a
fixed pool of five (`ELIGIBLE_DEVILS_ADVOCATES`: Scribe, Coach, Guardian,
the CIO, Sage) — never one of the proposal's own six analyst seats
(echo/scout/nova/sentinel/pulse/atlas), and never Keystone/Compass, who
per Feature 39 never route through operational work. Rotation is
derived from the existing report count, the same "no extra counter
needed" convention `app/academy_research.py` already established.
Generated automatically alongside the Debate the instant a new proposal
is created (`nexus.py`), with a "Request Another Review" button in
Executive Voting mirroring Feature 17's own "request another debate."

**Innovation Points, not a duplicate Academy ladder.** `app/innovation.py`
computes a second, deliberately narrow tier ladder — where Academy's
`KnowledgeLevel` (and Feature 40's Career Level relabeling of it) tracks
general knowledge mastery, this tracks one specific real skill: an
agent's own record as a Devil's Advocate. Points are awarded per
Challenge Report the agent authored, weighted by its own real severity
(`MAJOR_POINTS` 3.0 > `MINOR_POINTS` 1.0 > `NONE_FOUND_POINTS` 0.5 — the
brief's own philosophy that intellectual honesty, not just catching
problems, is a real contribution). Four thresholds
(`TIER_THRESHOLDS = (3.0, 8.0, 18.0, 35.0)`) give five real tiers
(Research Contributor → Research Specialist → Innovation Leader → Chief
Innovator → Legendary Innovator), computed fresh every tick as a pure
function of the persisted `challenge_reports` list — the same
"recomputed, not incrementally mutated" convention `app/academy.py`'s
`compute_academy_state()` already established, so it can never drift.

**Cut, and why.** Re-awarding Innovation Points for events Academy
Points already scores (course completion, research, mentoring) would be
double-counting the same real signal under two names — the exact
duplication check this session runs before building anything. Project
Proposals (the brief's 9-field business-plan workflow: Problem/Why/
Existing Solutions/Proposed Improvement/Expected Benefits/Risks/
Required Research/Departments/Success Metrics) are cut outright: no real
signal in this codebase backs any of those fields, and fabricating them
would be the same dishonesty already rejected for Player Knowledge
Import (see Feature 25/31's own scope-cut note above). "CEO Innovation
Challenges" don't exist anywhere in this codebase. Breakthrough
Recognition / a Legacy Museum is not separately built — Hall of Fame's
existing `best_research` category (Feature 24) already is permanent
recognition of a real broken record, and a second version of the same
real concept would be the exact duplication this feature otherwise took
care to avoid throughout. Per-concern "documented response" tracking
(the brief's Team Discussion section) is cut: concerns in a Challenge
Report have no persistent per-item identity anywhere else in this
codebase, and the CEO's own real decision (buy/sell/wait, or Feature
40.5's Request More Research/Delay Decision) already *is* the real,
visible resolution sitting right next to the report in Executive Voting
— tracking a second, parallel per-bullet response would invent
structure with nothing real behind it.

**Frontend.** A new "Devil's Advocate Review" expandable section in
`ExecutiveVoting.tsx` (mirroring the Debate Room's own toggle pattern)
shows the assigned employee, severity badge, and every real field above,
with its own "Request Another Review" button. A new "Innovation Points"
card in the Command Center's `KNOWLEDGE` tab (`AcademyPanel.tsx`) lists
every agent's real points/tier, right below the existing Career Level
display — an honest empty state until the first Challenge Report is
filed.

**Verification.** 18 new backend tests (`test_devils_advocate.py`,
`test_innovation.py`) covering rotation, severity classification, real
signal extraction (hidden risks/weak assumptions/missing evidence/
historical comparisons), and tier/points accumulation — full backend
suite 455/455 passing (437 pre-existing + 18 new), mypy/ruff clean.
Frontend `tsc -b`/eslint/build clean. Playwright regression re-verified
across `executiveVoting.spec.ts` (new test opening the Devil's Advocate
Review, confirming real content, and confirming the rotating assignment
actually changes across two consecutive "Request Another Review" calls)
and `commandCenter.spec.ts` (new Innovation Points assertion on the
`KNOWLEDGE` tab) — 36/36 passing, plus the same tolerated real-trade-
timing skip every run of this suite already carries.

### Advanced Quantitative Research Division

The brief's "Chief Quantitative Strategist," "Quant Lab," "Black Box
Research Projects," "CEO Research Dashboard," "Advanced Research
Teams," "Team Chemistry," "Research Meetings," "Innovation Points"
progression, "Eureka! Breakthrough System," "Founder Council Review,"
"Museum of Discoveries," "Failed Research," and "World Reputation,"
checked against every already-real system it overlaps before writing
anything: Devil's Advocate + Innovation Points (Feature 41 above,
which already owns the exact five-tier Research Contributor →
Legendary Innovator ladder the brief separately asks for), the
Founder Council (Feature 39), the Simulation Lab's real backtesting
engine (v0.5), the Hall of Fame's permanent-record mechanism, and
`company_health.py`'s real `reputation` sub-score.

**Vector, the Chief Quantitative Strategist — the fourteenth agent.**
Added the same proven way Meridian/Sage/Keystone/Compass were: a real
`AgentId`, `AgentProfile`, schedule (`app/schedule.py`), dialogue
lines, and a palette-swapped sprite (same 7-color remap table
reverse-engineered by diffing `Player.png` against an existing
variant). Works out of the **existing Simulation Lab room** — no new
physical "Quant Lab" scene was built; that's real content layered onto
an already-real room, the same precedent Discipline Chamber/Reasoning
Lab/Reflection Chamber/Mentor already established for not needing new
art per feature.

**Black Box Research Projects, not a third rotating-queue system.**
`app/black_box.py` mirrors `academy_research.py`'s own "exactly one
active project, real fixed catalog, deterministic rotation" shape, but
on a genuinely different cadence: progress advances once per real
in-game day (gated on the same `is_evening` marker the weekly/monthly
cadences already use), not once per tick, so a project takes 21-35
in-game days to reach review — a real weeks-scale investment, not a
minutes-scale one dressed up with a bigger number. Funding and
priority are real levers: an unfunded project's daily gain drops to a
near-stall and logs a real "Insufficient funding" obstacle; obstacles
mechanically lower the project's own `confidence_level`.

**Team formation is real occupation-fit, never a fabricated score.**
The brief asks for team selection weighted by "Skill/Experience/
Innovation Points/Collaboration Score/Personality/Workload/Previous
Research Success" — most of those have no real per-agent number
anywhere in this codebase. What's actually built: four seats matched
to whichever existing agent already has that real occupation (Echo/
Technical Analyst, Nova/Fundamental Analyst, Sentinel-or-Guardian/Risk
Specialist alternating by project count, Coach/Psychology Coach), and
a Devil's Advocate seat chosen from `devils_advocate.py`'s existing
eligible pool by whichever candidate has the most real Innovation
Points — one genuine real signal reused, not several fabricated ones
invented. No "AI Research Scientist" seat: no agent in this thirteen-
(now fourteen-)agent roster has that occupation, and this feature
already adds one new agent — a documented cut, not a silent omission.

**Devil's Advocate and Innovation Points reused, not duplicated.**
`generate_project_challenge()` builds the exact `ChallengeReport` shape
`devils_advocate.py` already defined, from the project's own real
fields (obstacles → hidden risks, low confidence → weak assumption, an
empty `researchNotes` → missing evidence). The resulting report is
appended into the same `challenge_reports` history `innovation.py`
already reads, so a project's Devil's Advocate review earns real
Innovation Points through the existing pipeline automatically — a
second, parallel points ladder was never built.

**Founder Council Review is a new mode of the existing council
generator.** `founders.py`'s `generate_breakthrough_review()` sits
beside the existing monthly `generate_council_session()` rather than
inventing a second, independent Founder meeting type. The verdict is
real and checkable: approved only if the Devil's Advocate found
nothing major *and* the project's confidence level cleared a real
55/100 bar — never a coin flip, never a fabricated "the Founders
debated for hours" narrative.

**Museum of Discoveries extends Hall of Fame, doesn't duplicate its
mechanism.** `HallOfFameEntry` gained three optional fields
(`discoveryTimeline`/`supportingEvidence`/`companyImpact`), populated
only for a new `breakthrough` category — reusing the exact "permanent,
never-evicted record" guarantee `hall_of_fame.py`'s own module
docstring already establishes, rather than building a second
permanent-record system next to it.

**Failed Research is the project archive, not a second schema.** A
rejected project moves into `blackBox.archive` with `status: "failed"`
and the Council's own real rejection reason appended to
`researchNotes` — that archive entry *is* the brief's "Research
Archives... never wasted." No separate `ResearchArchiveEntry` type
was needed.

**World Reputation is the real number, not simulated institutions.**
`company_health.py`'s `reputation` sub-score already grows with Hall
of Fame entry count (which a breakthrough's Museum entry feeds
automatically). A breakthrough additionally files one real `NewsItem`
naming that real number — never a fabricated "University X references
our research" event, since no such external-entity system exists
anywhere in this codebase.

**Explicitly not built, and why.** Team Chemistry as a distinct
fabricated pairwise-relationship system — no real per-pair signal
exists anywhere in this codebase to back one honestly, and inventing
one would be exactly the kind of "invented mechanic with no real
backing" this session's whole convention exists to avoid. A separate
"Research Meetings" transcript system — the Quant Journal (one real
templated line per project-day) already serves as the real meeting
record, the same "don't duplicate `discussion.py`/`debate.py`"
reasoning `founders.py`'s own module docstring already applied to the
brief's Founder "teaching sessions." Breakthrough effects like
"unlock new Academy lessons/buildings/automation/dialogue" — checked
directly: `education.py`'s lessons have no locked/unlocked concept at
all (`all_lessons()` returns a fixed list), and no other system in
this codebase tracks lockable content, so there's nothing honest to
hook an "unlock" into.

**Backend.** `app/black_box.py` (new), `app/founders.py`
(`generate_breakthrough_review()`), `app/schemas.py` (`AgentId` +=
`"quant"`, `BlackBoxProject`/`BreakthroughReview`/`BlackBoxState`,
`HallOfFameEntry`/`HallOfFameCategory` extended), `app/agents.py` +
`app/schedule.py` (the Quant's profile/schedule), `app/nexus.py`
(daily tick + review orchestration), `app/state.py` (CEO Research
Dashboard controls), `app/routers/black_box.py` (new), `app/
save_modules.py` (`black_box` added to the `research` module).

**Frontend.** `BlackBoxPanel.tsx` (new BLACKBOX Command Center tab —
current project, team with real reassignment, obstacles, CEO controls,
Founder Council review history, Museum of Discoveries, Research
Archives), `BreakthroughMoment.tsx` (new — the Eureka! cinematic, a
real full-block overlay added to `gameStore.ts`'s existing
`OVERLAY_KEYS` mechanism), `AgentProfiles.ts`/`Schedule.ts`/
`DialogueManager.ts` (the Quant's frontend mirrors), `types.ts`/
`NexusManager.ts`/`EventBus.ts`/`socket.ts`/`api.ts` (the new
`BlackBoxState` wiring end-to-end).

**Verification.** 12 new backend tests (`test_black_box.py`) covering
default state, team formation, Devil's Advocate non-collision,
paused/unfunded projects, severity classification, and Founder Council
approval/rejection — full backend suite 485/485 passing (473
pre-existing + 12 new), mypy/ruff clean. A full end-to-end simulation
(15,000 five-minute ticks ≈ 52 in-game days) confirmed a real project
ran, stalled on real obstacles, was rejected by a real Founder Council
verdict with a real reason, and archived — with the whole resulting
state round-tripping cleanly through Pydantic validation. Frontend
`tsc -b`/eslint/build clean. Playwright regression re-verified with a
new `blackBox.spec.ts` (Quant agent + `blackBox` present in `GET
/api/load`; the BLACKBOX Command Center tab opens and shows real
content with zero console errors) — passed cleanly in every run,
isolated and as part of the full suite.

The full existing suite itself showed elevated flakiness while
verifying this feature: 10-19 pre-existing tests intermittently
failed, always with the identical signature — a real Executive Voting
popup (`data-testid="executive-voting"`) intercepting a click meant for
something else, because the sim generates real trade proposals
continuously in real time across this suite's ~12-14 minute single-
worker run. This was investigated thoroughly rather than assumed
harmless: an isolated single test passed cleanly; a fresh-backend
(day-1, zero accumulated state) full-suite re-run still showed 15
failures spread across `campusMap.spec.ts`, `executiveVoting.spec.ts`,
and `marketObservatory.spec.ts` — files this feature never touches —
confirming the elevated rate is a pre-existing, environment-wide
characteristic of this session's test run, not something this feature
introduced or something a code fix here could resolve. One genuine gap
this investigation did surface and fix: `commandCenter.spec.ts` had
several tests that clicked "EXPAND" without first calling the file's
own `dismissTradeOutcomePopups()` helper (which most other tests in
the same file already did) — 15 missing calls added, plus the
21-tab-count test updated to 22 for the new BLACKBOX tab. `blackBox.spec.ts`
itself never failed in any of these runs.

### Decision Replay Center

The brief asked for per-trade Stop Loss/Profit Target/Expected Value
recording, a 13-stage decision timeline (Research Started → ... →
Reflection Chamber Review), a "Team Replay" of every real opinion,
natural-language "Smart Search," and automatic lesson generation. Checked
first against everything real this codebase already computes per
decision: `TradeDecision` already carries `researchSummary`/
`technicalSummary`/`fundamentalSummary`/`riskSummary`/`confidenceEngine`/
`gatekeeperVerdict` forward from the `TradeProposal` that produced it, and
a decision's id (`decision-{proposalId}`) already joins cleanly across
`Debate.proposalId`, `ChallengeReport.proposalId`,
`CeoDecisionRecord.decisionId`/`.proposalId`, `PaperTrade.decisionId`,
`DisciplineReview.decisionId`, and `CaseStudy.decisionId` — every one of
these is already broadcast over the WebSocket in a capped, permanent
list. There was no missing data, only a missing unified viewer — so this
shipped as a **frontend-only feature**, no new backend endpoint or
schema for the join itself.

**The join lives in `frontend/src/ui/components/CommandCenter/lib/derive.ts`.**
`buildDecisionReplay()` does the actual cross-list lookup (the same
`linkedOrderFor()`/`exitOrdersForPosition()` helpers `DecisionDetail.tsx`
already used, extended to the five additional lists);
`buildReplayTimeline()` turns that into the brief's 13 named stages, each
tagged `recorded` / `not_generated` / `not_applicable` rather than a
fabricated "in progress." Two honest departures from a literal reading:

- **"Quant Review" is always `not_applicable`.** Quant/Vector reviews
  long-horizon Black Box research projects (weeks of in-game time), never
  an individual trade decision — confirmed by grep, there is no per-trade
  Quant review mechanism anywhere in this codebase, and none was invented
  to fill this stage.
- **"AI Research" is folded into Research/Technical/Fundamental
  Analysis** rather than shown as a fifth, separate stage — all four
  would read from the exact same real summary fields on `TradeDecision`,
  so splitting them would just repeat identical text under a second
  label.

The final stage is labeled "Post-Decision Review," backed by
`DisciplineReview`, rather than a literal "Reflection Chamber Review" —
this codebase's real per-decision post-mortem is the Discipline
Chamber (`app/discipline.py`); "Reflection Chamber" names a different,
company-wide weekly/monthly system (`app/wisdom.py`) with no per-decision
link to key off. Naming it accurately here avoids implying a link that
doesn't exist.

**Smart Search became structured filters, not a fabricated NL parser.**
No LLM/language-understanding infrastructure exists anywhere in this
backend (confirmed by grepping the whole codebase for
`openai|anthropic|LLM|gpt-|claude-|embeddings` — zero real hits; every
"AI-generated" line in TradeTown is deterministic string templating, by
design, per nearly every module's own docstring). Rather than fake a
parser, `matchesReplayFilters()` implements the brief's own filter list
(Employee/Strategy→Category/Market/Date/Result/Confidence/Risk/
Department) as real dropdowns and a slider, and every one of the brief's
own search *examples* ("show all losing trades," "show trades above 85%
confidence," "show every trade where Risk disagreed") is reachable
through them. "Department" maps to `AnalystRole` (technical/news/macro/
risk/sentiment/execution) — the closest real per-decision "who reviewed
this" grouping this codebase has, since no literal department concept
exists at the per-trade level. "Show every breakout strategy" and "show
every trade during earnings" are not supported (no strategy taxonomy or
earnings calendar exists in this codebase) and "reviewed by the Quant"
is not supported for the same reason Quant Review is `not_applicable`.

**Stop Loss / Profit Target / Expected Value are not shown — an
inherited, already-documented boundary, not a new gap.** TradeTown's
paper broker has never placed a real stop-loss/take-profit exit order
(`OrderType` has always included the literal `"stop"`/`"take_profit"`/
`"stop_loss"` values, but grepping `executive.py`/`broker.py` confirms
nothing has ever placed one), and no calibrated probability model exists
anywhere to honestly compute an Expected Value from. This is the exact
same boundary `DecisionDetail.tsx`'s "Trade Plan" section and
`app/gatekeeper.py`'s own module docstring already documented — the
Replay Center's Decision Recording panel says so explicitly rather than
inventing a number.

**"Successes" lesson generation, `app/successes.py` — the one genuinely
new backend piece.** The brief's "Lesson Generation" list (Successes,
Mistakes, Missed Opportunities, Suggested Improvements, Academy Lessons,
Reflection Questions, Case Studies) is mostly already real under other
names (`ChallengeReport.suggestedImprovements`, `CaseStudy` itself for
Mistakes, `GatekeeperRejection.outcome == "would_have_won"` for Missed
Opportunities) except "Successes" — `app/mistakes.py`'s Library of
Mistakes has only ever filed a `CaseStudy` for a real loss.
`app/successes.py` mirrors it exactly for a real win: three new
`CaseStudyCategory` values (`disciplined_process`,
`rigorous_cross_examination`, `patient_execution`), each the crisp
inversion of one of the six existing mistake categories' real trigger
signal (a discipline score of 70+, real cross-examination beyond opening
statements, holding to the patient-hold target) — reusing the exact same
`CaseStudy` schema and `case_studies` list rather than a second, parallel
one. The other three mistake categories (`incomplete_research`/
`ignored_dissent`/`confirmation_bias`) have no equally crisp opposite
("research was NOT incomplete" is just the normal case, not a
distinguishable success story) and are deliberately not mirrored. The
Command Center's Discipline tab is retitled "Library of Mistakes &
Successes" and color-codes each entry (green/red) rather than silently
mixing success entries into a section still named only for mistakes.

**Verification.** Backend: `test_successes.py` (10 new tests, mirroring
`test_mistakes.py`'s structure — each category's real trigger condition
checked to fire exactly when expected and not otherwise) + the full
suite (496/496) + mypy/ruff clean. Frontend: `tsc -b`/eslint/build clean;
a new `replay.spec.ts` (3 Playwright tests against the live stack —
opening the REPLAY tab, filtering + resetting, opening a real decision's
replay and confirming the Full Decision Timeline renders with an honest
per-stage status) all passed; `commandCenter.spec.ts`'s tab-count test
updated to 23 tabs, its number-key-shortcut test updated for COMPANY's
shifted index (8 → 9, since REPLAY now sits between DECISIONS and RISK),
and its Discipline-tab test updated for the retitled panel heading.

### Executive Intelligence Dashboard

The brief asked for a 13-metric "Company Health" list, proactive "CEO
Insights," an AI-ranked "Executive Priorities" list, multi-year
"Performance Trends," and per-department status for 8 named departments.
Checked first against what already exists: `company_health.py`'s
`CompanyHealth` (10 sub-scores) and `company_score.py`'s `CompanyScore`
(7 metrics) already cover most of the brief's own "Company Health" list
under different names; `PerformanceSnapshot` (weekly/monthly/all-time,
already surfaced on the PERFORMANCE tab) already covers "Performance
Trends"; and `CompanyHealth.recommendations` already generates real,
checkable "why this matters" text every tick — the honest core of "CEO
Insights" already existed, just not unified into one ranked view. Two
pieces were genuinely missing: a company-wide behavioral profile
("Company DNA," the one item the overlap research flagged as clean) and
a real per-department rollup.

**Company DNA — the one genuinely net-new concept** (`app/company_dna.py`).
Five real, descriptive behavioral traits, each computed from the
company's own historical decision/trade record, each with an honest
neutral 50.0 default and a real `sampleSize` field until there's enough
history to say anything real:

- **Risk Appetite** — % of executed trades taken on a "moderate" or
  weaker Decision Confidence Engine tier rather than strong/elite.
- **Patience** — average real `PaperTrade` hold duration against
  `discipline.py`'s own `PATIENCE_TARGET_MINUTES` bar, the same real
  yardstick the Discipline Chamber already uses per trade, applied here
  as a company-wide average.
- **Contrarian Tendency** — % of `CeoDecisionRecord`s where
  `agreedWithAi` is false.
- **Research Rigor** — average real Decision Confidence Engine score
  across every graded decision.
- **Collaboration Style** — % of decisions where the six analysts cast
  at least two distinct real vote choices.

Deliberately reuses none of `company_health.py`'s `team_chemistry` or
`company_score.py`'s `team_coordination` signals — three independent
company-culture readings exist now, each backed by a genuinely different
real behavior (debate stance ratio, raw agent mood, and historical
decision/trade patterns respectively), not three fabricated readings of
the same thing under different names.

**Team Chemistry — a real 11th `CompanyHealth` sub-score, and a
self-corrected inconsistency.** While researching Company DNA, the
Advanced Quantitative Research Division's own module docstring
(`app/black_box.py`) was found to claim "Team Chemistry... genuinely
new" among that feature's real additions — but no `team_chemistry` field
had ever actually been implemented anywhere; the claim was aspirational,
not shipped. `company_health.py`'s new `_team_chemistry()` makes it real:
the fraction of "support" (vs. "challenge") stance turns across the
company's most recent 20 AI Debates — genuinely distinct from
`employee_morale` (individual mood, no debate involved) and from
`company_score.py`'s `team_coordination` (also a mood proxy) — this is
specifically about how the team behaves *together* during real
cross-examination, never a fabricated pairwise relationship graph (no
per-agent-pair data exists anywhere in this codebase to build one from).
`black_box.py`'s docstring was corrected to point here instead of
repeating the unfulfilled claim.

**Executive Priorities and Department Health are both pure frontend
derivations** — like the Decision Replay Center, no second backend
computation was needed. `lib/derive.ts`'s `computeExecutivePriorities()`
merges and dedupes `CompanyHealth.recommendations` with the latest
`CoachReport` and `ExecutiveReview`'s own real recommendation text
(first occurrence wins, so a live Company Health read outranks a
possibly-stale periodic report repeating the same point — no invented
ranking model). `computeDepartmentHealth()` maps the brief's 8 named
departments onto the 7 real subsystems this codebase actually has state
for (Academy/Research/Risk/Trading/Innovation/Coach/Founders), each
showing whichever of the brief's five requested dimensions
(Efficiency/Workload/Morale/Productivity/Bottlenecks) that subsystem
genuinely tracks — never a uniform template forced onto systems that
don't track all five. "Brain Room" is dropped entirely: it's the
physical room housing the Overview HUD, not an operational unit with
its own state, so including it would mean inventing metrics for a room.

**Verification.** Backend: `test_company_dna.py` (15 new tests, one per
trait's real trigger/formula, plus the honest empty-history default) +
`test_company_health.py` extended with a `TestTeamChemistry` class (4
new tests) + the full suite (515/515) + mypy/ruff clean. Frontend:
`tsc -b`/eslint/build clean; a new `execIntel.spec.ts` (2 Playwright
tests against the live stack — confirming `companyDna` is present in
`GET /api/load` with all 5 traits, and that the EXECINTEL tab renders
Company DNA/Executive Priorities/Department Health with zero console
errors) both passed; `commandCenter.spec.ts`'s tab-count test updated to
24 tabs (COMPANY's own number-key-shortcut index is unaffected, since
EXECINTEL was inserted immediately after COMPANY rather than before it).

### Talent Discovery System

The brief asked for a "Performance Analysis" trait breakdown, automatic
"Discovery Events" when an employee shows real talent, a CEO decision to
invest in that talent, a per-employee "Growth History," "Career
Development" (promotions, role changes, specializations), and "Team
Optimization" (best-performing pairs, ideal roster composition). Checked
first against what already exists and what the codebase's own
architecture allows: Performance Analysis turned out to already be real
and shipped — `mentor.py`'s `ThinkingProfile` (six traits per agent,
built for Feature 32's Sage/Mentor Chamber) is exactly what the brief
describes, just not surfaced in a talent-specific view. Career
Development and most of Team Optimization ran straight into this
codebase's fixed-roster architecture: `agents.py`'s `AgentProfile` is a
`@dataclass(frozen=True)`, and `founders.py`'s own module docstring
states plainly that there is "no new-hire system, no employee ever joins
the company after the game starts... nothing to onboard." No agent's
occupation, schedule, or room ever changes anywhere in the shipped
codebase (confirmed by grepping for any code that mutates an
`AgentProfile` field — there is none). A promotion or role-change
mechanic, or a roster-recomposition recommendation, would have to be
invented from nothing; neither was built.

**Discovery Events — the one genuinely net-new concept**
(`app/talent.py`'s `generate_talent_reports`). A `TalentReport` only
ever files for one specific agent/trait pair when both of two real,
independently checkable signals hold:

1. That agent's own best `ThinkingProfile` trait score is at or above
   `TALENT_SCORE_THRESHOLD` (80/100) — always the real highest trait,
   never a lower one picked for a better story.
2. Their last `CONSISTENCY_REPORT_WINDOW` (3) `CoachReport` scores are
   *all* at or above `CONSISTENCY_MIN_SCORE` (70) — a one-off good report
   never triggers a Discovery Event on its own; the pattern has to be
   real and sustained.

The report's `evidence` field is the trait's own real `detail` string
(nothing paraphrased or invented), and `report_id` is deterministic
(`talent-{agent_id}-{trait_id}`) so the same pair never re-files once
recorded. "Suggested Focus" deliberately replaces the brief's literal
"Suggested Career Path": since no agent's occupation can ever change,
a career-path recommendation would promise a mechanic this codebase
doesn't have — the field instead names a real coaching focus tied to
the real trait that triggered the report. `MAX_TALENT_REPORTS` (30) caps
the archive the same way `mistakes.py`/`successes.py`/`black_box.py`
already cap their own permanent record lists.

**Growth History and Best Collaborators are both pure frontend
derivations** — like the Decision Replay Center and Executive
Intelligence Dashboard's own derived sections, no second backend
computation was needed for either. `lib/derive.ts`'s
`computeGrowthHistory(agentId, state)` builds a real per-agent timeline
from six sources that already name that agent somewhere in existing
state: `DisciplineReview.attendees`, `ReasoningChallenge.contributions`,
`ReflectionSession.insights`, `ChallengeReport.assignedAgent` (the
Devil's Advocate rotation), Black Box project team membership (active +
archived), and `CoachReport.agentRankings` (that agent's own real score
on each report's filing date) — sorted chronologically by each record's
own real `createdAt`. `computeBestCollaborators(debates)` is the one
real signal salvageable from the brief's "Team Optimization": since the
roster can't be recomposed, nothing about composition can be optimized,
but which agents actually support vs. challenge each other's points
across every real AI Debate (`DebateTurn.respondingTo` + `stance`) is a
real, checkable tally — counted turn by turn, nothing inferred or scored
beyond the real count.

**New `TALENT` Command Center tab** (`TalentPanel.tsx`, inserted right
after `MENTOR` since it directly extends that tab's `ThinkingProfile`
data): Discovery Events with an acknowledge action
(`POST /api/talent/ack-report` → `game_state.ack_talent_report()` →
`mark_talent_report_viewed()`, the same "seen" tracking pattern
`viewedBreakthroughIds`/`viewedTradeNotificationIds` already use), a
per-employee Growth History timeline behind an agent selector, Best
Collaborators, and a Performance Analysis section that reuses the
Mentor tab's own `ThinkingProfileCard` layout rather than recomputing
anything.

**Save/load.** `TalentState` (`reports`, `viewedReportIds`, `updatedAt`)
lives in the `"knowledge_archive"` save module alongside
`case_studies`/`hall_of_fame`/`discipline_reviews` — a permanent,
append-only record, excluded from `GET /api/load` and hydrated purely
via the WebSocket broadcast. `default_state()` seeds an empty
`TalentState`, so an older save missing the field migrates cleanly
through `load_modules()`'s existing deep-merge-onto-`default_state()`
recovery path with no new migration code required.

**Verification.** Backend: `test_talent.py` (8 new tests — fires only
when both thresholds clear, doesn't fire on a short or inconsistent
score history, never re-files an already-filed pair, a missing
`ThinkingProfile` is skipped rather than erroring, the report always
names the real highest trait, and no literal career-path language is
ever promised) + the full suite (523/523) + mypy/ruff clean. Frontend:
`tsc -b`/eslint/build clean; a new `talent.spec.ts` (2 Playwright tests
against the live stack — confirming `talent` is present in
`GET /api/load`, and that the TALENT tab renders Discovery Events/Growth
History/Best Collaborators/Performance Analysis with zero console
errors) both passed; `commandCenter.spec.ts`'s tab-count test updated to
25 tabs (MENTOR's own number-key-shortcut range is unaffected, since
TALENT was inserted well past the 1-9 shortcut range).

### Research Sandbox

The brief asked for an 8-stage strategy pipeline that "strategies cannot
skip," 9 Testing Environments, 10 performance metrics, auto-generated
Strategy Reports, and a 5-role Approval Process gated by Automation
Mode. Checked first against what already exists (see
`app/sandbox.py`'s module docstring): `Strategy`, `ResearchItem`,
`BacktestSession`, and `SimulationResult` were all real and shipped
back in v0.5 — the actual gap was stage-gating, scenario-awareness,
auto-generated reports, and a real multi-reviewer review, not new base
data.

**The 8-stage pipeline never skips a stage** (`Strategy.stage`/
`stageHistory`, `app/sandbox.py`'s `_advance()`). The first four stages
advance automatically the moment a real signal clears:

- **idea → research**: a completed `ResearchItem` in the strategy's own
  `focus_category` exists.
- **research → historical_backtest**: a completed `SimulationResult`
  with `scenario == "historical"` exists.
- **historical_backtest → market_simulation**: a completed result in
  any *other* scenario exists — but only once historical backtesting is
  already on record, so a strategy can't "skip" straight to Market
  Simulation by testing a bull scenario first.

The last four stages are real CEO actions — `POST /api/sandbox/
begin-paper-trial` / `begin-limited-live` / `request-review` /
`decide` — because this codebase's live/paper trading loop is symbol-
and AI-Debate-driven, not `Strategy`-driven: there is no mechanism
anywhere in this codebase to attribute a real executed trade back to a
specific `Strategy` object, and building one would be a structural
rewrite of the whole decision loop, not a Feature-45-sized change.
Rather than fabricate that linkage, Paper Trading/Limited Live
Capital/Company Review are real, CEO-authorized trust checkpoints — a
tracked, bounded `allocated_capital` ceiling the CEO sets on entering
Limited Live Capital (capped at `MAX_LIMITED_LIVE_CAPITAL`, $2,000) is a
real number the CEO chose, never wired into fabricated live P&L.

**Scenario-aware backtesting, one real engine** (`app/simulation.py`).
`BacktestSession`/`SimulationResult` gained a `scenario` field
(`TestScenario`) reusing the exact 5 regime names
`market_environment.py` already computes live for the whole company
(bull/bear/sideways/high_volatility/low_volatility), plus "historical"
(the pre-Feature-45 default, keeping every old session's meaning) and
"custom" (a CEO-tunable deterministic bias — `custom_return_bias_pct`/
`custom_volatility_bias`, real chosen numbers applied to the same
placeholder ranges, never an independently invented range). "Earnings
weeks" and "economic news" from the brief's longer Testing Environments
list are deliberately not built: no earnings calendar or economic-event
data source exists anywhere in this codebase (confirmed by grep — even
`app/calendar.py`'s own `systemEvents` never included either). Building
a second, independent backtest engine for "Market Simulation" would
have been the exact redundant-remeasurement trap this session's whole
discipline exists to avoid — one real engine, scenario-parameterized,
honestly serves both Historical Backtest and Market Simulation stages.

**Fuller, internally-consistent metrics.** `win_count`/`loss_count`/
`avg_win_pct`/`avg_loss_pct` are now the placeholder engine's own real
*generating* inputs — `total_return_pct` is derived FROM them
(`win_count * avg_win_pct + loss_count * avg_loss_pct`), not the
reverse, so `expected_value_pct`/`profit_factor`/`risk_reward_ratio` are
real, internally-consistent derivations of that one run's own numbers,
never independently rolled. "Consistency" and "Trade Frequency" from
the brief are left as frontend derivations over a strategy's own stored
result *history* (`lib/derive.ts`'s `computeStrategyConsistency`)
rather than stored per-run, since both are properties of the history,
not of any single run.

**Strategy Reports, auto-generated per completed run**
(`generate_strategy_report`). Executive Summary/Strengths/Weaknesses/
Failure Conditions/Best Market Environment/Recommended Improvements,
every field a templated read of that one real `SimulationResult`'s own
numbers — the same discipline `app/mistakes.py`/`app/successes.py`
already established, filed automatically the instant a run completes
(`app/nexus.py`'s `tick()`, right alongside the existing "Simulation
complete" news item).

**Company Review — five real reviewers, each a real occupation**
(`generate_strategy_review`):

| Role | Agent | Real signal checked |
|---|---|---|
| Quant | Vector (Chief Quantitative Strategist) | sample size ≥ `QUANT_MIN_SAMPLE_SIZE` (3), avg win rate ≥ 50%, avg Sharpe ≥ 1.0 |
| Risk Specialist | Guardian (Portfolio Protection) | avg max drawdown ≤ `RISK_MAX_AVG_DRAWDOWN` (20%) |
| Technical Analyst | Echo (Technical Analyst) | ≥ 2 distinct Testing Environments actually exercised |
| Fundamental Analyst | Nova (Research Analyst, authored the seeded "Value Fundamentals" strategy) | ≥ 1 completed `ResearchItem` in the strategy's own category |
| Devil's Advocate | rotates through `STRATEGY_DEVILS_ADVOCATES` (scribe/coach/cio/sage — distinct from the four fixed seats above) | worst single run's max drawdown > `DEVILS_ADVOCATE_MAX_SINGLE_DRAWDOWN` (25%), or any run with a negative `expected_value_pct` |

Every verdict cites the real number that produced it — the same
threshold-citation discipline `app/devils_advocate.py` already
established for individual trades, applied here to a strategy's own
aggregated history. `overall_verdict` is `fail` if any reviewer fails,
`concern` if any reviewer has a concern, `pass` only if all five pass.

**Automation Mode governs the final CEO call** (`app/nexus.py`'s
`tick()`), reusing `_apply_operating_mode`'s exact convention: Learning
Mode always waits for a real manual `POST /api/sandbox/decide`;
Executive Mode auto-resolves every pending `StrategyReview` using its
own real `overall_verdict` (`pass` → approve, else reject); Assisted
Mode only auto-resolves the unambiguous `pass`/`fail` cases, leaving a
genuine `concern` verdict for real CEO judgment — tagged
`resolved_by="auto"` for honest provenance either way, the identical
convention trade-decision auto-resolution already established.

**New `SANDBOX` Command Center tab** (`SandboxPanel.tsx`, inserted
after `TALENT`): per-strategy pipeline visualization with real stage
history, a scenario-picker backtest queue form (including the Custom
scenario's two real bias inputs), a per-run metrics table (Return/Win
Rate/EV/Profit Factor/Max Drawdown/Sharpe/Risk-Reward/Trades), the
auto-generated Strategy Reports, and the Approval Process section
(stage-appropriate CEO action buttons plus any filed review's five
verdicts with Approve/Reject when a decision is still pending).

**Save/load.** `strategy_reports`/`strategy_reviews` join `strategies`/
`backtest_sessions`/`simulation_results` in the `"company"` core module
— returned in full by `GET /api/load`, the same as every other
company-scoped list. `default_state()` seeds both as empty lists, so an
older save migrates cleanly through `load_modules()`'s existing
deep-merge-onto-`default_state()` recovery path with no new migration
code required — confirmed live: restarting the backend against a
pre-Feature-45 dev save produced no migration warning and the existing
seeded strategies picked up real `stage`/`stageHistory` on the very
next tick.

**Verification.** Backend: `test_sandbox.py` (29 new tests — stage
gating never skips forward and never moves backward, every reviewer's
real threshold in both directions, the devil's-advocate rotation stays
distinct within one review, report generation cites real numbers) + the
full suite (552/552) + mypy/ruff clean. Frontend: `tsc -b`/eslint/build
clean; a new `sandbox.spec.ts` (2 Playwright tests against the live
stack — confirming every strategy carries real `stage`/`stageHistory`/
`allocatedCapital`, and that the SANDBOX tab renders the pipeline and
successfully queues a real scenario backtest) both passed;
`commandCenter.spec.ts`'s tab-count test updated to 26 tabs.

### Professional Academy — Feature 49 Revision (employees are the students, the CEO manages)

**Supersedes the "Foundational Mentor Program (Phase 3)" section
immediately below** in one specific way — everything below about
content, lessons, roadmap, and the attribution boundary is still
accurate; what changed is *who does the lessons*. This revision was an
explicit CEO request: TradeTown is a company management sim (the player
is the CEO, the employees are the staff), so requiring the CEO to
personally click through every lesson/quiz to make company progress
happen was the wrong shape.

**The pivot.** Real employee agents — `STUDENT_AGENT_IDS` in
`app/foundational_mentors.py` (scout, atlas, echo, nova, scribe,
sentinel, pulse, guardian; the same roster `academy_research.py`'s own
company-wide Academy project rotation already uses, minus Coach, who is
explicitly the teacher/monitor in this revision's own brief) — now
auto-progress through the company's one active mentor track every real
backend tick (`tick_employee_progress()`, wired into `nexus.py`'s
`tick()` right after the existing Academy-project tick, Rest Mode-gated
the same way). This is the same honest "progress climbs each tick, no
LLM content generation" convention `academy_research.py`'s
`AcademyProject` already established, applied to a second real system.

**The honest signal behind an auto-graded quiz.** There is no player
picking an option for an employee's own quiz attempt — inventing a
fabricated "the employee selected option C" would be dishonest. Instead
`_agent_aptitude()` computes each employee's real average
`DisciplineReview` score across every review they attended (the same
kind of real per-agent signal `mentor.py`'s ThinkingProfile already
treats as a legitimate aptitude proxy), clamped between
`MIN_QUIZ_PASS_PROBABILITY` (0.35) and `MAX_QUIZ_PASS_PROBABILITY`
(0.90) so no employee is deterministically guaranteed or barred. A
failed quiz doesn't erase all study progress — it lands the employee at
`FAILURE_STUDY_RESET_PCT` (50%), an honest middle ground between "no
penalty" and "start the lesson over."

**Graduation Queue — a real CEO gate, not automatic.** Completing every
lesson (correctly quizzed) moves an employee's `graduationStatus` to
`"pending_approval"`, not immediately `"graduated"` — matching the
brief's own "CEO Responsibilities: Approve Graduation" and "Graduation
Queue" dashboard section. Only `POST /api/foundational-mentors/approve-
graduation` (a real CEO action) advances it to `"graduated"`. Once every
student has an approved graduation on the active mentor, the company as
a whole graduates that track (`companyGraduatedSimDay`) and the next
roadmap entry unlocks — "mastery before progression."

**The Academy Dashboard is a pure client-side derivation — zero new
backend broadcast fields.** `computeAcademyDashboard()` in
`frontend/src/ui/components/CommandCenter/lib/derive.ts` computes
Currently Studying, Top Students, Needing Help, Graduation Queue,
Upcoming Graduations, Academy Statistics (avg quiz score, avg knowledge
points), Current Certifications, and Coach Recommendations entirely
from state already broadcast (`foundationalMentorState` +
`agentKnowledge`) — the same "frontend-only feature" pattern Feature
47's Knowledge Base (`computeKnowledgeBase`) already established, chosen
deliberately over adding a parallel backend-computed dashboard schema.
Clicking an employee in any list opens their real Employee Academy
Report (mentor, current lesson, completion %, quiz average, Discipline/
Knowledge scores, certifications).

**Coach Recommendations are real, not the brief's full list.** Only
"Repeat Lesson" and "One-on-One Coaching" are computed, both driven by
the real `consecutiveQuizFailures` counter (escalating past
`COACH_ESCALATION_THRESHOLD` = 3 consecutive misses). The brief's other
recommendation types — Extra Reading, Extra Backtesting, Reflection
Session, Research Assignment, Paper Trading Practice — have no real
backing signal or assignment plumbing yet and are not fabricated.

**CEO Learning Mode — entirely optional, never required.** A new
`Settings.ceoAcademyLearningMode` toggle (default off) reveals a
separate "Your Personal Learning" panel where the CEO may voluntarily
take the exact same lessons personally. This writes to
`FoundationalMentorState.ceoProgress` — an entirely separate bucket from
real employee progress, never gating or required for company
advancement. The pre-revision CEO-facing view/quiz endpoints were
renamed to `/api/foundational-mentors/ceo/view` and `.../ceo/quiz` to
make this separation explicit at the API layer too.

**New company-wide CEO controls**, unchanged in spirit from Phase 3 but
now operating on the whole cohort at once rather than a single shared
record: pause/resume the active track, skip straight to the next
roadmap entry (every employee's progress preserved, not discarded), and
repeat a graduated track (resets every employee's progress on it).

**Curriculum change**: TJR's lesson set expanded from 6 to 8 lessons —
added "Liquidity and Market Structure" and "Risk Management
Fundamentals" — to cover the revision's wider TJR focus-area list
(Trading Psychology, Discipline, Daily Routine, Liquidity, Market
Structure, Patience, Risk Management, Journaling, Trade Planning, High
Quality Trade Selection).

**Explicit scope cuts, checked against the revision brief and NOT
built** (see `foundational_mentors.py`'s own module docstring for the
full reasoning on each; CEO custom-mentor-authoring UI / "Add Custom
Courses" / "Add New Mentors" was cut here but has since been built for
real — see the Mentor Lab section below): per-employee assignment of individual
books/videos/PDFs/research papers/backtesting/paper-trading (the one
real assignment mechanic that exists — bookmarked external resources —
stays company-wide per mentor track, unchanged from Phase 3); the
brief's full "Mentor Validation" pipeline (every concept Discussed →
Backtested → Paper Traded → Sandbox Tested → Quant Reviewed → Risk
Reviewed → Devil's Advocate Reviewed → Founder Council Reviewed →
becomes Company Knowledge/Operating System/Constitution/Playbooks) —
this would mean building an entirely new cross-cutting approval-
workflow engine touching six-plus existing systems, and graduation
stays gated on the real lessons-plus-quiz signal only, the same honesty
boundary `sandbox.py`'s own docstring already documents (no mechanism
exists anywhere in this codebase to attribute a validated "concept" to
a specific later trade); "Quant Approval" as a literal second
graduation gate; CEO Daily Settings additions from the revision brief
(Trading Sessions, Allowed Strategies — `RiskLimits` doesn't have these
fields, a real separate follow-up to Feature 49 Phase 1); post-halt
automatic activity redirection (employees demonstrably switching to
study/research/backtest/journal once the Daily Trading Objective halts
trading — a real behavioral change to `schedule.py`/`nexus.py`'s task-
assignment logic, large and orthogonal to this module); "growth"
metrics as deltas over time (no snapshot-history mechanism exists — the
dashboard shows real current aggregate values instead, explicitly
relabeled); TradeTown's own retired Founders/Coach/Quant becoming
Foundational Mentors themselves (explicitly framed in the brief as a
"long term goal").

**Verified**: backend — `test_foundational_mentors.py` rewritten (27
tests covering default-state seeding, per-employee tick progression
including the Rest-Mode/no-active-content no-ops, high- and low-
aptitude quiz outcome distributions, the full Graduation Queue →
Approve → company-wide advancement path, all 4 company-wide CEO
controls, and the CEO's separate personal-learning bucket) + the full
suite (648/648) + mypy/ruff clean. Frontend: `tsc -b`/eslint/build
clean; `MentorLibraryPanel.tsx` rebuilt as the dashboard + Employee
Report modal + CEO Learning Mode toggle; `mentorLibrary.spec.ts`
rewritten (2 Playwright tests against the live stack — confirming the
backend seeds real per-employee progress restricted to
`STUDENT_AGENT_IDS` only, and that the MENTORLIB tab renders the
dashboard with CEO Learning Mode initially hidden and revealed on
toggle, including a full personal-quiz round-trip through
`POST /api/foundational-mentors/ceo/quiz`).

### Mentor Lab — Command Center UI Revision (real CEO custom-mentor authoring)

A follow-up "Command Center UI Revision" brief asked for the Academy /
Training / Mentor Lab tabs to become three distinct dashboards. Two of
those three names collide with pre-existing, unrelated real systems in
this codebase:

- **"ACADEMY"** is already the v0.6.2 Trading Academy tab
  (`EducationPanel` — the player's own lesson/quiz curriculum).
- **"TRAINING"** is already the Signal Calibration mini-game
  (`CalibrationPanel`), whose real content (pattern-recognition drills)
  overlaps with the real backtesting/paper-trading pipeline already on
  the SANDBOX tab.

Rather than silently reusing those names for a third, different meaning,
the existing **MENTORLIB** tab (built in the Revision above) keeps its
name — it already is the employees'-progress dashboard the brief
describes — and only one new tab, **MENTORLAB**, was added. TRAINING was
left untouched entirely; this is a deliberate, documented scope decision,
not an oversight.

**What's real and built** — Mentor Lab is a mentor-centric browsing and
authoring surface, distinct from MENTORLIB's employee-centric management
view:

- `FoundationalMentorId` is loosened from a fixed six-value `Literal` to
  a plain `str` (`schemas.py`, `types.ts`), since custom mentor/lesson
  IDs are CEO-chosen at runtime, not a closed enum.
- `add_custom_mentor(state, *, name, track_label, focus_areas)` appends a
  real new mentor to `state.mentors` and to the end of a newly-persisted
  `FoundationalMentorState.roadmap_order` (previously the roadmap
  sequence was a hardcoded module constant; it's now real runtime state
  so CEO-added mentors actually participate in the automatic sequential
  unlock, capped at `MAX_CUSTOM_MENTORS = 20`).
- `add_custom_lesson(state, mentor_id, *, title, simple_explanation,
  deeper_explanation, quiz_question, quiz_options, correct_index)` adds a
  real lesson to that mentor's curriculum (capped at
  `MAX_LESSONS_PER_MENTOR = 30`). Built-in lessons keep their correct
  answer in a module-level Python constant that's never serialized to
  the client; a CEO-authored lesson has no such constant, so its answer
  is stored for real in a new `FoundationalMentorState.
  custom_lesson_answers: dict[str, int]` field — `grade_ceo_lesson_quiz`
  falls back to it when the built-in lookup misses.
- `set_active_mentor(state, mentor_id)` is a real CEO override: jumps
  company-wide focus straight to any mentor with lesson content,
  built-in or custom, pausing (not discarding) whatever was active —
  the same mechanism `skip_to_next_mentor` already used, just addressable
  by ID instead of "next in sequence."
- Three new endpoints back these: `POST /add-mentor`, `POST
  /add-lesson`, `POST /set-active`.
- `MentorLabPanel.tsx`: a Mentor Roadmap list (with "+ Add New Mentor"),
  a selected-mentor detail panel (focus areas, content-attribution note,
  lesson count, company graduation day, "Make Active Track," "+ Add
  Lesson"), a Curriculum list, a "Company Concepts Learned" card
  (`computeCompanyConceptsLearned` — a real, derivable distinct-lesson
  count), and a Mentor Comparison table (`computeMentorComparison`) — all
  three new `lib/derive.ts` computations follow the same "frontend-only
  feature" pattern as Feature 47's Knowledge Base and the Academy
  Dashboard above: computed client-side from data already broadcast, no
  new WS payload fields needed beyond `roadmapOrder`/`customLessonAnswers`.

**Deliberately not shown**: the brief's "Concepts Validated" / "Concepts
Rejected" counters. No real cross-system validation pipeline (Discussed →
Backtested → Paper Traded → Sandbox Tested → Quant Reviewed → Risk
Reviewed → Devil's Advocate Reviewed → Founder Council Reviewed) exists
in this codebase to back those numbers honestly — this is the same gap
the Revision section above already declined to build for the same
reason. The panel states this explicitly rather than fabricating either
number.

**Verified**: backend — `test_foundational_mentors.py` gains 12 new
tests (`TestAddCustomMentor`, `TestAddCustomLesson`,
`TestSetActiveMentor` — 39 tests in the file, 660/660 full suite) +
mypy/ruff clean. Frontend: `tsc -b`/eslint/build clean; new
`mentorLab.spec.ts` (live-stack Playwright test: add a real mentor, add
a real lesson to it, make it the active track, then restore TJR as
active so the shared dev backend's state doesn't leak into other tests);
`commandCenter.spec.ts`'s tab-count regression updated (29 → 30 tabs,
`MENTORLAB` added to the tab list).

### Certification Management — full CEO controls, a quality-of-life fix

**The bug this fixes.** The original "Revoke Graduation" design (below,
superseded) derived a certification purely from
`FoundationalMentorProgress.graduation_status == "graduated"` — there
was no independent, permanent certification record. That created a real
reachability bug: the Current Certifications list's only path to a
Revoke action was through the CEO clicking that employee's name inside
one of the *active* mentor track's own summary lists (Currently
Studying/Top Students/Needing Help/Graduation Queue) — see
`computeAcademyDashboard` (frontend `lib/derive.ts`), which derives
those lists from `activeSummaries` only. Once the company progressed
past a track, any employee whose certification lived on that
now-inactive track could never appear in those lists again, and so
their Revoke button became permanently unreachable — "once an agent
appears under Current Certifications there is no way to revoke it."

**The fix: `CertificationRecord`, a real independent registry**
(`schemas.py`, `FoundationalMentorState.certifications`) — one permanent
record per (agent, mentor) pair that has ever been earned, keyed
`cert-{agentId}-{mentorId}` so every certification is always directly
addressable regardless of which track is currently active. Unlike
`FoundationalMentorProgress` (which a revoke genuinely resets, so the
employee can really repeat the track), a `CertificationRecord` is never
deleted — only its `status` changes, with every transition permanently
appended to `history` (`CertificationHistoryEntry`), so "View
Certification History" always has the complete real timeline.

**A real three-state lifecycle** (`CertificationStatus`): **active**
(currently qualified), **suspended** (temporarily disabled, reversible
— Downgrade/Promote), **revoked** (permanently pulled until re-earned).
`"expired"` is deliberately not built: it would need a real
passage-of-time renewal/decay signal, and nothing in this codebase
tracks certification age or renewal — **postponed to v1.0**
(see `docs/ROADMAP.md`), not fabricated here to fill out a fourth
status.

**Six real actions, all in `app/foundational_mentors.py`'s
"Certification Management" section:**

- **View Certification / View Certification History** — no new mutation
  needed; both read directly from the record already broadcast in
  `FoundationalMentorState.certifications`, the same "already-broadcast
  state" pattern the rest of this feature uses.
- **`downgrade_certification`** — Active → Suspended. Requires a real
  reason (this is a real personnel action). Deliberately does NOT touch
  `FoundationalMentorProgress` — the employee's raw lesson/quiz record
  stays exactly as it was, so Promote can cleanly reinstate without
  re-earning anything.
- **`promote_certification`** — Suspended → Active, the mirror image;
  only "eligible" (offered at all) while suspended.
- **`revoke_certification`** — Active or Suspended → Revoked. Requires a
  real reason. Resets the employee's `FoundationalMentorProgress` to
  fresh (the exact same reset `repeat_mentor_company_wide` already uses
  per student) so they genuinely return to the Mentor Track and can
  re-earn it — approving a later graduation on the same (agent, mentor)
  pair reuses the *same* `CertificationRecord`, flipping it back to
  `"active"` and appending a fresh `"earned"` entry, rather than
  creating a second record — "they should be able to earn the
  certification again later" without losing the first earning's history.
- **`reset_certification_progress`** — only offered on an already-
  revoked certification: wipes any renewed re-training headway made
  *since* the revoke (a genuinely separate admin action from the revoke
  itself, which already reset progress once).

**Deliberately NOT built: "Downgrade"/"Promote" to a performance tier**
(Bronze/Silver/Gold or similar). No tiered-certification concept exists
anywhere in this codebase — Foundational Mentor graduation is a real
pass/fail signal (every lesson correctly quizzed), never a graded scale
— so Downgrade/Promote are real *standing* transitions (above) instead
of an invented tier system with no real signal behind it.

**Executive Log.** No generic "Executive Log" exists in this codebase;
its real analog is the Newspaper's `NewsItem(category="company")` feed
(`Newspaper.tsx`'s "Company News" section) — every prior `NewsItem` was
generated inside `nexus.py`'s own tick loop, so this is the first
direct-from-REST append (`GameState.revoke_academy_certification` in
`state.py`). One real headline per revoke, matching the requested
format exactly: `"Day {simDay} — {AgentName}'s {trackLabel}
Certification revoked by CEO. Reason: {reason}"`. Capped the same lazy
way every other news item is — `nexus.py`'s `_trim_news()` runs once per
tick over the full accumulated list, so this entry gets folded into
that same `MAX_NEWS_PER_CATEGORY` (8) cap on the very next tick, no
duplicate trimming logic needed in `state.py`.

**Frontend** (`MentorLibraryPanel.tsx`): a new `CurrentCertifications`
component reads directly from `foundationalMentorState.certifications`
(the real, always-addressable source) instead of the old derived-from-
progress list, split into two sections — **Current Certifications**
(active + suspended, with View/History, Downgrade-or-Promote depending
on the row's own status, and Revoke) and **Revoked Certifications —
awaiting re-earn** (revoked records, with View/History and Reset
Progress). A single shared `CertificationActionDialog` renders every
action's confirmation modal; Revoke's copy matches the brief's request
exactly ("Are you sure you want to revoke {Agent}'s {Track}
Certification?" / "This will remove the active certification but
preserve all historical records." / Cancel / Revoke Certification), with
a required reason field — Downgrade reuses the same shell with lower-
severity copy and its own required reason, Promote takes an optional
note, Reset Progress needs no reason at all. The old ad hoc "Revoke
Graduation" button and its Certifications sub-section inside the per-
employee Academy Report modal are removed (superseded); that modal now
shows certifications read-only, pointing to the new dedicated section
for actions. `computeAcademyDashboard`'s derived `certifications` field
(`lib/derive.ts`) is removed entirely — no longer needed now that a real
registry exists, and keeping it would have meant two sources of truth
that could drift.

**Verified**: `test_foundational_mentors.py`'s `TestCertificationManagement`
(replacing the old `TestRevokeGraduation`) — 20 tests covering revoke
(status reversion, real progress reset, the real Coach note's content
including the CEO's own reason text, non-interference with the track's
company-wide status and other employees' progress, history preservation
instead of deletion, the required-reason and double-revoke error paths),
downgrade/promote (suspend/reinstate, progress untouched, eligibility
gates), reset progress (revoked-only gate, real wipe), and re-earning a
revoked certification (same record, appended history, never a second
record) — plus a new `TestApproveGraduation` test confirming
`approve_graduation` itself creates the permanent `CertificationRecord`
with a real "earned" history entry — 826/826 full backend suite,
mypy/ruff clean. Frontend: `tsc -b`/`eslint`/`vite build` clean;
`mentorLibrary.spec.ts`'s honest-empty-state test updated to check the
new real `foundationalMentorState.certifications` signal (rather than a
progress-derived one) and assert no Revoke/Downgrade buttons render
before any certification exists — 3/3 passing against the live stack.

### Executive Intelligence Network — Feature 50

The brief's own instruction: "Do NOT create duplicate systems. Refactor
and upgrade the current implementation so all existing functionality is
preserved while expanding it." Researched first, and this turned out to
be achievable almost entirely as a synthesis layer — every one of the
brief's eight named departments (Research, Quant, Risk, Simulation,
Decision Intelligence, Coach, Founders, Devil's Advocate) already has a
real, checkable system behind it in this codebase:

| Department | Real backing system |
|---|---|
| Research | `TradeProposal.research_summary` (real `ResearchItem` confidence, already generated at proposal time) |
| Quant | `DecisionConfidence`'s real "technical"/"research" `ConfidenceFactor` readings (`app/confidence.py`) |
| Risk | `TradeProposal.risk_summary` (Sentinel/Guardian, `app/risk_engine.py`) plus the real "risk" `AnalystVote` |
| Simulation | The What-If Simulation Lab's real worst-case read, already carried on a `ChallengeReport` as `worst_case_scenario` when one exists (`app/whatif.py` via `app/devils_advocate.py`) |
| Decision Intelligence | `DecisionConfidence` itself (score/tier/summary) — this department's opinion IS the Decision Confidence Engine's own real read |
| Coach | The most recent real `CoachReport`'s strengths/recommendations (`app/coach.py`) |
| Founders | The real Library of Mistakes titles already attached to a `ChallengeReport` as `historical_comparisons` |
| Devil's Advocate | The `ChallengeReport` itself when one exists (CEO-requested, not automatic) |

**What's genuinely new** (`app/executive_intelligence.py`): the
synthesis layer itself, filling exactly the gap the "Multiple Opinions"
Development Rules addendum already identified — the Brain Room's "combine
every perspective" claim wasn't true yet. `generate_department_opinions()`
produces a real `DepartmentOpinion` per department (role, stance, real
summary text, real confidence %), reading the systems above rather than
recomputing anything. `compute_executive_recommendation()` is a real,
rule-based (never fabricated) aggregate over those opinions — checked in
priority order (an active major Devil's Advocate/Risk concern always
outranks a merely-lukewarm average) — producing one of six real actions
(`trade_normally`, `reduce_risk`, `wait`, `research_more`,
`pause_trading`, `focus_on_simulation`) with real supporting/opposing
department lists. `GET /api/executive/intelligence?proposalId=...`
exposes it, computed fresh on every request (same "no permanence
requirement, every input already lives somewhere permanent" reasoning as
`app/whatif.py` — no game-state lock needed, nothing here mutates the
save).

**Explicit phasing, not silent scope-cutting** — this is easily the
largest single brief given this session; it was built the same way
Feature 49 was (Phases 1/2/3 + a Revision), not crammed into one pass:

- **Part 1 (done)**: the department-opinion synthesis layer above — the
  foundational piece everything else builds on.
- **Part 2/3 (done — see the section below)**: Decision Grade (A+–F),
  the permanent Executive Meeting Log, per-department weekly
  Self-Evaluation, and the Company Health formula redesign.
- **Explicit cut, not deferred**: the brief's "Session Changes / Market
  Open / Market Close" simulation environments. No session-boundary
  model exists anywhere in this codebase's continuous sim clock to back
  them honestly, and none is being invented.

**Verified**: `test_executive_intelligence.py` — 20 new tests (every
department's real-field reuse, every honest "not yet" fallback, and the
recommendation engine's priority-ordered rules) — 680/680 full suite,
mypy/ruff clean.

**Frontend (Part 1's Executive Recommendation Panel)**: built as a
proposal-scoped collapsible section inside the existing Executive
Voting popup (`ExecutiveVoting.tsx`), the same slot pattern as the
What-If Simulation Lab beside it — `ExecutiveRecommendation` is
computed fresh per-proposal (never persisted), exactly like
`WhatIfSimulation`, so a standalone company-wide dashboard tab isn't
the right shape for it yet (there's no history to show). Opening
"EXECUTIVE INTELLIGENCE NETWORK" calls
`api.getExecutiveIntelligence(proposalId)` and renders the recommended
action, network confidence, supporting/opposing department lists, and
each of the 8 department opinions with its own real stance and
summary. New TS mirrors (`ExecutiveRecommendation`, `DepartmentOpinion`,
`ExecutiveAction`, `ExecutiveStance`, `ExecutiveDepartmentRole`) in
`types.ts`; `executiveActionTone()`/`executiveStanceTone()` tone
helpers in `derive.ts`, following the same pattern as
`confidenceTierTone()`. Verified: `tsc --noEmit` and `eslint` clean,
`npm run build` clean, and a new Playwright test in
`executiveVoting.spec.ts` that boosts a real research item to
threshold, opens its real Executive Voting popup, opens the network
panel, and asserts all 8 department labels plus the recommendation and
supporting/opposing lists render from the real live endpoint — passing
against the running dev stack. The 30-tab Command Center regression and
the rest of `executiveVoting.spec.ts` were re-run afterward and remain
green (one pre-existing, unrelated flake in that suite — a real trade
proposal intercepting a click mid-test in the shared long-running dev
backend — was confirmed present even with this change's diff stashed
out, i.e. not a regression).

### Executive Intelligence Network Part 2/3 — Decision Grade, Executive Meeting Log, Weekly Self-Evaluation, Company Health redesign

Three new real, permanent systems built directly on Part 1's synthesis
layer, plus one redesign of an existing system — none of them a second
opinion engine.

**Decision Grade (A+–F)** — `app/executive.py`'s `compute_decision_grade()`
grades the decision-making PROCESS at the moment `resolve_proposal()`
makes it, never the trade's own P&L (the same "process over outcome"
convention `app/discipline.py`'s Discipline Score already established,
so it's available immediately, not just once a trade closes). A real,
weighted composite — 50% the Decision Confidence Engine's own score,
25% the real multi-agent analyst agreement rate, 25% whether the trade
actually cleared the Trade Gatekeeper (100 if approved or never
reached — a WAIT — 40 if vetoed) — mapped onto a standard 12-step
academic letter scale. Attached directly to every `TradeDecision` going
forward (`decisionGrade`/`decisionGradeScore`, `null` on older records).

**Executive Meeting Log** — makes Part 1's previously ephemeral,
compute-on-open synthesis permanent. `app/executive_intelligence.py`'s
`generate_meeting_log_entry()` runs the exact same
`generate_department_opinions()`/`compute_executive_recommendation()`
pair Part 1 uses, then records one real `ExecutiveMeetingLogEntry` —
the department opinions, the recommendation, the CEO's actual choice,
whether the two agreed (`networkAgreed`), and the decision's own real
grade (read straight off the already-built `TradeDecision`, never
recomputed) — at every real `resolve_proposal()` call site: a genuine
CEO decision (`app/state.py`'s `submit_ceo_decision`), a Company
Operating Mode auto-resolution, and a stale-proposal expiry (both in
`app/nexus.py`). Capped at `MAX_MEETING_LOG_ENTRIES` (200), broadcast
live and archived in the `trade_history` save module (see `docs/API.md`).

**Weekly Self-Evaluation** — `generate_weekly_self_evaluations()`,
fired on the exact same weekly cadence as `wisdom.py`'s
`ReflectionSession` (`nexus.py`'s `WEEKLY_INTERVAL_DAYS`). One real
`DepartmentSelfEvaluation` per department per week, built entirely from
that department's own real `DepartmentOpinion` entries already logged
to the Meeting Log over the trailing 7 sim days — average confidence as
the score, real agree/concern counts driving honest strengths/
improvement-area text, and an explicit "no real decisions yet" neutral
default for a department with nothing on record that week. Capped at
`MAX_SELF_EVAL_HISTORY` (250), archived in `knowledge_archive`.

**Company Health redesign** (`app/company_health.py`) — ten new real
Executive-tier dimensions, additive alongside the eleven Operational
ones Feature 23 already established (never replacing them — this
codebase's own "no duplicate systems" convention bars replacing a real
working formula with one that can't actually improve on it, and
`overall`/`tier` stay byte-for-byte unchanged so every existing
consumer — Company Priorities, the Founders' retirement trigger, the
COMPANY tab — keeps working identically):

| Dimension | Real backing signal |
|---|---|
| Decision Quality | average real Decision Grade score across recent `TradeDecision`s |
| Executive Alignment | % of recent Meeting Log entries where `networkAgreed` is true |
| Risk Governance | real Gatekeeper approval rate (closed trades ÷ closed trades + rejections) — the same real signal `wisdom.py`'s `follow_principles` already reads, reused for a different question |
| Simulation Coverage | % of recent Meeting Log entries whose Simulation opinion wasn't an honest "not yet stress-tested" |
| Department Consensus | % of all recent Meeting Log opinions with an "agree" stance |
| Self-Evaluation Health | mean of the latest weekly Self-Evaluation score per department |
| Institutional Memory | the real `WisdomState.score`, reused directly |
| Innovation Velocity | average real Innovation Points, normalized against the real Legendary Innovator threshold |
| Talent Development | real Academy graduation rate (graduated ÷ possible across active mentor tracks × students) |
| Founder Oversight | real Founder Council session frequency, capped at 100 |

`executiveOverall`/`executiveTier` are this tier's own headline;
`combinedOverall`/`combinedTier` (an equal blend of `overall` and
`executiveOverall`) is the true redesigned headline number, and
`recommendations` now surfaces the weakest metric from each tier
(capped at 4 total) rather than just the Operational one.

**Note on the brief's exact ten dimension names**: the original
chat-only brief text wasn't preserved verbatim in this session's history
by the time Part 2/3 began. Rather than fabricate plausible-sounding
names that couldn't be checked against the real brief, these ten were
chosen as the most defensible honest real signals available — every one
backed by data this phase's own new systems produce (Decision Grade,
the Meeting Log, Self-Evaluation) or by a real existing system not yet
folded into Company Health (Wisdom, Innovation Points, the Academy, the
Founder Council).

**Frontend (built)**: `CompanyPanel.tsx`'s Company Health card gained a
second "Executive Health" card directly beneath it — `executiveOverall`/
`executiveTier` header, a Meter, all ten new dimension cells, and a
"Combined Overall" footer row for `combinedOverall`/`combinedTier`.
`DecisionsPanel.tsx` (the Decision Intelligence dashboard) gained a
"Decision Grade Distribution" card (grade counts as `StatusPill`s, shown
only once real decisions exist) and a Grade column on the decision
table. `RiskPanel.tsx` (the Risk dashboard) gained a fifth mini-card for
Risk Governance. `ExecutiveIntelPanel.tsx` (the Executive Intelligence
Network's own company-wide hub) gained a Weekly Self-Evaluation grid (one
card per department — score, Meter, summary, top strength/improvement
area) and an expandable Executive Meeting Log list (symbol, recommended
action, decision grade, CEO-agreed/diverged indicator; expanding an entry
shows the recommendation reason plus all 8 department opinions) —
integrating directly into the existing network rather than creating a
new standalone Simulation dashboard, since Simulation's own real
company-wide signal (stress-test coverage) already lives there beside
the other 7 departments' self-evaluations. Data layer: new fields
threaded through `types.ts`, `NexusManager.ts` (diff-and-emit plus
`loadFromSave`), `EventBus.ts`, `gameStore.ts`, and `socket.ts`; new
`decisionGradeTone()`/`computeDecisionGradeDistribution()`/
`recentMeetingLogEntries()`/`latestSelfEvaluationsByRole()` helpers in
`derive.ts`.

**Verified (backend)**: new tests in `test_executive.py` (`TestComputeDecisionGrade`,
7 tests), `test_executive_intelligence.py` (`TestGenerateMeetingLogEntry`/
`TestGenerateWeeklySelfEvaluations`, 9 tests), and `test_company_health.py`
(`TestExecutiveTier`, 11 tests) — 717/717 full suite (see the wisdom.py
bug-fix note below for the 717th), mypy/ruff clean. A direct
9-in-game-day `nexus.tick()` simulation run (not just unit tests)
confirmed the Meeting Log/Self-Evaluation cadences and Company Health's
new fields populate correctly with no exceptions, and a `save_modules`
split/assemble round-trip confirmed the new archive fields persist
correctly.

**Verified (frontend)**: `npx tsc -b --noEmit` (the correct invocation
for this repo's solution-style `tsconfig.json` — a bare `tsc --noEmit`
silently checks nothing), `npm run lint`, and `npm run build` all clean.
A new `tests/feature50Part2.spec.ts` (4 tests, same real-app approach as
`executiveVoting.spec.ts`) exercises all four surfaces above against the
live dev stack; the 30-tab `commandCenter.spec.ts` regression stayed
green.

**Incidental bug found and fixed while verifying this phase**
(unrelated to Feature 50's own scope): `app/wisdom.py`'s `_questions()`
scans the full shared `case_studies` list — populated by both
`mistakes.py`'s `record_case_studies` and `successes.py`'s (Feature 42)
`record_success_studies` — but its title lookup only covered
`mistakes.py`'s six categories. Whenever the most common real category
turned out to be one of `successes.py`'s three (e.g.
`disciplined_process`), it raised `KeyError`. Because `app/sim.py`'s
`run_sim_loop()` has no exception handling beyond `CancelledError`, and
`app.state.sim_task` holds a permanent reference to the task (so its
exception is never retrieved or logged), this silently froze the sim
clock — HTTP endpoints kept responding, but game time stopped advancing,
with zero log output. This is what was actually causing the severe
Playwright flakiness observed while first verifying this phase (not
ordinary real-popup-intercepts-click flakiness — the clock had genuinely
stopped for a long real-world stretch, confirmed via two `/api/load`
polls 15 seconds apart returning identical `time`). Fixed by merging
both modules' `CATEGORY_TITLES` into a `wisdom.py`-local
`_CATEGORY_TITLES`; reproduced directly against the real persisted save
file and added a regression test.

### Professional Day Trading Program — Foundational Mentor Program (Phase 3, original design — content/roadmap/attribution still accurate, see the Revision section above for who now does the lessons)

The third phase of Feature 49 — an expandable, CEO-facing library of
named trading-educator "tracks" (`app/foundational_mentors.py`), worked
through as a sequential lesson-and-quiz curriculum with a roadmap of
unlockable tracks.

**The content-attribution boundary this phase was built around.** The
brief names real, living public trading educators (TJR, Al Brooks,
Linda Raschke, Mark Douglas, Tom Hougaard, Mike Bellafiore). This
codebase has no HTTP client, no PDF/video parser, and no LLM call
anywhere (confirmed by grep across the whole backend, consistent with
the precedent in `app/education.py` and Feature 40's own docstring) —
so TradeTown cannot actually watch, read, or otherwise ingest any real
person's real published content. This was escalated to an explicit CEO
decision rather than assumed: given the choice between refusing to use
real names at all, or using real names as CEO-assigned track labels over
100% original TradeTown-authored content with an explicit in-product
disclaimer, the CEO chose the latter. Every `FoundationalMentorProfile`
carries a `contentNote` stating this directly — never a claimed
transcription, summary, or quote of that person's actual work.

**What's real vs. roadmap — the same "ship one real depth, document the
rest as an honest roadmap" pattern Features 47/48 already established.**
Only the **"tjr" track** ships real lesson content: 6 original lessons,
each tied to a real, checkable TradeTown mechanic —

| Lesson | Real TradeTown mechanic |
|---|---|
| Trading Psychology: Process Over Outcome | The Discipline Score (`discipline.py`) never reads trade P&L — it scores real process signals only |
| Building a Daily Routine | Honestly conceptual — `schedule.py`'s workday mechanic is availability, not ritual; points at the real Daily Trading Objectives review as the actionable analog |
| Patience as a Skill | The real `PATIENCE_TARGET_MINUTES` (240) Discipline factor — a real measured hold-duration-vs-target signal |
| High-Quality Trade Selection | The real Gatekeeper (`gatekeeper.py`) and Daily Trading Objectives (`risk_engine.py`) filters — most proposals getting blocked is the system working, not a bug |
| Trade Planning & Journaling | The real Trading Journal (`journal.py`) — including why its `screenshot` field is honestly a placeholder string, not a fabricated image |
| Emotional Control & Consistency | Honestly can't read literal emotion — points at Discipline tier stability and the Wisdom Score (`wisdom.py`) as the closest real, checkable analog |

The other **5 named tracks are real, ordered roadmap entries** — real
display name, real track label, real focus-area topics drawn straight
from the brief — but deliberately ship with zero lessons and
`status: "planned"` rather than five fabricated placeholder shells.
`_LESSON_SPECS_BY_MENTOR` in `foundational_mentors.py` is exactly where
a future track's real content gets added; nothing else needs to change
for it to come online.

**Graduation and unlock mechanics.** A track graduates when every one of
its lessons is in the agent's `completed_lesson_ids` — a real, checkable
signal. This deliberately does **not** reuse Research Sandbox backtest
stats: `sandbox.py`'s own docstring already documents that there's no
mechanism to attribute a real executed trade to a specific `Strategy`; a
"mentor track concept" is one level further removed than that, so
reusing Sandbox stats would just be a second, worse version of the same
non-attribution problem. Graduating a track flips the next roadmap entry
from `"planned"` to `"active"` — a real mechanical unlock, honest that
the newly-unlocked track still has no lessons until its own content is
authored.

**CEO manual controls**, modeled on `black_box.py`'s pause/resume
router pattern: pause/resume an active/paused track, skip straight to
the next roadmap entry (progress preserved, not discarded), and repeat a
graduated track (resets its progress). Plus a bookmark-only "External
Resources — CEO Reading List": a CEO-provided title/URL/type TradeTown
stores and displays, but never fetches, parses, or grades — the same
"bookmark, never ingest" boundary the whole module is built around.

**Explicit scope cuts, checked against the brief and not built**: no
CEO custom-mentor-authoring UI (the data model is expandable — add an
id, roadmap entry, and lesson tuple — but there's no in-product
authoring form; a repo-side content contribution is the real workflow
for now); no "concepts adopted/rejected" or "statistical success"
mentor rating (no real signal in this codebase could honestly measure
whether an agent "adopted" a mentor's concept in a later trade).

**Verified**: backend — new `test_foundational_mentors.py` (22 tests
covering default-state seeding, lesson viewing, quiz grading and
graduation-triggered unlock, all 4 CEO controls, and resource
bookmarking) + the full suite (642/642) + mypy/ruff clean. Frontend:
`tsc -b`/eslint/build clean; new `MentorLibraryPanel.tsx` (a new
"MENTORLIB" Command Center tab, distinct from the pre-existing
"MENTOR"/Sage Socratic-advisor tab); `commandCenter.spec.ts`'s tab-count
test updated to 29 tabs; new `mentorLibrary.spec.ts` (2 Playwright tests
against the live stack — confirming the backend seeds all 6 tracks in
roadmap order with only tjr active, and that the MENTORLIB tab renders
the disclaimer and a real quiz round-trips through
`POST /api/foundational-mentors/quiz`).

### Professional Day Trading Program — Liquidity/Market Structure Curriculum (Phase 2)

The second phase of Feature 49 (see Phase 1 below for the shared
research this whole feature was scoped from). The brief asked for a
"complete curriculum on liquidity": buy-side/sell-side liquidity, swing
highs/lows, equal highs/lows, stop clusters, resting/engineered
liquidity, liquidity sweeps/grabs, inducement, market structure shifts,
displacement, premium/discount pricing, order flow.

**Extends the existing Trading Education curriculum, doesn't build a
new one.** `app/education.py` (v0.6.2 Phase 9) already has a real,
ordered 10-lesson progression (candlesticks → ... → why NO TRADE can be
correct), a real `EducationTopic` Literal, real server-side quiz
grading, and a real `EducationPanel.tsx` UI. This phase adds 8 more
`_LessonSpec` entries (orders 11-18) continuing the exact same real
progression, rather than inventing a second curriculum system.

**The honesty check that shaped every lesson**: `app/market_data.py`'s
`Candle` is a single aggregate OHLC bar with one `volume` float per
period, generated independently of that bar's own price move — there is
no order-book, no bid/ask spread, and no trade-by-trade tape anywhere in
this codebase. That rules out ever claiming to *detect* a real swing
high, equal high, sweep, or inducement — this module teaches the
concepts, it does not run detectors that don't exist.

**Real analogs, named explicitly where one exists**:

| Lesson | Real TradeTown analog |
|---|---|
| `liquidity_sweeps` | The What-If Simulation Lab's real "Liquidity Sweep" scenario (`app/whatif.py`'s `_SCENARIO_PARAMS`) — a real hypothetical move scaled off the symbol's own measured volatility, already honestly labeled a *scenario*, never a claim of detection |
| `structure_shifts` | The Scanner's real `breakout` alert (`app/scanner.py`'s `_classify`), which only fires when a large price move is confirmed by a real volume spike in the same tick — the closest real signal this codebase has to genuine displacement |
| `swing_structure` | Builds directly on the pre-existing Trends vs. Ranges lesson's own real trend read |
| `premium_discount` | Builds directly on the pre-existing Support and Resistance lesson's own real range concept, and the real market regime classification (`app/market_environment.py`) |

**Honestly disclaimed, where no real analog exists**: `liquidity_basics`,
`equal_highs_lows`, and `inducement` each say directly, in their own
`visual_example_note`, that TradeTown has no order-book/participant-
positioning data to confirm the concept — teaching material, not a
claimed mechanic. The closing lesson, `order_flow_intro`, makes this the
explicit theme of the whole module: every other lesson is a way of
*inferring* likely order flow from price action alone, because the real
order-by-order data isn't available here — a legitimate, widely-used
real trading approach, but one worth being honest about the difference
from actually seeing the flow.

**Zero new persistence, zero new endpoints.** The existing
`GET /api/education/lessons`, `POST /api/education/view`, and
`POST /api/education/quiz` already handle any lesson id in the real
curriculum; `EducationProgress`'s `viewed_lesson_ids`/
`completed_lesson_ids` already track by id with no schema change needed.

**Verified**: backend — `test_education.py`'s topic-count test updated
to 18 lessons/orders 1-18, plus a new test confirming all 8 Liquidity
module ids are present and every one of the 18 ids is unique + the full
suite (621/621) + mypy/ruff clean. Frontend: `tsc -b`/eslint/build
clean (the frontend's own `EducationTopic` literal union, previously a
second hand-copied 10-member list, was extended to match); the existing
`commandCenter.spec.ts` Trading Academy test extended to assert the new
module's first (`11. What Is Liquidity?`) and last (`18. Order Flow`)
lessons render in the lesson list.

### Professional Day Trading Program — Daily Trading Objectives (Phase 1)

A large brief (Daily Trading Objectives, a "Trade Quality Checklist," a
full Liquidity/Market Structure curriculum, and a Foundational Mentor
Program with TJR plus a five-mentor roadmap). Researched first — a full
audit of `RiskLimits`, `app/gatekeeper.py`, `app/discipline.py`,
`app/academy.py`/`app/academy_research.py`, `app/market_data.py`,
`app/mentor.py`, and `app/sandbox.py` — before scoping. This is the
first, narrowest real slice: Daily Trading Objectives. The Liquidity
curriculum and Foundational Mentor Program are separate follow-up
phases of the same feature.

**The headline finding**: `RiskLimits.max_daily_loss_pct` already
existed (v0.6 brief) but was never enforced anywhere — confirmed by
grep before writing any code; its only readers were `nexus.py`'s
automation-mode scaling and `RiskPanel.tsx`'s display. This feature
makes it real, and adds two genuinely new limits alongside it:
`daily_profit_target_pct` and `max_trades_per_day`. All three read
`PaperTrade.opened_sim_minutes`/`closed_sim_minutes` (already real,
already persisted — `// 1440` is the sim day a trade opened/closed on),
so zero new data was needed.

**Enforcement reuses the existing Gatekeeper block path — deliberately
not a second mechanism.** `app/risk_engine.py`'s `evaluate_sentinel_risk`
gains three new early-return checks (daily max loss, daily profit
target, max trades/day), positioned right after the account-equity
check and before the pre-existing lifetime-drawdown check — a
day-scoped halt is the more common real event in normal play, so
checking it early keeps the returned warning's message relevant to
*today*. Each returns a critical, symbol-scoped `RiskWarning` exactly
the way the pre-existing drawdown check already does. That warning
becomes the new proposal's own `riskSummary`
(`app/executive.py`'s `generate_proposal`) and drives Sentinel's real
analyst vote to "wait" (`_risk_vote`) — which then fails
`app/gatekeeper.py`'s `_risk_manager_check` if the CEO tries to force a
trade through anyway. A trade cannot be forced past a reached daily
objective, by construction, the same way it can't be forced past any
other critical risk warning.

**Why no new "penalize forcing a trade after the halt" Discipline
factor was added**: once the Gatekeeper blocks a trade, no `PaperTrade`
— and therefore no `DisciplineReview` — is ever created for it. This is
the exact "structurally constant, nothing real to score" case
`app/discipline.py`'s own module docstring already documents for "did
it pass the Gatekeeper." Adding a factor for an event that structurally
cannot happen for the population `compute_discipline_score` ever sees
would be fake precision on an invariant, the same trap that docstring
already warns against.

**A real-time readout** (`DailyObjectiveStatus`,
`compute_daily_objective_status()` in `app/risk_engine.py`): today's
real trade count, today's real realized P&L (as a % of the portfolio's
real starting balance, the same fixed-reference convention
`total_pnl_pct` already uses), and which objective (if any) halted
trading — computed fresh every tick from `paper_portfolio.trade_history`,
the same "derived, recomputed rather than persisted" convention
`CompanyHealth`/`CompanyDNA` already use, so it can never drift from
what the Gatekeeper is actually enforcing.

**The first real CEO write path for `RiskLimits`.** Before this
feature, `RiskLimits` was purely display-only — no endpoint existed at
all (confirmed by grep across every router). `POST /api/risk-limits`
(new `app/routers/risk.py`, backed by `GameState.update_risk_limits()`)
lets the CEO configure daily profit target, daily max loss, max trades
per day, plus the two pre-existing per-trade limits (risk per trade,
max open positions) the brief also names — every field optional so one
call can change just one limit, each validated positive before merging
into the real `RiskLimits` object `evaluate_sentinel_risk` already
enforces every tick. Surfaced in `RiskPanel.tsx`'s new "Daily Trading
Objectives" section: a live status card (trades today, realized P&L
today, halt reason if any) plus an editable form that round-trips
through the real endpoint.

**Scope cuts, citing this codebase's own already-shipped precedent**
(the "Trade Quality Checklist" from the brief):

| Checklist item | Why cut |
|---|---|
| Market structure / liquidity analysis / higher-timeframe context | `app/gatekeeper.py`'s own module docstring already explicitly refuses these by name — no real data source |
| Risk/reward vs. company minimum, stop-loss placement | The paper broker has never placed stop-loss/take-profit exit orders — same cut `derive.ts`'s `preTradeChecklist` comment already documents |
| Session confirmation, economic news check | `app/sandbox.py`'s and `app/schemas.py`'s own "Earnings weeks / economic news" cuts already establish there is no economic-calendar or market-session-hours data source anywhere in this codebase |
| Strategy matches validated playbook | `app/sandbox.py`'s own docstring: no mechanism exists to attribute a real executed trade back to a specific `Strategy` object |

Four of the checklist's eleven items were already real and already
enforced before this feature touched anything (Quant confidence via
`MIN_CONFIDENCE`, Risk Department approval via
`_risk_manager_check`/`_risk_warning_check`, position sizing via
`recommended_quantity`/`_exposure_check`) — no duplicate "checklist"
object was built on top of the Gatekeeper's own real
`GatekeeperCheck` list.

**Verified**: backend — new `test_risk_engine.py` (20 tests: the two
new today-scoped helpers, all three new `evaluate_sentinel_risk`
checks including that yesterday's trades don't count against today's
objectives, `compute_daily_objective_status`'s halt-reason priority
order, plus baseline coverage of the pre-existing sentinel/guardian
checks this file had zero tests for before) + `test_state.py` gained a
`TestUpdateRiskLimits` class (4 tests: partial updates, all-five-at-once,
positive-value validation, empty-call rejection) + the full suite
(620/620) + mypy/ruff clean. Frontend: `tsc -b`/eslint/build clean; a
new `dailyObjectives.spec.ts` (2 Playwright tests against the live
stack — confirming the real backend fields, and a real CEO edit
round-tripping through `POST /api/risk-limits` and rendering back in
the RISK tab).

### Company Operating System

The brief asked for one place where "everything the company learns" is
visible, a system that "references company principles when giving
advice" (its own example: "This violates Company Principle 8"), and
"Continuous Improvement" fed by 8 named sources (Reflection Chamber,
Academy, Research Division, Innovation Lab/Black Box, Constitution,
Founder Lessons, Coach Reviews, Decision Replay Center). Checked first:
every one of those 8 sources already exists in this codebase and already
produces real, persisted records — so "Continuous Improvement" needed no
new backend data at all, only somewhere to actually see it aggregated.
Two honest, additive pieces:

**Knowledge Base — a pure, zero-new-backend-data aggregation**
(`frontend/src/ui/components/CommandCenter/lib/derive.ts`'s
`computeKnowledgeBase`). Joins six real, already-persisted learning
records — Library of Mistakes `CaseStudy`, Research Sandbox
`StrategyReport`, Constitution `ConstitutionCitation`, `CoachReport`'s
own `recommendations`, completed `AcademyProject`s, and Reflection
Chamber `ReflectionInsight`s — into one flat, chronological,
source-filterable timeline. The same "frontend-only feature" pattern
Feature 45's Consistency metric used: every field a direct read or
simple join, nothing generated. Rendered as the new `OPS` tab
(`KnowledgeBasePanel.tsx`, inserted after `CONSTITUTION`). Deliberately
distinct from the existing Knowledge Graph tab (`KNOWLEDGE`, Feature
25.5): that is a *relational* node/edge structure built over research
items, completed Academy projects, executive reviews, coach reports, and
Hall of Fame entries; this is a *flat timeline* over a different (and
partially non-overlapping) set of six sources — three of them
(Constitution, Reflection Chamber, Library of Mistakes) the graph never
touches at all. Naming them "KNOWLEDGE" and "OPS" rather than two tabs
both called "Knowledge ___" keeps them unambiguous in the tab bar.

**Real-Time Guidance — Constitution citations surfaced on the report
itself** (`app/constitution.py`'s new `articles_for_challenge()`). A
Devil's Advocate `ChallengeReport` (Feature 41) already computes four
real concern buckets before this feature ever runs:  `hiddenRisks`,
`weakAssumptions`, `missingEvidence`, `historicalComparisons`. Each
non-empty bucket now maps to the one real Article it most directly
speaks to (`hiddenRisks`→VII "Respect risk", `weakAssumptions`→III
"Challenge assumptions", `missingEvidence`→IV "Evidence over opinions",
`historicalComparisons`→VI "Every mistake must teach something"), stored
on the report's new `citedArticleIds` field and shown directly beneath
the report in the Executive Voting popup (`ExecutiveVoting.tsx`) —
literally realizing the brief's "This violates Company Principle 8" /
"conflicts with historical evidence" examples with 100% real,
already-computed data, no new detection logic. This is deliberately
**not** the same mechanism as `nexus.py`'s own separate "Live
Enforcement" citation log (Feature 46), which always cites Article III
on any filed `ChallengeReport` for a different, unconditional reason
(the act of filing a challenge itself is "challenging assumptions") and
writes to the permanent, global `ConstitutionState.citations` feed — the
two coexist without duplicating each other: one is a permanent company-
wide audit log, the other is guidance attached to the specific report
the CEO is looking at right now.

**Scope cut, explicitly**: no fabricated "AI recommendation engine," no
new detection heuristics — every citation traces to a field the report
already computed for itself before this feature touched it.

### Company DNA System

The brief asked for a "Company Identity" label, DNA that "changes
slowly" and is influenced by "every major event," DNA effects on
company behavior, a Founder-retirement "Legacy," and — the primary
honest scope cut — "no two companies should think exactly alike."
Checked first: Company DNA (Feature 43, `app/company_dna.py`) already
exists as five real behavioral traits (Risk Appetite, Patience,
Contrarian Tendency, Research Rigor, Collaboration Style), each read off
the company's own historical decision/trade record and recomputed fresh
from full history on nearly every tick. This feature adds two real,
additive pieces on top, deliberately without touching those five
formulas' own tested behavior or documented meaning — changing an
already-shipped, already-tested contract to build a new feature is
exactly the kind of risk this session's discipline avoids.

**Company Identity — a pure label, zero new data**
(`classify_identity()`). Reads the five existing trait scores in a
fixed priority order so exactly one label always applies: "Ultra
Conservative" (low risk appetite, high patience), "Research Driven"
(high research rigor), "Highly Disciplined" (high patience, moderate-
or-lower risk appetite), "Independent Thinker" (high contrarian
tendency), "Collaborative Culture" (high collaboration style),
"Aggressive Risk-Taker" (high risk appetite alone), or "Balanced
Operator" as the honest default. "Not Yet Established" until
`sampleSize` is real, the same "don't dress up thin data" convention
the five traits themselves already follow.

**Legacy — a small, permanent, capped delta layered on top of the fresh
score, never mixed into it.** The five traits' own formulas keep
computing a pure historical average exactly as before — `nudge_legacy()`
adds a second, independent signal on top: a persisted
`companyDnaLegacy: dict[trait_id, float]` (a new field on
`GameSaveState`, living in the `derived` save module alongside
`company_dna` itself), capped at `LEGACY_DELTA_CAP` (15 points per trait,
either direction) so no single event can swing a trait far, and no
accumulation of events can either. Four real, already-tracked company
events each contribute one small nudge, wired at their own real
`app/nexus.py` `tick()` hook points:

| Real event | Nudge |
|---|---|
| A Black Box breakthrough is ratified (`breakthrough_review.verdict == "approved"`) | Research Rigor +2.0 — real completed deep-research effort |
| An Academy project completes | Research Rigor +0.5 — real completed research effort, smaller since these are far more frequent |
| A `disciplined_process` success study is filed | Risk Appetite −1.0 — records real behavior that just happened, never a prediction |
| A `patient_execution` success study is filed | Patience +1.0 — same "real behavior, not a forecast" rule |
| The Founders' one-time "Legendary Status" retirement fires (Feature 39; `founder_state.retired` flips False→True) | Risk Appetite −3.0 **and** Research Rigor +3.0 at once — Keystone (Chief Risk Architect) and Compass (Chief Learning Architect) retire together, so both domains' legacy lands in the same event |

This is what makes DNA genuinely "change slowly": most events happening
before or after `compute_company_dna()`'s own call point in the same
tick take effect starting the next tick (a few sim-minutes' lag,
deliberately not worth restructuring `tick()`'s existing event order
to avoid), and every nudge is small and capped — no single event can
swing a trait's reading in one step the way a single fabricated
"personality shift" would.

**Explicit scope cut**: this codebase is single-tenant — `state.py`'s
and `save_modules.py`'s own module docstrings both say so directly ("one
company, one save slot"). "No two companies should think exactly alike"
and any recruitment/cross-generation/cross-company DNA comparison have
no real mechanism to attach to here and are not built.

**Verified**: backend — 30 tests in `test_company_dna.py` (`nudge_legacy`
accumulation/capping/immutability, `classify_identity`'s full priority
order, `compute_company_dna`'s new `legacy_deltas` parameter adding on
top of and clamping the base score) + the full suite (596/596) + mypy/
ruff clean. Frontend: `tsc -b`/eslint/build clean;
`execIntel.spec.ts` extended to assert `companyDna.identity` is a real
non-empty string in both the raw backend state and the rendered
EXECINTEL tab.

### Company Constitution

The brief asked for a permanent rulebook of Articles, "Live
Enforcement" (Coach quotes it, Founders teach it, Academy explains it,
Risk Department enforces it, Devil's Advocate references it), and a
CEO-driven amendment process. Checked first: no rule-of-conduct concept
existed anywhere in this codebase before this feature — the 8 example
Articles are genuinely new. The harder, more interesting design problem
was making "Live Enforcement" real rather than decorative: sprinkling
literal Article text into five unrelated systems' own generated content
would mean editing (and risking) `CoachReport`/`FounderLogEntry`/
`ChallengeReport`'s own tested generation logic in five different
places. Instead, `app/constitution.py`'s `ConstitutionCitation` is a
new, standalone, permanent log — `app/nexus.py`'s `tick()` appends to it
at six real event points this codebase already has, never touching any
of those five systems' own schemas or generation functions.

**8 real Articles, permanent from game start**
(`default_constitution()`): Protect Capital First, Research Before
Execution, Challenge Assumptions, Evidence Over Opinions, No Revenge
Trading, Every Mistake Must Teach Something, Respect Risk, Continuous
Learning Is Mandatory — the brief's own text, seeded verbatim as
Articles I-VIII.

**Articles IX-XIII — the Probability First Trading Philosophy.** Added
later as a documentation-driven, non-feature addition (see
`docs/DESIGN_BIBLE.md`'s "Probability First Trading Philosophy"
section, the fuller design document this codifies): We Trade
Probabilities, Not Predictions; A Single Trade Does Not Determine
Success; Risk Must Be Accepted Before Entry; Process Is More Important
Than Outcome; Statistics Become Meaningful Only Through Consistent
Execution Over A Large Sample Of Trades. Seeded verbatim in
`_ARTICLE_SEED` exactly like I-VIII, so `default_constitution()` now
returns 13 Articles for every new game. Deliberately scoped to the
Articles themselves: no new "Live Enforcement" citation hooks were
added for IX-XIII, since building new detectors for them would be new
feature engineering, not a documentation addition — the existing six
hooks continue to cite only I-VIII, the Articles with a real detector
already behind them. Because this only changes seeded *content*, not
the `ConstitutionState` schema shape, an existing in-progress save's own
persisted Constitution (created before this change) keeps whatever
Article count it already had — the schema-mismatch migration path in
`app/persistence.py` only triggers on a genuine validation failure, not
on stale-but-valid content, so no retroactive backfill was built for
already-running saves. This mirrors how every other seed-only addition
in this codebase behaves.

**Live Enforcement — six real citation hooks, one shared mapping table.**
`MISTAKE_ARTICLE_MAP` gives each of the 6 real `CaseStudyCategory`
mistake types (and their 3 positive inversions from
`SUCCESS_CASE_STUDY_CATEGORIES`) a specific, defensible Article:
`overconfidence`→VII, `incomplete_research`→II,
`unchallenged_assumptions`→III (and its inversion
`rigorous_cross_examination`→III), `acted_too_quickly`→V (and its
inversion `patient_execution`→V), `ignored_dissent`→IV,
`confirmation_bias`→IV. Every filed case study or success study cites
both Article VI (the mechanic itself is literally "every mistake must
teach something") and its own specific mapped Article. The other five
hooks, each firing at a real, already-existing event in
`app/nexus.py`'s `tick()`:

| Real event | Citation |
|---|---|
| A `ChallengeReport` is filed | Article III always (challenging is the Devil's Advocate's whole job); Article IV when `missingEvidence` is real and non-empty |
| A genuinely *new* critical `RiskWarning` appears (not already on the previous tick's watch) | Articles I and VII |
| An Academy project completes | Article VIII (a direct, literal instance of continuous learning) |
| The monthly Founder Council session runs | Keystone (risk domain) reaffirms Article VII; Compass (learning domain) reaffirms Article VIII |
| A weekly/monthly `CoachReport` carries real `commonMistakes` | whichever Article the most recent real `CaseStudy`'s own category maps to |

`MAX_CONSTITUTION_CITATIONS` (120) caps the log the same way every
other capped list in this codebase does.

**A real amendment pipeline, not a fabricated debate transcript**
(`app/constitution.py`). Three CEO actions, each a real, checkable
computation over the amendment's own real proposed text — never
randomly generated opinions:

1. `POST /api/constitution/propose` — creates a real
   `ConstitutionAmendment` in `status: "proposed"`.
2. `POST /api/constitution/advance` — runs Founder debate, Coach
   evaluation, and the employee vote in one step (unlike the Research
   Sandbox's stages, nothing here needs real elapsed time to gather more
   evidence; every part is an immediate computation over already-known
   text):
   - **Founder debate** (`_founder_verdict`): Keystone and Compass each
     check the proposal's significant words against their own real
     domain keyword set (risk vs. learning), and both run a real
     word-overlap redundancy check against every existing Article's own
     text. The redundancy check requires `MIN_SHARED_WORDS_FOR_REDUNDANCY`
     (2) shared words, not just a ratio — the seeded Articles are each
     one short sentence (as few as 2 significant words), so a bare
     single-word match would flag nearly any risk-themed proposal as
     "redundant" against Article VII ("Respect risk") purely because it
     also uses the word "risk."
   - **Coach evaluation** (`generate_coach_evaluation`): a real templated
     read of whichever real `CompanyHealth` sub-score the proposal's own
     keywords match (risk → `operational_stability`/`capital_health`,
     learning → `research_progress`/`education_progress`), falling back
     to overall `CompanyHealth.tier` when neither theme matches — never a
     fabricated simulation of "how this rule would have changed history."
   - **Employee vote** (`generate_employee_votes`): all 11 non-Founder
     agents cast a real vote — "support" with a real named reason when
     their own real `AgentProfile.occupation` keyword-matches the
     amendment's theme, "abstain" only when a Founder's own real
     redundancy flag was raised (a genuine conditional link to that real
     verdict), "support" by default otherwise. Advisory only — no vote
     count ever gates anything.
3. `POST /api/constitution/decide` — the CEO's own real, final,
   *manual* call. Deliberately **not** wired to Automation Mode, unlike
   the Research Sandbox's Company Review stage: amending the company's
   permanent law is exactly the kind of decision the brief frames as
   inherently the CEO's, never appropriate to auto-resolve. Approval
   calls `ratify_amendment()`, which appends a real new
   `ConstitutionArticle` (next Roman numeral — "IX," "X," ...) to the
   permanent list; rejection leaves the Articles untouched.

**New `CONSTITUTION` Command Center tab** (`ConstitutionPanel.tsx`,
inserted after `SANDBOX`): the Articles grid (with an "Amendment" badge
on any Article ratified after game start), a filterable Live
Enforcement citation feed, an amendment proposal form, and per-amendment
Founder verdicts/Coach evaluation/employee vote tally with
Ratify/Reject actions once a decision is pending.

**Save/load.** `constitution` (`ConstitutionState` — articles, citations,
amendments) joins `founder_state` in the `"founders"` core save module
— returned in full by `GET /api/load`, reflecting that Founders are the
system most directly tied to teaching the Constitution.
`default_state()` seeds the real 8-Article `default_constitution()`, so
an older save missing the field migrates cleanly through
`load_modules()`'s existing deep-merge-onto-`default_state()` recovery
path — confirmed live: restarting the backend against a pre-Feature-46
dev save produced a clean migration and the full 8-Article Constitution
on the very next `GET /api/load`.

**Verification.** Backend: `test_constitution.py` (18 new tests — the
redundancy-overlap edge case that motivated
`MIN_SHARED_WORDS_FOR_REDUNDANCY`, domain-keyword matching in both
directions for both Founders, the Coach evaluation's three real
branches, employee-vote exclusion of the two Founders, and the full
propose→debate→ratify pipeline including the next-Roman-numeral
assignment) + the full suite (570/570) + mypy/ruff clean. Frontend:
`tsc -b`/eslint/build clean; a new `constitution.spec.ts` (2 Playwright
tests against the live stack — confirming the real 8 Articles are
present in `GET /api/load`, and that proposing an amendment through the
CONSTITUTION tab runs the real pipeline end to end, surfacing real
Founder/Coach/employee output and a Ratify button) both passed;
`commandCenter.spec.ts`'s tab-count test updated to 27 tabs.

**Feature 47 verified**: backend — new `TestArticlesForChallenge` (6
tests covering each of the four concern buckets independently and in
combination) + `test_devils_advocate.py` gained 5 tests confirming
`generate_challenge_report`'s real wiring end to end (none-found reports
cite nothing; each real concern bucket cites its own mapped Article) +
the full suite (581/581) + mypy/ruff clean. Frontend: `tsc -b`/eslint/
build clean; a new `knowledgeBase.spec.ts` (2 Playwright tests against
the live stack — confirming every real `ChallengeReport`'s
`citedArticleIds` only ever names a real Article on the Constitution,
and that the OPS tab opens and renders the Knowledge Base timeline with
no console errors); `commandCenter.spec.ts`'s tab-count test updated to
28 tabs.

### Market Intelligence Department — Feature 51, "the company's eyes"

GOAL (from the brief): before any department searches for trades, the
company must first understand the environment it's operating in — every
department should receive Market Intelligence before deciding.

**The honesty boundary, decided before any code was written.** This
codebase's `MarketDataProvider` (`app/market_data.py`) exposes real (mock)
OHLCV `Candle` data — no order book, no Level 2, no dark-pool prints, no
economic calendar. The brief's longer feature list names several things
with no real data source anywhere in this codebase: true institutional
positioning, real resting stop-order locations, real per-symbol news/
event-risk timing. Rather than fabricate any of these, `app/market_intelligence.py`
draws a line documented in its own module docstring and repeated in every
affected schema field's own docstring:

| Real (standard technical analysis over real mock candle data) | Named PROXY (a real, computable stand-in, always labeled) | Explicitly not built |
|---|---|---|
| 13-way regime classification (trend/volatility/volume-ratio thresholds) | Institutional Activity — volume/price-move divergence ("absorption"), not real order flow | Real order-book/Level-2/dark-pool data |
| Market Structure — real local-extrema swing highs/lows, Break of Structure | Accumulation/Distribution regimes — flat price + rising/fading volume, not confirmed Wyckoff volume-at-price | Real resting stop-order locations |
| Liquidity zones — real equal-high/low clustering + a real sweep-and-close-back pattern | News Risk — the real count of `market`-category `NewsItem`s on file (no per-symbol linkage exists), not a real economic calendar | A real economic/earnings calendar |
| Volatility Engine — current/historical/session `volatility_pct()` readings | | |
| Session Intelligence — real wall-clock UTC time, fixed windows (documented, no DST handling) | | |
| Momentum — real rate-of-change across two real candle sub-windows | | |
| Strategy Matching — real cross-reference against `app/sandbox.py`'s own `StrategyReport.bestMarketEnvironment` | | |
| Learning Loop — real comparison against `app/market_environment.py`'s own regime timeline and real closed `PaperTrade` outcomes | | |

Every regime/quality/liquidity/structure string in the UI states this
distinction directly (e.g. `InstitutionalActivityRead`'s docstring: "a
real volume/price-divergence proxy, not verified order-flow data"), the
same discipline `app/confidence.py`'s own module docstring already
established for an overlapping list of factors it deliberately doesn't
compute.

**Two-tier architecture, mirroring `MarketEnvironmentState`/`CompanyHealth`'s
own "cheap live reading vs. permanent snapshot" split:**

- **`MarketIntelligenceState`** (`market_intelligence` on `GameSaveState`) —
  the always-current "eyes," recomputed fresh every tick from real (mock)
  candles across the live watchlist, before any trade proposal is
  generated (`app/nexus.py`'s `tick()`, right after `tick_watchlist`).
  This is what a new `TradeProposal` and the Trade Gatekeeper actually
  read — never the once-daily report below, which can be up to a day
  stale by the time a proposal fires.
- **`MarketIntelligenceReport`** (the Executive Market Brief,
  `market_intelligence_reports`) — one real, permanent snapshot per real
  in-game evening (`is_evening`, every day — not gated by a weekly/
  monthly modulo, per the brief's own "every day produce an Executive
  Market Brief"), embedding that day's `MarketIntelligenceState` plus a
  fresh 5-specialist Market Debate and Strategy Match. Capped at
  `MAX_MARKET_INTELLIGENCE_REPORTS` (60).
- **`MarketIntelligenceLearningEntry`** (`market_intelligence_learning`) —
  the Learning Loop, generated the day AFTER a report, once that day's
  real outcomes exist: compares the predicted regime against the real
  `MarketEnvironmentRegime` `app/market_environment.py`'s own timeline
  recorded for that day (via a documented, direction-only
  `_REGIME_CONSISTENCY_MAP` — several of the 13 regimes honestly map to
  more than one acceptable outcome against that coarser 5-way scale) and
  the real win rate of `PaperTrade`s actually closed that day. Either
  comparison field is honestly `None` when nothing real exists yet to
  compare against. Capped at `MAX_MARKET_INTELLIGENCE_LEARNING` (60).

**Market Debate System** (`app/market_debate.py`) — five specialists
(Liquidity/Price Action/Momentum/Quant/Risk), each independently reading
the real `MarketIntelligenceState` — never a trade-specific opinion, and
deliberately distinct from two other real debate-shaped systems already
in this codebase: `app/debate.py`'s `AiDebate` (proposal-scoped, six
analyst-vote seats) and the Executive Intelligence Network's own "Risk"
department (a proposal's portfolio-exposure read). This module's Risk
specialist reads only real market-CONDITION risk (session liquidity,
quality tier, news volume) — never portfolio positions or drawdown,
which stays Sentinel/Guardian's job, so it's additive rather than a
duplicate.

**Integration — "every department receives Market Intelligence" made
literally true by construction, not by rewriting eight separate
modules:**

- **Trade Gatekeeper** (`app/gatekeeper.py`) — a new 8th real check,
  `_market_intelligence_check`: a trade cannot pass while the
  department's own current Market Quality Score reads `avoid_trading` —
  the mechanical enforcement of the brief's closing rule ("no department
  may recommend a trade without first explaining the current market
  environment... every recommendation must be justified before capital
  is committed").
- **TradeProposal** (`app/executive.py`'s `generate_proposal`) — every
  new proposal carries a real one-line `marketIntelligenceSummary`
  citation of the department's regime/quality read at generation time.
- **Executive Intelligence Network** (`app/executive_intelligence.py`) —
  `market_intelligence` becomes a real ninth `ExecutiveDepartmentRole`.
  Because the Executive Meeting Log and Weekly Self-Evaluation already
  iterate `_ALL_DEPARTMENT_ROLES` generically (Feature 50), adding one
  more role to that tuple plus one new `_market_intelligence_opinion()`
  function was the entire integration — no changes needed to either of
  those two systems. `compute_executive_recommendation()` also gained a
  new top-priority rule: a real `avoid_trading` read outranks every
  other department's opinion, mirroring what the Gatekeeper's own check
  is about to do mechanically.
- **Strategy Matching** cross-references `app/sandbox.py`'s real
  `Strategy`/`StrategyReport` history — only ever recommends a strategy
  with real positive evidence in a matching regime, only ever avoids one
  with a real recorded loss in one, honest "no real match yet" otherwise.

**Academy Integration** (`app/foundational_mentors.py`) — a real,
shipped seventh roadmap track, `market_intelligence`, appended after
`mike_bellafiore`. Deliberately NOT attributed to any real external
trading educator (unlike the other six tracks): its own content note
states this directly, since Market Intelligence is TradeTown's own
in-house department, not a real person's expertise. Eight real lessons —
Market Regimes & Trend Analysis, Market Structure, Liquidity,
Institutional Behavior, Session Characteristics, Volatility, Probability
Thinking, and Risk Context — each citing a specific real
`app/market_intelligence.py` field or formula the same way `_TJR_LESSONS`
already cites `app/discipline.py`/`app/risk_engine.py`/etc., including
where a lesson is honest about a named proxy (Institutional Activity,
Liquidity zones) rather than claiming real order-flow knowledge. Employee
auto-progression, the aptitude-based auto-quiz, and CEO-approved
graduation all reuse the module's existing generic machinery with zero
new code needed beyond the lesson content itself and the roadmap/focus-
area entries — exactly what the module's own docstring already
described as the extension point. One real, measurable consequence: with
two tracks (`tjr` and `market_intelligence`) both real and `"active"`
by default on a fresh game, `app/company_health.py`'s
`_talent_development()` metric's real denominator now spans both real
active tracks (students × active-track count), not just one — its own
formula already supported this correctly; only the test fixtures
assuming a single active track needed updating.

**Frontend — a new "MARKETINTEL" Command Center tab**
(`MarketIntelPanel.tsx`), mirroring EXECINTEL's precedent rather than
being crammed into RISK/COMPANY given the data volume. Data-layer wiring
follows the exact same pattern `marketEnvironment`/`companyHealth`
already established: `NexusManager.ts` gained the three new fields (an
object-reference diff for the always-current `marketIntelligence` state,
a `.length` diff for the two growing history arrays), `EventBus.ts`
gained the three matching event names, `gameStore.ts` gained matching
defaults (identical to `default_market_intelligence_state()`'s own
honest empty-state values) and listeners, and `socket.ts` threads the
three fields through untouched from the WS "state" payload — no new
data-fetching logic anywhere. The panel itself shows: the live regime/
quality read (score, confidence, evidence, historical similarity);
Session/Volatility/Momentum/Institutional Activity/News Risk cards (the
latter two visibly marked as named proxies); a per-symbol Liquidity &
Structure grid; the latest Executive Market Brief (all 5 debate
specialists, Strategy Match) or its honest empty state before the first
in-game evening; and the Learning Loop history or its own honest empty
state before the first graded day. The Academy track's own lesson UI
needed zero new frontend code: `MentorLibraryPanel.tsx`/
`MentorLabPanel.tsx` already iterate `foundationalMentorState.mentors`
generically, so the new `market_intelligence` roadmap track appeared
there automatically once the backend shipped it.

**Verified**: two new backend test files — `test_market_intelligence.py`
(41 tests: structure/liquidity/session/news-risk/regime-classification/
quality-score/strategy-matching/learning-loop/end-to-end state
computation) and `test_market_debate.py` (10 tests: all 5 specialists
present, each reads its own real field, the Risk specialist never reads
portfolio state) — plus updates to the pre-existing gatekeeper/executive/
executive_intelligence/company_health/foundational_mentors suites for
the new department/check/track — 775/775 full suite, mypy/ruff clean. A
direct ~10-in-game-day `nexus.tick()` simulation (not just unit tests)
confirmed the daily report/Learning Loop cadence, real
`TradeProposal.marketIntelligenceSummary` citations, and real
`market_intelligence` opinions landing in the Executive Meeting Log with
no exceptions; a `save_modules` split/assemble round-trip confirmed the
new fields persist correctly (`market_intelligence` joins `derived`
alongside `market_environment`; `market_intelligence_reports`/
`market_intelligence_learning` join `knowledge_archive` alongside
`department_self_evaluations`). Frontend: `npx tsc -b --noEmit`/
`npm run lint`/`npm run build` all clean; the new panel was verified
against the live Vite + FastAPI stack via scripted browser screenshots
(both the honest pre-first-evening empty state and, after fast-forwarding
real in-game time via `POST /api/time/advance`, the fully populated
Executive Market Brief and a graded Learning Loop entry) with zero
console/React errors. The repo's standard `commandCenter.spec.ts`/new
`marketIntel.spec.ts` Playwright specs were updated for the 31st tab, but
this sandbox's Playwright run currently fails to reach the title screen's
"Continue" button at its configured 1400×900 viewport for every Command
Center spec — reproduced identically on unmodified, pre-existing spec
files unrelated to this feature — a pre-existing environment flake, not
a regression from this change.

### Strategy Validation Laboratory — Feature 52 (Part 1), "Never Trade An Untested Idea"

GOAL (from the brief): no strategy should ever be traded simply because an
employee believes it works — every strategy earns its way to real capital
through evidence, not opinion.

**Researched first.** This codebase already had almost every real
building block the brief's longer validation pipeline (Monte Carlo /
Market Regime / Liquidity / Risk / 9-department Executive Review /
Founder Approval) asks for — `app/sandbox.py`'s already-real 8-stage
gated pipeline, `app/market_intelligence.py`'s regime/liquidity/structure
engines, `app/whatif.py`'s Monte Carlo bootstrap pattern,
`app/executive_intelligence.py`'s 9-department opinion machinery, and
`app/founders.py`'s threshold-approval pattern — just not assembled into
named, reported-on artifacts. New `app/strategy_lab.py` is that
enrichment layer, not a rebuild.

**Monte Carlo Testing** — `run_strategy_monte_carlo()` is a real
trade-sequence bootstrap (200 simulated paths), distinct from
`app/whatif.py`'s own Monte Carlo (which resamples *price paths* for a
symbol, not a strategy's own trade sequence). Every generating number —
win rate, average win %, average loss %, trades-per-path — is a real
aggregate of the strategy's own already-real `SimulationResult` history;
nothing is independently invented. Tracks median/10th/90th-percentile
return, median/worst-case (5th-percentile) drawdown, probability of
profit, and a real, explicitly-scoped **probability of ruin**: the share
of this run's own 200 paths that breached a named `RUIN_DRAWDOWN_PCT`
(50%) bar — never claimed as a true infinite-sample probability.

**Market Regime Testing** — `compute_strategy_regime_test()` buckets a
strategy's `SimulationResult` history by `TestScenario` (bull/bear/
sideways/high_volatility/low_volatility/historical), since results are
only ever tagged at that coarser 7-way grain. Each bucket is labeled with
which of Feature 51's real 13-way `MarketIntelligenceRegime`s it covers
(the reverse of `market_intelligence.py`'s own `_REGIME_TO_SCENARIO_KEYWORD`
map) — an honest "here's what this bucket represents," never a claim of
independently-tested 13-way granularity.

**Liquidity Validation** — `validate_strategy_liquidity()` reuses Feature
51's real `compute_liquidity()`/`compute_market_structure()` against the
strategy's own live watchlist, as-is. No new liquidity math, and no claim
beyond what those functions already claim (real equal-high/low
clustering + a real sweep pattern, never real resting stop-order
locations or institutional order flow).

**Risk Analysis (a real, standalone gate)** — `sandbox.py`'s new
`evaluate_risk_gate()` reuses Guardian's own `RISK_MAX_AVG_DRAWDOWN`
threshold and now also gates Market Simulation → Paper Trading directly
(`begin_paper_trial()` calls it first), honoring the brief's stage order
(Risk Analysis before Paper Trading). This is an earlier, narrower real
checkpoint — it does not replace the richer five-reviewer `StrategyReview`
risk verdict still run later at Company Review.

**Executive Review (9 departments)** — `generate_strategy_executive_review()`
reuses the exact same nine real department seats as Feature 50's
`ExecutiveDepartmentRole` (research/quant/risk/simulation/
decision_intelligence/coach/founders/devils_advocate/market_intelligence).
The brief's ninth seat, "Brain Room," is not a distinct department
anywhere in this codebase (see `ExecutiveIntelPanel.tsx`'s own real/cut
note) — reuses the same `devils_advocate` seat every other 9-role read in
this codebase already does. Each department's opinion is a real read of
already-real inputs (the `StrategyReview`'s own verdicts, the Monte Carlo
result, the regime test, Coach reports, live Market Intelligence) — never
an independently invented number. The nine opinions combine into a real
`advance` / `request_more_evidence` / `hold_for_improvement` / `reject`
recommendation (`StrategyExecutiveAction` — deliberately distinct from
the trade-scoped `ExecutiveAction`, since strategy-lifecycle semantics
differ from single-trade semantics): 2+ rejecting departments rejects
outright, exactly 1 holds for improvement, 4+ departments wanting more
evidence requests it, otherwise the strategy advances.

**Founder Approval** — `generate_strategy_founder_approval()` is a new
mode of `app/founders.py`'s existing threshold-approval pattern
(previously only applied to Black Box Projects), applied to a strategy:
approved only when the Executive Review both recommends `advance` and
clears `FOUNDER_APPROVAL_CONFIDENCE_THRESHOLD` (60%).

**Confidence Score** — `compute_strategy_confidence_score()` is a real
composite (Executive Review confidence + Monte Carlo probability of
profit, averaged) with real evidence/strengths/weaknesses pulled directly
from the artifacts above, plus a real risk rating and a real recommended
position size that scales down as real ruin risk rises. Computed fresh on
request, never persisted — same reasoning as `ExecutiveRecommendation`/
`WhatIfSimulation`: every input it reads already lives somewhere
permanent.

**Strategy Dossier** — `generate_strategy_dossier()` is the brief's
"auto-generated professional report": assembles the latest
`StrategyReport`/`StrategyReview`/Monte Carlo/regime test/liquidity
validation/executive review/founder approval/confidence score for one
strategy into a single read. Exposed at new
`GET /api/sandbox/dossier?strategyId=` (no game-state lock needed,
mirrors `GET /api/executive/intelligence`'s own compute-on-request
pattern).

**Integration** — `POST /api/sandbox/request-review` now files the
`StrategyExecutiveReview` and `StrategyFounderApproval` in the same real
CEO action as the existing `StrategyReview`: Company Review, Executive
Review, and Founder Approval are one moment, not three separate CEO
requests, per the brief's own stage ordering. `app/nexus.py`'s tick loop
re-runs the Monte Carlo bootstrap, regime test, and liquidity validation
automatically every time a Market Simulation run completes for a
strategy, right alongside the existing `StrategyReport` generation. Five
new capped (`MAX_STRATEGY_*_RESULTS/TESTS/VALIDATIONS/REVIEWS/APPROVALS`,
40 each), permanent `GameSaveState` lists join the `company` save module
right after `strategy_reviews`, and are broadcast over the WS tick
alongside it.

**Explicitly not built, and why**: a true infinite-sample probability of
ruin (only ever a real share of this run's own simulated paths, clearly
labeled); real institutional liquidity/retail stop clusters/market maker
behavior (inherited directly from Feature 51's own honesty boundary, not
re-litigated here); a second backtest/Monte Carlo engine (would repeat
the exact "redundant re-measurement" trap `app/sandbox.py`'s own
docstring already warns against — this module's bootstrap always reuses
`SimulationResult`'s real generating statistics).

**Verified**: new `backend/tests/test_strategy_lab.py` (17 tests
covering the Monte Carlo bootstrap, regime bucketing, liquidity
validation, all 9 executive department opinions, founder approval
thresholds, confidence scoring, and dossier assembly) plus a new
sandbox risk-gate rejection test — 793/793 full backend suite, `mypy`/
`ruff` clean. Feature 52 Part 2 ("Living Strategies" — Strategy Library,
Versioning, Health, Hall of Fame, Failed Strategy Archive, Competitions,
Company DNA integration) and both parts' frontend are deliberately
deferred to a follow-up pass — this codebase has no mechanism to
attribute a live/paper trade back to a specific `Strategy` object
(`strategy_id` exists only on `BacktestSession`/`SimulationResult`/
`StrategyReport`/`StrategyReview`, never on `PaperTrade`/`TradeDecision`/
`TradeProposal`), so Part 2's "Live Performance Monitor" will need an
honest reframe around real `SimulationResult`/`StrategyReport` history
rather than literal live-trade attribution when it's built.

### Strategy Validation Laboratory — Feature 52 (Part 2), "Living Strategies"

GOAL (from the brief): a strategy should never become "finished" — the
company's greatest asset is a growing library of validated strategies
that evolve, prove themselves permanently, or teach real lessons when
they fail.

**Scoping decision, made explicit before any code was written.** Part
2's brief is the largest single section of Feature 52 — Strategy
Library, Version Control, Strategy Evolution, a Live Performance
Monitor, Strategy Health, Automatic Revalidation, Strategy Retirement,
a Strategy Hall of Fame, a Failed Strategy Archive, long-running
Research Projects, Strategy Competitions, Knowledge Preservation, an
Executive Dashboard, and Company DNA integration. Building all of it
honestly in one pass would mean inventing a real strategy-versioning
mechanism this codebase has never had (parent/child strategy links, a
full pipeline re-run per revision) — a structural addition on the order
of Part 1 itself, not a natural extension of what already exists. This
pass builds the real, tractable subset that extends Part 1's own
already-real artifacts, and explicitly documents every cut below rather
than silently shipping a partial "Strategy Library."

**Strategy Health** (`compute_strategy_health()`) — a real
recent-vs-lifetime trend read over a strategy's own `SimulationResult`
history: the last `HEALTH_RECENT_WINDOW` (3) real runs compared against
the strategy's full real lifetime average (including those same recent
runs, so a young strategy's recent and lifetime reads are honestly
identical rather than dividing an already-thin sample in two). Lands on
one of seven real statuses — Excellent/Healthy/Stable/Needs Review/
Declining/Critical/Retire Candidate — from a fixed, deterministic ladder
over real win-rate/return/drawdown deltas (reusing `sandbox.py`'s own
real `RISK_MAX_AVG_DRAWDOWN` for the "critical" bar rather than a second
invented threshold). Re-computed on the exact same per-completed-
simulation trigger in `nexus.py`'s tick loop as Part 1's Monte Carlo/
Regime Test/Liquidity Validation, capped and persisted the same way.
Deliberately NOT the brief's literal "Live Performance Monitor" — see
Part 1's own honesty-boundary note (this codebase cannot attribute a
live/paper trade back to a specific `Strategy` object); this reads the
real Market Simulation run history a strategy actually has.

**Strategy Retirement** — the only genuinely new lifecycle mechanic in
this pass. `StrategyStage` gains a terminal `"retired"` value, placed
last in `sandbox.py`'s own `STAGE_ORDER` so every existing stage-gated
advance function (`maybe_advance_after_research`/`maybe_advance_after_result`/
`begin_paper_trial`/etc.) treats a retired strategy as "already furthest
along" and safely no-ops — no special-casing needed anywhere else in the
pipeline. New `retire_strategy()` (in `sandbox.py`, reusing `_advance`)
is reachable from any non-terminal stage via a real, deliberate CEO
action — `POST /api/sandbox/retire` — never automatic. This is a
narrower interpretation than the brief's fully autonomous "Automatic
Revalidation" workflow (Research Review → Backtest Review → ... →
Continue/Modify/Suspend/Archive/Retire): every other terminal Research
Sandbox decision in this codebase is already a real CEO call (Learning
Mode's own precedent — see this doc's Feature 45 section), so retirement
follows the same discipline rather than inventing a new autonomous
decision loop. The CEO is expected to cite the strategy's own real
`StrategyHealthAssessment` as the reason, though the field itself is
just a required real string.

**Strategy Hall of Fame / Failed Strategy Archive** — every real
retirement files exactly one of these two permanent records, never both,
never neither (`generate_strategy_retirement_outcome()`). Hall of Fame
induction requires a real, strict bar checked only at the moment of
retirement, never speculatively: ≥30 aggregated real trades, ≥55% win
rate, ≥1.5 profit factor, ≤20% average drawdown (`sandbox.py`'s own
`RISK_MAX_AVG_DRAWDOWN`), `stage == "approved"` immediately before
retirement, and a real, on-file `StrategyFounderApproval` with
`verdict == "approved"`. Every retirement that doesn't clear that bar
becomes a Failed Strategy Archive entry instead — "what failed" pulled
from the strategy's own real `StrategyReview` verdicts that didn't pass,
"lessons learned" pulled from the real `concerns` every department filed
in its last `StrategyExecutiveReview`, never invented after the fact
(an honest fallback note when neither exists yet). Both records are
permanent — nothing here is ever deleted, matching the brief's own
"nothing is ever deleted" rule for the fuller Strategy Library this pass
doesn't build.

**Company DNA integration** — a Hall of Fame induction nudges Company
DNA's real `research_rigor` Legacy trait up (`STRATEGY_HALL_OF_FAME_NUDGE`),
a fifth real trigger alongside the four `app/company_dna.py`'s own module
docstring already tracked (Black Box breakthroughs, Academy completions,
success studies, Founder retirement). Fired synchronously inside
`state.py`'s `retire_strategy()` CEO action rather than `nexus.py`'s tick
loop, since retirement is itself a real, one-time CEO decision the tick
loop never independently discovers — every other Legacy nudge fires from
inside `tick()` because its own trigger (a completed research item, a
filed success study) is something the tick loop notices, not something a
CEO directly requests.

**Executive Dashboard** (`compute_strategy_executive_dashboard()`,
`GET /api/sandbox/dashboard`) — a real, computed-on-request aggregate,
same no-lock-needed pattern as `GET /api/sandbox/dossier`: real stage
counts (active/in-development/in-validation/paper-trading/approved/
retired), real Hall of Fame/Failed Archive counts, and five named slots
(best/weakest/most-improved/newest/highest-confidence strategy), each
citing the real metric value that earned it the slot — average real
return for best/weakest, a real recent-vs-lifetime return delta (reusing
`compute_strategy_health()`) for most-improved, and a real confidence
score (reusing Part 1's `compute_strategy_confidence_score()`) for
highest-confidence. "Newest" is date-based rather than a magnitude, so
its `metricValue` is honestly `0.0` — documented on
`StrategyExecutiveDashboardEntry` itself rather than silently overloading
the field's meaning.

**Explicitly not built in this pass, and why**:

| Brief section | Why cut |
|---|---|
| Version Control / Strategy Evolution | No strategy revision/parent-child mechanism exists anywhere in this codebase to extend — a real structural addition, not a data-honesty cut. Deferred to a dedicated follow-up. |
| Strategy Competitions | Needs Version Control as a real prerequisite (comparing "v2.3 vs v2.4" requires versions to exist first). |
| Automatic Revalidation as an autonomous workflow | Narrowed to a real, deliberate CEO retirement action instead — see "Strategy Retirement" above for why. |
| Dedicated Research Projects | Already real and shipped as Black Box Projects (`app/black_box.py`) — long-running, multi-month, funded research efforts already exist under a different name; not duplicated. |
| A literal "Strategy Library" UI concept | The existing `strategies` list plus Part 1's `StrategyDossier` already carries every real field the brief's Library section asks for (creator/status/stage/confidence/regimes/risk profile/description/historical performance/executive notes) — no new backend artifact needed; this is purely a frontend presentation concern, deferred with the rest of Feature 52's UI. |
| Knowledge Preservation beyond what Failed Archive/Hall of Fame already carry | Without Version Control, "knowledge transfers forward on evolution" has no real forward-transfer event to hook into — the real lessons-learned text each retirement record carries already satisfies the brief's underlying goal (a citable, permanent lesson) without the transfer mechanic. |

**Verified**: 11 new tests in `backend/tests/test_strategy_lab.py` (28
total: Strategy Health status ladder, Hall of Fame induction/rejection
paths, Failed Archive fallback lessons, Executive Dashboard stage
counting and named slots) plus 3 new tests in `backend/tests/test_sandbox.py`
(retirement from every non-terminal stage, rejecting a double retirement,
confirming a retired strategy never advances further) — 807/807 full
backend suite, `mypy`/`ruff` clean. Both parts' frontend remain
deliberately deferred to a follow-up pass, per this project's
backend-first discipline.

### Strategy Validation Laboratory — frontend (both Feature 52 parts)

One Command Center tab (`SANDBOX`), restructured into eight real
sub-views under `frontend/src/ui/components/CommandCenter/panels/sandbox/`
rather than eight more top-level tabs — this Command Center already
carries 31 (`FullCommandCenter.tsx`'s own `TABS` array); the sub-tab bar
pattern mirrors that same nav's visual language at a smaller scale.

- **`SandboxPanel.tsx`** — the container. Owns `subTab`/`selectedId`
  state so the CEO's current strategy selection persists across
  sub-tabs. `STRATEGY_SCOPED` (PIPELINE/CERTIFICATION/HEALTH/EVOLUTION)
  render the shared `StrategySidebarPanel` + a right-column detail view;
  LIBRARY/HALL OF FAME/FAILED ARCHIVE/DASHBOARD render full-width,
  company-wide views with no per-strategy sidebar.
- **`StrategyPipelineView.tsx`** — the original Feature 45 Research
  Sandbox content (queue backtests, walk the real CEO-authorized stage
  checkpoints), plus a new Retirement card: a real, named-reason,
  irreversible CEO action reachable from any non-terminal stage, wired
  to `POST /api/sandbox/retire` via `NexusManager.setStrategyRetirementOutcome()`.
- **`StrategyLibraryView.tsx`** — every strategy this company has ever
  created, including retired ones, in one table with real aggregated
  stats (avg return/win rate across that strategy's own `SimulationResult`
  history) and a click-through into CERTIFICATION. Satisfies the brief's
  "Strategy Library" section without a new backend artifact — every
  field it asks for (creator/status/stage/description/historical
  performance) already lives on the real `Strategy` object plus its own
  history.
- **`StrategyCertificationView.tsx`** — fetches the full real
  `StrategyDossier` on request (`GET /api/sandbox/dossier`) and renders
  Confidence Score, Monte Carlo Testing, Market Regime Testing,
  Liquidity Validation, the 9-department Executive Review, and Founder
  Approval — each section only rendered when that real artifact exists,
  an honest empty state otherwise.
- **`StrategyHealthView.tsx`** — an **honest reframe** of the brief's
  "Live Performance Monitor." This codebase has no mechanism to
  attribute a live/paper trade back to a specific `Strategy` object (see
  `backend/app/sandbox.py`'s own module docstring) — there is no real
  live P&L stream to monitor. The view states this directly in its own
  header copy, then shows what IS real: `StrategyHealthAssessment`'s
  recent-vs-lifetime trend read, plus a full history table.
- **`StrategyEvolutionView.tsx`** — an **honest reframe** of "Strategy
  Evolution." This codebase has no strategy revision/versioning
  mechanism (no v1.0→v1.1→v2.0 parent/child links — see the Part 2
  backend section's own cut table), so rather than fabricate a fake
  version history, this shows the strategy's own real `stageHistory`
  timeline (every stage it has actually earned, each backed by a real
  signal) plus, for a retired strategy, its one real permanent
  Hall of Fame/Failed Archive outcome.
- **`StrategyHallOfFameView.tsx`** / **`StrategyFailedArchiveView.tsx`**
  — the two permanent real retirement outcomes, read straight from
  `strategyHallOfFame`/`strategyFailedArchive`.
- **`StrategyExecutiveDashboardView.tsx`** — fetches the real,
  computed-on-request `StrategyExecutiveDashboard` (`GET /api/sandbox/dashboard`)
  on open and on a manual Refresh, rendering stage counts and the five
  named best/weakest/most-improved/newest/highest-confidence slots, each
  citing its real metric value (except "newest," a date-based pick —
  its `metricValue` is honestly `0.0`, per the schema's own docstring).

**Data-layer wiring** — all 8 new WS-broadcast state fields
(`strategyMonteCarloResults`/`strategyRegimeTests`/
`strategyLiquidityValidations`/`strategyExecutiveReviews`/
`strategyFounderApprovals`/`strategyHealthAssessments`/
`strategyHallOfFame`/`strategyFailedArchive`) were threaded end to end
through `types.ts` (new interfaces mirroring every Part 1/2 backend
schema 1:1, plus `"retired"` added to the `StrategyStage` union) →
`net/socket.ts`'s `ServerMessage`/dispatch → `NexusManager.ts`'s
`NexusSnapshot`/private fields/getters/`applyServerUpdate()`/
`loadFromSave()` → `EventBus.ts`'s event map → `state/gameStore.ts`'s
`GameUiState`/subscriptions — the exact same diff-and-emit pattern every
existing field (e.g. `strategyReviews`) already uses, so no new data-flow
concept was introduced. Two new `NexusManager` setters apply a CEO
action's REST response immediately rather than waiting for the next WS
tick, the same pattern `setSandboxState` already established:
`setStrategyExecutiveOutcome()` (for `/request-review`'s richer
response, which now also files a real `StrategyExecutiveReview`/
`StrategyFounderApproval`) and `setStrategyRetirementOutcome()` (for
`/retire`'s real, exactly-one-of-two outcome). New `net/api.ts`
functions for `POST /sandbox/retire`, `GET /sandbox/dossier`,
`GET /sandbox/dashboard`.

**New `lib/derive.ts` tone helpers** — `strategyExecutiveActionTone`/
`strategyRegimeVerdictTone`/`strategyLiquidityVerdictTone`/
`strategyRiskRatingTone`/`strategyHealthTone` each map a real backend
enum onto the existing green/cyan/amber/red `StatusPill` convention,
mirroring `executiveActionTone`'s own precedent. The trade-scoped
`executiveStanceTone` is reused as-is (not duplicated) for the Strategy
Executive Review's department opinions, since `StrategyDepartmentOpinion.stance`
and `DepartmentOpinion.stance` share the exact same real `ExecutiveStance`
union. `STAGE_LABELS` (including the new `"retired"` entry) moved into
`derive.ts` so it can be shared across every sandbox sub-view file
without violating React Fast Refresh's one-component-per-file
convention (`react-refresh/only-export-components`).

**Verified**: `npx tsc -b --noEmit`/`npm run lint`/`npm run build` all
clean. `sandbox.spec.ts` extended with a new Playwright test that opens
every sub-tab against the live Vite + FastAPI stack, drills into a real
Certification dossier via the Library's Open button, and opens/cancels
the real Retire form — deliberately never confirms retirement, since
that's a real, irreversible CEO action a test must not perform as a
side effect against the shared dev backend. All three `sandbox.spec.ts`
tests pass with zero console errors.

### Company Certification — Feature 53 (Slice 1), backend

GOAL (from the brief): "Before ANY strategy is allowed to trade live
capital, it must receive official Company Certification" — a formal
gate combining a named list of 14 real requirements, revocable at any
time if performance deteriorates.

**Researched first.** Every one of the brief's 14 requirements already
had a real, existing artifact behind it after Feature 52 — this slice's
whole job was combining them into one explicit checklist, not measuring
anything new: minimum sample size/expectancy/drawdown read off
`SimulationResult` and `StrategyMonteCarloResult`; regime consistency
off `StrategyRegimeTestReport`; the five named department approvals off
`StrategyExecutiveReview.opinions` (checking `stance == "agree"` for the
`risk`/`market_intelligence`/`quant`/`simulation`/`decision_intelligence`
roles); Founder/CEO approval off `StrategyFounderApproval`/
`StrategyReview.ceo_decision`. The one requirement with no obvious
existing analog — "Successful Stress Testing," named as distinct from
Monte Carlo Testing in the brief's own list — is honestly built by
reusing existing Monte Carlo tail data (`return_range_low_pct`, the
real 10th-percentile bootstrap return) plus the regime test's weak
buckets under a new, brief-requested lens, rather than building a
second bootstrap engine (`app/strategy_lab.py`'s own module docstring
already warns against exactly that trap).

**`compute_strategy_certification()`** (app/strategy_lab.py) returns a
`StrategyCertification`: 15 real `StrategyCertificationRequirement`
entries (the brief's 14, plus one this codebase adds — see below) and a
`certified: bool` that's `True` only when every one passes. Computed
fresh on request (`GET /api/sandbox/certification?strategyId=`), the
same "every input already lives somewhere permanent" reasoning as
`StrategyDossier`.

**The 15th requirement, Health Standing, is how "may be revoked at any
time" is honestly satisfied.** Rather than build a separate persisted
"certified" flag with its own revocation event log, `certified` is
*always* a fresh read of the strategy's own real current state — so the
moment a certified strategy's `StrategyHealthAssessment.status` degrades
to `"critical"`/`"retire_candidate"`, the Health Standing requirement
fails on the very next `GET /api/sandbox/certification` call and
`certified` flips to `false` automatically. No separate revocation
mechanism, no stored history of "was certified, now isn't" — the
current real state is the only source of truth, matching every other
compute-on-request artifact in this codebase.

**Two requirements — Founder Approval and Final CEO Approval — can
only ever be real at `stage == "approved"`,** since both only exist
once a strategy reaches Company Review, which in this codebase's real
pipeline order comes *after* Limited Live Capital (paper_trading →
limited_live_capital → company_review → approved). This creates a real
ordering conflict with the brief's "before ANY strategy trades live
capital" framing: full Certification literally cannot exist yet at the
point real capital first gets allocated (`begin_limited_live_capital`).
Rather than silently ignore this or restructure the whole pipeline
order (a change far outside this slice's scope), the honest resolution
is two-tiered:

- **`evaluate_certification_readiness()`** — the real, ENFORCED subset
  of the same checklist restricted to what's achievable *before* Company
  Review (sample size, expectancy, Monte Carlo drawdown/ruin, stress
  test, regime consistency) — now a hard gate on
  `POST /api/sandbox/begin-limited-live` itself
  (`app/state.py`'s `begin_strategy_limited_live()`), reusing the exact
  same thresholds as the full checklist rather than a second set of
  numbers. This is the real, literal answer to "before any strategy
  trades live capital, it must clear real Certification checks."
- **`compute_strategy_certification()`**'s full 15-point checklist
  (including Founder/CEO approval) is the complete, transparent audit
  shown once a strategy has progressed further — the authoritative
  answer to "is this specific `stage == 'approved'` strategy backed by
  every real requirement the brief asks for," which in practice isn't
  automatically guaranteed by reaching "approved" alone (e.g. under
  Assisted/Executive Automation Mode, a review can auto-resolve without
  every enrichment artifact having been separately generated first) —
  so Certification is a genuinely new, real transparency feature, not
  a duplicate of the "approved" stage label.

**Verified**: 6 new tests in `test_strategy_lab.py` — a strategy with
strong real results across two regimes and every department opinion
forced to a real "agree" stance passes all 15 requirements; a strategy
with zero evidence fails all 15; a real health decline to "critical"
flips a previously-met Health Standing requirement to failed; the
readiness gate passes on a strong pre-Company-Review fixture and fails
on both an empty-evidence fixture and a deliberately ruinous Monte
Carlo fixture — 813/813 full backend suite, `mypy`/`ruff` clean.
Frontend (surfacing the 15-point checklist on the CERTIFICATION
sub-tab) is a separate, immediately-following commit per this project's
backend-first discipline.

### Company Certification — Feature 53 (Slice 1), frontend

`StrategyCertificationView.tsx` (the CERTIFICATION sub-tab, already
rendering the Feature 52 dossier) now also fetches
`GET /api/sandbox/certification` in the same `Promise.all` as the
existing dossier fetch, and renders the 15-point checklist as a new
`Glass` panel above every dossier section — a `CERTIFIED`/`NOT
CERTIFIED` `StatusPill`, then each `StrategyCertificationRequirement`'s
own met/not-met pill, label, and detail string in a responsive grid. No
new client-side interpretation of certification status: the component
displays exactly what `compute_strategy_certification()` returned, so
the backend's fresh-read revocation behavior (a real Health decline
flipping `certified` to `false`) shows up here automatically the next
time the tab is opened — nothing to keep in sync client-side.

New `StrategyCertification`/`StrategyCertificationRequirement`
interfaces in `types.ts`, mirroring the backend schemas field-for-field,
and `api.getSandboxCertification(strategyId)` in `net/api.ts`, following
the same read-only compute-on-request pattern already used for
`getSandboxDossier`/`getSandboxDashboard` — no data-layer wiring through
`socket.ts`/`NexusManager.ts`/`EventBus.ts`/`gameStore.ts`, since this
is fetched directly into component-local state on open, not broadcast
over the WS tick.

**Verified**: `sandbox.spec.ts`'s existing CERTIFICATION assertion
extended to also check for the new checklist banner text and the
CERTIFIED/NOT CERTIFIED pill; `tsc -b --noEmit`, `eslint --max-warnings
0`, and `vite build` all clean; all 3 `sandbox.spec.ts` tests pass
against the live Vite + FastAPI stack with zero console errors.

### The Decision Memory System — Feature 54 (Feature 53 in the brief), backend

GOAL (from the brief): "TradeTown should never make the same mistake
twice... every meaningful trading decision is automatically archived...
Nothing should ever be deleted." Paired with a companion Performance
Analytics brief asking for a per-trade Trade Report Card and a
Similarity Engine ("this setup closely matches N historical trades").

**Naming collision, resolved up front.** The brief self-numbers itself
"Feature 53," but that number is already permanently in use in this
codebase's own history for Company Certification (the section directly
above this one). Rather than silently overwrite that number or leave the
collision unaddressed, this slice is referred to as **Feature 54**
everywhere it appears — code comments, commit history, this document —
while the module docstring still notes the brief's own self-numbering
for anyone cross-referencing the original brief text.

**Researched first.** Before any code was written, every existing
trade/decision-review system in this codebase was mapped end to end. The
overwhelming majority of the brief's asks already exist as real,
separate artifacts — this table is the full accounting:

| Brief asks for | Already real, as |
|---|---|
| Decision Grade | `app/executive.py`'s `compute_decision_grade()` |
| Discipline / Patience score | `app/discipline.py`'s `DisciplineReview` |
| Evidence / Confidence | `app/confidence.py`'s `DecisionConfidence` |
| Mistake detection | `app/mistakes.py`'s `CaseStudy` |
| Lessons learned | `app/journal.py`'s `PaperTrade.lessonsLearned` |
| Executive notes | `app/executive_intelligence.py`'s `ExecutiveMeetingLogEntry` |
| Company DNA update | `app/company_dna.py`'s `nudge_legacy()` |

This slice's real, novel job is exactly the two things the brief asked
for that genuinely did not exist anywhere: a permanent **Decision
Vault** that JOINS all of the above into one addressable record per
closed trade, and a **Similarity Engine** that can honestly answer "have
we seen this before."

**`build_vault_entry()`** (`app/decision_vault.py`) constructs one
permanent `DecisionVaultEntry` per closed trade, joining its
`TradeDecision`, `PaperTrade`, `DisciplineReview`, any filed `CaseStudy`,
`ExecutiveMeetingLogEntry`, and `CeoDecisionRecord` — plus two genuinely
new context fields, computed fresh at the moment the trade closes:

- **`marketRegime`** reuses `app/market_intelligence.py`'s own
  already-live `MarketIntelligenceState.regime` — the same regime a
  `TradeProposal` and the Trade Gatekeeper actually read.
- **`liquidityContext`** calls `compute_liquidity()` fresh for the
  trade's own symbol, using the same `PROPOSAL_TIMEFRAME`/
  `PROPOSAL_CANDLE_COUNT` convention `app/devils_advocate.py` already
  established, never a second liquidity engine.

Both are honestly documented as "as of trade close," not "as of the
original decision" — nothing in this codebase stamps either onto a
proposal or decision at the moment it's made, so claiming otherwise
would misrepresent what's actually being measured.

**Evidence Score vs. Confidence Score are genuinely different numbers,
not two labels for the same one.** `DecisionConfidence` has 6 weighted
factors; `compute_evidence_score()` is a real renormalized weighted
average over just the 3 evidence-oriented ones (Technical Alignment,
Research Confidence, News/Macro/Sentiment — 45 of the original 100
weight), deliberately excluding the consensus/portfolio-state factors
(Multi-Agent Agreement, Risk Conditions, Portfolio Exposure).
`confidenceScore` remains the full, unmodified `DecisionConfidence.score`
composite.

**Capital Allocation Grade and Patience Grade reuse the existing A+–F
scale rather than inventing a second one.** `app/executive.py`'s
previously-private `_GRADE_THRESHOLDS`/`_grade_for_score` were made
public (`GRADE_THRESHOLDS`/`grade_for_score`) and applied to the
`DisciplineReview`'s own `position_sizing_discipline`/`patience` factor
scores.

**`compute_trade_report_card()`** is a pure relabeling of one vault
entry's own real fields — Evidence/Confidence/Capital
Allocation/Decision/Discipline/Patience grades, `overallTradeQuality`
(deliberately the same value as `decisionGrade`, not a third invented
composite), `wouldTakeAgain`, and a templated `recommendation`.
`wouldTakeAgain` is a real, checkable rule: `true` only when Decision
Grade clears the company's B- bar (the same `GRADE_THRESHOLDS` band)
AND no real non-success `CaseStudy` was filed against this exact trade
— never a vibe, and three distinct recommendation strings cover which
condition (if any) failed.

**`find_similar_vault_entries()` is the Similarity Engine** — real,
rule-based tiered bucket matching, never a fabricated "94% similar"
score. It tries three tiers in order, using the first with at least
`MIN_SIMILAR_MATCHES` (3) real matches: (1) same symbol AND same market
regime AND same confidence tier; (2) same market regime AND same
confidence tier, any symbol; (3) same confidence tier alone. The
returned `matchedOn: list[str]` names exactly which real dimensions
produced the match, so the CEO always sees why trades were considered
"similar," never a black box. `summarize_similarity()` computes real win
rate, average/worst P&L, and best/worst regime by average P&L over the
matched set, and folds Mistake Prevention directly into the same result
— a `warning` (and `mostCommonMistakeCategory`) fires only when one real
non-success `CaseStudyCategory` accounts for at least
`MISTAKE_WARNING_SHARE` (30%) of the matched trades' own linked case
studies, reusing the same match set rather than a separate mechanism.

**New read-only endpoints** (`app/routers/decision_vault.py`, mirroring
`routers/sandbox.py`'s `/certification` convention exactly — `await
game_state.snapshot()`, no lock, computed fresh every call, nothing
mutates the save): `GET /api/decision-vault/report-card?vaultEntryId=`
and `GET /api/decision-vault/similar?symbol=&marketRegime=&confidenceTier=`
(with an optional `excludeId` so a just-closed trade's own vault entry
can compare itself against everything before it).

**Wiring** (`app/nexus.py`): `build_vault_entry()`/`record_vault_entry()`
run inside the existing closed-trade loop, right after that trade's
`DisciplineReview` and case-study/success-study are generated — so a
vault entry always has a real process trail to join, and never runs for
a trade with no matched `decision_id` (the same precondition Feature 26
already established). `decision_vault` is capped at
`MAX_DECISION_VAULT_ENTRIES` (200), oldest evicted first, and was added
to `save_modules.py`'s `knowledge_archive` module — the same category as
`case_studies`, a permanent, only-growing archive excluded from `GET
/api/load` and hydrated live from the WS broadcast instead.

**What's deliberately NOT here, and why:**

| Brief asks for | Why it's not built |
|---|---|
| R-Multiple | No stop-loss/initial-risk concept exists anywhere in this codebase's real risk engine — confirmed by directly reading `app/risk_engine.py`'s `recommended_quantity()`, which sizes purely off `equity * risk_per_trade_pct / 100`. (An Academy lesson's own prose claimed otherwise; checked against the actual function body and found inaccurate.) `rMultiple` is always `None`, never backfilled with a fabricated value. |
| `strategyId` on ordinary trades | Only Research Sandbox-tested strategies link back to a `Strategy` object (`app/sandbox.py`) — an ordinary Trading Floor trade never does. Always `None`. |
| Execution Grade, Psychology Grade | No real signal anywhere in this codebase measures order-execution quality separately from the decision itself, or reads literal emotion — the same honesty boundary the Probability First Trading Philosophy work already established. Not on `TradeReportCard`. |
| True NLP / natural-language search | No LLM/HTTP client dependency exists anywhere (`backend/requirements.txt`: `fastapi, uvicorn, sqlalchemy, pydantic, python-dotenv, websockets` only). A frontend built on real structured filters (symbol/regime/confidence tier/grade/date range) is the honest substitute. |
| True vector/embedding similarity | Same dependency gap — `find_similar_vault_entries()`'s real rule-based bucket matching is the honest substitute. |

**Deferred to a later slice** (each already has a real signal to build
on — this slice doesn't duplicate them, a later one can surface them):
a continuous per-employee Improvement Profile trajectory; Recurring
Mistake Detection as a real frequency/trend signal (today's `wisdom.py`
only has a plain most-common-category count, not a trend); a dedicated
Executive After-Action Review view and CEO Dashboard view (the
underlying numbers already exist in `app/company_health.py`'s Executive
tier and `app/executive_review.py`/`app/founders.py`).

**Verified**: new `tests/test_decision_vault.py` — 26 tests covering
evidence-score renormalization (including the empty-factor-list
zero-division guard), vault-entry joining/grade-fallback/cap-at-200
behavior, all three Trade Report Card recommendation branches, all
three Similarity Engine tiers plus the empty-vault fallback and
`excludeId` behavior, and the Mistake Prevention warning's share
threshold. 852/852 full backend suite passing, `mypy`/`ruff` clean.
Frontend (a Command Center surface for the Trade Report Card and
Similarity Engine) is a separate, immediately-following commit per this
project's backend-first discipline.

### Executive Decision Simulator (War Room) & Enterprise Portfolio Intelligence — Features 55 & 56, backend

GOAL (from the briefs): before risking company capital, every significant
decision should be stress-tested by a "Digital War Room" of independent
department perspectives, scored on real expected value, challenged by a
Devil's Advocate, and given a contingency plan (Feature 55) — and
TradeTown should manage its capital like a professional hedge fund: real
category/correlation exposure, a continuous portfolio-heat read, and
capital-efficiency tracking rather than one trade at a time (Feature 56).

**Naming collision, resolved up front, same pattern as Feature 54 above.**
Brief 1 self-numbers itself "Feature 54" (already in use — the Decision
Memory System, previous section); brief 2 calls itself "Feature 55" in
its own title. Both are renumbered here and in commit history —
**Feature 55** for the War Room, **Feature 56** for Portfolio
Intelligence — to avoid the collision.

**A stale local git checkout briefly caused rework, not data loss.**
Mid-session, the local branch fell behind `origin` without it being
obvious, and an entire CIO + AI Academy backend was rebuilt from scratch
before a rejected `git push` surfaced that the real, more advanced
implementation already existed upstream. Recovered via `git reset --hard`
onto the real remote tip after explicit user confirmation (including a
requested side-by-side diff showing the rebuilt modules added no unique
value). Nothing of the rebuilt work had been pushed, so nothing genuine
was lost — noted here only because it's why this slice starts cleanly
from the real `2c5f74b` history.

#### Feature 55 — War Room (`app/war_room.py`, new)

**Researched first.** Nearly everything the brief asks for already
exists as a real, separate system:

| Brief asks for | Already real, as |
|---|---|
| Digital War Room department analysis | `app/executive_intelligence.py`'s `generate_department_opinions()` / `compute_executive_recommendation()` (9 real department seats) |
| Devil's Advocate | `app/devils_advocate.py`'s `generate_challenge_report()` (already assigns one real employee per proposal) |
| 12-scenario multi-scenario simulation | `app/whatif.py`'s `run_whatif_simulation()` (12 real bootstrap-resampled scenarios) |
| Historical comparison / "Institutional Knowledge Graph" | `app/decision_vault.py`'s `find_similar_vault_entries()` / `summarize_similarity()` |
| Evidence Score vs. Confidence Score | `app/decision_vault.py`'s `compute_evidence_score()` + `app/confidence.py`'s `DecisionConfidence` — "confidence may never exceed evidence" already holds by construction |

**Scenario mapping.** The brief names 12 scenarios; `app/whatif.py`
already has 12, built for the identical "stress-test a trade candidate"
purpose. Rather than build a second scenario engine (exactly the kind of
duplication this codebase's own rule forbids), they're mapped directly:

| Brief's scenario | whatif.py's real equivalent |
|---|---|
| Best Case | `best_case_scenario` (whichever real scenario has the highest reward range) |
| Expected Case | `baseline` (organic, unbiased resample) |
| Worst Case / Difficult Case | `worst_case_scenario` / `bearish_reversal` |
| Black Swan | `flash_crash` |
| High Volatility | `high_volatility` |
| Low Liquidity | `liquidity_sweep` |
| Trend Continuation | `bullish_continuation` |
| Trend Reversal | `trend_failure` |
| Range Expansion | `breakout_confirmation` |
| Range Compression | `sideways_consolidation` |
| News Shock | `news_shock` |

(`whatif.py` additionally has `low_volatility`/`gap_up`/`gap_down`, real
extras beyond the brief's own list — kept, not trimmed, since cutting a
working real signal to match a brief's exact count would be its own kind
of dishonesty.)

**This slice's real, novel job** is exactly three things that genuinely
didn't exist anywhere:

1. A permanent **`WarRoomSession`** (`build_war_room_session()`) that
   JOINS all of the above into one addressable record per new
   `TradeProposal` — department opinions, the executive recommendation,
   the What-If simulation, the Decision Vault similarity summary,
   expected value, decision score, and contingency plan, all in one
   place.
2. A real **Expected Value / Statistical Edge / Risk-to-Reward** read
   (`build_expected_value_analysis()`) — the probability-weighted
   midpoint of every one of the 12 real scenarios' reward ranges, edge
   measured against the organic unbiased baseline, and Risk-to-Reward as
   a real reward/drawdown-magnitude ratio. Deliberately labeled
   **Risk-to-Reward, not "R-Multiple"** — no stop-loss/initial-risk basis
   exists anywhere in this codebase's real risk engine to measure R
   against (`app/risk_engine.py`'s `recommended_quantity()` sizes purely
   off equity%, the same gap `DecisionVaultEntry.rMultiple` already
   documents).
3. A real, signal-grounded **Contingency Plan**
   (`build_contingency_plan()`) — 5 IF/THEN steps, each tied to a real
   signal already computed for this symbol this tick (Guardian's
   liquidity-sweep read, market regime, news risk level, Market Quality
   tier), each carrying a real `triggered` flag for whether that
   condition is live right now, never an invented playbook.

**Decision Score** (`build_decision_score()`) is a composite over 7 real
sub-scores — Evidence, Confidence, Risk (tiered off Guardian's own
per-symbol warnings), Expected Value (a bounded linear map off Expected
Value %), Market Quality, Liquidity Quality, and Portfolio Compatibility
(penalized per already-open correlated position, reusing the same
category-concentration signal `app/gatekeeper.py`'s `_correlation_check()`
already computes) — checked against `DECISION_SCORE_THRESHOLD` (70.0),
the same "good decision" bar `app/discipline.py`'s `tier_for_score()` and
`app/executive.py`'s `compute_decision_grade()` already use.
`strategyHealthScore` is always `null`: no ordinary Trading Floor
proposal links back to a tested Strategy, so the composite renormalizes
over only the 7 real sub-scores that exist rather than substituting a
fabricated placeholder.

`evidence_never_exceeds_confidence()` computes (not hardcodes) the
"confidence may never exceed evidence" invariant, so a future change that
ever broke it would show up honestly. `compare_scenario_to_outcome()`
fills in `WarRoomSession.outcomeComparison` once the linked trade
actually closes — finds whichever real scenario's predicted range
midpoint sits numerically closest to what actually happened, then reports
whether the real outcome landed inside that scenario's own predicted
range. Never a claim that the scenario "predicted" the trade — only a
real, honest after-the-fact comparison.

**What's deliberately NOT here, and why:**

| Brief asks for | Why it's not built |
|---|---|
| Literal R-Multiple | Same gap as `DecisionVaultEntry.rMultiple` — no stop-loss/initial-risk unit exists anywhere in the real risk engine. |
| Historical Expectancy per ordinary trade | Only exists at the Strategy-aggregate level (`app/strategy_lab.py`'s expectancy); no ordinary Trading Floor proposal links to a tested Strategy. |
| Auto-failing negative-EV trades / any automatic corrective action | `docs/ROADMAP.md`'s own documented v0.8 stop condition: "risk is measured and displayed, never auto-hedged or auto-corrected without the player." `DecisionScoreBreakdown.passed` is a real, visible flag the CEO sees, never an automatic veto. |
| LLM-generated analysis text | No LLM/HTTP client dependency exists anywhere (`backend/requirements.txt` has none) — every string is templated from real computed values, the same convention every other module in this codebase uses. |

**Wiring** (`app/nexus.py`): a `WarRoomSession` is built eagerly inside
the existing per-new-proposal loop, the same "ready the instant Executive
Voting opens" convention `Debate` (Feature 17) and `ChallengeReport`
(Feature 41) already use — never computed lazily on request. Once a
linked trade closes, the closed-trades loop finds that proposal's session
and fills in its `outcomeComparison`. `war_room_sessions` is capped at
`MAX_WAR_ROOM_SESSIONS` (60), oldest evicted first, and added to
`save_modules.py`'s `knowledge_archive` module alongside `decision_vault`.

#### Feature 56 — Enterprise Portfolio Intelligence (`app/portfolio_intelligence.py`, new)

**Researched first.** `app/portfolio.py`'s `PaperPortfolio` has no
sector/correlation/heat field anywhere; `app/risk_engine.py`'s
`evaluate_guardian_exposure()`/`monitor_portfolio()` cover per-symbol
concentration and drawdown-limit breaches, and `app/gatekeeper.py`'s
`_correlation_check()` is a real but narrow category-co-occurrence gate —
none of it is a real correlation coefficient, a heat score, or a
capital-efficiency read. This slice is almost entirely genuinely new,
built on top of those existing signals.

"Sector" is called **"category"** throughout — this codebase has no real
sector taxonomy (the same honest note `app/risk_engine.py`'s
`evaluate_guardian_exposure()` docstring already makes); every symbol's
only real classification is its `ResearchCategory`
(`app/watchlist.py`'s `SYMBOL_CATEGORY`, reused directly rather than
inventing a second taxonomy).

**Correlation Intelligence** (`_correlation_pairs()`) is a **real
Pearson correlation coefficient** (`statistics.correlation()`), computed
from each pair of currently-held symbols' own real recent
candle-to-candle returns — the same `Candle` series every other
technical read in this codebase already uses. Only pairs clearing
`CORRELATION_CLUSTER_THRESHOLD` (0.6) are reported, so a portfolio of
genuinely unrelated positions honestly reports none — never an invented
relationship.

**Portfolio Heat** (`_heat()`) is a real, visible **reading** across four
tiers (cool/warm/hot/overheated), driven by real total-capital-at-risk,
largest-position%, and category concentration — never an automatic
corrective action, per the same v0.8 stop condition Feature 55 cites
above. Nothing in this module places, closes, or resizes an order.

**Capital Efficiency** (`_capital_efficiency()`) is real profit-per-dollar
and profit-per-dollar-hour, averaged only over
`portfolio.trade_history`'s actually-closed trades — never a
forward-looking prediction. **Max Drawdown is deliberately NOT
duplicated here**: `app/analytics.py`'s `PerformanceSnapshot.max_drawdown_pct`
already computes this per period (daily/weekly/monthly/all_time) from the
same trade history — a future Executive Portfolio Dashboard should read
that existing field, not a second one computed here.
`PortfolioHeat.unrealizedDrawdownPct` is a distinct, live/current-tick
reading (`abs(total_pnl_pct)` when negative), not a re-implementation of
historical max drawdown.

**Opportunity Cost** (`_opportunity_cost()`) is four real templated
branches off cash percentage and pending-proposal count — high cash with
pending proposals names the real count; high cash with none reads as
deliberate patience; low cash warns about little room to act; the
balanced middle reports no immediate concern. Never generic filler.

**Wiring** (`app/nexus.py`): `portfolio_intelligence` is recomputed fresh
every tick, right after `academy_state`, the same "cheap to recompute,
never a stale second copy" convention `company_health`/`market_intelligence`
already use. Added to `save_modules.py`'s `derived` module.

**No new API router for either feature.** Unlike Decision Vault's
report-card/similar-trades endpoints (parametrized, on-demand lookups
over an existing archive), a `WarRoomSession` and `PortfolioIntelligence`
are each already fully computed and present in the regular WS tick
broadcast — there's no additional query shape either feature needs
served separately. `ws_manager.py`'s `build_state_message()` and
`save_modules.py`'s module map were both updated proactively in the same
edit pass as the schema changes, having already been bitten once by
exactly this class of wiring gap (see Feature 54's frontend work).

**Verified**: new `tests/test_war_room.py` (27 tests: expected-value/
edge/risk-to-reward math, decision-score composite and threshold
behavior, all 5 contingency-plan branches, the confidence-never-exceeds-
evidence invariant, predicted-vs-actual outcome comparison in both the
in-range and out-of-range cases, end-to-end session assembly, and session
capping) and `tests/test_portfolio_intelligence.py` (32 tests: real
Pearson correlation including the &lt;3-points and zero-variance guards,
category-exposure grouping/sorting, all four Portfolio Heat tiers,
capital-efficiency averaging including the zero-capital-locked guard, all
four opportunity-cost branches, and an end-to-end computation with real
correlated open positions). 911/911 backend tests passing, `mypy`/`ruff`
clean. Frontend (Command Center surfaces for the War Room and a Portfolio
Intelligence dashboard) is a separate, immediately-following commit per
this project's backend-first discipline.

#### Frontend

`types.ts` mirrors every new schema (`ExpectedValueAnalysis`,
`ContingencyStep`, `DecisionScoreBreakdown`, `ScenarioOutcomeComparison`,
`WarRoomSession`, `CategoryExposure`, `CorrelationPair`, `PortfolioHeat`,
`CapitalEfficiency`, `PortfolioIntelligence`), and both new fields are
wired through the full data-layer pipeline (`socket.ts` ->
`NexusManager.ts` -> `EventBus.ts` -> `gameStore.ts`) — `warRoomSessions`
follows the same capped-archive diff-and-emit pattern `decisionVault`
already uses (only emits when the array length changes), while
`portfolioIntelligence` follows the same recomputed-every-tick pattern
`companyHealth`/`marketIntelligence` already use (emits on reference
change).

**WARROOM tab** (`WarRoomPanel.tsx`): a session list (newest first) next
to a detail view showing the Decision Score's 7 real sub-scores against
the shared 70-point bar (with `strategyHealthScore` honestly rendered as
"n/a — not a tested strategy" rather than a fake number), the Expected
Value/edge/risk-to-reward numbers, the real Contingency Plan (each step
shows a live "TRIGGERED NOW" pill when its real condition is currently
true), the Institutional Knowledge Graph's similar-trade summary, every
department's real opinion, and — once the linked trade closes — the real
predicted-vs-actual outcome comparison.

**PORTFOLIO tab** (`PortfolioIntelPanel.tsx`): Capital Allocation
(equity/cash/deployed split plus the real opportunity-cost read),
Portfolio Heat (a color-coded reading across the four real tiers, with
an explicit "a reading, never an automatic action" label so the CEO
never mistakes it for a control), Category Exposure (a real per-category
meter, this codebase's honest "sector" stand-in), Correlation
Intelligence (real Pearson-correlated pairs among currently-held symbols
only — an explicit, honest empty state when none clear the threshold,
worded as "this portfolio's real exposure is genuinely diversified right
now" rather than a blank list), and Capital Efficiency (real
profit-per-dollar / profit-per-dollar-hour over actually-closed trades
only).

**Verified**: `commandCenter.spec.ts`'s existing "renders all N tabs"
sweep extended to 34 tabs (was 32), plus two new dedicated tests —
WARROOM (asserts either the honest empty state or a real session's
Decision Score/Expected Value/Contingency Plan) and PORTFOLIO (asserts
Capital Allocation, a real heat tier, and either real category exposure
or the honest empty state) — following the same "always real content or
an honest empty state" pattern every other archive/derived-state tab
test already uses. `tsc -b --noEmit`, `eslint --max-warnings 0`, and
`vite build` all clean; targeted Playwright tests (WARROOM, PORTFOLIO,
and the extended 34-tab sweep) pass against the live Vite + FastAPI
stack.

### Institutional Position Sizing & Capital Deployment Engine — Design Bible Chapter 57, backend

GOAL (from `docs/DesignBible/volumes/09-departments/chapter-57-position-sizing-capital-deployment.md`,
written first per Appendix G's "design before code" policy): position
size should be justified by evidence, probability, and portfolio
context — never emotion, confidence alone, or a flat percentage.

**Researched first.** Position sizing was exactly two flat
percent-of-equity numbers (`app/risk_engine.py`'s
`recommended_quantity()`: `min(risk_per_trade_pct, max_position_pct)` of
equity), with no regard for how strong the evidence behind a specific
trade actually was. That function is not duplicated — its output becomes
this engine's ceiling, a hard cap `app/position_sizing.py`'s new
`build_position_sizing()` only ever narrows, never widens. Every input it
reads already exists elsewhere: the Sizing Score is War Room's own
`DecisionScoreBreakdown.overall` (Feature 55), Portfolio Heat is Feature
56's `PortfolioHeat` (the entering tick's already-computed reading — one
tick, 5 sim-minutes, stale by the time a same-tick proposal is sized, the
same tradeoff every other same-tick consumer of a recomputed-fresh signal
in this codebase already accepts), and risk warnings are Sentinel/
Guardian's existing `RiskWarning` severity.

**Four real, independent constraints**, each named honestly in the
result's `detail` string when it binds:

1. **Position Tier fraction** — a four-tier system (`exploratory` /
   `standard` / `high_conviction` / `institutional`, gated by Sizing
   Score plus Expected Value's `positive_expectancy` plus Portfolio
   Heat's tier, with Institutional additionally requiring
   `decision_score.passed` and no active critical risk warning for the
   symbol) scales the ceiling by `TIER_FRACTION` (0.35 / 0.70 / 0.90 /
   1.0). **Design correction made before shipping**: an earlier version
   scaled by an *absolute* per-tier percentage
   (`RiskLimits.tier_allocation`) competing via `min()` against the
   ceiling — but that can only ever bind if a CEO happens to set it below
   `risk_per_trade_pct`'s own ceiling, which silently made "weaker
   evidence, smaller position" a no-op for every tier below
   Institutional. A live-simulation smoke test (2000 ticks, Executive
   mode) surfaced this directly. Fixed by scaling the ceiling
   *multiplicatively* by tier first; the absolute `tier_allocation`
   per-tier cap remains underneath as a separate, real, independently-
   meaningful CEO guardrail.
2. **Real spendable weekly Risk Budget** — `RiskLimits.max_weekly_deployment_pct`
   (new, default 15%), checked against `_capital_deployed_pct_in_window()`:
   real capital newly committed (both closed `trade_history` and still-
   open `positions`) in a trailing 7-sim-day window, as % of equity.
   Genuinely new — `max_daily_loss_pct` was always a static realized-loss
   halt threshold, never a decrementing deployment budget.
3. **Optional CEO-set Portfolio Heat cap** — `RiskLimits.portfolio_heat_cap_pct`
   (new, `None` by default — today's read-only-heat behavior is
   unchanged). Deliberately CEO-set and CEO-triggered only, never
   system-triggered or auto-corrective, to stay inside the documented
   v0.8 stop condition ("risk is measured and displayed, never
   auto-hedged... without the player").
4. **Cash reserve requirement** — `RiskLimits.cash_reserve_pct` (new,
   default 10%): the engine never proposes spending into the reserve.

**Integration bug found and fixed.** `recommended_quantity()` is called
from two places: `app/nexus.py`'s `_generate_trade_proposals()` (the
initial ceiling at proposal-creation time, where `build_position_sizing()`
is now also called and the result stored on the new
`WarRoomSession.position_sizing`) and `app/executive.py`'s
`resolve_proposal()` (a fresh ceiling recomputed at execution/approval
time, since portfolio state may have changed). `resolve_proposal()` was
recomputing quantity from scratch and completely ignoring the resized
`proposal.quantity` — the whole engine had zero real effect on actually
executed trades until fixed to `min(fresh_ceiling, proposal.quantity)`,
which preserves both the evidence-based narrowing and the pre-existing
"always recompute fresh, never trust a stale number" guarantee an
existing test (`test_zero_quantity_falls_back_to_wait`) relies on.

**Explicitly not built** (see the chapter's own Implementation Notes for
the full reasoning): Position Scaling/Reduction on already-open positions
(would need each position's entry-time evidence score stored, which
`PaperPosition` has no field for — separate future work); Day/Swing/
Hybrid allocation splits (this codebase has one real trading mode; a
control that changes a label but nothing behavioral would violate the
"no placeholder systems" rule); auto-executing any reduction.

**Verified**: `backend/tests/test_position_sizing.py` (25 tests — the
weekly-window's boundaries and both trade/position sources, every tier
gate individually including the critical-warning override and all three
Institutional gates failing independently, and `build_position_sizing()`
end-to-end: the ceiling never widened, each of the four constraints
independently binding and correctly named, the tier-fraction
monotonicity guarantee itself, and the zero-equity/zero-ceiling early
return). Full backend suite: 936/936 passing (confirming the
`executive.py` fix didn't regress anything else), `mypy`/`ruff` clean.

#### Frontend

`types.ts` mirrors `TierAllocationLimits`, the six new `RiskLimits`
fields, `PositionTier`, and `PositionSizingResult`.
`WarRoomSession.positionSizing` needed no new data-layer plumbing —
`WarRoomSession` already flows through `socket.ts` -> `NexusManager.ts`
-> `EventBus.ts` -> `gameStore.ts` as one whole object per session, so
adding a field to the interface was sufficient.

The **WARROOM tab** (`WarRoomPanel.tsx`) gained a Position Sizing block
per session, shown whenever `positionSizing` is present: a tier pill
(exploratory/standard/high_conviction/institutional, color-coded), the
Sizing Score, a meter comparing `finalQuantity` against `ceilingQuantity`
(color-coded amber when narrowed, green when sized at the full ceiling —
this engine only ever narrows it, never widens it), a second meter for
the real weekly capital deployment budget used, and pills for the cash
reserve and Portfolio Heat cap gates. Every number is read directly off
`positionSizing`, nothing is recomputed client-side.

The **RISK tab** (`RiskPanel.tsx`) gained a "Position Sizing — Capital
Deployment" panel with controls for four of the six new `RiskLimits`
fields: `maxWeeklyDeploymentPct`, `portfolioHeatCapPct` (with an
explicit Enabled/Disabled checkbox, since `null` disabled vs. a real
cap enabled needs a real UI distinction, not just an empty input),
`cashReservePct`, and the four `tierAllocation` per-tier caps.
`scalingAggressivenessPct`/`emergencyReductionHeatPct` are deliberately
NOT exposed as controls — see the backend section above for why (no
real consumer exists yet, so a control that changed them would be a
placeholder).

**Backend write path extended.** `POST /api/risk-limits`
(`app/routers/risk.py`, `app/state.py`'s `update_risk_limits()`) gained
four new optional fields plus an explicit `clearPortfolioHeatCap`
boolean flag — needed because `portfolioHeatCapPct: number | null` alone
can't distinguish "this field was omitted from the request" from "the
CEO wants to disable the cap" (both look identical on the wire); the
flag resolves the ambiguity and wins even if a value is also present in
the same request. Validation: `maxWeeklyDeploymentPct`/
`portfolioHeatCapPct` must be positive when provided, `cashReservePct`
must be `>= 0` and `< 100`, every `tierAllocation` tier must be
positive.

**Verified**: 11 new `backend/tests/test_state.py` cases covering each
new field, the clear-flag's precedence over a same-request value, and
each validation boundary — full backend suite 947/947 passing,
`mypy`/`ruff` clean. `tsc --noEmit`, `eslint --max-warnings 0`, and
`vite build` all clean. Two new Playwright tests against the live Vite +
FastAPI stack: one confirms the WARROOM tab's Position Sizing block
renders for a real session (extending the existing WARROOM test rather
than duplicating it), one confirms the RISK tab's Position Sizing
controls round-trip a real save (enables the heat cap, changes the
weekly deployment budget, saves, confirms no validation error and the
value persists).

### Institutional Trade Filter & Opportunity Gatekeeper — Design Bible Chapter 58, backend

GOAL (from `docs/DesignBible/volumes/09-departments/chapter-58-trade-filter-opportunity-gatekeeper.md`,
written first per Appendix G's "design before code" policy): TradeTown
should never feel pressured to trade — reject poor opportunities before
they ever reach the CEO, not just filter what the CEO already sees.

**Researched first — this is not a new scoring engine.** Chapter 55's
War Room already computes exactly the 0-100 "Trade Quality Score"
composite the chapter's brief calls for
(`app/war_room.py`'s `DecisionScoreBreakdown.overall`, checked against
a real threshold) and a real, probability-weighted Expected Value read.
**The real gap**: both were purely informational — computed only
*after* a candidate already became a CEO-facing `TradeProposal`, with
`app/nexus.py`'s only real pre-proposal filter being a single
confidence threshold. Feature 20's existing `app/gatekeeper.py` is a
real, separate, *later*-stage check (after the CEO's own buy/sell
choice, against a different checklist) — this chapter adds a new,
*earlier* sibling in the same pipeline, not a replacement.

**`app/opportunity_gatekeeper.py`'s `evaluate_opportunity()`** is the
engine's one real decision: gate on `decision_score.overall` and
`expected_value.expected_value_pct` (both already computed by War Room)
against two new `RiskLimits` fields — `min_trade_quality_score` (default
70.0, matching today's fixed bar's own default value, but a genuinely
separate CEO-adjustable field; `DECISION_SCORE_THRESHOLD` itself is
untouched, keeping its existing meaning for every other consumer) and
`min_expected_value_pct` (default 0.0, equivalent to requiring
`positive_expectancy` at default settings, but a real floor the CEO can
raise) — plus the existing Market Quality `avoid_trading` tier.

**Wired into `app/nexus.py`'s restructured per-candidate loop.**
Previously, `trade_proposals`/`debates` were appended/generated
*before* each candidate's Challenge Report and War Room session were
even built. Now the loop, for each raw candidate: generates its
Challenge Report and full War Room session first (unchanged from
before this chapter — department opinions, the 12-scenario simulation,
Decision Score, Expected Value, all real), then calls
`evaluate_opportunity()` using that session's own real
`decisionScore`/`expectedValue`. A rejection builds a new
`OpportunityRejection` and the loop `continue`s — the candidate is never
appended to `trade_proposals`, never gets a Debate, and its Challenge
Report/WarRoomSession are simply discarded rather than persisted (the
CEO never sees it, so keeping an orphan record referencing a proposal
that doesn't exist would serve no purpose). `trade_proposals`,
`debates`, and the "new trade proposal" news items are now built once,
after the loop, only over the approved candidates.

**Design decision: gate after the session is built, not before.**
Building the full War Room session (department opinions, a Devil's
Advocate Challenge Report) for a candidate that might get rejected is a
small, bounded, accepted CPU cost — the alternative, a second
lighter-weight computation of Expected Value used only for gating,
would risk drifting from the "official" number shown in the WARROOM tab
for an approved candidate: `app/whatif.py`'s bootstrap resampling is
genuinely randomized per call (no fixed seed), so calling it twice for
the same candidate could legitimately produce two different Expected
Value reads. Computing it exactly once and either keeping or discarding
the result is the only way to guarantee the gate's number and the
CEO-visible number are always identical. This is the same "cheap, close
enough, documented" tradeoff precedent Chapter 57's own Portfolio Heat
staleness note already established for this codebase.

**A new, honestly-separate rejection record.** `OpportunityRejection`
(`app/schemas.py`) mirrors Feature 20's `GatekeeperRejection` shape but
cannot reuse it directly — a rejected candidate here never had a real
CEO choice (`GatekeeperRejection.ceoChoice`), so `OpportunityRejection`
records the desk's own `overallRecommendation` as
`wouldHaveRecommended` instead, plus the real Decision Score/Expected
Value that failed the gate (kept on the record itself, since no
WarRoomSession survives for a rejected candidate to cross-reference).
Graded by `grade_opportunity_rejections()` — the exact same real
would-have-won/would-have-lost logic
`app/gatekeeper.py`'s own `grade_gatekeeper_rejections()` already uses
(reusing its `GATEKEEPER_EVAL_WINDOW_MINUTES` directly rather than a
second magic number), purely from the symbol's own real subsequent
watchlist price movement, never a fabricated P&L. A `wouldHaveRecommended`
of `"wait"` has no real direction to grade against and is deliberately
left `"pending"` forever rather than arbitrarily treated as a `"sell"`.

**Explicitly not built in this pass**: promoting
`app/gatekeeper.py`'s hardcoded `MAX_CORRELATED_POSITIONS` to a real
CEO-configurable field (a genuinely separate, small change to Feature
20's own module, not required to close this chapter's specific gap);
News/Volatility Sensitivity controls (no real economic calendar
exists); Maximum Swing/Day Position controls (no real distinct trading
modes exist); a real "Capital Saved Through Rejections" dollar figure
beyond an honestly-labeled estimate.

**Verified**: `backend/tests/test_opportunity_gatekeeper.py` (16 tests —
every gate branch individually including multiple simultaneous
failures, the CEO-configured thresholds actually being consulted rather
than hardcoded, real field mapping on the rejection record, and every
grading branch: the window boundary, both buy/sell directions, the
"wait" no-op, a missing watchlist price, and an already-resolved
rejection left untouched). Full backend suite: 963/963 passing,
`mypy`/`ruff` clean. A live-simulation smoke test (2000 ticks, Executive
mode) confirmed the real effect: `war_room_sessions`/`debates`/
`challenge_reports` stayed in exact 1:1 sync (60/60/60 — proving no
orphaned records for rejected candidates), 100 real
`OpportunityRejection`s accumulated and were correctly capped, grading
correctly resolved buy/sell directions while leaving every "wait"
permanently pending, and Feature 20's own separate `gatekeeperRejections`
kept firing independently and unaffected (5 in the same run) —
confirming the two gates genuinely coexist rather than one silently
replacing the other.

#### Frontend

`types.ts` mirrors `OpportunityRejection` and the two new `RiskLimits`
fields (`minTradeQualityScore`, `minExpectedValuePct`).
`opportunityRejections` was wired through the full data-layer pipeline
(`socket.ts` -> `NexusManager.ts` -> `EventBus.ts` -> `gameStore.ts`),
the same capped-archive diff-and-emit pattern `gatekeeperRejections`
already uses.

The **EXECUTIVE tab** (`ExecutivePanel.tsx`) gained a new "Opportunity
Gatekeeper" panel alongside the existing "Trade Gatekeeper" one. A new
`computeOpportunityGatekeeperStats()` (`derive.ts`) is a deliberately
separate function from the existing `computeGatekeeperStats()` — there
is no "approved" count to report the way Feature 20's stats have one,
since an approved candidate simply becomes an ordinary `TradeProposal`
with no distinguishing marker; only rejections (the one thing this
engine actually persists) are counted. The panel shows real total/
resolved/pending counts, a rejection-accuracy percentage (the same real
"would it have worked?" self-evaluation Feature 20's own veto accuracy
already establishes), and a recent-rejections list showing the desk's
own `wouldHaveRecommended` direction, the real Decision Score/Expected
Value at rejection time, and the top failed reason.

The **RISK tab** (`RiskPanel.tsx`) gained a "Opportunity Gatekeeper"
panel with controls for the two new `RiskLimits` fields.

**Backend write path extended.** `POST /api/risk-limits`
(`app/routers/risk.py`, `app/state.py`'s `update_risk_limits()`) gained
the two new fields as part of this same pass (unlike Chapter 57's own
two fields, which were deferred to their own frontend pass — Chapter
58's write path was small enough to build alongside the UI).
`minTradeQualityScore` is validated into `[0, 100]`;
`minExpectedValuePct` deliberately has no range check — a CEO can
legitimately set it negative to relax the gate below "merely positive",
and 0 or lower is a real, intentional configuration, not an error.

**Verified**: 6 new `backend/tests/test_state.py` cases covering both
new fields and their validation boundaries — full backend suite
969/969 passing, `mypy`/`ruff` clean. `tsc --noEmit`, `eslint
--max-warnings 0`, and `vite build` all clean. Two new Playwright tests
against the live Vite + FastAPI stack: one confirms the RISK tab's
Opportunity Gatekeeper controls round-trip a real save, one confirms
the EXECUTIVE tab renders either a real rejection or the honest empty
state.

### Capital Priority & Opportunity Cost Engine — Design Bible Chapter 59

GOAL (from `docs/DesignBible/volumes/09-departments/chapter-59-capital-priority-opportunity-cost.md`,
written first per Appendix G's "design before code" policy): "Good
trades deserve consideration. Great trades deserve capital." Chapter 58
already decides whether a candidate earns a `TradeProposal` at all;
this chapter decides the *order* capital is offered to the ones that
did — highest quality first, never first-come-first-served, closing the
exact gap Chapter 58's own Implementation Notes flagged as unbuilt.

**Researched first — reuses, does not duplicate.** The brief's own
Priority Score factor list (Expected Value, Evidence, Risk, Portfolio
Compatibility, Market Quality, Liquidity...) is, factor-for-factor, the
same real composite `app/war_room.py`'s `DecisionScoreBreakdown.overall`
already is. The honest design is to reuse it directly rather than invent
a second, competing composite from the same underlying signals — the
same reuse precedent Chapters 57 and 58 already established.

**`app/capital_priority.py`** is the new module, three functions:
`priority_score()` looks up a proposal's own linked `WarRoomSession` by
`proposalId` (the same lookup pattern `app/nexus.py`'s outcome-comparison
step already uses) and returns its `decisionScore.overall`, or `None` if
somehow unlinked. `rank_trade_proposals()` stable-sorts the pending
queue by that score, highest first, with any unscored proposal (should
never happen — every proposal reaching `trade_proposals` is appended
alongside its own `record_war_room_session()` call) sorting last rather
than crashing. `cash_reserve_breached()` is true once cash as a % of
equity is at or below a new CEO-set `RiskLimits.capitalReservePct` —
additive to, and layered on top of, Chapter 57's existing hard
`cashReservePct` floor (`app/position_sizing.py` still never spends into
that floor regardless of this engine; this is the CEO's own *voluntary*
choice to hold back even more).

**Wired into `app/nexus.py`'s post-Chapter-58 approved-candidate loop.**
Right after `trade_proposals = [*trade_proposals, *new_proposals]`, the
*entire* pending queue (not just this tick's new arrivals) is re-sorted
by `rank_trade_proposals()` every tick — so switching CEO controls or a
new high-quality candidate arriving mid-game re-orders the existing
backlog too, not just future proposals.

**Two new real gates in `_apply_operating_mode()`'s per-proposal loop**,
processed top-down over the now-ranked queue: `is_significant_proposal()`
(`app/executive.py`) gained an optional `priority_score` parameter — a
proposal scoring below the CEO's `minPriorityScore` floor is now
"significant" the same way a low-confidence one or an oversized position
already was, keeping it pending for the CEO in **Assisted Mode only**
(Executive Mode's whole point, unchanged, is auto-resolving everything
unconditionally — extending the gate there would contradict that mode's
own documented contract). Separately, once `cash_reserve_breached()` is
true, further BUY proposals stay pending in **both** modes — a real
capital constraint, not a significance judgment, so it applies
regardless of how hands-off the CEO wants to be, mirroring how Chapter
57's own hard `cashReservePct` floor already applies unconditionally
in both modes.

**Both new `RiskLimits` fields default to `0.0`** — unlike Chapter 58's
`minTradeQualityScore` (which matched an existing fixed constant's
default), neither `minPriorityScore` nor `capitalReservePct` replaces
prior behavior, so `0.0` is the honest "opt-in, currently a no-op" default
rather than one chosen to silently preserve some other pre-existing
number.

**Explicitly not built in this pass** (all named directly in the
chapter's own Implementation Notes): Replacement Analysis against
already-open positions (Chapter 60's job entirely — this queue only ever
holds *pending*, not-yet-capitalized proposals); Swing vs. Day
allocation ratio (no real distinct trading modes exist); "Missed
Opportunity Rate" as the brief frames it (would require knowledge of
opportunities that were never real candidates at all — fabrication, not
analysis).

**Verified**: `backend/tests/test_capital_priority.py` (12 tests —
`priority_score`'s real lookup and honest `None` for an unlinked
proposal, `rank_trade_proposals`'s sort order/stability/unscored-last
behavior, and `cash_reserve_breached`'s boundary at exactly the
reserve target plus the zero-equity edge case), plus new cases in
`backend/tests/test_executive.py` (4 — the new `priority_score` gate on
`is_significant_proposal`, including the "no score to check" honest
no-op) and `backend/tests/test_state.py` (7 — both new fields' update
and validation boundaries). Full backend suite: 985/985 passing,
`mypy`/`ruff` clean. A live 400-tick simulation smoke test with both
controls raised well above their no-op defaults confirmed real, observed
effects: the pending queue's real Priority Scores stayed sorted on every
single tick checked, proposals scoring below a raised `minPriorityScore`
were repeatedly held pending, and a raised `capitalReservePct` produced
real `cash_reserve_breached()` holds (31 of 56 checks true in one run) —
not merely reachable code paths, but observed to actually fire during
ordinary simulated play.

#### Frontend

`types.ts` mirrors the two new `RiskLimits` fields (`minPriorityScore`,
`capitalReservePct`); `net/api.ts`'s `updateRiskLimits()` accepts both.

The **EXECUTIVE tab**'s Pending Proposals list (`ExecutivePanel.tsx`)
required no client-side re-sort — the WS payload's `tradeProposals` is
the exact same list `app/nexus.py` already sorted server-side via
`rank_trade_proposals()`, so displaying it in arrival order from the
server *is* displaying it in Priority Score order. This adds a rank
number and each proposal's real Priority Score, read through a new
`priorityScoreFor()` helper (`CommandCenter/lib/derive.ts`) that mirrors
the backend's own `capital_priority.py`'s `priority_score()` lookup
exactly — matching by `proposalId` against `warRoomSessions` (already
wired through the full data-layer pipeline since Feature 55) and
reading the same `decisionScore.overall`, never a second,
independently-computed number. A proposal with no linked session (should
not happen in practice — see the backend's own note) shows the honest
"Priority N/A" rather than a fabricated score.

The **RISK tab** (`RiskPanel.tsx`) gained a "Capital Priority —
Opportunity Cost" panel with controls for the two new fields, following
the exact same per-section state/save-button/error pattern every other
RISK tab control (Chapters 57/58, Daily Trading Objectives) already
uses.

**Verified**: `tsc --noEmit`, `eslint --max-warnings 0`, and `vite
build` all clean. Two new Playwright tests against the live Vite +
FastAPI stack (`frontend/tests/commandCenter.spec.ts`): one confirms the
RISK tab's Capital Priority controls round-trip a real save, one
confirms the EXECUTIVE tab's Pending Proposals queue always renders
either a real Priority Score or the honest empty state.

### Knowledge Graph extension — Design Bible Chapter 61

GOAL (from `docs/DesignBible/volumes/09-departments/chapter-61-knowledge-graph-company-memory.md`,
written first per Appendix G's "design before code" policy): unify this
codebase's already-extensive, already-real institutional memory into one
connected graph. **Researched first, and the finding was the opposite of
most prior chapters in this volume**: Company Memory, the Decision
Vault/Trade Report Card/Similarity Engine, Pattern Recognition for both
mistakes and successes, Institutional Learning, and Company DNA's
behavioral loop were all already real — only the Knowledge Graph's own
node/edge coverage was narrower than the chapter's worked example.

**`app/knowledge_graph.py`'s `build_knowledge_graph()`** gained three
new node types, each backed by an already-real, already-persisted object
this codebase generates elsewhere — never a second, competing store:
`trade` (`DecisionVaultEntry`, one per closed trade), `case_study`
(`CaseStudy`, filed by both `app/mistakes.py` and `app/successes.py`),
and `strategy` (`Strategy`, excluding any still in the raw `idea` stage
— mirroring the existing "only `completed` research becomes a node"
filter, since an unstarted idea has no real work behind it yet). Four
new edge relations, each traced to one real, checkable field: `documented_by`
(a trade's own real `caseStudyId`, already a direct 1:1 link — matched
against the case-study id set so a trade whose linked case study was
evicted from the capped list never gets a dangling edge),
`same_symbol` (a trade and a completed research item sharing the real
symbol field — deliberately labeled descriptively, never claimed as "this
research caused this trade," since no field anywhere links a specific
ResearchItem to a specific trade), `same_category` (a Strategy and
completed research sharing the real `focusCategory`/`category`, the same
non-causal honesty boundary), and `created` (a Strategy's own real
`createdBy` agent — a literal fact, not an inference).

**Frontend needed no structural change.** `KnowledgeGraphView.tsx`'s
rendering logic is already generic over `KnowledgeNodeType` — only its
`TYPE_COLORS`/`TYPE_LABELS`/`NODE_RADIUS` lookup maps (and `types.ts`'s
mirrored `KnowledgeNodeType`/`KnowledgeEdgeRelation` unions) needed the
three new node types and four new relations added, each with a distinct
color (`trade` teal, `case_study` red, `strategy` blue) so they read at
a glance against the existing seven.

**Verified**: 8 new backend tests
(`backend/tests/test_knowledge_graph.py`'s
`TestKnowledgeGraphChapter61Extension` — each new node type appearing,
the `documented_by` edge firing only for a case study id that actually
exists in the current (capped) list, both `same_symbol`/`same_category`
matching and non-matching cases, and the `idea`-stage strategy filter).
`mypy`/`ruff` clean; full backend suite 1002/1002 passing. `tsc
--noEmit`, `eslint --max-warnings 0`, and `vite build` all clean. A live
400-tick simulation (Executive mode, to force real trades to actually
close rather than sit pending forever in the default Learning mode)
confirmed all three new node types and all four new edge relations
appear with real data via a direct in-process call to
`build_knowledge_graph()`; a second check against the running dev
server's real `GET /api/knowledge-graph` endpoint (restarted to pick up
the new code) confirmed the same, and the existing Knowledge Graph
Playwright test passed unchanged against it.

**Not built in this pass** (see the chapter's own Implementation Notes):
Knowledge Retention Rules and Knowledge Quality Score remain target
design (Pattern Detection Sensitivity was built in a following pass —
see below). `MAX_MEMORY_RECORDS` (`app/memory.py`) specifically is a
larger, separate change than promoting the Similarity Engine's own
constants, since it would require threading a CEO-configurable limit
through `app/scribe.py`'s 14 separate `record()` call sites — the
codebase's real, deliberate "one writer gateway" design.

### Pattern Detection Sensitivity CEO controls — Design Bible Chapter 61

The remaining piece of Chapter 61's CEO Controls table flagged as
"straightforward" above: two new `RiskLimits` fields,
`minSimilarMatches` (default 3) and `mistakeWarningSharePct` (default
30.0), each defaulting to the exact prior fixed constant
(`app/decision_vault.py`'s `MIN_SIMILAR_MATCHES`/`MISTAKE_WARNING_SHARE`)
so existing behavior is unchanged until the CEO adjusts them — the same
"default preserves prior behavior" pattern Chapter 58's own
`minTradeQualityScore` already established.

**`find_similar_vault_entries()` and `summarize_similarity()`** each
gained an optional parameter (`min_matches`, `mistake_warning_share`)
defaulting to the module constant — every other caller (including the
test suite's own direct calls) keeps today's exact behavior unless it
explicitly opts in. **`build_war_room_session()`** gained a required
`risk_limits` parameter threading the CEO's real, current values
through to both calls; the one real call site (`app/nexus.py`) already
had `effective_risk_limits` in scope for the Opportunity Gatekeeper
call immediately after building the session, so no new plumbing was
needed to reach it. **`POST /api/risk-limits`** extended with both
fields: `minSimilarMatches` validated to ≥ 1; `mistakeWarningSharePct`
validated to `(0, 100]` — 0% is rejected rather than silently accepted,
since a 0% threshold would fire a Mistake Prevention warning on zero
real mistakes, a meaningless "always warn" state rather than an honest
sensitivity setting.

**Verified**: 4 new tests covering the Similarity Engine's own tiering
behavior at a CEO-lowered/raised match floor (a thin tier1 winning that
would normally fall through, and vice versa) and the mistake-warning
threshold catching a share that clears a CEO-lowered bar but not the
default one; 5 new tests for the CEO write path's validation boundaries
(`backend/tests/test_state.py`). `mypy`/`ruff` clean; full backend
suite 1010/1010 passing. A live simulation (Executive mode, CEO
controls set away from their defaults) confirmed the configured values
flow through to real `WarRoomSession.similarTrades` reads without
error.

### Knowledge Retention Rules CEO control (Decision Vault slice) — Design Bible Chapter 61

The Decision Vault half of Chapter 61's Knowledge Retention Rules
control: one new `RiskLimits` field, `maxDecisionVaultEntries` (default
200), matching the exact prior fixed constant
(`app/decision_vault.py`'s `MAX_DECISION_VAULT_ENTRIES`) so existing
behavior is unchanged until the CEO adjusts it.

**`record_vault_entry()`** gained an optional `max_entries` parameter
defaulting to the module constant — every other caller keeps today's
exact behavior unless it explicitly opts in. Its one real call site
(`app/nexus.py`, immediately after a trade closes and the vault entry
is built) already had `effective_risk_limits` in scope for the
Opportunity Gatekeeper call right after it, so no new plumbing was
needed. **`POST /api/risk-limits`** extended with
`maxDecisionVaultEntries`, validated to ≥ 1.

The Company Memory half of the same control
(`app/memory.py`'s `MAX_MEMORY_RECORDS`) was deliberately NOT built in
this pass: unlike `record_vault_entry()`'s single real call site,
`app/memory.py`'s `record()` is called from 14 separate places inside
`app/scribe.py` — the codebase's real "one writer gateway" design (see
`app/memory.py`'s own module docstring) — so making that ceiling
CEO-configurable would mean threading the value through all 14 sites, a
larger, riskier change left for a separate pass.

**Verified**: 2 new tests covering the Decision Vault's own capping
behavior at a CEO-lowered and CEO-raised ceiling; 2 new tests for the
CEO write path's validation boundary (`backend/tests/test_state.py`).
`mypy`/`ruff` clean; full backend suite 1014/1014 passing. A live
`POST /api/risk-limits` call against the running dev server confirmed
both the accepted value (`maxDecisionVaultEntries: 50` echoed back) and
the rejected one (`0` → "Maximum Decision Vault Entries must be at
least 1.").

### Knowledge Retention Rules CEO control (Company Memory slice) — Design Bible Chapter 61

The change the previous section deferred as "larger, riskier" —
implemented in a separate, careful pass since it touches `app/nexus.py`'s
core `tick()` loop across many more call sites than the Decision Vault
slice did. One new `RiskLimits` field, `maxMemoryRecords` (default
200), matching the exact prior fixed constant
(`app/memory.py`'s `MAX_MEMORY_RECORDS`) so existing behavior is
unchanged until the CEO adjusts it.

**`app/memory.py`'s `record()`** gained an optional `max_records`
parameter defaulting to the module constant. **Every one of
`app/scribe.py`'s 18 wrapper functions** — the codebase's real "one
writer gateway" callers (`record_research_completions`,
`record_meeting`, `record_paper_trade`, and so on — see that module's
own docstring) — gained the same optional `max_records` parameter,
passed straight through to every internal `record()` call each wrapper
makes (some, like `record_research_completions`, call it up to three
times per invocation).

**Threading it through `app/nexus.py`** turned out to need one more
step than the Decision Vault slice: of the 20 real call sites across
these 18 wrappers, 18 sit directly inside `tick()`, where
`effective_risk_limits` was already in scope (the same pattern the
Decision Vault and Pattern Detection Sensitivity controls used). The
remaining 2 — `record_meeting` inside `_maybe_call_meeting`, and
`record_ceo_decision` inside `_apply_operating_mode` — live in helper
functions that run *outside* `tick()`'s own scope. `_apply_operating_mode`
already receives `risk_limits` as a parameter (used for other real gates
like the cash-reserve check), so its call needed no new plumbing, just
`risk_limits.max_memory_records`. `_maybe_call_meeting` gained a new
`max_memory_records: int = MAX_MEMORY_RECORDS` parameter, and its one
call site (inside `tick()`) now passes
`effective_risk_limits.max_memory_records` through. **`POST
/api/risk-limits`** extended with the field, validated to ≥ 1.

**Verified**: 3 new tests for `record()`'s own capping behavior at a
CEO-lowered and CEO-raised ceiling, in a new `backend/tests/test_memory.py`
(no test file existed for `app/memory.py` before this pass); 2 new
tests confirming a representative wrapper (`record_scanner_alert`)
actually passes its `max_records` argument through to `record()` rather
than silently keeping the module default, in a new
`backend/tests/test_scribe.py` (likewise the first test file for that
module); 2 new tests for the CEO write path's validation boundary
(`backend/tests/test_state.py`). `mypy`/`ruff` clean; full backend
suite 1021/1021 passing. A live simulation was the most important check
here, given how many real `tick()` code paths this change touches: a
`POST /api/risk-limits` call set the CEO's `maxMemoryRecords` to 20,
then a 48-simulated-hour `POST /api/time/advance` run against the
running dev server exercised research, discovery, future-trade
flagging, meetings, discussion, mentorship, Academy projects, scanner
alerts, and simulation results — the memory log came back capped at
exactly 20 real entries across nine different categories, with no
errors anywhere in the server log across the whole run.

### Knowledge Quality Score — Design Bible Chapter 61

Chapter 61's last remaining major piece: a real, three-part composite
score over a closed trade's own Decision Vault entry, computed fresh
per request (`app/decision_vault.py`'s `compute_knowledge_quality_score()`,
exposed via `GET /api/decision-vault/quality-score`) — never persisted,
matching the same "no second driftable copy" discipline the Knowledge
Graph extension already established.

**Historical Success** reuses the exact same three-tier Similarity
Engine bucket match the War Room already uses
(`find_similar_vault_entries()`), excluding the entry from its own
comparison — the real win rate of every *other* Vault entry sharing
this entry's own symbol/marketRegime/confidenceTier profile.
**Pattern Frequency** is that same bucket's match count — an honest
proxy for "how often has this kind of situation recurred," deliberately
NOT a literal usage counter, since nothing in this codebase tracks how
many times a specific entry was actually shown to the CEO in a real War
Room session (`SimilarTradesSummary` is computed fresh per request,
never logged anywhere). **Relevance** is this entry's age relative to
the Vault's own real span (oldest entry's simDay to the current sim
day) rather than an arbitrary fixed decay window — a genuinely derived
number, not a second invented constant.

`overallScore` averages whichever of the three are real numbers;
`PATTERN_FREQUENCY_CAP = 10` (reusing the exact figure
`summarize_similarity()` already uses for `SimilarTradesSummary.examples`,
rather than inventing a new one) normalizes Pattern Frequency's
contribution to the composite while the field itself still reports the
real, uncapped count. When no comparable entry exists at all (Pattern
Frequency 0), Historical Success is honestly `None` by construction —
the score falls back to Relevance alone rather than letting an empty
cohort read as poor quality, since "no precedent yet" means "not enough
evidence," not "bad."

`GET /api/decision-vault/quality-score` honors the CEO's
`RiskLimits.minSimilarMatches` — notably, the older, pre-existing
`GET /api/decision-vault/similar` endpoint in the same router does NOT
(it still reads the module's fixed default). This was left as-is rather
than "fixed": that endpoint is dead code on the frontend today
(`net/api.ts`'s `getDecisionVaultSimilar` is never called from any
component — the real `SimilarTradesSummary` reads all flow through
`WarRoomSession.similarTrades`, which already does honor the CEO
setting), so changing its behavior carries real risk for zero real
benefit.

**Frontend**: `types.ts` gained the mirrored `KnowledgeQualityScore`
interface; `net/api.ts` gained `getDecisionVaultQualityScore()`;
`DecisionVaultPanel.tsx` gained a new card, fetched alongside the
existing Trade Report Card and Similarity Engine reads, showing the
three components and the overall score (color-coded green/amber/red),
with an honest empty state when no comparable entry exists yet.

**Verified**: 6 new backend tests — no-comparable-entry fallback, the
full composite's exact arithmetic worked through by hand, the entry
excluding itself from its own comparison, Pattern Frequency staying
honest (uncapped) while `overallScore` stays bounded even with more
matches than the normalization cap, and a CEO-lowered
`minSimilarMatches` changing which Similarity Engine tier wins
(`backend/tests/test_decision_vault.py`). `mypy`/`ruff` clean; full
backend suite 1026/1026 passing. `tsc --noEmit`/`eslint`/`vite build`
all clean. A live simulation (Executive mode, 120 simulated hours
across two `POST /api/time/advance` calls) against the running dev
server confirmed real, internally-consistent scores for both an older
and a just-closed Vault entry (relevance correctly higher for the more
recent one), and a clean 404 for an unknown vault entry id, with no
server errors anywhere in the log.

**Bug found and fixed along the way**: verifying this feature's full
`npm run build` (not just `npx tsc --noEmit`, which the team had been
running alone and which does not exercise the project-reference build
check `tsc -b` performs) surfaced two real, pre-existing type errors.
`frontend/src/types.ts`'s `RiskLimits` interface was missing all four
fields the two prior Chapter 61 passes had already added to the backend
(`minSimilarMatches`, `mistakeWarningSharePct`, `maxDecisionVaultEntries`,
`maxMemoryRecords`) — a gap in this session's own prior work, now
closed. Fixing that revealed a second, older, unrelated bug that
predates this session entirely: `NexusManager.ts`'s and `gameStore.ts`'s
static default `RiskLimits` objects were both already missing two
Chapter 59 fields (`minPriorityScore`, `capitalReservePct`). Both
defaults now list every real `RiskLimits` field with its actual backend
default value. Going forward, `npm run build` — not just `npx tsc
--noEmit` — is the check that actually catches this class of error.

### Institutional Innovation Lab — Design Bible Chapter 62

Chapter 62's own research (like Chapter 61's) found the brief describes
a system that's almost entirely already real: the full 8-stage gated
pipeline (`app/sandbox.py`), Monte Carlo/Regime/Liquidity/Risk/
9-department Executive Review/Founder Approval/Certification
(`app/strategy_lab.py`), and a fully shipped 8-view Strategy Lab
frontend all predate this pass. Three pieces were genuinely new,
implemented here.

**Knowledge Integration.** `app/state.py`'s `retire_strategy()` already
nudged Company DNA on a Hall of Fame induction; it now also calls two
new `app/scribe.py` wrappers — `record_strategy_hall_of_fame_entry()`
and `record_strategy_failed_archive_entry()` — writing a real
`MemoryRecord` under the `"strategy"` `MemoryCategory` for *every*
retirement, Hall of Fame or Failed Archive alike. `"strategy"` has been
a declared category (and already listed in `app/knowledge.py`'s
`KNOWLEDGE_CATEGORIES` for the Company Knowledge Library) since long
before this chapter — nothing had ever actually recorded one. Verified
live: `POST /api/sandbox/retire` against one of the game's four seeded
strategies produced a real Failed Archive entry and a matching
`"strategy"`-category `MemoryRecord`, confirmed via `GET
/api/load/archive/knowledge_archive` (the `memory` field lives in the
`knowledge_archive` archive module — `GET /api/load` alone deliberately
returns only core modules, per that endpoint's own docstring, so
checking the wrong endpoint first briefly looked like a missing write
before this was traced to the right one).

**Innovation Budget CEO control.** `RiskLimits.maxLimitedLiveCapital`
(default $2,000, matching the prior fixed `MAX_LIMITED_LIVE_CAPITAL`)
threaded through `app/sandbox.py`'s `begin_limited_live()`, whose one
real call site (`app/state.py`'s `begin_strategy_limited_live()`)
already had `self.data.risk_limits` in scope. `POST /api/risk-limits`
extended and validated (> 0). Verified live: a CEO write to $500
persisted and echoed back correctly; a write of `0` was rejected with
"Maximum Limited Live Capital must be a positive amount."

**Experiment Tiering.** `app/strategy_lab.py`'s
`compute_experiment_tier()` classifies a strategy's own real Monte Carlo
projection — the larger in magnitude of `medianReturnPct` (upside) or
`worstCaseDrawdownPct` (downside) — into minor/moderate/major/
transformational against three honestly-arbitrary-but-declared
thresholds (`EXPERIMENT_TIER_MODERATE_PCT`/`_MAJOR_PCT`/
`_TRANSFORMATIONAL_PCT` = 10%/25%/50%), the same "conservative but
arbitrary" resolution `RiskLimits`' own docstring already uses for its
defaults. Wired into `generate_strategy_dossier()` so
`StrategyDossier.experimentTier`/`experimentTierRationale` are real
whenever a Monte Carlo result exists for that strategy, and `None`
otherwise — never guessed ahead of real evidence. `StrategyCertificationView.tsx`
shows it as a tone-coded badge (`experimentTierTone()` in `derive.ts`)
next to the Monte Carlo Testing card. Verified live: `GET
/api/sandbox/dossier` for a strategy with a real (placeholder-sourced,
per this codebase's own honesty boundary on backtest data) Monte Carlo
result returned `"transformational"` with a rationale citing the real
641.2% magnitude driving it.

**Verified overall**: 13 new backend tests across
`tests/test_scribe.py` (Hall of Fame/Failed Archive entries become real
`"strategy"` memories, `maxMemoryRecords` respected), `tests/test_state.py`
(the retirement integration end-to-end, the Innovation Budget CEO write
path), `tests/test_sandbox.py` (Innovation Budget's ceiling behavior at
a CEO-raised/lowered cap), and `tests/test_strategy_lab.py` (each
Experiment Tier boundary, and that the larger-magnitude side drives the
classification). `mypy`/`ruff` clean; full backend suite 1039/1039
passing; `tsc --noEmit`/`eslint`/`vite build` all clean.

### Company Health tier thresholds and Benchmarking — Design Bible Chapter 63

Researched first (see the chapter's own Executive Summary): almost the
entire brief was already real (Company Health Score, Company Score,
Department Scorecards, the monthly Executive Review). This pass closed
two of the chapter's remaining CEO Controls gaps.

**Tier thresholds (backend + frontend).** `app/company_health.py`'s
`_TIER_THRESHOLDS` (85/70/50/30) are now four `RiskLimits` fields
(`companyHealthExcellentThreshold`/`GoodThreshold`/`StableThreshold`/
`NeedsAttentionThreshold`), threaded through `compute_company_health()`'s
new optional threshold parameters and applied identically to `tier`,
`executiveTier`, and `combinedTier`. `app/state.py`'s
`update_risk_limits()` validates the fully-merged candidate stays
strictly descending regardless of which subset a given call changes
(the same whole-object check `tierAllocation` already used). A real bug
surfaced and was fixed while wiring this up: the first pass only
threaded the new thresholds into `tier`, leaving `executiveTier`/
`combinedTier` still reading the old hardcoded constants — caught by a
new unit test (`TestCeoConfiguredTierThresholds::test_thresholds_apply_identically_to_executive_and_combined_tiers`)
before it ever reached the frontend. `CompanyPanel.tsx` gained a real
"Company Health Tier Thresholds" card (four number inputs, save,
validation-error display).

**Benchmarking (frontend only).** `lib/derive.ts`'s
`computeScoreBenchmark()` computes a real delta between the current and
a CEO-chosen 1x/3x/6x/12x-periods-back `ExecutiveReview.companyScore`,
reading straight off the `executiveReviews` history already retained
server-side (`MAX_EXECUTIVE_REVIEWS = 20`) and already loaded into the
client. No backend change was needed. Surfaced as a new "Benchmarking"
card in the COMPANY tab with an honest empty state when history is too
short.

**Verified**: 4 new `compute_company_health()` unit tests, 4 new CEO
write-path tests (single-field update, out-of-range rejection,
descending-order rejection, a full valid reordering in one call),
`mypy`/`ruff` clean, full backend suite 1073/1073 passing,
`tsc`/`eslint`/`vite build` clean, and live browser verification
(`TestClient` for the backend write path; a scripted Playwright session
for the frontend save/validation-error round trip).

### Company Goals — Design Bible Chapter 64

The opposite research outcome from Chapter 63: a genuine, mostly-unbuilt
gap (see the chapter's own Executive Summary — `CompanyPriority`, the
Capital Priority Engine, and `_long_term_goals()` are all real but
explicitly not substitutes). Implemented the chapter's own recommended
smallest real, independently-useful slice.

A new `app/goals.py` module: `create_goal()` builds a `Goal` from CEO
input; `validate_target_value()` rejects a non-positive target or one
above its metric's own real ceiling (100 for the two composite scores,
5 for Academy level, uncapped for portfolio return);
`resolve_metric_value()` reads the one real number each of four offered
metrics maps to (`company_health_combined`, `company_score_overall`,
`portfolio_return_pct`, `academy_level`); `tick_goal()`/`tick_goals()`
recompute every active goal's real progress every tick (wired into
`app/nexus.py`'s `tick()` right after `academy_state` is computed,
alongside `company_health`/`company_score`), transitioning a goal to
`completed` (target reached) or `expired` (deadline passed unmet) — both
permanent, matching `app/hall_of_fame.py`'s "a crossed milestone stays
crossed" convention; `cancel_goal()` lets the CEO withdraw an active
one. `POST /api/goals/create` / `POST /api/goals/cancel`
(`app/routers/goals.py`), capped at `MAX_GOALS = 20`. `CompanyPanel.tsx`
gained a "Company Goals" card (create form, real progress bars, cancel
control). Full data-layer plumbing across `types.ts`, `api.ts`,
`NexusManager.ts` (including a new `setGoals()`), `EventBus.ts`,
`socket.ts`, and `gameStore.ts` — the `goals` field threaded through the
shared `NexusSnapshot` interface used for both the initial `/api/load`
and every live WS tick.

**A real bug found via live verification, not any automated test:**
`app/ws_manager.py` builds its per-tick broadcast as an explicit
field-by-field dict, the same convention every other real list already
follows — `goals` was added to the schema, `GET /api/load` (via
`save_modules.py`'s generic module serialization), and `tick()`, but
missed here. The frontend's `goals` store field silently went from its
real initial `[]` default to `undefined` the moment the first live WS
tick landed, crashing the new Goals card with `Cannot read properties
of undefined (reading 'length')`. Diagnosed by adding temporary
`pageerror`/`console` listeners to a live Playwright session (the
screenshot alone only showed a black canvas, the same symptom this
codebase has previously traced to zombie dev-server processes — this
time it was a real code bug, confirmed by checking `ps aux` showed no
stale processes before concluding it wasn't). Fixed in its own commit
before the frontend commit that surfaced it, per this project's
backend-before-frontend discipline.

Explicitly not built, per this chapter's own scope: an Executive
Priority Engine ranking goals against each other, and Resource
Allocation recommendations.

**Verified**: 18 new `app/goals.py` unit tests, 8 new CEO write-path
tests (`create`/`cancel`, including the empty-title, non-positive-target,
past-deadline, and duplicate-cancel rejections), `mypy`/`ruff` clean,
full backend suite 1073/1073 passing, `tsc`/`eslint`/`vite build`
clean, and a live scripted Playwright session confirming goal creation,
cancellation, and the target-ceiling validation error all round-trip
correctly against the real running dev stack.

### Milestone Tracking — Design Bible Chapter 64 (second pass)

The "next honest slice" that chapter's own Implementation Notes named,
extending the existing `Goal` object with real checkpoints rather than
introducing a second tracking concept. A new `Milestone` schema (id,
`thresholdPct`, `reached`, `reachedAt`) and `Goal.milestones`.
`app/goals.py`'s `_build_milestones()` generates three fixed checkpoints
per goal (`MILESTONE_THRESHOLDS = (25.0, 50.0, 75.0)`) — no milestone
for 100%, since goal completion already tracks that real fact via
`status`. `_mark_reached_milestones()` marks a milestone permanently
reached the moment real `progress_pct` crosses it, checked both at
`create_goal()` (a goal can honestly start past a milestone if the CEO
sets a target the company already exceeds part of the way to) and every
`tick_goal()` call. A reached milestone never reverts, matching every
other "a crossed milestone stays crossed" convention already documented
in this file. `CompanyPanel.tsx`'s Goal cards render each milestone as
a filled/hollow marker with a tooltip.

A real bug surfaced and was fixed via a new test before it ever reached
the frontend: `_mark_reached_milestones()`'s first version called
`m.model_copy(update={"reached": True, "reachedAt": now})` — but
`model_copy()`'s `update` dict keys must be the model's actual Python
field names (`reached_at`), not the wire alias (`reachedAt`); the
unrecognized key was silently dropped, so `reached` flipped to `True`
while `reached_at` stayed `None` forever.
`test_tick_marks_a_newly_crossed_milestone_reached` caught it by
asserting `reached_at is not None`, the same class of "assert every
field a real state transition should touch, not just the obvious one"
discipline this test suite already practices elsewhere.

**Verified**: 6 new backend tests (creation-time milestone state,
mid-tick crossing, permanence once reached, all-reached-on-completion,
frozen-once-inactive), `mypy`/`ruff` clean, full backend suite
1079/1079 passing, `tsc`/`eslint`/`vite build` clean, and a live
scripted Playwright session confirming all three milestone percentages
render correctly for a freshly-created goal against the real running
dev stack.

### Executive Priority Engine for goals — Design Bible Chapter 64 (third pass)

The next honest slice in this chapter's own recommended sequencing: a
real, named formula ranking active goals by urgency — deliberately NOT
a reuse of Chapter 59's trade-proposal Priority Score
(`app/capital_priority.py`'s `rank_trade_proposals()`), which reads
`WarRoomSession.decisionScore`, a composite built entirely from
trade-specific signals (Expected Value, Evidence, Risk, Portfolio
Compatibility, ...) that don't exist for a goal.

New `GoalPriority` schema (goalId, score, remainingPct, daysRemaining).
`app/goals.py`'s `compute_goal_priority()` scores an ACTIVE goal (`None`
for any other status) from two real cases: with no real deadline, the
score is `100 - progressPct` alone; with a real deadline, the score is
the real pace required per day to hit it
(`remainingPct / max(daysRemaining, 1)`), clamped against a stated,
transparent ceiling (`MAX_URGENCY_PACE_PCT_PER_DAY = 5.0` — 5+
percentage points of real progress needed per real remaining day reads
as maximally urgent) and scaled into the same 0-100 range as the
no-deadline case — never a hidden weighting.
`rank_goals_by_priority()` sorts every active goal by that real score,
descending, excluding non-active goals entirely.

New read-only `GET /api/goals/priorities` (`app/routers/goals.py`),
computed fresh per request from `game_state.snapshot()`'s current real
goals and sim day — never a second persisted copy, the same convention
`GET /api/decision-vault/quality-score` already uses. Frontend: the
Company Goals card fetches real priorities (refetched via a `useEffect`
keyed on the `goals` array, so any create/cancel/tick-driven change
refreshes the ranking) and reorders active goals by real priority score
— non-active goals keep their prior most-recent-first ordering, since
there's nothing left to prioritize once a goal is
completed/expired/cancelled. Each active goal shows a real PRIORITY
badge and, when it has a real deadline, real days-remaining.

**Verified**: 13 new backend tests (non-active returns `None`,
no-deadline scoring, tight-deadline clamping to the real ceiling,
generous-deadline low urgency, a passed deadline still producing a real
score rather than dividing by zero/negative, ranking order, exclusion
of non-active goals), `mypy`/`ruff` clean, full backend suite
1086/1086 passing, `tsc`/`eslint`/`vite build` clean, and a temporary
Playwright spec (reusing the project's own real popup-dismissal
helpers from `tests/helpers.ts`, deleted after use) confirming a goal
with a 2-real-day deadline correctly ranked above an open-ended
Academy-level goal against the live running dev stack.

### Resource Allocation for goals — Design Bible Chapter 64 (fourth pass)

The last piece that chapter's own Implementation Notes had deferred
pending the Priority Engine above. The real design question, once
actually addressed: what "resource" a `Goal` even has to allocate. A
goal tracks a company-wide metric (Company Health, Company Score,
portfolio return, Academy level), not a set of open positions with a
real capital pool behind it — Chapter 56/59/60's real capital machinery
has no concept of "this goal's share of the portfolio," so inventing
one would have meant fabricating a number nothing in this codebase
tracks. The honest slice instead: a normalized share of executive
ATTENTION, not capital.

New `GoalAllocation` schema (goalId, score, allocationPct).
`app/goals.py`'s `compute_resource_allocation()` reuses
`rank_goals_by_priority()`'s own real scores directly — no second
composite — and normalizes each active goal's score against the sum of
every active goal's score, so the recommendation always sums to ~100%
across whatever active goals exist. The one real edge case (every
active goal's urgency score is exactly 0 — possible only in the narrow
window where a goal's `current_value` already meets its target but the
next tick hasn't yet flipped its `status` to `completed`) falls back to
an even split across goals rather than dividing by zero — an honest
fallback, not a fabricated number.

New read-only `GET /api/goals/allocations` (`app/routers/goals.py`),
computed fresh per request from `game_state.snapshot()`'s current real
goals and sim day — same convention as `GET /api/goals/priorities`,
never a second persisted/driftable copy, and never a claim about
moving real capital (`compute_resource_allocation()` never reads or
writes `PaperPortfolio`/`PaperBroker` — the same recommend-only
boundary Chapter 59's Priority Score and Chapter 60's Capital Rotation
already respect). Frontend: each active goal's card in the COMPANY tab
now renders a "Recommended attention" progress bar with a real %
underneath its progress meter, fetched via a `useEffect` keyed on the
`goals` array — the same refetch trigger already used for priorities.

**Verified**: 5 new backend tests (empty goal list, a single active
goal gets 100%, allocations sum to 100% and favor the more urgent goal,
non-active goals excluded, the even-split fallback when every active
goal's urgency score is 0), `mypy`/`ruff` clean, full backend suite
1091/1091 passing, `tsc`/`eslint`/`vite build` clean, and a temporary
Playwright spec (reusing the project's own real popup-dismissal
helpers from `tests/helpers.ts`, deleted after use) confirming two real
active goals against the live running dev stack both rendered a
correctly normalized 50% "Recommended attention" bar.

### Strategic Review Cycle for goals — Design Bible Chapter 64 (fifth and final pass)

The last piece named in this chapter's own Implementation Notes,
closing out its real scope entirely. Mirrors Chapter 63's own monthly
`ExecutiveReview` structure (`app/executive_review.py`) but asks a
different question: not "how is the company performing" but "how is
CEO-authored goal progress moving."

New `StrategicReview` schema (id, createdAt, activeGoalCount,
completedSinceLastReview, expiredSinceLastReview,
milestonesReachedSinceLastReview, topPriorityGoalId, topPriorityScore,
summary). `app/goals.py`'s `generate_strategic_review()` finds what
genuinely changed since the previous review by comparing each real
`Goal.updatedAt`/`completedAt` and each real `Milestone.reachedAt`
against the previous review's own real `createdAt` — a monotonic
ISO-8601 string comparison (the same timestamp format `_now_iso()`
already guarantees), never a fabricated period-over-period number.
Reuses `rank_goals_by_priority()`'s own top-ranked active goal directly
for the "current top priority" field rather than a second ranking.
`record_strategic_review()` appends the new review and caps the list at
`MAX_STRATEGIC_REVIEWS = 20`, the same convention `MAX_EXECUTIVE_REVIEWS`
already uses.

Generated on the exact same monthly evening boundary as the Executive
Review, right after it, in `app/nexus.py`'s `tick()`
(`if is_evening and new_time.day % MONTHLY_INTERVAL_DAYS == 0:`).
Wired through `app/save_modules.py`'s `"company"` module and
`app/ws_manager.py`'s explicit per-tick broadcast dict (the same spot
whose omission caused the Chapter 64 first-pass `goals` bug above —
added correctly this time). Frontend: full data-layer plumbing
(`types.ts`, `socket.ts`, `NexusManager.ts`, `EventBus.ts`,
`gameStore.ts`) and a new "Strategic Review Cycle" card on the COMPANY
tab, listing every real review newest-first with its own real summary
sentence — an honest empty state before the first monthly review
generates (no CEO write path exists for this report, matching
`ExecutiveReview`'s own read-only nature).

**Verified**: 8 new backend tests (no-previous-review baseline,
completion/expiry inclusion with no previous review, exclusion of
completions/expiries from before the previous review, milestone
counting since the previous review, top-priority reflects the real
Priority Engine, an honest empty review when no goals exist at all,
`record_strategic_review()` appending and capping), `mypy`/`ruff`
clean, full backend suite 1099/1099 passing, `tsc`/`eslint`/`vite
build` clean, a real assertion added to `commandCenter.spec.ts`'s
existing Company tab test, and live verification against the running
dev stack — advancing time to a real month boundary via
`POST /api/time/advance` produced a real review (2 goals expired unmet,
4 milestones newly reached) whose exact real summary text rendered
correctly in the Command Center.

### Chapters 65/66 — Market Regime Detection & Institutional Safety

Written per this volume's own research-first convention, from two
parallel research passes rather than assumption. Chapter 65 (Market
Regime Detection & Adaptive Strategy Engine) found two independent,
real, indicator-driven regime classifiers already exist —
`app/market_environment.py`'s 5-way threshold classifier and
`app/market_intelligence.py`'s 13-way multi-factor classifier, the
latter already computing a real `MarketQualityScore.confidence_pct`
(a genuine Regime Confidence Score) and real regime-vs-strategy
evidence matching via `app/strategy_lab.py`'s `StrategyRegimeTestReport`.
Neither engine is CEO-configurable, and neither reconciles with the
other. The chapter's smallest honest slice — reconciling the two into
one CEO-facing read — was implemented this pass; see below. Adaptive
Strategy Profiles per regime and an Automatic Adaptation mechanism
remain not yet built — nothing today lets a detected regime move any
real `RiskLimits` lever.

Chapter 66 (Institutional Safety, Capital Protection & Failsafe
Framework) found a real, live, mechanically-enforced daily circuit
breaker (Sentinel → `RiskWarning` → Trade Gatekeeper, no CEO override
possible) and a real multi-stage pre-trade veto pipeline (Position
Sizing's cash-reserve floor, Opportunity Gatekeeper's pre-proposal
veto, Trade Gatekeeper's eight-check final authority) that already
functions as the brief's "Trade Quality Override." One precise gap was
implemented this pass — see below.

### Regime Reconciliation — Design Bible Chapter 65

`app/regime_reconciliation.py`'s `compute_regime_reconciliation()`
closes Chapter 65's own scoped gap: the two real regime engines never
cross-referenced each other, and neither had a CEO-facing confidence
read to act on. The new function takes the current
`MarketEnvironmentState` and `MarketIntelligenceState` and returns an
`agreement` (`aligned`/`diverging`) by checking whether the
intelligence engine's live regime falls in the environment regime's
bucket of the existing `REGIME_CONSISTENCY_MAP` — the same mapping
`app/market_intelligence.py`'s own regime-learning loop already used
internally, promoted from a private `_REGIME_CONSISTENCY_MAP` to a
public constant rather than duplicated. It also returns a read-only
`posture` recommendation (`cautious`/`normal`/`opportunistic`): the
`avoid_trading` and `poor` `MarketQualityScore.tier`s are always
cautious regardless of confidence; `excellent`/`good` tiers become
`opportunistic` only once `confidence_pct` clears a fixed
`OPPORTUNISTIC_MIN_CONFIDENCE_PCT = 70.0` threshold; everything else
stays `normal`. A plain-language `rationale` names both engines' real
labels and the real quality tier, never a fabricated sentence.

Exposed via new `GET /api/market/regime-reconciliation`
(`app/routers/market.py`), computed fresh from `game_state.snapshot()`
on every request — never persisted as a second driftable copy of
either source engine's own state, matching this codebase's established
convention (`GoalPriority`/`GoalAllocation`, Chapter 63's Benchmarking).
Nothing writes the posture to any `RiskLimits` field — recommend-only,
the same boundary Chapter 64's Resource Allocation established.

The Command Center's Company tab now shows a "Regime Reconciliation"
card (`CompanyPanel.tsx`) directly above the existing Market
Environment card: both engines' regime labels side by side, an
agreement pill, a posture pill, the real confidence percentage, and the
rationale — fetched via a new `getRegimeReconciliation()` client method,
re-fetched whenever `marketEnvironment` changes. 8 new backend tests
(including a completeness guard over every real `MarketIntelligenceRegime`
value via `typing.get_args`), `mypy`/`ruff` clean, full backend suite
1110/1110 passing, `tsc`/`eslint`/`vite build` clean, a real assertion
added to `commandCenter.spec.ts`'s existing Company tab test, and live
verification against the running dev stack confirming the card renders
real reconciled data. The full `commandCenter.spec.ts` regression run
had one unrelated failure (a movement-key test, line 82) that
reproduces identically against the pre-Chapter-65 baseline with none of
this pass's changes present — confirmed pre-existing flakiness, not a
regression.

### AI Consensus Safety enforcement — Design Bible Chapter 66

`app/executive_intelligence.py`'s `compute_executive_recommendation()`
already set `ExecutiveRecommendation.action = "pause_trading"` when 2+
departments actively oppose a stance, or Market Intelligence reads
`avoid_trading` — a real, already-computed signal. Chapter 66's own
research confirmed, via grep, that zero code paths checked this signal
before a proposal auto-resolved: the detection was real, the pause was
not.

`app/nexus.py`'s `_apply_operating_mode()` now closes that gap. Before
auto-resolving any non-"wait" proposal, it looks up the same real
`ChallengeReport` the router's own recommendation endpoint uses,
builds the same real department opinions via
`generate_department_opinions()`, and checks
`compute_executive_recommendation(proposal, opinions).action ==
"pause_trading"`. If it fires, the proposal stays pending — in BOTH
Assisted and Executive mode. This mirrors the exact precedent the
existing cash-reserve check (`cash_reserve_breached()`) already
established: a real safety constraint applies regardless of how
hands-off the CEO's chosen Operating Mode is, never just a
mode-dependent significance judgment. It is a genuine, honest change to
what Executive Mode's own docstring used to claim ("auto-resolves
everything") — the docstring was updated to say so.

No new frontend code was needed. The CEO's existing Executive Voting
popup (`ExecutiveVoting.tsx`) already fetches and renders any
`ExecutiveRecommendation` generically via its `ExecutiveIntelligencePanel`
— `EXECUTIVE_ACTION_LABEL`/`executiveActionTone` already cover every
`ExecutiveAction` value, `pause_trading` included, and the panel
already shows the real `reason` text and the real supporting/opposing
department breakdown. A proposal that now stays pending because of
this new gate is therefore already fully explained the moment the CEO
opens it — this component predates this pass and needed no changes.

**Verified**: 3 new backend tests
(`tests/test_nexus.py::TestApplyOperatingModePauseTrading` — an
otherwise non-"significant" proposal stays pending under an
`avoid_trading` regime in Assisted mode; the same proposal stays
pending in Executive mode too, the real behavioral change this pass
makes; a normal regime still auto-resolves in Executive mode, confirming
the gate is regime-specific rather than a blanket block), `mypy`/`ruff`
clean, full backend suite 1102/1102 passing. Frontend regression-checked
via the existing `executiveVoting.spec.ts` suite against a freshly
restarted dev stack (4/5 passed on the first run; the one failure was a
pre-existing, content-dependent strict-mode text collision in an
unrelated assertion — confirmed non-deterministic and unrelated to this
change by passing cleanly on an immediate retry). Forcing the exact
`avoid_trading`/2+-opposing condition through the live UI was not
attempted, deliberately: no real CEO-facing control exists to force
that state (correctly, per this chapter's own honesty boundary), so the
3 backend unit tests are the more precise and more honest verification
of this exact branch than a contrived live click-through would be.

### TTOS Phase 1 — 7-section grouped navigation, Design Bible Chapter 67

Chapter 67 (TradeTown Operating System) is structurally different from
every other Volume 9 chapter: it describes navigation/UX architecture,
not a trading department. A dedicated research pass confirmed the
Command Center had grown to 34 real, independently-shipped tabs
rendered as one flat, ungrouped, horizontally-scrolling button row
(`FullCommandCenter.tsx`'s `TABS` constant), with three independently-
built "company overview" dashboards (QuickView, OverviewPanel,
BrainRoomHud's toolbar pull-up) and 5 more standalone overlays (Newspaper,
Company Memory, Coach Dashboard, Brain Room HUD, Campus Map) living
entirely outside the Command Center's own navigation.

Before any code was written, a full audit and migration plan was
presented — every existing tab, overlay, toolbar action, and
notification inventoried; duplicate screens named explicitly; breaking
changes flagged (renaming the 34 `Tab` identifiers would break every
`clickTab()` call across the Playwright suite; a real Emergency Stop
requires new backend enforcement, not a UI button; workspace docking
requires a new frontend dependency this codebase doesn't have) — and
approved before implementation began, per this chapter's brief's own
explicit "stop and wait for approval on breaking changes" requirement.

**What was built (Phase 1, the smallest slice from that plan):**
`frontend/src/ui/components/CommandCenter/lib/navigation.ts`'s new
`TAB_SECTION` record maps every one of the 34 real `Tab` identifiers to
one of TTOS's 7 permanent sections (Headquarters/Markets/AI Workforce/
Research/Portfolio/Operations/Archive); `groupTabsBySection()` groups
them in that order. `FullCommandCenter.tsx`'s `<nav>` now renders 7
labeled section rows instead of one flat row. Deliberately additive,
not a restructure: the `TABS` array, every `Tab` string, and every
button's visible accessible name are byte-for-byte unchanged, so
`clickTab()` (which looks buttons up by exact accessible name) and the
number-key 1-9 shortcut (which indexes into `TABS` positionally) both
keep working exactly as before — the chosen alternative to a true
identifier restructure, specifically to avoid rippling into the whole
Playwright suite for zero real user benefit.

Several tab placements are genuine judgment calls, documented directly
in `navigation.ts`'s own module docstring: TREASURY sits under
Headquarters rather than Portfolio because it's explicitly CEO-*personal*
capital (`TreasuryPanel.tsx`'s own "isolated second account" framing),
distinct from the company's own trading portfolio; OPS sits under
Research despite its name colliding with the Operations section,
because its real content (`KnowledgeBasePanel.tsx`'s Knowledge
Absorption feed) is a learning-source feed, not infrastructure.
Operations ends up real but thin — LOGS only — because Automation,
Integrations, Infrastructure, and Broker Configuration have no backing
feature anywhere in this codebase; per the chapter's own "no
placeholder pages" constraint, no stub tabs were added to fill it out.

**Deferred to their own approved phases, not assumed to follow
automatically from this slice:** dashboard consolidation (the 3
overview screens found above), universal search, the command palette,
priority-tiered notifications, a real backend-enforced Emergency Stop
(explicitly Chapter 66 territory, not a navigation change), the unified
Quick Action Dock, workspace docking, and navigation analytics.

**Verified**: `tsc`/`eslint`/`vite build` clean, live-verified against
a freshly restarted dev stack (screenshot confirming all 7 section
labels render with every original tab intact), a real assertion added
to `commandCenter.spec.ts`'s existing 34-tab test for the 7 section
labels, full `commandCenter.spec.ts` regression run.

### TTOS Part 3 — real Global Emergency Stop, Design Bible Chapter 67

Part 3's own brief asked for a Global Emergency Stop, a Safety Settings
page, a global status bar, the Quick Action Dock, a priority-tiered
Alert Center, executive dashboard/navigation polish, and command
palette expansion. Before writing code, a dedicated research pass (a
background Explore agent covering broker integration, the tick loop's
trading/research separability, `RiskLimits`' real circuit-breaker
coverage, and every command-palette example) confirmed everything past
Emergency Stop is greenfield with no real backing feature anywhere:
`app/broker.py`'s own module docstring is explicit that trading is
"completely simulated... no such adapter exists or is wired in v0.6,"
so "Open Charles Schwab" has no real destination; no "Swing Trading
Mode" or "Day Trading Mode" exists under any name; `RiskLimits` has
exactly one loss-based circuit breaker (daily-scoped) and no weekly/
monthly limit. Only Part 3's own Primary Objective — the Emergency
Stop — was implemented this pass.

**Backend** (`app/emergency_stop.py`, new): `activate_emergency_stop()`/
`resume_trading()` are pure functions transitioning a new
`EmergencyStopState` (`active`, `activatedAt`) on `GameSaveState`,
registered in `save_modules.py`'s `"company"` module. Enforcement
threads through three real sites, all in `app/nexus.py`/`app/state.py`:
`tick()` skips `_generate_trade_proposals()` entirely while active
(`nexus.py`); `_apply_operating_mode()` gained a third hard-block
condition — checked *first*, before the existing cash-reserve and
Chapter 66 `pause_trading` checks, since it's the CEO's own explicit
override of every other signal — keeping every pending proposal frozen
in Assisted/Executive mode; and `submit_ceo_decision()` in `app/state.py`
now rejects the CEO's own manual `"buy"`/`"sell"` call too (only
`"wait"` — declining a trade — is still allowed), since the brief's
"only the CEO can resume trading" reads as "nothing executes, at all,
until they explicitly resume," not just an automation-only halt.
Activating/resuming both call a new `record_emergency_stop_event()`
wrapper in `app/scribe.py`, writing a real, permanent, capped Company
Memory entry under a new `"emergency"` category — deliberately reused
as the brief's own "incident report" requirement rather than a second,
parallel record of the same event (this codebase's "reuse, don't
duplicate" convention). Two new endpoints,
`POST /api/emergency-stop/activate` and `/resume`
(`app/routers/emergency.py`), mirroring the exact
request/response/persist shape `app/routers/treasury.py`'s
deposit/withdraw already established.

Deliberately narrower than the brief on two points, both explicit scope
cuts rather than oversights: already-pending proposals are left
pending, never auto-cancelled — the brief's own "Cancel pending orders
(configurable)" line is treated as out of scope for this pass, since
force-resolving a proposal to a decision the CEO didn't actually make
is a real behavioral choice that deserves its own scoping, not a
byproduct of this one; and already-placed broker orders are never
force-closed — `tick_broker()` is untouched, so any fill already in
flight before the stop settles normally, since yanking a resting order
mid-flight risks leaving the paper portfolio in a state nothing in this
codebase was built to reconcile.

**Frontend**: a new, permanent, always-visible red "EMERGENCY STOP"
button in `TopStatusBar.tsx` — nested inside the same right-side flex
group as the existing connection-status badge (not appended as a 4th
top-level flex child, which would have broken the row's `justify-between`
layout) — never inside a Command Center tab, matching the brief's own
"must not live inside a tab" requirement. Clicking it emits a
`"ui:emergencyStopConfirm"` EventBus event rather than rendering its own
dialog inline: an `absolute inset-0` confirmation dialog needs a
full-viewport positioned ancestor, which `TopStatusBar.tsx`'s own small
flex row is not, so the actual dialog (`ConfirmDialog.tsx` — the first
reusable confirm-before-you-act component in this codebase; research
confirmed no such pattern existed anywhere, every other destructive/
high-stakes action here still fires immediately) is owned by a new
top-level `EmergencyStopConfirm.tsx`, rendered as an `App.tsx` sibling
alongside `CommandCenter`/`ExecutiveVoting`, the same "trigger event
from anywhere, top-level component owns the actual overlay" pattern
those already use. While active, the button becomes a pulsing
"EMERGENCY — RESUME TRADING" badge. Full data-layer wiring matches the
existing `RiskLimits` pattern exactly: `types.ts`, `api.ts` client
methods, an `EventBus` event + type, `NexusManager`'s static
field/getter/setter (both the immediate-update path used right after
each API call, and the two WS-tick/save-load sync paths inside
`applyServerUpdate()`/`loadFromSave()`), and `gameStore.ts`'s state +
listener + default.

**Verified**: 14 new/extended backend tests
(`tests/test_emergency_stop.py`'s 4 pure-function tests;
`tests/test_state.py`'s `TestActivateAndResumeEmergencyStop` (4) and
`TestSubmitCeoDecisionEmergencyStopGuard` (3); `tests/test_nexus.py`'s
`TestApplyOperatingModeEmergencyStop` (3), mirroring the existing
`pause_trading` test class), `mypy`/`ruff` clean, full backend suite
1124/1124 passing. `tsc`/`eslint`/`vite build` clean. Live-verified
against a freshly restarted dev stack via a temporary Playwright script
— first pass caught a real bug: the badge's active-state label
("EMERGENCY MODE — RESUME TRADING") overflowed past the viewport's
right edge, because appending `<EmergencyStopControl />` as a 4th
top-level child of `TopStatusBar.tsx`'s 3-way `justify-between` row
distorted the whole row's layout — fixed by nesting it inside the
existing connection-status group instead, and by shortening the label.
A new `frontend/tests/emergencyStop.spec.ts` exercises the real running
app end-to-end (open dialog, cancel, activate for real, confirm the
button stays visible with the Command Center open, resume for real).
`executiveVoting.spec.ts` (5/5) and the full `commandCenter.spec.ts`
regression (30/32, run sequentially against the shared dev backend —
concurrent runs were tried first and correctly abandoned once found to
race against the same backend state) both passed; the one failure in
each run is the already-confirmed pre-existing flaky movement-key test,
unrelated to this change.

### TTOS Safety Settings core — real weekly/monthly loss circuit breakers, Design Bible Chapter 67

Part 3's own Safety Settings scope had three pieces: weekly/monthly
loss limits (a second/third circuit breaker beyond the pre-existing
daily one), Black Swan Protection, and Broker Failover/recovery
procedures. Research confirmed `RiskLimits` had exactly one loss-based
circuit breaker (daily-scoped) and a lifetime drawdown cap, and that
Black Swan Protection and Broker Failover have zero real backing
anywhere (no external market-crash data feed, no live broker
integration to fail over from — `app/broker.py`'s own module docstring
is explicit that trading is "completely simulated"). This slice builds
the one piece with a real, honest implementation: the weekly/monthly
loss limits.

**Backend**: `RiskLimits` (`app/schemas.py`) gained
`max_weekly_loss_pct`/`max_monthly_loss_pct` (defaults 10%/15%, sitting
between the existing daily 5% and lifetime drawdown 20% — each wider
scope allows more cumulative loss before it fires, but stays well
inside the lifetime cap). `app/risk_engine.py` gained
`WEEKLY_INTERVAL_DAYS`/`MONTHLY_INTERVAL_DAYS` constants mirroring
`app/nexus.py`'s own weekly/monthly cadence (not imported, to avoid a
`risk_engine.py -> nexus.py` dependency — `nexus.py` already imports
`risk_engine.py`, never the reverse) and two new functions,
`weekly_realized_pnl_pct()`/`monthly_realized_pnl_pct()`, summing
`PaperPortfolio.trade_history`'s real realized P&L within the current
sim week (7 days)/month (30 days) as a % of starting balance — the same
shape `daily_realized_pnl_pct()` already used, just a wider window.
Two new checks inside `evaluate_sentinel_risk()`, placed right after
the existing daily ones (a week/month-scoped halt is a more common real
event than the lifetime drawdown check below it): a breach returns a
`critical`-severity `RiskWarning`, which — like every other Sentinel
warning — becomes a hard-reject vote that unconditionally blocks new
trades (`decision.py`'s `HARD_REJECT_CHOICES`). CEO-editable through
the existing `POST /api/risk-limits` write path: `update_risk_limits()`
(`app/state.py`) gained the two new params with the same
reject-non-positive validation every other percentage limit already
has; `UpdateRiskLimitsRequest` (`app/routers/risk.py`) gained the two
matching optional fields.

**Frontend**: no new Command Center tab — the smallest honest slice
extends `RiskPanel.tsx` (the existing RISK tab) with a new "Safety &
Capital Protection" block, rather than adding a standalone Operations-
section tab that would otherwise sit alone (Operations remains real but
thin — LOGS only — since Automation/Integrations/Infrastructure/Broker
Configuration still have no backing feature). The block holds: inputs +
save button for the two new limits (matching every other RiskLimits
sub-panel's own save-button pattern exactly); a live Emergency Stop
status/control reusing the same `"ui:emergencyStopConfirm"` EventBus
event `EmergencyStopControl.tsx` (TopStatusBar) already emits, styled
to match this panel's terminal aesthetic rather than reusing that
component's pixel-art styling directly; and an explicit paragraph
documenting Black Swan Protection, Broker Failover, and Emergency
Contacts as not built, naming the real gap for each (no external
market-crash feed, no live broker integration, no contact/notification-
delivery system) rather than a placeholder control. The two new limits
were also added to the panel's existing read-only "Configured Risk
Limits" summary. `types.ts`'s `RiskLimits` interface,
`api.ts`'s `updateRiskLimits()` payload type, and the two hardcoded
`RiskLimits` object literals in `NexusManager.ts`/`gameStore.ts`
(caught by a real `tsc -b` build failure the first pass's narrower
`tsc --noEmit` run had missed) all gained the two new fields.

**Verified**: 10 new backend tests
(`test_risk_engine.py`'s `TestWeeklyAndMonthlyLossLimits`, 7 cases
carefully isolating the week/monthly check under test from the daily
one by neutralizing it with a 100% threshold; `test_state.py`'s 3 new
cases in `TestUpdateRiskLimits`), `mypy`/`ruff` clean, full backend
suite 1134/1134 passing. `tsc`/`eslint`/`vite build` clean. A new
Playwright test in `commandCenter.spec.ts` exercises the real save
round-trip for both new limits and confirms the panel surfaces
Emergency Stop status and the "not built" disclaimers; full
`commandCenter.spec.ts` regression (31/32, one skipped) passed — the
one failure is the same already-confirmed pre-existing flaky
movement-key test, unrelated to this change.

### TTOS Global Status Bar — always-visible risk/health/capital/broker strip, Design Bible Chapter 67

The last genuinely-buildable piece of Part 3's brief researched to have
real backing: the "always-visible broker-status/risk-status/
capital-status/company-health strip" Chapter 67's own Safety Systems
section had explicitly named as missing (Risk Status, Company Health,
and Market Environment were previously real but shown only inside
OverviewPanel/QuickView, never persistently).

**Frontend only** — no new backend fields or endpoints; every value
this bar shows was already computed and broadcast over WS by an earlier
feature. `GlobalStatusBar.tsx` (new) renders a second row under
`TopStatusBar.tsx`, positioned `absolute top-11` so it never overlaps
that bar's own content, visible from every in-game scene the same way
`TopStatusBar`/`EmergencyStopControl` already are. Seven items, each
reading a real gameStore field directly rather than computing anything
fresh: Risk Level reuses `lib/derive.ts`'s own `riskLevel()`/
`RISK_LEVEL_LABEL` (the same Sentinel/Guardian severity bucket
`RiskPanel.tsx` already derives, imported rather than re-implemented —
this is the first import of that Command Center-scoped utility module
from outside the CommandCenter folder, judged safe since the module has
no React/DOM coupling); Company Health reuses `companyHealth.overall`/
`.tier`; Portfolio reuses `portfolioIntelligence.heat.tier` (Chapter
56's real Portfolio Heat reading — deliberately left as "Portfolio" in
the pill, not relabeled "Portfolio Health," so the label doesn't imply
a metric this codebase doesn't actually compute); Market reuses
`marketEnvironment.label`; Automation reuses `settings.operatingMode`;
Deployed reuses `portfolioIntelligence.deployedPctOfEquity`; Broker
Status is honestly static text — "SIMULATED" — since no live broker
integration exists anywhere in this codebase to read a real status
from (`app/broker.py`'s own module docstring is explicit that trading
is "completely simulated"), and inventing a field to back it would have
violated this project's no-fabrication rule. Connection status
deliberately stays in `TopStatusBar.tsx`'s own dot rather than being
duplicated into the new strip.

**A real regression, caught and fixed, not worked around**: adding this
bar gave two pre-existing real labels — RiskPanel's own "NORMAL" risk
banner and PortfolioIntelPanel's own "COOL" heat-tier pill — a second,
correct on-screen instance, which broke two existing
`commandCenter.spec.ts` assertions that used non-`exact` `getByText()`
locators expecting exactly one match (Playwright strict mode). Fixed by
adding `.first()` to both existing locators — the same disambiguation
pattern already used for the "RESUME TRADING" collision in Part 3's
Emergency Stop slice — never by removing or renaming the real duplicate
content itself, since both instances are genuinely correct.

**Verified**: `tsc`/`eslint`/`vite build` clean. A new
`globalStatusBar.spec.ts` exercises the real running app end-to-end,
confirming all seven items render with real (never blank) values from
both the base game view and from inside the Command Center. Full
`commandCenter.spec.ts` regression run twice: the already-confirmed
pre-existing flaky movement-key test failed both times; a TREASURY
deposit/withdrawal test failed once on a stale balance read (confirmed
via a standalone rerun to be live-backend-ticking flakiness — a real
trade landing between the test's own balance reads — unrelated to this
change, since nothing in this slice touches Treasury or portfolio
balances).

### TTOS Quick Action Dock — Automation Mode cycling + tab quick-jumps, Design Bible Chapter 67

Part 3's brief asked for one dock consolidating Pause/Resume (Work
Mode), Automation Mode, Emergency Stop, and quick-jumps to Risk/Company
Health/Portfolio/Executive. Two of those four pieces (Pause/Resume+Work
Mode in `BottomToolbar.tsx`, Emergency Stop in `TopStatusBar.tsx` from
this chapter's own earlier Part 3 slice) were already real, global,
always-visible controls; this slice builds the two pieces that weren't:
Automation Mode as a global one-click cycle, and real quick-jump
buttons.

**Frontend only** — no new backend fields or endpoints; Operating Mode
already had a real, working write path (`SettingsManager.update({
operatingMode })`), this dock just surfaces a second entry point to it.
`QuickActionDock.tsx` (new), positioned `absolute bottom-16 right-3` —
a corner cluster deliberately chosen to avoid `BottomToolbar.tsx`'s own
already-crowded centered row and `TopStatusBar.tsx`'s own right-side
group, both of which have already caused real layout regressions this
session when a 4th/5th element was appended to them. Two rows: a
"MODE" pill whose button cycles `learning → assisted → executive →
learning` on click (same `SettingsManager.update()` call
`CompanyPanel.tsx`'s own Operating Mode buttons already make), and a
"JUMP" row of four buttons.

**Quick-jump plumbing** mirrors `pendingInspectDecision` exactly (the
mechanism the Trade Outcome Banner's "View Trade"/"Analyze" buttons
already use to jump the Command Center to a specific decision), rather
than inventing a second "request an action, a listener consumes and
clears it" shape: a new `"ui:commandCenterJump": { tab: string }`
EventBus event (the payload is a bare string, not `FullCommandCenter`'s
own `Tab` union, since `EventBus.ts` can't import a type back from a
file that already imports `EventBus` — a real circular-import
constraint, not an arbitrary choice); `gameStore.ts`'s constructor
listens for it, setting a new `pendingCommandCenterTab: string | null`
field and opening the Command Center in full mode (mirroring
`"trade:inspect"`'s own listener exactly, including the
`world:interactionBlocked` emit); `FullCommandCenter.tsx` gained a
`useEffect` that validates the string against the real `TABS` constant
before calling `setTab()`, then clears it via a new
`gameStore.clearPendingCommandCenterTab()` — the same
validate-then-clear shape `pendingInspectDecision`'s own consuming
effect already uses.

**A real regression, caught and fixed at the source, not worked
around**: because `QuickActionDock` (like `GlobalStatusBar`) is always
mounted rather than conditionally rendered per Command Center tab, its
first draft's plain labels — a bare "LEARNING"/"ASSISTED"/"EXECUTIVE"
mode button, and jump buttons literally labeled "Risk"/"Company
Health"/"Portfolio"/"Executive" — collided with already-correct content
elsewhere in the 34-tab Command Center the moment both were
simultaneously in the DOM (Playwright's `getByText`/`getByRole` match
by content regardless of `z-index`/visual occlusion, so a full-screen
Command Center overlay sitting on top of the dock doesn't exempt the
dock's own elements from strict-mode ambiguity). Three real regressions
surfaced this way in the existing suite: `commandCenter.spec.ts`'s
Company tab test (`getByText("Company Health", { exact: true })` now
matched both `CompanyPanel.tsx`'s own label and the dock's jump button;
`getByRole("button", { name: /^ASSISTED/ })` would have matched both
`CompanyPanel.tsx`'s own Operating Mode button and the dock's mode
button once mode actually became "assisted"), and
`globalStatusBar.spec.ts`'s own "AUTOMATION"/"LEARNING" checks (the
dock's structural "AUTOMATION" label duplicated `GlobalStatusBar.tsx`'s
own, and its "LEARNING" value text duplicated `GlobalStatusBar.tsx`'s
own span). Given how many of the dock's natural labels — "Risk",
"Portfolio", "Executive", "Company Health", every Operating Mode name —
are common real headings/values reused throughout a 34-tab app, patching
every downstream test individually was judged less robust than fixing
the labels at the source: the dock's structural label was renamed
"AUTOMATION" → "MODE" (a legitimate distinction — one is a read-only
glance, the other an actionable control); the mode-cycle button's
accessible name was set via `aria-label` (`"Cycle Automation Mode
(currently LEARNING)"`) so `getByRole` queries elsewhere never match it
by bare mode name, while its *visible* text still shows the plain mode
name for compactness; and the four jump buttons' visible text was
changed to an arrow-prefixed form ("→ Risk", not bare "Risk") so
`getByText(exact)` queries against real headings elsewhere never match
them either. `globalStatusBar.spec.ts`'s own single remaining "LEARNING"
check needed `.first()` (that value text is now legitimately real in
two always-mounted places at once — GlobalStatusBar's span and the
dock's own button — the same "second correct instance" reasoning
already applied to the NORMAL/COOL collisions in this chapter's Global
Status Bar slice above).

**Verified**: `tsc`/`eslint`/`vite build` clean. A new
`quickActionDock.spec.ts` exercises the real running app end-to-end:
cycling the mode button through a real `SettingsManager` write, and two
separate quick-jumps (RISK, then COMPANY) each confirmed by checking
the resulting active tab's own `text-cmd-cyan` highlight class — proof
the jump lands on the real requested tab, not just that the Command
Center opened. Full `commandCenter.spec.ts` regression clean except the
already-confirmed pre-existing flaky movement-key test;
`emergencyStop.spec.ts` and `globalStatusBar.spec.ts` reverified
passing after the label fixes above.

### TTOS Command Palette (Cmd/Ctrl+K), Design Bible Chapter 67

The last of Part 3's originally-scoped brief with real backing: a
keyboard-driven command palette. This phase (Phase 2 in the chapter's
own phased plan) had originally proposed building the palette *over* a
universal-search index — in practice the palette's own real command set
needed no search index to be honest, so it shipped independently rather
than waiting on Universal Search, which remains its own separate,
unbuilt slice. This is a real, documented deviation from the original
phased plan, not a silent scope change.

**Frontend only** — no new backend fields or endpoints; every command
maps to an already-real EventBus event or manager call this codebase
already uses elsewhere. `CommandPalette.tsx` (new): opens on
`(metaKey || ctrlKey) && key === "k"`, closes via `useCloseOnEscape`
(the same hook every other overlay in this codebase already uses) or by
executing a command. A single text input drives substring filtering
against each command's label + section hint; `ArrowUp`/`ArrowDown`
move a `selected` index, `Enter` executes the currently-selected
command. The command list is built once per render from real state
(`paused`, `settings.workMode`, `settings.operatingMode`,
`emergencyStop.active` — so labels like "Pause"/"Resume" and
"Activate"/"Resume Trading" always reflect the real current state, not
a static guess) and covers: the same six `BottomToolbar.tsx` actions
(Save/Load/Open Company Memory/Coach Dashboard/Brain Room Dashboard/
Settings — `SaveManager.save()`/`.load()` imported statically, the same
way `BottomToolbar.tsx` already does, not a dynamic `import()` hack);
Pause/Resume via `GameManager.getInstance()?.togglePause()`; Work Mode
toggle and Operating Mode switching via `SettingsManager.update()`
(offering only the two modes *not* currently active, mirroring
`CompanyPanel.tsx`'s own three-button layout without an inert
already-selected option); Emergency Stop, which emits
`"ui:emergencyStopConfirm"` to open the real confirm dialog — the
palette is deliberately not a shortcut around the CEO's own
confirmation step Chapter 67 Part 3's Emergency Stop slice already
established; and 34 "Go to X" tab commands, one per real
`navigation.ts` `TAB_SECTION` key (`Object.keys(TAB_SECTION) as
(keyof typeof TAB_SECTION)[]`, avoiding a fourth hand-maintained tab
list alongside `FullCommandCenter.tsx`'s own `TABS`, `navigation.ts`'s
`TAB_SECTION`, and `commandCenter.spec.ts`'s own 34-tab test array),
each executing via the exact `"ui:commandCenterJump"` EventBus event
`QuickActionDock.tsx`'s own quick-jump buttons already established
(Chapter 67 Part 3's Quick Action Dock slice) — reused verbatim, not
reimplemented. Two of the brief's own example commands are deliberately
absent: "Open Charles Schwab" (no live broker integration exists
anywhere — `app/broker.py`'s own module docstring: "Completely
simulated... no such adapter exists or is wired in v0.6") and "Swing
Trading Mode"/"Day Trading Mode" (confirmed no such mode exists under
any name) — the same honesty boundary this chapter's own Part 3
research already drew for Emergency Stop and the Global Status Bar.

**A real collision, found and fixed differently than the Dock's own**:
because the palette is only mounted while `open` is true (unlike
`GlobalStatusBar`/`QuickActionDock`, which are always mounted), it
doesn't inherit their always-visible-label-collision risk — but while
it *is* open, several of its real command labels ("Save", every tab
name) do legitimately duplicate other always-visible real controls
(`BottomToolbar.tsx`'s own "Save" button, in particular). Rather than
renaming the palette's own labels (unnecessary here, since the
collision only exists for the few seconds the palette is actually
open, not permanently), the fix was narrower: a `data-testid=
"command-palette"` on the palette's own root container, with its test
scoping every `getByText` query through that container instead of the
full page.

**Verified**: `tsc`/`eslint`/`vite build` clean. A new
`commandPalette.spec.ts` exercises the real running app end-to-end:
opening via Ctrl+K, confirming real (non-fabricated) commands are
listed, filtering to a single real command by substring, executing it
via Enter and confirming the Command Center actually opens on the real
requested tab (checking the resulting tab button's own `text-cmd-cyan`
highlight class, the same verification pattern
`quickActionDock.spec.ts` already established), and confirming Escape
closes the palette cleanly on reopen. Full `commandCenter.spec.ts`
regression clean except the already-confirmed pre-existing flaky
movement-key test.

### TTOS Universal Search, built into the Command Palette, Design Bible Chapter 67

The last piece of Part 3's original brief with real backing beyond the
Executive Alert Center. Rather than a second Ctrl+K-shaped overlay,
Universal Search extends the Command Palette's own input, since both
need the identical type/filter/arrow-nav/enter-to-act shape — building
a second competing overlay for the same interaction pattern would have
been the duplication this codebase's own "reuse, don't duplicate"
convention warns against.

**Frontend only, no new backend endpoint** — same "index of what we
already have, never a new source of truth" pattern `CompanyMemory.tsx`'s
own client-side filter already established, even though two real
backend search functions exist unexposed by any route
(`app/memory.py`'s `search()`, `app/knowledge.py`'s
`search_knowledge()`). `CommandPalette.tsx`'s `commands` list gained
four new real-data sections, appended after the existing action/tab
commands: employees (one entry per `AGENT_IDS`, reading the real
name/occupation from `AGENT_PROFILES`, executing a jump to AGENTS);
closed trades (one entry per `paperPortfolio.tradeHistory` record,
labeled with the real symbol/side/P&L%, jumping to REPLAY — where trade
history is actually browsable, unlike the decision-level REPLAY
timeline that lives on the same tab but isn't deep-linked to a specific
trade in this slice); research items (one entry per real `research`
item, labeled with title + symbol, jumping to RESEARCH); and Company
Memory records (one entry per real `memory` record, opening the actual
Company Memory overlay — this palette only gets the CEO to the right
surface, it deliberately doesn't reimplement `CompanyMemory.tsx`'s own
search a second time). All four read directly off `useGameStore()`,
so they're never stale relative to what's actually on screen elsewhere.

Because a mature save can accumulate hundreds of trades/research items/
memory records, rendering every match unfiltered would make the
overlay unusably long. The fix: `filtered` (the full match list, used
for search correctness) is separate from `visible = filtered.slice(0,
MAX_RESULTS)` (used only for what's rendered and for the keyboard
`ArrowUp`/`ArrowDown`/`Enter` bounds) — the underlying search still
runs across every real record the CEO has, only the render and the
keyboard-navigable range are capped at 50, with a "+N more — refine
your search" hint appended when truncated. This is the same "cap
render, never cap the real underlying data" shape this Design Bible's
own `max_decision_vault_entries`/`max_memory_records` CEO controls
already use for a different reason (retention limits), applied here to
UI performance instead.

**Verified**: `tsc`/`eslint`/`vite build` clean. Live-verified against
the running dev stack: searching "scout" surfaces the real employee
result with its real occupation ("Scout — Market Scanner"); searching a
real symbol ("gld") surfaces multiple real research items and Company
Memory records actually generated by the live sim, proving the search
runs over live data, not a static fixture. A new Universal Search test
in `commandPalette.spec.ts` confirms the Scout employee result appears
and that executing it opens the Command Center on the real AGENTS tab.
Full `commandCenter.spec.ts` regression clean except the already-
confirmed pre-existing flaky movement-key test — the entity-search
additions only render while the palette is open (unlike
`GlobalStatusBar`/`QuickActionDock`, which are always mounted), so they
don't inherit that always-visible-label-collision risk class.

### TTOS Smart Notification priority tiers + Executive Alert Center, Design Bible Chapter 67

The one remaining genuinely unbuilt piece of Part 3's original brief.
Every `CyberNotifications.tsx` toast now carries a real
`NotificationTier` (`"critical" | "high" | "normal"`), always derived
from the same field already driving that toast's own kind/copy — never
a second-guessed severity computed separately. `push()`'s signature
gained a `tier` parameter and an optional `sticky` flag; every call site
was updated to pass its own real tier: `RiskWarning.severity ===
"critical"` for risk toasts, `ScannerAlert.alertType ===
"high_volatility"` for "high," `save:failed` for a real data-loss risk
("critical", and now sticky — a genuine behavioral change from the
previous always-auto-dismissing save-failure toast), everything else
"normal".

**Two real event sources previously produced zero proactive
notification anywhere in this codebase** — a critical `RiskWarning`
(only passive visibility existed, in `RiskPanel.tsx`/
`GlobalStatusBar.tsx`) and Emergency Stop activation (only the button's
own visual flip and a Company Memory entry). Both now push a sticky,
non-auto-dismissing "critical" toast — the one real interrupt behavior
this phase adds to an otherwise always-auto-dismissing (6s) toast
system. A true modal interrupt already exists for trade proposals via
`ExecutiveVoting.tsx` and stays that component's own territory, not
duplicated here.

**Diffing correctly required more care than a plain boolean flip.** The
risk-warning listener diffs newly-appeared warning ids against the
previous tick's `Set<string>` (`priorRiskWarningIds`), safe because risk
warnings are purely WS-tick-driven with no competing update channel.
Emergency Stop is different: `NexusManager.setEmergencyStop()` applies
the activate/resume API response *immediately*, ahead of the next real
WS broadcast tick — the same "don't wait for the next tick" pattern
`riskLimits` already uses. That immediate-apply channel can race a
regular broadcast: a stale, already-in-flight `active: false` tick sent
by the server *before* activation can be processed by the client's
`onmessage` handler *after* the immediate apply resolves (fetch
resolution and WS message delivery are two independent async sources
with no ordering guarantee between them, even though messages *within*
the WS stream itself stay ordered). A plain `wasActive` boolean would
read that stale tick as "resumed," then read the next real (still
`active: true`) tick as a brand-new activation and double-push — this
exact bug was caught live by a first draft of `alertCenter.spec.ts`
(`getByText(...)` resolving to 2 elements after a single, real
activation). The fix keys the "already notified" marker off the real
`activatedAt` timestamp (unique per genuine activation) instead of a
boolean: `notifiedEmergencyStopAt` only advances when `state.active &&
state.activatedAt !== notifiedEmergencyStopAt.current`, and is left
untouched by any `active: false` tick, stale or current, since that
branch never runs when `state.active` is false. A genuine resume-then-
reactivate cycle still notifies correctly, since the backend always
mints a new `activatedAt` for a real new activation.

**Every toast (not just critical ones) is recorded** into a new
`gameStore.alertHistory: AlertEntry[]` via `pushAlert(tier, title,
body)`, called from inside `push()` itself so no call site needs to
remember to record separately. Capped at 200 entries
(`MAX_ALERT_HISTORY`) — a render/storage cap only, the same "cap
render, never cap the real underlying data" shape Universal Search's
`MAX_RESULTS` already established, applied here to history retention
instead of search results.

**`AlertCenter.tsx` (new)** is the browsable history view, opened via
the Command Palette's new "Open Alert Center" command
(`EventBus.emit("ui:alertCenter", { open: true })`) rather than a
second Ctrl+K-shaped surface or a bespoke trigger — one more entry in
the same real-actions list the palette already offers. It reuses
`Glass`/`StatusPill`/`TerminalLabel`/`EmptyState` from
`CommandCenter/ui.tsx` for its own chrome rather than inventing new
overlay primitives, and joins the existing `OVERLAY_KEYS` set
(`alertCenterOpen`) so opening it closes any other exclusive overlay and
blocks movement the same way every other full-screen overlay in this
codebase already does. Tier filter chips (All/Critical/High/Normal)
each show a real live count derived from `alertHistory` itself, never a
static or placeholder number.

**Verified**: `tsc`/`eslint`/`vite build` clean. Live-verified against
the running dev stack: activating the real Emergency Stop produces the
sticky red pulsing toast, confirmed still visible 7s later (past the 6s
auto-dismiss every other toast kind uses); opening the Alert Center via
the palette shows the real accumulated history with working tier
filtering. A new `alertCenter.spec.ts` exercises this same flow end to
end against the real backend (`POST /api/emergency-stop/activate`, the
same endpoint `emergencyStop.spec.ts` already exercises), asserting the
sticky toast, the real recorded history entry, and the tier filter —
using `.first()` where the shared dev backend can legitimately carry
more than one real Emergency Stop activation across a test session, the
same "real second correct instance, not a bug" pattern this chapter's
`GlobalStatusBar`/`QuickActionDock` slices already established. Full
Playwright regression passing.

## Test suite popup resilience

`frontend/tests/helpers.ts` is the shared home for what every one of the
suite's 17 spec files previously carried its own slightly-drifted copy
of. The problem it fixes: this app's sim clock keeps ticking in real
time against one shared dev backend for the whole length of every spec
file's run, so a genuinely new `TradeProposal`, a real closed
`PaperTrade`, a Trade Gatekeeper veto, or a Founder-approved
`BlackBoxReview` can pop a real overlay up over whatever a test is doing
at any moment — correct, honest gameplay behavior, not a test-only
quirk, and a test should never fail because one showed up.

`dismissBlockingPopups()` knows all four real overlays this can produce:
`executive-voting` (Feature 12, closed via "Decide later" — the one
real exit that neither submits a decision nor can chain anywhere),
`gatekeeper-rejection` (Feature 20's veto screen, closed via
"ACKNOWLEDGE"), the `trade-outcome-banner` (closed via "Dismiss"), and
`BreakthroughMoment` (the Eureka! system — no `data-testid`, matched by
its own dismiss button's accessible name). Auditing the pre-existing
per-file copies found two of these four were never handled anywhere
(`gatekeeper-rejection`, `BreakthroughMoment`), and some files'
`continueGame()` never dismissed anything at all — real resilience
gaps, not just duplication. `clickRobust()` (and the `clickButton()`/
`clickTab()`/`clickExpand()` wrappers built on it) turn any click into a
dismiss-then-retry loop, so a popup intercepting a click gets cleared
and the click retried rather than failing the test outright. A popup
that genuinely can't be dismissed still fails loudly: each
`tryDismiss*` function throws if clicking its own dismiss control
doesn't actually close it — the real "cannot be dismissed / behaves
incorrectly" case the brief for this change asked to keep failing.

**A background auto-dismiss fixture was tried and reverted.** The
idea — a `test.extend()` fixture polling `dismissBlockingPopups()`
independently of the test body's own control flow, so no call site
would ever need to remember to dismiss first — sounded like the more
scalable fix. In practice it raced with the foreground's own
dismiss-then-retry clicks over the same page, and its teardown (`await`ing
the background loop's current in-flight iteration after the test
finished) could itself exceed the test's timeout budget, which broke
two previously-passing `campusMap.spec.ts` tests that had nothing to do
with popups. Verified via a live suite run that reintroduced exactly
those two failures, then via a second run confirming they were gone
once the fixture was reverted back to the manual, per-click retry
pattern. `executiveVoting.spec.ts` and `feature50Part2.spec.ts`'s
`ensureAtLeastOneRealDecision()` deliberately don't use even the manual
helpers' `continueGame()`-level auto-dismissal in the same blanket way —
those tests' own subject is directly interacting with the
`executive-voting` popup (BUY/SELL/hold/Devil's Advocate/...), so they
dismiss explicitly at the points where a bystander popup could
plausibly appear, never reflexively on the one they're testing.

Two other real bugs surfaced and were fixed while verifying this:
`campusMap.spec.ts` had a hardcoded employee-count assertion ("13")
that had already gone stale once before (per its own now-removed
comment) and had gone stale again with the CIO/Quant hires — it now
reads the real live count from `GET /api/load` instead. `marketIntel.spec.ts`
had two assertion bugs unrelated to popups: a case-sensitive regex
matching against `TerminalLabel`'s rendered text, which is uppercase
only via CSS `text-transform` (the DOM text `getByText` actually
matches stays title-case); and a `.or()` locator with a broad
`/predicted/` pattern that becomes strict-mode-ambiguous once the
shared backend has accumulated more than one real graded Learning Loop
entry, fixed with `.first()`.

**Verified**: three full ~60-70-test suite runs against the live Vite +
FastAPI stack (each ~11 minutes, exercising a real, continuously-ticking
backend) confirmed the same set of popup-interception failures does not
recur across runs. Six failures surfaced during verification that are
unrelated to popups and pre-existing — a movement-hold timing flake, a
dialogue-render timing flake (both in `interaction.spec.ts`), Devil's
Advocate assignee-rotation determinism on a small eligible-employee
pool, one strict-mode text ambiguity (the word "Coach" matching both a
department label and an agent name), and one Phaser runtime
`TypeError` — deliberately left alone rather than folded into this
change, since none of them involve a popup.

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
