# Known Limitations

**Status:** Canonical, honest. This document exists so that no future
version "discovers" one of these limitations the hard way — every item
below is either a deliberate, documented trade-off made for good reasons
at the current scale, or a real gap that should be closed before the
scenario that breaks it actually happens. Where a limitation has a
tracked fix, it links to the relevant `TASK_BACKLOG.md` item(s).

This document complements `ARCHITECTURE_REVIEW.md` (which scores the
codebase) rather than duplicating it — this is the itemized "here's
exactly what's true today and why," that review is the graded summary.

---

## Architectural

### Single-process, in-memory backend

`GameState` (`backend/app/state.py`) is a process-wide singleton behind
one `asyncio.Lock`, and `sim.py` runs exactly one background tick task
for the process's entire lifetime. This is correct and simple *today*
because TradeTown is explicitly single-tenant (`docs/Architecture.md`).
It becomes a hard ceiling the moment either of two things happen:
running the backend with `--workers N` (each worker gets its own
disconnected copy of the simulation, and their SQLite writes race), or
introducing multi-company saves (v1.2). Both are already flagged in
`docs/Architecture.md`'s "Production hardening notes" as things that
must never be "fixed" back into a broken state by someone who doesn't
know this constraint. **Tracked:** `TASK_BACKLOG.md` I6 (multi-company
support), I10 (scaling investigation).

### Single-tenant by design, not by accident — but still a real ceiling

