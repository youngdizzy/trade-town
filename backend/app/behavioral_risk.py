"""Behavioral Circuit Breaker — the real revenge-trading detector Design
Bible Chapter 66's own Gatekeeper docstring and app/constitution.py's
Article V both already named as a deliberately unbuilt gap ("this
codebase has no real signal for literally re-entering a position out of
anger after a loss"). Closes that gap honestly: every signal below reads
real, already-persisted trade data (symbol, quantity, price, pnl,
timestamps) — never a fabricated read of the CEO's emotional state. This
system detects observable behavioral risk. It does not claim to detect
human emotion.

Ships as the Gatekeeper's tenth check (app/gatekeeper.py::_behavioral_check),
never a second, parallel enforcement path — see that module for the
composition. `compute_behavioral_check()` below is the one real function
serving both that per-proposal check (a real `candidate` TradeProposal in
scope) and the ambient tick-level dashboard read (`candidate=None`, no
specific proposal to evaluate yet — capped at `warning`, since the two
corroborating signals below need a real candidate to compare against).

Four signals, all deterministic:
  1. Recent loss    — the most recently closed trade lost money.
  2. Rapid re-entry — a new trade is being considered within
                       `cooldown_minutes` of that loss closing.
  3. Same instrument — the candidate trades the same symbol as the loss.
  4. Loss-driven size increase — the candidate's dollar size is more than
                       `size_increase_threshold_pct` above this account's
                       own recent normal (a self-relative baseline, never
                       a hard-coded dollar figure).
A fifth, "repeated rapid re-entry," counts how many times signal 1+2 have
already co-occurred in recent trade history — real corroborating
evidence of a pattern, not a new data source (it's a count over the same
trade_history every other signal here already reads).

Severity requires corroboration, matching the CEO's own review: "a
legitimate setup immediately following a loss must remain possible."
Timing alone (signals 1+2, no candidate, or no corroborating 3/4) never
exceeds `warning` — informational only, never blocks. Only signals 1+2
plus at least one of 3/4 reaches `triggered`, which fails this one
Gatekeeper check for this one proposal — never a blanket future block,
never Emergency Stop.

Account-Awareness: this reads `portfolio.trade_history` — the single
real, live-execution-connected `PaperPortfolio` (Design Bible Chapter 69
Part 1 already confirmed no secondary Account has live trade routing
today). There is no per-Account trade history to scope against yet, so
no per-Account plumbing is invented here; if/when per-Account live
execution is built, this check must be re-scoped to run per-Account
rather than company-wide.

Explicitly NOT built this pass (named as deferred, not silently
skipped): repeated-rejected-setups-retried, repeated trading-mode-
switching, and "recovering the exact dollar amount lost" — none has a
real per-proposal data source in this codebase yet.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.schemas import BehavioralCircuitBreakerRead, BehavioralCircuitBreakerStatus, PaperTrade, TradeProposal
from app.trading_modes import compute_consecutive_losses

# How many of the account's own most recent closed trades (excluding the
# loss itself) establish "recent normal" size — a real trailing window,
# not the whole account history, so a years-old sizing habit can't mask a
# genuine recent change. Mirrors the trailing-window shape of
# app/trading_modes.py's own HEALTH_RECENT_TRADE_WINDOW without reusing
# that constant, since it answers a different question (size baseline vs.
# win-rate health).
SIZE_BASELINE_TRADES = 10

# How far back to look for prior rapid-re-entry occurrences when counting
# a "repeated" pattern — real trade history, not a new data source.
REPEATED_REENTRY_LOOKBACK_TRADES = 20


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_behavioral_circuit_breaker() -> BehavioralCircuitBreakerRead:
    return BehavioralCircuitBreakerRead(
        status="clear",
        reasons=[],
        previousLossSymbol=None,
        previousLossPnl=None,
        minutesSinceLoss=None,
        cooldownMinutes=60,
        sameInstrument=None,
        sizeIncreasePct=None,
        consecutiveLosses=0,
        repeatedRapidReentryCount=0,
        computedAt=_now_iso(),
    )


def _size_baseline_dollar_value(trade_history: list[PaperTrade]) -> float | None:
    """Average dollar value (quantity * entry price) of the account's own
    most recent closed trades, excluding the most recent trade (the loss
    itself, when signal 1 is active). None when there's no real baseline
    to compare against yet (fewer than one prior trade) — the honest
    "not applicable" read, never a divide-by-zero or a fabricated
    default."""
    baseline_trades = trade_history[:-1][-SIZE_BASELINE_TRADES:]
    if not baseline_trades:
        return None
    values = [t.quantity * t.entry_price for t in baseline_trades if t.quantity > 0 and t.entry_price > 0]
    if not values:
        return None
    return sum(values) / len(values)


def _count_repeated_rapid_reentries(trade_history: list[PaperTrade], cooldown_minutes: int) -> int:
    """Walks the trailing window of closed trades, counting how many
    times a trade opened within `cooldown_minutes` of the prior trade's
    loss-close — real historical evidence of a pattern, derived entirely
    from fields every PaperTrade already carries (opened_sim_minutes,
    closed_sim_minutes, pnl)."""
    window = trade_history[-REPEATED_REENTRY_LOOKBACK_TRADES:]
    count = 0
    for previous, current in zip(window, window[1:]):
        if previous.pnl < 0 and current.opened_sim_minutes - previous.closed_sim_minutes < cooldown_minutes:
            count += 1
    return count


def compute_behavioral_check(
    candidate: TradeProposal | None,
    trade_history: list[PaperTrade],
    now_sim_minutes: int,
    cooldown_minutes: int,
    size_increase_threshold_pct: float,
) -> BehavioralCircuitBreakerRead:
    consecutive_losses = compute_consecutive_losses(trade_history)
    repeated_rapid_reentry_count = _count_repeated_rapid_reentries(trade_history, cooldown_minutes)

    last_loss = trade_history[-1] if trade_history and trade_history[-1].pnl < 0 else None
    if last_loss is None:
        return BehavioralCircuitBreakerRead(
            status="clear",
            reasons=[],
            previousLossSymbol=None,
            previousLossPnl=None,
            minutesSinceLoss=None,
            cooldownMinutes=cooldown_minutes,
            sameInstrument=None,
            sizeIncreasePct=None,
            consecutiveLosses=consecutive_losses,
            repeatedRapidReentryCount=repeated_rapid_reentry_count,
            computedAt=_now_iso(),
        )

    minutes_since_loss = now_sim_minutes - last_loss.closed_sim_minutes
    rapid_reentry = minutes_since_loss < cooldown_minutes

    reasons = [f"Previous trade on {last_loss.symbol} lost ${abs(last_loss.pnl):,.2f}, closed {minutes_since_loss} minute(s) ago."]

    if not rapid_reentry:
        return BehavioralCircuitBreakerRead(
            status="clear",
            reasons=reasons,
            previousLossSymbol=last_loss.symbol,
            previousLossPnl=last_loss.pnl,
            minutesSinceLoss=minutes_since_loss,
            cooldownMinutes=cooldown_minutes,
            sameInstrument=None,
            sizeIncreasePct=None,
            consecutiveLosses=consecutive_losses,
            repeatedRapidReentryCount=repeated_rapid_reentry_count,
            computedAt=_now_iso(),
        )
    reasons.append(f"That is within the {cooldown_minutes}-minute post-loss cooldown window.")

    same_instrument: bool | None = None
    size_increase_pct: float | None = None
    corroborated = False

    if candidate is not None:
        same_instrument = candidate.symbol == last_loss.symbol
        if same_instrument:
            reasons.append(f"The proposed trade is the same instrument ({candidate.symbol}) as the loss.")
            corroborated = True

        baseline = _size_baseline_dollar_value(trade_history)
        if baseline is not None and baseline > 0 and candidate.quantity > 0 and candidate.price > 0:
            candidate_value = candidate.quantity * candidate.price
            size_increase_pct = round((candidate_value - baseline) / baseline * 100, 1)
            if size_increase_pct > size_increase_threshold_pct:
                reasons.append(f"Position size is {size_increase_pct:+.0f}% above this account's recent normal (loss-driven).")
                corroborated = True

    if repeated_rapid_reentry_count >= 2:
        reasons.append(f"Repeated rapid re-entry pattern detected: {repeated_rapid_reentry_count} rapid re-entries in recent trading history.")

    status: BehavioralCircuitBreakerStatus = "triggered" if (candidate is not None and corroborated) else "warning"

    return BehavioralCircuitBreakerRead(
        status=status,
        reasons=reasons,
        previousLossSymbol=last_loss.symbol,
        previousLossPnl=last_loss.pnl,
        minutesSinceLoss=minutes_since_loss,
        cooldownMinutes=cooldown_minutes,
        sameInstrument=same_instrument,
        sizeIncreasePct=size_increase_pct,
        consecutiveLosses=consecutive_losses,
        repeatedRapidReentryCount=repeated_rapid_reentry_count,
        computedAt=_now_iso(),
    )
