# TradeTown Design Bible

## Design Philosophy — The Self-Improving Company

**Status:** Foundational. This section is the highest-level design
philosophy for TradeTown and outranks every other section in this
document, including the pillars below. It is never overwritten or
removed — future updates may only expand it. If a proposed idea
conflicts with it, the philosophy takes priority: the idea is redesigned
or dropped, never the reverse.

TradeTown is **not** just a trading game. TradeTown is a living AI
company that continuously learns, improves, and evolves over time. Every
mechanic, building, department, employee, and AI system should
contribute toward one ultimate objective: **building the world's first
self-improving AI investment company.**

### The Golden Question

Before adding any new feature, ask:

> "Will this make the company smarter five years from now?"

If the answer is **yes**, the feature is worth building. If the answer
is **no**, the feature should be redesigned or removed. The company
should become more intelligent through systems — not through
unnecessary complexity. (This is the same discipline the "No Clutter"
pillar already enforces at the UI layer; the Golden Question is that
same discipline applied to the whole company, not just a panel.)

### The Compounding Principle

Every system should strengthen multiple other systems. For example: a
better Academy creates better employees; better employees produce
better research; better research creates better breakthroughs; better
breakthroughs improve the company's Operating System; the Operating
System strengthens future employees; future employees make better
decisions; better decisions increase the company's DNA and legacy.
Knowledge should compound exactly like long-term investing. Nothing
should exist in isolation. Everything should improve something else.

### Design Principles

Every new feature should improve at least one of the following:

- Trading Performance
- Decision Quality
- Risk Management
- Research Quality
- Learning Speed
- Collaboration
- Discipline
- Innovation
- Company Culture
- Long-Term Knowledge
- CEO Decision Making

Features that do not improve the company should not be added.

### The Company Philosophy

TradeTown values:

- Truth over Ego
- Evidence over Authority
- Process over Prediction
- Discipline over Emotion
- Teamwork over Individual Brilliance
- Continuous Learning over Complacency
- Knowledge Preservation over Short-Term Success
- Innovation through Research
- Respectful Debate
- Long-Term Thinking

### Probability First Trading Philosophy

TradeTown does not predict the market. TradeTown thinks in
probabilities.

This is the company's foundational trading philosophy — permanent,
non-negotiable, and inherited automatically by every department,
employee, AI agent, strategy, simulation, executive review, Academy
lesson, and Mentor Track, present and future. No department ever needs
to restate it; no future feature ever needs to redefine it. If a future
feature's own design conflicts with it, the feature is redesigned, not
this philosophy — the same rule the Design Philosophy above already
applies to itself.

**The core belief.** Nobody — not the company, not any employee, not any
model — knows what the market will do next. TradeTown is not in the
prediction business. It is in the probability business. The company
never asks *"What will the market do?"* It asks *"Does this setup
satisfy a validated statistical edge?"* Uncertainty is permanent and is
never eliminated — only managed.

**Evidence creates confidence. Confidence justifies capital allocation.**
A trade is proposed only when real evidence — a validated strategy, a
favorable market regime, acceptable risk, sufficient liquidity — is
already on the table. Confidence is *calculated* from that evidence,
never felt. Capital is allocated only to what the evidence has already
earned, never to a hunch.

**The process matters more than any single outcome.** Good decisions can
still lose. Bad decisions can still win. TradeTown grades the *decision*
— did it follow the validated framework, was risk accepted before entry,
was the setup real — not the one trade's dollar result. A well-reasoned
loss is a successful decision. A lucky, undisciplined win is a poor one.
This is why the company already values "Process over Prediction" (see
The Company Philosophy above) — Probability First Trading is that value
made concrete and operational.

**Statistics only mean something at scale.** One trade proves nothing.
Ten trades mean very little. A strategy's real edge only becomes visible
across a large sample — hundreds or thousands of trades. TradeTown
never judges a strategy, a department, or an employee from a single
result. It judges them from the distribution.

**Risk is accepted before entry, never negotiated after.** Before any
trade is proposed, its maximum loss must already be acceptable — in
capital terms and in company-discipline terms. Once a trade is live, the
risk has already been agreed to; the company does not renegotiate it out
of fear, excitement, or a change of mood. Discipline before entry is
what makes discipline after entry possible.

**"No trade" is a valid, often correct, decision.** When a setup does
not satisfy the company's validated framework, declining to trade is not
a missed opportunity — it is the philosophy working exactly as intended.

**Where this applies.** Every system that touches a trading decision
inherits this philosophy without needing its own copy of it, including
(non-exhaustively, since new departments inherit it automatically too):
Market Intelligence, Research, Quant, Risk, Simulation, Decision
Intelligence, the Strategy Validation Laboratory, the Academy, Mentor
Tracks, Company DNA, the Executive Intelligence Network, and every
department built after this one. Concretely, today:

