# TradeTown — v0.9

TradeTown is a pixel-art AI investment company simulation. You play the
CEO, walking around a small headquarters while a team of AI employees —
now fourteen of them — research the market, vote on trade candidates,
run strategy simulations, place paper trades, hold meetings, take
breaks, and log everything to a searchable company memory, live, in the
background, whether or not you're watching. Think Stardew Valley's
overworld crossed with a Bloomberg terminal's sense of "the market never
sleeps."

**The roster**: Scout & Pulse (Market Scanners), Atlas (Strategy Lead),
Echo (Technical Analyst), Nova (Research Analyst), Vector (Chief
Quantitative Strategist), Scribe (Company Historian), Coach (Performance
& Improvement), Sentinel (Risk Management), Guardian (Portfolio
Protection), Meridian (Chief Investment Officer), Sage (Socratic
Mentor), and the company's two founders, Keystone (Chief Risk Architect)
and Compass (Chief Learning Architect).

Everything below is reachable from the **Command Center** overlay
(press **Tab** anywhere) — over 30 tabs surfacing every system the
company runs. **TradeTown still does not connect to a real brokerage or
execute real trades** — every position, order, and dollar in the Paper
Trading engine is simulated; see [`docs/Architecture.md`](docs/Architecture.md)
for the exact boundary, and [`CHANGELOG.md`](CHANGELOG.md) for the full,
unabridged history.

## What's new

**Before a trade is placed:**
- **Decision Confidence Engine** — a real, persisted six-factor score on every trade decision
- **What-If Simulation Lab** — stress-tests a proposal against 12 named market scenarios, each a resample of the symbol's own real recent price action
- **AI Debate Room** — a full investment-committee review with real cross-examination before the CEO decides
- **Devil's Advocate** & **Innovation Points** — one analyst is always assigned to argue against the trade
- **Trade Gatekeeper** — seven real checks that can veto even the CEO's own call
- **War Room** — every proposal stress-tested across all nine executive departments, scored on real Expected Value, Risk-to-Reward, and a composite Decision Score against a shared 70-point bar
- **Decision Vault** — a permanent per-trade archive with a real, rule-based Similarity Engine ("has the desk seen this setup before?")

**Managing the portfolio, not just one trade:**
- **Enterprise Portfolio Intelligence** — real Pearson-correlation clustering between held positions, category exposure, a live Portfolio Heat reading, and capital efficiency
- **Market Intelligence Department** — the company's always-current read on regime, volatility, session, momentum, and liquidity
- **Market Environment Simulation** — real bull/bear/sideways/volatility regime classification from the watchlist's own price action
- **Company Health & Stability** scorecard — a second rating asking "is the company stable?" rather than "is it winning?"
- **Advanced Quantitative Research Division**, led by Vector

**Learning from every decision:**
- **Discipline Chamber** — grades the decision *process*, structurally blind to the outcome
- **Library of Mistakes** — permanent case studies filed only when a real process gap caused a loss
- **Reasoning Lab** — the company practices how it thinks, independent of trade outcomes
- **Reflection Chamber** & a real **Company Wisdom** score
- **Decision Journal & Mistake Tracker**
- **Research Sandbox / Strategy Validation Laboratory** — a strategy is tested, reviewed, and must earn **Company Certification** before it can size up
- **Professional Day Trading Program** — daily trading objectives and real risk-of-ruin discipline

**Running the company:**
- **Company Operating Modes** — Learning / Assisted / Executive, controlling how much NEXUS auto-resolves
- **CEO Treasury** — a protected reserve, structurally isolated from Operating Capital
- **Company Priorities** & **Time Controls** (End Workday/Week/Month, bounded fast-forward)
- **Company Constitution** — the company's own governing document, amendable by the CEO
- **Company Operating System** — a unified, filterable Knowledge Base over every learning source
- **Company DNA System** — long-run behavioral drift the company can point to and explain
- **Company Campus Map** & **CEO Calendar & Company Schedule**
- **Work Mode System** & **Living World Schedules** — every agent runs a real 24-hour day
- **Black Box** research projects — long-running, higher-risk innovation bets

**People:**
- **Meridian, Chief Investment Officer** — reviews every department rather than trading itself; a new Executive Boardroom room and a real Monthly Executive Review
- **AI Academy & Knowledge Network** — every agent earns real Knowledge Points across six branches, plus the **Company Knowledge Graph**, an interactive node-edge map of everything the company has learned
- **Sage, the Socratic Mentor** — a daily Question of the Day and per-agent Thinking Profiles
- **Keystone & Compass, the Original Founders** — the company's Chief Risk Architect and Chief Learning Architect
- **Talent Discovery System** & **Expert Consultation / Career Levels**
- **Executive Intelligence Network** — synthesizes every department's perspective into one recommendation, with a permanent Executive Meeting Log

**Interface:**
- **Command Center** — one overlay, 30+ tabs, surfacing every system above
- **Decision Replay Center** — walks back through a decision's full real timeline
- **Premium Trade Outcome Banner** — a non-blocking, queued result banner

See [`CHANGELOG.md`](CHANGELOG.md) and [`docs/VersionHistory.md`](docs/VersionHistory.md)
for the complete, feature-by-feature history.

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
  (NEXUS) that keeps all fourteen agents' schedules, tasks, research,
  paper trading (voting, risk checks, order fills, scanner alerts),
  simulations, coaching reports, and the game clock ticking.

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
- **Tab** — open the Command Center; **1-9** jump straight to a tab while it's open
- **M** — open the Company Campus Map
- **Esc** — pause / close an open panel

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

TradeTown is under active, ongoing development — new features land
continuously rather than as fixed milestones (see `CHANGELOG.md`'s
`## Unreleased` section for the complete, current list, and
`docs/DEVELOPMENT_RULES.md` for the canonical rules every new feature is
built against). No version, including this one, implements live
brokerage connections or real trade execution of any kind — Paper
Trading remains entirely simulated. The save schema is versioned and
self-migrating (see `backend/app/persistence.py`), so an older save
loads forward rather than being discarded.
