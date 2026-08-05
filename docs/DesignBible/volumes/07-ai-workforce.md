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
