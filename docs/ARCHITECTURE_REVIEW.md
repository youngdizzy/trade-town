# Architecture Review — v0.4 Baseline

**Status:** Canonical, dated to the v0.3.1 codebase (post the
NPC-distinctness and whiteboard-placement fixes, pre-v0.4 documentation).
Per `TASK_BACKLOG.md`'s D15, this review should be re-scored at every
major version from here forward — each re-score should diff against the
previous one, not just restate current-state scores in isolation.

Every score below is a 1–10 rating with the concrete evidence that
produced it — no score in this document is a vibe. Where a score implies
a task, that task is in `TASK_BACKLOG.md` and cited by ID.

---

## Scores

| Category | Score | Trend |
|---|---|---|
| Maintainability | 8/10 | — (baseline) |
| Scalability | 5/10 | — (baseline) |
| Performance | 7/10 | — (baseline) |
| Readability | 9/10 | — (baseline) |
| Modularity | 8/10 | — (baseline) |
| Extensibility | 9/10 | — (baseline) |
| Security | 4/10 | — (baseline) |
| Testing | 2/10 | — (baseline) |
| Documentation | 9/10 | — (baseline, post-v0.4) |

**Unweighted average: 6.8/10.** The spread is the actual finding here,
not the average: TradeTown is architecturally excellent where it's been
exercised (extensibility, readability) and honestly weak where it
hasn't been exercised yet at all (testing, security) — a startup-shaped
risk profile, not a uniformly-mediocre one.

---

### Maintainability — 8/10

**Evidence for:** Every backend manager module follows the same
function-in, data-out shape (`CODING_STANDARDS.md`); every frontend
manager follows the same static-class-with-private-state shape; the
`model_copy(update=...)` gotcha, once discovered, was documented in
`docs/Architecture.md` immediately and specifically to prevent
recurrence — and still recurred once anyway (`current_task`, see
`CHANGELOG.md`), which is *also* evidence for this score, not against
it: the second occurrence was found fast (a live gameplay walkthrough)
and fixed in the same session, because the codebase's consistency made
"grep for the same pattern elsewhere" a viable diagnostic strategy.

**Evidence against:** Hand-mirrored schemas (`schemas.py` ↔ `types.ts`,
`agents.py` ↔ `AgentProfiles.ts`, `schedule.py` ↔ `Schedule.ts`) are a
standing maintenance tax with no automated drift check
(`KNOWN_LIMITATIONS.md`). No `pyproject.toml` pinning lint/type-check
strictness means the bar could silently shift under a tooling upgrade.

**Score rationale:** An 8, not higher, specifically because of the
mirroring risk — the codebase is highly maintainable *as long as a
human remembers to update both sides*, which is a process guarantee, not
a structural one. **Related:** `TASK_BACKLOG.md` O5, O9, O10, I1.

### Scalability — 5/10

**Evidence for:** The adapter pattern (`MarketDataProvider`) and the
"add a field, broadcast it, diff it" pattern used for every v0.3 feature
both scale cleanly to *more features* without a rewrite — this is
extensively documented and demonstrated in `FUTURE_ARCHITECTURE.md`.

**Evidence against:** The backend is a single-process, single-tenant,
in-memory singleton by explicit design (`docs/Architecture.md`,
`KNOWN_LIMITATIONS.md`). This isn't a bug — it's the right choice for
what TradeTown is today — but it is a real, hard, documented ceiling:
this architecture cannot scale to multiple concurrent companies, cannot
run with multiple worker processes, and would need a genuine rewrite of
`state.py`'s ownership model to do either.

**Score rationale:** A 5 reflects "excellent at scaling *features*,
poor at scaling *tenancy/concurrency*, and both facts are equally true
and equally load-bearing." This is not a criticism of a wrong choice —
it's an accurate description of a chosen, documented trade-off with a
known future cost (v1.2). **Related:** `TASK_BACKLOG.md` I6, I10.

### Performance — 7/10

