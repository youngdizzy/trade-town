"""CEO directive "Professional Trading Firm Transformation" — Post-Trade
Review, Exit Efficiency.

RESEARCH FIRST (per the directive's own mandatory rule): `PaperTrade.maePct`/
`mfePct` (CEO Company Health + Live Market Realism directive, Feature 24)
already carry a real, live-computed watermark of the worst/best paper
P&L% a closed position ever saw (see `app/portfolio.py`'s
`mark_to_market()`) — never a retroactive reconstruction from historical
candles. A full audit of the existing Post-Trade Review stack
(`app/discipline.py`'s outcome-blind PROCESS score,
`app/mistakes.py`/`app/successes.py`'s CaseStudy filing,
`app/failure_review.py`'s WHY-the-thesis-failed `FailureReason`
taxonomy) found that none of them ever reads this real data. This
module closes that gap — and only that gap: a genuinely new, third
review axis (HOW WELL WAS THE EXIT MANAGED) computed fresh over
`state.paper_portfolio.trade_history`, the same original CAGS
convention (no new `GameSaveState` field). It does not read, write, or
duplicate Discipline's score or `failure_review.py`'s classification —
those stay completely untouched.

THE METRIC: `capture_pct = (pnl_pct - mae_pct) / (mfe_pct - mae_pct) * 100`
— a real, continuous, professionally-recognized read (sometimes called
an "Edge Ratio" or "trade efficiency ratio"): where, within this one
trade's own real observed high-low range, it actually closed. 100 means
it closed at the best point the trade ever reached; 0 means it closed
at the worst point; 50 means squarely in the middle. This single
formula honestly covers BOTH wins and losses — a losing trade that
recovered most of the way back from its own worst drawdown before
closing reads a real, meaningful `capturePct` exactly like a winning
trade that gave back most of its peak gain does, with no separate
win/loss branch needed.

THE HONESTY BOUNDARY: `maePct`/`mfePct` both default to `0.0` (see their
own schema docstrings — a trade closed before this watermark existed,
or one closed before a single mark-to-market tick ever ran, both read
identically). `mfePct - maePct == 0.0` is therefore genuinely ambiguous
between "this trade never really moved" and "no real watermark was ever
tracked" — this module reports `not_enough_data` rather than guessing
either way, never a fabricated 50%.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.schemas import (
    ExitEfficiencySummary,
    ExitEfficiencyState,
    PaperTrade,
    TradeExitEfficiency,
)

_EFFICIENT_THRESHOLD_PCT = 70.0
_POOR_THRESHOLD_PCT = 30.0


def _evidence_state(capture_pct: float | None) -> ExitEfficiencyState:
    if capture_pct is None:
        return "not_enough_data"
    if capture_pct >= _EFFICIENT_THRESHOLD_PCT:
        return "efficient_exit"
    if capture_pct < _POOR_THRESHOLD_PCT:
        return "poor_exit"
    return "average_exit"


def compute_exit_efficiency(trade_history: list[PaperTrade]) -> ExitEfficiencySummary:
    reads: list[TradeExitEfficiency] = []
    for trade in trade_history:
        trade_range = trade.mfe_pct - trade.mae_pct
        capture_pct = round((trade.pnl_pct - trade.mae_pct) / trade_range * 100.0, 1) if trade_range > 0 else None
        reads.append(
            TradeExitEfficiency(
                tradeId=trade.id,
                symbol=trade.symbol,
                pnlPct=trade.pnl_pct,
                maePct=trade.mae_pct,
                mfePct=trade.mfe_pct,
                capturePct=capture_pct,
                evidenceState=_evidence_state(capture_pct),
                simDay=trade.closed_sim_minutes // 1440,
            )
        )

    captures = [r.capture_pct for r in reads if r.capture_pct is not None]
    avg_capture = round(sum(captures) / len(captures), 1) if captures else None

    return ExitEfficiencySummary(
        reads=reads,
        avgCapturePct=avg_capture,
        efficientExitCount=sum(1 for r in reads if r.state == "efficient_exit"),
        averageExitCount=sum(1 for r in reads if r.state == "average_exit"),
        poorExitCount=sum(1 for r in reads if r.state == "poor_exit"),
        notEnoughDataCount=sum(1 for r in reads if r.state == "not_enough_data"),
        updatedAt=datetime.now(timezone.utc).isoformat(),
    )
