"""Covers app/survivorship.py — CEO directive "Professional Quant
Trading Firm — Quant Intelligence + Market Analysis Completion Phase
(Next Research + Validation Pass)," item 8. This module is a disclosed
data-availability interface, not a real check — every test here confirms
it stays honest rather than ever fabricating a "no bias found" result.
"""
from __future__ import annotations

from app.survivorship import check_survivorship_bias


class TestCheckSurvivorshipBias:
    def test_a_seed_symbol_is_still_honestly_reported_unavailable(self) -> None:
        result = check_survivorship_bias("AAPL")
        assert result.status == "unavailable"
        assert "no historical constituent" in result.detail or "historical constituent" in result.detail

    def test_an_unknown_symbol_gets_the_same_honest_answer_not_a_different_guess(self) -> None:
        known = check_survivorship_bias("AAPL")
        unknown = check_survivorship_bias("NOT-A-REAL-SYMBOL")
        assert known.status == unknown.status == "unavailable"
        assert known.detail == unknown.detail

    def test_symbol_is_echoed_back_uppercased(self) -> None:
        result = check_survivorship_bias("aapl")
        assert result.symbol == "AAPL"

    def test_the_detail_never_claims_no_bias_was_found(self) -> None:
        result = check_survivorship_bias("AAPL")
        assert "no bias detected" not in result.detail.lower()
        assert "unavailable" in result.detail.lower()
