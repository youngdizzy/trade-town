# TradeTown Design Bible

**Status:** Canonical. This document is the permanent source of truth for
what TradeTown is, why it exists, and what it will never become. Every
future version's scope is evaluated against this document before it is
evaluated against anything else — including a good idea. If a proposed
feature (however compelling) conflicts with a design pillar below, the
pillar wins, or the pillar changes first, deliberately, in a document
edit of its own.

This is a design document, not an implementation guide. For "how the code
is organized," see `PROJECT_STRUCTURE.md`. For "how NEXUS actually
works," see `NEXUS_ARCHITECTURE.md`. For "what's planned next," see
`ROADMAP.md`.

---

## Vision

TradeTown is a small pixel-art HQ inhabited by a team of AI employees who
research markets, discuss what they find, write it down, and get better
at their jobs over time — all in front of the player, all the time,
whether the player is watching or not.

The long-term vision is a single sentence: **a company you can walk
into.** Not a dashboard with mascots bolted on, not a trading bot with a
UI skin — an actual simulated company, with a building, a headcount, a
culture, and a memory, that happens to be staffed by AI agents whose job
is investment research. The game is the company. The company is the
game.

## Philosophy

Three beliefs shape every decision in this codebase, stated as directly
as possible:

1. **The simulation is real, not decorative.** When Atlas's whiteboard
   says "72% confidence," that number came from `research.py`'s
   `tick_research()` actually incrementing a `ResearchItem.confidence`
   field over real ticks — it is not a random label refreshed for
   flavor. Every visible number in TradeTown is backed by a real,
   inspectable piece of server state (see `GameSaveState` in
   `backend/app/schemas.py`). This is why the WebSocket protocol
   broadcasts full typed snapshots instead of pre-rendered strings: the
   client renders truth, it doesn't fake it.
2. **Legibility beats realism.** A real investment firm's internal state
   is illegible even to its own employees. TradeTown is not trying to
   simulate that. It is trying to make an AI research process *watchable*
   — every agent has exactly one active task, exactly one active research
   item, and a plain-English status line, on purpose, even though a real
   research desk juggles dozens of half-finished threads. Where realism
   and readability conflict, `docs/UI_UX_BIBLE.md`'s "no clutter" pillar
   wins.
3. **Nothing acts on money.** This is not a hedge — it is the single
   hardest boundary in the project (see "What TradeTown Is NOT," below).
   Every version's own brief restates it because it is load-bearing for
   trust: a game where AI agents can plausibly be mistaken for a real
   trading system must be relentlessly explicit about the line between
   "logs a candidate" and "places an order."

## Core Gameplay Loop

There is no win condition and no fail state. The loop is observational
and managerial, not competitive:

