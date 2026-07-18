# TradeTown Coding Standards

**Status:** Canonical. These are the actual conventions already enforced
by the tooling in this repository (`tsconfig.json`, `.eslintrc.cjs`,
`ruff`/`mypy` as run in CI-equivalent local checks) plus the unwritten
conventions the existing code already follows consistently. Nothing here
is aspirational tooling that doesn't exist yet — where a standard isn't
currently enforced by a tool, that's called out explicitly rather than
implied.

---

## TypeScript Conventions

Enforced by `frontend/tsconfig.app.json` (`strict: true`,
`noUnusedLocals`, `noUnusedParameters`, `noFallthroughCasesInSwitch`,
`noUncheckedIndexedAccess`) and `.eslintrc.cjs`
(`eslint:recommended` + `@typescript-eslint/recommended` +
`react-hooks/recommended`, zero warnings allowed — `npm run lint` uses
`--max-warnings 0`):

- **No `any`.** `noUncheckedIndexedAccess` plus strict mode means every
  array/record access is typed as possibly-`undefined` — handle it (a
  guard, a non-null assertion with a comment explaining why it's safe,
  or a default), never silence it with `any` or `!` used casually. See
  `RoomScene.ts`'s `getAgentSpawnPoint` for the pattern: `seats[index %
  seats.length]!` — a non-null assertion is acceptable *only* when the
  modulo makes out-of-bounds provably impossible, and that provability
  should be obvious from the surrounding code, not asserted blindly.
- **Path alias `@/*` for all cross-directory imports.** Never a relative
  `../../../` chain more than one level deep — `frontend/tsconfig.app.json`'s
  `paths` maps `@/*` to `src/*` specifically so imports read as "what
  module" not "where is it relative to me."
- **One export shape per file, named exports only** for game systems,
  entities, and scenes (`export class GameManager`, `export function
  screenGapToWorld`) — no default exports outside the two files React
  conventionally requires them for (`App.tsx`, `main.tsx`). This makes
  every import statement self-documenting about what it's pulling in.
- **Interfaces for data shapes, classes for behavior.** `AgentProfile`,
  `GameUiState`, `SceneTransitionData` are `interface`s — plain data.
  `GameManager`, `NPCManager`, `SaveManager` are `class`es with static or
  instance methods — behavior. Don't blur the two (a class with only
  static readonly fields and no methods should be a `const` object or an
  `interface` instead).
- **Static-only "manager" classes use `private static` state, never
  module-level `let`.** `NPCManager`/`NexusManager`/`GameManager` all
  keep their singleton state as `private static` class fields rather
  than free module variables — this keeps the public API
  (`NPCManager.getAgent(id)`) visually distinct from the private state
  it reads, and matches the existing pattern exactly; don't introduce a
  new module-level mutable singleton with a different shape.
- **JSDoc-style comments only where the *why* isn't obvious from the
  code.** See "Comment Style" below — this applies identically to
  TypeScript and Python.
- **React components are functions, not classes**, always
  `export function ComponentName()`, never `React.FC`. Props are typed
  inline for small components (`{ label, onClick }: { label: string;
  onClick: () => void }`) or as a named `interface` only once the prop
  list gets unwieldy (three or more optional props, roughly).
- **Tailwind utility classes only — no CSS modules, no styled-components,
  no inline `style` props** except where a value is genuinely dynamic and
  can't be expressed as a class (e.g. `ConfidenceBar`'s
  `style={{ width: ... }}`, `BrainRoomHud.tsx`'s dynamic tint swatch
  color). See `UI_UX_BIBLE.md` for the palette itself.

## Python Conventions

Enforced by `ruff==0.8.1` and `mypy==1.13.0` (pinned in
`backend/requirements-dev.txt`), run as `ruff check app/` and `mypy
app/` with no repo-level config file — both currently run on their
built-in defaults, which is itself a gap worth closing (see "A note on
missing config," below).

- **`from __future__ import annotations` at the top of every module.**
  Every current backend file starts with it — keep doing so; it's what
  lets `schemas.py`'s forward references and modern union syntax
  (`str | None`) work cleanly across the whole 3.11 codebase.
- **Pydantic `CamelModel` base for every wire-facing schema.** Never
  define a bare `BaseModel` for something that crosses the WebSocket/REST
  boundary — `CamelModel`'s `populate_by_name=True` is what makes
  camelCase-on-the-wire, snake_case-in-Python work at all. Purely
  internal dataclasses (`AgentProfile` in `agents.py`, `ScheduleBlock` in
  `schedule.py`) correctly use `@dataclass(frozen=True)` instead, since
  they never serialize over the wire.
- **`model_copy(update={...})` keys must be real field names, never wire
  aliases.** This is the single most-repeated gotcha in this codebase
  (see `docs/Architecture.md`'s dedicated Gotcha section and
  `CHANGELOG.md` for two real bugs it caused) — grep
  `backend/app/schemas.py` for `Field(alias=` and check every key
  against that list before writing a new `model_copy(update=...)` call.
- **Module-level function style for stateless managers, not classes.**
  `research.py`, `watchlist.py`, `discussion.py`, `memory.py`,
  `scribe.py` are all plain functions operating on data passed in and
  returned out (`tick_research(research) -> tuple[...]`), never a class
  wrapping that same logic in `self`. This is a deliberate, consistent
  choice across every current manager module — a new manager module
  should match it unless it genuinely needs to hold instance state
  across calls (the one current exception, `MockMarketDataProvider`, is
  a class specifically because per-symbol random-walk state must persist
  between calls — see "when a class *is* correct," below).
- **`ABC` + a single registration function for anything pluggable.**
  `MarketDataProvider` is the reference pattern: an abstract base class,
  one concrete implementation today, and a single `_select_provider()`
  function gated by an env var that's the only place a new
  implementation gets wired in. Any future adapter (a real trading
  execution backend, a second historical-data provider for Simulation
  Lab) should follow this exact shape.
- **When a class *is* correct**: state that must persist across calls
  and isn't just "the current tick's data" (an in-memory cache, a
  provider with connection state, a singleton like `GameState`). The
  rule isn't "no classes" — it's "don't wrap stateless per-tick
  transformations in a class just for the sake of it."
- **Private helpers are `_prefixed`, always module-level, never
  nested functions**, even when only used by one caller — `_now_iso()`,
  `_truncate()`, `_task_category()` in `nexus.py` are all top-level so
  they're independently readable and (eventually) testable without
  needing to invoke their caller first.
- **Type hints on every function signature, including return type.**
  `mypy`'s success is a hard requirement (see "Testing Requirements"
  below) — every function in the current codebase has a full signature;
  new code must match.

### A note on missing config

Neither `ruff` nor `mypy` has a repo-level config file today — both run
on their tool defaults. This works because the codebase is small enough
that defaults happen to match the conventions above, but it's a real gap:
a `pyproject.toml` with an explicit `[tool.ruff]`/`[tool.mypy]` section
(pinning rule selection, `strict = true` for mypy, line length, etc.)
should be added before the backend grows much further — tracked in
`TASK_BACKLOG.md`'s Infrastructure category.

## Folder Organization

- **Backend**: flat `backend/app/` — no subpackages except `routers/`.
  This is intentional at the current size; a `services/` or `managers/`
  subpackage split should only happen once `app/` genuinely gets
  unwieldy (see `KNOWN_LIMITATIONS.md`), not preemptively.
- **Frontend**: `game/{systems,entities,scenes}` for Phaser-side code,
  `ui/{components,hooks}` for React-side code, `state/` for the
  EventBus-to-React bridge, `net/` for the two network clients. A new
  file's folder is determined by *which side of the Phaser/React
  boundary it lives on*, not by feature — there is no
  `features/research/` style vertical slicing in this codebase, and
  introducing one would fight the existing horizontal-by-layer
  organization rather than complement it.
- **One class/manager per file, file name matches the export.**
  `NPCManager.ts` exports `NPCManager`, `nexus.py`... is the one
  deliberate exception (a module of related functions, not a single
  class — matching the "module-level function style" convention above).

## Naming Rules

- **`AgentId` values are lowercase, single-word, matching the agent's
  actual name** (`"scout"`, `"atlas"`) — never abbreviated, never
  suffixed (`"scout_agent"`). This is a `Literal` union in `schemas.py`
  and `types.ts`; a new agent's id is added to both in the same change.
- **Schedule/task label strings are full sentences in present participle
  form** ("Scanning market news," not "scan_news" or "News scan") —
  they're displayed verbatim in whiteboards, dialogue, and the newspaper,
  so the string *is* the UI copy. Never introduce a task label that
  needs translation before display.
- **EventBus event names are `noun:verb`** (`agent:updated`,
  `task:assigned`, `ui:companyMemory`) — never `verb:noun`. Check
  `EventBus.ts`'s `GameEvents` interface before inventing a new event
  name; if an existing event's shape almost fits, extend it rather than
  adding a near-duplicate.
- **React component files are `PascalCase.tsx`, everything else is
  `PascalCase.ts` for classes/managers and `camelCase.ts` only for
  genuinely function-only utility modules** (there are currently none of
  the latter on the frontend — every current `.ts` file exports at least
  one class).
- **Python module names are `snake_case`, matching their primary
  export's domain** (`market_data.py` not `marketdata.py` or
  `MarketData.py`).

## Documentation Rules

- **Every new manager/service/scene gets a module or class-level
  docstring/comment explaining its *role*, not its contents.** Compare
  `nexus.py`'s module docstring (explains what NEXUS's job is) against a
  bad docstring that would just restate the function list. `AgentNPC.ts`'s
  class comment is the reference example: it explains *why* there's no
  in-world speech bubble anymore, not just what the class does.
- **`docs/DeveloperGuide.md` gets a new "Adding a..." section whenever a
  new extension point is introduced**, the same way "Adding a new agent"
  and "Adding a symbol to the watchlist" exist today. A feature without
  a corresponding how-to-extend-it section is incomplete.
- **This document suite (`docs/`) is updated in the same change that
  invalidates it**, not in a follow-up. If a change contradicts a claim
  in `PROJECT_STRUCTURE.md` or `NEXUS_ARCHITECTURE.md`, the doc edit is
  part of the same commit.

## Comment Style

- **Default to no comment.** If a well-named function/variable already
  says what's happening, a comment restating it is noise. This rule is
  already stated in this project's own operating instructions and the
  existing codebase follows it closely — most functions in `nexus.py`
  have zero inline comments.
- **Write a comment only for the *why*: a hidden constraint, a subtle
  invariant, a workaround for a specific bug, or behavior that would
  surprise a reader.** The reference examples already in this codebase:
  `AnimatedActor.ts`'s comment on `NAME_TAG_SCREEN_GAP_PX` (explains
  *why* a fixed world-space offset wouldn't work across rooms with
  different zoom levels — a non-obvious constraint); `nexus.py`'s inline
  comment block right above the final `model_copy(update={...})` call
  (explains a bug class that would otherwise silently recur).
- **Never comment out dead code.** Delete it — git history is the
  record, not a commented block. (There is currently no dead/commented
  code anywhere in the shipped backend or frontend; keep it that way.)
- **No comment ever references "the current fix," a ticket number, or a
  specific past conversation.** A comment should make sense to someone
  reading the file cold, five versions from now, with zero context about
  when or why the surrounding code was written — beyond the *technical*
  reason the comment itself states.

## Git Commit Style

- **Imperative mood, present tense subject line** ("Fix whiteboards
  clipping their room's own wall," not "Fixed whiteboards" or "Fixes
  whiteboard bug") — matches every commit in this repository's history.
- **Body explains *why*, not a restated diff.** `git log --stat` already
  shows what changed; the body's job is the reasoning a diff can't
  carry — see any commit in this repo's history for the standing
  example (root cause, how it was found, why the fix is shaped the way
  it is).
- **One logical change per commit.** The NPC-distinctness commit and the
  whiteboard-placement commit shipped separately in this repo's history
  specifically because they were found and fixed at different points
  in the same session, even though they touched adjacent code — commits
  should be splittable by *reviewable idea*, not batched by "everything
  I did today."
- **Never commit with a failing `tsc`/`eslint`/`ruff`/`mypy`.** Every
  commit in this repository's history passes all four at commit time —
  this is a hard bar, not a best-effort one.

## Branch Strategy

The project currently develops on a single long-lived feature branch per
major work session (e.g. `claude/tradetown-v0-1-build-...`), rebasing
forward as versions ship, rather than a `main` + per-feature-branch
workflow. This is appropriate at the current single-contributor,
single-track-of-work stage. **The moment a second concurrent line of
work exists** (a hotfix needed while a version is mid-flight, or a second
contributor), the project should adopt: `main` as the always-deployable
branch, one short-lived feature branch per version or per bug-fix batch,
merged via PR. This transition is not scheduled — it's a trigger
condition (concurrent work appears), documented here so it isn't
improvised under pressure. See `TASK_BACKLOG.md`'s Infrastructure
category.

## Testing Requirements

**Honest current state: there are zero automated tests in this
repository.** `pytest==8.3.3` is pinned in `backend/requirements-dev.txt`
and has never been used — no `test_*.py` file exists anywhere under
`backend/app/`. The frontend has no test runner configured at all (no
Vitest, no Jest, no Playwright test suite committed to the repo, despite
Playwright being used ad hoc for manual gameplay verification during
development — see `CHANGELOG.md` for examples). This is the single
largest gap this document documents rather than papers over; see
`KNOWN_LIMITATIONS.md` and `ARCHITECTURE_REVIEW.md`'s Testing score for
the full accounting.

**Standard going forward, starting with the next version that touches
`nexus.py` or any manager module:**

- New pure-function backend logic (anything in `research.py`,
  `watchlist.py`, `discussion.py`, `memory.py`, `scribe.py`, and the
  non-agent-state helpers in `nexus.py`) should ship with a `pytest`
  unit test in a new `backend/tests/` directory, since these functions
  already take plain data in and return plain data out — they were
  *written* to be trivially testable even though nothing tests them yet.
- `model_copy(update={...})` call sites are the single highest-value
  target for a regression test, given they've caused two real bugs
  already — a test that constructs a model, calls the update, and
  asserts every intended field actually changed would have caught both.
- Frontend testing remains manual/Playwright-driven for now (verifying
  actual rendered gameplay is disproportionately valuable relative to
  the current test-infrastructure investment required) — but any new
  pure TypeScript utility function (in the shape of `UpcomingEvents.ts`'s
  `upcomingEvents()`) is a good Vitest-unit-test candidate once a runner
  is actually added.
- **Every version's completion gate remains manual verification**
  (`tsc`, `eslint`, `ruff`, `mypy`, a live gameplay walkthrough) until
  automated coverage exists to replace part of that manual burden — this
  standard doesn't retroactively block shipping v0.4 or v0.5 on having
  tests first, but every version from here forward should grow the
  suite rather than leave it at zero.

## Docker Standards

- **Multi-stage builds, non-root runtime user.** `backend/Dockerfile`
  runs as a non-root `app` user; the frontend's build stage produces
  static assets served by an nginx stage — never a `node`/`vite dev`
  process in the production image.
- **No secrets baked into an image.** Every credential-shaped value is
  an environment variable with a documented default in `.env.example`
  (root) and `backend/.env.example` — `config.py` is the only place
  `os.getenv` is called, and it's audited for exactly this reason.
- **`docker compose up -d --build` must always work on a clean checkout**
  with zero manual steps beyond `cp .env.example .env` (optional — every
  variable has a working default). This is a completion gate for every
  version, not just infrastructure work, per `DESIGN_BIBLE.md`'s
  "Deployability Is a Feature" pillar.
- **`.dockerignore` excludes anything that shouldn't be in the build
  context**: `node_modules`, `dist`, `.venv`, `__pycache__`, `data/*.db`
  — verified, not assumed, whenever a new top-level generated directory
  is introduced.
- **Healthchecks are mandatory for any new long-running service** added
  to `docker-compose.yml`, following `backend`'s existing
  `GET /api/health` pattern.
