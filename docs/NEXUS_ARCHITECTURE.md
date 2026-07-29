# NEXUS Architecture

**Status:** Canonical. This is the complete technical architecture of
NEXUS — the orchestration layer that owns every agent's location, task,
research, and meeting behavior. `COMPANY_LORE.md` describes what NEXUS
*feels* like from inside the building; this document describes what it
*is*.

NEXUS is not a class, a service, or a running process with its own
identity. It is `backend/app/nexus.py`'s `tick()` function and the
cluster of manager modules it calls in a fixed order, once per
simulation tick. There is no NEXUS object anywhere in the codebase —
"NEXUS" is the name for that whole call graph, the same way "the
weather" isn't one object either.

---

## System Overview

```
run_sim_loop()  (backend/app/sim.py)
  every TICK_INTERVAL_SECONDS (default 2s):
    │
    ├─► GameState.tick(minutes)        (backend/app/state.py)
    │     advances the clock, then calls:
    │     └─► nexus.tick(state, new_time, minutes)   ◄── "NEXUS" starts here
    │
    ├─► ws_manager.broadcast(build_state_message(state))   (every connected client)
    │
    └─► persist_modules(state)   (every PERSIST_INTERVAL_TICKS, or immediately on a day/trade event)
          v0.7 Save Architecture Redesign Phase 2 — splits state into
          per-module rows (backend/app/save_modules.py) and skips writing
          any module whose content hash hasn't changed since the last
          write; see backend/app/persistence.py's persist_modules().
```

Everything downstream of `nexus.tick()` is synchronous, in-process Python
— there is no message queue, no separate worker, no network hop between
any of NEXUS's own components. The entire orchestration step for all
five (soon more) agents completes inside one `asyncio.Lock`-guarded
call before the broadcast goes out. This is deliberate: partial ticks
are never observable by a client, and `KNOWN_LIMITATIONS.md` documents
the resulting single-process ceiling this implies.

## Agent Lifecycle

An agent's state (`AgentState` in `schemas.py`) is small on purpose:
`transform`, `location`, `current_task`, `mood`, `energy`, `memory`
(capped list), `override` (nullable). Its lifecycle within one tick is a
strict pipeline inside `_tick_agent()`:

1. **Override check.** If the agent has an active `AgentOverride`
   (meeting or break), decrement `remaining_minutes`. If it just
   expired, fall through to step 2 as if there were no override. If
   it's still active, the agent's location/task come from the override,
   not the schedule (`location = agent.override.location`, `task_label =
   _override_task_label(...)`).
2. **Schedule lookup.** With no active override, `block_for_hour(agent_id,
   new_time.hour)` (`schedule.py`) returns the `ScheduleBlock` for the
   current hour — this is the agent's *default* behavior, described as
   such in `schedule.py`'s own module docstring.
3. **Break roll.** If energy is below `BREAK_ENERGY_THRESHOLD`, there's a
   `BREAK_CHANCE_PER_TICK` random chance of starting a break override
   right there, overriding the schedule's own answer for this tick.
4. **Energy/mood update.** Energy moves by a fixed delta depending on
   whether the resulting location is restful (`RESTFUL_LOCATIONS`);
   mood drifts by a small random amount every tick, independent of
   location.
5. **Task-change detection.** If the resulting `task_label` differs from
   the agent's *previous* `current_task`, a `MemoryEntry` is appended
   (capped, `MAX_MEMORY`) and `_replace_working_task()` is called — this
   is the only point where a new `Task` object enters the shared `tasks`
   list.
6. **Return.** A new `AgentState` via `model_copy(update={...})` — every
   key in that dict must be the real Python field name, not the wire
   alias (`current_task`, not `currentTask`) — see `docs/Architecture.md`'s
   Gotcha section and `CHANGELOG.md` for the two times this was gotten
   wrong in practice.

