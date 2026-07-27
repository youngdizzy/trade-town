# Changelog

All notable changes to TradeTown are documented here. Versions are
development milestones, not semver releases.

## Unreleased

### Fixed

- **Opening the newspaper (or Company Memory / Coach Dashboard) made the
  game feel stuck** — these full-screen overlays only had a mouse-click
  "Close" button (no keyboard close, unlike the existing `DialogueBox`)
  and didn't pause the world, so the player kept invisibly moving behind
  the panel while it was open. Added a shared `useCloseOnEscape` hook (all
  three panels now close on Escape) and a new `world:overlayOpen` event
  that a `GameManager.worldActive` flag tracks; `LobbyScene` and
  `RoomScene` now skip movement/interaction processing entirely while any
  overlay (or the pause menu) is open, rather than just hiding the world
  while it silently keeps simulating underneath.
- **The ESC pause menu's Resume never actually resumed** — a pre-existing
  bug independent of the above: `togglePause()` used
  `game.scene.getScenes(true)` to find the scene to resume, but that
  filters to *currently active* (`RUNNING`) scenes — a scene that was just
  paused no longer satisfies that, so the resume loop always iterated zero
  scenes and input stayed frozen after un-pausing. Superseded by the same
  `worldActive` flag above, which doesn't depend on Phaser's scene-pause
  state machine at all.
- **Held movement/pause keys could re-trigger themselves across an
  overlay transition** — Phaser's `Key.JustDown()` is a read-and-consume
  flag set by the raw keydown event regardless of whether anything is
  currently reading it; without an explicit reset, closing the newspaper
  with Escape could leave the scene's own pause key "still just-pressed"
  the instant the world reactivated, immediately popping the pause menu.
  `GameManager` now calls `resetKeys()` on the active scene's keyboard
  whenever `worldActive` transitions back to true.
- **Hedge collision could snag while walking diagonally past it** — the
  hedge wall was built from one 16x16 static Arcade body per tile;
  abutting separate bodies are a known source of a moving body catching
  at the seams between them. `buildHedges()` now still places one visual
  tile per cell (so the cap/fill pixel art reads correctly) but registers
  a single merged collision rectangle per contiguous hedge run instead —
  no internal seams left to catch on.

### Changed

- **Asset pipeline reorganization** — `assets/cute-fantasy-rpg/` restructured
  from pack-native folders (`Tiles/`, `Player/`, `Enemies/`, `Animals/`,
  `Outdoor decoration/`) into five purpose-named folders: `tilesets/`,
  `characters/{player,enemies,animals}/`, `props/` (incl. `buildings/`),
  `animations/`, and `ui/`. `scripts/generate-assets.mjs`'s categorization
  and every asset id referenced in scene/entity code were updated to match
  (`tiles/grass-middle` → `tilesets/grass-middle`, `player/player` →
  `characters/player/player`, `outdoor-decoration/buildings/*` →
  `props/buildings/*`, etc.) — see `docs/Architecture.md#asset-pipeline`.
- **`generate-assets.mjs` now does a true sync**, wiping
  `frontend/public/assets/` before re-copying instead of copying
  additively — a renamed or removed source file no longer leaves a stale
  orphaned copy served alongside the current one.
- Consolidated the premium-pack license note (previously nested inside
  `Outdoor decoration/Buildings/`) into a single root-level
  `assets/cute-fantasy-rpg/PREMIUM_PACK_LICENSE.txt` covering all
  premium-sourced files.

### Added

