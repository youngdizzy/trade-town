# Chapter 73 — Compliance, Audit & Governance System (CAGS)

**Status:** Implemented as a real audit synthesis layer — backend
(`app/audit_log.py`, `app/routers/audit.py`) and frontend (a real
`COMPLIANCE` Command Center tab, `CompliancePanel.tsx`). The brief
asks for per-event fields (Broker, User, Credentials, Software Version)
this single-player, single-broker, no-credential codebase has no real
data or mechanism to back — those stay cut, see Implementation Notes.
What shipped is real: every important event this company already
produces — CEO decisions (including real overrides), Gatekeeper/
Opportunity rejections, critical Risk Warnings, Discipline Reviews,
Emergency Stop and Defensive Mode activations, Black Swan Post-Event
records — synthesized into one searchable, chronological Audit Log,
computed fresh from already-real, already-persisted state, exactly the
way Chapter 61's Knowledge Graph and Chapter 65's Regime Reconciliation
already established for this kind of cross-cutting view. The
Institutional Time Machine addendum ships as this same Audit Log's own
chronological, steppable view — see Implementation Notes for why a full
arbitrary-instant state reconstruction ("what did the whole company
know at 3:47pm on Day 12") is explicitly cut.

**CEO directive "Features 31-35: Compliance, Governance & Continuous
Improvement System," Feature 31** adds the one real exception to "CAGS
is entirely read-only" below: `app/compliance_incidents.py` is a
genuinely persisted, mutable Incident Resolution lifecycle (`open` ->
`investigating` -> `remediation` -> `awaiting_verification` ->
`resolved` -> `reopened` -> `investigating`), the CEO-editable
open/acknowledged/resolved workflow this chapter's original
Implementation Notes explicitly cut as having "no real pending state to
triage." That reasoning held for the original, ephemeral Incident view
(`compute_incidents()`, still unchanged below) — a blocked trade or
filed Discipline Review really is fully resolved by construction the
instant it's recorded. Feature 31 opens a *second*, genuinely pending
question on top of that: **what did the company actually do about the
underlying problem the incident flagged** — and that answer is not
resolved by construction; it requires real investigation, a real
remediation plan with a real deadline, and real verification before
anyone may call it closed. See the new "Incident Resolution Engine"
section below.

## Executive Summary

The brief's thesis — "nothing inside TradeTown should happen without
explanation" — is already mostly true. This codebase's real discipline
(established long before this chapter) already records *why* almost
everything happened: every `GatekeeperRejection` carries real `reasons`;
every `CeoDecisionRecord` carries `agreedWithAi`; every
`DisciplineReview` carries real scored `factors`; every
`ExecutiveMeetingLogEntry` carries the real department-by-department
`opinions` that led to a recommendation. What was missing was not the
underlying accountability data — it was one place to search, filter, and
step through all of it together. That is the real, closeable gap CAGS
closes.

## Mission

Give the CEO one honest, searchable answer to "what happened, why, and
who was accountable" — built entirely from real, already-persisted
records this company produces during normal play, never a second,
parallel logging system, and never a fabricated field this codebase has
no data source for.

## Philosophy

Accountability is not a new mechanic bolted onto trading — it is the
trading system's own decision trail, made visible. Every check this
chapter's Audit Log surfaces (Gatekeeper's 9 named checks, Sentinel/
Guardian's risk gates, the Executive Board's department opinions) was
already real and already enforced before this chapter existed. CAGS
does not add new authority, new policies, or new enforcement — it adds
transparency over authority, policy, and enforcement that already runs
every tick.

## Responsibilities

**Owns:** the unified Audit Log (`AuditEntry`, synthesized from ten real
source types), the Incident view (a severity-filtered read of the same
log), the Governance Framework display (a disclosed, real description of
Gatekeeper's actual 9-check order plus where the Institutional Rule
Engine sits relative to it), the Compliance Overview aggregate, CEO
Override tracking (`CeoOverrideRecord`, reading `CeoDecisionRecord.
agreedWithAi`, real since Chapter 70 Part 2), (Feature 31) the Incident
Resolution Engine, and (Feature 32) CEO Override Governance — both
described under Decision Logic below.

**Does NOT own** (see Appendix E): any trade-approval authority
(`app/gatekeeper.py` — CAGS reads its real check results, never adds a
10th check or changes pass/fail logic), Risk Limits enforcement
(`app/risk_engine.py` — read-only), the Institutional Rule Engine's own
evaluation logic (`app/rule_engine.py` — CAGS surfaces its real output,
never recomputes a rule check), and Executive Board voting
(`app/executive_intelligence.py` — read-only). CAGS adds no new
decision-pipeline check anywhere in this pass.

## Ownership

Real code this chapter is authoritative over: `app/audit_log.py` (all
compute functions below), `app/routers/audit.py` (five original
read-only GET endpoints, unchanged, plus Feature 31's nine new
incident-case endpoints). The original five endpoints keep their exact
prior behavior: no new `GameSaveState` fields, no WS broadcast changes,
no `app/nexus.py` per-tick wiring — every one of those functions is
still computed fresh per request from state the game already persists,
the identical convention `app/knowledge_graph.py`, `app/whatif.py`, and
`app/regime_reconciliation.py` already established for a cross-cutting,
read-only synthesis.

**Feature 31 adds** `app/compliance_incidents.py`, the one real
exception: `GameSaveState.compliance_incidents` (a new, persisted,
`MAX_COMPLIANCE_INCIDENTS = 500`-capped list), synced once per tick in
`app/nexus.py` (from that tick's own final Audit Log, after every
source list has reached its tick-final value) and mutated via seven new
`GameState` methods in `app/state.py`. Deliberately **not** added to the
WS broadcast — matching this chapter's own "genuine on-demand fetch"
convention above; a 500-entry incident backlog has no reason to ride
every real-time tick when the Compliance panel already fetches on
demand.

