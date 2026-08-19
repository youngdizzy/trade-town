"""CEO directive "Session Trading Education & Agent Training" —
real SESSION × REGIME evidence over this company's own closed trades.

RESEARCH FIRST (per the directive's own mandatory rule): `app/decision_vault.py`
already stamps a real `session` (`TradingSession`, from
`app/market_intelligence.py`'s `compute_session()`) and a real
`market_regime` (`MarketIntelligenceRegime`) on every `DecisionVaultEntry`
— one per real closed trade — at the moment the trade closes. That is
the only honest substrate this codebase has for asking "does this
company's own trading actually perform differently by session." This
module answers exactly that question, and nothing more: a pure,
computed-fresh-per-request aggregate over `state.decision_vault`, the
same original CAGS convention `app/audit_log.py`/`app/control_effectiveness.py`
already established — no new `GameSaveState` field.

THE HONESTY BOUNDARY, explicit: the CEO directive's own curriculum asks
about "SESSION × REGIME × STRATEGY × SETUP × OUTCOME." `DecisionVaultEntry.strategy_id`
is `None` on every real entry today (that field's own docstring: "no
ordinary Trading Floor trade links back to a specific Strategy object")
and no "setup" taxonomy exists anywhere in this codebase (confirmed by
research — `app/executive.py`'s `TradeProposal` has no setup-type
field). Building a five-axis bucketing over data that doesn't carry two
of those five axes would mean either fabricating a fake setup/strategy
label or silently dropping the honesty this codebase's own conventions
require. This module deliberately ships the real two-axis version
(SESSION × REGIME → OUTCOME) that the data actually supports, and
discloses the STRATEGY/SETUP gap here rather than papering over it —
see this module's own Design Bible entry for the same disclosure in
narrative form.

`MIN_SESSION_REGIME_SAMPLE` is a real, disclosed evidence floor — the
same "a real, arbitrary-but-disclosed number, not a fitted model"
honesty convention Feature 33's `MIN_ACCURACY_SAMPLE_FOR_VERDICT` and
Feature 34's `MIN_CONTROL_SAMPLE_FOR_VERDICT` already established.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.schemas import (
    DecisionVaultEntry,
    MarketIntelligenceRegime,
    SessionRegimeEvidence,
    SessionRegimeEvidenceState,
    SessionRegimeEvidenceSummary,
    TradingSession,
)

MIN_SESSION_REGIME_SAMPLE = 5

_FAVORABLE_THRESHOLD_PCT = 60.0
_UNFAVORABLE_THRESHOLD_PCT = 40.0


def _evidence_state(sample: int, win_rate_pct: float | None) -> SessionRegimeEvidenceState:
    if sample < MIN_SESSION_REGIME_SAMPLE or win_rate_pct is None:
        return "not_enough_evidence"
    if win_rate_pct >= _FAVORABLE_THRESHOLD_PCT:
        return "favorable"
    if win_rate_pct < _UNFAVORABLE_THRESHOLD_PCT:
        return "unfavorable"
    return "mixed"


def compute_session_regime_evidence(vault: list[DecisionVaultEntry]) -> SessionRegimeEvidenceSummary:
    """One `SessionRegimeEvidence` record per (session, regime) pairing
    this company has ever actually closed a real trade under. A pairing
    this company has never seen simply never appears in `buckets` —
    never backfilled with a fabricated zero-evidence row."""
    grouped: dict[tuple[TradingSession, MarketIntelligenceRegime], list[DecisionVaultEntry]] = {}
    for entry in vault:
        grouped.setdefault((entry.session, entry.market_regime), []).append(entry)

    buckets: list[SessionRegimeEvidence] = []
    for (session, regime), entries in grouped.items():
        sample = len(entries)
        win_count = sum(1 for e in entries if e.pnl_pct > 0)
        loss_count = sum(1 for e in entries if e.pnl_pct <= 0)
        win_rate = round(win_count / sample * 100.0, 1) if sample else None
        avg_pnl = round(sum(e.pnl_pct for e in entries) / sample, 2) if sample else None
        buckets.append(
            SessionRegimeEvidence(
                session=session,
                regime=regime,
                sampleSize=sample,
                winCount=win_count,
                lossCount=loss_count,
                winRatePct=win_rate,
                avgPnlPct=avg_pnl,
                evidenceState=_evidence_state(sample, win_rate),
            )
        )
    buckets.sort(key=lambda b: b.sample_size, reverse=True)
    return SessionRegimeEvidenceSummary(
        buckets=buckets,
        minSampleSize=MIN_SESSION_REGIME_SAMPLE,
        updatedAt=datetime.now(timezone.utc).isoformat(),
    )


def lookup_session_regime_evidence(
    summary: SessionRegimeEvidenceSummary, session: TradingSession, regime: MarketIntelligenceRegime
) -> SessionRegimeEvidence | None:
    """`None` (not a fabricated zero-record) when this company has never
    closed a real trade under this exact pairing yet."""
    return next((b for b in summary.buckets if b.session == session and b.regime == regime), None)