- **Curated premium-pack imports**: `animations/` (lilypad, cattail, and
  grass-sway sprites, now animated around the Lobby's pond) and `ui/`
  (two icon sheets, staged for future in-game UI use, not yet drawn
  anywhere). Deliberately curated, not a wholesale import — the premium
  pack ships hundreds of files (mounts, crops, cave tiles, weather
  effects, …) outside TradeTown's office-simulation setting.
- **One ambient chicken** near the Lobby's Barn (Performance Center) —
  the free pack's animal sprites had been discovered and manifest-
  registered since v0.1 but never actually rendered anywhere. Caught in
  the process: `characters/animals/chicken/chicken.png` is a 2x2 grid of
  4 poses, not a single sprite as its `"kind": "static"` entry assumed —
  cropped a clean single frame (`chicken-idle`) rather than render the
  raw sheet.

### Lobby redesign: a real town square, paths, and street furniture

- **The pond moved to the map's dead center** and the town square around
  it now fills the entire gap between the two building rows (18x12
  tiles) — previously it sat off in a corner near the spawn point, more
  like leftover decoration than a town's actual center.
- **The whole road network — square included — went through three
  materials** before settling: a hand-picked cobblestone cell (square
  only, roads still on the old flat tile), `tilesets/farmland-tile`
  (packed-dirt, applied uniformly), then `tilesets/wood-floor`, a
  blue-grey square-tile pattern the user hand-picked from an uploaded
  reference sheet — replaced outright each time rather than kept as a
  second material, so the whole town reads as one consistent surface.
  Itself later superseded by `tilesets/dirt-path` — see the courtyard
  redesign section below. Every candidate confirmed to tile with zero
  seams before use.
- **The pond is 2x bigger and actually curved** — swapped the old
  rectangle of flat water tiles for `props/pond-curved`, a single
  pre-composed 48x48 organic pond graphic discovered inside
  `tilesets/water-tile`'s source sheet (that sheet turns out to be a
  ready-made pond/island illustration, not a repeating tile; its opaque
  corner pixels are the exact same green as the grass tile, so it drops
  onto the ground with no visible seam), scaled up 3.6x. Every piece of
  pond decor (lilypads, cattails, dock, ducks, flowers) and the four
  corner benches scaled up to match.
- Removed a decorative fence that read as a random jumble in the
  bottom-left corner — `props/fences` turned out to be a 4-piece
  tileset (post/rail/lattice/post) meant to be sliced into individual
  tiles and assembled, not a single sprite; rendering the whole sheet as
  one image (an earlier pass here did exactly that) shows all four
  disconnected pieces crammed together.
- **Fixed the Hall of Fame windmill's sails, which weren't mounted on
  the tower** — `Windmill.png`'s source file turned out to be the tower
  and the sail assembly side by side, not pre-composited; rendering it
  whole showed the sails as a disconnected chunk floating next to the
  building instead of on it. Recomposited at the asset level (sails
  layered onto the tower at their shared native Y-coordinate, then
  trimmed) rather than worked around in scene code.
- **Paths now lead to every building's door**, not just past it — a
  short spur connects the road to each doorstep, closing the 2-tile gap
  between the road and the building's base.
- **Fixed three spurs that missed the actual door** — they'd been
  computed from each building sprite's horizontal bounding-box center,
  which lines up with the door for most of these buildings but not all:
  Blacksmith_House_Blue's canvas is a house-plus-forge assembly with the
  door well left of the bbox midpoint (the spur landed on the forge/
  anvil instead), and Fisherman_House_Base_Blue/Shed_Base_Red both have
  a door a few pixels left of center. Measured each door's true offset
  directly from its source PNG and added a `doorOffsetX` correction
  (Scout Office, Brain Room, Break Room) used by the path spur, the
  door's interact zone, and its flanking flowers alike, rather than
  patching only the visual symptom.
- **The pond** gained a small wooden dock (cropped from the bridge-wood
  sheet), two ducks, and more flowers ringing the shore, alongside the
  lilypads/cattails already added.
- **Benches flank the pond on all four corners** of the town square, and
  flickering lampposts stand at its east/west entrances — the lamppost
  is a genuine 6-frame animation (a flickering flame), not a static
  prop.
- **Two new tree varieties** (spruce, fruit) join the oaks near the
  plaza, each a middle frame cropped from a 3-frame growth-stage sheet.
- Fixed a real bug found along the way: `generate-assets.mjs`'s `public/`
  mirror had gone stale (70 files served for 38 current ones) after the
  earlier folder reorg, since the sync only copied additively and never
  pruned; confirmed the fix (wipe-then-copy, from the prior changelog
  entry) is holding at the correct count through this round of changes.

### Courtyard redesign, round two: hedges, fountain, market stalls, and a denser village cluster

Matched a reference screenshot of a similarly-themed HQ-town layout —
dense building cluster, hedge-lined courtyard, dirt path, fountain,
market stalls — rather than TradeTown's original evenly-spaced rows.

- **All nine buildings pulled in toward the map's center third**, rather
  than spread edge-to-edge across the full 1728px width (back row span
  went from 67% of the map width to 46%, front row from 75% to 49%).
  CEO Office anchors the back row at dead center, the same "hero
  building facing the square" role the reference's Command Center
  plays. Freed up roughly 400px of park margin on both sides that used
  to be empty grass past the corner trees — now home to the fountains
  and extra tree variety (see below).
