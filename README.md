# TradeTown — v0.1

TradeTown is a pixel-art AI investment company simulation. You play the
CEO, walking around a small headquarters while an AI research employee
(Scout) works his schedule — scanning market news, back-testing strategies,
and reviewing positions — live, in the background, whether or not you're
watching. Think Stardew Valley's overworld crossed with a Bloomberg
terminal's sense of "the market never sleeps."

This is **version 0.1**: one employee (Scout), four rooms, a save/load
system, and a live backend simulation. See [`docs/Architecture.md`](docs/Architecture.md)
for what's deliberately deferred to a future version.

## Quick start (Docker — recommended)

```bash
docker compose up --build
```

Then open **http://localhost**. That's it — no local Node/Python install
required. The stack is:

- **frontend**: an nginx container serving the built React/Phaser app and
  reverse-proxying `/api` and `/ws` to the backend.
- **backend**: FastAPI + SQLite, running a background simulation loop that
  keeps Scout's schedule and the game clock ticking.

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
- **E** — interact (enter a building, talk to Scout, exit a room)
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
- [`docs/FolderStructure.md`](docs/FolderStructure.md) — annotated directory tree
- [`docs/DeveloperGuide.md`](docs/DeveloperGuide.md) — day-to-day dev workflow, adding a scene/NPC/asset, deployment

## Asset license

The art in `assets/cute-fantasy-rpg/` ("Cute Fantasy Free") is used under
its **non-commercial** free license — see `assets/cute-fantasy-rpg/read_me.txt`.
It may be modified but not redistributed or resold, even modified. If
TradeTown is ever shipped commercially, this pack must be replaced with
appropriately licensed or original art first.

## Status

Version 0.1 is feature-complete per the milestone checklist (see
`docs/Architecture.md#version-01-scope`). Development stops here until the
next milestone is scoped.
