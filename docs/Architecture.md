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
