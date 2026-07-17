# Changelog

All notable changes to TradeTown are documented here. Versions are
development milestones, not semver releases.

## v0.3

### Added

- **Scribe, a fifth agent** (Company Historian: meticulous, quiet, writes
  everything down) — home room Brain Room, own daily schedule, and the
  first agent that doesn't research; it records. Added with zero Phaser
  scene changes, validating the v0.2 architectural investment in
  `AGENT_IDS`-driven iteration (see `docs/DeveloperGuide.md`'s "Adding a
  new agent").
- **`MarketDataProvider` interface** (`backend/app/market_data.py`) — an
  `ABC` with `get_quote`/`get_quotes`, a shipped `MockMarketDataProvider`
  (seeded-hash starting price + per-call random walk, no network calls),
  and a `_select_provider()` registration point gated by the
  `MARKET_DATA_PROVIDER` env var. No real vendor is wired in v0.3 by
  design — see "Adding a real `MarketDataProvider`" in
  `docs/DeveloperGuide.md`.
- **Watchlist system** (`backend/app/watchlist.py`) — eight seeded symbols
  spanning every `ResearchCategory` (stock/etf/index/economy/gold/
  bitcoin/company/sector: AAPL, MSFT, SPY, QQQ, GLD, BTC-USD, XLF, DXY).
  Each entry tracks ticker, name, last price, daily change %, status,
  research progress, and assigned agent, kept in sync with the research
  queue every tick.
- **Rotating research queue** (`backend/app/research.py`) — one active
  research item per research-capable agent (Scout/Echo/Atlas/Nova) plus a
  capped per-agent completed history, each with title, symbol, category,
  priority, status, assigned agent, summary, confidence (0–100), and
  timestamps. Confidence climbs each tick until the item completes.
- **Discussion & meeting minutes** — meetings now generate a real
  discussion transcript (`backend/app/discussion.py`, per-role templated
  lines keyed off each participant's current research topic) and, on
  meeting end, Scribe produces `MeetingMinutes` (`backend/app/scribe.py`)
  summarizing attendees and topics discussed. `MeetingState` gained a
  `discussion` field rather than a parallel state machine.
- **`CompanyMemory`** (`backend/app/memory.py`) — a capped (200), searchable,
  categorized log (research / meeting / whiteboard / event / discussion /
  discovery / future_trade) that every other new system writes into via
  `record()`. A new `CompanyMemory` React modal (search box + category
  filter chips) surfaces it, opened from a new "Memory" button in the
  bottom toolbar.
- **"Future trade candidate" flag** — when a completed research item's
  confidence crosses `FUTURE_TRADE_CONFIDENCE_THRESHOLD` (85), Scribe logs
  a `future_trade` memory record. This is a logged note for a human to
  consider later, never a queued or simulated order — v0.3 does not trade.
- **Brain Room HUD rebuilt** — Market Clock, Research Queue (one row per
  researching agent), Watchlist table, Upcoming Events, and animated
  confidence/progress bars (CSS width-transition, not a static number),
  alongside the existing Company/Agent Status panels.
- **Newspaper rebuilt** into five sections — Company News, Research
  Updates (sorted by most recently updated), Agent Activity, Market
  Headlines (placeholder pending a real provider), and Upcoming Events —
  replacing v0.2's three-section layout.
- **`UpcomingEvents` shared module** (`frontend/src/game/systems/
  UpcomingEvents.ts`) — extracts "next schedule transition per agent"
  logic that both `BrainRoomHud` and `Newspaper` need, avoiding a second
  copy of the same computation.
- **`Task` categories** — tasks now carry a `category` (research / review
  / meeting / watchlist_update / news_scan / chart_analysis /
  documentation), inferred from the task label/agent via keyword
  matching in `nexus.py`.
- **Extended save schema** (`version: "0.3"`): `research`, `watchlist`,
  `memory`, and `meetingMinutes` are now persisted and round-tripped
  through save/load alongside every v0.2 field.
- **`docs/API.md`** and **`docs/VersionHistory.md`** created; `docs/
  Architecture.md` gained a full "Research & market intelligence (v0.3)"
  section and an explicit "Version 0.3 scope" (not-in-scope) section.

### Changed

- `nexus.py`'s `tick()` rewritten to orchestrate the new managers each
  tick: tick agents → `tick_research()` → record completions into memory
  → `tick_watchlist()` → maybe call a meeting (now discussion- and
  minutes-aware) → roll market news.
- Whiteboards now show Current Assignment / Latest Discovery / Priority /
  Completion % (2-line truncated format) instead of v0.2's single status
  line.
- Duplicated "complete old working task, start new one" logic (previously
  inlined separately for normal task rotation and for meeting attendance)
  consolidated into a shared `_replace_working_task()` helper in
  `nexus.py`.
- The old random `DISCOVERY_LINES` news generator was removed; discovery
  news is now driven directly by real research completions instead of an
  independent random roll.

### Fixed

- **Scribe missing from the top status bar**: `TopStatusBar.tsx` had its
  own locally hardcoded `AGENT_ORDER` array that was never updated when
  Scribe was added elsewhere. Fixed by removing the local array and
  importing the shared `AGENT_IDS` constant instead, eliminating this
  whole class of "forgot to add the new agent here" bug at its root.
- **`meetingMinutes`/`updatedAt` silently never updated**: `nexus.py`'s
  final `state.model_copy(update={...})` call used the wire aliases
  (`"meetingMinutes"`, `"updatedAt"`) instead of the actual Python field
  names (`"meeting_minutes"`, `"updated_at"`). Pydantic v2's `model_copy`
  writes directly into `__dict__` by field name, bypassing alias
  resolution entirely — the keys were silently absorbed as no-ops rather
  than raising an error. Found via direct WS-protocol soak testing
  (meeting cycles confirmed complete, but `meetingMinutes` stayed empty).
  Fixed by using the correct field names; documented as a standing
  "Gotcha" in `docs/Architecture.md` so it isn't reintroduced by a future
  `model_copy` call.
- **Meeting minutes over-citing an attendee's entire research history**:
  `build_minutes()`'s topic collection wasn't filtered by
  `status == "in_progress"`, so it cited every research item an attendee
  had ever touched instead of just their current focus. Fixed by adding
  the status filter.
- **Whiteboard text overflowing the board sprite**: the new 2-line
  enriched whiteboard text overflowed the small fixed-size board prop.
  Fixed with a coordinated two-sided change: shortened/truncated text
  server-side (`nexus.py`'s `_truncate()`) and an enlarged, smaller-font
  board with `lineSpacing` and wider `wordWrap` client-side
  (`Whiteboard.ts`) — Phaser's `wordWrap` only wraps by width, not by box
  height, so either fix alone was insufficient.

## v0.2

### Added

- **Three new agents** — Atlas (Strategy Lead: calm, strategic, rarely
  speaks, makes decisions), Echo (Technical Analyst: loves charts,
  frequently studies monitors), and Nova (Research Analyst: reads books,
  studies reports) — join Scout (Market Scanner), each with its own daily
  schedule, home room, mood/energy/memory, and personality-flavored
  dialogue lines per task.
- **Two new rooms** — Meeting Room (a table + six seats, a whiteboard, and
  the destination for NEXUS-triggered meetings) and Break Room (a coffee
  counter and seating, the destination for low-energy breaks).
- **Brain Room upgraded** into "Mission Control": an animated holographic
  market core, four monitor desks, and a React `BrainRoomHud` overlay
  panel showing live Company Status, Agent Status, Current Tasks, Market
  Status (placeholder — no live feed yet), and Recent Discoveries.
- **A fifth Lobby door** (Meeting Room, Break Room join Scout Office, CEO
  Office, Brain Room) and a **newspaper stand** ("TradeTown Daily") that
  opens a modal grouping news by Company News / Agent Discoveries / Market
  Headlines (placeholder).
- **A reusable `Task` system** (id, owner, priority, description, status,
  createdAt, completedAt) driven by each agent's schedule-block
  transitions, surfaced in the Brain Room HUD and newspaper.
- **NEXUS**, the backend orchestrator (`backend/app/nexus.py`): assigns/
  completes tasks, occasionally calls meetings and sends low-energy agents
  on breaks (both via a single `AgentOverride` mechanism), regenerates
  whiteboard text, and generates "discovery" news items. NEXUS does **not**
  trade or connect to any market data source — that plumbing is
  deliberately placeholder, wired for a future version.
- **Whiteboards** in every office, updating live via `whiteboard:updated`
  EventBus events.
- **EventBus extensions**: `agent:updated`, `room:entered`/`room:left`,
  `meeting:started`/`meeting:ended`, `whiteboard:updated`,
  `task:assigned`/`task:completed`, `news:updated`, `ui:newspaper`.
- **Extended save schema** (`version: "0.2"`): every agent's location,
  mood, energy, current task, and override; the task list; whiteboard
  text; meeting state; news feed; and time of day — all server-
  authoritative and round-tripped through save/load.

### Changed

- `ScoutNPC` generalized into `AgentNPC`, parameterized by `AgentId`, used
  for all four agents.
- `NPCManager` generalized from a single hardcoded Scout slot to a
  `Record<AgentId, AgentState>` registry.
- Lobby widened (30 → 72 tiles) to fit five buildings plus the newspaper
  stand comfortably.
- `RoomScene.getAgentSpawnPoint` made overridable so a room can lay out
  multiple simultaneous agents by design (Meeting Room's fixed seats,
  Brain Room's spread row) instead of always defaulting to a single-line
  spread.
- Agent name tags now only render when the player is within 32px, instead
  of always-on — rooms that legitimately hold all four agents at once
  (Brain Room, Meeting Room during a gathering) would otherwise show
  overlapping, unreadable tag text.

### Fixed

- **Right-facing player animation glitch**: the v0.1 `animation-config.json`
  row mapping for `Player.png` was wrong — it assumed 8 movement rows
  including dedicated `idle-right`/`walk-right` rows, but the sheet only
  has 6 real movement rows; rows 6–7 are actually attack/action-pose
  frames. Moving right briefly flashed a sword and a white crescent
  artifact over the character. Fixed by correcting the row mapping to the
  real 6 rows and mirroring the `-left` animation horizontally for
  right-facing movement (see `docs/Architecture.md`'s "Sprite sheet
  notes"). Caught via gameplay testing (Playwright screenshot), not code
  review.
- **Room-exit door never worked**: `RoomScene.update()` read
  `this.player.interactPressed` twice per frame — once for the
  agent-dialogue check, once for the door-exit check. Phaser's
  `JustDown()` consumes the "just pressed" flag on the first read, so the
  door-exit check always saw it as already consumed and pressing E to
  leave a room silently did nothing. Fixed by reading the flag once into
  a local and reusing it.
- **Dialogue box could get stuck across a scene transition**: pressing E
  while standing near both an agent and the exit door (rooms are small
  enough for both interact radii to overlap) could open a dialogue and
  transition the scene in the same frame, leaving the dialogue box
  permanently on screen with nothing left to close it. Door-exit and
  starting a new dialogue are now mutually exclusive, and `RoomScene`
  ignores E entirely while a dialogue is already open (the dialogue UI's
  own key handling owns the press instead).
- **Overlapping name tags when two agents cluster near each other**:
  distance-to-player tag visibility alone wasn't enough — Brain Room
  regularly holds all four agents at once, and two of them standing near
  *each other* (not just near the player) could both pass the radius
  check and show overlapping tags simultaneously (e.g. "EchoNova"). Tag
  visibility is now decided once per frame by `RoomScene`, which shows at
  most one tag — whichever agent is nearest the player — instead of each
  `AgentNPC` deciding independently.
- **Market Status/newspaper "Market Headlines" went permanently empty
  after enough play time**: two independent caps on the shared `news`
  list both trimmed strictly by recency across *all* categories combined.
  Discovery news fires far more often than market or company news (it's
  tied to every task-changing event across four agents, not a flat
  per-tick roll), so within roughly a day of game time discovery news
  crowded every market headline out of both the persisted list
  (`nexus.py`, `MAX_NEWS` → per-category `MAX_NEWS_PER_CATEGORY` via a new
  `_trim_news()`) and, independently, the WS broadcast shaping
  (`ws_manager.py`'s `build_state_message()` re-sliced to a flat "last
  10" on top of that). Fixed both: the persisted list now keeps the most
  recent items *per category*, and the broadcast sends that
  already-bounded list as-is instead of re-truncating it.
- **Duplicate/overlapping interact UI**: the old single-Scout interact
  handler opened both a full `DialogueBox` conversation and a separate
  in-world floating speech bubble showing the same first line — visually
  colliding, especially once multiple agents could be interacted with in
  the same room. The redundant speech-bubble mechanism was removed;
  `DialogueBox` is now the only interact UI.
- Old (v0.1-schema) saves no longer crash the backend on startup —
  `persistence.py` catches the schema-validation failure and starts a
  fresh v0.2 default state instead (see "Save format compatibility" in
  `docs/Architecture.md`).

## v0.1

Initial release: pixel-art HQ (main menu, Lobby, Scout Office, CEO Office,
Brain Room), one NPC (Scout) with a daily schedule/mood/energy/memory/
dialogue, WASD movement with camera-follow and collision, save/load
(autosave + manual, backend-persisted with a localStorage fallback), a
live WebSocket simulation feed, and Docker Compose deployment with an
nginx reverse proxy.
