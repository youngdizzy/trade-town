"""Covers app/signal_correlation.py — CEO directive "Professional
Trading Firm — Market-Analysis Knowledge + Session Intelligence
Expansion," Phase 6, the Confluence Engine. `independent_evidence_count`
must only ever fall below `naive_confirmation_count` for the real,
disclosed reasons in the module docstring — never as an arbitrary
discount.
"""
from __future__ import annotations

from app.schemas import AnalystVote
from app.signal_correlation import assess_confluence


def _vote(role: str, choice: str = "buy") -> AnalystVote:
    return AnalystVote(role=role, agentId="echo", choice=choice, reasoning="test", evidence=[])  # type: ignore[arg-type]


class TestAssessConfluence:
    def test_no_votes_reads_zero_with_no_fabricated_evidence(self) -> None:
        read = assess_confluence([], "buy")
        assert read.naive_confirmation_count == 0
        assert read.independent_evidence_count == 0
        assert read.correlated_pairs == []

    def test_no_agreement_reads_zero(self) -> None:
        votes = [_vote("technical", "sell"), _vote("risk", "wait")]
        read = assess_confluence(votes, "buy")
        assert read.naive_confirmation_count == 0
        assert read.independent_evidence_count == 0

    def test_three_genuinely_independent_roles_have_no_divergence(self) -> None:
        votes = [_vote("technical"), _vote("risk"), _vote("sentiment")]
        read = assess_confluence(votes, "buy")
        assert read.naive_confirmation_count == 3
        assert read.independent_evidence_count == 3
        assert read.correlated_pairs == []
        assert "genuinely independent" in read.detail

    def test_news_and_macro_agreeing_are_counted_as_one_independent_source(self) -> None:
        votes = [_vote("technical"), _vote("news"), _vote("macro")]
        read = assess_confluence(votes, "buy")
        assert read.naive_confirmation_count == 3
        # technical (independent) + {news,macro} (one correlated group) = 2
        assert read.independent_evidence_count == 2
        assert len(read.correlated_pairs) == 1
        pair = read.correlated_pairs[0]
        assert {pair.role_a, pair.role_b} == {"news", "macro"}

    def test_news_agreeing_alone_without_macro_is_not_flagged_correlated(self) -> None:
        votes = [_vote("technical"), _vote("news")]
        read = assess_confluence(votes, "buy")
        assert read.naive_confirmation_count == 2
        assert read.independent_evidence_count == 2
        assert read.correlated_pairs == []

    def test_execution_agreeing_counts_toward_naive_but_never_independent(self) -> None:
        votes = [_vote("technical"), _vote("risk"), _vote("execution")]
        read = assess_confluence(votes, "buy")
        assert read.naive_confirmation_count == 3
        assert read.independent_evidence_count == 2
        assert "only" in read.detail

    def test_execution_and_correlated_pair_together(self) -> None:
        votes = [_vote("technical"), _vote("news"), _vote("macro"), _vote("execution")]
        read = assess_confluence(votes, "buy")
        assert read.naive_confirmation_count == 4
        # technical (independent) + {news,macro} (one group) = 2; execution excluded entirely
        assert read.independent_evidence_count == 2
        assert len(read.correlated_pairs) == 1

    def test_only_votes_matching_the_recommendation_are_counted(self) -> None:
        votes = [_vote("technical", "buy"), _vote("risk", "sell"), _vote("sentiment", "wait")]
        read = assess_confluence(votes, "buy")
        assert read.naive_confirmation_count == 1
        assert read.independent_evidence_count == 1
