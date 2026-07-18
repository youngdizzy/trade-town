# TradeTown Project Structure

**Status:** Canonical. `docs/FolderStructure.md` is the quick-reference
file tree; this document is the same codebase organized by *role*
instead of *location* — every manager, service, scene, and entity, with
what it actually does and who it talks to. If you're asking "where does
X live," check `FolderStructure.md`. If you're asking "what does X do
and what's it allowed to touch," this is the document.

---

## Backend (`backend/app/`)

### Entry points & infrastructure

| File | Purpose |
|---|---|
| `main.py` | FastAPI app construction, CORS, router mounting, and the lifespan hook that starts/stops `sim.py`'s background task and initializes the DB. |
| `config.py` | The single `Settings` dataclass, populated entirely from environment variables — no other module reads `os.getenv` directly. |
| `db.py` | SQLAlchemy engine/session setup. |
| `models.py` | SQLAlchemy ORM model(s) — the `saves` table, one row, single-tenant. |
| `persistence.py` | Reads/writes the one save row; the schema-mismatch self-heal (old save → fresh default state) lives here. |
| `sim.py` | The background tick loop (`run_sim_loop`) — the only place that calls `GameState.tick()` on a timer and broadcasts the result. |
| `ws_manager.py` | Tracks connected WebSocket clients and `build_state_message()`, the one function that shapes `GameSaveState` into the wire-format broadcast dict. |

### Routers (`routers/`)

| File | Purpose |
|---|---|
| `health.py` | `GET /api/health` — liveness only, no auth, used by Docker healthchecks. |
| `save.py` | `GET /api/load`, `POST /api/save` — REST save/load, delegating to `persistence.py`/`state.py`. |
| `ws.py` | `WS /ws` — accepts a connection, registers it with `ws_manager`, and does nothing else (the connection exists purely to detect disconnects; the client never sends anything meaningful). |

### Domain schema

| File | Purpose |
|---|---|
| `schemas.py` | Every Pydantic model in the system — the single source of truth for the wire format, mirrored by hand in `frontend/src/types.ts`. Defines `AgentId`, `AgentState`, `Task`, `ResearchItem`, `WatchlistEntry`, `DiscussionMessage`, `MeetingMinutes`, `MemoryRecord`, `GameSaveState`, and every `Literal` category type (`TaskCategory`, `ResearchCategory`, `MemoryCategory`, etc.). |

### Static roster data

| File | Purpose |
|---|---|
| `agents.py` | `AGENT_PROFILES` — name, occupation, personality, home location, tint, for every current agent. Mirrored by hand in `frontend/src/game/systems/AgentProfiles.ts` (which additionally carries frontend-only cosmetic fields: badge, wander radius, idle-pause chance). |
| `schedule.py` | `AGENT_SCHEDULES` — every agent's full 24-hour `ScheduleBlock` list and `block_for_hour()`, the lookup NEXUS calls every tick. Mirrored by hand in `frontend/src/game/systems/Schedule.ts` for the offline fallback. |

### Orchestration & simulation managers

| File | Purpose |
|---|---|
| `nexus.py` | The orchestrator. Owns `tick()` and every per-tick decision: agent lifecycle, task routing, meeting start/end, whiteboard text, news rolls. See `NEXUS_ARCHITECTURE.md` for the full breakdown. |
| `state.py` | The single in-memory `GameState` singleton (lock-guarded) and `default_state()`. Advances the clock, then delegates to `nexus.tick()`. |
| `market_data.py` | `MarketDataProvider` (ABC), `Quote`, `MockMarketDataProvider`, and `_select_provider()` — the adapter-pattern boundary for all price data. Nothing outside this file and `watchlist.py` should ever import a market-data vendor SDK. |
| `watchlist.py` | `SEED_SYMBOLS`, `default_watchlist()`, `tick_watchlist()` — keeps `WatchlistEntry` price/status/progress in sync with research state and the injected provider. |
| `research.py` | `RESEARCHER_IDS`, `default_research()`, `tick_research()` — the rotating one-active-item-per-agent research queue. |
| `discussion.py` | `generate_discussion()` — templated per-role meeting dialogue, keyed off each participant's current research topic. |
| `memory.py` | `record()`, `search()` — the single write/read gateway for `CompanyMemory`, capped at `MAX_MEMORY_RECORDS`. |
| `scribe.py` | `record_research_completions()`, `build_minutes()`, `record_meeting()` — turns research/meeting events into `CompanyMemory` records; the only module that calls `memory.record()`. |

---

## Frontend (`frontend/src/`)

### Bootstrapping

