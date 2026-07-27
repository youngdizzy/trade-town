"""Player vs AI (v0.6.2 Phase 8) — the player calls ENTER/WAIT/AVOID on a
real past trade candidate *before* the AI's actual call is revealed, then
both are graded against the same real, already-realized outcome. Never
assumes the AI is right: `ai_correct` is computed from the same realized
P&L as `player_correct`, so a losing AI trade shows up as AI being wrong,
same as it would for the player.

Only decisions that led to a trade whose real outcome has already closed
are eligible — see `_eligible_decisions()`. A "no_trade" decision has no
realized P&L to grade against (we truly don't know what would have
happened), and an open position's outcome isn't final yet, so neither is
offered as a round; this is an honest scope limit, not an oversight.

Prompts are transient — held in `_pending` between GET .../prompt and
POST .../submit, never part of GameSaveState — the same treatment
signal_calibration.py's challenges get. Only the graded PlayerVsAiRound
is persisted, as real progress.
"""
from __future__ import annotations

import random
from datetime import datetime, timezone

from app.market_data import MarketDataProvider
from app.market_data import trend_pct as _trend_pct
from app.market_data import volatility_pct as _volatility_pct
from app.schemas import (
    MarketRegime,
    PaperTrade,
    PlayerVsAiPrompt,
    PlayerVsAiRound,
    PlayerVsAiState,
    ResearchCategory,
    ResearchItem,
    SignalChoice,
    TradeDecision,
)

REGIME_TIMEFRAME = "1h"
REGIME_CANDLE_COUNT = 30
MAX_ROUNDS = 100

# Transient in-process store: prompt id -> (prompt, decision, closed_trade).
# Not persisted — see module docstring.
_pending: dict[str, tuple[PlayerVsAiPrompt, TradeDecision, PaperTrade]] = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _category_for_symbol(symbol: str, research: list[ResearchItem]) -> ResearchCategory:
    """Best-effort: the current (or most recent) research item for this
    symbol's category. TradeTown's research queue rotates topics over
    time, so the exact item that was active when the original decision
    was made may since have completed and been replaced — this looks at
    whatever's on record for the symbol now, not a stored historical
    snapshot, and is honestly a best-effort label, not a guaranteed
    point-in-time category."""
    item = next((r for r in research if r.symbol == symbol), None)
    return item.category if item else "stock"


def _regime_for_symbol(symbol: str, provider: MarketDataProvider) -> MarketRegime:
    """The market's current read for this symbol — computed live at
    prompt time from the same trend/volatility functions Signal
    Calibration's level 3 uses (see market_data.py), not a reconstruction
    of what the market looked like when the original decision was made
    (TradeTown doesn't store historical candle snapshots per decision)."""
    candles = provider.get_candles(symbol, REGIME_TIMEFRAME, REGIME_CANDLE_COUNT)
    trend = _trend_pct(candles)
    volatility = _volatility_pct(candles)
    if abs(trend) <= 2 * max(volatility, 0.1):
        return "ranging"
    return "trending_up" if trend > 0 else "trending_down"


def _closed_trade_for(decision: TradeDecision, trade_history: list[PaperTrade]) -> PaperTrade | None:
    return next((t for t in trade_history if t.decision_id == decision.id), None)


def _eligible_decisions(
    decisions: list[TradeDecision], trade_history: list[PaperTrade], used_decision_ids: set[str]
) -> list[tuple[TradeDecision, PaperTrade]]:
    """Decisions that (a) led to a real trade, (b) that trade has since
    closed with a known, real P&L, and (c) haven't already been used for
    a round — so the same real outcome is never asked about twice."""
    eligible = []
    for decision in decisions:
        if decision.id in used_decision_ids or decision.outcome != "trade":
            continue
        trade = _closed_trade_for(decision, trade_history)
        if trade is not None:
            eligible.append((decision, trade))
    return eligible


def generate_prompt(
    decisions: list[TradeDecision],
    trade_history: list[PaperTrade],
    research: list[ResearchItem],
    provider: MarketDataProvider,
    used_decision_ids: set[str],
) -> PlayerVsAiPrompt:
    eligible = _eligible_decisions(decisions, trade_history, used_decision_ids)
    if not eligible:
        raise ValueError("No resolved AI trades available to compare against yet — check back once a paper trade closes.")

    decision, trade = random.choice(eligible)
    category = _category_for_symbol(decision.symbol, research)
    regime = _regime_for_symbol(decision.symbol, provider)

    prompt_id = f"pvai-{decision.id}-{_now_iso()}"
    prompt = PlayerVsAiPrompt(
        id=prompt_id,
        decisionId=decision.id,
        symbol=decision.symbol,
        category=category,
        researchSummary=decision.research_summary,
        technicalSummary=decision.technical_summary,
        riskSummary=decision.risk_summary,
        confidence=decision.confidence,
        regime=regime,
        createdAt=_now_iso(),
    )
    _pending[prompt_id] = (prompt, decision, trade)
    return prompt


def grade_submission(
    state: PlayerVsAiState, prompt_id: str, player_choice: SignalChoice
) -> tuple[PlayerVsAiState, str | None]:
    """Grades a pending prompt against the linked trade's real realized
    P&L and records the round. Returns (state, error) — error is set (and
    nothing changes) if the prompt id is unknown or already consumed."""
    pending = _pending.pop(prompt_id, None)
    if pending is None:
        return state, "That round has expired or was already answered — request a new one."

    prompt, decision, trade = pending
    ground_truth_choice: SignalChoice = "enter" if trade.pnl > 0 else "avoid"
    ai_correct = trade.pnl > 0  # the AI did enter (that's how this round became eligible); was it right to?
    player_correct = (player_choice == "enter") == (ground_truth_choice == "enter")

    round_ = PlayerVsAiRound(
        id=f"{prompt_id}-round",
        decisionId=decision.id,
        symbol=prompt.symbol,
        category=prompt.category,
        regime=prompt.regime,
        playerChoice=player_choice,
        aiChoice="enter",
        realizedPnlPct=trade.pnl_pct,
        groundTruthChoice=ground_truth_choice,
        playerCorrect=player_correct,
        aiCorrect=ai_correct,
        createdAt=_now_iso(),
    )
    rounds = [*state.rounds, round_][-MAX_ROUNDS:]
    new_state = state.model_copy(
        update={
            "rounds": rounds,
            "player_correct_count": state.player_correct_count + (1 if player_correct else 0),
            "ai_correct_count": state.ai_correct_count + (1 if ai_correct else 0),
            "total_count": state.total_count + 1,
        }
    )
    return new_state, None
