# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

TradeTown: a pixel-art AI investment company simulation. Client/server game — a Phaser 3 + React frontend renders the world; a FastAPI backend runs the **authoritative** simulation of six AI employees (Scout, Atlas, Echo, Nova, Scribe, Coach) in a background asyncio loop, pushing state over WebSocket. Currently v0.5. Market data is a local seeded random walk (`MockMarketDataProvider`) and Paper Trading is entirely simulated — **no real brokerage, market API, or trade execution exists anywhere in this codebase.**

## Commands

```bash
# Frontend (cd frontend/)
npm install
npm run dev            # Vite dev server, http://localhost:5173 (proxies /api,/ws to :8000)
npm run typecheck      # tsc -b --noEmit
npm run build           # typecheck + production build
npm run lint            # eslint --max-warnings 0 (zero warnings allowed)
npm run assets:sync    # re-scan assets/cute-fantasy-rpg/ into manifest.generated.json (auto-runs on dev/build)

# Backend (cd backend/, after `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements-dev.txt`)
uvicorn app.main:app --reload   # http://localhost:8000
ruff check app/
mypy app/

# Full stack via Docker
docker compose up --build                       # production-style, http://localhost
docker compose -f docker-compose.dev.yml up --build   # hot reload, both ports published
```

There are currently **zero automated tests** in this repo (`pytest` is pinned in `backend/requirements-dev.txt` but no `test_*.py` exists; no frontend test runner is configured). Every commit's completion gate is `tsc` + `eslint` + `ruff` + `mypy` all passing, plus manual gameplay verification — never commit with any of the four failing. See docs/CODING_STANDARDS.md's "Testing Requirements" for the standard going forward (new pure-function backend logic and `model_copy(update=...)` call sites should get `pytest` unit tests in a new `backend/tests/`).

## Architecture

- **Frontend owns rendering, backend owns truth.** Phaser owns the world (tilemaps, player, agents, camera, collision); React owns HUD/menus via a `useSyncExternalStore` bridge (`frontend/src/state/gameStore.ts`) fed by `EventBus`. The backend's NEXUS tick loop (`backend/app/nexus.py`, driven by `backend/app/sim.py`) is the single source of truth for every agent's location/task/mood/energy/overrides, the task list, whiteboards, meetings, news, research, watchlist, memory, paper trading, simulations, coaching, and company score — it runs whether or not a browser is connected. Player position, camera facing, UI settings, and dialogue history are the one exception: client-authoritative, backend just stores what's last reported on save.
- **Offline fallback exists but is intentionally incomplete.** If the WebSocket drops, the frontend mirrors the same schedule data (`Schedule.ts` / `schedule.py` — kept in sync by hand) via `NPCManager.startOfflineFallback`/`TimeManager.startLocalFallback`, but meetings/breaks are NEXUS-only embellishments never mirrored offline.
- **Backend is a flat module list** (`backend/app/`, no subpackages except `routers/`) — see the module table in `docs/Architecture.md`'s "Backend" section for what each of `nexus.py`, `state.py`, `research.py`, `portfolio.py`, `paper_trading.py`, `simulation.py`, `coach.py`, `hall_of_fame.py`, `knowledge.py`, `analytics.py`, `company_score.py`, `scribe.py`, `memory.py`, `ws_manager.py`, `persistence.py` etc. own. `nexus.py` ties every manager together each tick; `scribe.py` is the sole writer of `CompanyMemory`.
- **Frontend is organized by Phaser/React boundary, not by feature** — `game/{systems,entities,scenes}` for Phaser-side code, `ui/{components,hooks}` for React-side, `state/` for the EventBus↔React bridge, `net/` for the two network clients (`api.ts` REST, `socket.ts` WS with reconnect). No `features/x/` vertical slicing. See the systems table in `docs/Architecture.md` for what each of `EventBus`, `AssetLoader`, `GameManager`, `NPCManager`, `NexusManager`, `AgentProfiles`, `DialogueManager`, `SaveManager`, `TileWorld` etc. owns.
- **Frontend types mirror backend schemas by hand**: `frontend/src/types.ts` ↔ `backend/app/schemas.py`, and `frontend/src/game/systems/AgentProfiles.ts`/`Schedule.ts` ↔ `backend/app/agents.py`/`schedule.py`. A change to one side (new `AgentId`, new `SceneId`, new schedule block) needs the matching edit on the other — there's no codegen.
- **SQLite is a single JSON-blob row**, not a normalized schema (one save slot, one company) — `persistence.py` guards deserialization with try/except so an old-schema save is treated as "no save" rather than crashing on startup (the save format changes between versions; see CHANGELOG.md).
- **Pluggable-provider pattern**: `MarketDataProvider` (`backend/app/market_data.py`) is the reference shape for anything swappable later — an ABC, one concrete implementation (`MockMarketDataProvider`), and a single env-var-gated `_select_provider()` registration point. Follow this shape for any future real data/execution adapter.

## Critical gotcha: `model_copy(update={...})` uses field names, not wire aliases

Every wire-facing Pydantic model in `schemas.py` is a `CamelModel` (camelCase alias, `populate_by_name=True`). Constructors/validation accept either the field name or the alias — but `model_copy(update={...})` bypasses validation and writes directly by Python field name. Passing the camelCase alias silently creates an unused phantom entry while the real field never updates. This has caused two real shipped bugs (meeting minutes never attached; agent task text frozen forever). **Before writing any `model_copy(update={...})` call, grep `backend/app/schemas.py` for `Field(alias=` and check every key against that list.** Full writeup: `docs/Architecture.md`'s "Gotcha" section.

## Conventions (see `docs/CODING_STANDARDS.md` for the complete, canonical list)

- TypeScript: strict mode, no `any`, `@/*` path alias instead of deep relative imports, named exports only (except `App.tsx`/`main.tsx`), Tailwind utility classes only.
- Python: `from __future__ import annotations` in every module, `CamelModel` base for wire schemas / `@dataclass(frozen=True)` for internal-only data, module-level functions (not classes) for stateless managers — classes only for state that persists across calls, `_prefixed` module-level private helpers, full type hints including return types.
- Comments: default to none; write one only for non-obvious *why* (hidden constraint, workaround, surprising behavior) — never restate what the code does, never reference a ticket/conversation.
- Commits: imperative present-tense subject, body explains why not what, one logical change per commit, never commit with a failing `tsc`/`eslint`/`ruff`/`mypy`.
- Every new extension point gets a corresponding "Adding a..." section in `docs/DeveloperGuide.md` (it already documents adding a sprite/tile, an interior room, an agent, a watchlist symbol, and a real `MarketDataProvider` — follow those steps rather than improvising when extending in those directions).

## Documentation map

This repo documents itself extensively in `docs/` — check there before re-deriving something from source:

- `docs/Architecture.md` — systems, data flow, module responsibilities, the gotcha above, version scope history
- `docs/DeveloperGuide.md` — step-by-step for adding a sprite, room, agent, watchlist symbol, or real market data provider; deployment
- `docs/API.md` — REST/WebSocket wire format
- `docs/FolderStructure.md` — annotated directory tree
- `docs/CODING_STANDARDS.md` — canonical conventions (TS/Python style, naming, git, Docker)
- `docs/KNOWN_LIMITATIONS.md`, `docs/ARCHITECTURE_REVIEW.md` — honest gaps (e.g. zero test coverage)
- `docs/TASK_BACKLOG.md`, `docs/ROADMAP.md`, `docs/VersionHistory.md` — planned/completed work
- `CHANGELOG.md` — what changed each version, including save-format breaks
