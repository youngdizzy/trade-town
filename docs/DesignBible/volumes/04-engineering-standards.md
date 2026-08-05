# Volume 4 — Engineering Standards

**Status:** Outline. Not yet written. See [the master Table of
Contents](../../README.md).

## What this volume will cover

- Code Architecture
- Folder Structure
- Naming Conventions
- Documentation Standards
- Logging Standards
- Testing Standards
- Error Handling
- State Management
- Performance Standards
- Scalability Standards
- Security Standards
- Maintainability Standards
- Code Review Standards
- Refactoring Standards

## Where the real content lives today

Most of this volume already exists as real, followed practice — it needs
consolidating here, not inventing:

- `docs/PROJECT_STRUCTURE.md` / `docs/FolderStructure.md` — Folder
  Structure.
- `docs/CODING_STANDARDS.md` — Naming Conventions, Documentation
  Standards, Error Handling.
- `docs/DEVELOPMENT_RULES.md` — the project's actual engineering
  discipline (research overlap first, scope honestly, backend before
  frontend, verify thoroughly).
- `backend/app/save_modules.py`'s module-map validation and
  `backend/tests/` — Testing Standards and State Management, both
  enforced by real code (`_validate_module_map()`), not just documented.