An agent's lifecycle has no separate "spawn"/"despawn" concept on the
backend — every agent that exists in `AGENT_IDS` gets a `_tick_agent()`
call every tick, forever, from the moment `register_agents()`
self-heals a missing id into existence (this is also how a save from an
older, smaller roster upgrades itself the instant a new agent ships —
see `docs/DeveloperGuide.md`'s "Adding a new agent"). The *frontend*
Phaser scene's agent presence (`RoomScene.refreshAgentPresence()`) is a
pure reflection of `agent.location` re-evaluated every frame — an agent
is never explicitly "spawned into" a room by any message; it simply
appears because a scene now sees its location matches that scene's
`agentLocation`.

## Task Routing

Tasks (`Task` in `schemas.py`) are NEXUS's activity log, not a queue an
agent pulls from — nothing is ever "assigned" to an agent from a backlog.
A task is created reactively, exactly when an agent's task label changes,
by exactly one function: `_replace_working_task()`. It does two things
atomically:

1. Marks the agent's previous `"working"`-status task `"completed"`.
2. Appends a brand-new `"working"`-status task, with a category inferred
   by `_task_category()` (keyword-matched against the label and the
   agent's own default via `_DEFAULT_CATEGORY_BY_AGENT`, falling back to
   an override-reason check for meetings/breaks).

`_replace_working_task()` is called from exactly two places —
`_tick_agent()` (schedule-driven changes) and `_maybe_call_meeting()`
(a meeting starting is also a task change) — and both can fire for the
*same agent in the same tick* if a meeting starts the instant an
agent's previous override ends. Task ids are `task-{agent}-{day}-{hour}-{minute}`,
which collides in exactly that scenario; the fix is a numeric suffix on
collision, not a redesign of the id scheme (see `CHANGELOG.md`). The
broadcast list is capped to the most recent `MAX_TASKS` entries — routing
is real-time, history is bounded.

## Memory

Two distinct memory systems exist and should never be conflated:

- **Per-agent `MemoryEntry` list** (`AgentState.memory`) — a short,
  capped (`MAX_MEMORY`) personal log of "Started: {task}" entries,
  private to that agent's own state, surfaced nowhere in the UI directly
  today beyond being part of the broadcast payload.
- **Company-wide `CompanyMemory`** (`backend/app/memory.py`) — the
  searchable, categorized (`research` / `meeting` / `whiteboard` /
  `event` / `discussion` / `discovery` / `future_trade`), capped
  (`MAX_MEMORY_RECORDS` = 200, flat across all categories) log that
  powers the Company Memory viewer. Every write goes through one
  function, `record()`, which mutates the shared list in place and trims
  from the front — the same accumulator-list convention used for
  `tasks` and `news`. Only `scribe.py` calls `record()` in the current
  codebase; every other manager hands Scribe the data to record rather
  than writing to `CompanyMemory` directly, keeping "who's allowed to
  write company memory" a one-file answer.

`memory.py`'s `search()` function already implements the full
category+query filter contract used by the frontend's `CompanyMemory`
modal — it's just not wired to a REST route yet, since the frontend
currently filters the already-synced list client-side (see `docs/API.md`).

## Events

Two separate, non-overlapping event systems exist, one per side of the
WebSocket boundary:

- **Backend: no event bus.** `nexus.tick()` is a single ordered function
  call chain — "events" are just Python function calls returning updated
  data structures, threaded explicitly through `tick()`'s local
  variables (`tasks`, `news`, `memory`, `meeting_minutes`, `research`,
  `watchlist`). There is no publish/subscribe mechanism on the backend;
  ordering is guaranteed by literally being sequential code, not by a
  queue.
- **Frontend: `EventBus`** (`frontend/src/game/systems/EventBus.ts`), a
  typed pub/sub bus (see the `GameEvents` interface for the full,
  authoritative event catalog) that decouples Phaser scenes from React
  UI from the WebSocket client from `NPCManager`/`NexusManager`. A
  single incoming WS `"state"` message fans out into many typed events
  (`agent:updated`, `task:assigned`, `research:completed`,
  `watchlist:updated`, `meeting:minutesRecorded`, etc.) via diffing in
  `NexusManager.applyServerUpdate()` — comparing the previous local
  snapshot against the new one to decide which discrete events to fire,
  rather than the backend explicitly labeling what changed.

**One hard rule, learned the expensive way**: any function that updates
*multiple* pieces of state and fires *one event per piece* inside a loop
risks exposing a torn intermediate snapshot to a listener that
re-reads the *whole* current state on each fire — this exact bug shipped
in `NPCManager.loadAgents()` (fixed by updating the whole map before
firing a single event; see `CHANGELOG.md`). Any new batch-update function
on the frontend must follow the same "mutate everything, then emit once"
shape.

## Decision Pipeline

NEXUS makes exactly three kinds of "decisions" today, and none of them
are agent-authored — every one is a deterministic rule or a seeded random
roll evaluated centrally in `tick()` or its helpers:

1. **Where is each agent right now?** — schedule lookup + override state
   (see Agent Lifecycle above). Not a choice; a table lookup.
2. **Should a meeting happen?** — `_maybe_call_meeting()` rolls
   `random.random() >= MEETING_CHANCE_PER_TICK` against however many
   agents are currently free (`override is None`), requiring at least
   `MEETING_MIN_ATTENDEES`. Attendance is `random.sample()`-selected, not
   chosen by any agent.
3. **Is this research candidate worth flagging?** — `scribe.py`'s single
   threshold check, `confidence >= FUTURE_TRADE_CONFIDENCE_THRESHOLD`
   (85). The only "judgment" in the current build, and it's a fixed
   number, not a model.

There is deliberately no agent-level autonomy or LLM call anywhere in
this pipeline today — see `DESIGN_BIBLE.md`'s "Transparency Over
Automation" pillar. Every future pipeline below is scoped to extend this
list without hiding a decision from the player.

## Research Pipeline

Owned by `research.py`, called once per tick from `nexus.tick()`
immediately after agents are ticked:

```
tick_research(research)
  for each id in RESEARCHER_IDS (scout, atlas, echo, nova — never scribe):
    find that agent's one "in_progress" ResearchItem
    raise its confidence by a random amount in CONFIDENCE_GAIN_RANGE
    if confidence >= CONFIDENCE_COMPLETE (100.0):
      mark "completed", move it into that agent's capped completed history
      pick the agent's next symbol via _next_symbol() (prefers an
        unclaimed watchlist entry) and start a fresh "in_progress" item
  → returns (full research list, just-completed items)
```

The "one active item per research-capable agent" invariant is structural,
not incidental — it's the direct implementation of `DESIGN_BIBLE.md`'s
"Readable Information" pillar (one confidence bar per researcher, always,
never a backlog). Completions feed two downstream consumers in the same
tick: `record_research_completions()` (writes to `CompanyMemory` via
Scribe) and a `discovery`-category `NewsItem` appended directly in
`tick()`. `tick_watchlist()` runs immediately after, syncing each
`WatchlistEntry`'s price (via the injected `MarketDataProvider`) and
status/progress/assignedAgent from whichever research item currently
targets that symbol.

## Meeting Pipeline

Also owned by `nexus.py`, `_maybe_call_meeting()`, running after the
research pipeline so meeting attendees reflect the tick's *latest*
research state:

```
if a meeting is already active:
    still active?  → check each participant's override for reason=="meeting"
    nobody left?   → build_minutes() (scribe.py) → record_meeting()
                     → append a "meeting ended" NewsItem → clear MeetingState
    else           → no-op, meeting continues
else:
    random roll against MEETING_CHANCE_PER_TICK
    pick attendees from agents with override is None
    for each attendee: apply a "meeting" AgentOverride,
                        force location/task, replace their working task
    generate_discussion() (discussion.py) — templated per-role lines,
        each keyed off that attendee's own current research topic
    append a "meeting started" NewsItem
    → new active MeetingState with the discussion attached
```

`build_minutes()` only cites topics from research items with
`status == "in_progress"` at the moment the meeting ends — an earlier
version cited an attendee's *entire* research history, over-crediting
the summary (fixed, see `CHANGELOG.md`). `generate_discussion()` never
calls a language model — every line is a template in `_ROLE_LINES`,
interpolated with the real topic string. This is the explicit hook point
for a future model-backed discussion generator (see "Future Learning
Pipeline" below) — the architecture (participants + their current
research focus + a transcript slot on `MeetingState`) was built so that
swap could happen without touching the meeting start/end state machine
itself.

## Risk Pipeline *(not yet implemented — planned v0.9)*

No risk computation exists in the current codebase. The planned shape,
per `ROADMAP.md`'s v0.9 (Risk Engine) and `AI_AGENT_BIBLE.md`'s Guardian
and Watchtower entries: a new stage in `tick()`, running after the (by
then existing) paper-trading ledger updates, computing position
concentration and confidence-vs-outcome calibration per agent, writing
results to a new `RiskState` field on `GameSaveState` following the
exact same "add a field, broadcast it, diff it client-side" pattern
`research`/`watchlist`/`memory` used in v0.3. See `FUTURE_ARCHITECTURE.md`
for the full integration plan.

## Future Trading Pipeline *(not yet implemented — planned v0.7)*

Paper Trading's planned shape, per `ROADMAP.md` and Ledger's entry in
`AI_AGENT_BIBLE.md`: a new stage after the research pipeline that can
convert a `future_trade`-flagged `CompanyMemory` record into a paper
ledger entry, entirely simulated, with a Guardian-enforced boundary that
this pipeline can never call a real brokerage adapter — see
`FUTURE_ARCHITECTURE.md` for exactly where that boundary would live in
code (answer, in short: it wouldn't exist as code to remove later; the
real brokerage adapter itself simply wouldn't exist until v1.0, so there
is nothing for the paper pipeline to accidentally call).

## Future Learning Pipeline *(not yet implemented — no version committed)*

The hook point already exists: `discussion.py`'s `generate_discussion()`
and `research.py`'s confidence-gain logic are both currently
deterministic/templated specifically so either could be swapped for a
real model call later without changing their function signatures or
`tick()`'s call sites. "Learning" here would mean an agent's research
speed or confidence trajectory adapting based on Coach/outcome data
(v0.5+), not a foundation-model rewrite of the whole company.

## Future Coaching Pipeline *(planned v0.5)*

Coach (see `AI_AGENT_BIBLE.md`) reads `CompanyMemory`'s `future_trade`
records and the player's own engagement with them — no new backend
computation is required beyond what `memory.search()` already supports;
v0.5 is primarily a new frontend surface (a Coach dialogue flow) over
existing data. See `FUTURE_ARCHITECTURE.md`.

## Future Simulation Pipeline *(planned v0.6)*

The Simulation Lab's planned shape: a second `MarketDataProvider`
implementation serving historical series through the exact same
interface real-time providers use (`get_quote`/`get_quotes`), so Quant
and Oracle's backtests are, from `watchlist.py`'s `tick_watchlist()` perspective, just
another provider — no new data-access pattern, only a new
implementation of an interface that already exists specifically to be
implemented more than once. See `FUTURE_ARCHITECTURE.md`.

---

## How Every Component Actually Communicates

A reference table, because the prose above covers *why*; this covers
*exactly what calls what*:

| From | To | Mechanism |
|---|---|---|
| `sim.py` | `state.py` | direct `await` call, once per tick |
| `state.py` | `nexus.py` | direct function call (`nexus.tick(...)`), lock-held |
| `nexus.py` | `research.py`, `watchlist.py`, `discussion.py`, `scribe.py`, `schedule.py`, `agents.py`, `market_data.py` | direct function calls, no indirection |
| `sim.py` | connected clients | `ws_manager.broadcast()` → one JSON `"state"` message per client, every tick |
| `main.py` (startup) | `sim.py` | `asyncio.create_task(run_sim_loop())` in the FastAPI lifespan, one task for the process's lifetime |
| WS client message | `NPCManager` + `NexusManager` | `socket.ts`'s `onmessage` handler calls both directly, synchronously, in the same message handler |
| `NPCManager` / `NexusManager` | React UI | `EventBus` typed events → `gameStore.ts`'s listeners → `useSyncExternalStore` re-render |
| Phaser scenes | `NPCManager` | direct property reads every frame (`refreshAgentPresence()`), not event-driven |
| React UI (buttons) | Phaser / state | `EventBus.emit()` (e.g. `ui:companyMemory`, `ui:pause`) — the only path from UI back into game systems |

No component in this table talks to a component more than one hop away
without going through the ones in between — there is no direct line from
a React modal to `nexus.py`, for instance. This single-path-per-hop
property is what `PROJECT_STRUCTURE.md` and `CODING_STANDARDS.md` mean
when they say "no tight coupling": every new manager should be
addable to this table with exactly one new row, not a rewiring of
existing rows.