- **The road network is paved in `tilesets/dirt-path`**, a flat
  warm-tan tile with a faint speckle mark, cropped from the premium
  pack's `FarmLand_Tile.png` (a clean interior cell of an otherwise
  blob-shaped autotile sheet) — superseding `tilesets/wood-floor` to
  match the reference's dirt-path square.
- **A low hedge wall borders the square's east/west edges**
  (`props/hedge-tiles`, a 4x4 premium-pack sheet), with a 2-tile gateway
  at each existing lamppost rather than the hedge running straight
  through them. Walk-blocking like the benches and lampposts, not
  decoration you phase through.
- **Two fountains flank the courtyard** in the newly-freed park margin —
  a flat stone basin on one side, a taller spouting tier on the other
  (both frames of one `props/fountain` sheet).
- **Two market stalls (red/blue striped awnings)** sit outside Trading
  Floor's entrance, echoing the reference's stall row outside its
  Armory.
- **The pond's dock is now a proper ramp, not a sideways plank** — the
  same `props/dock` graphic, previously rotated 90° to jut off the east
  bank, now sits unrotated on the south bank (its native portrait shape
  already reads as a ramp) running from shore down into the water, with
  a small rowboat (`props/boat`) resting just off its end.
- Caught and fixed a placement bug from the rearrange itself: Hall of
  Fame and Trading Floor's first-pass positions landed almost exactly on
  the new hedge/lamppost line, and the spruce tree's original ±260
  symmetric offset landed inside Hall of Fame's new footprint, half-
  hiding it behind the roof. Both back-row buildings (which sit above
  the plaza's top edge) tolerate x-overlap with the plaza fine, but
  front-row buildings (which sit inside the plaza's own vertical span at
  y=336) can't — moved Hall of Fame, Trading Floor, and the extra tree
  spots clear once this was caught in a live screenshot pass.
- **The dirt path didn't land** — reverted `tilesets/dirt-path` back to
  the grey square-tile pattern from two rounds ago
  (`tilesets/cobblestone-grey`, the same cell used previously as
  `tilesets/wood-floor`, now under a name matching how it actually
  reads).
- **The pond, dock, and boat are ~2 tiles wider** — `POND_SCALE` bumped
  from 3.6 to 4.27; every pond-relative decor offset (lilypads, cattails,
  dock, boat, ducks, flowers, the four corner benches) scaled by the
  same ratio rather than hand-tuned individually, to keep the same
  relative layout at the larger size.
- **Fixed two real bugs the proportional-scaling approach above
  introduced**, both caught from a live screenshot: benches (scaled
  outward to keep clear of the bigger pond) ended up overlapping the
  hedge on the plaza's other side instead — reverted them to their
  original, already-clear offsets, since the wider pond needed no help
  there. The dock, boat, and the water-bobbing duck all landed on dry
  bank/grass instead of water — `props/pond-curved`'s water region turns
  out to be asymmetric within its own canvas (extends 11-15px from
  center depending on direction, well short of the ~19px the bank's
  jagged spikes reach), so a single scale-up ratio pushed water-bound
  decor right past the actual shoreline. Repositioned by checking each
  candidate spot against the source PNG's actual pixels rather than
  computed radii.
- Nudged the dock and the water-bobbing duck up one tile (16px) at the
  user's request, moving both a bit further from the south shore and
  deeper into open water — reconfirmed against the source pixels that
  both still land correctly (dock's north end further into water, its
  south end still past the bank on grass) before shipping.
- Moved the boat up a tile and the east duck down a tile, at the user's
  request. The east duck was originally the one "preening on the bank"
  rather than swimming (see above) — moving it south by a tile put it
  past the bank into water too, so both ducks now bob on the pond.

### Nine distinct agent character sprites

- Each of the nine AI employees now renders from its own
  `characters/player/player-<id>` sheet — hair, shirt, and pants
  hue-shifted to that agent's existing identity color (the same color
  used for its HUD dot) — instead of the player's shared sheet washed
  with a single `sprite.setTint()`. Investigated using the premium pack's
  modular character rig (separate Player_Base/Hair/Chest/Legs layers)
  first, but its ~112-row animation layout didn't match this project's
  verified 6-row convention and reverse-engineering it reliably wasn't
  feasible without risking a broken walk cycle; palette-swapping the
  already-verified sheet instead carries zero animation risk.