**Feature 32 adds** `app/override_governance.py`, on the identical
pattern: `GameSaveState.ceo_override_evaluations` (a new, persisted,
`MAX_OVERRIDE_EVALUATIONS = 500`-capped list), synced and refreshed once
per tick, mutated via one new `GameState` method (`add_override_review`),
also kept off the WS broadcast.

Ten real, already-persisted source types this chapter reads from but
never duplicates or recomputes:

- **CEO Decisions** (`CeoDecisionRecord`, `app/executive.py`) — real
  `agreedWithAi` flag is the honest CEO Override signal (Chapter 70
  Part 2's own accuracy-tracking field, reused here for the identical
  meaning the brief asks for).
- **Executive Meeting Log** (`ExecutiveMeetingLogEntry`) — the real
  department-by-department `opinions` behind a recommendation.
- **Gatekeeper Rejections** / **Opportunity Rejections** — real blocked
  trades, with real `reasons`.
- **Risk Warnings** (critical severity only) — Sentinel/Guardian's real
  gates (`app/risk_engine.py`).
- **Discipline Reviews** (`app/discipline.py`) — real scored process
  reviews, `weak`/`reckless` tiers surfaced as incidents.
- **Emergency Stop** activation/resume (`app/emergency_stop.py`, via its
  real `CompanyMemory` record).
- **Defensive Mode** activation/deactivation (Chapter 72,
  `BlackSwanEventRecord`).
- **Crisis Briefings** (Chapter 72, via their real `CompanyMemory`
  record).
- **Rule Evaluations** (`app/rule_engine.py`'s `RuleCheckResult`, across
  every Account with enabled custom rules) — real `correctiveAction`
  text, reused verbatim, never invented.

## Inputs

`ceo_decisions`, `executive_meeting_log`, `gatekeeper_rejections`,
`opportunity_rejections`, `risk_warnings`, `discipline_reviews`,
`memory` (filtered to `alert`-category records for Emergency Stop/Crisis
Briefing), `black_swan_events`, `accounts` (for live Rule Engine
evaluation) — all already on `GameSaveState`, already capped by their
own existing `MAX_*` constants, so this chapter adds no new unbounded
growth anywhere.

## Outputs

- `GET /api/audit/log?category=&severity=&search=&limit=` — the
  unified, filterable, keyword-searchable Audit Log, newest first.
- `GET /api/audit/incidents` — the same log, filtered to
  `warning`/`critical` severity only.
- `GET /api/audit/governance` — the real, disclosed 9-layer Gatekeeper
  check order plus the Institutional Rule Engine's real (disconnected)
  position.
- `GET /api/audit/overview` — the Compliance Dashboard aggregate: open
  incident count, Executive Accuracy (reused from Chapter 70 Part 2,
  never recomputed), CEO Override count/rate, automation status (reused
  from the real Company Operating Mode), Defensive Mode status (Chapter
  72).
- `GET /api/audit/overrides` — every `CeoOverrideRecord`, the CEO's
  real disagreements with the AI's recommendation and their real
  resolved outcome once known.
- **Feature 31 — the Incident Resolution Engine.** `GET
  /api/audit/incidents/cases` (the real, persisted case list, distinct
  from the ephemeral `/incidents` filter above), `GET
  /api/audit/incidents/summary` (the real aggregate — see Decision
  Logic below), and seven `POST /api/audit/incidents/{id}/...` lifecycle
  mutation endpoints (`investigate`, `remediate`, `evidence`,
  `submit-verification`, `fail-verification`, `resolve`, `reopen`).
- **Feature 32 — CEO Override Governance.** `GET
  /api/audit/overrides/evaluations` (the real, persisted
  `CeoOverrideEvaluation` list, distinct from the ephemeral
  `CeoOverrideRecord` list above), `GET /api/audit/overrides/summary`
  (the real aggregate — see Decision Logic below), and `POST
  /api/audit/overrides/{id}/review` (a reviewer's note, never a change
  to `processQuality`/`outcome`). `POST /api/executive/decide` also
  gained an optional `overrideReason` field — a real, new CEO-provided
  mechanism, `None` for every decision before it existed.
- **Feature 34 — Compliance Control Effectiveness.** `GET
  /api/audit/controls/effectiveness` — per-control effectiveness for all
  11 real Gatekeeper checks, computed fresh from
  `TradeDecision.gatekeeperVerdict.checks` and
  `GatekeeperRejection.outcome` (see Decision Logic below). Read-only,
  same computed-fresh-per-request convention as the original five
  endpoints above — no new persisted state, unlike Features 31/32.
- **Feature 35 — the Continuous Compliance Improvement Loop.** `GET
  /api/audit/continuous-improvement` — real remediation effectiveness
  and root-cause recurrence over `state.compliance_incidents` (see
  Decision Logic below). Read-only, same computed-fresh-per-request
  convention as Feature 34.

## Internal Workflow

1. On request, `compute_audit_log()` walks the ten real source lists
   above, converts each real record into one `AuditEntry` (a real
   summary/detail string built from that record's own real fields,
   never templated filler), and sorts newest-first.
2. Query params (`category`, `severity`, `search`, `limit`) filter the
   already-built list server-side — a real, working search, not a UI
   placeholder over an unfiltered dump.
3. `compute_incidents()` is a pure filter over the same list
   (`severity != "info"`) — never a second, independently-built list
   that could drift from the Audit Log.
