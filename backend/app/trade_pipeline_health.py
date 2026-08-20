"""app/trade_pipeline_health.py — CEO directive "Professional Quant Firm
Phase 41-45," Critical Task #0's own explicitly-requested trade-flow
diagnostic ("ADD A TRADE-PIPELINE HEALTH CHECK... distinguish 'no valid
trade existed' from 'a valid trade existed but the system failed to
execute it'").

RESEARCH FIRST. A real, empirical forensic audit of this codebase's own
live save file (see app/opportunity_gatekeeper.py's module docstring for
the full write-up) found the trade-decision pipeline working exactly as
designed at every stage traced — no exception, no silent state-machine
failure, no order created-but-never-filled. The near-total absence of
real trades in that save (31 sim-days, 47 resolved decisions, only 2
real trades) is the real, honest, INTENTIONAL consequence of two real
design decisions working together: (1) `app/opportunity_gatekeeper.py`'s
own `min_trade_quality_score` gate rejecting the vast majority of
candidates before they ever become a CEO-facing proposal, and (2)
`GameSaveState.settings.operating_mode` defaulting to `"learning"`,
which requires an explicit CEO/player decision on every proposal that
DOES clear that gate. This module makes that real, honest state
observable on demand — it computes NO new backtest math, adds NO new
rejection logic, and changes NO existing gate's behavior. It is purely a
read: a funnel count over data this codebase's own pipeline (app/
nexus.py) already persists.

DIAGNOSTIC ONLY, NEVER A SCORE. Nothing here feeds `app/company_score.py`
or any other scoring system, and nothing here was tuned to make any
number look any particular way — per the directive's own explicit "Do
NOT change the scoring system merely to make these numbers look good."

HONESTY BOUNDARY — several of the lists this reads are real, capped,
ROTATING windows, not full-session-lifetime counters:
  - `research` retains each researcher's own last `MAX_RESEARCH_
    HISTORY_PER_AGENT` (24) completed items alongside its current
    in-progress one (app/research.py) — "completedResearchSignals"
    below is that retained sample, not a lifetime total.
  - `decisions` is capped at `MAX_DECISIONS` (200, app/nexus.py).
  - `opportunity_rejections` is capped at `MAX_OPPORTUNITY_REJECTIONS`
    (100, app/nexus.py).
  - `gatekeeper_rejections` is capped at `MAX_GATEKEEPER_REJECTIONS`
    (100, app/nexus.py).
A session older than these caps has real history that fell off the
front of each list — this module reports what is honestly still
retained, never a fabricated full-history estimate.

WHAT THIS MODULE DOES NOT (YET) COVER, DISCLOSED RATHER THAN GUESSED:
`app/nexus.py`'s `_generate_trade_proposals()` has its own real, earlier
skip conditions (research confidence below `FUTURE_TRADE_CONFIDENCE_
THRESHOLD`, a duplicate pending symbol, `MAX_PENDING_PROPOSALS` reached,
missing/invalid price, a zero-sized recommended quantity) that produce
NO persisted record at all today — a real candidate skipped there simply
never becomes anything this module (or any other part of this codebase)
can count after the fact. This is a real, disclosed architectural gap,
not fabricated as "0 occurrences" — see `data_honesty_note`.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

from app.schemas import GameSaveState, NoTradeReasonCodeTally, TradePipelineHealthSnapshot


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def compute_trade_pipeline_health(state: GameSaveState) -> TradePipelineHealthSnapshot:
    """The one real entry point. Pure read over already-persisted real
    state — see this module's own docstring for the exact honesty
    boundary on each count below."""
    completed_research_signals = sum(1 for item in state.research if item.status == "completed")
    pending_proposals = len(state.trade_proposals)
    resolved_decisions = len(state.decisions)
    trades_executed = sum(1 for d in state.decisions if d.outcome == "trade")
    no_trade_decisions = sum(1 for d in state.decisions if d.outcome == "no_trade")

    code_counter: Counter[str] = Counter()
    for opportunity_rejection in state.opportunity_rejections:
        code_counter.update(opportunity_rejection.reason_codes)
    for gatekeeper_rejection in state.gatekeeper_rejections:
        code_counter.update(gatekeeper_rejection.reason_codes)
    reason_code_breakdown = [NoTradeReasonCodeTally(code=code, count=count) for code, count in sorted(code_counter.items(), key=lambda pair: (-pair[1], pair[0]))]  # type: ignore[arg-type]

    return TradePipelineHealthSnapshot(
        completedResearchSignals=completed_research_signals,
        pendingProposals=pending_proposals,
        resolvedDecisions=resolved_decisions,
        tradesExecuted=trades_executed,
        noTradeDecisions=no_trade_decisions,
        opportunityRejections=len(state.opportunity_rejections),
        gatekeeperRejections=len(state.gatekeeper_rejections),
        reasonCodeBreakdown=reason_code_breakdown,
        dataHonestyNote=(
            "completedResearchSignals/resolvedDecisions/opportunityRejections/gatekeeperRejections are real, "
            "capped, ROTATING windows (24-per-agent/200/100/100 respectively) — what this session's own real "
            "pipeline currently retains, never a fabricated full-lifetime total. This snapshot cannot see candidates "
            "app/nexus.py's own pre-proposal skip conditions (stale research confidence, a duplicate pending symbol, "
            "the pending-proposal cap, missing price data, a zero-sized recommended quantity) discarded before ever "
            "becoming a real, persisted record — a real, disclosed architectural gap, not counted as zero."
        ),
        generatedAt=_now_iso(),
    )
