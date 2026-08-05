# TradeTown Design Bible

**Status:** Canonical, permanent, living. Beginning with this document,
TradeTown operates from a single Design Bible — one source of truth for
every department, every AI employee, every workflow, every trading
system, every broker integration, every company law, every philosophy,
every feature, and every future decision. **The code follows the Design
Bible. The Design Bible never follows the code.**

This document is the Table of Contents and the entry point. It should
read like the internal operating manual of a world-class AI-powered
quantitative hedge fund — not a game design document, not scattered
feature notes. A new engineer should be able to read only the Design
Bible and understand how every part of the company functions.

## How this is built

The Design Bible is built **one volume at a time**, not all at once. This
document and the folder structure below exist now; the volumes and
appendices are filled in incrementally as each is written, and every new
feature going forward is added as a new chapter under the appropriate
volume — never as a standalone, disconnected write-up. The status column
below tracks what's real today versus what's still an outline waiting to
be written.

**Permanent development policy** (see Appendix G once written): every
future feature must (1) determine its correct Design Bible chapter, (2)
follow Company Law and Company Philosophy, (3) avoid duplicate systems
and overlapping responsibilities, and (4) have the Design Bible updated
**before** implementation begins — not after.

## Relationship to existing docs

TradeTown already has a real, working set of documentation
(`docs/DESIGN_BIBLE.md`, `docs/AI_AGENT_BIBLE.md`, `docs/UI_UX_BIBLE.md`,
`docs/NEXUS_ARCHITECTURE.md`, `docs/Architecture.md`,
`docs/DEVELOPMENT_RULES.md`, and others). None of that is being deleted
or invalidated by this initiative. As each Design Bible volume is
actually written, it absorbs and supersedes the overlapping parts of
those documents (for example, Volume 1 will eventually incorporate
`docs/DESIGN_BIBLE.md`'s pillars, Volume 6 will incorporate the trading
philosophy scattered across `CHANGELOG.md`/`docs/Architecture.md`, and so
on) — one deliberate migration per volume, not a wholesale rewrite done
in a single pass. Until a volume says otherwise, the existing document it
will eventually absorb remains the real, current reference.

---

## Table of Contents

| Volume | Title | Status |
|---|---|---|
| 1 | [Company Foundation](volumes/01-company-foundation.md) | Outline |
| 2 | [Company Laws](volumes/02-company-laws.md) | Outline |
| 3 | [Company Architecture](volumes/03-company-architecture.md) | Outline |
| 4 | [Engineering Standards](volumes/04-engineering-standards.md) | Outline |
| 5 | [UI / UX Design System](volumes/05-ui-ux-design-system.md) | Outline |
| 6 | [Trading Operating System](volumes/06-trading-operating-system.md) | Outline |
| 7 | [AI Workforce](volumes/07-ai-workforce.md) | Outline |
| 8 | [Research Division](volumes/08-research-division.md) | Outline |
| 9 | [Departments](volumes/09-departments/README.md) | Outline — chapter template defined |
| 10 | [Broker & Live Trading](volumes/10-broker-live-trading.md) | Outline |
| 11 | [Testing & Quality Assurance](volumes/11-testing-quality-assurance.md) | Outline |
| 12 | [Security](volumes/12-security.md) | Outline |
| 13 | [Audits](volumes/13-audits.md) | Outline |
| 14 | [Roadmap](volumes/14-roadmap.md) | Outline |

| Appendix | Title | Status |
|---|---|---|
| A | [Glossary](appendices/appendix-a-glossary.md) | Outline |
| B | [Data Dictionary](appendices/appendix-b-data-dictionary.md) | Outline |
| C | [Naming Standards](appendices/appendix-c-naming-standards.md) | Outline |
| D | [Version History](appendices/appendix-d-version-history.md) | Outline |
| E | [Decision Authority Matrix](appendices/appendix-e-decision-authority-matrix.md) | Outline |
| F | [Performance Targets](appendices/appendix-f-performance-targets.md) | Outline |
| G | [Permanent Development Policy](appendices/appendix-g-permanent-development-policy.md) | Outline |

---

## Architecture principles

These apply across every volume, not just Volume 4:

- Favor simplicity over unnecessary complexity.
- Favor modular systems over tightly coupled systems.
- Favor explainability over cleverness.
- Favor reliability over speed.
- Favor maintainability over shortcuts.
- Favor scalability over temporary solutions.
- Every decision must be explainable.
- Every AI action must be traceable.
- Every workflow must be documented.
- Every department must own exactly one responsibility.

## Final objective

TradeTown should become a complete enterprise operating system for an
AI-powered quantitative hedge fund. From this point forward, every future
feature becomes a new Design Bible chapter rather than a standalone
prompt.
