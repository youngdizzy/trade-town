"""app/sandbox.py — v0.7 Feature 45, the Research Sandbox.

GOAL (from the brief): no strategy should ever enter live trading
without earning the company's trust through a real, gated pipeline —
Idea -> Research -> Historical Backtest -> Market Simulation -> Paper
Trading -> Limited Live Capital -> Company Review -> Approved Strategy.

Researched first. This codebase already had almost every real building
block the brief asks for, just not stage-gated or reported on:

  Idea / Strategy object     - already real (app/simulation.py's
                                `Strategy`, shipped in v0.5).
  Research                   - already real (`ResearchItem`, scoped by
                                the exact same `ResearchCategory` a
                                Strategy's own `focus_category` uses).
  Historical Backtest /
  Market Simulation          - one real engine (`app/simulation.py`'s
                                explicitly-placeholder backtest math, see
                                that module's own docstring) now made
                                Testing-Environment-aware: a `scenario`
                                field reuses the exact same 5 regime
                                names `app/market_environment.py` already
                                computes live (bull/bear/sideways/
                                high_volatility/low_volatility), plus
                                "historical" (the pre-Feature-45 default)
                                and "custom" (a CEO-tunable deterministic
                                bias on the same placeholder ranges —
                                never an independently invented range).
                                "Earnings weeks" and "economic news" from
                                the brief's longer Testing Environments
                                list are NOT built: no earnings calendar
                                or economic-event data source exists
                                anywhere in this codebase (confirmed by
                                grep — app/calendar.py's own
                                `systemEvents` never included either).
  Performance Metrics         - `SimulationResult` already had Win Rate/
                                Max Drawdown/Sharpe/Sortino/Avg Return
                                (as total_return_pct); this feature adds
                                win_count/loss_count/avg_win_pct/
                                avg_loss_pct as the placeholder engine's
                                own real *generating* inputs (see
                                app/simulation.py — total_return_pct is
                                now derived FROM them, not the reverse),
                                so Expected Value/Profit Factor/Risk-
                                Reward below are real, internally-
                                consistent derivations of a run's own
                                numbers, never independently rolled.
                                "Consistency" and "Trade Frequency" are
                                left as frontend derivations over a
                                strategy's own stored SimulationResult
                                history (see lib/derive.ts) rather than
                                stored per-run, since both are properties
                                of the *history*, not of one run.

What's genuinely new here:

  Stage gating                - `Strategy.stage` (8 real values) only
                                ever advances forward (see `_advance`
                                below), each transition backed by a real
                                signal: research needs a completed real
                                ResearchItem in the strategy's own
                                category; historical_backtest/
                                market_simulation need a real completed
                                SimulationResult in the matching
                                scenario bucket; paper_trading/
                                limited_live_capital/company_review are
                                real CEO-authorized actions (this
                                codebase's live/paper trading engine is
                                symbol- and AI-Debate-driven, not
                                Strategy-driven — there is no mechanism
                                anywhere in this codebase to attribute a
                                real executed trade back to a specific
                                Strategy object, and building one would
                                be a structural rewrite of the whole
                                decision loop, not a Feature-45-sized
                                change. Rather than fabricate that
                                linkage, these later stages are real,
                                CEO-authorized trust checkpoints: a
                                tracked, bounded `allocated_capital`
                                ceiling — a real number the CEO chose,
                                never wired into fabricated live P&L).
  StrategyReport               - auto-generated on every completed
                                SimulationResult (Executive Summary/
                                Strengths/Weaknesses/Failure Conditions/
                                Best Market Environment/Recommended
                                Improvements), the exact same templated-
                                framing-over-real-numbers discipline
                                app/mistakes.py and app/successes.py
                                already established.
  StrategyReview                - the Company Review stage's five real
                                reviewer verdicts (Quant/Risk Specialist/
                                Technical Analyst/Fundamental Analyst/
                                Devil's Advocate), each computed from
                                that strategy's own real, aggregated
                                SimulationResult + ResearchItem history —
                                the same real-threshold-citation
                                discipline app/devils_advocate.py already
                                established for individual trades,
                                applied here to a strategy as a whole.
                                Quant = Vector (Chief Quantitative
                                Strategist), Risk = Guardian (Portfolio
                                Protection), Technical = Echo (Technical
                                Analyst), Fundamental = Nova (Research
                                Analyst, the same agent who authored the
                                seeded "Value Fundamentals" strategy) —
                                every mapping is that agent's own real
                                occupation, never arbitrary. The Devil's
                                Advocate seat rotates through a small
                                pool distinct from the other four
                                reviewers, mirroring
                                app/devils_advocate.py's own rotation
                                convention.
  Automation Mode integration  - the brief's "CEO approves deployment
                                (depending on Automation Mode)" reuses
                                app/nexus.py's existing
                                `_apply_operating_mode` convention
                                exactly: Learning Mode always waits for a
                                real manual CEO decision; Assisted/
                                Executive Mode auto-resolve a filed
                                StrategyReview using the review's own
                                real overall_verdict, tagged
                                resolved_by="auto" for honest provenance
                                (see app/nexus.py's tick()).

Explicitly NOT built, and why:
  Per-strategy live P&L attribution - see "Stage gating" above; this
                                       codebase's live trading loop has
                                       no Strategy-scoped execution path.
  Earnings weeks / economic news
  Testing Environments              - no real data source anywhere in
                                       this codebase (see above).
  A second, independent backtest
  engine for "Market Simulation"    - would be the same class of
                                       redundant re-measurement this
                                       session's whole discipline exists
                                       to avoid; one real engine,
                                       scenario-parameterized, serves
                                       both Historical Backtest and
                                       Market Simulation stages honestly.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.schemas import (
    AgentId,
    ResearchItem,
    SimulationResult,
    Strategy,
    StrategyReport,
    StrategyReview,
    StrategyReviewVerdict,
    StrategyStage,
    StrategyStageEvent,
    StrategyVerdict,
)

MAX_STRATEGY_REPORTS = 60
MAX_STRATEGY_REVIEWS = 30
MAX_LIMITED_LIVE_CAPITAL = 2000.0
MIN_PAPER_TRIAL_SIM_DAYS = 1

QUANT_MIN_SAMPLE_SIZE = 3
QUANT_MIN_AVG_WIN_RATE = 50.0
QUANT_MIN_AVG_SHARPE = 1.0
RISK_MAX_AVG_DRAWDOWN = 20.0
DEVILS_ADVOCATE_MAX_SINGLE_DRAWDOWN = 25.0

# Distinct from the four fixed reviewer seats (quant/guardian/echo/nova)
# so no agent appears twice in the same StrategyReview — mirrors
# app/devils_advocate.py's own ELIGIBLE_DEVILS_ADVOCATES rotation.
STRATEGY_DEVILS_ADVOCATES: tuple[AgentId, ...] = ("scribe", "coach", "cio", "sage")

STAGE_ORDER: tuple[StrategyStage, ...] = (
    "idea",
    "research",
    "historical_backtest",
    "market_simulation",
    "paper_trading",
    "limited_live_capital",
    "company_review",
    "approved",
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def stage_index(stage: StrategyStage) -> int:
    return STAGE_ORDER.index(stage)


def _advance(strategy: Strategy, new_stage: StrategyStage, detail: str, sim_day: int) -> Strategy:
    """Strategies cannot skip stages, and a stage transition never fires
    twice or moves backward — see this module's docstring."""
    if stage_index(new_stage) <= stage_index(strategy.stage):
        return strategy
    event = StrategyStageEvent(id=f"stage-{strategy.id}-{new_stage}", stage=new_stage, detail=detail, simDay=sim_day, createdAt=_now_iso())
    return strategy.model_copy(update={"stage": new_stage, "stage_history": [*strategy.stage_history, event]})


