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
