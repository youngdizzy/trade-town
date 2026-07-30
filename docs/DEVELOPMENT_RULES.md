# TradeTown Development Rules (v0.9)

**Status:** Canonical and binding. This document defines how every future
feature must be designed and implemented in TradeTown. It applies to
every update from this point forward. Where any other document, spec, or
request creates ambiguity about how to build something, **these rules
take priority.**

This doc sits alongside the other canonical references in `docs/` —
[`Architecture.md`](Architecture.md) (what's actually built),
[`CODING_STANDARDS.md`](CODING_STANDARDS.md) (how code is written),
[`AI_AGENT_BIBLE.md`](AI_AGENT_BIBLE.md) / [`COMPANY_LORE.md`](COMPANY_LORE.md)
(who the employees are), [`UI_UX_BIBLE.md`](UI_UX_BIBLE.md) /
[`DESIGN_BIBLE.md`](DESIGN_BIBLE.md) (how it looks and feels) — but this
one is the constitution: it governs *what gets built and why*, not just
how.

---

## Core Vision

TradeTown is **not just a game.**

TradeTown is a living AI trading company inside a game world.

Every feature should strengthen the company. Every feature should improve:

- Intelligence
- Decision Making
- Research
- Discipline
- Knowledge
- Long-Term Growth
- Company Culture

Never add systems that exist only to create busywork.

## Elite Intelligence Objective

The primary objective of v0.9 is to build the smartest autonomous
trading company possible **before risking real capital.**

Every feature should improve one or more of the following:

- Reasoning
- Critical Thinking
- Research Ability
- Pattern Recognition
- Market Understanding
- Decision Quality
- Statistical Thinking
- Risk Management
- Trading Psychology
- Adaptability
- Communication
- Long-Term Learning

The company should continuously become more intelligent.

**Intelligence is the primary progression system.**

**Money is the result of intelligence — not the goal itself.**

When scoping a new feature under this doc's Implementation Style
structure, its GOAL should name which of the twelve categories above it
serves; if it doesn't clearly serve at least one, reconsider whether it
belongs in v0.9 at all (see "Never add systems that exist only to create
busywork," above).

## Long Term Thinking

Every feature should still make sense after 100 days, 1,000 days, and
10,000 days of play. Avoid systems that become useless after early
progression. Always think long-term.

## Company Over Player

The player is TradeTown's CEO. The employees do the work.

Employees research, study, train, debate, backtest, journal, and
improve. **The CEO manages. The CEO should rarely perform employee
tasks.**

## Autonomous Employees

Employees should think independently. Employees should:

- Discover ideas
- Ask questions
- Challenge assumptions
- Suggest improvements
- Debate strategies
- Request research
- Teach each other
- Warn about risk
- Notice opportunities

The company should feel alive without constant player input.

## Every Building Needs a Purpose

Buildings should never exist only for decoration. Every building must
perform a meaningful company function. Examples:

| Building | Function |
|---|---|
| Academy | Education |
| Brain Room | Decision Making |
| Research Lab | Research |
| Treasury | Capital Management |
| Gym | Energy |
| Cafe | Team Discussions |
| Employee House | Rest |
| Reflection Chamber | Learning |
| Innovation Lab | Experimentation |

## Real Progression

Avoid fake progression. Never increase numbers simply for the sake of
progression. Instead improve:

- Research Quality
- Decision Quality
- Trading Quality
- Communication
- Knowledge
- Leadership
- Innovation
- Company Efficiency

Everything should have meaningful effects.

## Permanent Company Memory

Knowledge should never disappear. The company remembers strategies,
mistakes, discoveries, mentors, constitution changes, founder lessons,
research, breakthroughs, and company history. **Knowledge compounds
forever.**

## Unique Personalities

Every employee should become unique. Examples: the Quant uses statistics;
the Researcher loves learning; the Risk Specialist protects capital; the
Coach develops employees; a Founder thinks long-term. No two employees
should feel identical.

## Evidence First

No idea becomes company knowledge without validation. Every idea follows
this pipeline:

```
Learn → Discuss → Backtest → Paper Trade → Sandbox Test
      → Quant Review → Risk Review → Founder Council → Company Adoption
```

Evidence comes before opinion.

## Modular Design

Every system should be modular. Avoid hardcoding whenever possible.
Future features should integrate without rewrites. Systems should be
expandable.

## Performance

Design every feature for scalability. The game should remain smooth with
hundreds of employees, thousands of trades, thousands of research
records, large knowledge archives, many buildings, and many historical
events.

## No Placeholder Systems

Never implement placeholder mechanics simply to satisfy a feature
request. If a system is introduced, it should have meaningful gameplay,
integrate with existing systems, and be designed with future expansion
in mind. Avoid temporary solutions that will require complete rewrites
later. Whenever possible, build production-quality systems from the
beginning while keeping the architecture modular and extensible.

## Foundational Principle

Whenever multiple implementation choices exist, always choose the
solution that creates:

- Greater realism
- Greater scalability
- Greater autonomy
- Greater intelligence
- Greater long-term depth

## UI Philosophy

The UI should always answer: **"What does the CEO need to know?"**

- Avoid unnecessary clicks.
- Avoid overwhelming menus.
- Prioritize clarity.
- Dashboards should summarize information first.
- Detailed information appears only when selected.

## Implementation Style

Every future feature request should be interpreted using this structure:

1. **GOAL**
2. **REQUIREMENTS**
3. **SYSTEM BEHAVIOR**
4. **PLAYER ACTIONS**
5. **EMPLOYEE ACTIONS**
6. **UI**
7. **RULES**
8. **DO NOT**
9. **SUCCESS CRITERIA**

Claude should follow this structure whenever implementing new systems —
scope each new feature against these nine headings before writing code,
and check the result against them (plus every rule above) before calling
it done.

This structure works alongside, not instead of, this repo's own
established engineering discipline: research existing overlap before
building, scope an honest subset and document every cut explicitly
(never fabricate data or metrics that have no real backing signal),
implement backend before frontend and commit the backend first to limit
exposure to session data loss, verify thoroughly (`mypy`/`ruff`/`pytest`
backend; `tsc`/`eslint`/build frontend; Playwright regression against the
live stack), then update `CHANGELOG.md` / `docs/Architecture.md` /
`docs/API.md` before committing and pushing.

## Final Philosophy

TradeTown should eventually feel less like a game and more like running
a real hedge fund filled with intelligent autonomous employees. Every
feature should move the company closer to becoming a self-improving
organization whose greatest competitive advantage is its ability to
learn faster than everyone else.

The ultimate goal is not to build the biggest company.

**The ultimate goal is to build the smartest company.**