def maybe_advance_after_research(strategy: Strategy, research_items: list[ResearchItem], sim_day: int) -> Strategy:
    if strategy.stage != "idea":
        return strategy
    matches = [r for r in research_items if r.category == strategy.focus_category and r.status == "completed"]
    if not matches:
        return strategy
    return _advance(strategy, "research", f"{len(matches)} completed research item(s) in {strategy.focus_category} back this idea.", sim_day)


def maybe_advance_after_result(strategy: Strategy, result: SimulationResult, sim_day: int) -> Strategy:
    """Historical Backtest is always the first real evidence a strategy
    earns; Market Simulation (any non-"historical" scenario) only counts
    once Historical Backtest is already on record — cannot skip stages."""
    if result.scenario == "historical" and stage_index(strategy.stage) < stage_index("historical_backtest"):
        return _advance(strategy, "historical_backtest", f"Historical backtest completed: {result.total_return_pct:+.1f}% return, {result.win_rate:.0f}% win rate over {result.trade_count} trades.", sim_day)
    if result.scenario != "historical" and stage_index(strategy.stage) == stage_index("historical_backtest"):
        label = result.scenario.replace("_", " ").title()
        return _advance(strategy, "market_simulation", f"{label} scenario simulation completed: {result.total_return_pct:+.1f}% return, {result.max_drawdown_pct:.1f}% max drawdown.", sim_day)
    return strategy


