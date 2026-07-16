# Folder Structure

```
tradetown/
├── assets/
│   └── cute-fantasy-rpg/          Source art — single source of truth (see root README license note)
│       ├── Player/                Player.png (idle/walk sheet), Player_Actions.png
│       ├── Animals/, Enemies/     Discovered + manifest-registered; unused in v0.1 gameplay
│       ├── Outdoor decoration/    Buildings, trees, fences, chest
│       ├── Tiles/                 Ground tiles (grass/path/water/beach/cliff/farmland)
│       └── read_me.txt            Pack's original license terms
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
│       │   ├── systems/           GameManager, SceneManager, NPCManager, DialogueManager,
│       │   │                      SaveManager, AssetLoader, InputManager, CameraManager,
│       │   │                      EventBus, TimeManager, SettingsManager, Schedule, TileWorld
│       │   ├── entities/          AnimatedActor (base), PlayerController, ScoutNPC
│       │   └── scenes/            BootScene, PreloadScene, MainMenuScene, LobbyScene,
│       │                          RoomScene (base), ScoutOfficeScene, CeoOfficeScene, BrainRoomScene
│       ├── net/
│       │   ├── api.ts             REST client (save/load/health)
│       │   └── socket.ts          WebSocket client with reconnect + offline fallback wiring
│       ├── state/
│       │   └── gameStore.ts       EventBus → React bridge (useSyncExternalStore)
│       └── ui/
│           ├── components/        GameCanvas, TopStatusBar, BottomToolbar, DialogueBox,
│           │                      SettingsMenu, PauseMenu
│           └── hooks/useGameStore.ts
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt, requirements-dev.txt
│   ├── .env.example
│   └── app/
│       ├── main.py                FastAPI app, lifespan (DB init, load save, start sim loop)
│       ├── config.py              Env-var-driven settings
│       ├── schemas.py             Pydantic models mirroring frontend/src/types.ts
│       ├── schedule.py            Scout's authoritative daily routine
│       ├── state.py               In-memory authoritative GameState + tick()
│       ├── sim.py                 Background tick/broadcast/persist loop
│       ├── ws_manager.py          WebSocket connection registry + broadcast
│       ├── db.py, models.py, persistence.py   SQLAlchemy engine/models/save read-write
│       └── routers/
│           ├── health.py          GET /api/health
│           ├── save.py            GET /api/load, POST /api/save
│           └── ws.py              WS /ws
│
├── deploy/
│   └── nginx/tradetown.conf.example   Example HOST-level nginx vhost for a VPS (TLS termination)
│
├── docs/
│   ├── Architecture.md
│   ├── FolderStructure.md         (this file)
│   └── DeveloperGuide.md
│
├── docker-compose.yml              Production: single published port via nginx
├── docker-compose.dev.yml          Development: hot reload, both ports published
├── .env.example                    Root-level compose variable overrides
└── README.md
```
