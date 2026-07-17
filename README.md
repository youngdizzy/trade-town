# TradeTown — v0.3

TradeTown is a pixel-art AI investment company simulation. You play the
CEO, walking around a small headquarters while a team of five AI employees —
Scout, Atlas, Echo, Nova, and Scribe — research the market, hold meetings,
take breaks, and log everything to a searchable company memory, live, in
the background, whether or not you're watching. Think Stardew Valley's
overworld crossed with a Bloomberg terminal's sense of "the market never
sleeps."

This is **version 0.3**: a fifth employee (Scribe, the company historian),
a rotating research queue across a watchlist of market symbols, a
swappable market-data-provider layer (mock data in this version — see
"Market intelligence" below), meetings that now produce real discussion
transcripts and minutes, a searchable Company Memory log, and an upgraded
Brain Room / newspaper / whiteboards surfacing all of it. **TradeTown does
not place trades in this version** — it researches, discusses, and
records; see [`docs/Architecture.md`](docs/Architecture.md) for the exact
boundary and what's deliberately deferred to a future version, and
[`CHANGELOG.md`](CHANGELOG.md) / [`docs/VersionHistory.md`](docs/VersionHistory.md)
for what changed since v0.2.

## Market intelligence (and what it isn't)

Every agent (except Scribe) always has one research topic "in progress"
from an 8-symbol watchlist (stocks, ETFs, an index, gold, Bitcoin, a
sector, and a macro proxy), with a confidence score that climbs over time
until it completes and rotates to a new topic. Prices come from a mock
market-data provider — a local, seeded random walk, not a live feed — behind
a `MarketDataProvider` interface designed so a real adapter (Polygon,
Finnhub, Alpha Vantage, Yahoo Finance, Schwab, ...) can be dropped in later
without touching anything that consumes it. **No real market API is called
and no trade is ever placed** — completed research above a confidence
threshold gets logged as a "future trade candidate," a note for a human to
consider later, not an executed action.

## Quick start (Docker — recommended)

```bash
docker compose up --build
```

Then open **http://localhost**. That's it — no local Node/Python install
required. The stack is:

- **frontend**: an nginx container serving the built React/Phaser app and
  reverse-proxying `/api` and `/ws` to the backend.
- **backend**: FastAPI + SQLite, running a background simulation loop
  (NEXUS) that keeps all five agents' schedules, tasks, research, meetings,
  and the game clock ticking.

To change the host port, copy `.env.example` to `.env` and set `HTTP_PORT`.

## Local development

```bash
docker compose -f docker-compose.dev.yml up --build
```

This runs the Vite dev server (hot reload, port 5173) and `uvicorn --reload`
(port 8000) with source directories bind-mounted.

Or without Docker:

```bash
# Backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

The frontend's Vite dev server proxies `/api` and `/ws` to
`http://localhost:8000` automatically (see `frontend/vite.config.ts`).

## Controls

- **WASD / Arrow keys** — move
- **E** — interact (enter a building, talk to an agent, read the newspaper, exit a room)
- **Esc** — pause

## Project layout

See [`docs/FolderStructure.md`](docs/FolderStructure.md) for the full tree.
Top level:

```
assets/cute-fantasy-rpg/   Source art (see License below)
frontend/                  React + TypeScript + Phaser 3 + Tailwind
backend/                   FastAPI + SQLite
scripts/                   Asset discovery pipeline
deploy/                    Example host-level nginx config for a VPS
docs/                      Architecture, folder structure, developer guide
```

## Documentation

- [`docs/Architecture.md`](docs/Architecture.md) — systems, data flow, why things are built this way
- [`docs/API.md`](docs/API.md) — REST/WebSocket wire format
- [`docs/FolderStructure.md`](docs/FolderStructure.md) — annotated directory tree
- [`docs/DeveloperGuide.md`](docs/DeveloperGuide.md) — day-to-day dev workflow, adding a scene/NPC/asset, deployment
- [`docs/VersionHistory.md`](docs/VersionHistory.md) — version-by-version scope and roadmap
- [`CHANGELOG.md`](CHANGELOG.md) — what changed each version

## Asset license

The art in `assets/cute-fantasy-rpg/` ("Cute Fantasy Free") is used under
its **non-commercial** free license — see `assets/cute-fantasy-rpg/read_me.txt`.
It may be modified but not redistributed or resold, even modified. If
TradeTown is ever shipped commercially, this pack must be replaced with
appropriately licensed or original art first.

## Status

Version 0.3 is feature-complete per the milestone checklist (see
`docs/Architecture.md#version-03-scope`). Development stops here until the
next milestone is scoped — v0.3 explicitly does not implement paper
trading, brokerage connections, or live trading of any kind. **Note:** the
save format changed again in v0.3 (see `CHANGELOG.md`) — a v0.1 or v0.2
save will not load; the backend detects the mismatch and starts fresh
rather than crashing.
