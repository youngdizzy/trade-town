# Version History

A version-by-version summary of TradeTown's scope. For the itemized
per-change list (including bug fixes), see [`CHANGELOG.md`](../CHANGELOG.md)
at the repo root; this file is the higher-level "what was each version
about and why" narrative, plus what's intentionally deferred.

## v0.1 — Foundation

One employee (Scout), a small HQ (Lobby + Scout Office + CEO Office +
Brain Room), a live backend simulation driving Scout's daily
schedule/mood/energy/memory, save/load, and Docker Compose deployment with
an nginx reverse proxy. Established the core client/server architecture
(server-authoritative agent state over WebSocket, client-authoritative
player/settings/dialogue) that every later version builds on without
rewriting.

## v0.2 — Multi-agent office

Three more agents (Atlas, Echo, Nova), each with a distinct personality
and daily routine; two new rooms (Meeting Room, Break Room) plus an
upgraded Brain Room ("Mission Control"); a reusable server-authoritative
`Task` system; the NEXUS orchestrator (task assignment, meetings, breaks,
whiteboards, discovery news); a newspaper stand; and an extended save
schema. Generalized the v0.1 single-agent architecture (`ScoutState` →
`Record<AgentId, AgentState>`, `ScoutNPC` → `AgentNPC`) to support an
arbitrary agent roster without a rewrite — a design choice that paid off
directly in v0.3, where adding a fifth agent (Scribe) required zero
Phaser scene changes.

## v0.3 — Intelligence & research

A fifth agent (Scribe, the company historian); a `MarketDataProvider`
interface with a mock adapter (no real market API, no trades — see
`docs/Architecture.md`); a rotating research queue across an 8-symbol
watchlist with per-agent confidence; meetings that now produce real
discussion transcripts and minutes; a searchable `CompanyMemory` log with
a dedicated viewer; and an upgraded Brain Room HUD / newspaper /
whiteboards surfacing all of it. Extended (not replaced) v0.2's `Task`
system with categories, and v0.2's meeting/break `AgentOverride`
mechanism gained a `discussion` field rather than a parallel state
machine.