1. **Watch.** Time advances on its own (`GAME_MINUTES_PER_TICK` per
   `TICK_INTERVAL_SECONDS`, see `backend/app/config.py`) whether or not
   anyone is connected — the backend's `sim.py` loop is the actual clock.
   Agents move between rooms on a schedule (`schedule.py`), research
   symbols on a rotating queue (`research.py`), and occasionally gather
   for a meeting (`nexus.py`'s `_maybe_call_meeting`).
2. **Walk in.** The player's only verb in the world is movement +
   interact (`E`). Walking into a room shows whichever agents are
   scheduled there right now; walking up to one opens a dialogue line
   reflecting their current task. There is nothing to fail at here — the
   player cannot break an agent's schedule by talking to it.
3. **Read.** The Brain Room HUD, the whiteboards, TradeTown Daily (the
   newspaper), and Company Memory are all *read* surfaces, not *control*
   surfaces (v0.3 and earlier). The player's role so far is closer to a
   visitor with backstage access than a manager giving orders — that
   changes starting with Coach (v0.5, see `ROADMAP.md`), but even then
   the player directs *quality*, not individual trades.
4. **Return.** Because the simulation keeps advancing offline (persisted
   to SQLite every `PERSIST_INTERVAL_TICKS`), coming back later always
   shows a company that kept working without you — new research
   completed, new memory records, a newspaper with fresh headlines. The
   loop's payoff is the same one a good idle/management sim gives: "what
   did they get done while I was away."

This loop deliberately has no economy, no currency, no score, and no
combat. It is closer to *Powerwash Simulator*'s "watch the tile get
clean" satisfaction than to a trading game's win/loss cycle — the
satisfaction is watching a system you understand produce legible,
incremental progress.

## What TradeTown Is

- A **living-company simulation** where AI agents have schedules, moods,
  energy, memory, and visible research output — see `AgentState` in
  `backend/app/schemas.py` for the literal shape of "alive" here.
- A **transparent AI research demo.** Every agent's current task,
  confidence score, and reasoning trail (meeting discussion, memory
  records) is inspectable by the player at any time. Nothing about an
  agent's state is hidden or requires a debug flag to see.
- A **pixel-art management toy.** The player manages atmosphere and
  attention, not spreadsheets — walking into a room, reading a
  whiteboard, and leaving is a complete, satisfying unit of play.
- A **platform for a market-data adapter pattern.** `MarketDataProvider`
  (`backend/app/market_data.py`) exists specifically so a real feed can
  be added later without touching any downstream consumer — this is a
  design commitment, not an implementation accident.

## What TradeTown Is NOT

- **Not a trading platform.** No version of TradeTown through v0.9
  executes, queues, or simulates order execution against real capital.
  "Future trade candidate" flags (`memory.py`'s `FUTURE_TRADE_CONFIDENCE_THRESHOLD`)
  are logged notes for a *human* to consider later — never an
  autonomous action. This restriction is re-stated in every version's
  own brief on purpose; see `FUTURE_ARCHITECTURE.md` for how Paper
  Trading (v0.7) is scoped to still respect it.
- **Not a brokerage client.** No API keys for Schwab, Alpaca, IBKR, or
  any brokerage exist in this codebase, and none will until a version's
  brief explicitly authorizes it (currently targeted no earlier than
  v1.0 — see `ROADMAP.md`).
- **Not a real-time multiplayer game.** One save, one company, one
  player (`docs/Architecture.md`'s "single-tenant by design" note). There
  is no plan to add other players, guilds, or a shared world.
  TradeTown's "liveness" comes from the simulation continuing without
  you, not from other humans being present.
- **Not a spreadsheet with a mascot.** If a feature's only way to exist
  is as a numeric table with an agent's face pasted next to it, it
  belongs in a dashboard product, not TradeTown. Every system must have
  a legible *in-world* presence — a room, a prop, a schedule, a
  dialogue line — not just a data field.
- **Not a difficulty-driven game.** There is no fail state, no game
  over, no resource the player can run out of. Pacing comes from
  curiosity ("what did Nova find?"), not pressure.

## Long-Term Vision

By v1.0, TradeTown should be a company you could plausibly work at:
agents research, discuss, and flag ideas; a Coach agent (v0.5) helps the
*player* get better at evaluating those ideas; a Simulation Lab (v0.6)
lets flagged candidates be replayed against historical data with zero
real risk; Paper Trading (v0.7) lets the player practice execution
without money; a Risk Engine (v0.9) makes the company's own risk posture
visible and manageable; and only at v1.0, with all of that scaffolding
in place and explicitly re-authorized, does a real (optional,
opt-in, sandboxed) brokerage connection become possible. Every step
between here and there is designed to be useful and complete *on its
own* even if the project stopped at that version — see `ROADMAP.md` for
why each milestone is scoped as a standalone deliverable, not a
partial feature.

Past v1.0 (see `ROADMAP.md`'s v1.x/v2.0 entries), the vision widens from
"one company" to "a genre": user-authored agents, a strategy
marketplace, and multi-company play — all still bound by the same
pillars below.

## Inspiration

Named honestly, including where TradeTown deliberately diverges:

- **Two Point Hospital / Software** — the "walk through your own
  simulation and watch it work" camera and room-based staff AI. TradeTown
  borrows the room-presence model (`RoomScene.refreshAgentPresence()`)
  directly from this lineage, but drops the failure/pressure loop
  entirely.
- **Stardew Valley** — the pixel-art HQ, the schedule-driven NPCs, the
  gentle non-punishing pacing. TradeTown's `AnimatedActor`/`AgentNPC`
  movement and the cute-fantasy-rpg asset pack are a direct aesthetic
  descendant.
- **Universal Paperclips / idle-sim genre** — the "it kept running while
  you were away" payoff. TradeTown's persisted, always-ticking backend
  (`sim.py`) is this mechanic implemented with a real simulation instead
  of a multiplier.
- **Bloomberg Terminal / real trading-desk research tooling** — for tone
  and vocabulary only (confidence scores, watchlists, research queues),
  explicitly *not* for interaction model. A real terminal is dense and
  expert-only; TradeTown's HUD is deliberately the opposite (see
  "Readable Information" pillar below).
- **The Sims** — mood/energy/memory as visible, legible agent state
  rather than hidden NPC variables. `AgentState.mood`/`energy` and the
  agent memory log are TradeTown's version of Sims' needs bars, tuned
  for "AI employee" instead of "person."

## Design Pillars

Every pillar below is a real, load-bearing constraint — each has already
shaped a concrete decision in the shipped codebase, cited as evidence.

### 1. Living AI Company

Agents are not decorative NPCs with a name and a walk cycle. They have
server-authoritative state (`AgentState`), a daily schedule
(`AGENT_SCHEDULES`), a rotating research assignment (`research.py`'s `tick_research()`),
and a persistent memory (`CompanyMemory`). The simulation runs whether or
not a client is connected (`sim.py`'s background loop is independent of
WebSocket connections). *Evidence this is real, not aspirational:* the
whole v0.3 build exists because this pillar demanded a research/watchlist/
discussion system, not just more decoration.

### 2. Readable Information

Every panel answers "what's happening right now" in under two seconds of
reading. The Brain Room HUD (`BrainRoomHud.tsx`) shows one line per
agent, one active research item per researcher, and animated (not
snapping) confidence bars — never a raw dump of the underlying state.
*Evidence:* `nexus.py`'s `_truncate()` helper exists specifically to cap
whiteboard text to what a small pixel-art prop can legibly hold, even
though the underlying research summary might be longer.

### 3. Beautiful, Honest Pixel Art

Every visual asset comes from the single licensed pack
(`assets/cute-fantasy-rpg/`) via the generated manifest — no external art,
no AI-generated sprites, no placeholder programmer art shipped as final.
Where the pack doesn't have an asset TradeTown needs (multiple distinct
character sprites, for instance), the honest solution is tint + a small
in-world badge glyph (see `AgentProfiles.ts`), not a fake extra sprite
sheet. *Evidence:* the v0.3.1 NPC-distinctness work explicitly chose
"badge + tint + behavior" over inventing new art precisely because of
this pillar.

### 4. No Clutter

A panel that needs a scrollbar to show its most important line has
failed. Every list in the game is bounded server-side before it's ever
sent (see `docs/API.md`'s "Bounding / trimming" table — tasks, news,
research, memory, and meeting minutes are all capped) specifically so
the client never has to decide what to hide. *Evidence:* the per-category
news cap (`MAX_NEWS_PER_CATEGORY`) exists because a single flat cap let
frequent discovery news crowd out rare market headlines — a clutter bug,
fixed as a clutter bug.

### 5. Modular Systems, Not a Monolith

Every subsystem is a manager with one job, connected through the
`EventBus` (frontend) or explicit function composition in `nexus.tick()`
(backend) — never a god object. `MarketDataProvider` is an `ABC` swapped
via one registration point specifically so a real vendor can be added
without touching `watchlist.py`, `research.py`, or any UI
component. *Evidence:* Scribe (a fifth agent, v0.3) was added with *zero*
Phaser scene changes, because every consumer already iterated `AGENT_IDS`
instead of a hardcoded roster.

### 6. Transparency Over Automation

The player can always see *why* an agent believes what it believes: a
confidence score, a discussion transcript, a memory record citing what
was researched. Nothing in the simulation is a black box the player must
simply trust. This is also why "future trade candidate" is a flag
visible in Company Memory, not a silent internal decision — the player
should be able to audit every claim TradeTown's agents make about the
market, even in v0.3 where nothing acts on those claims yet.

### 7. Deployability Is a Feature

TradeTown must always run with `docker compose up -d --build` on a
bare Ubuntu VPS, with no separate Node/Python/Nginx install on the host
(see `docs/DeveloperGuide.md`). This isn't infrastructure trivia — it's a
design pillar because it keeps the project honest about complexity: if a
feature can't be explained and deployed this simply, it's probably
solving the wrong problem for this project's stage. Every version's
brief has required Docker verification as a completion gate for exactly
this reason.

## Explaining the Major Design Decisions

A few decisions look arbitrary from the outside. They aren't — each
follows directly from a pillar above:

- **Why one active research item per agent instead of a real queue?**
  Readable Information. A visible backlog of 40 half-started research
  items is realistic and unreadable. One active item, one confidence
  bar, is legible at a glance in the Brain Room HUD.
- **Why does NEXUS orchestrate everything from one `tick()` function
  instead of each agent running independently?** Living AI Company +
  Modular Systems in tension, resolved deliberately: agents *feel*
  independent (each has its own schedule and state) but the simulation
  needs one authoritative, ordered pass per tick so meetings, task
  changes, and research completions don't race each other within the
  same tick (see the `_replace_working_task` duplicate-id bug in
  `CHANGELOG.md` for what happens when that ordering isn't respected).
- **Why is the server the sole source of truth for agent state, with the
  client only locally authoritative for the player and settings?** Living
  AI Company. If the client could fudge agent state, the company
  wouldn't be "alive" independently of the player — it'd be a puppet.
- **Why mock market data by default instead of shipping a free-tier real
  API key?** Not a Trading Platform + Deployability Is a Feature. A real
  key ties the project to a vendor's rate limits and terms of service by
  default; mock data keeps the out-of-the-box experience deterministic,
  free, and legally uncomplicated, while the adapter pattern keeps a real
  integration a config change away, not a rewrite.
- **Why no fail state, ever?** Core Gameplay Loop. TradeTown's tension is
  curiosity, not risk — introducing a fail state would require
  introducing stakes, which requires introducing something the company
  can lose, which the "not a trading platform" boundary explicitly
  forbids being money. Any fail state would have to be manufactured and
  would read as arbitrary.
