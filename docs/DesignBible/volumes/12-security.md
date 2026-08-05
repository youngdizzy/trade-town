# Volume 12 — Security

**Status:** Outline. Not yet written. See [the master Table of
Contents](../../README.md).

## What this volume will cover

- Authentication
- Authorization
- Secrets Management
- Encryption
- Audit Logs
- API Security
- Rate Limiting
- Disaster Recovery
- Backup Strategy

## Where the real content lives today

- `docs/ARCHITECTURE_REVIEW.md` — the existing security-posture review,
  including its own note that authentication/authorization is
  deliberately out of scope pre-real-money (see its "shape of security
  model" recommendation, revisit at the real-money milestone).
- `backend/.env.example` — the current secrets-management convention
  (environment variables, never committed values).
- `backend/app/persistence.py` — the closest real analogue to Backup
  Strategy / Disaster Recovery today: real save migration
  (`_migrate_dict()`) that attempts recovery before ever discarding a
  save, and a raw-payload backup on unrecoverable failure.
- **There is no user authentication, no API authorization, no encryption
  at rest, no audit log, and no rate limiting anywhere in this codebase
  today** — this is a single-player, local/self-hosted simulation with
  no real-money or multi-tenant surface yet. This volume's honest job,
  until real brokerage integration is scoped (Volume 10), is to say so
  plainly rather than describe security controls that don't exist.