4. `compute_compliance_overview()` counts the filtered results and reads
   two already-real computed values (`compute_executive_accuracy_scores()`
   from Chapter 70 Part 2, `state.defensive_mode.active` from Chapter
   72) rather than inventing a new "compliance score" formula from
   scratch — see Decision Logic for the one genuinely new number this
   chapter does compute.

## Decision Logic

**AuditEntry severity** — reused directly where the source record
already has one (`RiskWarning.severity`, `Rule` corrective actions →
`warning`), or mapped from a real, disclosed table where it doesn't
(Gatekeeper/Opportunity rejections → `warning`; Emergency Stop/Crisis
Briefing/`reckless`-tier Discipline Reviews → `critical`; everything
else → `info`). Never a fabricated numeric risk score per event.

**Compliance Score** — the one new number this chapter computes: `100 -
min(60, 5 × open_incident_count)`, where `open_incident_count` is the
real count of `warning`/`critical` entries in the current Audit Log.
Disclosed and simple on purpose — this is a real, checkable formula over
a real count, not a fitted or backtested model, the same "conservative
but arbitrary, no real regulatory requirement behind it" honesty note
`RiskLimits` itself already carries. **This formula is unchanged by
Features 31, 32, 34, or 35.** The CEO directive's own Feature 35 rules
require explicit CEO authorization before this specific formula may be
edited — see this section's own "Compliance Score formula — the
documented limitation" note below for the full disclosure, the proposed
change, and confirmation that no such authorization has been sought or
given, so nothing here touches it. There is still no "resolved
incidents" *count feeding this score* — but see the Incident Resolution
Engine below for the real resolution workflow that now exists
independently of it, and Feature 35's real Company Health connection
below for where that evidence DOES flow today.

**Incident Resolution Engine (Feature 31)** — a strict, explicitly
enforced state machine, `ALLOWED_TRANSITIONS` in
`app/compliance_incidents.py`:

```
open -> investigating -> remediation -> awaiting_verification -> resolved
                                                  |                  |
                                                  v                  v
                                             remediation          reopened -> investigating
```

`open -> resolved` in one step is structurally impossible — every
transition function checks the incident's *current* status against
`ALLOWED_TRANSITIONS` and returns `None` (never raises, never silently
succeeds) on an invalid request, the same "return `None`, let the caller
reject the request" convention `app/executive.py`'s `hold_proposal()`
already established. `verify_and_resolve()` is the *only* path to
`status="resolved"`, and it is the only function that ever sets
`resolvedAt`/`resolutionSimDay`/`rootCause`/`correctiveAction` — set
together, atomically, never partially. A verification can also
genuinely fail (`fail_verification()`), bouncing the incident back to
`"remediation"` rather than forcing a false resolution.

`sync_incidents_from_audit_log()` (called once per tick, from
`app/nexus.py`, after that tick's own Audit Log is final) is the *only*
creation path — every `ComplianceIncident.sourceEntryId` traces back to
exactly one real `AuditEntry.id` this chapter's own `compute_audit_log()`
already produced, deduplicated so the same event can never open two
cases. Nothing here re-detects incidents a second way.

`rootCause` (`process_failure` / `control_failure` / `data_failure` /
`model_failure` / `human_error` / `governance_failure` /
`communication_failure` / `unknown`) is genuinely optional everywhere
except `verify_and_resolve()`, and even there `"unknown"` is always an
honest, valid answer — never forced to a specific category the evidence
doesn't support (per the CEO directive's "Missing Data Is Not Failure"
rule).

Three honest aggregates in `ComplianceIncidentSummary`
(`compute_incident_summary()`), each guarding against the CEO
directive's specific "do not fabricate" concerns:
`averageResolutionSimDays` is `null`/`None` — never a fabricated `0` —
when nothing has ever actually resolved through the real lifecycle yet;
`severityWeightedBacklog` reuses `app/company_health.py`'s own existing
`_SEVERITY_PENALTY` weight table rather than inventing a second one;
`overdueCount` only counts a real SLA deadline (stamped once at
`begin_remediation()`, never guessed at incident-creation time) that has
actually passed while the incident remains unresolved — a `"resolved"`
incident is never counted overdue even past its old deadline.

**CEO Override Governance (Feature 32)** — the CEO directive's own
brief warned "CEO OVERRIDES: 138, 69.0% — do not assume this is good or
bad." Research first: `CeoDecisionRecord.outcome` (`app/executive.py`'s
`resolve_proposal()`) already resolves an override that produces a real
trade exactly like any other decision — `outcome="pending" if
order_id is not None else "undecidable"` is keyed on whether a real
order was placed, **not** on `agreed_with_ai`. Only an override that
resolves to `"wait"` (no order at all) stays `"undecidable"` forever,
correctly, since there is nothing real to grade. Feature 32 never
re-grades that outcome a second way — `refresh_override_outcomes()`
only mirrors it every tick.

