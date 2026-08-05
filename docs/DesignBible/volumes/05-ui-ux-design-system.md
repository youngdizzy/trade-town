# Volume 5 — UI / UX Design System

**Status:** Outline. Not yet written. See [the master Table of
Contents](../../README.md).

## What this volume will cover

- Feature 67
- Command Center
- Navigation Philosophy
- Headquarters
- Markets
- AI Workforce
- Research
- Portfolio
- Operations
- Archive
- Universal Search
- Command Palette
- CEO Dashboard
- 30 Second Rule
- Color System
- Typography
- Spacing
- Cards
- Buttons
- Tables
- Charts
- Animations
- Notifications
- Responsive Design
- Accessibility
- Future Expansion

## Where the real content lives today

- `docs/UI_UX_BIBLE.md` — the existing UX principles document.
- `frontend/src/ui/components/CommandCenter/` — the real Command Center
  (30+ tabs today), including its shared visual primitives
  (`ui.tsx`: `Glass`, `TerminalLabel`, `DataRow`, `StatusPill`, `Meter`,
  `EmptyState`) — the real, current Color System/Cards/Buttons/Tables
  building blocks this volume should document, not redesign.
- **Feature 67** and the reorganized navigation groups (Headquarters /
  Markets / AI Workforce / Research / Portfolio / Operations / Archive,
  Universal Search, Command Palette, the "30 Second Rule") are not yet
  built in this codebase — the current Command Center is a flat tab bar.
  This volume should say so plainly once written, distinguishing the
  real current navigation from the target one.