- **Coach** reinforces it directly with employees — reminding them that
  one trade does not define them, that the process matters more than
  today's result, and that validated statistics are trusted over
  emotion.
- **Quant** is this philosophy's home department — evaluating sample
  size, expected value, win rate, variance, and drawdown, and training
  the rest of the company to trust evidence over instinct.
- **Decision Intelligence** grades whether a decision itself was
  disciplined and probability-driven — not merely whether the trade it
  produced happened to win.
- **Risk** enforces that no trade proceeds until its risk has genuinely
  been accepted in advance, matching Constitution Article XI below.
- **The Strategy Validation Laboratory** exists specifically to build
  the large-sample statistical evidence (Monte Carlo testing, regime
  testing, expectancy) this philosophy requires before any strategy may
  deploy real capital — see Feature 52/53's Company Certification.

**Company Constitution.** This philosophy is codified as five permanent
Articles (IX-XIII), seeded alongside the original eight from game start
— see `backend/app/constitution.py`:

> **Article IX.** We trade probabilities, not predictions.
>
> **Article X.** A single trade does not determine success.
>
> **Article XI.** Risk must be accepted before entry.
>
> **Article XII.** Process is more important than outcome.
>
> **Article XIII.** Statistics become meaningful only through consistent
> execution over a large sample of trades.

**The company motto.**

> *We do not predict the market. We prepare for probabilities. We
> protect capital. We execute our edge with discipline. Over time, the
> statistics work in our favor.*

### The Player's Role

The player is not simply controlling traders. The player is building an
institution. Every generation of employees should inherit the wisdom,
discoveries, systems, and culture created by previous generations. The
company's greatest competitive advantage is not a single strategy. It is
its ability to continuously learn, question, improve, innovate, and
teach.

### The Ultimate Vision

By the late game, TradeTown should feel less like a business and more
like a world-renowned research institution whose AI employees
continuously advance the science of trading, risk management, decision
making, and collaboration. The goal is not to build the richest company.
The goal is to build the smartest company — one whose knowledge
compounds forever and whose legacy grows stronger with every generation.

---

**Status:** Canonical. This document is the permanent source of truth for
what TradeTown is, why it exists, and what it will never become. Every
future version's scope is evaluated against this document before it is
evaluated against anything else — including a good idea. If a proposed
feature (however compelling) conflicts with a design pillar below, the
pillar wins, or the pillar changes first, deliberately, in a document
edit of its own. The Design Philosophy above is the one exception to
"the pillar changes first" — it does not change to accommodate a
feature; a feature changes (or is dropped) to fit it.

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
game. Per the Design Philosophy above, it's also a company that is
never finished getting better at that job — the building doesn't just
house the company, it's where the compounding actually happens.

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
3. **Read, then decide as CEO — never as a trader.** The Brain Room HUD,
   the whiteboards, TradeTown Daily (the newspaper), Company Memory, the
   Coach Dashboard, the Simulation Lab/Hall of Fame/Performance Center
   room readouts, and the Trading Floor's live ticker/Central Command
   display are all *read* surfaces the player never edits directly. The
   line this pillar actually protects is narrower than "the player never
   decides anything" (that boundary was true through v0.6 and did soften
   deliberately from v0.6.3 onward, per the Design Philosophy's "CEO
   Decision Making" principle) — it is *the player never does an
   employee's job*. Scout/Atlas/Echo/Nova/Sentinel/Guardian still do
   every real analysis, vote, and risk check autonomously; the player's
   own real decisions sit one level up, at the institution's controls:
   Executive Voting lets the CEO approve, reject, request more research,
   or delay the desk's own recommendation on a real `TradeProposal`
   (never place an order from scratch, never override a specific agent's
   vote); the Treasury, Time Controls, Company Priority, Calendar, and
   the CEO Research Dashboard let the CEO fund, pace, prioritize, and
   steer the company without ever touching an agent's research process
   or a position's entry/exit itself. The player still never sets
   `RiskLimits` numerically or hand-picks a trade's size or price — that
   stays Sentinel/Guardian's and the broker's job, not the CEO's.
4. **Return.** Because the simulation keeps advancing offline (persisted
   to SQLite every `PERSIST_INTERVAL_TICKS`), coming back later always
   shows a company that kept working without you — new research
   completed, new memory records, a newspaper with fresh headlines. The
   loop's payoff is the same one a good idle/management sim gives: "what
   did they get done while I was away."

