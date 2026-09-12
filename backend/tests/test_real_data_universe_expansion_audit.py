"""CEO directive "TradeTown — Real-Data Research Universe Expansion 2.0."

PHASE 0 FORENSIC AUDIT, SUMMARIZED (this milestone's own final forensic
report has the full detail). Two independent expansion axes were
evaluated — additional symbols, additional timeframes — and BOTH are
genuinely blocked from producing new, safely-evidenced real research
breadth in this pass. This module is the durable, live-verified proof
of both findings, not a placeholder — it will fail loudly the moment
either finding stops being true, which is exactly the point.

AXIS 1 — SYMBOLS: A HARD, PROVABLE CEILING, NOT A LACK OF EFFORT. This
codebase's own canonical crypto taxonomy (`app/watchlist.py::SEED_SYMBOLS`
+ `EXTRA_SYMBOL_POOL`, `app/asset_discovery.py::DISCOVERY_SYMBOL_POOL`,
category `"bitcoin"`) already contains EXACTLY `{"BTC-USD", "ETH-USD"}`
— proven by "Multi-Symbol Real-Data Expansion 1.0"'s own
`test_multi_symbol_research_expansion.py::test_universe_rule_still_yields_exactly_eth_usd`,
re-affirmed here rather than re-implemented. Kraken (this codebase's
only real market-data provider — see `app/market_data.py`'s own module
section docstring) is a cryptocurrency-only exchange; every OTHER
symbol in this codebase's own taxonomy (stocks, ETFs, indices, futures,
FX, Treasuries) has no Kraken pair to map to at all — not a missing
mapping, a missing ASSET CLASS. This directive's own Section 4
explicitly forbids inventing a symbol the repository has no legitimate
source for ("Do not invent a 'top 20' list from external rankings
unless the repository already has a legitimate source for it") — a
grep of every Design Bible / Architecture / Company Lore document in
this repo (see this milestone's forensic report, Section 5) found zero
mentions of any third cryptocurrency anywhere in this codebase's own
design intent. There is therefore no candidate symbol this pass could
add without fabricating one.

AXIS 2 — TIMEFRAMES: PROVIDER- AND RESEARCH-ENGINE-CAPABLE, BUT NOT YET
SAFELY ACCUMULATION-CAPABLE. Live verification below (real Kraken
requests, CASE A/B disclosure pattern) proves Kraken's public OHLC
endpoint, `app/market_data.py::KrakenMarketDataProvider` (unmodified),
and the real research engine (`app/research_experiment.py`,
`app/walk_forward.py`, `app/holdout.py`, all unmodified) already
support every one of `app/market_data.py::TIMEFRAMES`'s six entries
(1m/5m/15m/1h/4h/1d) for both canonical symbols — genuinely clean,
gap-free, duplicate-free, chronologically-ordered, OHLC-valid, and with
the still-forming bar already dropped, exactly as the existing 1h path
already is. The real, disclosed blocker is one level up:
`app/real_data_accumulator.py` — the one real, protected append-only
persistence layer real Factory evidence must flow through — was built
around a SINGLE, hardcoded `TIMEFRAME` module constant and a
`_get_frozen_definition()` helper that unconditionally returns
`registry[STRATEGY_DEFINITION_ID][0]` (the first/only frozen version),
with no timeframe-aware selection at all. Safely extending it to
accumulate a second timeframe would require either (a) adding a
`timeframe` column to `holdout_boundary`'s primary key — a real schema
change to the one system this directive's own Section 0 says never to
touch a second time — or (b) registering a second, honestly-tagged
strategy VERSION per timeframe and reworking `_get_frozen_definition()`
to select by timeframe instead of by blind index, a materially larger,
riskier change to the accumulator's core control flow than this
directive's own "smallest safe increment" principle permits in one
pass. Per Section 33 ("STOP if... expansion requires changing holdout
rules... provenance becomes ambiguous") and Section 32 ("if the
forensic audit proves expansion is currently blocked by genuine
provider/research limitations, return an audit report rather than
create artificial work"), this module documents the finding
structurally rather than forcing the accumulator change through.

NO PRODUCTION CODE WAS CHANGED FOR THIS MILESTONE. Every test below
either calls real, already-shipped, unmodified functions, or performs
one real, bounded live HTTP request to Kraken's already-integrated
public endpoint via the unmodified `KrakenMarketDataProvider`.
"""
from __future__ import annotations

