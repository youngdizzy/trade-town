# Folder Structure

```
tradetown/
├── assets/
│   └── cute-fantasy-rpg/          Source art — single source of truth (see root README license note)
│       ├── tilesets/              Ground tiles (grass/path/water/beach/cliff/farmland)
│       ├── characters/
│       │   ├── player/            Player.png (idle/walk sheet), Player_Actions.png
│       │   ├── enemies/           Discovered + manifest-registered; unused in gameplay (no combat system)
│       │   └── animals/           chicken/cow/pig/sheep; chicken-idle is a cropped single-pose frame
│       │                          (see animation-config.json — the raw sheet is a 2x2 pose grid, not one sprite)
│       ├── props/
│       │   ├── buildings/         The nine Lobby buildings (premium pack — see PREMIUM_PACK_LICENSE.txt)
│       │   └── ...                Trees, fences, chest, bridge, the decor tileset
│       ├── animations/            Animated pond/grass decor (premium pack) — lilypad, cattail, grass sway
│       ├── ui/                    Icon sheets (premium pack), staged for future in-game UI use
│       ├── read_me.txt            Free-pack license terms
│       └── PREMIUM_PACK_LICENSE.txt  License terms for the premium-pack files (buildings/animations/ui)
│
├── scripts/
│   └── generate-assets.mjs        Discovers assets/, copies into frontend/public/, writes the manifest
│
├── frontend/
│   ├── Dockerfile                 dev / builder / runner (nginx) stages
│   ├── deploy/nginx.conf          In-container nginx: serves SPA, proxies /api + /ws to backend
│   ├── index.html, vite.config.ts, tailwind.config.js, tsconfig*.json
│   └── src/
│       ├── main.tsx, App.tsx      React entry; composes GameCanvas + HUD components
│       ├── types.ts               Shared domain types (mirrors backend/app/schemas.py)
│       ├── vite-env.d.ts
│       ├── assets/
│       │   ├── animation-config.json     Hand-authored frame/animation metadata
│       │   └── manifest.generated.json   Generated — do not edit by hand
│       ├── game/
│       │   ├── systems/           GameManager, SceneManager, NPCManager, NexusManager,
│       │   │                      AgentProfiles, DialogueManager, SaveManager, AssetLoader,
│       │   │                      InputManager, CameraManager, EventBus, TimeManager,
│       │   │                      SettingsManager, Schedule, TileWorld, UpcomingEvents
│       │   ├── entities/          AnimatedActor (base), PlayerController, AgentNPC, Whiteboard
│       │   └── scenes/            BootScene, PreloadScene, MainMenuScene, LobbyScene,
│       │                          RoomScene (base), ScoutOfficeScene, CeoOfficeScene,
│       │                          BrainRoomScene, MeetingRoomScene, BreakRoomScene
│       ├── net/
│       │   ├── api.ts             REST client (save/load/health)
│       │   └── socket.ts          WebSocket client with reconnect + offline fallback wiring
│       ├── state/
│       │   └── gameStore.ts       EventBus → React bridge (useSyncExternalStore)
│       └── ui/
│           ├── components/        GameCanvas, TopStatusBar, BottomToolbar, DialogueBox,
│           │                      SettingsMenu, PauseMenu, BrainRoomHud, Newspaper, CompanyMemory
│           └── hooks/useGameStore.ts
│
├── backend/
│   ├── Dockerfile                  Runs as a non-root "app" user; reads HOST/PORT from env
│   ├── .dockerignore                Excludes .venv/__pycache__/data/*.db from the build context
│   ├── requirements.txt, requirements-dev.txt
│   ├── .env.example
│   └── app/
│       ├── main.py                FastAPI app, lifespan (DB init, load save, start sim loop)
│       ├── config.py              Env-var-driven settings
│       ├── schemas.py             Pydantic models mirroring frontend/src/types.ts
│       ├── agents.py              Per-agent profile data (name/occupation/personality/home/tint)
│       ├── schedule.py            Every agent's authoritative daily routine
│       ├── market_data.py         MarketDataProvider interface + MockMarketDataProvider
│       ├── watchlist.py           WatchlistManager: tracked symbols, price refresh
│       ├── research.py            ResearchManager: rotating per-agent research queue
│       ├── discussion.py          DiscussionManager: meeting discussion transcripts
│       ├── memory.py              CompanyMemory: capped, categorized, searchable log
│       ├── scribe.py              ScribeManager: research/meetings -> CompanyMemory + minutes
│       ├── nexus.py               NEXUS: ties every manager above together each tick
│       ├── state.py               In-memory authoritative GameState + tick() (delegates to nexus.py)
│       ├── sim.py                 Background tick/broadcast/persist loop
│       ├── ws_manager.py          WebSocket connection registry + broadcast (build_state_message)
│       ├── db.py, models.py, persistence.py   SQLAlchemy engine/models/save read-write
│       └── routers/
│           ├── health.py          GET /api/health
│           ├── save.py            GET /api/load, POST /api/save
│           └── ws.py              WS /ws
│
├── deploy/
│   ├── setup-droplet.sh                Bootstraps Docker + Compose on a fresh Ubuntu 24.04 Droplet
│   └── nginx/tradetown.conf.example    Example HOST-level nginx vhost for a VPS (TLS termination)
│
├── docs/
│   ├── Architecture.md
│   ├── API.md                     REST/WebSocket wire format
│   ├── FolderStructure.md         (this file)
│   ├── DeveloperGuide.md
│   └── VersionHistory.md          Version-by-version scope and roadmap
│
├── docker-compose.yml              Production: single published port via nginx, healthchecks, log rotation
├── docker-compose.dev.yml          Development: hot reload, both ports published
├── .dockerignore                    Excludes node_modules/dist/etc. from the frontend's build context
├── .env.example                    Root-level compose variable overrides
└── README.md
```
