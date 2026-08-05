# Appendix C — Naming Standards

**Status:** Outline. Not yet written. See [the master Table of
Contents](../README.md).

## What this appendix will cover

- Departments
- Classes
- Files
- Variables
- Components
- Database Tables
- APIs
- Functions

## Where the real convention lives today

The real, already-followed conventions this appendix should transcribe
(not invent):

- Backend: `snake_case` modules and functions, `PascalCase` Pydantic
  models, one feature per module (`war_room.py`, `portfolio_intelligence.py`,
  `decision_vault.py`) rather than one giant file.
- Schemas: every model extends `CamelModel` (`backend/app/schemas.py`) so
  Python stays `snake_case` while the wire format is `camelCase` —
  `frontend/src/types.ts` mirrors the wire format exactly, field for
  field.
- Frontend: `PascalCase` components (`WarRoomPanel.tsx`), one file per
  Command Center panel under `frontend/src/ui/components/CommandCenter/panels/`.
- Feature numbering: sequential, permanent once assigned — when two
  briefs collide on the same number (as Features 53/54 and 54/55/56 did),
  the renumbering and the reason are documented in the module docstring,
  the commit message, and `CHANGELOG.md`, never silently overwritten. See
  `docs/CODING_STANDARDS.md` for the fuller version of this convention.