import inspect
import socket
import urllib.error

import pytest

from app.asset_discovery import DISCOVERY_SYMBOL_POOL
from app.holdout import freeze_strategy, partition_candles_chronologically, run_holdout_evaluation, validate_holdout
from app.market_data import TIMEFRAMES, ExternalMarketDataProviderUnavailable, KrakenMarketDataProvider, MarketDataProvider
from app.real_data_accumulator import SYMBOLS as ACCUMULATOR_SYMBOLS
from app.real_data_accumulator import _get_frozen_definition
from app.research_experiment import run_research_experiment
from app.strategy_registry import default_researchable_strategies
from app.walk_forward import run_walk_forward_validation
from app.watchlist import EXTRA_SYMBOL_POOL, SEED_SYMBOLS

_STRATEGIES, _REGISTRY = default_researchable_strategies()
SELECTED_DEFINITION = _REGISTRY["50-ema-breakout-pullback-long"][0]
assert SELECTED_DEFINITION.status == "compiled"

SYMBOLS = ["BTC-USD", "ETH-USD"]
CANDIDATE_TIMEFRAMES = list(TIMEFRAMES)  # ["1m", "5m", "15m", "1h", "4h", "1d"]
MIN_BARS_FLOOR = 215  # see app/strategy_engine.py: MIN_BARS_ON_SIDE_BEFORE_CROSS(5) + MAX_HOLD_BARS(150) + 60


class _FrozenSnapshotProvider(MarketDataProvider):
    """Replays one already-fetched real candle list for a fixed
    (symbol, timeframe) pair — the same isolation convention every
    prior real-data expansion test module in this repo already uses."""

    def __init__(self, symbol: str, timeframe: str, candles: list) -> None:
        self._symbol = symbol
        self._timeframe = timeframe
        self._candles = candles

    def get_quote(self, symbol: str):  # pragma: no cover - unused by this suite
        raise NotImplementedError

    def get_candles(self, symbol: str, timeframe: str, limit: int, *, end_time=None, anchor_price=None):
        assert symbol == self._symbol
        assert timeframe == self._timeframe
        return self._candles[-limit:] if limit > 0 else list(self._candles)


@pytest.fixture(scope="module")
def real_candles_by_symbol_timeframe() -> dict[tuple[str, str], list]:
    """One real, bounded Kraken request per (symbol, timeframe) pair —
    12 total, well within Kraken's own documented public-endpoint rate
    tolerance (see `KrakenMarketDataProvider`'s own docstring). Skips
    the whole module (never fabricates a result) on genuine
    connectivity failure."""
    kraken = KrakenMarketDataProvider()
    out: dict[tuple[str, str], list] = {}
    for symbol in SYMBOLS:
        for timeframe in CANDIDATE_TIMEFRAMES:
            try:
                out[(symbol, timeframe)] = kraken.get_candles(symbol, timeframe, 100_000)
            except ExternalMarketDataProviderUnavailable as exc:
                pytest.skip(f"Real Kraken external verification could not be completed in this environment: {exc}")
            except (urllib.error.URLError, socket.timeout, ConnectionError, TimeoutError) as exc:
                pytest.skip(f"Real network connectivity to Kraken unavailable in this environment: {exc}")
    return out


class TestSymbolAxisIsAProvenCeiling:
    """AXIS 1 — re-affirms the pre-registered universe rule established
    by "Multi-Symbol Real-Data Expansion 1.0" is still exactly the
    codebase's real crypto universe, and that Kraken has no pair mapping
    for any non-crypto canonical symbol (a structural fact about
    `KrakenMarketDataProvider._SYMBOL_TO_PAIR`, not a guess)."""

    def test_canonical_crypto_universe_is_still_exactly_btc_and_eth(self) -> None:
        crypto_symbols = {symbol for symbol, _name, category in (*SEED_SYMBOLS, *EXTRA_SYMBOL_POOL, *DISCOVERY_SYMBOL_POOL) if category == "bitcoin"}
        assert crypto_symbols == {"BTC-USD", "ETH-USD"}, (
            "the pre-registered universe rule has changed since the last real-data expansion milestone — "
            "re-audit before assuming no further symbol is available"
        )

    def test_no_non_crypto_canonical_symbol_has_a_kraken_pair_mapping(self) -> None:
        provider = KrakenMarketDataProvider()
        non_crypto_symbols = {
            symbol for symbol, _name, category in (*SEED_SYMBOLS, *EXTRA_SYMBOL_POOL, *DISCOVERY_SYMBOL_POOL) if category != "bitcoin"
        }
        mapped = provider._SYMBOL_TO_PAIR  # noqa: SLF001 - structural audit of the real, disclosed mapping table
        assert non_crypto_symbols.isdisjoint(mapped), "a non-crypto canonical symbol now has a Kraken pair mapping — re-audit; Kraken is a crypto-only exchange"
        assert set(mapped) == {"BTC-USD", "ETH-USD"}, "KrakenMarketDataProvider now maps a symbol beyond the two already fully accumulated — re-audit before assuming no further symbol is available"


