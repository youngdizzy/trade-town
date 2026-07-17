# Architecture

## Overview

TradeTown v0.3 is a client/server game:

- **Frontend** (`frontend/`): a React app that mounts a single Phaser 3
  game instance into a `<div>`. Phaser owns the world (tilemaps, player,
  agents, camera, collision); React owns the HUD/menus and reads game state
  through a small pub/sub bridge rather than reaching into Phaser directly.
- **Backend** (`backend/`): a FastAPI service that is the **authoritative**
  simulation of all five agents — NEXUS (`backend/app/nexus.py`) advances
  every agent's schedule, task, mood, energy, meetings, breaks, and (new in
  v0.3) research progress in a background asyncio loop even if no browser
  is connected, and pushes the result to connected clients over a
  WebSocket. It also persists the save to SQLite.

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
| `AgentProfiles` | Static per-agent metadata (name, occupation, personality blurb, home location, sprite tint) for all five agents — mirrors `backend/app/agents.py`. |
| `NPCManager` | Registry of every agent's live state (`AgentState`), keyed by `AgentId`. Applies server pushes; offline fallback. |
| `NexusManager` | Frontend mirror of NEXUS's shared state — tasks, whiteboards, meeting, news, and (v0.3) research, watchlist, memory, meeting minutes. Diffs previous vs. new server pushes to emit discrete `task:*`/`whiteboard:*`/`meeting:*`/`news:updated`/`research:*`/`watchlist:updated`/`memory:updated` events rather than just handing scenes a raw blob. |
| `UpcomingEvents` | Computes each agent's next deterministic schedule-block transition from `Schedule.ts` (meetings are excluded — NEXUS calls those at random, so there's nothing genuine to predict). Shared by `BrainRoomHud` and `Newspaper` so both "Upcoming Events" sections agree instead of each re-deriving it. |
| `DialogueManager` | Per-agent, per-task flavor lines plus mood/override fallbacks; opens the React `DialogueBox` and records dialogue history. |
| `SettingsManager` | localStorage-backed user preferences. |
| `SaveManager` | Builds a full state snapshot (player/settings/dialogue **and** a copy of the current agents/tasks/whiteboards/meeting/news/research/watchlist/memory/meetingMinutes for instant restore), POSTs it to the backend (with a localStorage backup), autosave interval. |
| `TileWorld` | Small helpers for building a Phaser tilemap ground layer / perimeter walls / interaction zones from a manifest asset — used by every scene so tilemap setup isn't duplicated per room. |

React state (`frontend/src/state/gameStore.ts`) is a minimal
`useSyncExternalStore`-compatible store that just listens to `EventBus` and
exposes a plain snapshot object — deliberately not a full state-management
library, since the UI's needs here are "mirror a handful of events."

## Scenes (`frontend/src/game/scenes/`)

- `BootScene` → `PreloadScene` (loads every manifest asset, builds
  animations) → `MainMenuScene`.
- `LobbyScene`: the HQ courtyard. Five buildings (Scout Office, CEO Office,
  Brain Room, Meeting Room, Break Room), each an interactable door, plus a
  "TradeTown Daily" newspaper stand that opens the React `Newspaper` modal.
- `RoomScene` (abstract base): shared floor/walls/door/camera/agent-presence
  logic for every interior. Each concrete scene (`ScoutOfficeScene`,
  `CeoOfficeScene`, `BrainRoomScene`, `MeetingRoomScene`, `BreakRoomScene`)
  just declares its size, floor tile, room label, and which
  `AgentLocation` (if any) places agents there — the base class spawns/
  despawns *however many* agents currently match that location (via
  `refreshAgentPresence`), spreading them with an overridable
  `getAgentSpawnPoint` hook so a room-specific layout (e.g. Meeting Room's
  fixed seats around the table) can replace the default even-spread.
  `BrainRoomScene` additionally builds the "Mission Control" holographic
  market core and monitor desks as procedural Phaser graphics/tweens (no
  new art assets — see "Use only supplied assets" below).

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
is parameterized by `AgentId` and used for all five agents (Scout, Atlas,
Echo, Nova, and — new in v0.3 — Scribe, the company historian) — the only
per-agent differences are sprite tint/name (from `AgentProfiles`) and which
room the current server state spawns it into. Adding Scribe required zero
scene code: it's just a fifth entry in `AGENT_IDS` with a home location
like everyone else — see "Adding a fifth agent" in `DeveloperGuide.md` for
the general pattern.