- Fixed a latent bug found while touching this code:
  `AgentNPC`'s constructor called `sprite.play("player/player::idle-down")`
  — a hardcoded pre-reorg animation key that the folder-reorg's string
  rename had missed because it wasn't wrapped in matching quotes. It
  silently no-opped since the key no longer existed in the manifest.

## v0.6

### Added

- **Trading Floor room** (`frontend/src/game/scenes/TradingFloorScene.ts`) —
  the ninth Lobby door. Large trading desks, wall monitors, a live market
  ticker bound to the watchlist, a Central Command display bound to the
  live paper portfolio, individual desks for Sentinel/Pulse/Guardian,
  a conference table, server cabinets, and status lights that reflect
  Guardian's standing risk watch.
- **Three new agents**: Sentinel (Risk Management), Pulse (Market
  Scanner), Guardian (Portfolio Protection) — profiles, schedules, and
  dialogue in both backend (`backend/app/agents.py`, `schedule.py`) and
  frontend (`AgentProfiles.ts`, `Schedule.ts`, `DialogueManager.ts`).
  TradeTown now has nine agents total.
- **Order-book paper trading engine** (`backend/app/broker.py`) —
  PaperBroker: market/limit/stop/take-profit/stop-loss orders go through
  an explicit `open → filled/cancelled` lifecycle (`place_order()` /
  `tick_broker()`), one tick of latency between placement and the
  earliest possible fill, same as every other NEXUS system. Completely
  simulated — no brokerage SDK, no API key, no real order-execution path
  — but shaped so a real adapter (Schwab/IBKR/Alpaca) could later
  implement the same two calls, mirroring `market_data.py`'s provider
  pattern.
- **RiskEngine** (`backend/app/risk_engine.py`) — Sentinel's configurable
  trade-approval gate (position size, portfolio drawdown, open-position
  count) and Guardian's exposure/concentration monitor, both backing
  votes in the new decision pipeline. `RiskLimits` are configurable and
  persisted; Sentinel/Guardian can reject a trade outright.
- **ScannerManager** (`backend/app/scanner.py`) — Pulse's continuous
  market scan across the watchlist (stocks, ETFs, indexes, gold,
  bitcoin), flagging gap ups/downs, breakouts, volume spikes, and high
  volatility as `ScannerAlert` records.
- **VotingManager + DecisionEngine** (`backend/app/voting.py`,
  `backend/app/decision.py`) — every high-confidence completed research
  item becomes a trade candidate voted on by the four researcher agents
  plus Sentinel and Guardian; Atlas's `decide_trade()` produces a
  permanent, explainable `TradeDecision` (research/technical/
  fundamental/risk summaries, supporting/opposing agents, confidence,
  final reasoning). Any Sentinel "risk too high" or Guardian "position
  too large" vote is an absolute veto, regardless of researcher votes.
- **TradeJournal** (`backend/app/journal.py`) — stamps every closed
  trade with a coach review, lessons learned, a link back to the
  decision that approved it, and a placeholder screenshot field. Also
  closes a v0.5 gap: `PaperTrade.coach_review`/`.lessons_learned`
  existed in the schema since v0.5 but nothing had ever populated them.
- **Brain Room HUD expansion** — Open Positions, Pending Orders, Risk
  Management (score/limits/warnings), Latest Decision & Votes, and
  Scanner Alerts sections, alongside everything v0.3–v0.5 already showed.
- **TradeTown Daily expansion** — Today's Trades, Top Opportunities,
  Performance, Coach's Review, Scanner Alerts, and Company Rating
  sections added to the newspaper.
- **Save system** — `GameSaveState` gained `riskLimits`, `riskWarnings`,
  `scannerAlerts`, and `decisions`; save version bumped to `"0.6"`.
  Orders and trades gained order-type/fill/decision-link fields. Old
  saves are not migrated — see `backend/app/persistence.py`'s existing
  "start fresh on schema mismatch" policy, unchanged since v0.1.

### Design notes / intentional simplifications

- TradeTown has no real sector taxonomy, so "sector concentration" risk
  checks are implemented as per-symbol concentration of portfolio equity
  instead — see `risk_engine.py`'s module docstring.
