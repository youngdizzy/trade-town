# Chapter 71 — Institutional Rule Engine (IRE)

**Status:** Pure architecture, not yet implemented — same posture as
[Chapters 68](chapter-68-institutional-broker-management-system.md)/
[69](chapter-69-multi-account-fund-management-system.md)/
[70](chapter-70-prop-firm-rule-engine.md). **Researched first:** this
chapter's own central claim — "no account type should implement its
own independent rule system; every account loads its own configurable
Rule Profile into one centralized engine" — is the exact opposite of
how this codebase enforces every real risk check today. `evaluate_
sentinel_risk()`, `evaluate_guardian_exposure()`, and the Trade
Gatekeeper's eight checks (Chapters 57/58/66) are real, working, and
deliberately hardcoded Python functions with named, fixed thresholds —
not a data-driven rule interpreter, not organized into swappable
profiles, and not configurable without a code change. That's not an
oversight this chapter's architecture quietly fixes; it's a genuine
trade-off this chapter must own honestly: today's hardcoded checks are
simple and auditable by design (this Design Bible's own repeated "no
black-box composite" convention), and any real IRE implementation has
to preserve that same transparency for a CEO-authored rule, never trade
it away for configurability. See the Implementation Notes at the
bottom for the precise inventory.

## Executive Summary

Every account type this Design Bible has described so far — Personal,
IRA, Business, Prop Firm, Family (Chapter 69) — would otherwise tempt a
separate, bespoke rule system per type. This chapter's own mission is
to prevent that duplication before it starts: one centralized engine,
fed a per-account Rule Profile, enforcing every account's rules the
same way. **Researched first:** the risk-checking *shape* this brief
wants — unconditional, pre-trade, block-and-explain — already exists
and already works, real today, for the one account this codebase has.
What doesn't exist is the *generalization*: today's checks are
hardcoded per-function, not data-driven per-profile, so there is
nothing yet a CEO could point a new account type at without a code
change.

## Company Philosophy

"TradeTown should never hard-code account behavior; accounts define
rules, the Institutional Rule Engine enforces them" is a real
architectural commitment this codebase has not made yet — today, every
real risk rule *is* hard-coded, on purpose, readable in one place per
check (`app/risk_engine.py`, `app/gatekeeper.py`), which is exactly how
this Design Bible's own transparency principle ("every decision must be
explainable," Volume 9's own architecture principles) has been honored
so far. Adopting this chapter's philosophy is not a free upgrade — it
trades some of that today's-code-is-the-documentation simplicity for
real configurability, and a real implementation has to earn that trade,
not just declare it.

## Primary Responsibilities

**Would own:** centralized rule enforcement for every account type,
Rule Profile loading/management, the fourteen-plus Rule Categories, the
Custom Rule Builder, and the Rule Execution Order every trade would
pass through.

**Does NOT own** (matches the brief, and matches this codebase's real
division of labor): Trade Decisions (the analyst desk), Broker
Communication (Chapter 68), Account Management itself (Chapter 69 owns
*which* accounts exist; the IRE only enforces the rules attached to
them), and — critically — deciding *what* any specific account type's
rules should be (Chapter 70 owns the Prop Firm rule list; a future
chapter would own Personal/IRA/Business/Family's own lists; the IRE
only ever executes them).

## Ownership

Every brief concept checked against the real codebase before this
chapter was written:

| Brief concept | Real system today | What it actually does |
|---|---|---|
| "Institutional Rule Engine" (one centralized enforcer) | *(genuinely does not exist)* | Grep-confirmed: no `Rule`, `RuleProfile`, or `RuleEngine` class or module exists anywhere in `backend/app/`. Every real check is its own named function, called directly by `app/nexus.py`, never through a shared interpreter. |
| "Rule Profiles" (per-account-type rule sets) | *(does not exist)* | `RiskLimits` is one single global object per game save — not a set of named profiles a CEO could pick from, and not attachable to a specific account, since no per-account model exists (Chapter 69). |
| "Rule Execution Order" (AI Decision → Risk Authority → IRE → Broker Management System → Order Execution) | Real for two of five stages | AI Decision (real — the analyst desk) → Risk Authority (real — Chapters 57/58/66's pre-trade veto pipeline) → *IRE* (does not exist) → *Broker Management System* (Chapter 68, itself pure architecture) → Order Execution (real — `app/broker.py`'s simulated fill). Today's real pipeline skips straight from Risk Authority to Order Execution — the exact same finding Chapter 68's own Internal Workflow section already made independently. |
| "If any rule fails: block, explain, suggest corrective actions, record in Company Memory" | Three of four real today | Block (real — the Trade Gatekeeper's unconditional reject), Explain (real — every real check carries a specific reason string, never generic), Record in Company Memory (real — `app/scribe.py` already records risk-relevant events). **Not real:** "suggest corrective actions" — a rejected proposal today states *why* it failed, never a recommended fix (e.g., "reduce size by X% to comply"). |
| "Rule Categories" (14 named + Future Rule Packs) | Five real, individually, under different names | Capital Rules (real — cash-reserve floor, Ch57), Risk Rules (real — `RiskLimits`), Drawdown Rules (real — `maxDrawdownPct`), Position Rules (real — `maxPositionPct`/`maxOpenPositions`), Automation Rules (real, but singular — Operating Mode, not a rule set). **Not real:** Leverage Rules (no leverage concept, Ch68/70), Broker Rules (no broker, Ch68), Time Rules (no weekday/hour-gating, Ch70's addendum), Market Rules (Chapter 65's regime read is real but never framed as a blocking rule), Account Rules (no account model, Ch69), Strategy Rules (Chapter 45's `Strategy` stage-gating is real but not rule-driven), Tax Rules (no tax concept anywhere in this codebase), Compliance Rules (no compliance framework exists), Custom CEO Rules (no rule-authoring surface exists), Future Rule Packs (aspirational by the brief's own framing). |
| "Custom Rule Builder" (CEO writes rules without code changes) | *(genuinely does not exist)* | No rule-authoring UI, no rule DSL or parser, no natural-language-to-check pipeline anywhere in this codebase. Checked against the brief's own six examples individually — see Custom Rule Builder section below. |

## Inputs

**Real today:** every individual `RiskLimits` field this chapter's
Rule Categories table confirms real, and Chapter 65's real market
regime/volatility read. **Would need, once real:** a Rule Profile per
account (does not exist — depends on Chapter 69), a rule-definition
format the Custom Rule Builder could parse (does not exist).

## Outputs

**Real today:** a blocked trade with a real, specific reason (the
Trade Gatekeeper's own output shape). **Would produce, once real:** a
suggested corrective action alongside the block reason, and a
per-account Rule Compliance state distinct from today's single global
risk-warning list.

## Internal Workflow

**The brief's own Rule Execution Order, stage by stage, already covered
in full under Ownership above** — two of five stages real, three
(IRE, Broker Management System, and any account-scoped hand-off between
them) not yet built. A real IRE would insert itself as one new stage
between two real, already-connected ones (Risk Authority and Order
Execution), not replace either.

## Decision Logic

**Real today, for every individually-real check:** each is a
transparent, named threshold comparison — Chapter 66's own "no
black-box composite" convention, restated once more here because it's
the one principle a Custom Rule Builder implementation must not break.
**Not real:** any generic rule-evaluation formula that could take an
arbitrary CEO-authored rule (a string, a DSL expression, whatever form
it eventually takes) and decide pass/fail against live trade data —
this is the one piece of new decision logic this whole chapter actually
requires, and it doesn't exist in any form yet.

## Department Cooperation

**Would receive from:** Chapters 57/58/66 (Risk Authority — the real
rule logic this engine would centralize, never duplicate), Chapter 68
(Broker Management System — the real next stage in the brief's own
execution order, itself pure architecture), Chapter 69 (Account
Management — the source of which Rule Profile applies to which
account), Chapter 70 (the Prop Firm rule list — the first, and so far
only, fully-specified Rule Profile this Design Bible has written).
**Would provide:** pass/fail decisions with reasons to every account's
trade pipeline, a corrective-action suggestion, and a Company Memory
record for every real block.

## CEO Controls

| Control | Status |
|---|---|
| Select a Rule Profile for an account | **Not built** — no account model (Chapter 69) and no Rule Profile concept exist yet. |
| Author a Custom Rule | **Not built** — no rule-authoring surface exists anywhere. |
| Configure existing named limits (Daily Loss, Position Size, ...) | **Already real**, globally scoped — every one of these is already a CEO-editable `RiskLimits` field via `POST /api/risk-limits`, today, for the one account that exists. |
| Enable/disable a Rule Category | **Not built** — rules aren't organized into toggleable categories today; each is its own independent check. |

## Rule Profiles

**Genuinely unbuilt, for all five named examples** (Personal, IRA,
Business, Prop Firm, Family) — this section restates Chapter 69's own
Portfolio DNA finding rather than re-deriving it: the underlying
machinery several of these profiles would need already exists
(position sizing, daily/weekly/monthly loss limits, the Prop Firm
profile's own special rules per Chapter 70), just not organized as a
named, selectable, per-account bundle. **The one real exception,
already confirmed by Chapter 70's own research:** the Prop Firm
profile's core three rules (Daily Loss Limit, Maximum Drawdown, Maximum
Position Size) are the most fully real of any profile in this list —
everything else in a real Prop Firm Rule Profile (Trailing Drawdown,
Consistency Rules, Scaling Milestones, Leverage Rules, Challenge
Deadlines) remains unbuilt per Chapter 70's own addendum research.

## Rule Categories

Covered in full under Ownership above — five of fourteen real
individually, none organized into a named, toggleable category system.

## Custom Rule Builder

**Checked against each of the brief's own six examples individually,
since "no code changes" claims are exactly the kind of thing this
Design Bible's own conventions require verifying rather than assuming:**

- "Never risk more than 1%" — the underlying number (`riskPerTradePct`)
  is real and CEO-editable today, but only as a fixed schema field, not
  free-form rule text a CEO could type.
- "Never trade after 2:00 PM" / "No trades on Fridays" — both require
  the Weekday-Aware Time System Chapter 70's addendum already confirmed
  doesn't exist (`TimeState` has no hour-gating or weekday concept to
  check against).
- "Maximum three open positions" — the underlying number
  (`maxOpenPositions`) is real and CEO-editable today, same shape as
  the 1%-risk example above.
- "Only trade when market volatility is below a defined threshold" —
  Chapter 65's real market regime read includes a `high_volatility`/
  `low_volatility` state, but it's never wired as a configurable,
  trade-blocking threshold anywhere.
- "Require AI confidence above 92%" — confidence is a real field on
  every `TradeDecision`, and the Trade Gatekeeper already checks it as
  one of its eight hardcoded checks (Chapter 58) — but the specific
  threshold isn't CEO-configurable as an arbitrary rule; it's a fixed
  constant in code today.

**The honest summary:** three of six examples reference numbers that
are already real, CEO-editable `RiskLimits` fields (just not
free-form-rule-shaped); three reference infrastructure (weekday
awareness, a volatility-threshold hook, a configurable confidence
threshold) that doesn't exist in any form. Building a genuine
"CEO writes a rule, no code change needed" system is real, new work in
every case — even the three real-number examples would need a rule
parser/interpreter layer that doesn't exist today, since editing a
`RiskLimits` field via the API is not the same thing as parsing
free-form rule text.

## Security

No new surface — inherits Chapters 68/69/70's identical finding: no
credential or per-account permission model exists yet for a Rule
Profile to need isolating between accounts.

## Reports

**Not built.** No named IRE-specific report exists. The real
per-check `RiskWarning` history remains the closest live analog, same
as every other chapter in this volume.

## KPIs

**Not honestly computable, for a Rule Compliance Score or Rule
Violation Rate across profiles** — no Rule Profile exists yet to score
compliance against, and only one account's worth of real risk-check
history exists to measure from. Reporting either today would fabricate
a cross-account measurement this system has no foundation for, the
same trap named explicitly in Chapter 70's own KPIs section.

## Learning System

**Not built**, for the same reason as every other chapter in this
volume: no Rule Profile or cross-account violation history exists yet
to learn from.

## Dependencies

Chapters 68 (Broker Management System), 69 (Multi-Account & Fund
Management — the account model Rule Profiles attach to), and 70 (the
Prop Firm Rule Profile, the only fully-specified profile so far). All
previous Design Bible chapters, per the same honest framing Chapters
66/68/69/70 already use correctly.

## Future Expansion

Rule Packs distributed or shared across CEOs, machine-learned rule
suggestions, and natural-language rule authoring beyond a fixed DSL all
require the base Custom Rule Builder this chapter itself confirms
doesn't exist yet. Matches this volume's own Future Expansion precedent
exactly — not invented or stubbed here.

## Design Bible Integration

**Would integrate with, once real:** every chapter that currently
enforces its own hardcoded check (57/58/66) would migrate that check
into a Rule Profile rather than duplicate it — a real, non-trivial
refactor of already-working code, not a greenfield addition layered on
top. Company Memory would record every real rule violation exactly the
way it already records other risk events today.

## Company Principle

"Accounts define rules. The Institutional Rule Engine enforces them."
This is a real, specific architectural commitment this codebase has
not made — today, the code that defines a rule and the code that
enforces it are the same function, which is precisely what has made
every existing risk check simple to audit. Splitting definition from
enforcement is the right long-term direction for a multi-account,
multi-profile future, and it must be built without losing the
transparency that hardcoding has given every real check so far — the
one non-negotiable constraint on any future implementation of this
chapter.

## Implementation Notes

**What's real today, found by direct research before this chapter was
written, not assumed:** five of fourteen Rule Categories are already
real, individually, as hardcoded checks (Capital, Risk, Drawdown,
Position, and — singularly — Automation via Operating Mode); the
brief's own Rule Execution Order is real for its first two stages
(AI Decision, Risk Authority) and its last stage (Order Execution),
with the middle two (IRE, Broker Management System) both genuinely
unbuilt; every real check already blocks unconditionally and explains
why, and is already recorded into Company Memory — three of the
brief's own four required behaviors on a rule failure are real today,
only "suggest corrective actions" is missing. Grep-confirmed: no
`Rule`/`RuleProfile`/`RuleEngine` class exists anywhere in
`backend/app/`. **What's genuinely, entirely unbuilt:** the centralized
engine itself, any Rule Profile concept, the Custom Rule Builder (checked
against all six of the brief's own examples individually — three
reference already-real numbers with no rule-authoring surface around
them, three reference infrastructure that doesn't exist at all), and
every KPI/report that depends on cross-account or cross-profile data
that doesn't exist yet. No code was written against this chapter.
Gated by the same [Live Trading Gate](../../appendices/appendix-g-permanent-development-policy.md)
Chapters 68/69/70 are gated by.
