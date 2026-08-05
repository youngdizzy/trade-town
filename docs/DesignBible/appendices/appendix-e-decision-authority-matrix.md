# Appendix E — Decision Authority Matrix

**Status:** Outline. Not yet written. See [the master Table of
Contents](../README.md).

Defines exactly who owns every decision — CEO, Executive Intelligence,
Market Intelligence, Portfolio Intelligence, Risk Authority, Research
Division, Execution Engine, Broker. No ambiguity. This is the
enforceable, tabular counterpart to Volume 3's Company Architecture and
the "no overlapping ownership" rule every Volume 9 chapter's
Responsibilities section must satisfy.

## Where the real content lives today

The real authority chain already exists in code; this appendix's job is
to make it one explicit table rather than something a reader has to
trace through five files:

- `backend/app/gatekeeper.py` — final veto authority over a trade
  (Risk Authority's real power: it can override the CEO).
- `backend/app/executive_intelligence.py` — synthesizes every
  department's opinion into one recommendation, but the recommendation
  is advisory, not binding — the real final call for an ordinary trade
  stays with the CEO (or, in Assisted/Executive operating mode, with
  `backend/app/nexus.py`'s `is_significant_proposal()` auto-resolution
  rule).
- `backend/app/sandbox.py` — Company Certification's real authority over
  whether a strategy may size up beyond its tested allocation.
- `backend/app/founders.py` — Keystone/Compass's approval authority over
  strategy promotion (`StrategyFounderApproval`).

This appendix should turn each of those real authority relationships into
one row of a single table, not restate them in prose.