This loop deliberately has no *real* economy, no real currency, and no
combat — v0.5's Paper Portfolio and Company Score introduce a simulated
score/economy (a fake $100,000 balance, a 0–100 company rating) purely so
the company's research quality has something legible to be measured
against, never as a player-facing win/loss cycle to optimize. It is
closer to *Powerwash Simulator*'s "watch the tile get clean" satisfaction
than to a trading game's win/loss cycle — the satisfaction is watching a
system you understand produce legible, incremental progress, including
now watching it grade its own performance.

## What TradeTown Is

- A **self-improving institution**, per the Design Philosophy above —
  the reason "get better at their jobs over time" (see Vision) is a
  mechanical fact (Academy Knowledge Points, Innovation Points, Company
  Health, Hall of Fame, the Founder Council, the Museum of Discoveries),
  not a flavor claim. Every system below exists to make that compounding
  real and inspectable, not to exist in isolation.
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

- **Not a trading platform.** No version of TradeTown through v0.7
  executes or queues order execution against **real capital**, and no
  version connects to a real brokerage. v0.5's Paper Trading engine
  (`portfolio.py`, `paper_trading.py`) does autonomously open and close
  *simulated* positions from high-confidence research completions — an
  autonomous action, but against a fake $100,000 balance that never
  touches a real account. "Future trade candidate" flags
  (`memory.py`'s `FUTURE_TRADE_CONFIDENCE_THRESHOLD`) predate and still
  coexist with this: they remain a logged note for a *human* to
  consider, the same threshold Paper Trading also reads to decide when
  to open a simulated position. This restriction is re-stated in every
  version's own brief on purpose; see `FUTURE_ARCHITECTURE.md` for how
  live brokerage support (v1.0) is scoped to still respect it.
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
agents research, discuss, and flag ideas; a Coach agent (shipped v0.5)
helps the *player* get better at evaluating those ideas; a Simulation Lab
(shipped v0.5) lets flagged candidates be replayed against placeholder
backtest data with zero real risk; Paper Trading (shipped v0.5, with
order-book execution and a full Decision Voting/Risk Engine/Market
Scanner pipeline added in v0.6) lets the player watch the company
practice execution without money; a Strategy Marketplace (v0.7) lets the
player curate which ideas the company prioritizes; Risk Calibration &
Analytics (v0.8) rounds out the company's own risk posture with
confidence-vs-outcome calibration and historical trend tracking; and
only at v1.0, with all of that scaffolding in place and explicitly
re-authorized, does a real (optional, opt-in, sandboxed) brokerage
connection become possible. Every step between here and there is
designed to be useful and complete *on its own* even if the project
stopped at that version — see `ROADMAP.md` for why each milestone is
scoped as a standalone deliverable, not a partial feature.

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
They implement the Design Philosophy above at the level of concrete
decisions; where a pillar and the philosophy ever appear to point
different directions, re-read the pillar as the philosophy applied to
this specific case, not as a competing authority.

### 1. Living AI Company

Agents are not decorative NPCs with a name and a walk cycle. They have
server-authoritative state (`AgentState`), a daily schedule
(`AGENT_SCHEDULES`), a rotating research assignment (`research.py`'s `tick_research()`),
and a persistent memory (`CompanyMemory`). The simulation runs whether or
not a client is connected (`sim.py`'s background loop is independent of
WebSocket connections). *Evidence this is real, not aspirational:* the
whole v0.3 build exists because this pillar demanded a research/watchlist/
discussion system, not just more decoration. This pillar is also where
the Compounding Principle becomes mechanical rather than aspirational:
an agent's schedule, memory, and knowledge state are real fields that
later systems (Academy, Innovation Points, the Founder Council) read
and grow — a "living" agent is, among other things, one whose present
state was actually shaped by its own past.

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
research, memory, meeting minutes, paper trade history, simulation
results, hall of fame entries, coach reports, and performance snapshots
are all capped) specifically so the client never has to decide what to
hide. *Evidence:* the per-category
news cap (`MAX_NEWS_PER_CATEGORY`) exists because a single flat cap let
frequent discovery news crowd out rare market headlines — a clutter bug,
fixed as a clutter bug.

### 5. Modular Systems, Not a Monolith

Every subsystem is a manager with one job, connected through the
`EventBus` (frontend) or explicit function composition in `nexus.tick()`
(backend) — never a god object. `MarketDataProvider` is an `ABC` swapped
via one registration point specifically so a real vendor can be added
without touching `watchlist.py`, `research.py`, or any UI
component. *Evidence:* Scribe (a fifth agent, v0.3) and Coach (a sixth,
v0.5) were both added with *zero* Phaser scene changes, because every
consumer already iterated `AGENT_IDS` instead of a hardcoded roster; v0.5
also kept its eight new "Manager" services (Coach/Simulation/Paper
Trading/Portfolio/Analytics/Hall of Fame/Performance/Knowledge) as plain
function modules rather than classes, matching the pattern `research.py`
and `watchlist.py` already established.

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