Each agent wanders gently within its current room. Rooms like Brain Room
and Meeting Room can legitimately hold all five agents at once (that's the
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

`Player.png` (`assets/cute-fantasy-rpg/Player/`) only has **6 real
movement rows** (0–5: idle-down, walk-down, idle-up, idle-left, walk-left,
walk-up), verified by pixel-level inspection of every row. Rows 6–8 are
attack/action poses (sword frames) and row 9 is a faint/death pose — not
walk cycles, despite occupying plausible-looking positions in the sheet.
There is **no dedicated right-facing row at all**. `walk-right`/`idle-right`
are produced by playing the `-left` animation with the sprite horizontally
flipped (`AnimatedActor.playAnim()` maps `facing === "right"` to the
`-left` animation key and calls `sprite.setFlipX(true)`), which is the
standard Phaser approach for asset packs that only ship one side
direction. `frontend/src/assets/animation-config.json`'s `player/player`
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
| `scribe.py` | `ScribeManager` — turns research completions and meeting transcripts into `CompanyMemory` records and `MeetingMinutes`; Scribe (the agent) has no simulation logic of its own beyond its schedule, this module *is* "the historian recording everything." |
| `nexus.py` | NEXUS: the orchestrator, tying every manager above together each tick. Per agent: resolves any active override (meeting/break) or falls back to the schedule block for the current hour, updates mood/energy, and creates/completes `Task`s when the schedule-driven task label changes (task lifecycle piggybacks on the same "did the block change" check schedule-following already needed, rather than a parallel system). Separately: advances the research queue, refreshes watchlist prices, occasionally calls a meeting (`_maybe_call_meeting`) or sends a low-energy agent on a break — meetings and breaks are both the *same* `AgentOverride` mechanism (`location` + `reason` + `remainingMinutes`) rather than two bespoke state machines. Also regenerates the whiteboard text for each office. |
| `sim.py` | The background loop: sleep → tick → broadcast over WebSocket → periodically persist to SQLite. |
| `ws_manager.py` | Tracks connected WebSocket clients; `build_state_message()` is the single place that shapes an outbound `GameSaveState` into the broadcast JSON, shared by both the sim loop and a client's initial `/ws` snapshot so the two never drift out of sync. |
| `persistence.py` | Reads/writes the single save row (`slot="default"`) as a JSON blob. Guards `GameSaveState.model_validate_json()` with a `try`/`except ValidationError` — an old-schema save fails validation and is treated as "no save" (fresh state, logged as a warning) rather than crashing the app on startup. |
| `routers/save.py` | `GET /api/load`, `POST /api/save` — merges client-owned fields (player, settings, dialogue) onto server-owned fields (agents, tasks, whiteboards, meeting, news, research, watchlist, memory, meetingMinutes, time). |
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
source of truth for art), copies every PNG into `frontend/public/assets/`,
reads each file's real dimensions from its PNG header, and writes
`frontend/src/assets/manifest.generated.json`. Frame-layout metadata that
can't be inferred from pixel data (which row is "walk-down", tile grid
size, …) lives in the hand-authored
`frontend/src/assets/animation-config.json` and is merged in by id. Nothing
in game code ever references a file path — everything goes through
`AssetLoader.get(id)`. Adding a new sprite to the pack and re-running
`npm run assets:sync` (wired into `predev`/`prebuild`) makes it available
with zero code changes; only *animating* it requires an entry in
`animation-config.json`.

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

## Save format compatibility

The save schema's `version` field has changed with every version so far —
`"0.1"` → `"0.2"` → `"0.3"` — and the shape changed non-trivially each
time (`0.1→0.2`: `scout: ScoutState` → `agents: Record<AgentId,
AgentState>`, plus new `tasks`/`whiteboards`/`meeting`/`news` fields;
`0.2→0.3`: `AgentId` gained `"scribe"`, `Task` gained `category`,
`MeetingState` gained `discussion`, and `research`/`watchlist`/`memory`/
`meetingMinutes` were added). An older save fails Pydantic validation on
load; `persistence.py` catches that failure, logs a warning, and starts a
fresh default state for the current version rather than crashing — there
is no migration path between versions, by design, since none of v0.1/v0.2/
v0.3 was a public release.