def evaluate_risk_gate(strategy: Strategy, results: list[SimulationResult]) -> tuple[bool, str]:
    """v0.7 Feature 52 (Part 1) — Guardian's own real average-drawdown
    threshold, checked as its own standalone gate before Paper Trading —
    honors the Strategy Validation Laboratory's brief's own stage order
    (Risk Analysis before Paper Trading). Does not replace the richer
    five-reviewer StrategyReview risk verdict `_risk_verdict` still runs
    later at Company Review; this is an earlier, narrower real
    checkpoint reusing the exact same real threshold."""
    strategy_results = [r for r in results if r.strategy_id == strategy.id]
    if not strategy_results:
        return False, "Risk Department has no completed Market Simulation runs yet to evaluate."
    avg_drawdown = sum(r.max_drawdown_pct for r in strategy_results) / len(strategy_results)
    if avg_drawdown > RISK_MAX_AVG_DRAWDOWN:
        return False, f"Risk Department rejects Paper Trading: average max drawdown {avg_drawdown:.1f}% exceeds the {RISK_MAX_AVG_DRAWDOWN:.0f}% comfort bar across {len(strategy_results)} real run(s)."
    return True, f"Risk Department approves Paper Trading: average max drawdown {avg_drawdown:.1f}% is within bounds across {len(strategy_results)} real run(s)."


def begin_paper_trial(strategy: Strategy, results: list[SimulationResult], sim_day: int) -> tuple[Strategy | None, str | None]:
    if strategy.stage != "market_simulation":
        return None, f'"{strategy.name}" must complete Market Simulation before Paper Trading (currently: {strategy.stage.replace("_", " ")}).'
    risk_approved, risk_detail = evaluate_risk_gate(strategy, results)
    if not risk_approved:
        return None, risk_detail
    return _advance(strategy, "paper_trading", f"CEO authorized a real paper trading trial. {risk_detail}", sim_day), None


def begin_limited_live(strategy: Strategy, amount: float, sim_day: int) -> tuple[Strategy | None, str | None]:
    if strategy.stage != "paper_trading":
        return None, f'"{strategy.name}" must complete a Paper Trading trial before Limited Live Capital (currently: {strategy.stage.replace("_", " ")}).'
    trial_start = next((e for e in strategy.stage_history if e.stage == "paper_trading"), None)
    if trial_start is not None and sim_day - trial_start.sim_day < MIN_PAPER_TRIAL_SIM_DAYS:
        return None, f"The Paper Trading trial needs at least {MIN_PAPER_TRIAL_SIM_DAYS} full in-game day of real observation first."
    if amount <= 0:
        return None, "Allocated capital must be positive."
    if amount > MAX_LIMITED_LIVE_CAPITAL:
        return None, f"Can't allocate more than ${MAX_LIMITED_LIVE_CAPITAL:,.0f} to a strategy still in Limited Live Capital."
    strategy = strategy.model_copy(update={"allocated_capital": amount})
    return _advance(strategy, "limited_live_capital", f"CEO allocated ${amount:,.0f} in limited live capital.", sim_day), None