**Evidence for:** No observed performance problems at the current scale
(five agents, 2-second tick interval, bounded list sizes everywhere).
Every list sent over the wire is server-side bounded before broadcast
(`docs/API.md`'s trimming table) specifically to keep client-side
rendering cheap.

**Evidence against:** Zero instrumentation exists — there is no data
point for tick duration, WebSocket payload size growth, or React
re-render frequency under load, because nobody has measured any of
them. "No observed problems" and "verified performant" are different
claims, and this codebase can only honestly claim the first one.

**Score rationale:** A 7 reflects confidence in the *design* (bounded
lists, capped history, adapter patterns that don't add overhead) without
the *measurement* to back a higher score. **Related:** `TASK_BACKLOG.md`
P1, P2, P12.

### Readability — 9/10

**Evidence for:** The "comment only for the why" discipline
(`CODING_STANDARDS.md`) is consistently followed — grep any backend
module and the comments that exist explain a constraint or a bug class,
never restate the adjacent code. Function and variable names carry real
information (`_replace_working_task`, `screenGapToWorld`,
`CONFIDENCE_GAIN_RANGE`) rather than being placeholder-generic. Every
non-obvious design decision this review's own citations point to
(sprite mirroring, camera cover-fit zoom, the alias gotcha) is explained
in prose *somewhere* in `docs/`, not left as tribal knowledge.

**Evidence against:** Almost nothing — the one honest ding is that
`nexus.py` at 456 lines is approaching the size where a reader needs to
hold several pipeline stages in mind at once to follow `tick()` fully;
still comfortably readable today, worth watching as more pipeline
stages (Paper Trading, Risk Engine) are added.

**Score rationale:** A 9 is a genuinely high score and earned —
docked one point purely on `nexus.py`'s growing length as a forward-
looking concern, not a present one.

### Modularity — 8/10

**Evidence for:** `EventBus` decouples every frontend system from every
other one by name, not by reference. `MarketDataProvider`'s adapter
pattern decouples price-data sourcing from every consumer. Scribe (a
fifth agent) shipped with *zero* changes to `RoomScene`, `NPCManager`,
or any Phaser scene — the strongest single piece of evidence in this
whole codebase that the module boundaries are drawn in the right places.

**Evidence against:** `nexus.py` is still the one place that "knows
about" every other backend manager (`research.py`, `watchlist.py`,
`discussion.py`, `scribe.py`) by direct import and call. This is
correct today — NEXUS's *job* is orchestration — but it means `nexus.py`
grows by one import and one call site for every new pipeline stage
(`FUTURE_ARCHITECTURE.md` describes exactly this pattern for Paper
Trading and Simulation Lab), and there is no ceiling on how many stages
`tick()` could eventually accumulate before it needs to be split.

**Score rationale:** An 8 — genuinely modular at the consumer/producer
boundary, with one honestly-necessary central orchestrator that is a
natural, monitored growth point rather than a design flaw.

### Extensibility — 9/10

**Evidence for:** This is the codebase's strongest property, and it has
been *proven*, not just designed for, twice: Scribe was added in v0.3
with zero Phaser scene changes (the payoff of v0.2's `AGENT_IDS`-driven
iteration investment, explicitly noted in `docs/VersionHistory.md`), and
`FUTURE_ARCHITECTURE.md` demonstrates that Coach, Simulation Lab, Hall of
Fame, and Paper Trading all attach to existing extension points without
a rewrite. The "Adding a new agent" / "Adding a symbol to the watchlist"
/ "Adding a real MarketDataProvider" sections in
`docs/DeveloperGuide.md` are not aspirational — they describe a checklist
that has already been executed successfully.

**Evidence against:** Extensibility has only been proven for the
*specific* extension shapes the codebase was designed around (new
agent, new watchlist symbol, new provider). A genuinely novel extension
shape — one not anticipated by any existing pattern — hasn't been
attempted yet, so its cost is unverified.

**Score rationale:** A 9, one of the two highest scores in this review,
because the evidence is unusually strong for a project this young — most
codebases claim extensibility; this one has shipped proof of it twice.

### Security — 4/10

**Evidence for:** No secrets are hardcoded anywhere (`config.py` is the
sole `os.getenv` call site, audited for exactly this reason); Docker
runs as a non-root user; CORS origins are explicitly configured, not
wildcarded.

**Evidence against:** No authentication, no rate limiting, no request
validation beyond Pydantic's type checking, and — looking forward — no
credential-storage design exists yet for the brokerage integration that
`FUTURE_ARCHITECTURE.md` explicitly flags as needing its own dedicated
security design pass before v1.0.

**Score rationale:** A 4 is an honest score for a single-tenant,
typically-self-hosted, no-real-money application — the *actual* risk
today is low because the threat model is narrow (see
`KNOWN_LIMITATIONS.md`'s Security section for the explicit reasoning),
but the score reflects the *architecture's* current security posture,
not a risk-adjusted "it's probably fine" judgment. This score should
rise sharply before v1.0 and should be re-scored, not assumed, the
moment any multi-tenant or real-money capability is added.

### Testing — 2/10

**Evidence for:** `pytest` is already a pinned dependency, meaning
adopting it requires zero new tooling decisions — pure execution debt,
not a blocked decision. Every backend manager module's function-in/
data-out shape (`CODING_STANDARDS.md`) was, whether deliberately or not,
already written to be trivially unit-testable.

**Evidence against:** Zero automated tests exist anywhere in this
repository, backend or frontend (`KNOWN_LIMITATIONS.md`). Every version
to date has shipped on manual verification alone. The `model_copy` alias
bug recurring once, despite being documented after its first occurrence,
is the single clearest piece of evidence that manual verification and
documentation alone are not sufficient — a five-line regression test
would have caught the second occurrence at write-time instead of at
gameplay-walkthrough-time.

**Score rationale:** A 2, not a 0 or 1, purely because the
*preconditions* for good testing (a testable architecture, a pinned
test framework) already exist — the gap is entirely execution, not
design. This is the single lowest score in this review and the single
highest-leverage fix available: closing it doesn't require an
architecture change, just doing the work.

### Documentation — 9/10

**Evidence for:** As of v0.4, TradeTown has more design documentation
than code — `docs/` now includes an architecture reference, a developer
guide, an API reference, a version history, a changelog, and (as of this
review) a full design-and-planning suite (`DESIGN_BIBLE.md` through
this document). Every non-obvious decision cited throughout this review
has a documented home.

**Evidence against:** All of this documentation is new as of v0.4 and
therefore *unproven* against drift — `KNOWN_LIMITATIONS.md`'s
"Documentation drift risk" entry is the honest caveat: a large doc suite
introduced all at once is a large doc suite that can go stale all at
once if the "update docs in the same change" discipline
(`CODING_STANDARDS.md`) isn't actually followed starting at v0.5.

**Score rationale:** A 9 reflects genuine, current completeness, with
one point held back specifically because completeness at a single point
in time isn't the same claim as staying accurate — that claim can only
be earned version over version, which is exactly why D15
(re-score every major version) exists.

---

## Recommendations for Version 0.5

In priority order, reasoned from the scores above:

1. **Stand up the testing infrastructure before writing Coach's logic,
   not after.** Testing's 2/10 is this review's clearest finding, and
   v0.5 is the first version since this review to add real new backend
   behavior. Do `TASK_BACKLOG.md` I1–I4 (ruff/mypy config, `pytest`
   suite, Vitest runner, CI pipeline) as v0.5's first work, then write
   Coach's review-flow logic *with* tests from the start, rather than
   adding v0.5 to the pile of untested code and hoping v0.6 is when
   testing finally happens. This is the single highest-leverage
   recommendation in this document.
2. **Write the `model_copy` alias regression test (Q6) immediately,
   independent of everything else.** It's the cheapest possible test to
   write, it directly targets a bug class that has already cost real
   debugging time twice, and it validates that the testing
   infrastructure from recommendation 1 actually works before anything
   more complex is built on top of it.
3. **Do not let `nexus.py` cross ~600 lines without revisiting its
   structure.** Modularity's one real risk is `tick()`'s growing stage
   count. Coach doesn't add a pipeline stage (it's a pure reader), so
   v0.5 is safe on this front — but Simulation Lab and Paper Trading
   (v0.6/v0.7) both do, per `FUTURE_ARCHITECTURE.md`. Flag this as a
   check to make explicitly at v0.6's kickoff, not a v0.5 task.
4. **Close the two cheapest UI accessibility gaps as part of v0.5's own
   scope, not a separate pass.** U1 (Escape-to-close) and U3
   (colorblind-safe indicator) are both Small complexity and High
   priority in `TASK_BACKLOG.md` — Coach's dialogue-review UI is new
   surface area, and building it with these fixes already in place is
   cheaper than retrofitting them later across a larger UI surface.
5. **Do not begin closing the Security score (4/10) at v0.5.** This is
   a deliberate *non*-recommendation: security work (auth, rate
   limiting) has no natural home in Coach's scope, and doing it
   piecemeal ahead of a real driving requirement (multi-tenancy at
   v1.2, or brokerage integration at v1.0) risks building the wrong
   shape of security model. Revisit this recommendation at v0.9 (Risk
   Engine) or v1.0's kickoff, whichever comes first — not before.
6. **Re-run this review at v0.6's kickoff**, after Coach ships,
   specifically checking whether recommendation 1 actually happened —
   if Testing is still 2/10 at that point, treat it as a process
   failure worth discussing before adding Simulation Lab's own
   complexity on top.
