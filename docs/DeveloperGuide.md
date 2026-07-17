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
   `floorAsset`, `roomLabel`, `scoutLocation` (or `null` if Scout never
   visits). Override `onBuild()`/`onUpdate()` for room-specific decoration.
3. Register the scene class in `GameManager`'s `scene: [...]` array.
4. Add a `SceneId` union member in `frontend/src/types.ts` and the matching
   `Literal` in `backend/app/schemas.py`.
5. If the room should be reachable from the Lobby, add a `DoorDef` entry in
   `LobbyScene.ts`'s `DOORS` array.

## Adding a second NPC

v0.1 intentionally has only Scout, but the seams are there:

1. Extend `ScoutLocation`-style types into a more general `NpcLocation`
   union, or key locations per-NPC.
2. `NPCManager` already stores NPCs in a `Map<string, ScoutState>` — add a
   second key instead of restructuring.
3. Give the new NPC its own schedule (`Schedule.ts` / `schedule.py`) and
   dialogue lines (`DialogueManager.ts`).
4. On the backend, `GameState` currently has a single `scout: ScoutState`
   field — generalize it to a dict of NPCs keyed by id, and update
   `sim.py`'s tick to iterate all of them.

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