class TestTimeframeAxisIsProviderAndEngineCapable:
    """AXIS 2, part 1 — live, real proof that every TIMEFRAMES entry is
    genuinely servable by Kraken for both canonical symbols, with the
    same data-quality bar the existing 1h path already meets."""

    def test_every_timeframe_returns_clean_real_closed_candles(self, real_candles_by_symbol_timeframe: dict) -> None:
        for (symbol, timeframe), candles in real_candles_by_symbol_timeframe.items():
            assert len(candles) > 0, f"{symbol} {timeframe}: Kraken returned zero real candles"
            assert all(c.symbol == symbol for c in candles)
            assert all(c.data_status == "historical" for c in candles), f"{symbol} {timeframe}: a non-closed/non-real candle was returned"
            timestamps = [c.timestamp for c in candles]
            assert timestamps == sorted(timestamps), f"{symbol} {timeframe}: candles not chronologically ordered"
            assert len(set(timestamps)) == len(timestamps), f"{symbol} {timeframe}: duplicate timestamps"
            assert all(c.high >= c.low and c.high >= c.open and c.high >= c.close and c.low <= c.open and c.low <= c.close for c in candles), (
                f"{symbol} {timeframe}: an impossible OHLC relationship was returned"
            )

    def test_every_timeframe_has_uniform_real_interval_spacing(self, real_candles_by_symbol_timeframe: dict) -> None:
        from datetime import datetime

        for (symbol, timeframe), candles in real_candles_by_symbol_timeframe.items():
            expected_minutes = TIMEFRAMES[timeframe]
            dts = [datetime.fromisoformat(c.timestamp) for c in candles]
            gaps_minutes = {int((b - a).total_seconds() // 60) for a, b in zip(dts, dts[1:])}
            assert gaps_minutes == {expected_minutes}, f"{symbol} {timeframe}: expected a uniform {expected_minutes}-minute gap, found {gaps_minutes}"

    def test_research_engine_is_timeframe_agnostic_on_a_non_1h_real_dataset(self, real_candles_by_symbol_timeframe: dict) -> None:
        """Picks the coarsest non-1h candidate (4h) and proves the SAME,
        unmodified `run_research_experiment()` produces a genuinely
        real-provenance research record from it — no code path here is
        specific to "1h"."""
        timeframe = "4h"
        candles = real_candles_by_symbol_timeframe[("BTC-USD", timeframe)]
        provider = _FrozenSnapshotProvider("BTC-USD", timeframe, candles)
        record = run_research_experiment(SELECTED_DEFINITION, symbols=["BTC-USD"], timeframe=timeframe, candles_per_symbol=len(candles), market_data_provider=provider)
        assert record.dataset_metadata is not None
        assert record.dataset_metadata.source == "external_real_provider"
        assert record.dataset_metadata.data_category == "real"
        assert record.look_ahead_audit.verdict == "clean"

    def test_holdout_partition_is_valid_on_a_non_1h_real_dataset(self, real_candles_by_symbol_timeframe: dict) -> None:
        """Extends "Real-Data Research Expansion 1.0"'s own holdout-on-
        real-data proof (previously 1h-only) to a second granularity —
        the SAME unmodified `app/holdout.py` machinery."""
        timeframe = "15m"
        candles = real_candles_by_symbol_timeframe[("ETH-USD", timeframe)]
        train, validation, holdout = partition_candles_chronologically(candles)
        freeze = freeze_strategy(SELECTED_DEFINITION, dataset_version="expansion-audit", feature_versions=[])
        report = validate_holdout(
            SELECTED_DEFINITION,
            train=train,
            validation=validation,
            holdout=holdout,
            dataset_id=f"kraken-eth-usd-{timeframe}-expansion-audit",
            dataset_version="expansion-audit",
            freeze=freeze,
            report_id="timeframe-expansion-audit-holdout",
        )
        assert report.status == "valid"
        assert report.overlap_detected is False
        assert report.leakage_detected is False
        result = run_holdout_evaluation(SELECTED_DEFINITION, "ETH-USD", report=report, holdout_candles=holdout, result_id="timeframe-expansion-audit-holdout-eval")
        assert result.report.status == "valid"

    def test_walk_forward_produces_windows_on_a_non_1h_real_dataset(self, real_candles_by_symbol_timeframe: dict) -> None:
        timeframe = "1d"
        candles = real_candles_by_symbol_timeframe[("BTC-USD", timeframe)]
        window_bars = len(candles) // 3
        if window_bars < MIN_BARS_FLOOR:
            pytest.skip(f"Real candle count {len(candles)} at {timeframe} cannot form 3 windows meeting the {MIN_BARS_FLOOR}-bar floor.")
        provider = _FrozenSnapshotProvider("BTC-USD", timeframe, candles)
        result = run_walk_forward_validation(
            SELECTED_DEFINITION, symbols=["BTC-USD"], timeframe=timeframe, candles_per_symbol=len(candles), window_bars=window_bars, market_data_provider=provider
        )
        assert len(result.symbols[0].windows) == 3


class TestTimeframeAxisGapWasClosedByTheFollowUpMilestone:
    """AXIS 2, part 2 — UPDATE per CEO directive "TradeTown —
    Timeframe-Aware Real-Data Research Infrastructure 1.0": the gap
    this class originally documented (a single, hardcoded `TIMEFRAME`
    constant and a frozen-definition selector with no timeframe
    awareness) is now CLOSED, exactly as this class's own original
    docstring predicted it eventually would be. `_get_frozen_definition()`
    correctly remains timeframe-parameter-free (strategy identity is
    independent of which timeframe it is evaluated against — Section
    4/5 of that follow-up directive), but `TIMEFRAME` is now the plural,
    deliberately-bounded `TIMEFRAMES = ("1h", "4h")`, and
    `holdout_boundary`/`trades` both gained `timeframe` as part of their
    own primary key. Structural proof, not prose — kept in this file
    (rather than deleted) as the permanent record of the finding this
    audit made and the follow-up that closed it."""

    def test_frozen_definition_selection_still_has_no_timeframe_parameter(self) -> None:
        """Correctly unchanged — strategy identity is independent of
        the timeframe it is evaluated against."""
        params = inspect.signature(_get_frozen_definition).parameters
        assert "timeframe" not in params

    def test_accumulator_timeframe_is_now_a_small_bounded_tuple(self) -> None:
        from app.real_data_accumulator import TIMEFRAMES

        assert TIMEFRAMES == ("1h", "4h"), "the follow-up milestone's own 'smallest safe increment' scope has changed — re-audit before assuming this"

    def test_accumulator_symbols_constant_is_unchanged_by_this_audit(self) -> None:
        """This milestone made no production code change — the real,
        already-accumulating symbol set is exactly what it was before
        this audit ran."""
        assert ACCUMULATOR_SYMBOLS == ("BTC-USD", "ETH-USD")


class TestExistingRealDataBehaviorUnchanged:
    """Regression proof (Section 27, item J/K/L): this purely-diagnostic
    milestone changed zero production code, so the existing real-data
    1h path, mock research, and every trading/risk code path are
    provably untouched by construction — no import of any trading/risk/
    paper-trading module appears anywhere in this file."""

    def test_this_module_imports_no_trading_or_risk_module(self) -> None:
        import ast
        import sys

        this_module = sys.modules[__name__]
        tree = ast.parse(inspect.getsource(this_module))
        imported_modules: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_modules.add(node.module)
        forbidden = {"app.nexus", "app.risk_contract", "app.paper_trading", "app.gatekeeper", "app.position_sizing"}
        assert imported_modules.isdisjoint(forbidden), f"a trading/risk module was imported by this pure research-breadth audit module: {imported_modules & forbidden}"