What Feature 32 genuinely adds is a second axis, PROCESS QUALITY,
answering "was the override justified by evidence available at the
moment the CEO decided" — independent of the trade's eventual P&L (no
hindsight contamination, per the directive's own explicit rule). Built
entirely from the real, already-persisted `ExecutiveMeetingLogEntry`
for that same proposal (`opinions`, `decisionGrade`/`decisionGradeScore`)
— never a fabricated confidence score, and never a second copy of
`app/risk_engine.py`'s own logic (only the Risk department's own
already-recorded opinion `stance` is read). A disclosed 2x2 heuristic —
"strong" (`decisionGradeScore >= 80.0`, reusing the exact B- boundary
`app/executive.py`'s own `GRADE_THRESHOLDS` already established) crossed
with "contested" (fewer than half the real department opinions on file
plainly agreed with the recommended action) — yields
`justified`/`unjustified`/`mixed`, with `not_enough_evidence` when no
`ExecutiveMeetingLogEntry` exists for the proposal at all. Process
quality and outcome are two separate, never-collapsed fields: a
justified override that lost money and an unjustified override that won
are both shown honestly.

`overrideReason` is a genuinely new, real, optional CEO-provided text
field on `POST /api/executive/decide` — `None` for every decision
recorded before it existed, never a fabricated backfill. Sample-size
honesty: `CeoOverrideGovernanceSummary.overrideRatePct` is `None`
(never a fabricated 0%) when there are no real decisions to divide by,
and `sampleSizeSufficient` gates trend interpretation on a disclosed,
arbitrary floor (`MIN_OVERRIDE_SAMPLE_FOR_TREND = 5`), the same honesty
convention this chapter's own Compliance Score already carries.

**Compliance Control Effectiveness (Feature 34)** — the CEO directive's
own core question: "did the control prevent or detect the problem it
was designed to address," not just how often it exists or fires.
Research first: all 11 real Gatekeeper checks
(`app/gatekeeper.py::evaluate_gatekeeper()`) already run unconditionally
on every real trade decision and are stored, per-decision, on
`TradeDecision.gatekeeperVerdict.checks` — so `triggeredCount` is a real
count of every time a control actually ran, never a fabricated "how
often could this fire" estimate. `passedCount`/`failedCount` are a
direct tally over the same real per-decision checks.

Proving CONTROL WORKS (not just CONTROL EXISTS) needs real evidence a
rejection was right or wrong — the only honest source is the
already-real `GatekeeperRejection.outcome` grading
(`would_have_won`/`would_have_lost`, resolved purely from real
subsequent watchlist price movement, never a placed order). But
`evaluate_gatekeeper()`'s `approved = all(c.passed for c in checks)`
means a single rejection can have several checks failing at once, so an
outcome can only be attributed to one specific control when that
control was the *sole* failing check for that decision
(`soleReasonRejectionCount`) — every other case counts as
`ambiguousAttributionCount` instead, never guessed at. Among sole-reason
rejections, `would_have_lost` means the block was correct
(`confirmedPreventedCount`); `would_have_won` means the block was a
false positive (`confirmedFalsePositiveCount`); still-`pending` or a
rejection record no longer on file (evicted by
`MAX_GATEKEEPER_REJECTIONS`) both count as `pendingEvaluationCount` —
not yet confirmed either way, never assumed.

`effectivenessState` is `not_yet_tested` when a control has never once
failed a decision (CONTROL EXISTS, never yet had the chance to prove
CONTROL WORKS — the directive's own "NO TRIGGERS ≠ FAILURE" rule,
literally implemented, not just disclosed in prose), `insufficient_data`
when it has failed decisions but fewer than
`MIN_CONTROL_SAMPLE_FOR_VERDICT = 3` confirmed outcomes exist yet (the
same evidence-floor pattern Feature 33's `MIN_ACCURACY_SAMPLE_FOR_VERDICT`
established), `mixed` when there IS enough confirmed evidence but the
prevented-vs-false-positive split lands in the ambiguous 40-60% middle
band (real mixed evidence, deliberately never collapsed into
`insufficient_data`, which would misreport it as no evidence), and only
`effective`/`ineffective` once that sample floor is cleared and the
split clearly favors one side — the same 60%/40% convention Feature 33
already reused from `ExecutiveVoting.tsx`'s own pre-existing
green/amber/red thresholds, reused a third time here for one consistent
evidence-grading language across the whole Compliance system.

`controlRegression` answers the directive's "if a previously effective
control begins failing, flag CONTROL REGRESSION" instruction with a real
computation, not a hardcoded flag: a control's own confirmed,
sole-reason outcome history is sorted chronologically and split into an
earlier half and a more recent half — only when each half
independently clears the same sample floor — and regression is flagged
only when the earlier half read `effective` and the recent half now
reads `ineffective`. A single bad recent outcome, or a sample too thin
to support both halves' own verdicts, never triggers it.

**Continuous Compliance Improvement Loop (Feature 35)** — closes the
loop the CEO directive named: INCIDENT (Feature 31) -> ROOT CAUSE (the
real, CEO-recorded `rootCause`, set only at `verify_and_resolve()`) ->
REMEDIATION (the real `correctiveAction` text) -> MONITORING/OUTCOME/
EFFECTIVENESS REVIEW (this feature) -> COMPANY HEALTH (below). No new
persisted state — every incident this reads already existed from
Feature 31.

*Remediation effectiveness.* `compute_remediation_effectiveness()`
grades every incident that has ever been resolved at least once. The
strongest possible evidence a fix failed is a real, CEO-driven
`reopen()` — an incident with `reopenedCount > 0` always reads
`ineffective`, regardless of the observation window below. Short of
that, `REMEDIATION_EVAL_WINDOW_SIM_DAYS = 5` (reused verbatim from the
Incident Cases UI's own existing default SLA window,
`CompliancePanel.tsx`'s `deadlineSimDay = incident.simDay + 5` — this
codebase's own established real expectation for how long a remediation
reasonably takes, not a fourth invented number) must elapse since
resolution before "no recurrence yet" honestly reads `effective` rather
than `not_enough_evidence`. Once that window has passed, a real OTHER
incident sharing this one's exact (`rootCause`, `category`,
`department`) signature that opened *after* this incident's resolution
reads `partially_effective` — this specific fix never reopened, but the
same underlying problem class showed up again elsewhere.

*Recurring failure.* `compute_root_cause_recurrence()` implements the
directive's own literal wording — "the same root cause repeatedly
produces incidents" — as a real, coarser, disclosed-as-broader count per
`rootCause` alone (not narrowed by category/department the way
per-incident effectiveness scoring above is): `RECURRING_FAILURE_MIN_COUNT
= 2` (recurring honestly means "happened more than once," a structural
count, not a statistical rate, so this floor is deliberately lower than
the rate-verdict floors Features 33/34 use).