- `scanner.py`'s "breakout" detection is threshold-based against the
  current quote only (no persisted rolling price history yet) — a true
  multi-period range breakout needs a real historical
  `MarketDataProvider`, which doesn't exist yet (same boundary
  `watchlist.py` already documents for v0.3).
- `decision.py`'s technical/fundamental summaries explicitly state that
  no dedicated technical/fundamental analysis pass exists, rather than
  fabricating analysis that was never run.

**No live brokerage connections. No real money. Every "trade" is a row
in `GameSaveState.paper_portfolio`, nothing more — see
`docs/DESIGN_BIBLE.md`'s "What TradeTown Is NOT."**

## v0.5

### Added

- **Coach, a sixth agent** (Performance & Improvement: encouraging but
  exacting, asks more questions than it answers) — home room Performance
  Center, own daily schedule split across the Performance Center/Brain
  Room/Simulation Lab, and the first agent whose job is evaluation, not
  research or record-keeping. Coach never places or closes a trade — see
  `backend/app/coach.py`'s module docstring.
- **Paper Trading engine** (`backend/app/portfolio.py`,
  `backend/app/paper_trading.py`) — a fully simulated $100,000 starting
  account. High-confidence completed research (≥85%, the same threshold
  that already flagged "future trade candidates" in v0.3) can open a
  `PaperPosition`; positions mark-to-market every tick and close after a
  minimum simulated hold, producing a `PaperTrade` with PnL, duration,
  and supporting/opposing agents. Hold duration is tracked against
  TradeTown's in-game clock (`opened_sim_minutes`), not wall-clock time —
  consistent with how research confidence already advances by tick count.
  **No real brokerage is connected and no real capital is ever at risk.**
- **Simulation Lab** (`backend/app/simulation.py`) — a new room where
  agent-authored `Strategy` objects queue, run, and complete as
  `BacktestSession` → `SimulationResult`, using explicitly placeholder
  backtest math (see the module docstring — no real historical
  `MarketDataProvider` exists yet). Structured so a real historical
  provider, Monte Carlo variant, or parameter optimizer can be added later
  as new functions without changing the queueing/progress/archiving
  pipeline.
- **Hall of Fame** (`backend/app/hall_of_fame.py`) — a new room
  celebrating best research, best strategy, best simulation, lowest
  drawdown, longest winning streak, highest confidence accuracy, best
  monthly performance, and top agent. Entries are evaluated every tick and
  filed only when a new record is actually set (before/after length
  diffing), then logged to Company Memory.
- **Learning System** (`backend/app/knowledge.py`) — every closed paper
  trade is fed to `derive_lesson()`, producing a `lesson` (on a win) or
  `mistake` (on a loss) Company Memory record with the trade's reason,
  market conditions, confidence, and PnL — TradeTown's training-data
  record for the Coach's mistake/recommendation analysis.
- **Company Score** (`backend/app/company_score.py`) — a seven-metric
  rating (Research Quality, Decision Quality, Risk Management, Paper
  Trading Performance, Team Coordination, Knowledge Growth, Simulation
  Success) recomputed every tick and shown in an expanded Brain Room HUD
  and the Performance Center's in-world scoreboard.
- **Coach reports and Coach Dashboard** — weekly (every 7th day) and
  monthly (every 30th day) `CoachReport`s generated at the evening review
  (20:00), covering agent rankings, research/confidence accuracy, win/loss
  rate, risk score, common mistakes, and recommendations. A new
  `CoachDashboard.tsx` React modal (opened from a new "Coach" toolbar
  button) surfaces the latest weekly/monthly report and the live overall
  company score.
- **Performance analytics** (`backend/app/analytics.py`) — daily,
  weekly, monthly, and all-time `PerformanceSnapshot`s (return %, win
  rate, max drawdown, placeholder Sharpe/Sortino, average holding time,
  research accuracy, confidence accuracy), recorded on their respective
  cadences.
- **Three new rooms** — Simulation Lab, Hall of Fame, and Performance
  Center — each with a distinct floor tile, procedural props (server
  racks, trophy cases, a scoreboard), and a live in-world text readout
  synced to the same WebSocket state driving the React HUD. The Lobby
  widened from five doors to eight to fit them.
- **Company Memory gained six new categories** — `lesson`, `mistake`,
  `strategy`, `coach_review`, `simulation`, `paper_trade` — all
  searchable/filterable in the existing `CompanyMemory` viewer alongside
  v0.3's seven categories.
