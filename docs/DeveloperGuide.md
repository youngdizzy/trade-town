# Developer Guide

## Prerequisites

- Docker + Docker Compose (recommended path — see README "Quick start")
- For non-Docker local dev: Node.js 22+, Python 3.11+

## Everyday commands

```bash
# Frontend
cd frontend
npm install
npm run assets:sync   # re-scan assets/cute-fantasy-rpg/ into the manifest (auto-runs on dev/build)
npm run dev            # Vite dev server, http://localhost:5173
npm run typecheck      # tsc -b --noEmit
npm run build           # typecheck + production build
npm run lint

# Backend
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload   # http://localhost:8000
ruff check app/
mypy app/
```

## Adding a new sprite/tile to the pack

1. Drop the `.png` anywhere under `assets/cute-fantasy-rpg/`.
2. Run `npm run assets:sync` (from `frontend/`) — it's discovered automatically,
   copied into `frontend/public/assets/`, and given an id in
   `manifest.generated.json` based on its path (e.g.
   `Outdoor decoration/Well.png` → `outdoor-decoration/well`).
3. If it's a directional character sheet or needs specific animation rows,
   add an entry to `frontend/src/assets/animation-config.json` keyed by that
   same id (see the existing `player/player` entry for the shape). Static
   images and single-tile ground tiles need no entry — they default to
   `"kind": "static"`.
4. Reference it from game code via `AssetLoader.get("your/asset/id")` —
   never hardcode a path.

## Adding a new interior room

1. Create `frontend/src/game/scenes/YourRoomScene.ts` extending `RoomScene`.
2. Set the required fields: `sceneKey`, `widthTiles`, `heightTiles`,
   `floorAsset`, `roomLabel`, `agentLocation` (an `AgentLocation`, or `null`
   if no agent ever visits). Override `onBuild()`/`onUpdate()` for
   room-specific decoration, and `getAgentSpawnPoint()` if the default
   even-spread-around-center layout isn't right for this room (see
   `MeetingRoomScene`'s fixed seats for an example).
3. Register the scene class in `GameManager`'s `scene: [...]` array.
4. Add a `SceneId` union member in `frontend/src/types.ts` and the matching
   `Literal` in `backend/app/schemas.py`, plus an `AgentLocation` member
   (both files) if agents can be scheduled there, and a
   `LOCATION_TO_SCENE` entry in `AgentProfiles.ts` / `agents.py`.
5. If the room should be reachable from the Lobby, add a `DoorDef` entry in
   `LobbyScene.ts`'s `DOORS` array.
6. If the room should have a whiteboard, add a `Whiteboard` instance (see
   `ScoutOfficeScene`) and a matching key in NEXUS's
   `_update_whiteboards()`.

## Adding a new agent

The agent system is already generalized past a fixed count — Scribe (v0.3)
was added this way on top of v0.2's four, with zero Phaser scene changes.
Adding another means touching data, not architecture:

1. Add an `AgentId` union member in `frontend/src/types.ts` and
   `backend/app/schemas.py` (`AGENT_IDS`/`AgentId`).
2. Add an `AgentProfile` entry (name, occupation, personality, home
   location, sprite tint) in both `frontend/src/game/systems/
   AgentProfiles.ts` and `backend/app/agents.py` — keep them in sync, the
   backend copy is authoritative but the frontend needs its own for the
   offline fallback and rendering.
3. Give the new agent a daily schedule in both `Schedule.ts` and
   `schedule.py` (`AGENT_SCHEDULES[id]`, a list of `ScheduleBlock`s
   covering all 24 hours).
4. Add personality-flavored dialogue lines in `DialogueManager.ts`'s
   `AGENT_TASK_LINES[id]`, keyed by the task strings used in that
   schedule, plus a greeting in `AGENT_GREETINGS[id]`.
5. If the agent should research (see below) rather than just record/manage
   like Scribe, add it to `RESEARCHER_IDS` in `backend/app/research.py`
   and give it a line template in `discussion.py`'s `_ROLE_LINES` and a
   title template in `research.py`'s `_RESEARCH_TITLE_BY_AGENT`.
