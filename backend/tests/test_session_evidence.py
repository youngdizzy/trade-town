"""Covers app/session_evidence.py — CEO directive "Session Trading
Education & Agent Training." A (session, regime) pairing with too few
real observations must read NOT_ENOUGH_EVIDENCE, never a fabricated
favorable/unfavorable verdict; a pairing this company has never traded
under must never appear as a fabricated zero-evidence row.
"""
from __future__ import annotations

from app.schemas import DecisionVaultEntry, LiquidityRead
from app.session_evidence import (
    MIN_SESSION_REGIME_SAMPLE,
    compute_session_regime_evidence,
    lookup_session_regime_evidence,
)


def _now_iso() -> str:
    return "2026-01-01T00:00:00+00:00"


def _vault_entry(
    *,
    entry_id: str,
    session: str = "new_york",
    market_regime: str = "sideways_range",
    pnl_pct: float = 1.0,
    sim_day: int = 1,
) -> DecisionVaultEntry:
    return DecisionVaultEntry(
        id=entry_id,
        tradeId=f"trade-{entry_id}",
        decisionId=f"decision-{entry_id}",
        symbol="NEXA",
        simDay=sim_day,
        session=session,  # type: ignore[arg-type]
        strategyId=None,
        marketRegime=market_regime,  # type: ignore[arg-type]
        marketRegimeLabel="test regime",
        liquidityContext=LiquidityRead(symbol="NEXA", zones=[], sweepDetected=False, sweepDirection="none", liquidityScore=50.0, detail="test"),
        evidenceScore=70.0,
        confidenceScore=70.0,
        confidenceTier="strong",  # type: ignore[arg-type]
        capitalAllocationGrade="B",  # type: ignore[arg-type]
        decisionGrade="B",  # type: ignore[arg-type]
        decisionGradeScore=80.0,
        disciplineTier="sound",  # type: ignore[arg-type]
        disciplineScore=75.0,
        patienceGrade="B",  # type: ignore[arg-type]
        positionSize=10.0,
        entryPrice=100.0,
        exitPrice=100.0 + pnl_pct,
        pnl=pnl_pct * 10.0,
        pnlPct=pnl_pct,
        holdDurationMinutes=60,
        rMultiple=None,
        caseStudyId=None,
        caseStudyCategory=None,
        executiveNotes=None,
        lessonsLearned="test lesson",
        companyDnaChange=None,
        ceoOverride=False,
        createdAt=_now_iso(),
    )


class TestComputeSessionRegimeEvidence:
    def test_empty_vault_produces_no_buckets(self):
        summary = compute_session_regime_evidence([])
        assert summary.buckets == []
        assert summary.min_sample_size == MIN_SESSION_REGIME_SAMPLE

    def test_below_floor_sample_reads_not_enough_evidence(self):
        entries = [_vault_entry(entry_id=f"e{i}", session="asian", pnl_pct=1.0) for i in range(MIN_SESSION_REGIME_SAMPLE - 1)]
        summary = compute_session_regime_evidence(entries)
        bucket = summary.buckets[0]
        assert bucket.sample_size == MIN_SESSION_REGIME_SAMPLE - 1
        assert bucket.evidence_state == "not_enough_evidence"

    def test_high_win_rate_at_the_floor_reads_favorable(self):
        entries = [_vault_entry(entry_id=f"e{i}", session="london", pnl_pct=1.0) for i in range(MIN_SESSION_REGIME_SAMPLE)]
        summary = compute_session_regime_evidence(entries)
        bucket = summary.buckets[0]
        assert bucket.evidence_state == "favorable"
        assert bucket.win_rate_pct == 100.0
        assert bucket.win_count == MIN_SESSION_REGIME_SAMPLE
        assert bucket.loss_count == 0

    def test_low_win_rate_reads_unfavorable(self):
        entries = [_vault_entry(entry_id=f"e{i}", session="new_york", pnl_pct=-1.0) for i in range(MIN_SESSION_REGIME_SAMPLE)]
        summary = compute_session_regime_evidence(entries)
        assert summary.buckets[0].evidence_state == "unfavorable"

    def test_mid_win_rate_reads_mixed(self):
        entries = [_vault_entry(entry_id=f"e{i}", session="new_york", pnl_pct=1.0 if i < 2 else -1.0) for i in range(4)] + [
            _vault_entry(entry_id="e4", session="new_york", pnl_pct=1.0)
        ]
        summary = compute_session_regime_evidence(entries)
        assert summary.buckets[0].sample_size == 5
        assert summary.buckets[0].win_rate_pct == 60.0
        # 60% is exactly the favorable threshold, so bump one win to a loss instead.
        entries = [_vault_entry(entry_id=f"m{i}", session="new_york", pnl_pct=1.0 if i < 2 else -1.0) for i in range(5)]
        summary = compute_session_regime_evidence(entries)
        assert summary.buckets[0].win_rate_pct == 40.0
        assert summary.buckets[0].evidence_state == "mixed"

    def test_a_zero_pnl_trade_counts_as_a_loss_never_dropped(self):
        entries = [_vault_entry(entry_id=f"e{i}", session="asian", pnl_pct=0.0) for i in range(MIN_SESSION_REGIME_SAMPLE)]
        summary = compute_session_regime_evidence(entries)
        bucket = summary.buckets[0]
        assert bucket.win_count == 0
        assert bucket.loss_count == MIN_SESSION_REGIME_SAMPLE

    def test_different_sessions_and_regimes_form_separate_buckets(self):
        entries = [
            _vault_entry(entry_id="a", session="asian", market_regime="sideways_range"),
            _vault_entry(entry_id="b", session="london", market_regime="sideways_range"),
            _vault_entry(entry_id="c", session="asian", market_regime="expansion"),
        ]
        summary = compute_session_regime_evidence(entries)
        assert len(summary.buckets) == 3

    def test_buckets_sorted_by_sample_size_descending(self):
        entries = [_vault_entry(entry_id=f"a{i}", session="asian") for i in range(3)] + [
            _vault_entry(entry_id=f"b{i}", session="london") for i in range(7)
        ]
        summary = compute_session_regime_evidence(entries)
        assert summary.buckets[0].session == "london"
        assert summary.buckets[0].sample_size == 7


class TestLookupSessionRegimeEvidence:
    def test_returns_none_for_a_never_seen_pairing(self):
        summary = compute_session_regime_evidence([_vault_entry(entry_id="e1", session="asian", market_regime="expansion")])
        assert lookup_session_regime_evidence(summary, "london", "compression") is None

    def test_returns_the_matching_bucket(self):
        entries = [_vault_entry(entry_id=f"e{i}", session="london_ny_overlap", market_regime="strong_bull_trend") for i in range(6)]
        summary = compute_session_regime_evidence(entries)
        found = lookup_session_regime_evidence(summary, "london_ny_overlap", "strong_bull_trend")
        assert found is not None
        assert found.sample_size == 6
