#!/usr/bin/env python3
"""Script-seeded external-agent read approval (v0).

TradeTown Read-Only MCP Boundary 1.0 approves records for external-agent
reading with an explicit, auditable, fail-closed flag. Nothing inside the MCP
boundary can set it — approval is authored TradeTown-side only, and in v0 that
means this script.

WHY A SCRIPT AND NOT A UI ACTION. A CEO-facing approval action is a real
feature with its own design surface (who approves, what the player sees, how
it is revoked). Building it was not in scope for this milestone, and inventing
a half-version of it would be exactly the "placeholder system" this repo's
DEVELOPMENT_RULES.md forbids. The script is the honest minimum: explicit,
reviewable, and recorded on the record itself.

WHAT IT DOES. Sets, on records you name explicitly:

    approvedForAgentRead              = true
    approvedForAgentReadAt            = now (ISO-8601 UTC)
    approvedForAgentReadAtSimMinutes  = the save's current simulated minute
    approvedForAgentReadBy            = the operator string you pass

It never approves by wildcard, never approves everything, and prints exactly
what it changed. Run with --dry-run first.

USAGE
    python scripts/seed_agent_read_approval.py --dry-run --by ceo \
        --research-id r-123 --memory-id im-456
    python scripts/seed_agent_read_approval.py --by ceo --research-id r-123

Run it from the repository root with the backend stopped, or accept that the
running simulation may overwrite the save on its next persist tick.
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.persistence import load_state, persist_modules  # noqa: E402
from app.portfolio import sim_minutes  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Approve TradeTown records for external-agent reading.")
    parser.add_argument("--by", required=True, help="Operator identifier recorded on each approval.")
    parser.add_argument("--research-id", action="append", default=[], help="ResearchItem id (repeatable).")
    parser.add_argument("--memory-id", action="append", default=[], help="InstitutionalMemoryEntry id (repeatable).")
    parser.add_argument("--dry-run", action="store_true", help="Report what would change; write nothing.")
    args = parser.parse_args()

    if not args.research_id and not args.memory_id:
        parser.error("nothing to approve: pass at least one --research-id or --memory-id")

    state = load_state()
    if state is None:
        print("No save found. Nothing to approve.", file=sys.stderr)
        return 1

    now_iso = datetime.now(timezone.utc).isoformat()
    now_sim = sim_minutes(state.time)
    changed: list[str] = []
    missing: list[str] = []

    wanted_research = set(args.research_id)
    for item in state.research:
        if item.id in wanted_research:
            wanted_research.discard(item.id)
            if item.approved_for_agent_read:
                print(f"  research {item.id}: already approved, unchanged")
                continue
            if not args.dry_run:
                item.approved_for_agent_read = True
                item.approved_for_agent_read_at = now_iso
                item.approved_for_agent_read_at_sim_minutes = now_sim
                item.approved_for_agent_read_by = args.by
            changed.append(f"research {item.id} ({item.title!r})")
    missing.extend(f"research {rid}" for rid in sorted(wanted_research))

    wanted_memory = set(args.memory_id)
    for entry in state.institutional_memory:
        if entry.id in wanted_memory:
            wanted_memory.discard(entry.id)
            if entry.approved_for_agent_read:
                print(f"  memory {entry.id}: already approved, unchanged")
                continue
            if not args.dry_run:
                entry.approved_for_agent_read = True
                entry.approved_for_agent_read_at = now_iso
                entry.approved_for_agent_read_at_sim_minutes = now_sim
                entry.approved_for_agent_read_by = args.by
            changed.append(f"memory {entry.id} ({entry.source})")
    missing.extend(f"memory {mid}" for mid in sorted(wanted_memory))

    for line in changed:
        print(f"  {'WOULD APPROVE' if args.dry_run else 'APPROVED'}: {line}")
    for line in missing:
        print(f"  NOT FOUND: {line}", file=sys.stderr)

    if args.dry_run:
        print(f"\nDry run. {len(changed)} record(s) would change; nothing written.")
        return 1 if missing else 0

    if changed:
        persist_modules(state)
        print(f"\nPersisted. {len(changed)} record(s) approved at sim-minute {now_sim} by {args.by!r}.")
    else:
        print("\nNothing changed; nothing written.")
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