def _quant_verdict(results: list[SimulationResult]) -> StrategyReviewVerdict:
    if len(results) < QUANT_MIN_SAMPLE_SIZE:
        return StrategyReviewVerdict(reviewerRole="quant", reviewerAgent="quant", verdict="concern", summary=f"Only {len(results)} completed run(s) on record — fewer than the {QUANT_MIN_SAMPLE_SIZE} Quant wants before trusting the statistics.")
    avg_win_rate = sum(r.win_rate for r in results) / len(results)
    avg_sharpe = sum(r.sharpe_ratio for r in results) / len(results)
    if avg_win_rate >= QUANT_MIN_AVG_WIN_RATE and avg_sharpe >= QUANT_MIN_AVG_SHARPE:
        return StrategyReviewVerdict(reviewerRole="quant", reviewerAgent="quant", verdict="pass", summary=f"{len(results)} runs, {avg_win_rate:.0f}% average win rate, {avg_sharpe:.2f} average Sharpe — the statistics hold up.")
    return StrategyReviewVerdict(reviewerRole="quant", reviewerAgent="quant", verdict="fail" if avg_win_rate < 40.0 else "concern", summary=f"{len(results)} runs, {avg_win_rate:.0f}% average win rate, {avg_sharpe:.2f} average Sharpe — below the {QUANT_MIN_AVG_WIN_RATE:.0f}%/{QUANT_MIN_AVG_SHARPE:.1f} bar.")


def _risk_verdict(results: list[SimulationResult], allocated_capital: float) -> StrategyReviewVerdict:
    avg_drawdown = sum(r.max_drawdown_pct for r in results) / len(results) if results else 0.0
    if avg_drawdown <= RISK_MAX_AVG_DRAWDOWN:
        return StrategyReviewVerdict(reviewerRole="risk", reviewerAgent="guardian", verdict="pass", summary=f"Average max drawdown {avg_drawdown:.1f}% across {len(results)} run(s), ${allocated_capital:,.0f} at risk — exposure is within bounds.")
    return StrategyReviewVerdict(reviewerRole="risk", reviewerAgent="guardian", verdict="fail" if avg_drawdown > 30.0 else "concern", summary=f"Average max drawdown {avg_drawdown:.1f}% exceeds the {RISK_MAX_AVG_DRAWDOWN:.0f}% comfort bar — exposure needs a second look before more capital moves.")


def _technical_verdict(results: list[SimulationResult]) -> StrategyReviewVerdict:
    scenarios = {r.scenario for r in results}
    if not scenarios:
        return StrategyReviewVerdict(reviewerRole="technical", reviewerAgent="echo", verdict="concern", summary="No completed runs on record yet — nothing to stress-test the technical setup against.")
    if len(scenarios) >= 2:
        return StrategyReviewVerdict(reviewerRole="technical", reviewerAgent="echo", verdict="pass", summary=f"Tested across {len(scenarios)} distinct Testing Environments ({', '.join(sorted(scenarios))}) — the technical setup has been stressed, not just curve-fit to one regime.")
    return StrategyReviewVerdict(reviewerRole="technical", reviewerAgent="echo", verdict="concern", summary=f"Only tested under the \"{next(iter(scenarios))}\" scenario so far — no evidence yet of how the technical setup holds up outside it.")


def _fundamental_verdict(strategy: Strategy, research_items: list[ResearchItem]) -> StrategyReviewVerdict:
    matches = [r for r in research_items if r.category == strategy.focus_category and r.status == "completed"]
    if matches:
        return StrategyReviewVerdict(reviewerRole="fundamental", reviewerAgent="nova", verdict="pass", summary=f"{len(matches)} completed research item(s) in {strategy.focus_category} back the strategy's own assumptions.")
    return StrategyReviewVerdict(reviewerRole="fundamental", reviewerAgent="nova", verdict="concern", summary=f"No completed research on record for {strategy.focus_category} — the strategy's assumptions haven't been independently checked.")


