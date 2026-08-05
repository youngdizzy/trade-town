# Volume 3 — Company Architecture

**Status:** Outline. Not yet written. See [the master Table of
Contents](../../README.md).

## What this volume will cover

- Organization Chart
- Department Hierarchy
- Information Flow
- Decision Flow
- Approval Flow
- Communication Flow
- Risk Flow
- Learning Flow
- Company Operating Model

**Governing rule:** every department must have exactly one
responsibility. No overlapping ownership. This volume is where that rule
gets checked against reality — the Decision Authority Matrix (Appendix
E) is the enforceable, tabular version of the same rule.

## Where the real content lives today

- `backend/app/agents.py` — the real roster (14 agents) and their
  `occupation` fields, the closest thing to an org chart today.
- `backend/app/nexus.py` — the real tick loop is the closest thing to a
  literal information/decision/approval flow diagram; every step in this
  volume's flows should trace to a real block of that function, not an
  invented sequence.
- `backend/app/gatekeeper.py`, `backend/app/executive_intelligence.py` —
  the real approval flow (Gatekeeper) and the real cross-department
  synthesis (Executive Intelligence Network).
