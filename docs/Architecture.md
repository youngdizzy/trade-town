# Architecture

## Overview

TradeTown v0.1 is a client/server game:

- **Frontend** (`frontend/`): a React app that mounts a single Phaser 3
  game instance into a `<div>`. Phaser owns the world (tilemaps, player,
  NPC, camera, collision); React owns the HUD/menus and reads game state
  through a small pub/sub bridge rather than reaching into Phaser directly.
- **Backend** (`backend/`): a FastAPI service that is the **authoritative**
  simulation of Scout — his schedule, task, mood, and energy keep advancing
  in a background asyncio loop even if no browser is connected, and get
  pushed to connected clients over a WebSocket. It also persists the save
  to SQLite.

```
┌─────────────────────────┐        WebSocket (/ws)         ┌──────────────────────────┐
│  Frontend (Phaser+React)│ <────── time + scout state ──── │  Backend (FastAPI)       │
│                          │                                 │                          │
│  EventBus ── gameStore   │ ───── REST (/api/save,/load) ─> │  GameState (in-memory)   │
│     │                    │                                 │      │                   │
│  Phaser scenes           │                                 │  SQLite (saves table)    │
└─────────────────────────┘                                 └──────────────────────────┘
```

## Why server-authoritative Scout?

The brief calls for the office to "feel alive" — Scout should be doing
research whether or not the CEO is watching. That only works if his state
lives somewhere that keeps running independent of the browser tab, so the
tick loop (`backend/app/sim.py`) is the single source of truth for
`scout.location`, `scout.currentTask`, `scout.mood`, and `scout.energy`,
and for the game clock. The frontend has a **local fallback**
(`NPCManager.startOfflineFallback` / `TimeManager.startLocalFallback`) that
mirrors the same schedule (`Schedule.ts` / `schedule.py`) so the game stays
playable if the WebSocket drops, but it defers to the server the instant a
connection is available again.

The player's position, camera-relative facing, UI settings, and dialogue
history are **client-authoritative** — the backend just stores whatever the
client last reported on save.

## Frontend systems (`frontend/src/game/systems/`)

| System | Responsibility |
|---|---|
| `EventBus` | Typed pub/sub decoupling Phaser scenes, React UI, and the network layer. Every cross-cutting event (`time:tick`, `scout:updated`, `dialogue:open`, `save:completed`, …) flows through here. |
| `AssetLoader` | The **only** place that reads `assets/manifest.generated.json`. Scenes/entities ask for an asset by id; nothing hardcodes a file path. |
| `GameManager` | Owns the single `Phaser.Game` instance and the cross-scene player transform (scenes are destroyed/recreated on transition, so "where is the player" has to live above any one scene). |
| `SceneManager` | Fade-transition helper between scenes with spawn-point handoff. |
| `CameraManager` | Consistent camera-follow (lerp, deadzone, zoom) across every scene. |
| `InputManager` | Normalizes WASD/arrows/E/Esc into a movement vector + discrete actions. One instance per scene. |
| `TimeManager` | Mirrors the server's clock; local fallback ticker when offline. |
| `NPCManager` | Registry of NPC state, keyed by id (only `"scout"` exists in v0.1). Applies server pushes; offline fallback. |
| `DialogueManager` | Scout's flavor lines (selected by current task/mood), dialogue history recording. |
| `SettingsManager` | localStorage-backed user preferences. |
| `SaveManager` | Builds a full state snapshot, POSTs it to the backend (with a localStorage backup), autosave interval. |
| `TileWorld` | Small helpers for building a Phaser tilemap ground layer / perimeter walls / interaction zones from a manifest asset — used by every scene so tilemap setup isn't duplicated per room. |

React state (`frontend/src/state/gameStore.ts`) is a minimal
`useSyncExternalStore`-compatible store that just listens to `EventBus` and
exposes a plain snapshot object — deliberately not a full state-management
library, since the UI's needs here are "mirror a handful of events."

## Scenes (`frontend/src/game/scenes/`)

- `BootScene` → `PreloadScene` (loads every manifest asset, builds
  animations) → `MainMenuScene`.
- `LobbyScene`: the HQ courtyard. Three buildings (Scout Office, CEO
  Office, Brain Room), each an interactable door.
- `RoomScene` (abstract base): shared floor/walls/door/camera/Scout-presence
  logic for every interior. `ScoutOfficeScene`, `CeoOfficeScene`, and
  `BrainRoomScene` each just declare their size, floor tile, room label, and
  which `ScoutLocation` (if any) places him there — the base class handles
  spawning/despawning him to match the server-driven schedule.

## Scout (`frontend/src/game/entities/`)

`AnimatedActor` is the shared base for anything rendered from the
directional Player.png-style sheet (idle/walk × 4 directions) —
`PlayerController` (input-driven) and `ScoutNPC` (schedule/wander-driven)
both extend it so animation/direction handling isn't duplicated. Scout also
wanders gently within his current room, shows a name tag, and opens a
speech bubble + the React `DialogueBox` on interact.

## Backend (`backend/app/`)

| Module | Responsibility |
|---|---|
| `state.py` | The single in-memory `GameState` (async-lock guarded) and its `tick()` method — advances the clock, re-evaluates Scout's schedule block, nudges mood/energy. |
| `schedule.py` | Scout's daily routine (authoritative copy; `frontend/src/game/systems/Schedule.ts` is the offline mirror). |
| `sim.py` | The background loop: sleep → tick → broadcast over WebSocket → periodically persist to SQLite. |
| `ws_manager.py` | Tracks connected WebSocket clients, broadcasts JSON. |
| `persistence.py` | Reads/writes the single save row (`slot="default"`) as a JSON blob. |
| `routers/save.py` | `GET /api/load`, `POST /api/save` — merges client-owned fields (player, settings, dialogue) onto server-owned fields (scout, time). |
| `routers/ws.py` | `/ws` — sends the current snapshot on connect, then just watches for disconnects (the sim loop drives all outbound messages). |

SQLite is deliberately a single JSON-blob row rather than a fully
normalized schema — v0.1 has exactly one save slot and one company, so
normalizing further would be speculative. The `DATABASE_URL` env var is
already SQLAlchemy-driven, so swapping to Postgres later is a
connection-string change, not a rewrite (see "Future-ready" below).

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

## Version 0.1 scope

Built: main menu, HQ lobby + 3 interior rooms, camera-follow smooth
movement with collision, one NPC (Scout) with schedule/mood/energy/memory/
dialogue, top status bar + toolbar + settings + pause UI, save/load
(autosave + manual, backend-persisted with a localStorage fallback), a live
WebSocket simulation feed, Docker Compose deployment with an nginx reverse
proxy, and day/night architecture (`TimeManager.isDay` /
`isDaytime()` are wired through, though only a status-bar/clock consumes it
today — a visual day/night tint is a natural v0.2 addition, not built yet
to avoid speculative rendering work). Weather is likewise architected for
(the clock/tick model has room for it) but not implemented, per the
instruction to build only v0.1.

Explicitly **not** in v0.1 (by design, not oversight): a second employee,
combat/enemies (the `enemies/` assets are discovered and manifest-registered
but unused), broker API integration, Postgres/Redis, multiplayer, and any
monetization — these are the "future ready" hooks the stack leaves room
for (env-var-driven `DATABASE_URL`, a plugin-shaped NPC registry, a
schedule model that generalizes past one NPC) without building them now.