- **Extended save schema** (`version: "0.5"`): `paperPortfolio`,
  `strategies`, `backtestSessions`, `simulationResults`, `hallOfFame`,
  `coachReports`, `companyScore`, and `performanceSnapshots` are now
  persisted and round-tripped through save/load alongside every v0.3
  field.

### Changed

- **Backend "manager" modules stay function modules, not classes** — the
  v0.5 brief names eight services (CoachManager, SimulationManager,
  PaperTradingManager, PortfolioManager, AnalyticsManager,
  HallOfFameManager, PerformanceManager, KnowledgeManager); all eight are
  implemented as plain function modules (`coach.py`, `simulation.py`,
  `paper_trading.py`, `portfolio.py`, `analytics.py`, `hall_of_fame.py`,
  `company_score.py`, `knowledge.py`) naming their conceptual role in the
  module docstring, matching the established `research.py`/`watchlist.py`
  precedent (see `docs/CODING_STANDARDS.md`).
- **Scribe extended, not bypassed** — `scribe.py` remains CompanyMemory's
  sole writer; it gained `record_paper_trade`, `record_simulation_result`,
  `record_coach_report`, and `record_hall_of_fame_entry` rather than
  letting the four new modules call `memory.record()` directly.

## v0.4

Documentation only — see `docs/VersionHistory.md`'s "v0.4 — Design &
Architecture Foundation" entry. No application code changed.

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

- **Agents made visually and behaviorally distinct.** Every agent shares
  the same sprite sheet (the asset pack only ships one), so tint alone
  wasn't enough to tell them apart at a glance in a crowded room. Each
  agent now also gets an always-visible badge glyph above its head
  (unlike the name tag, never proximity-gated: 🔍 Scout, ♟ Atlas, 📈 Echo,
  📚 Nova, 📜 Scribe), a wider tint spread (Scribe moved off a
  near-duplicate of Atlas's gold onto a distinct rose), and its own
  wander radius / idle-pause chance drawn from its personality blurb
  (`AgentProfiles.ts`/`AgentNPC.ts`) — Atlas and Scribe barely move,
  Scout roams widely and rarely idles.
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

### Fixed (found via a live gameplay walkthrough after the initial v0.3 build)

- **`currentTask` silently frozen forever, for every agent**: the same
  `model_copy(update=...)` alias bug as the `meetingMinutes` fix above,
  in a different call site — `_tick_agent()`'s and `_maybe_call_meeting()`'s
  return values both used `"currentTask"` (the wire alias) instead of
  `current_task` (the real field name), so every agent's task text froze
  at whatever `_default_agent_state()` set it to on the very first tick,
  forever, while `location` kept updating normally on the correct
  schedule. Found by walking into the Brain Room and noticing an agent's
  displayed location and task text belonged to two different schedule
  blocks — confirmed with a raw WebSocket probe showing Atlas stuck on
  "Reviewing overnight strategy" through 2.5 hours of sim time and
  several break/meeting cycles while its location cycled correctly.
- **Duplicate task ids / React key collision**: an agent's meeting
  override ending and a brand-new meeting starting could both call
  `_replace_working_task()` for that same agent within one tick,
  producing two `Task` objects with an identical
  `task-{agent}-{day}-{hour}-{minute}` id. Fixed by disambiguating with a
  numeric suffix on collision.
- **Newspaper and Company Memory could both be open at once**: neither
  modal's close action touched the other's open flag, so opening one
  while the other was already open (or open-but-unnoticed) left it stuck
  open underneath, invisible once the topmost one closed. Opening either
  now closes the other (`gameStore.ts`).
- **`NPCManager.loadAgents()` torn-map reads**: it fired one
  `"agent:updated"` event per agent inside its update loop, so a listener
  reacting mid-loop (`gameStore`'s agents snapshot) could see a map where
  only some agents reflected the new tick and the rest were still stale.
  The whole map now updates before a single event fires.
- **Whiteboards clipping the room's own wall**: the v0.3 overflow fix
  enlarged every board from 72×44 to 92×58 world px but nobody moved the
  three rooms' placement coordinates to match, so the boards in Scout
  Office and CEO Office now overflowed 6px past the room's side wall
  (clipping the board itself, not just its text) and all three boards'
  "WHITEBOARD" title label sat a few px above the room's top wall.
  Re-positioned all three placements with enough clearance for the
  larger board size.

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