6. That's it for presence/dialogue/schedule — `NPCManager`, `NexusManager`,
   `RoomScene`/`AgentNPC`, `TopStatusBar`, `BrainRoomHud`, and the save
   schema all iterate `AGENT_IDS`/`Record<AgentId, ...>` rather than
   hardcoding a count, so a new id shows up everywhere automatically once
   the steps above are done.

## Adding a symbol to the watchlist

Edit `SEED_SYMBOLS` in `backend/app/watchlist.py` — each entry is
`(ticker, display name, ResearchCategory)`. The research queue
(`research.py`) rotates agents through this same list, so a new symbol
starts getting researched automatically; no other file needs to change.

## Adding a real `MarketDataProvider`

v0.3 ships only `MockMarketDataProvider` (`backend/app/market_data.py`) —
a local seeded random walk, no network calls. To wire in a real vendor
(Polygon, Finnhub, Alpha Vantage, Yahoo Finance, Schwab, ...):

1. Implement the `MarketDataProvider` ABC (`get_quote`, and optionally
   override `get_quotes` if the vendor has a real batch endpoint — the
   default implementation just loops `get_quote` per symbol).
2. Register it in `_select_provider()`, gated on an env var (following the
   existing `MARKET_DATA_PROVIDER` pattern) so the mock stays the default
   when no API key is configured — never make a real provider load
   unconditionally.
3. Nothing else changes: `watchlist.tick_watchlist()` only ever calls
   `provider.get_quotes()`, so every consumer downstream (Brain Room HUD,
   newspaper, whiteboards) keeps working unmodified.

## Environment variables

See `.env.example` (compose-level) and `backend/.env.example`
(backend-specific) for the full list. Nothing in the stack has a hardcoded
secret; `DATABASE_URL`, `CORS_ORIGINS`, and simulation pacing are all
env-driven.

## Deploying to a fresh Ubuntu VPS

```bash
# On the VPS (Ubuntu 24.04, e.g. a DigitalOcean Droplet):
git clone <your-repo-url> tradetown && cd tradetown
sudo bash deploy/setup-droplet.sh
# Installs Docker Engine + the Compose plugin via Docker's official apt repo
# (Ubuntu's own docker.io/docker-compose-v2 packages tend to lag behind and
# aren't as reliable for this). It does NOT touch the firewall.

cp .env.example .env
# Every variable in .env.example has a working default — this step is
# optional unless you want to change the port or simulation pacing.
# e.g. set HTTP_PORT=8080 if you'll front it with host nginx (see below)
docker compose up -d --build
```

That's the entire footprint: no separate Node/Python/Nginx install needed
on the host, per the brief. Two options from there:

- **Expose port 80/443 directly** from the `frontend` container (leave
  `HTTP_PORT=80`, add a TLS-terminating proxy in front later once you have
  a domain) — simplest for a quick deploy.
- **Front it with host nginx + Let's Encrypt** (recommended for a real
  domain): set `HTTP_PORT=8080` (or similar) in `.env` so compose binds
  only to localhost-reachable high port, then use
  `deploy/nginx/tradetown.conf.example` as a starting point for a host
  vhost that terminates TLS and proxies to it. `certbot --nginx` will fill
  in the HTTPS block for you.

### Updating a deployment

```bash
git pull
docker compose up -d --build
```

The SQLite save lives in the `tradetown-data` named Docker volume, so it
survives rebuilds/restarts. Back it up with:

```bash
docker run --rm -v tradetown_tradetown-data:/data -v "$PWD":/backup alpine \
  tar czf /backup/tradetown-data-backup.tar.gz -C /data .
```

## Troubleshooting

- **Blank screen / Phaser never appears**: check the browser console —
  usually a missing `manifest.generated.json` (run `npm run assets:sync`)
  or a Phaser texture-key typo (`AssetLoader.get()` throws a clear error
  naming the missing asset id).
- **WebSocket shows "Offline" in the top bar**: the frontend falls back to
  local simulation automatically. Check `docker compose logs backend` (or
  `uvicorn` output locally) — CORS origin mismatches are the most common
  cause (`CORS_ORIGINS` must include the origin the browser is loading
  from).
- **Save doesn't persist across a full stack restart**: confirm the
  `tradetown-data` volume exists (`docker volume ls`) and wasn't removed
  with `docker compose down -v`.