*Company Health connection.* Feature 35's real evidence connects into
the EXISTING Company Health architecture (Chapter 63,
`app/company_health.py`) as a genuinely new, additive eleventh
Executive-tier dimension, `complianceHealth` — never a rewrite of any
existing dimension. `_compliance_health()` blends three real, distinct
signals equally: incident resolution rate, the remediation-effectiveness
distribution above, and Feature 34's control-effectiveness distribution
— each defaulting to the neutral 50.0 `_risk_governance()` already
established for "no real evidence yet" (never a fabricated 0 or 100),
minus a real, disclosed, capped penalty (`min(30.0, recurring_failure_count
× 10.0)`) for any confirmed recurring failure.

*Compliance Score formula — the documented limitation.* The CEO
directive's own Feature 35 rules are explicit: if the existing
Compliance Score formula (`app/audit_log.py::compute_compliance_score()`
— `100 - min(60, 5 × open_incident_count)`) is inadequate, the correct
response is (1) document the limitation, (2) propose a change, (3)
determine whether the CEO has explicitly authorized changing the
formula, (4) only change it if explicitly authorized. Documented here,
per that rule:

- *The limitation:* the formula counts open incidents only. It has no
  way to reward a company that resolves incidents quickly and
  effectively, and no way to penalize one that resolves them but the
  same root cause keeps recurring (RECURRING FAILURE) or whose controls
  have regressed (CONTROL REGRESSION, Feature 34). Two companies with
  identical open-incident counts score identically today even if one
  has a spotless remediation record and the other reopens the same
  incident every week.
- *The proposed change (not applied):* fold a bounded adjustment from
  Feature 35's real remediation-effectiveness and recurring-failure
  evidence into the formula — for example, a real bonus for a
  genuinely high effective-remediation rate and a real penalty mirroring
  `_compliance_health()`'s own recurrence penalty, both capped the same
  conservative way the existing `min(60, ...)` term already is.
- *Authorization:* not sought, and not given. The CEO directive that
  commissioned Features 31-35 authorized building the evidence
  (Features 31/32/34/35) and connecting it to Company Health (this
  section, above) — it did not separately authorize rewriting
  `compute_compliance_score()` itself, and no later instruction in this
  session did either.
- *Result:* `compute_compliance_score()` is byte-for-byte unchanged by
  this feature. The real evidence lives in `complianceHealth`
  (Company Health) and `GET /api/audit/continuous-improvement`
  (this router) instead. If a future CEO instruction explicitly
  authorizes changing the Compliance Score formula itself, that
  authorization — quoted verbatim — belongs in this section before any
  such change ships.

