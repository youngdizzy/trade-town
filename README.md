# TradeTown — v0.6

TradeTown is a pixel-art AI investment company simulation. You play the
CEO, walking around a small headquarters while a team of nine AI employees —
Scout, Atlas, Echo, Nova, Scribe, Coach, Sentinel, Pulse, and Guardian —
research the market, vote on trade candidates, run strategy simulations,
place paper trades, hold meetings, take breaks, and log everything to a
searchable company memory, live, in the background, whether or not you're
watching. Think Stardew Valley's overworld crossed with a Bloomberg
terminal's sense of "the market never sleeps."

This is **version 0.6 — Paper Trading Operations**: three new employees
(Sentinel — Risk Management, Pulse — Market Scanner, Guardian — Portfolio
Protection) and a new Trading Floor room. Every high-confidence research
completion is now voted on by the four researchers plus Sentinel and
Guardian, with Atlas's ruling producing a permanent, explainable
`TradeDecision`; approved trades place an order through a new order-book
PaperBroker (market/limit/stop/take-profit/stop-loss) instead of opening
a position directly. A configurable Risk Engine backs Sentinel's
trade-approval gate and Guardian's exposure/concentration watch; a Market
Scanner backs Pulse's continuous gap/breakout/volume-spike/volatility
scan; a Trading Journal stamps every closed trade with a coach review and
lessons learned. **TradeTown still does not connect to a real brokerage
or execute real trades in this version** — every position, order, and
dollar in the Paper Trading engine is simulated; see
[`docs/Architecture.md`](docs/Architecture.md) for the exact boundary and
what's deliberately deferred to a future version, and
[`CHANGELOG.md`](CHANGELOG.md) / [`docs/VersionHistory.md`](docs/VersionHistory.md)
for what changed since v0.5.

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
  (NEXUS) that keeps all nine agents' schedules, tasks, research, paper
  trading (voting, risk checks, order fills, scanner alerts), simulations,
  coaching reports, and the game clock ticking.

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

## Assets

Art is organized under `assets/cute-fantasy-rpg/` into five folders —
`tilesets/`, `characters/` (`player/`, `enemies/`, `animals/`), `props/`
(including `buildings/`), `animations/`, and `ui/` — discovered
automatically by `scripts/generate-assets.mjs` into a generated manifest;
see [`docs/Architecture.md`](docs/Architecture.md#asset-pipeline) for how
the pipeline works and [`docs/DeveloperGuide.md`](docs/DeveloperGuide.md)
for how to add a new sprite.

The art comes from two versions of the same "Cute Fantasy" pack, each
under its own license:

- Everything **except** `props/buildings/`, `animations/`, and `ui/` is
  from the **free** version, used under its **non-commercial** license —
  see `assets/cute-fantasy-rpg/read_me.txt`. May be modified but not
  redistributed or resold.
- `props/buildings/` (the nine Lobby building sprites), `animations/`
  (pond decor), and `ui/` (icon sheets) are from the **premium** version,
  whose license permits commercial use — see
  `assets/cute-fantasy-rpg/PREMIUM_PACK_LICENSE.txt`.

Both forbid redistribution or resale of the assets themselves, even
modified. Since the free-pack files are non-commercial, TradeTown as a
whole is bound by the stricter of the two: if it's ever shipped
commercially, every free-pack file must be replaced with appropriately
licensed or original art first (the premium-sourced files would not need
replacing).

## Status

Version 0.6 is feature-complete per the milestone checklist (see
`docs/Architecture.md#version-06-scope`). Development stops here until the
next milestone is scoped — v0.6 explicitly does not implement live
brokerage connections or real trade execution of any kind; Paper Trading
is entirely simulated. **Note:** the save format changed again in v0.6
(see `CHANGELOG.md`) — a pre-v0.6 save will not load; the backend detects
the mismatch and starts fresh rather than crashing.
