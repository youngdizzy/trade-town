# TradeTown

A pixel-art AI investment company simulation (Phaser 3 + React frontend,
FastAPI backend). The player is the CEO of a headquarters staffed by AI
employees who research the market, debate strategy, vote on trades, run
paper-trading operations, study at an in-house Academy, and log
everything to a permanent company memory — live, in the background,
whether or not the player is watching.

## Read this first: the Development Rules

**[`docs/DEVELOPMENT_RULES.md`](docs/DEVELOPMENT_RULES.md) is the
constitution for this project.** It is canonical and binding — read it
before scoping or implementing any new feature. Where any request
creates ambiguity, those rules take priority. Its short version: the
company is a living, autonomous AI organization the CEO *manages*, not
operates; every feature must have real long-term substance (no
placeholders, no fake-progression numbers, no busywork); every idea
becomes company knowledge only after real evidence; and every feature
request should be scoped against its nine-part structure (GOAL /
REQUIREMENTS / SYSTEM BEHAVIOR / PLAYER ACTIONS / EMPLOYEE ACTIONS / UI /
RULES / DO NOT / SUCCESS CRITERIA) before code gets written.

## The Design Bible

**[`docs/DesignBible/`](docs/DesignBible/README.md) is the emerging
single source of truth for the whole company** — 14 volumes plus
appendices, one institutional chapter per department/feature. It is
being built one volume at a time, not all at once: today it is a real
folder structure and Table of Contents with most volumes still an
outline pointing at where their real content currently lives (scattered
across the docs below and the codebase itself). As each volume is
actually written, it absorbs and supersedes the overlapping parts of the
older documents rather than duplicating them. Check
`docs/DesignBible/README.md`'s status table before assuming a volume is
fully written — several are still stubs.

## Other canonical docs

- [`docs/Architecture.md`](docs/Architecture.md) — what's actually
  built, feature by feature, including every explicit scope cut and why.
- [`docs/API.md`](docs/API.md) — every backend endpoint and WS payload.
- [`docs/CODING_STANDARDS.md`](docs/CODING_STANDARDS.md) — TypeScript
  and Python conventions actually enforced by this repo's tooling.
- [`docs/AI_AGENT_BIBLE.md`](docs/AI_AGENT_BIBLE.md) /
  [`docs/COMPANY_LORE.md`](docs/COMPANY_LORE.md) — who each employee is.
- [`docs/UI_UX_BIBLE.md`](docs/UI_UX_BIBLE.md) /
  [`docs/DESIGN_BIBLE.md`](docs/DESIGN_BIBLE.md) — visual/interaction
  language.
- [`CHANGELOG.md`](CHANGELOG.md) — what changed, and the honest scope
  reasoning behind each change.

## Engineering discipline for every feature

This is the process that's produced everything in `CHANGELOG.md` so far,
and it's what the Development Rules' "Evidence First" / "No Placeholder
Systems" principles look like in practice:

1. **Research overlap first.** Grep/read before writing — most requested
   systems partially overlap something that already exists; extend it,
   don't duplicate it.
2. **Scope an honest subset.** If part of a request has no real data or
   mechanism to back it, cut it explicitly and say so in the code
   (module docstring / doc comment) and in `CHANGELOG.md` — never
   fabricate a number, a "growth" delta, or a validation step that isn't
   real.
3. **Backend before frontend — commit the backend first.** Implement and
   fully verify the backend slice, commit and push it, *then* start the
   frontend slice. This isn't just tidiness: in this project's history,
   sessions with both backend and frontend changes sitting uncommitted
   at the same time have caused real, unrecoverable data loss from
   stale-checkout/restart scenarios. Don't let that window stay open.
4. **Verify thoroughly before every commit:**
   - Backend (`backend/`): `python -m pytest -q`, `python -m mypy app/`,
     `python -m ruff check app/ tests/` — all clean.
   - Frontend (`frontend/`): `npx tsc --noEmit`, `npm run lint`,
     `npm run build` — all clean.
   - Playwright regression against the *live* stack (`frontend/tests/`)
     for any UI change — these hit the real running Vite + FastAPI dev
     servers, not a mock. Popups from the sim's own real-time ticking
     (trade proposals, executive votes) are expected mid-test; dismiss
     them the same way a player would (see any spec file's
     `dismissTradeOutcomePopups` helper) rather than treating them as
     bugs.
5. **Document, then commit.** Update `CHANGELOG.md`,
   `docs/Architecture.md`, and `docs/API.md` (if endpoints changed)
   before the final commit — the changelog entry is where every scope
   cut gets written down for good, not just held in conversation.

## Quick reference

- Backend: `cd backend && uvicorn app.main:app --reload --port 8000`
- Frontend: `cd frontend && npm run dev` (proxies `/api` and `/ws` to
  `:8000`)
- Backend tests: `cd backend && python -m pytest -q`
- Frontend typecheck/lint/build: `cd frontend && npm run typecheck &&
  npm run lint && npm run build`
- Frontend Playwright (needs both dev servers already running):
  `cd frontend && npx playwright test`