**Explicitly not in v0.3** (per the brief's STOP CONDITION): paper
trading, brokerage connections, live trading of any kind, or a real
market data API call. "Future trade" flags are a logged note for a human
to consider, never a queued or simulated order.

## v0.4 — Design & Architecture Foundation

Documentation only — **zero code changes**. Twelve planning documents
(`DESIGN_BIBLE.md`, `ROADMAP.md`, `AI_AGENT_BIBLE.md`, `UI_UX_BIBLE.md`,
`COMPANY_LORE.md`, `NEXUS_ARCHITECTURE.md`, `PROJECT_STRUCTURE.md`,
`CODING_STANDARDS.md`, `TASK_BACKLOG.md`, `KNOWN_LIMITATIONS.md`,
`FUTURE_ARCHITECTURE.md`, and a final `ARCHITECTURE_REVIEW.md` scoring the
codebase across nine dimensions) capturing the v0.3 codebase's design
intent, coding conventions, and a scored backlog of 268 candidate future
tasks. Explicitly forbade starting v0.5 or touching any trading feature —
v0.3 continued to run exactly as it did before this version.

## v0.5 — Intelligence Evolution

A sixth agent (Coach, Performance & Improvement) who reviews completed
research and closed paper trades and files weekly/monthly reports
(`coach.py`, `CoachDashboard.tsx`); a Simulation Lab (`simulation.py`) —
a new room where strategies queue, run, and complete with placeholder
backtest metrics (see `simulation.py`'s module docstring — no real
historical data source exists yet); a Paper Trading engine
(`portfolio.py`, `paper_trading.py`) with a fully simulated $100,000
starting account, opening/closing positions from high-confidence research
completions; a Hall of Fame room celebrating the company's best research,
strategies, simulations, streaks, and monthly performance
(`hall_of_fame.py`); a Learning System (`knowledge.py`) that derives a
`lesson` or `mistake` Company Memory record from every closed paper
trade; a seven-metric Company Score (`company_score.py`) — Research
Quality, Decision Quality, Risk Management, Paper Trading Performance,
Team Coordination, Knowledge Growth, Simulation Success — shown in an
expanded Brain Room HUD; and daily/weekly/monthly/all-time performance
snapshots (`analytics.py`). Company Memory gained six new searchable
categories (`lesson`, `mistake`, `strategy`, `coach_review`, `simulation`,
`paper_trade`). The Lobby widened from five doors to eight to fit the
three new rooms (Simulation Lab, Hall of Fame, Performance Center).

**Explicitly not in v0.5** (per the brief's STOP CONDITION): live
brokerage support, a connection to Charles Schwab or any other broker, or
execution of a single real trade. Every `PaperOrder`, `PaperPosition`,
and `PaperTrade` is simulated bookkeeping only — see `portfolio.py`'s
module docstring for the enforcement boundary.

## v0.6 — Paper Trading Operations

Three more agents (Sentinel — Risk Management, Pulse — Market Scanner,
Guardian — Portfolio Protection), TradeTown's ninth Lobby door: the
Trading Floor, home to all three. The v0.5 paper-trading engine's
opening logic moved behind a full Decision Voting pipeline
(`voting.py` + `decision.py`): every high-confidence completed research
item is now voted on by the four researcher agents plus Sentinel and
Guardian, with a permanent, explainable `TradeDecision` record (research/
technical/fundamental/risk summaries, supporting/opposing agents, final
reasoning) stored for every candidate — approved or not. Approved trades
route through a new order-book `PaperBroker` (`broker.py`, market/limit/
stop/take-profit/stop-loss orders, one tick of fill latency) instead of
opening a position directly. A configurable `RiskEngine`
(`risk_engine.py`) backs Sentinel's hard trade-approval gate and
Guardian's softer exposure/concentration watch; a `ScannerManager`
(`scanner.py`) backs Pulse's continuous gap/breakout/volume-spike/
volatility scan across the watchlist. A `TradeJournal` (`journal.py`)
stamps every closed trade with a coach review and lessons learned,
closing a v0.5 gap where those two schema fields existed but nothing
populated them. The v0.5 closing logic (mark-to-market, hold-duration-
based random-roll close) is unchanged — only how a position gets opened
moved. Brain Room HUD and the newspaper both gained sections surfacing
all of this (Open Positions, Pending Orders, Risk Management, Votes,
Scanner Alerts, Company Rating).

**Explicitly not in v0.6** (per the brief's STOP CONDITION): live
brokerage support, a connection to Charles Schwab or any other broker, or
execution of a single real trade — the same boundary every version
before it has held. Every `PaperOrder`, `PaperPosition`, and `PaperTrade`
is simulated bookkeeping only.

## v0.7 — Intelligence & Decision Systems

Six systems layered onto v0.6.3's Executive Voting rather than replacing
it, aimed at making both the AI desk and the player better decision-
makers over time rather than maximizing a single trade's P&L. A
**Decision Confidence Engine** (`confidence.py`) formalizes the old
client-side "Trade Quality Score" into a real, persisted six-factor
score carried onto every `TradeDecision`. A **What-If Simulation Lab**
(`whatif.py`) stress-tests a pending proposal against 12 named market
scenarios, each a bootstrap resample of the symbol's own real recent
returns — computed fresh per request, never persisted. An **AI Debate
Room** (`debate.py`) turns the six analyst votes into a full investment-
committee review (opening statement + real cross-examination per
analyst) before the CEO decides. The **Decision Journal & Mistake
Tracker** extends Coach's existing weekly/monthly reporting with two new
recurring-mistake patterns and a strengths readout, rather than building
a parallel journal. A **Premium Trade Outcome Banner** replaces the old
blocking trade-result popup with a non-blocking, queued, top-center
banner. Last, the **Trade Gatekeeper** (`gatekeeper.py`) sits between the
CEO's real buy/sell call and the order actually being placed — seven
real checks (confidence, risk-vote alignment, desk agreement, the AI
Debate's own recommendation, portfolio exposure, correlated positions,
active critical risk warnings) can now veto even the player's own
choice, ending v0.6.3's "the CEO's choice is unconditionally final"
model. A rejected trade never executes, so there's no real P&L to grade
it against — its hypothetical outcome instead resolves later purely from
the symbol's own real subsequent price move, the same "wait for real
time, check real data" convention every other outcome-grading path in
this codebase already uses.

Several factors named across these six features' briefs (multi-timeframe
confirmation, support/resistance quality, liquidity, reward-to-risk
ratio, stop-loss placement, strategy match, historical similar-setup
performance) have no real data source in this codebase and are
deliberately not computed anywhere — see each module's own docstring for
the same honesty boundary applied consistently across all six.

### v0.7 continued — AI Company Management & Simulation Systems

Three more systems, shifting the frame from grading individual trades to
managing the company itself. **Company Operating Modes** add a
`Learning | Assisted | Executive` toggle (`settings.operatingMode`) that
changes how much NEXUS auto-resolves on the player's behalf — Learning
Mode leaves every trade proposal to a real CEO click (unchanged v0.6.3
behavior); Assisted Mode auto-resolves only proposals a new
`is_significant_proposal()` check calls routine (adequate confidence, no
critical risk warning, reasonable position size), still surfacing
anything bigger; Executive Mode auto-resolves everything. Every auto-
resolved decision is honestly tagged `resolvedBy: "auto"` on its
`CeoDecisionRecord`, never presented as the player's own call. **Market
Environment Simulation** (`market_environment.py`) classifies the whole
watchlist into bull/bear/sideways/high-volatility/low-volatility every
tick from the real aggregated daily price changes already on hand, keeps
a real timeline of actual regime changes, and now drives which pool of
market headlines the News desk draws from — a genuine, if modest,
"departments react to conditions" hookup. **Company Health & Stability**
(`company_health.py`) adds a second scorecard alongside the existing
`CompanyScore`, deliberately asking a different question ("is the
company stable and well-run?" vs. "is it winning?") from ten real
sub-metrics — risk warnings, agent activity, research completion,
portfolio P&L, agent energy, hall-of-fame count, signal-calibration
level, watchlist expansion, and education progress — with plain-language
recommendations naming whichever two metrics are weakest. All three
systems, plus a new COMPANY tab surfacing them, are covered by 33 new
backend tests. The brief's "Executive Reports" is deliberately not a new
report engine — it reuses Feature 18's existing Coach reporting — and
"NPC Interactions" (persistent relationships, remembered conversations)
has no new memory system behind it in this pass; both are documented
scope cuts rather than fabricated mechanics.

### v0.7 continued — Executive AI & Academy System

A tenth agent and a company-wide learning system. **Meridian, the Chief
Investment Officer** (`app/executive_review.py`), joins the roster with a
real profile, schedule, and a palette-swapped sprite generated by
comparing the base sprite sheet against all nine existing agents to find
exactly which pixels each one recolors — but never votes on a trade or
generates a research signal, per the brief. Its one real responsibility
is a new **Monthly Executive Review**, generated on the same monthly
cadence as Coach's own report but asking a different question: real
department activity, research/knowledge output, real analyst
disagreement (Debate Room challenge counts), and real "worth a second
look" flags, plus one true period-over-period figure — company score
change against the previous review's own stored score. A new
**Executive Boardroom** room (34×22 tiles, the largest room in the game)
hosts six live readouts — world market display, department performance,
department status, the briefing screen, a report-archive timeline, and
current objectives — deliberately with no duplicate Command Center tab,
since the brief specifically wants the room itself walkable "at any
time." The **AI Academy & Knowledge Network** gives every agent a real
Knowledge Branch and a real, cumulative Knowledge Points total that only
grows from actually-completed work (finished research, a finished
Academy project, real meeting attendance), crossing real tiers the same
way Signal Calibration's own level already does. A new non-market
research queue (`academy_research.py`) cycles six knowledge topics
through the team, permanently archiving every completion as the **Company
Knowledge Library**; a company-wide Academy Level (1-5, named tiers)
blends real points and real completions rather than five new physical
rooms. Surfaced on a new KNOWLEDGE tab — not "ACADEMY," since that name
was already taken by the pre-existing Trading Academy lesson curriculum.
**Mentorship** is this pass's most deliberate honesty call: with zero
seniority or relationship data anywhere in the codebase, "seniority" is
grounded in the one real number that legitimately reflects it — an
agent's own earned Knowledge Points — rather than a fabricated status
label; when two agents' real point gap crosses a threshold, a real
session transfers a small real bonus, logged with both agents' actual
numbers. A full relationship graph and in-world mentoring animations are
explicit, documented scope cuts, as is per-tier "expanded dialogue" (33
bespoke lines was out of scope) and new academy-flavored meeting
dialogue (a completed project instead publishes a real news headline).
33 new backend tests; the full Playwright suite (16 tests across three
spec files) passes clean.

### v0.7 continued — Company Knowledge Graph (Feature 25.5)

The **Company Knowledge Graph** connects everything Feature 24/25
produced into one queryable network instead of leaving it as isolated
lists. `app/knowledge_graph.py` builds a real node-edge graph — computed
fresh on every `GET /api/knowledge-graph` call, never persisted, the same
convention the What-If Simulation Lab established — from six already-real
sources: completed research, completed Academy projects, each agent's own
Knowledge Branch, Executive Reviews, Coach Reports, and Hall of Fame
entries. Every edge traces to a real, checkable shared attribute (a
shared research category chained by real timestamps into a "builds on"
relationship, an agent's real appearance in a report, and so on) — never
a fabricated connection. The **Interactive Knowledge Map**
(`KnowledgeGraphView.tsx`, opened from the KNOWLEDGE tab) is a hand-rolled
canvas force-directed graph with real pan/zoom, per-type color coding
(agent nodes reuse each agent's own real sprite tint), a label search, and
a click-to-inspect side panel showing a node's real connections. The
Executive Review gained real **Knowledge Connections** — "this period's
research builds on earlier work" callbacks naming two real titles,
deliberately never claiming a specific elapsed time since these records
only carry real wall-clock timestamps. `DialogueManager` gained one
honest institutional-memory touch: roughly one conversation in three, an
agent recalls their own most recent real completed Academy project by
its real title. Explicit scope cut: the brief's request to
auto-generate Academy lessons/seminars/quizzes/museum exhibits/dialogue
from completed research is not built — this codebase has no
content-generation capability, and the existing Education curriculum was
checked directly and confirmed to have no real thematic overlap with the
Academy's own topics. 17 new backend tests; verified end-to-end against a
live dev backend with real data (zoom, pan, search, and node-selection all
producing correct real content, zero console errors).

### v0.7 continued — The Discipline Chamber & The Library of Mistakes (Features 26-27)

The company now rewards good decisions, not lucky outcomes. The
**Discipline Chamber** files a real `DisciplineReview` for every trade
that closes, scoring the decision PROCESS from seven real signals —
Research Depth, Viewpoint Diversity, Uncertainty Acknowledged,
Cross-Examination Occurred, Assumptions Challenged, Position Sizing
Discipline, Patience — reusing the Decision Confidence Engine's own
factors and the AI Debate's real turns. The rule "a lucky outcome should
never produce a high score" is enforced structurally: the scoring
function's own signature can never see the trade's pnl, only a real hold
duration and the original decision's real process trail — provably the
same score regardless of win or loss. The trade's real outcome is
attached to the finished review afterward purely so the player can see
whether a good process and a good outcome lined up; a sound process that
still lost reads as "bad luck, not a bad decision," while a weak process
that won reads as "a warning, not a validation." A real
`PostDecisionReview` answers the brief's seven questions from the
review's own real factors, naming a specific real dissenting analyst
(Echo or Scout) whose overridden vote proved right on a real loss.

The **Library of Mistakes** files a permanent `CaseStudy` whenever a
closed, losing trade's own Discipline Review shows a specific real
process gap — never merely "the trade lost" alone. Six categories, each
a real, checkable signal: The Cost of Overconfidence, Incomplete
Research, Failure to Challenge Assumptions, Acting Too Quickly, Poor
Communication, and Confirmation Bias. Every field (Timeline, Background,
Decision Process, Department Opinions, Missed Information, Lessons
Learned, Recommended Improvements, Related Company Principles) is built
from real structured data filled into a fixed template, never a
fabricated narrative. Both systems carry a real in-game day (`simDay`)
so NPCs can honestly reference "on Day X" — `DialogueManager` gained a
second real recall source (a case study from a decision the agent was a
real party to) alongside the existing Academy-project recall. A new
DISCIPLINE Command Center tab surfaces an aggregate score, the two
counts that make "process, not outcome" concrete, and expandable
reviews/case studies. Explicit scope cuts: "documentation created" and
"departments communicated effectively" (beyond real cross-examination)
have no real discriminating signal in this codebase and aren't scored;
Discipline Reviews only cover closed trades, since research projects and
company milestones have no comparable rich per-item process trail to
honestly score. 28 new backend tests; a 3000-tick standalone smoke test
in Executive Operating Mode confirmed the full pipeline end to end (60
reviews, 60 case studies, zero exceptions); verified in the running app
against seeded real data with zero console errors.

### v0.7 continued — The Reasoning Lab (Feature 29)

The company now practices how it thinks, not just what it decides. The
**Reasoning Lab** files a real `ReasoningChallenge` periodically from the
company's most recent real AI Debate plus its linked `TradeDecision` —
like the Discipline Chamber, this is decoupled from trade outcomes
structurally, not just by convention (no pnl is ever read to produce a
challenge). Seven honest categories out of the brief's nine, each a real,
checkable signal on the linked Debate/decision: Finding Missing
Information, Identifying Weak Evidence, Recognizing Contradictory Data,
Separating Facts from Assumptions, Evaluating Multiple Hypotheses,
Comparing Competing Explanations, and Improving Communication. Detecting
Logical Fallacies and Building Better Questions have no real checkable
signal anywhere in this codebase and aren't built. A real Reasoning
Level — mirroring `AcademyState`'s own progression convention — gates
which categories can actually appear, so an advanced category is
genuinely absent until the company has practiced the basics, never
faked early. Each challenge's Collaborative Thinking record reframes the
underlying AI Debate's own real opening/challenge/support turns as the
brief's "departments collaborate" record, and its Explain Your Thinking
solution answers the brief's six required questions from the linked
decision's own real Confidence Engine factors and vote reasoning — never
invented commentary. A new REASONING Command Center tab shows the
current level/progress and a filterable, expandable Reasoning History;
`DialogueManager` gained a third real recall source referencing a filed
challenge an agent actually contributed a real Debate turn to. Explicit
scope cuts: new seminar content and per-level collaboration animations
have no real data source and aren't built. 21 new backend tests; a
4000-tick standalone smoke test in Executive Operating Mode confirmed
the full pipeline end to end (7 challenges across three genuinely
different real categories, Reasoning Level correctly advancing); verified
in the running app with zero console errors.

### v0.7 continued — The Reflection Chamber & Knowledge Levels (Features 30-31)

The company now pauses to learn, not just to act. The **Reflection
Chamber** files a real `ReflectionSession` every in-game week and month,
answering the brief's nine reflection questions purely from data already
computed elsewhere (Discipline Reviews, Case Studies, Reasoning
Challenges, research) — several questions deliberately reuse the same
real number from opposite ends (the strongest Discipline factor answers
both "what are we doing well" and "what should we continue"). A new
**Company Wisdom** score — never profit-based — is a plain, unweighted
mean of eight real factors (learning from experience, sharing knowledge,
following the Gatekeeper's own principles, improving communication,
documenting lessons, avoiding repeated mistakes, completing research,
supporting collaboration), recomputed only when a session is generated
so it reads as genuinely slow-moving, and deliberately hard to max since
several factors pull against each other in practice. Cross-department
sharing is real recent output from real existing agents, never invented
department dialogue. A new REFLECTION Command Center tab shows the
current score/tier/factor breakdown and the full Reflection Journal
history; `DialogueManager`'s recall chance now scales up with the
company's real Wisdom tier — the honest version of "historical knowledge
referenced more often." **Knowledge Levels** extends the existing AI
Academy (Feature 25) rather than duplicating it: the same real per-agent
points now cross six thresholds into a real seven-level Novice-through-
Mentor scale, and the existing mentorship mechanism is phrased as real
teaching once a mentor actually reaches the top level. Explicit scope
cuts: no new physical Reflection Chamber or Learning Center room (no
real gameplay-data hook for a holographic table or a ten-room building
in this 2D codebase); Player Knowledge Import (PDFs/videos/books) isn't
built at all — no content-ingestion capability exists; the brief's
8-stage learning pipeline and per-lesson Knowledge Summaries aren't
separately modeled, since the existing Academy Project pipeline and
Education quizzes already cover real study/practice/understanding-check
activity honestly. 20 new backend tests; an 11,500-tick (~41 in-game
day) standalone smoke test in Executive Operating Mode confirmed the
full pipeline end to end (6 reflection sessions, Wisdom genuinely
growing from 23.8 "Young Company" to 71.2 "Seasoned Wisdom" from real
behavioral signals alone); verified in the running app with zero
console errors.

### v0.7 continued — Sage, the Socratic Mentor (Feature 32)

The company's eleventh agent, who never trades, votes, or generates a
research signal — structurally the same guarantee Meridian (Feature 24)
already made. Sage's home location reuses the Brain Room (no new scene);
its sprite is a new palette-swapped variant generated the same real,
deterministic way as all ten existing agents' — a PIL pixel-diff against
the base sheet recovered the exact 7-color remap table, reapplied with a
new deep indigo/violet target palette. Every in-game morning at 8:00,
`app/mentor.py` publishes one **Question of the Day**, drawn
deterministically from a small hand-authored 20-question library across
10 categories — real curated content, since this codebase has no
free-form question-generation capability. Each question carries at most
one honest pointer into already-existing real company content sharing
its category (a Reasoning Lab challenge, a Library of Mistakes case
study, a Reflection Chamber lesson, ...), never a fabricated
per-department "answer." Every entry is permanently archived; the
player may answer via a new endpoint, stored verbatim and never graded.
Every agent (including Sage) also gets a purely-computed **Thinking
Profile** — six traits, each reusing a distinct existing real signal
(Academy knowledge points, averaged Discipline Review factors across
trades the agent attended, Reasoning Lab/Reflection Chamber
participation counts) — deliberately not including "Patience" (already
scored directly by Discipline Review under that name) or the brief's
ungrounded "Communication"/"Adaptability." A new MENTOR Command Center
tab shows today's question, the full archive, the Question Library, and
every agent's Thinking Profile. Explicit scope cuts: a separate weekly
"Mentor Session" (the Reflection Chamber already is one), "Thinking
Exercises" (the Reasoning Lab already covers most of them), a graded
"Daily Thinking Bonus" (no honest way to grade free text), "Connected
Constitution Articles" (no Constitution system exists in this codebase),
the Question Library being consumed live by NPCs, and a dedicated
physical "Mentor Chamber" room. 14 new backend tests (336/336 passing);
verified in the running app (Playwright, 21/21) with zero console
errors — Sage's sprite and its Agent Status entry confirmed visually in
the Brain Room, and the QOTD submit-and-persist round trip confirmed via
a real save/reload.

### v0.7 continued — CEO Treasury, Company Priorities & Time Controls, Living World Schedules (Features 33-35)

The CEO gets a real protected reserve, a real strategic-focus lever, and
real control over how fast time passes; every agent's day now runs
through 24 real hours instead of stopping at the evening review. The
**CEO Treasury** is a second account, structurally isolated from
Operating Capital — every balance-changing function takes the CEO's
explicit amount as a parameter, and no automatic system anywhere in this
codebase ever reads or writes it, the same "never receives pnl"
structural guarantee the Discipline Chamber already established, checked
by grep rather than just documented. Smart Savings Rules are the one
deliberate exception, and the brief's "save 5%"/"save 10% after
profitable months" collapse into one real rule type rather than two
mechanically-identical ones. Deposit/Withdraw, rule management, the
Savings Growth Timeline, and the Monthly Savings Report all live in a
new TREASURY Command Center tab — no vault-door scene was built, the
same tab-not-new-art precedent every recent feature has followed — and
the brief's future CEO Benefits (Company Expansion, Emergency Funding,
...) aren't built since no system in this codebase can honestly spend a
real Treasury dollar into them yet. **Company Priorities** bias exactly
one real, already-existing lever each — Academy knowledge points 1.5x
faster, research confidence-gain 1.5x faster, or new trade proposals
sized against a tightened, purely-derived copy of the player's own risk
limits — never inventing a new mechanic, and the brief's Expansion/
Efficiency/Innovation options aren't offered since no real lever exists
for them. **Time Controls** (End Workday/Week/Month, plus a bounded
1-72 hour fast-forward) loop the exact same real per-tick step under one
lock rather than jumping the clock, so every exact-minute cadence check
along the way still fires — structurally identical to time actually
passing faster. **Living World Schedules** gives every agent a real,
personality-flavored off-hours routine (20:00-6:00) in the existing
Break Room rather than a new Residence scene — the asset pack has no
indoor-furniture sprites and the Lobby's 11-door layout is already
maximally packed, so the actual goal (agents feeling alive with real
routines, not vanishing after work) is delivered through 22 new
per-agent task labels and matching dialogue instead. 42 new backend
tests (378/378 passing); verified in the running app (Playwright, 20/21,
1 skipped for the same real-trade-timing reason every run of this suite
tolerates) — a real deposit/withdraw round trip, Company Priority
persisting across a reload, and a real End Workday clock jump all
confirmed against the live backend.

### v0.7 continued — CEO Calendar & Company Schedule (Feature 36)

One place that aggregates every real, already-computable recurring
company event, rather than the brief's fixed hourly company-wide
timetable — that exact synchronized choreography doesn't exist here,
since each of the 11 agents already runs its own distinct,
personality-driven schedule (Feature 35). The calendar instead surfaces
nexus.tick()'s own fixed cadence checkpoints (Weekly/Monthly Coach
Reports, the Monthly Executive Review, the Monthly Treasury Savings
Report, Weekly/Monthly Reflection Sessions, Sage's daily Question of the
Day) across a 35-day horizon; the two conditional cadences (the
Reasoning Lab challenge, the Academy mentorship check) get a live
`eligible` flag computed by re-running the exact real gate that decides
whether either actually fires, never a guess about the future. Active
research gets an honest ESTIMATED completion date/time projected from
real confidence and gain-rate data — labeled ESTIMATED, the same
standard the WhatIf Lab's own "SIMULATED" badge already set. The CEO can
also schedule custom calendar events (the brief's eight named types plus
"other") — informational only, since no real system exists anywhere in
this codebase to attach a mechanical effect to a "Company Holiday" or
"Extra Training Day" honestly. A new CALENDAR Command Center tab shows
Today's/Tomorrow's Schedule, a Weekly Agenda, Monthly Company Events, an
Executive View, and a Live Schedule where selecting any agent shows their
real current state plus their complete real daily schedule. Explicit
scope cuts: Academy Classes and Department Meetings get no fixed slot
(nothing steady to project from, meetings are spontaneous by design);
Employee Birthdays and Missed Meetings are cut outright — no real data
exists to back either; Guest Lecturer, Academy Exam, Innovation Day,
Department Workshop, Knowledge Fair, Reflection Conference, Celebration
Party, and Research Presentation have no real system behind them and
aren't fabricated. 26 new backend tests (404/404 passing); verified in
the running app (Playwright, 27/27) with a real custom-event create/
delete round trip confirmed against the live backend.

## What's next for v0.8 (not started, not scoped)

These are candidate directions surfaced by v0.6/v0.7's design, not
commitments — nothing below has been designed, and per every version's
stop condition, work stops at the end of its own brief:

- **A real `MarketDataProvider` adapter.** The interface and mock
  implementation are already in place (`market_data.py`); the natural
  next step is one real vendor (Polygon, Finnhub, Alpha Vantage, Yahoo
  Finance, or Schwab) behind an API key, still with a mock fallback when
  no key is configured. This would also let `simulation.py` replace its
  placeholder backtest metrics with real historical-data-driven ones, and
  let `scanner.py` do true rolling-window breakout detection instead of
  its current current-quote-threshold-only approach.
- **Model-generated meeting discussion, coach commentary, and vote
  reasoning.** `discussion.py`, `coach.py`'s recommendations, and
  `voting.py`'s per-agent reasons are all templated flavor text tied to
  real state; the architecture was deliberately built so a future version
  could swap the template call for a real model call without touching the
  surrounding state machines.
- **A real sector taxonomy.** v0.6's "sector concentration" risk check is
  a per-symbol concentration proxy (see `risk_engine.py`'s module
  docstring) since `ResearchCategory` isn't a real sector system — a
  future version could add one and make Guardian's concentration checks
  sector-aware rather than symbol-aware.
- **A `CompanyMemory` REST search endpoint.** `memory.search()` /
  `knowledge.search_knowledge()` already implement the filter contract;
  neither is wired to a route yet, since the frontend currently filters
  the WS-synced list client-side.
- **Monte Carlo simulation and parameter optimization.** `simulation.py`
  is deliberately structured so these can be added as new functions that
  still produce a `SimulationResult` — no other part of the pipeline
  (queueing, progress, archiving) needs to change. See
  `docs/FUTURE_ARCHITECTURE.md`.
- **Real broker paper-trading APIs** (e.g. a sandbox/paper endpoint from
  a real brokerage), once there's a real market data connection — still
  simulated money, but against real historical fills instead of
  placeholder math. `broker.py` is already shaped for this (see its
  module docstring), but no such adapter exists or is wired in v0.6.
  Explicitly not live trading.
- **Tighter order/position/decision traceability.** v0.6 links a closed
  trade back to the `TradeDecision` that approved it via a best-effort
  "most recent matching-symbol decision" lookup (see `nexus.py`'s
  `_journal_closed_trades()`), since neither `PaperOrder` nor
  `PaperPosition` carries an explicit decision/order id through the full
  chain. A future version could add those fields for exact attribution.