One company, one save, no auth, no per-user anything. This is a
deliberate v0.1–v0.9 design choice (see `DESIGN_BIBLE.md`'s "What
TradeTown Is NOT" — "not a real-time multiplayer game"), not an
oversight. It becomes a genuine limitation the moment v1.2 (Multi-Company
Saves) is scoped — see `ROADMAP.md`'s explicit call-out that this is
"the single largest architectural change on the entire roadmap."
**Tracked:** I6, N8 (auth support).

### Hand-mirrored schemas across the client/server boundary

`backend/app/schemas.py` and `frontend/src/types.ts` are two
independently maintained files that must describe the same shapes.
`backend/app/agents.py` / `frontend/src/game/systems/AgentProfiles.ts`
and `backend/app/schedule.py` / `frontend/src/game/systems/Schedule.ts`
have the same problem. Today this is manageable because a human keeps
them in sync deliberately and `tsc`/`mypy` catch most consequences of
drift quickly — but there is no automated check that the two sides
actually agree, and a silent mismatch would only surface as a runtime
bug, not a build failure. **Tracked:** O5, O9, O10, I17 (generated
OpenAPI client, the most complete long-term fix).

### No event bus on the backend

NEXUS's "events" are just sequential Python function calls inside
`nexus.tick()` (see `NEXUS_ARCHITECTURE.md`). This keeps ordering
trivially correct today, but means any future feature that wants to
react to "a research item completed" from *outside* `tick()`'s own call
chain (a webhook, a plugin system, a second consumer) has no hook to
attach to without modifying `tick()` itself. Not a problem yet — flagged
because it will be the first thing to hit if an external-integrations
feature (webhooks, Slack notifications, etc.) is ever scoped.

## Testing

### Zero automated test coverage

Stated plainly because it's the single largest gap this document
tracks: there are no `pytest` tests despite `pytest` being pinned in
`backend/requirements-dev.txt`, and no frontend test runner configured
at all. Every version to date has been verified by manual `tsc`/
`eslint`/`ruff`/`mypy` checks plus live gameplay walkthroughs (often via
ad hoc Playwright scripts that are never committed to the repo). This
has caught real bugs (see `CHANGELOG.md`) but doesn't scale, and doesn't
prevent regressions in code paths a given session's manual walkthrough
happens not to exercise. **Tracked:** `TASK_BACKLOG.md`'s entire Testing
category (Q1–Q20), especially I2–I4 (the infrastructure to make any of
it possible) and Q6 (a regression test for the `model_copy` alias bug
class specifically, since it has already recurred once).

### No CI pipeline

Nothing runs automatically on push or PR today — every check
(`typecheck`, `lint`, `ruff`, `mypy`) is run manually, by whoever is
making the change, in their own terminal. This means there is currently
no enforcement backstop if a change ships without those checks having
actually been run. **Tracked:** I4.

## Performance & Scaling

### Flat, small caps that don't yet account for a larger roster

`CompanyMemory`'s cap (`MAX_MEMORY_RECORDS` = 200) is flat across every
category and every agent. With five agents this comfortably holds a
useful window of history. `AI_AGENT_BIBLE.md`'s planned roster includes
Pulse, whose entire design intent is high-frequency, noisy output — at
ten or fifteen agents, a flat 200-record cap would very plausibly get
dominated by Pulse's write volume the same way the flat `news` cap was
once dominated by discovery news before it was split per-category (see
`CHANGELOG.md`'s v0.2 fix). This is a known, not-yet-triggered version
of a bug TradeTown has already hit once. **Tracked:** P7.

### No delta updates over WebSocket

Every tick broadcasts the *entire* `GameSaveState` to every connected
client, not just what changed. At five agents and the current bounded
list sizes this is a small payload; it will not stay small as agent
count, research history, and memory records grow, especially once
Simulation Lab (v0.6) and Paper Trading (v0.7) add their own
data. **Tracked:** P2, N1.

### No tick-duration instrumentation

`nexus.tick()`'s actual wall-clock cost per tick has never been
measured. At five agents it's clearly fast enough (2-second tick
interval, no observed lag), but there's no data point for what happens
at fifteen agents plus a Simulation Lab backtest queue plus a Risk
Engine pass all running in the same synchronous call chain.
**Tracked:** P1, A30.

### SQLite as the only persistence layer

Appropriate for a single-tenant, single-process app with one save row —
genuinely the right choice today, not a shortcut. Becomes a real
constraint only if multi-company saves (v1.2) or genuinely large
history/memory tables arrive. **Tracked:** P6.

## Frontend

### No audio system

There is no `this.sound` usage anywhere in the codebase — no music, no
SFX, and the `musicVolume`/`sfxVolume` settings in `SettingsMenu.tsx`
currently control nothing at all. This isn't a partial feature with
rough edges; it's a complete absence. **Tracked:** `TASK_BACKLOG.md`'s
entire Audio category, especially AU1 and AU8.

### No colorblind-safe indicator for bullish/bearish

Green/red is the standard financial-data color pairing and also the
single worst pairing for the most common form of color blindness. Not
addressed today. **Tracked:** U3.

### No screen-reader support

The Phaser canvas is inherently non-semantic, and the React UI layer
carries no `aria-*` attributes today. An honest limitation, not a solved
"good enough" state. **Tracked:** U21.

### No modal Escape/click-outside close

Every modal (Settings, Company Memory, Newspaper, Pause) only closes via
its own explicit "Close" button. This is also *how* the
Newspaper/Company Memory stacking bug (`CHANGELOG.md`) was first
noticed during manual testing — the fix for the stacking bug shipped,
but the underlying missing-Escape-handler gap is still open.
**Tracked:** U1, U2.

## Backend

### No repo-level ruff/mypy configuration

Both tools run on their built-in defaults — there is no
`pyproject.toml` pinning rule selection, strictness, or line length.
Works today because the codebase is small and consistent; will not stay
implicit-safe indefinitely as more contributors or more code arrive.
**Tracked:** I1.

### `model_copy(update=...)` alias bug class has recurred once already

Documented in detail in `docs/Architecture.md`'s Gotcha section and
`NEXUS_ARCHITECTURE.md`: Pydantic's `model_copy(update={...})` silently
no-ops when given a wire alias instead of a real field name, and this
has caused two real, separately-discovered bugs
(`meeting_minutes`/`updated_at`, then `current_task`) in this codebase's
history. The mitigation today is entirely process (grep before writing a
new call), not tooling. **Tracked:** Q6 (a regression test), and this is
the strongest argument in this whole document for I1/I2 existing at all.

### No REST search endpoint for Company Memory

`memory.py`'s `search()` already implements the full filter contract the
frontend needs — it's just never been wired to a route, since the
current `CompanyMemory` modal filters the already-synced WS list
client-side. Not a bug, but a gap that will matter the moment Company
Memory's total record count makes client-side filtering of the *full*
history (rather than the last 200) desirable. **Tracked:** N6.

## Security

### No authentication anywhere

There is no login, no session, no API key — anyone who can reach the
backend's port can read and write the single save. Correct for a
single-player, typically-localhost-or-behind-your-own-reverse-proxy
deployment target; a real gap the moment multi-company saves or any
kind of hosted/shared deployment is considered. **Tracked:** N8.

### No rate limiting

Neither the REST endpoints nor the WebSocket connection point have any
rate limiting. Low-risk at the current scale and deployment model
(single-tenant, typically self-hosted), but should not be assumed safe
if TradeTown is ever deployed somewhere with untrusted network access.
**Tracked:** I14, N10.

### Real brokerage credential handling is entirely unscoped

There is no code today that would need to store a brokerage credential
— which is itself the point (see `DESIGN_BIBLE.md`'s trading boundary).
This is flagged here as a *forward* risk: whenever v1.0 is actually
authorized, credential storage security is a research question that
needs its own dedicated design pass, not a bolt-on to existing
patterns (none of which were built with that requirement in mind).
**Tracked:** T18.

## Process

### Branch strategy doesn't yet support concurrent work

The project develops on a single long-lived branch per major work
session. Documented as intentional-for-now in `CODING_STANDARDS.md`,
with an explicit trigger condition (a second concurrent line of work
appearing) for when this needs to change — flagged here because it's a
real limitation of the *current* setup, not just a stylistic choice.
**Tracked:** I20.

### Documentation drift risk

This entire `docs/` suite (introduced in bulk at v0.4) is only as
trustworthy as the discipline that keeps it updated alongside code
changes — `CODING_STANDARDS.md` states the rule (doc updates land in the
same change that invalidates them), but there is no automated check
that a docs/ file wasn't left stale after a code change. A future task
worth adding once the doc suite has survived a few versions: a CI check
that flags PRs touching `backend/app/nexus.py` or `schemas.py` without a
corresponding `docs/` change, as a nudge rather than a hard gate.

---

## Reading This List Going Forward

A limitation moving from this document into `TASK_BACKLOG.md` with a
milestone attached means it's been scoped, not just noticed. A
limitation staying in this document indefinitely, with no
`TASK_BACKLOG.md` reference at all, is a signal it's still an open
question rather than a committed fix — the Real brokerage credential
handling entry above is the clearest current example: it's flagged
deliberately vague because the real answer depends on decisions not yet
made at v1.0's own kickoff.
