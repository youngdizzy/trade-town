# TradeTown AI Agent Bible

**Status:** Canonical. This document is the permanent personnel file for
every AI employee TradeTown has, or will have. It is split into two
parts: **Current Roster** (five agents, live in the shipped v0.3 code —
every field below is traceable to a real class, schema, or data file) and
**Planned Roster** (ten agents named in the v0.4 brief, plus one
additional support role, none of which exist in code yet — every field
below is a design intention, explicitly marked as such, scoped to the
`ROADMAP.md` version that would introduce it).

Adding any planned agent to the real roster follows the exact checklist
in `docs/DeveloperGuide.md`'s "Adding a new agent" section: an `AgentId`
union member, an `AgentProfile` entry (frontend + backend, kept in sync),
a full-day `ScheduleBlock` list, dialogue lines, and — if the agent
researches — an entry in `RESEARCHER_IDS`. Every architecture claim below
about *how* a planned agent would work is a claim about that same
checklist, not a new mechanism.

---

# Part 1 — Current Roster (v0.1–v0.3, shipped)

## Scout

| | |
|---|---|
| **Role** | Market Scanner |
| **Department** | Research |
| **Responsibilities** | First-pass news and headline scanning across the watchlist; opens the research thread that Echo and Nova go on to deepen. |
| **Decision Authority** | None (v0.3). Scout's location, task, and research assignment are all server-driven by `schedule.py` and `research.py`'s round-robin `_next_symbol()` — Scout doesn't choose what to look at yet. This is deliberate: see `DESIGN_BIBLE.md`'s "Transparency Over Automation" pillar — nothing decides anything the player can't see the rule for. |
| **Strengths** | Breadth. Scout's research titles skew toward company-level headline scanning ("Scanning news flow on Apple Inc.") — the widest, shallowest net of the four researchers. |
| **Weaknesses** | No synthesis. Scout surfaces, it doesn't interpret — that's Nova's and Echo's job downstream. |
| **Personality** | *"Curious. Always exploring."* (`agents.py`) — the largest `wanderRadius` (60px) and lowest `idlePauseChance` (0.15) of any agent (`AgentProfiles.ts`), so Scout visibly moves more than anyone else in the building. |
| **Daily Schedule** | 06:00 Scout Office ("Scanning market news") → 09:00 Brain Room ("Back-testing a strategy") → 12:00 Lobby ("Resting") → 13:00 Scout Office ("Building a research memo") → 17:00 Brain Room ("Reviewing overnight positions") → 19:00 Lobby ("Resting") → 22:00 Scout Office ("Scanning market news") through 06:00 ("Reviewing overnight positions"). Exact blocks: `backend/app/schedule.py`, `AGENT_SCHEDULES["scout"]`. |
| **Office** | Scout Office (home location `scout-office`; also visits Brain Room and Lobby on schedule). |
| **Dialogue Style** | Short, task-anchored lines keyed by the exact schedule task string, e.g. `"Scanning market news"` → a Scout-flavored one-liner (`DialogueManager.ts`'s `AGENT_TASK_LINES.scout`). |
| **Mood System** | Standard shared model: `mood`/`energy` floats 0–100, mood drifts ±2 to +2.5 per tick, energy costs 1.5/tick while working and gains 3/tick in restful locations (`nexus.py`'s `_tick_agent`, `RESTFUL_LOCATIONS`). Scout has no bespoke mood logic. |
| **Memory Usage** | Standard `MemoryEntry` log capped at `MAX_MEMORY` most-recent entries per agent, one entry per task change ("Started: ..."). Scout also owns whichever `ResearchItem` is currently assigned to it in the rotating queue (one active item, capped history — see `research.py`). |
| **Future Upgrades** | Real news-API integration behind `MarketDataProvider` (post-v0.3, no version committed); a "breadth vs. depth" dial once Strategy Marketplace (v0.8) lets the player weight research priorities. |

## Atlas

| | |
|---|---|
| **Role** | Strategy Lead |
| **Department** | Strategy / Leadership |
| **Responsibilities** | Weighs strategic exposure across the watchlist, finalizes decisions at end of research cycles, and is the agent most often present when NEXUS calls a meeting (home location is the Meeting Room itself). |
| **Decision Authority** | Highest priority task assignment of any agent (`_task_priority()` in `nexus.py` gives Atlas `"high"` priority unconditionally, every other agent gets `"normal"`), reflecting seniority — but like every agent, Atlas's actual task/location is still schedule- and NEXUS-driven, not self-directed, in the current build. |
| **Strengths** | Synthesis under uncertainty — Atlas's research titles read as strategic exposure assessments ("Weighing strategic exposure to SPDR Gold Shares"), one level more abstract than Scout's headline scanning. |
| **Weaknesses** | Slowest mover in the building — smallest `wanderRadius` (18px) and highest `idlePauseChance` (0.7) — a deliberate trait, not a bug: leadership is mostly stillness and listening. |
| **Personality** | *"Calm. Strategic. Rarely speaks. Makes decisions."* (`agents.py`) |
| **Daily Schedule** | 06:00 Meeting Room ("Reviewing overnight strategy") → 09:00 Brain Room ("Assessing agent performance") → 12:00 Break Room ("Resting") → 13:00 Meeting Room ("Weighing strategic options") → 16:00 Brain Room ("Finalizing decisions") → 19:00 Meeting Room ("Planning tomorrow's priorities") → 22:00 Meeting Room ("Reviewing the day") through 06:00 ("Standing by"). `AGENT_SCHEDULES["atlas"]`. |
| **Office** | Meeting Room (the only agent whose home location is Meeting Room rather than an office). |
| **Dialogue Style** | Sparse by design — matches the "rarely speaks" personality trait; `AGENT_TASK_LINES.atlas` lines are shorter and more declarative than Scout's. |
| **Mood System** | Standard shared model (see Scout). No bespoke logic yet — a planned v0.5+ direction is letting Atlas's mood reflect the *outcome* of the company's flagged candidates once Coach exists to track outcomes. |
| **Memory Usage** | Standard `MemoryEntry` log + one active `ResearchItem`. Atlas is also the agent whose completed research most often crosses `FUTURE_TRADE_CONFIDENCE_THRESHOLD` in soak testing, purely because "strategic exposure" research titles read as higher-conviction language — not a hard rule in the code. |
| **Future Upgrades** | Formal "call a meeting" authority once agents gain any self-direction; a visible link between Atlas's `future_trade` flags and Coach's review queue (v0.5). |

## Echo

| | |
|---|---|
| **Role** | Technical Analyst |
| **Department** | Research — Technicals |
| **Responsibilities** | Chart-pattern and momentum-indicator research; the agent most often physically in the Brain Room, consistent with "loves charts, frequently studies monitors." |
| **Decision Authority** | None (v0.3), same as every current agent. |
| **Strengths** | Highest research throughput of the four researchers in soak testing — Echo's Brain Room home location means fewer schedule-driven location changes eating into research-focused ticks. |
| **Weaknesses** | Narrowest research lens — technicals only; Echo's research titles never touch fundamentals or macro framing (that's Nova's and, eventually, Macro's territory). |
| **Personality** | *"Loves charts. Frequently studies monitors."* (`agents.py`) — mid-range `wanderRadius` (30px), moderate `idlePauseChance` (0.5). |
| **Daily Schedule** | 06:00 Brain Room ("Charting technical patterns") → 10:00 Break Room ("Refilling coffee") → 11:00 Brain Room ("Studying monitor feeds") → 15:00 Lobby ("Stretching legs") → 16:00 Brain Room ("Tracking momentum indicators") → 20:00 Lobby ("Resting") → 22:00 Brain Room ("Scanning overnight charts") through 06:00 ("Monitoring after-hours signals"). `AGENT_SCHEDULES["echo"]`. |
| **Office** | Brain Room (home location `brain-room`). |
| **Dialogue Style** | Chart/indicator vocabulary in every line (`AGENT_TASK_LINES.echo`), the most jargon-forward of the five current agents. |
| **Mood System** | Standard shared model (see Scout). |
| **Memory Usage** | Standard `MemoryEntry` log + one active `ResearchItem`, titled from `_RESEARCH_TITLE_BY_AGENT["echo"]`'s technical-analysis template. |
| **Future Upgrades** | A real charting surface (candlesticks, indicators rendered, not just text) once a real `MarketDataProvider` exists to feed it; closer coordination with Pulse (planned) on momentum signals. |

## Nova

| | |
|---|---|
| **Role** | Research Analyst |
| **Department** | Research — Fundamentals |
| **Responsibilities** | Fundamentals and filings research — quarterly reports, revenue growth, company-level deep dives, complementing Scout's headline breadth and Echo's technical narrowness. |
| **Decision Authority** | None (v0.3). |
| **Strengths** | Longest attention span in the building — Nova's schedule blocks are the widest (07:00–11:00, 13:00–17:00) of any agent, reflecting sustained-focus fundamentals work. |
| **Weaknesses** | Slowest to react to fast-moving news, by design — fundamentals research is the antithesis of Scout's headline speed. |
| **Personality** | *"Reads books. Studies reports."* (`agents.py`) |
| **Daily Schedule** | 07:00 Brain Room ("Reading quarterly reports") → 11:00 Lobby ("Taking a walk") → 12:00 Break Room ("Lunch break") → 13:00 Brain Room ("Summarizing research findings") → 17:00 Scout Office ("Cross-checking Scout's notes") → 19:00 Lobby ("Resting") → 22:00 Brain Room ("Reading overnight filings") through 07:00 ("Reviewing archived reports"). `AGENT_SCHEDULES["nova"]`. Nova is the only agent whose overnight block runs 00:00–07:00 instead of 00:00–06:00, and the only agent who regularly visits Scout Office despite not being home there — a deliberate cross-team collaboration beat ("Cross-checking Scout's notes"). |
| **Office** | Brain Room (home location `brain-room`). |
| **Dialogue Style** | Reflective, citation-flavored lines (`AGENT_TASK_LINES.nova`). |
| **Mood System** | Standard shared model (see Scout). |
| **Memory Usage** | Standard `MemoryEntry` log + one active `ResearchItem`, titled from the fundamentals-analysis template. |
| **Future Upgrades** | A visible link between Nova's fundamentals research and Macro's (planned) macroeconomic context once both exist — e.g. surfacing when a company-level finding and a macro trend agree or conflict. |

## Scribe

| | |
|---|---|
| **Role** | Company Historian |
| **Department** | Operations / Records |
| **Responsibilities** | Records every research completion, every meeting's minutes, and every "future trade candidate" flag into `CompanyMemory` — the only agent whose job is *recording*, not researching. Introduced in v0.3 specifically to give the company a long-term memory a player could search. |
| **Decision Authority** | Applies the `future_trade` flag when a completed research item's confidence crosses `FUTURE_TRADE_CONFIDENCE_THRESHOLD` (85) — the one piece of current-roster logic that looks most like a "decision," though it's a fixed threshold check (`scribe.py`), not judgment. |
| **Strengths** | Completeness — Scribe is the only agent excluded from `RESEARCHER_IDS`, so it never competes for research-queue bandwidth; its whole job is downstream of everyone else's output. |
| **Weaknesses** | Produces nothing new — Scribe can only ever be as good as what the other four agents generate. |
| **Personality** | *"Meticulous. Quiet. Writes everything down."* (`agents.py`) — smallest `wanderRadius` (15px) and highest `idlePauseChance` (0.75) of any agent; visually the stillest employee in the building, matching "quiet." |
| **Daily Schedule** | 06:00 Brain Room ("Reviewing overnight logs") → 09:00 Meeting Room ("Filing yesterday's minutes") → 12:00 Break Room ("Resting") → 13:00 Brain Room ("Logging research updates") → 17:00 Scout Office ("Cross-referencing the archive") → 19:00 Lobby ("Resting") → 22:00 Brain Room ("Indexing the day's discoveries") through 06:00 ("Archiving overnight records"). `AGENT_SCHEDULES["scribe"]`. |
| **Office** | Brain Room (home location `brain-room`; the only agent with a dedicated mid-morning Meeting Room block *unrelated* to an actual meeting being called — "Filing yesterday's minutes" happens on schedule regardless). |
| **Dialogue Style** | Archival, past-tense-leaning lines (`AGENT_TASK_LINES.scribe`) — the only agent whose dialogue regularly references *other* agents' work by name. |
| **Mood System** | Standard shared model (see Scout). |
| **Memory Usage** | Scribe doesn't just *use* `CompanyMemory` — it's the sole writer. Every `record()` call into `backend/app/memory.py` traces back to a Scribe-attributed action (`record_research_completions`, `record_meeting`), even though the data itself came from other agents. |
| **Future Upgrades** | A dedicated Scribe "desk" search UI beyond the current `CompanyMemory` modal filter chips; a REST search endpoint (`memory.search()` already implements the filter contract, unrouted — see `docs/API.md`). |

---

# Part 2 — Planned Roster (not yet implemented)

Every agent below is a design intention scoped to a `ROADMAP.md`
version. None has an `AgentId`, `AgentProfile`, schedule, or dialogue
lines in the current codebase. Fields marked *(planned)* describe intent,
not shipped behavior.

## Coach
*(Planned — introduced v0.5)*

| | |
|---|---|
| **Role** | Player mentor |
| **Department** | Player Development (a department with a headcount of one, and the only agent whose primary "client" is the player, not the market) |
| **Responsibilities** *(planned)* | Reviews `future_trade`-flagged `CompanyMemory` records with the player, asking questions rather than issuing verdicts — see `DESIGN_BIBLE.md`'s Core Gameplay Loop, where Coach is explicitly the version that gives the player their first real interaction beyond walk-and-read. |
| **Decision Authority** *(planned)* | None over the market. Coach's only "decision" is which flagged record to surface next for review. |
| **Strengths** *(planned)* | The only agent designed around dialogue *with* the player rather than dialogue *about* the market. |
| **Weaknesses** *(planned)* | Entirely dependent on what Scribe has already recorded — Coach reviews history, it doesn't generate new research. |
| **Personality** *(planned)* | Socratic, patient, asks more than it tells — deliberately the opposite register from Atlas's terseness. |
| **Daily Schedule** *(planned)* | Likely home in a new or repurposed room reachable from the Lobby; exact blocks scoped at v0.5 kickoff. |
| **Office** *(planned)* | Undetermined — candidates are a new "Coach's Office" room or a repurposed corner of the Meeting Room. |
| **Dialogue Style** *(planned)* | Question-first: "Nova flagged this at 91% confidence — what made you agree, or not?" — a genuinely new dialogue shape, since every current agent's `AGENT_TASK_LINES` are statements, not questions. |
| **Mood System** *(planned)* | Likely exempt from the standard mood/energy model — Coach doesn't "work" on a schedule the way researchers do; reacts to player engagement instead. |
| **Memory Usage** *(planned)* | Reads `CompanyMemory`; does not write to it in v0.5's planned scope. |
| **Future Upgrades** *(planned)* | Eventually surfaces player-specific calibration ("you tend to agree with Atlas more than the outcomes justify") once enough paper-trade outcomes (v0.7+) exist to grade against. |

## Quant
*(Planned — introduced v0.6, Simulation Lab)*

| | |
|---|---|
| **Role** | Quantitative Modeler |
| **Department** | Research — Quantitative |
| **Responsibilities** *(planned)* | Builds and runs the backtest models the Simulation Lab (v0.6) executes against historical data served through a second `MarketDataProvider` implementation. |
| **Decision Authority** *(planned)* | Selects which historical windows and parameters a backtest runs with; never touches live/paper positions. |
| **Strengths** *(planned)* | Rigor — the only agent whose output is a reproducible number (a backtest result), not a narrative summary. |
| **Weaknesses** *(planned)* | Overfitting risk is a deliberate, visible weakness to dramatize — Quant's confidence in a backtested model should sometimes read as *too* high, a teaching moment for Coach to pick up on. |
| **Personality** *(planned)* | Precise, slightly pedantic, uncomfortable with qualitative claims. |
| **Daily Schedule** *(planned)* | Home in the new Simulation Lab room (v0.6); schedule scoped at kickoff. |
| **Office** *(planned)* | Simulation Lab. |
| **Dialogue Style** *(planned)* | Numeric, hedged ("87% in-sample, untested out-of-sample"). |
| **Mood System** *(planned)* | Standard model likely reused; energy cost tied to backtest compute "load" as flavor. |
| **Memory Usage** *(planned)* | Writes backtest results to `CompanyMemory` under a new category (extending `MemoryCategory` in `schemas.py`). |
| **Future Upgrades** *(planned)* | Direct hand-off of validated backtests to Ledger/Atlas for Paper Trading (v0.7) consideration. |

## Pulse
*(Planned — near-term data agent, no version committed)*

| | |
|---|---|
| **Role** | Market Sentiment Tracker |
| **Department** | Research — Sentiment |
| **Responsibilities** *(planned)* | Tracks short-horizon sentiment/momentum shifts — the "what's moving right now" complement to Echo's slower technical-pattern work and Scout's headline scanning. |
| **Decision Authority** *(planned)* | None. |
| **Strengths** *(planned)* | Fastest reaction time of any planned research agent — designed to have the shortest schedule blocks and highest tick-to-tick task turnover. |
| **Weaknesses** *(planned)* | Noisy — Pulse's findings are explicitly designed to sometimes be false alarms, giving Coach and the player something real to calibrate against. |
| **Personality** *(planned)* | Energetic, slightly anxious, talks fast. |
| **Daily Schedule** *(planned)* | Likely Brain Room-centric like Echo/Nova. |
| **Office** *(planned)* | Brain Room. |
| **Dialogue Style** *(planned)* | Short, exclamatory, time-stamped. |
| **Mood System** *(planned)* | Likely the most volatile mood swings of any agent, matching "energetic/anxious." |
| **Memory Usage** *(planned)* | High write volume to `CompanyMemory`, capped tightly (see `KNOWN_LIMITATIONS.md` on the flat 200-record memory cap needing revisiting once agent count grows). |
| **Future Upgrades** *(planned)* | Real-time data feed integration is the single biggest reason Pulse needs an actual `MarketDataProvider` vendor, not mock data. |

## Macro
*(Planned — near-term data agent, complements Nova, no version committed)*

| | |
|---|---|
| **Role** | Macroeconomic Analyst |
| **Department** | Research — Macro |
| **Responsibilities** *(planned)* | Rates, inflation, currency, and broad-index research — the `economy` and `index` `ResearchCategory` values already exist in `schemas.py` and are currently researched by whichever of the four current researchers happens to be assigned DXY/SPY/QQQ by the rotation; Macro would be the agent that actually specializes in them. |
| **Decision Authority** *(planned)* | None. |
| **Strengths** *(planned)* | The only planned agent whose research explicitly spans multiple watchlist symbols at once (a macro view is never about one ticker). |
| **Weaknesses** *(planned)* | Slow-moving, abstract — Macro's findings are the hardest for Coach to turn into a concrete lesson. |
| **Personality** *(planned)* | Measured, historically minded, references past cycles. |
| **Daily Schedule** *(planned)* | Likely Meeting Room-adjacent like Atlas, reflecting a strategic-context role. |
| **Office** *(planned)* | Meeting Room or Brain Room, undetermined. |
| **Dialogue Style** *(planned)* | Longer, context-heavy lines — the opposite of Pulse's terse urgency. |
| **Mood System** *(planned)* | Standard model, low volatility. |
| **Memory Usage** *(planned)* | Standard `MemoryEntry` + `ResearchItem`, `economy`/`index` category by default. |
| **Future Upgrades** *(planned)* | Cross-referencing Nova's fundamentals with macro headwinds/tailwinds — a genuinely new discussion-generation template in `discussion.py`. |

## Oracle
*(Planned — introduced alongside or after v0.6, Simulation Lab)*

| | |
|---|---|
| **Role** | Forecaster / Scenario Modeler |
| **Department** | Research — Quantitative |
| **Responsibilities** *(planned)* | Longer-horizon scenario modeling ("if rates rise 50bp, what happens to XLF") built on top of Quant's backtesting infrastructure and the Simulation Lab. |
| **Decision Authority** *(planned)* | None. |
| **Strengths** *(planned)* | The only agent designed to reason about multiple future branches at once rather than a single research thread. |
| **Weaknesses** *(planned)* | Deliberately the least "confident" agent by design — Oracle's confidence scores should visibly compress toward the middle of the range, modeling genuine forecasting humility, in contrast to Atlas's higher-conviction language. |
| **Personality** *(planned)* | Hedged, probabilistic speech ("in most scenarios..."). |
| **Daily Schedule** *(planned)* | Simulation Lab-centric, alongside Quant. |
| **Office** *(planned)* | Simulation Lab. |
| **Dialogue Style** *(planned)* | Scenario-branch phrasing, never a flat statement. |
| **Mood System** *(planned)* | Standard model. |
| **Memory Usage** *(planned)* | Writes scenario summaries to `CompanyMemory`, likely under the same new category as Quant's backtests. |
| **Future Upgrades** *(planned)* | Feeding Risk Engine (v0.9) directly — Oracle's scenario spread is the natural input to a risk-of-loss estimate. |

## Guardian
*(Planned — introduced alongside Risk Engine, v0.9, or earlier as an infra role)*

| | |
|---|---|
| **Role** | Security & Data Integrity |
| **Department** | Operations / Infrastructure |
| **Responsibilities** *(planned)* | The in-universe face of TradeTown's own operational safeguards — data integrity checks on `CompanyMemory`, and (once real trading scaffolding exists in v0.7+) the agent whose "job" is enforcing the "not a trading platform" boundary from `DESIGN_BIBLE.md` inside the fiction itself, not just in code comments. |
| **Decision Authority** *(planned)* | The most authority of any planned agent by design: Guardian is the in-fiction reason paper trades (v0.7) can never silently become real ones — a narrative embodiment of a hard technical boundary. |
| **Strengths** *(planned)* | Uncompromising — the one agent whose "weakness" (below) is a feature, not a bug. |
| **Weaknesses** *(planned)* | Deliberately inflexible; Guardian should never be the agent players root for narratively "unlocking" past — that would undermine the boundary it represents. |
| **Personality** *(planned)* | Formal, procedural, quotes policy. |
| **Daily Schedule** *(planned)* | Likely a fixed post rather than a wandering schedule — an "always at the door" presence. |
| **Office** *(planned)* | Undetermined; thematically fits near the CEO Office or a future "Compliance" room. |
| **Dialogue Style** *(planned)* | Short, procedural, occasionally quotes the exact boundary language from `DESIGN_BIBLE.md`. |
| **Mood System** *(planned)* | Likely exempt or minimal — a steady, low-variance presence by design. |
| **Memory Usage** *(planned)* | Read/audit access to all of `CompanyMemory`, write access limited to a new audit-log category. |
| **Future Upgrades** *(planned)* | The literal implementation of whatever authorization gate v1.0's brokerage re-authorization requires (see `ROADMAP.md`). |

## Hunter
*(Planned — near-term research agent, no version committed)*

| | |
|---|---|
| **Role** | Opportunity Scout |
| **Department** | Research — Discovery |
| **Responsibilities** *(planned)* | Deeper, more aggressive discovery than Scout's headline breadth — actively hunting for under-covered symbols to *add* to the watchlist, complementing `watchlist.py`'s currently-fixed `SEED_SYMBOLS` list. |
| **Decision Authority** *(planned)* | Could plausibly be the first agent with real decision authority: proposing (not adding outright) new watchlist symbols for the player or Atlas to approve. |
| **Strengths** *(planned)* | The only agent whose job is expanding scope rather than deepening it. |
| **Weaknesses** *(planned)* | High false-positive rate by design — most "opportunities" Hunter surfaces should not pan out, another deliberate calibration lesson for Coach. |
| **Personality** *(planned)* | Restless, competitive, talks in terms of being "first." |
| **Daily Schedule** *(planned)* | Highest wander radius of any planned agent, narratively and mechanically, continuing Scout's movement pattern one step further. |
| **Office** *(planned)* | Scout Office-adjacent. |
| **Dialogue Style** *(planned)* | Punchy, pitch-like. |
| **Mood System** *(planned)* | High energy cost, matching constant movement. |
| **Memory Usage** *(planned)* | Proposed-symbol log, a new `MemoryCategory`. |
| **Future Upgrades** *(planned)* | Direct integration with Strategy Marketplace (v0.8) — Hunter's proposals as one input to shareable strategy configs. |

## Watchtower
*(Planned — introduced alongside Risk Engine, v0.9)*

| | |
|---|---|
| **Role** | Alerts & Anomaly Monitoring |
| **Department** | Operations / Risk |
| **Responsibilities** *(planned)* | Watches the whole company's state (not one symbol) for anomalies — a stalled research item, an agent stuck in an override loop, a watchlist entry that hasn't updated — the in-fiction face of what `KNOWN_LIMITATIONS.md` today calls "nothing currently alerts on simulation health." |
| **Decision Authority** *(planned)* | None over the market; can plausibly trigger an in-world "alert" news item or HUD flag. |
| **Strengths** *(planned)* | System-wide visibility no other agent has — Watchtower is the only planned agent whose scope is the *company*, not the *market*. |
| **Weaknesses** *(planned)* | Reactive by nature — can only flag problems after they occur. |
| **Personality** *(planned)* | Vigilant, terse, no small talk. |
| **Daily Schedule** *(planned)* | Likely a fixed Brain Room post, mirroring its "always watching" role. |
| **Office** *(planned)* | Brain Room. |
| **Dialogue Style** *(planned)* | Alert-formatted: what, where, since when. |
| **Mood System** *(planned)* | Possibly the first agent with a mood tied to *system* health rather than personal energy — a genuinely new mechanic if built. |
| **Memory Usage** *(planned)* | Writes to a new "event"/anomaly category (the existing `event` `MemoryCategory` value in `schemas.py` already anticipates this). |
| **Future Upgrades** *(planned)* | Natural pairing with Guardian for v0.9's Risk Engine HUD panel. |

## Lab
*(Planned — introduced v0.6, Simulation Lab — the room's "operator")*

| | |
|---|---|
| **Role** | Simulation Lab Operator |
| **Department** | Research — Quantitative |
| **Responsibilities** *(planned)* | Runs the Simulation Lab room day-to-day — queues backtests Quant designs and Oracle scenario-models, keeps the Lab's results organized. The "front desk" of the Lab, as distinct from Quant (the modeler) and Oracle (the forecaster). |
| **Decision Authority** *(planned)* | Scheduling/queuing only — which backtest runs next. |
| **Strengths** *(planned)* | Operational clarity — Lab exists so Quant and Oracle don't need their own scheduling logic, the same separation-of-concerns pattern NEXUS already uses for the current roster. |
| **Weaknesses** *(planned)* | Purely operational — no independent research output of its own. |
| **Personality** *(planned)* | Organized, checklist-driven. |
| **Daily Schedule** *(planned)* | Simulation Lab-based. |
| **Office** *(planned)* | Simulation Lab. |
| **Dialogue Style** *(planned)* | Status-update phrasing ("queued," "running," "complete"). |
| **Mood System** *(planned)* | Standard model. |
| **Memory Usage** *(planned)* | Indexes Quant's and Oracle's results, Scribe-style, but scoped to the Lab only. |
| **Future Upgrades** *(planned)* | Could absorb Quant and Oracle's scheduling entirely if the Lab's headcount needs trimming for pacing reasons — flagged here as an explicit design option, not a commitment. |

## Ledger
*(Planned additional support role — introduced v0.7, Paper Trading)*

| | |
|---|---|
| **Role** | Paper Trading Bookkeeper |
| **Department** | Operations / Finance |
| **Responsibilities** *(planned)* | The one role none of the ten named agents obviously own: maintaining the paper-trading ledger itself once v0.7 ships — position entries, simulated P&L, and the audit trail Guardian would check. Added here because a "professional AI investment company" (this document's explicit brief) does not function without someone who owns the books, and Scribe's existing role (general company historian) is deliberately kept distinct from Ledger's (financial record-keeping specifically) so v0.7 doesn't overload Scribe's scope. |
| **Decision Authority** *(planned)* | Records only; never initiates a paper trade — that's downstream of Atlas + Coach + Guardian's sign-off, whatever that pipeline ends up being at v0.7 kickoff. |
| **Strengths** *(planned)* | Precision, auditability. |
| **Weaknesses** *(planned)* | Entirely reactive — Ledger only exists once there's something to record. |
| **Personality** *(planned)* | Exacting, numbers-first, the financial mirror of Scribe's archival personality. |
| **Daily Schedule** *(planned)* | Likely Meeting Room or a new "Finance" nook, scoped at v0.7 kickoff. |
| **Office** *(planned)* | Undetermined. |
| **Dialogue Style** *(planned)* | Ledger-line phrasing: date, symbol, size, result. |
| **Mood System** *(planned)* | Standard model. |
| **Memory Usage** *(planned)* | Owns the new paper-trade ledger data structure entirely (extends `GameSaveState` with a new field, following the exact pattern `research`/`watchlist`/`memory` were added in v0.3). |
| **Future Upgrades** *(planned)* | The natural owner of any future real-brokerage reconciliation view, if v1.0 is ever authorized. |
