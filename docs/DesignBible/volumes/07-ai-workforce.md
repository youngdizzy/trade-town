# Volume 7 — AI Workforce

**Status:** Outline. Not yet written. See [the master Table of
Contents](../../README.md).

## What this volume will cover

- Employees
- Departments
- Academy
- Training
- Mentor Library
- Certifications
- Graduations
- Performance Reviews
- Psychology
- Knowledge Sharing
- Learning Systems
- Career Progression
- Hiring
- Retirement

## Where the real content lives today

- `backend/app/agents.py` — Employees (14 real agent profiles today:
  Scout, Atlas, Echo, Nova, Scribe, Coach, Sentinel, Pulse, Guardian,
  Meridian, Sage, Keystone, Compass, Vector).
- `backend/app/academy.py` / `backend/app/academy_research.py` — Academy,
  Training, Knowledge Sharing, Career Progression (real per-agent
  Knowledge Points and tiers).
- `backend/app/foundational_mentors.py` — Mentor Library, Certifications,
  Graduations.
- `backend/app/coach.py` — Performance Reviews.
- `backend/app/founders.py` — Retirement, real but narrow: Keystone and
  Compass's `FounderState.retired` flips permanently to True (Legendary
  Status) once company health sustains an "excellent" tier — a one-way
  transition, never reversed, and does not remove the founder from the
  roster.
- **Psychology and Hiring** have no real mechanic in this codebase today
  (the 14-agent roster is fixed; no agent is ever hired at runtime, and
  no agent has emotional/psychological state) — this volume should
  document that as a real, current gap, not imply it exists. Retirement
  beyond the two founders (an ordinary employee retiring) is likewise not
  built.

## Addendum — The Quant Organization (Quantitative Research & Intelligence System, Piece 1)

**Status:** Real, docs-only. No code changed by this piece — every role
named below was already doing this work under its existing name; this
addendum only makes the organizational structure explicit and
discoverable in one place. Per the CEO's own explicit instruction: *"Do
NOT rename an agent simply to make the organization look more
quantitative. Improve its actual capabilities."* Nothing here renames
`app/agents.py`'s `AgentProfile.name`/`.occupation` fields, adds a new
agent, or changes any agent's real behavior.

TradeTown's quant work is split across three real, independent
functions — the same separation Piece 4's Model Validator (see Chapter
62's own addendum) depends on and preserves:

**Chief Quant — Vector** (`agentId: "quant"`, occupation "Chief
Quantitative Strategist," `app/agents.py`). Leads every real Black Box
Research Project (`app/black_box.py`) and is the `"quant"` reviewer seat
on every `StrategyReview` (`app/sandbox.py`'s `_quant_verdict`) —
statistical-soundness research and strategy discovery, never risk
sign-off and never independent validation authority over its own work.

**Risk Quant — Sentinel, Guardian, and Keystone together**, a real
three-tier structure, not one seat wearing three names:
- **Sentinel** (`agentId: "sentinel"`, occupation "Risk Management") —
  the hard, per-trade gate: position size, open-position count, and
  portfolio drawdown (`app/risk_engine.py`'s `evaluate_sentinel_risk`).
  A failing check becomes a real `RiskWarning` that drives Sentinel's
  own analyst vote to "wait" and, if the CEO tries to force the trade
  anyway, fails `app/gatekeeper.py`'s `_risk_manager_check` — see
  `app/risk_engine.py`'s own module docstring.
- **Guardian** (`agentId: "guardian"`, occupation "Portfolio
  Protection") — the softer, per-trade concentration/exposure monitor:
  is this symbol or sector already a large share of the book
  (`evaluate_guardian_exposure`), the same shape as Sentinel's check but
  framed as "should we be worried" rather than "can this happen at
  all."
- **Keystone** (`agentId: "keystone"`, occupation "Chief Risk
  Architect") — the strategic, governance-level tier: a Founder board
  seat (`FILLED_BOARD_SEAT_AGENT_IDS` in `app/board.py`) whose real
  domain is Risk Management/Capital Preservation/Position Sizing at the
  Constitution-amendment level (`app/constitution.py`'s
  `FOUNDER_DOMAIN_KEYWORDS`) and Academy mentorship (`app/founders.py`),
  not a per-trade check — the company's risk conscience above the two
  tactical gates, not a third copy of them.

**Model Validator — Meridian (CIO)**, documented in full in
`docs/DesignBible/volumes/09-departments/chapter-62-innovation-lab-continuous-improvement.md`'s
own Piece 4 addendum — independent statistical validation of a
strategy before Company Review, organizationally separate from both the
research above and the risk tiers above it.

This is the real three-way separation the CEO's spec asked for: Vector
researches, Sentinel/Guardian/Keystone manage risk at their respective
tiers, and Meridian validates — cooperating without collapsing into one
general-purpose "Quant AI." **Quant Developer** and **Execution Quant**
(the spec's remaining two named roles) have no real seat in this
codebase yet and are tracked as separate, deferred future pieces (7 and
5 respectively) — not claimed here.