def _devils_advocate_verdict(strategy: Strategy, results: list[SimulationResult], existing_review_count: int) -> StrategyReviewVerdict:
    assigned = STRATEGY_DEVILS_ADVOCATES[existing_review_count % len(STRATEGY_DEVILS_ADVOCATES)]
    worst = max(results, key=lambda r: r.max_drawdown_pct) if results else None
    losers = [r for r in results if r.expected_value_pct < 0]
    if worst is None:
        return StrategyReviewVerdict(reviewerRole="devils_advocate", reviewerAgent=assigned, verdict="concern", summary="No completed runs to attack yet — nothing to find a weakness in.")
    if worst.max_drawdown_pct > DEVILS_ADVOCATE_MAX_SINGLE_DRAWDOWN or losers:
        detail = f"worst single run drew down {worst.max_drawdown_pct:.1f}% ({worst.scenario})" if worst.max_drawdown_pct > DEVILS_ADVOCATE_MAX_SINGLE_DRAWDOWN else f"{len(losers)} of {len(results)} run(s) show a negative expected value per trade"
        return StrategyReviewVerdict(reviewerRole="devils_advocate", reviewerAgent=assigned, verdict="concern", summary=f"Real weakness found: {detail}. Worth resolving before more capital is committed.")
    return StrategyReviewVerdict(reviewerRole="devils_advocate", reviewerAgent=assigned, verdict="pass", summary=f"Tried to break it across {len(results)} run(s) (worst drawdown {worst.max_drawdown_pct:.1f}%) and found no disqualifying weakness.")


def generate_strategy_review(strategy: Strategy, results: list[SimulationResult], research_items: list[ResearchItem], existing_review_count: int, *, sim_day: int) -> StrategyReview:
    strategy_results = [r for r in results if r.strategy_id == strategy.id]
    verdicts = [
        _quant_verdict(strategy_results),
        _risk_verdict(strategy_results, strategy.allocated_capital),
        _technical_verdict(strategy_results),
        _fundamental_verdict(strategy, research_items),
        _devils_advocate_verdict(strategy, strategy_results, existing_review_count),
    ]
    if any(v.verdict == "fail" for v in verdicts):
        overall: StrategyVerdict = "fail"
    elif any(v.verdict == "concern" for v in verdicts):
        overall = "concern"
    else:
        overall = "pass"
    return StrategyReview(
        id=f"review-{strategy.id}-{existing_review_count}",
        strategyId=strategy.id,
        strategyName=strategy.name,
        verdicts=verdicts,
        overallVerdict=overall,
        ceoDecision="pending",
        simDay=sim_day,
        createdAt=_now_iso(),
    )


_WIN_RATE_TIER = (
    (65.0, "a strong win rate"),
    (50.0, "a middling win rate"),
    (0.0, "a weak win rate"),
)
_SHARPE_TIER = (
    (1.5, "excellent risk-adjusted return"),
    (0.5, "modest risk-adjusted return"),
    (float("-inf"), "poor risk-adjusted return"),
)


def _tier(value: float, table: tuple[tuple[float, str], ...]) -> str:
    return next(label for threshold, label in table if value >= threshold)