**Governance Framework** — not a new authority chain. It is the real,
disclosed order `app/gatekeeper.py::evaluate_gatekeeper()` already
checks in (confidence → risk manager alignment → CEO/AI agreement → AI
debate outcome → portfolio exposure → correlation → active risk
warnings → market intelligence quality → weighted executive
recommendation), displayed as a real governance layer list, plus one
honest disclosure: the Institutional Rule Engine (Chapter 69 Part 3) is
real but **not wired into this live chain** — its Custom Rules attach to
secondary Accounts that live trade execution doesn't route through yet
(Chapter 70 Part 3's own documented gap, unchanged by this chapter).

## Department Cooperation

**Receives (read-only):** Executive Board, Trade Gatekeeper, Risk
Engine, Discipline Chamber, Institutional Rule Engine, Emergency Stop,
Black Swan Intelligence.

**Provides:** the Audit Log, Incident view, Governance display,
Compliance Overview, and CEO Override history to the CEO-facing
dashboard. Provides nothing back into any decision pipeline — CAGS
cannot block, delay, or approve anything; it is a read-only observer,
the same standing Chapter 71's Economic Intelligence Center and Chapter
72's Black Swan Intelligence both hold before any future Gatekeeper
wiring.

## CEO Controls

The original five endpoints stay entirely read-only — no configurable
retention window (every source list already caps itself), no
audit-log weight profile. Filtering (`category`/`severity`/`search`) is
a query-time read parameter, not a persisted setting.

**Feature 31 adds the first real exception:** the Incident Cases tab lets
the CEO (or an assigned owner/verifier agent, via the UI's real agent
picker) advance a real incident through its real lifecycle — assign an
owner, log a remediation plan and SLA deadline, log evidence, submit for
verification, and either verify-and-resolve (choosing a real root cause
and recording a real corrective action) or fail verification back to
remediation. Reopening a resolved incident is also a real CEO/owner
action. None of this is auto-advanced by the sim — every transition
requires a real action through the UI or API.

**Feature 32 adds a second:** the Override Governance tab lets a
reviewer (via the UI's real agent picker) attach a real review note to
an existing override evaluation — visible alongside the real,
automatically-computed process-quality/outcome read, never replacing or
gating either. The CEO may also now type a real reason at the moment of
an override decision (`overrideReason` on `POST /api/executive/decide`)
— optional, and honestly `None` when not provided.

## Learning System

None built this pass. The Audit Log is a real historical record, not a
grading loop — nothing here scores whether an incident "should have"
happened differently. Discipline Reviews (a real source this chapter
reads) already own that grading function; CAGS does not duplicate it.

## KPIs

The real Compliance Score (Decision Logic above) and the real CEO
Override rate (`overrideCount / totalDecisions` from
`CeoDecisionRecord`) are the only two published numbers. No fabricated
"transparency score" or "accountability index" — see the brief's own
Success Metrics list, most of which (Transparency, Traceability,
Decision Quality, Operational Integrity) already have a real analog
elsewhere in this codebase (Decision Grade, Executive Accuracy,
Discipline Tier) that this chapter reuses rather than re-deriving.

## Reports

None new. The Audit Log itself, freshly queryable at any time, is this
chapter's report — a fixed cadence (Daily/Weekly Compliance Brief) was
considered and cut: nothing about compliance state in this codebase
changes meaningfully faster than the CEO can just open the tab and look,
unlike Market/Economic/Black Swan Intelligence's real tick-driven
signals.

## Safety Systems

CAGS has no safety authority. It cannot activate Emergency Stop, cannot
override a Gatekeeper check, and cannot mutate any real risk/rule state.
It only ever reads.

## Dependencies

`app/executive.py`, `app/executive_intelligence.py`,
`app/gatekeeper.py` (read-only, for its real check *order*, not its
per-proposal results), `app/risk_engine.py`, `app/discipline.py`,
`app/emergency_stop.py`, `app/black_swan.py`, `app/rule_engine.py`,
`app/accounts.py`, `app/memory.py` — all read-only. No new external
dependency.

## Connected Features

`GET /api/audit/*` sits alongside `GET /api/knowledge-graph` and `GET
/api/market/regime-reconciliation` in the same "cross-cutting,
computed-fresh, read-only synthesis over real state" family. The
Institutional Time Machine (below) is this same family's chronological
presentation, not a separate data model.

## Future Expansion

The CEO-editable incident status workflow this section previously
deferred now ships as Feature 31's Incident Resolution Engine, override
*quality* evaluation (process vs. outcome, not just frequency) now ships
as Feature 32's CEO Override Governance, the Executive Accuracy Evidence
pipeline now ships as Feature 33 (Chapter 70 Part 4 — replaces
`compute_executive_accuracy_scores()`'s old `0.0`-when-untracked default
with a real `NOT_ENOUGH_EVIDENCE`/`PASS`/`FAIL`/`INCONCLUSIVE` state),
real per-control effectiveness measurement (did the control actually
prevent or detect what it was designed to address, not just how often it
exists/fires) now ships as Feature 34, and the Continuous Compliance
Improvement Loop — real remediation effectiveness, real recurring-
failure detection, and connecting all of the above into Company Health
through the existing architecture — now ships as Feature 35, above.
Per that feature's own Feature-35 rules, no change to the Compliance
Score formula itself was authorized, so none was made (see that
section's "documented limitation" note for the full disclosure and
proposed-but-not-applied change). Wiring the Compliance Score into the
Trade Gatekeeper as an advisory-only check, following the Chapter 70
Part 3 / Chapter 71 precedent, remains open if a future addendum
explicitly asks for it. Also open: prompting for `overrideReason`
directly in the quick-decision UI (`ExecutiveVoting.tsx`) — the field is
real and working via the API today, just not yet surfaced at the moment
of the decision itself.

## Company Principle

Every real decision this company makes already has a reason attached to
it somewhere in this codebase. CAGS's only job is to make sure the CEO
never has to go looking for it.

## Implementation Notes

**The honesty boundary, explicit and complete.** This codebase has one
player (no "User" identity distinct from "CEO"), one broker
(`PaperBroker`, 100% simulated, confirmed by Chapter 68's own
architecture doc), no credentials of any kind to protect, and no
per-event historical version tag. Given that, the brief's sections below
are cut outright rather than half-built:

- **Per-event Broker/User/Software Version fields** — cut from
  `AuditEntry` entirely rather than populated with a repeated constant
  ("SIMULATED" on every single row) or a fabricated identity. `Account`
  is a real per-entry field where the underlying record actually has
  one (a `CeoDecisionRecord`/`GatekeeperRejection` always trades the
  primary portfolio today — see Chapter 69 Part 1's own documented gap,
  "live trading execution in a chosen non-primary account is not wired
  here" — so this field would currently always read "Primary Portfolio"
  too; included anyway since it is at least real and non-constant once
  that gap closes).
- **Encrypted credentials / access permissions / Security section** —
  cut entirely. There is nothing to encrypt: no API keys, no stored
  password, no multi-user access-control model anywhere in this
  codebase (confirmed repeatedly across Chapters 68/71/72's own honesty
  boundaries).
- **A mutable Incident workflow** — originally cut with the reasoning
  that every incident this chapter surfaces is already fully resolved by
  construction the instant it's recorded (a blocked trade never
  executed; a Discipline Review is filed only after the trade already
  closed). That reasoning was correct as far as it went, and the
  original ephemeral `/incidents` view is untouched by what follows. But
  Feature 31 (CEO directive "Features 31-35") identified a genuinely
  different, genuinely pending question the original cut conflated with
  it: whether an event was *itself* resolved (yes, by construction) is
  not the same question as whether the company *did anything about the
  underlying problem it flagged* — investigate it, remediate it, verify
  the fix held. That second question has real pending state (nothing
  had ever been investigated, remediated, or verified for any of these
  incidents before Feature 31 shipped) and is now a real, built workflow
  — see the Incident Resolution Engine under Decision Logic above. This
  bullet is corrected rather than deleted so the reasoning trail stays
  honest about what changed and why.
- **In-game Version History / searchable release notes** — cut. This
  codebase's real version history already lives in `CHANGELOG.md` and
  git history, both already the authoritative record of every Design
  Bible chapter, feature, and bug fix. Building a second, in-game copy
  risks exactly the kind of silent drift this Design Bible forbids
  elsewhere (see Chapter 61's own refusal to duplicate the Knowledge
  Graph's source data). Not surfaced in this pass.
- **The Institutional Time Machine's full point-in-time state
  reconstruction** ("what did the whole company know at any arbitrary
  instant" — market data, portfolio, positions, news, Knowledge Graph
  state, Company Memory, all simultaneously, for any moment in
  history) — this codebase takes no periodic full-state snapshots; only
  specific subsystems snapshot themselves on their own real cadence
  (`EconomicIntelligenceReport`/`BlackSwanReport`/
  `MarketIntelligenceReport`, once per real in-game evening;
  `DecisionVaultEntry`/`ExecutiveMeetingLogEntry`, once per real
  decision). Reconstructing "the exact state at 3:47pm on Day 12" for
  an arbitrary instant with no report or decision on file at that
  moment is not possible without inventing data. What ships instead is
  real: the Audit Log's own chronological order, already covering every
  timestamped moment this codebase actually recorded — a real history
  browser, honestly scoped to real recorded moments, not a claim of
  omniscient rewind. The CEO can step through it exactly as the brief
  asks ("chronologically... read-only... for Learning, Auditing,
  Debugging, Incident Investigation") — just never for a moment this
  codebase never actually captured.

**What IS real:** the ten-source Audit Log, keyword/category/severity
filtering, the Incident view, the disclosed real Governance Framework
order, the Compliance Score formula, and CEO Override tracking off the
real `agreedWithAi` field — all described in full under Decision Logic
above.

**Files changed, original pass:** `app/schemas.py` (new
`AuditEventCategory`/`AuditEntry`/`GovernanceLayer`/
`ComplianceOverview`/`CeoOverrideRecord`); `app/audit_log.py` (new
module); `app/routers/audit.py` (new router, 5 endpoints); `app/main.py`
(router registration); `tests/test_audit_log.py`. Verification: `mypy
app/` clean, `ruff check app/ tests/` clean, full `pytest -q` passing,
zero regressions. No `app/state.py`/`app/nexus.py`/`app/ws_manager.py`/
`app/save_modules.py` changes — this chapter adds no persisted state.

**Files changed, Feature 31 (CEO directive "Features 31-35"):**
`app/schemas.py` (new `IncidentStatus`/`IncidentRootCause`/
`IncidentVerificationStatus`/`ComplianceIncident`/
`ComplianceIncidentSummary`, plus `GameSaveState.complianceIncidents`);
`app/compliance_incidents.py` (new module — sync + 7 lifecycle
functions + 3 aggregates); `app/nexus.py` (per-tick sync, after every
source list reaches its tick-final value); `app/state.py` (7 new
`GameState` mutation methods, `hold_trade_proposal()`'s "return `None`
on invalid transition" contract); `app/routers/audit.py` (9 new
endpoints, original 5 untouched); `app/save_modules.py`
(`compliance_incidents` added to the `knowledge_archive` save module);
`tests/test_compliance_incidents.py` (26 tests — sync/dedup/cap, every
lifecycle transition including the invalid ones, verification failure,
reopen history preservation, overdue/backlog/average-resolution
honesty). Frontend: `types.ts`, `net/api.ts` (9 new calls), and
`CompliancePanel.tsx` (new "Incident Cases" tab, distinct from and
alongside the original ephemeral "Incidents" tab). Verification: `mypy
app/` (145 files) clean, `ruff check app/ tests/` clean, full backend
`pytest -q` (1920 passed; 6 pre-existing `test_nexus.py` failures
confirmed present before this change and left untouched, not "fixed" to
force a green suite), `tsc --noEmit` clean, `npm run lint` clean, `npm
run build` clean, live Playwright verification against the real dev
stack (owner assignment and the open -> investigating transition
confirmed working end-to-end against the real backend).

**Files changed, Feature 32 (CEO directive "Features 31-35"):**
`app/schemas.py` (new `OverrideProcessQuality`/`CeoOverrideEvaluation`/
`CeoOverrideGovernanceSummary`, plus `GameSaveState.ceoOverrideEvaluations`
and a new optional `overrideReason` on `CeoDecisionRecord`);
`app/override_governance.py` (new module — process-quality heuristic,
sync, outcome-refresh, review, summary); `app/nexus.py` (per-tick
sync/refresh, after `ceo_decisions`/`executive_meeting_log` reach their
tick-final values); `app/state.py` (`submit_ceo_decision()` gained an
optional `override_reason` param; one new `add_override_review()`
method); `app/routers/executive.py` (`SubmitCeoDecisionRequest` gained
`overrideReason`); `app/routers/audit.py` (3 new endpoints);
`app/save_modules.py` (`ceo_override_evaluations` added to
`knowledge_archive`); `tests/test_override_governance.py` (20 tests —
the full 2x2 process-quality truth table plus not-enough-evidence,
sync/dedup, override-reason carry-through, outcome mirroring, review
notes never touching quality/outcome, summary aggregation). Frontend:
`types.ts`, `net/api.ts` (4 new calls), and `CompliancePanel.tsx` (new
"Override Governance" tab, distinct from the original ephemeral "CEO
Overrides" tab). Verification: `mypy app/` (146 files) clean, `ruff
check app/ tests/` clean, full backend `pytest -q` (1940 passed; same 6
pre-existing `test_nexus.py` failures, unchanged), `tsc --noEmit`
clean, `npm run lint` clean, `npm run build` clean, live Playwright
verification against the real dev stack (a real override evaluation
rendered with an honest `NOT_ENOUGH_EVIDENCE`/`UNDECIDABLE` read for a
decision that predates the meeting-log feature, and a real
`POST /api/audit/overrides/{id}/review` call was driven through the UI
end-to-end — the reviewer's name and note appeared immediately).

**Files changed, Feature 34 (CEO directive "Features 31-35"):**
`app/schemas.py` (new `GatekeeperControlEffectivenessState`/
`ControlEffectivenessRecord`/`ControlEffectivenessSummary` — no new
`GameSaveState` field, since this reads state that already exists);
`app/control_effectiveness.py` (new module — a static catalog of all 11
real Gatekeeper checks' purpose/owner text, plus a pure
`compute_control_effectiveness()` reading `state.decisions` +
`state.gatekeeper_rejections`); `app/routers/audit.py` (one new
read-only endpoint, `GET /api/audit/controls/effectiveness`, on the
original CAGS computed-fresh-per-request convention — no per-tick sync,
no `nexus.py`/`state.py`/`save_modules.py` change);
`tests/test_control_effectiveness.py` (15 tests — not-yet-tested vs.
never-triggered, sole-reason attribution for both outcomes, pending and
missing-rejection handling, ambiguous multi-check-failure attribution,
every evaluation-state boundary including the honest `mixed` state, and
control-regression detection on both a genuine earlier/later split and a
consistently-effective control that must never falsely regress).
Frontend: `types.ts`, `net/api.ts` (1 new call), and
`CompliancePanel.tsx` (new "Control Effectiveness" tab, alongside the
five CAGS tabs above it). Verification: `mypy app/` (147 files) clean,
`ruff check app/ tests/` clean, full backend `pytest -q` (1960 passed;
same 6 pre-existing `test_nexus.py` failures, unchanged, plus one
independently-confirmed-flaky `test_foundational_mentors.py` test that
passed in isolation), `tsc --noEmit` clean, `npm run lint` clean, `npm
run build` clean, live Playwright verification against the real dev
stack: a real live CEO-approved BUY on SPY drove a real `TradeDecision`
with a real `gatekeeperVerdict` through the actual Gatekeeper, and the
Control Effectiveness tab correctly rendered all 11 controls as
`triggeredCount: 1, passedCount: 1` — real live evidence, not a mock.

**What genuinely still separates CONTROL EXISTS from CONTROL WORKS,
honestly:** attribution is only unambiguous when a control was the
*sole* failing check for a rejection — multi-check-failure rejections
are counted as `ambiguousAttributionCount` rather than guessed at, so a
control that mostly fails alongside others will show a real
`effectivenessState` built from a smaller confirmed sample than its raw
`failedCount` might suggest. That's the honest cost of never inventing
an attribution the evidence doesn't support.

**Files changed, Feature 35 (CEO directive "Features 31-35"):**
`app/schemas.py` (new `RemediationEffectivenessState`/
`RemediationEffectivenessRecord`/`RootCauseRecurrence`/
`ContinuousImprovementSummary`, plus a new `complianceHealth` field on
`CompanyHealth` — no new `GameSaveState` field for the loop itself,
since this reads Feature 31's already-persisted incidents);
`app/continuous_improvement.py` (new module —
`compute_remediation_effectiveness()`, `compute_root_cause_recurrence()`,
`compute_continuous_improvement_summary()`); `app/company_health.py`
(new `_compliance_health()`, wired into `compute_company_health()` as
the executive tier's 11th dimension — two new required parameters,
`compliance_incidents`/`current_sim_day`, threaded through both real
call sites in `app/nexus.py`/`app/state.py`); `app/routers/audit.py`
(one new read-only endpoint, `GET /api/audit/continuous-improvement`);
`tests/test_continuous_improvement.py` (13 tests — never-resolved
exclusion, the observation-window boundary, reopened-always-wins even
past the window, same-signature recurrence with correct
category/department narrowing, recurring-failure detection at and below
the floor, summary aggregation) plus `tests/test_company_health.py`
(one fixture update so the existing "everything maxed, no
recommendations" test also supplies real strong compliance evidence).
Frontend: `types.ts`, `net/api.ts` (1 new call), `CompliancePanel.tsx`
(new "Continuous Improvement" tab), `CompanyPanel.tsx` (new "Compliance
Health" cell in the Executive Health grid, "Ten" corrected to "Eleven"),
and two client-side default `CompanyHealth` placeholders
(`NexusManager.ts`/`gameStore.ts`) updated with the new required field.
Verification: `mypy app/` (149 files) clean, `ruff check app/ tests/`
clean, full backend `pytest -q` (1974 passed; same 6 pre-existing
`test_nexus.py` failures, unchanged), `tsc -b --noEmit` clean (caught
and fixed two missing-required-field errors in the client-side
placeholders that a bare, unscoped `tsc --noEmit` invocation had
missed — the project's own `npm run typecheck`/`build` scripts use
`tsc -b --noEmit`, the composite-project-aware form, which is what
actually gates CI), `npm run lint` clean, `npm run build` clean, live
Playwright verification against the real dev stack: a real incident was
driven through its full real lifecycle
(investigate -> remediate -> submit-verification -> resolve) via the
live API, and the Continuous Improvement tab correctly rendered it as
NOT ENOUGH EVIDENCE (the observation window hadn't elapsed yet) with
the real corrective-action text and root cause; the Company panel's new
Compliance Health cell read 35, independently hand-verified against the
formula: `(1 resolved / 19 total incidents × 100 + 50 neutral
remediation + 50 neutral controls) / 3 = 35.1`.

**What's genuinely still unbuilt:** every item in the honesty-boundary
list above, plus a Trade Gatekeeper wiring for the Compliance Score,
plus everything the "Compliance Score formula — the documented
limitation" note above discloses (a real, proposed, but explicitly
not-CEO-authorized change to `compute_compliance_score()`), plus
surfacing `overrideReason` directly in the quick-decision UI — all
deliberate, all documented, none silently dropped. With Feature 35
shipped, the CEO's own 31->32->33->34->35 loop is complete: every stage
the directive named now has a real, working, honestly-evidenced
implementation.
