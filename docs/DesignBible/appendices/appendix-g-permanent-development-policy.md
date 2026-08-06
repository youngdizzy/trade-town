# Appendix G — Permanent Development Policy

**Status:** Real policy, stated here; full appendix formatting (cross-
references into every volume) still outstanding. See [the master Table
of Contents](../README.md).

Every future feature must, in order:

1. Determine its correct Design Bible chapter (which volume, and if it's
   a department, that it belongs in Volume 9).
2. Follow Company Law (Volume 2, once written) and Company Philosophy
   (Volume 1, once written).
3. Avoid duplicate systems and overlapping responsibilities — checked
   against Appendix E (Decision Authority Matrix) and the relevant
   volume's own "what this owns / doesn't own" section.
4. Have the Design Bible updated **before** implementation begins, not
   after.

This is not a new policy — it formalizes a discipline this codebase has
already followed for every feature slice so far: `docs/DEVELOPMENT_RULES.md`
already states "research overlap first, scope honestly and document
every cut, commit the backend before starting the frontend, verify
thoroughly, document before committing." This appendix's job, once fully
written, is to make that discipline explicitly point at the Design
Bible's own volume structure as the place research and documentation
happen, rather than a general instruction with no fixed destination.

## Applying this policy today

Until every volume above has real content, "determine its correct
chapter" for a department-level feature means: add or update its row in
[Volume 9's chapter table](../volumes/09-departments/README.md), and
write that feature's own chapter using the 20-section template defined
there — the same discipline this policy describes, scoped to what
already exists.

## The Live Trading Gate

A permanent, standing policy, not scoped to any one chapter: the
Institutional Broker Management System ([Chapter
68](../volumes/10-broker-live-trading/chapter-68-institutional-broker-management-system.md))
shall **not** connect to any live brokerage until every one of the
following is true:

1. Chapters 67–75 are completed.
2. Paper trading has been extensively tested.
3. Backtesting is validated.
4. Risk Authority is fully operational.
5. Emergency Stop is verified.
6. Audit Center is operational.
7. The CEO explicitly enables Live Trading Mode.

Live trading is the final deployment stage, not the development stage.
Every chapter written and every system implemented between now and
that gate is real, load-bearing work toward it — proven first against
`app/broker.py`'s simulated engine, per Chapter 68's own architecture —
never a placeholder waiting to be swapped for something real later.
This gate is checked, not assumed: no future session should build
toward a live connector, request broker credentials, or wire a real
execution endpoint without first confirming, explicitly and in writing,
that all seven conditions above hold.