def generate_strategy_report(strategy: Strategy, result: SimulationResult, *, sim_day: int) -> StrategyReport:
    """Auto-generated the moment a SimulationResult completes — every
    field is a templated read of that one real result's own numbers, the
    same discipline app/mistakes.py/successes.py already established."""
    win_tier = _tier(result.win_rate, _WIN_RATE_TIER)
    sharpe_tier = _tier(result.sharpe_ratio, _SHARPE_TIER)
    scenario_label = result.scenario.replace("_", " ").title()

    strengths: list[str] = []
    weaknesses: list[str] = []
    failure_conditions: list[str] = []

    if result.win_rate >= 55.0:
        strengths.append(f"Win rate held at {result.win_rate:.0f}% across {result.trade_count} trades under the {scenario_label} scenario.")
    else:
        weaknesses.append(f"Win rate was only {result.win_rate:.0f}% under the {scenario_label} scenario.")

    if result.profit_factor >= 1.5:
        strengths.append(f"Profit factor of {result.profit_factor:.2f} — gross profit comfortably covers gross loss.")
    elif result.profit_factor < 1.0:
        weaknesses.append(f"Profit factor of {result.profit_factor:.2f} — losses outweigh gains at this sample size.")
        failure_conditions.append(f"Under {scenario_label} conditions, losing trades ({result.loss_count} of {result.trade_count}) outpace winners in size.")

    if result.max_drawdown_pct > 20.0:
        weaknesses.append(f"Max drawdown reached {result.max_drawdown_pct:.1f}% — a real risk of a rough stretch under this scenario.")
        failure_conditions.append(f"A run of losing trades under {scenario_label} conditions can draw the strategy down {result.max_drawdown_pct:.1f}% before recovering.")
    else:
        strengths.append(f"Max drawdown stayed contained at {result.max_drawdown_pct:.1f}%.")

    executive_summary = (
        f'"{strategy.name}" under the {scenario_label} scenario returned {result.total_return_pct:+.1f}% over {result.trade_count} trades '
        f"({win_tier}, {sharpe_tier} at {result.sharpe_ratio:.2f} Sharpe). Expected value per trade: {result.expected_value_pct:+.2f}%."
    )

    recommended_improvements: list[str] = []
    if result.profit_factor < 1.5:
        recommended_improvements.append("Tighten entry criteria to raise the average win size relative to the average loss.")
    if result.max_drawdown_pct > 15.0:
        recommended_improvements.append("Test a reduced position size against the same scenario to see if drawdown comes down proportionally.")
    if not recommended_improvements:
        recommended_improvements.append("Run this strategy against at least one more Testing Environment before Company Review to confirm the result generalizes.")

    return StrategyReport(
        id=f"report-{result.id}",
        strategyId=strategy.id,
        strategyName=strategy.name,
        sourceResultId=result.id,
        scenario=result.scenario,
        executiveSummary=executive_summary,
        strengths=strengths or ["No standout strengths yet — results are still early."],
        weaknesses=weaknesses or ["No significant weaknesses found in this run."],
        failureConditions=failure_conditions,
        bestMarketEnvironment=f"{scenario_label} (based on this run — re-test other scenarios to compare)." if result.total_return_pct > 0 else f"Not yet {scenario_label} — this run lost money under this scenario.",
        recommendedImprovements=recommended_improvements,
        simDay=sim_day,
        createdAt=_now_iso(),
    )


def begin_company_review(strategy: Strategy, sim_day: int) -> tuple[Strategy | None, str | None]:
    if strategy.stage != "limited_live_capital":
        return None, f'"{strategy.name}" must complete Limited Live Capital before Company Review (currently: {strategy.stage.replace("_", " ")}).'
    return _advance(strategy, "company_review", "CEO requested a full Company Review.", sim_day), None


def apply_review_decision(strategy: Strategy, review: StrategyReview, approve: bool, sim_day: int) -> Strategy:
    """The final stage transition. Approval moves the strategy to
    "approved" — the pipeline's terminal, earned-trust state. Rejection
    sends it back to "limited_live_capital" rather than discarding all
    its progress: the strategy keeps every real stage it already earned
    and can request another Company Review once it has more evidence."""
    if not approve:
        return strategy.model_copy(update={"stage": "limited_live_capital", "stage_history": [*strategy.stage_history, StrategyStageEvent(id=f"stage-{strategy.id}-rejected-{review.id}", stage="limited_live_capital", detail=f"Company Review rejected ({review.overall_verdict}) — sent back for more evidence.", simDay=sim_day, createdAt=_now_iso())]})
    return _advance(strategy, "approved", f"Company Review passed ({review.overall_verdict}) — approved for full deployment.", sim_day)


def cap_strategy_reports(reports: list[StrategyReport]) -> list[StrategyReport]:
    if len(reports) > MAX_STRATEGY_REPORTS:
        del reports[: len(reports) - MAX_STRATEGY_REPORTS]
    return reports


def cap_strategy_reviews(reviews: list[StrategyReview]) -> list[StrategyReview]:
    if len(reviews) > MAX_STRATEGY_REVIEWS:
        del reviews[: len(reviews) - MAX_STRATEGY_REVIEWS]
    return reviews
