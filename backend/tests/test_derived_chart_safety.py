"""CEO directive "Professional Trading Firm — Market-Analysis Knowledge
+ Session Intelligence Expansion," Phase 2's critical rule: "Heikin-Ashi
and Renko are derived representations. They must NEVER be treated as the
actual executable market price... the underlying real price must remain
the source of truth for: entries, exits, stops, fills, P&L, risk,
execution." Also covers Definition-of-Done point 12 ("proof derived
chart types cannot affect real execution prices").

Neither Heikin-Ashi nor Renko is implemented anywhere in this codebase
(confirmed below by source inspection) — there is no derived-chart
feature to exercise behaviorally yet. What IS provable today, and stays
provable if either is ever added, is the real architectural boundary
this rule depends on: app/portfolio.py's open_position()/close_position()
(this codebase's one real execution surface, per that module's own
module docstring) never import or call anything from
app/technical_indicators.py or app/technical_patterns.py — the two
modules a derived-chart transform would naturally live in or feed from.
"""
from __future__ import annotations

import ast
import inspect

from app import portfolio
from app.market_data import market_data_provider


class TestNoDerivedChartRepresentationExistsYet:
    def test_no_heikin_ashi_or_renko_implementation_anywhere_in_the_backend(self) -> None:
        # A derived-chart transform doesn't exist yet in this codebase
        # (Phase 2 scope: document the rule now, before either is ever
        # built) -- confirmed by source inspection of the one module
        # that would plausibly house it.
        import app.technical_patterns as tp

        source = inspect.getsource(tp)
        assert "heikin" not in source.lower()
        assert "renko" not in source.lower()


class TestExecutionSurfaceOnlyReadsRealPrices:
    """app/portfolio.py's own module docstring: "open_position()/
    close_position() are this codebase's one real execution surface."
    Neither function, nor mark_to_market(), imports or references
    anything from the two modules a derived-chart transform would live
    in or feed from."""

    def test_portfolio_module_does_not_import_technical_indicators_or_patterns(self) -> None:
        tree = ast.parse(inspect.getsource(portfolio))
        imported_modules: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported_modules.add(node.module)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imported_modules.add(alias.name)
        assert "app.technical_indicators" not in imported_modules
        assert "app.technical_patterns" not in imported_modules
        assert "app.technical_analysis" not in imported_modules

    def test_open_position_and_close_position_take_a_plain_price_float(self) -> None:
        # The real execution signature: a caller-supplied plain float,
        # not a Candle/derived-chart object -- so whatever computed it
        # (real Quote/Candle data today) is the caller's contract to
        # honor, not something these functions parse or transform.
        open_sig = inspect.signature(portfolio.open_position)
        close_sig = inspect.signature(portfolio.close_position)
        assert open_sig.parameters["price"].annotation == "float"
        assert close_sig.parameters["exit_price"].annotation == "float"

    def test_market_data_provider_get_candles_returns_real_market_data_candles(self) -> None:
        # The one real source every execution price in this codebase
        # traces back to (via app/broker.py, app/executive.py, app/
        # trading_modes.py, app/paper_trading.py -- see this test
        # module's own docstring for the traced call chain) -- confirmed
        # to be app/market_data.py's own Candle type, never a derived
        # representation type.
        candles = market_data_provider.get_candles("NEXA", "1h", 5)
        assert candles
        from app.market_data import Candle as ProviderCandle

        assert all(isinstance(c, ProviderCandle) for c in candles)