| File | Purpose |
|---|---|
| `main.tsx` | React root (`createRoot`), `StrictMode`. |
| `App.tsx` | The full component tree — every persistent chrome piece and every modal, listed once, in z-order-relevant sequence. |
| `types.ts` | Hand-mirrored copy of `backend/app/schemas.py`'s shapes, plus frontend-only unions (`SceneId`, `AgentLocation`). |

### Game systems (`game/systems/`) — the frontend's own "managers"

| File | Purpose |
|---|---|
| `GameManager.ts` | Owns the single `Phaser.Game` instance and the cross-scene player transform (survives scene teardown/recreate). |
| `SceneManager.ts` | `goTo()` — the one function that performs a cross-scene transition (fade out → `scene.start()`), used by every door/exit in the game. |
| `CameraManager.ts` | `follow()`/`fadeIn()`/`fadeOutThen()` — the shared cover-fit zoom + smoothed-follow camera setup every room scene uses identically. |
| `EventBus.ts` | The typed pub/sub bus (`GameEvents` interface is the authoritative event catalog) connecting Phaser, React, and the network layer without direct references between them. |
| `NPCManager.ts` | The authoritative client-side mirror of every agent's `AgentState`, keyed by `AgentId`. `loadAgents()` applies a full server snapshot atomically (see `NEXUS_ARCHITECTURE.md`'s "Events" section for why atomicity here matters) and falls back to a local offline schedule simulation when disconnected. |
| `NexusManager.ts` | The authoritative client-side mirror of everything *except* agents: tasks, whiteboards, meeting state, news, research, watchlist, memory, meeting minutes. Diffs each incoming server snapshot against the previous one to emit discrete `EventBus` events (e.g. detecting a research item's status flip to `"completed"`). |
| `AgentProfiles.ts` | The frontend's copy of `agents.py`'s roster data, plus cosmetic-only fields (badge glyph, wander radius, idle-pause chance) that have no backend equivalent. |
| `Schedule.ts` | The frontend's copy of `schedule.py`, used only by `NPCManager`'s offline fallback loop. |
| `DialogueManager.ts` | `AGENT_TASK_LINES`/`AGENT_GREETINGS` — per-agent, per-task-string dialogue content, and `startConversation()`, which opens `DialogueBox` via `EventBus`. |
| `SaveManager.ts` | `buildSnapshot()`/`save()`/`load()` — assembles a full `GameSaveState`-shaped payload from every manager above for `POST /api/save`, and applies a loaded save back into every manager on load. |
| `TimeManager.ts` | The client-side clock — normally just mirrors server ticks, with a local fallback simulation while offline. |
| `SettingsManager.ts` | Music/SFX volume, autosave interval, FPS display — persisted as part of the save payload, applied to `localStorage` for instant load before the first server round-trip. |
| `AssetLoader.ts` | `get(id)` — the only sanctioned way any game code references a texture; reads `manifest.generated.json` + `animation-config.json`. |
| `InputManager.ts` | Keyboard state polling (WASD, `E`, pause key) shared by `PlayerController` and room scenes. |
| `TileWorld.ts` | `createGroundLayer()`/`createZone()`/`createPerimeterWalls()` — shared tilemap and interact-zone construction used by every room. |
| `UpcomingEvents.ts` | `upcomingEvents()` — "what's each agent's next schedule transition," shared by `BrainRoomHud` and `Newspaper` specifically so neither reimplements the same computation. |

### Scenes (`game/scenes/`)

| File | Purpose |
|---|---|
| `BootScene.ts` | First scene; kicks off asset manifest loading. |
| `PreloadScene.ts` | Loads every texture/animation via `AssetLoader` before anything else can run. |
| `MainMenuScene.ts` | New Game / Continue / Settings — the only scene with no room geometry. |
| `LobbyScene.ts` | The outdoor HQ courtyard — five building doors, the newspaper stand, ambient decoration. The hub every interior room is reached from. |
| `RoomScene.ts` | Abstract base class every interior room extends. Owns: perimeter walls, player spawn, camera setup, the shared exit door, whiteboard registration/cleanup (`addWhiteboard()`), and `refreshAgentPresence()` — the per-frame loop that spawns/despawns `AgentNPC`s to match server-reported location. |
| `ScoutOfficeScene.ts` | Scout's home office; one whiteboard. |
| `CeoOfficeScene.ts` | The player's own private office; no agent ever has this as a home location. |
| `BrainRoomScene.ts` | "Mission Control" — the holographic core, monitor desks, and the docking point for the `BrainRoomHud` React overlay. |
| `MeetingRoomScene.ts` | A table + six fixed seats; Atlas's home; the destination for every NEXUS-triggered meeting; one whiteboard. |
| `BreakRoomScene.ts` | A coffee counter + seating; the destination for low-energy break overrides. No whiteboard. |

### Entities (`game/entities/`)

| File | Purpose |
|---|---|
| `AnimatedActor.ts` | Base class for anything rendered from the shared `player/player` directional sheet — sprite, name tag, direction/animation handling. Both `PlayerController` and `AgentNPC` extend it. |
| `PlayerController.ts` | The human player's own movement/input handling, extending `AnimatedActor`. |
| `AgentNPC.ts` | One AI employee's in-scene rendering and idle-wander movement, extending `AnimatedActor`. Per-agent wander radius, idle-pause chance, tint, and an always-visible badge glyph come from `AgentProfiles.ts`. Task/mood/energy/location themselves are owned by `NPCManager`, not this class. |
| `Whiteboard.ts` | A reusable office prop that renders and auto-updates its text whenever `NexusManager` reports a `whiteboard:updated` event for its `boardId`. |

### Networking (`net/`)

| File | Purpose |
|---|---|
| `api.ts` | REST client — `GET /api/load`, `POST /api/save`. |
| `socket.ts` | `GameSocket` — the WebSocket client with reconnect/backoff, and the single `onmessage` handler that fans a `"state"` payload out to `NPCManager` and `NexusManager`. |

### State bridge (`state/`, `ui/hooks/`)

| File | Purpose |
|---|---|
| `gameStore.ts` | `GameStore` — a minimal `useSyncExternalStore`-compatible store that subscribes to every relevant `EventBus` event once, at construction, and re-derives a plain `GameUiState` object React components read. The only place `EventBus` events become React state. |
| `ui/hooks/useGameStore.ts` | The `useSyncExternalStore` hook wrapper components actually call. |

### UI components (`ui/components/`)

| File | Purpose |
|---|---|
| `GameCanvas.tsx` | Mounts the Phaser canvas into the DOM and bootstraps `GameManager`. |
| `TopStatusBar.tsx` | Clock, connection status, and one colored dot per `AGENT_IDS` entry — always visible. |
| `BottomToolbar.tsx` | Save / Load / Memory / Settings / Pause buttons — always visible. |
| `DialogueBox.tsx` | The single interact UI for talking to an agent (see `UI_UX_BIBLE.md`). |
| `BrainRoomHud.tsx` | The Mission Control overlay — Market Clock, Company/Agent Status, Research Queue, Watchlist, Current Tasks, Upcoming Events, Market Status, Recent Discoveries. Visible only in `BrainRoomScene`. |
| `Newspaper.tsx` | The five-section TradeTown Daily modal, opened from the Lobby newspaper stand. |
| `CompanyMemory.tsx` | The searchable, category-filtered `CompanyMemory` viewer modal, opened from `BottomToolbar`. |
| `SettingsMenu.tsx` | Volume sliders, autosave interval, FPS toggle. |
| `PauseMenu.tsx` | Resume / Save / Settings — the one modal intentionally allowed to coexist with Settings. |
| `DebugOverlay.tsx` | Dev-only FPS/debug readout, gated behind the `showFps` setting. |

---

## Cross-Cutting Concerns

- **`scripts/generate-assets.mjs`** — not part of either the backend or
  frontend runtime; a build-time tool that discovers `assets/`, copies
  into `frontend/public/assets/`, and writes
  `frontend/src/assets/manifest.generated.json`. Wired into
  `predev`/`prebuild`, never run manually in normal development.
- **`deploy/`** — `setup-droplet.sh` (bootstraps Docker on a fresh
  Ubuntu VPS) and an example host-nginx vhost. Not part of the
  application; operational tooling only.
- **`docker-compose.yml` / `docker-compose.dev.yml`** — production
  (single published port via nginx) and development (hot reload, both
  ports published) topologies. See `docs/DeveloperGuide.md`.

## What Belongs Where — a Quick Rule Set

- A new piece of **agent-affecting logic** belongs in `nexus.py` or a
  module it calls, never in a router or `state.py` directly — routers
  only ever read/write the save, they never compute simulation state.
- A new **frontend-only cosmetic concern** (an animation, a tint, a
  glyph) belongs in the relevant `game/systems/` file or entity class,
  never duplicated into `schemas.py` — the backend has no concept of
  "badge glyph" and shouldn't gain one just because the frontend has it.
- A new **cross-cutting UI concern** (a new modal, a new always-visible
  chip) belongs in `ui/components/`, wired through `EventBus` and
  `gameStore.ts` exactly like every existing modal — never given a
  private communication channel to a Phaser scene.
- A new **manager of any kind**, backend or frontend, should have
  exactly one job and a name that says what it is (`SaveManager`,
  not `Manager2`) — see `CODING_STANDARDS.md`'s naming rules.
