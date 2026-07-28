"""CoachManager — Coach (the agent)'s reporting logic. Coach only ever
evaluates: every function in this module reads research/paper-trading
state and produces a report; nothing here opens, closes, sizes, or
otherwise touches a position (that's app/paper_trading.py's job, and
Coach is deliberately excluded from RESEARCHER_IDS in app/research.py
the same way Scribe is).
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.analytics import average_confidence, confidence_accuracy, research_accuracy, win_rate
from app.schemas import AgentId, AgentScore, CeoDecisionRecord, CoachReport, CompanyScore, PaperPortfolio, ReportPeriod, ResearchItem, TimeState, TradeDecision

MAX_COACH_REPORTS = 20


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _risk_score(portfolio: PaperPortfolio) -> float:
    """0-100, higher = riskier — a simple concentration + drawdown proxy,
    not a real risk model (see docs/KNOWN_LIMITATIONS.md)."""
    concentration = len(portfolio.positions) * 10.0
    drawdown = max(0.0, -portfolio.total_pnl_pct) * 2.0
    return min(100.0, concentration + drawdown)


def _override_mistakes(ceo_decisions: list[CeoDecisionRecord], decisions: list[TradeDecision]) -> list[str]:
    """v0.7 Feature 18 — recurring-mistake patterns that need the CEO's
    own real decisions joined against the six-analyst TradeDecision that
    produced them (by decision_id), not just the closed PaperTrade alone.
    Only ever counts a decision that both went against a specific
    analyst's real vote (via TradeDecision.opposing_agents, populated in
    app/executive.py's resolve_proposal) *and* whose real linked trade
    actually lost (CeoDecisionRecord.outcome == "incorrect") — never a
    guess about what an unrealized or never-placed trade "would have"
    done, the same honesty boundary grade_ceo_decisions already applies."""
    decisions_by_id = {d.id: d for d in decisions}
    risk_overrides = 0
    trend_overrides = 0
    news_overrides = 0
    for record in ceo_decisions:
        if record.outcome != "incorrect" or record.decision_id is None:
            continue
        decision = decisions_by_id.get(record.decision_id)
        if decision is None:
            continue
        if "sentinel" in decision.opposing_agents:
            risk_overrides += 1
        if "echo" in decision.opposing_agents:
            trend_overrides += 1
        if "scout" in decision.opposing_agents:
            news_overrides += 1
    mistakes: list[str] = []
    if risk_overrides:
        mistakes.append(f"{risk_overrides} losing trade(s) overrode Sentinel's risk warning — overriding the Risk Manager is costing real P&L.")
    if trend_overrides:
        mistakes.append(f"{trend_overrides} losing trade(s) went against Echo's technical trend read — trading against the trend didn't pay off here.")
    if news_overrides:
        mistakes.append(f"{news_overrides} losing trade(s) went against Scout's news read — worth weighing news coverage more before overriding it.")
    return mistakes


def _common_mistakes(portfolio: PaperPortfolio, ceo_decisions: list[CeoDecisionRecord], decisions: list[TradeDecision]) -> list[str]:
    losses = [t for t in portfolio.trade_history if t.pnl <= 0]
    mistakes = _override_mistakes(ceo_decisions, decisions)
    if not losses:
        if not mistakes:
            mistakes.append("No losing paper trades recorded yet.")
        return mistakes
    overconfident = [t for t in losses if t.confidence >= 80]
    if overconfident:
        mistakes.append(
            f"{len(overconfident)} loss(es) came from positions opened at 80%+ confidence — "
            "confidence isn't translating to accuracy on those calls."
        )
    quick_losses = [t for t in losses if t.duration_minutes < 180]
    if quick_losses:
        mistakes.append(
            f"{len(quick_losses)} loss(es) closed within a 3-hour simulated hold — "
            "consider whether the minimum hold window lets a thesis play out."
        )
    if not mistakes:
        mistakes.append("Losses are spread evenly with no single dominant pattern yet.")
    return mistakes


def _strengths(portfolio: PaperPortfolio, decisions: list[TradeDecision], win_rate_value: float) -> list[str]:
    """v0.7 Feature 18 — the positive counterpart to _common_mistakes,
    same honesty rule: every strength here is a real, counted pattern
    over actually-closed trades, never a fabricated "great job" filler."""
    wins = [t for t in portfolio.trade_history if t.pnl > 0]
    losses = [t for t in portfolio.trade_history if t.pnl < 0]
    decisions_by_id = {d.id: d for d in decisions}
    strengths: list[str] = []

    if len(portfolio.trade_history) >= 5 and win_rate_value >= 60:
        strengths.append(f"Win rate is {win_rate_value:.0f}% over {len(portfolio.trade_history)} closed trades — consistent discipline is paying off.")

    patient_wins = [t for t in wins if t.duration_minutes >= 240]
    if patient_wins:
        strengths.append(f"{len(patient_wins)} winning trade(s) held 4+ simulated hours before closing — excellent patience letting a thesis play out.")

    trend_aligned_wins = 0
    for t in wins:
        decision = decisions_by_id.get(t.decision_id) if t.decision_id else None
        if decision and "echo" in decision.supporting_agents:
            trend_aligned_wins += 1
    if trend_aligned_wins:
        strengths.append(f"{trend_aligned_wins} winning trade(s) agreed with Echo's technical trend read — good trend recognition.")

    if wins and losses:
        avg_win_pct = sum(t.pnl_pct for t in wins) / len(wins)
        avg_loss_pct = abs(sum(t.pnl_pct for t in losses) / len(losses))
        if avg_win_pct > avg_loss_pct * 1.2:
            strengths.append(f"Average win ({avg_win_pct:.1f}%) outweighs average loss ({avg_loss_pct:.1f}%) — strong reward-to-risk discipline.")

    if not strengths:
        strengths.append("No standout strengths flagged yet — keep trading to build a track record.")
    return strengths


def _recommendations(win_rate_value: float, confidence_accuracy_value: float, research_accuracy_value: float) -> list[str]:
    recs: list[str] = []
    if win_rate_value < 50:
        recs.append("Win rate is below 50% — consider raising the confidence threshold before opening a paper position.")
    if confidence_accuracy_value < 50:
        recs.append("Confidence isn't tracking outcomes well — treat high-confidence research with more scrutiny before acting on it.")
    if research_accuracy_value < 50:
        recs.append("Fewer than half of completed research items land above 70% confidence — consider deeper research passes before closing items out.")
    if not recs:
        recs.append("No systemic issues detected this period — maintain current research and risk discipline.")
    return recs


def generate_report(
    period: ReportPeriod,
    research: list[ResearchItem],
    portfolio: PaperPortfolio,
    company_score: CompanyScore,
    researcher_ids: tuple[AgentId, ...],
    new_time: TimeState,
    *,
    ceo_decisions: list[CeoDecisionRecord] | None = None,
    decisions: list[TradeDecision] | None = None,
) -> CoachReport:
    ceo_decisions = ceo_decisions or []
    decisions = decisions or []
    rankings: list[AgentScore] = []
    for agent_id in researcher_ids:
        agent_research = [r for r in research if r.assigned_agent == agent_id and r.status == "completed"]
        agent_trades = [t for t in portfolio.trade_history if agent_id in t.supporting_agents]
        accuracy = research_accuracy(agent_research)
        calibration = confidence_accuracy(agent_trades)
        rankings.append(
            AgentScore(
                agentId=agent_id,
                score=round((accuracy + calibration) / 2, 1),
                researchAccuracy=round(accuracy, 1),
                confidenceCalibration=round(calibration, 1),
            )
        )
    rankings.sort(key=lambda a: a.score, reverse=True)

    wr = win_rate(portfolio.win_count, portfolio.loss_count)
    ca = confidence_accuracy(portfolio.trade_history)
    ra = research_accuracy(research)
    total_trades = portfolio.win_count + portfolio.loss_count

    return CoachReport(
        id=f"report-{period}-{new_time.day}-{new_time.hour}-{new_time.minute}",
        period=period,
        companyScore=company_score.overall,
        agentRankings=rankings,
        researchAccuracy=round(ra, 1),
        winRate=round(wr, 1),
        lossRate=round(100.0 - wr, 1) if total_trades else 0.0,
        averageConfidence=round(average_confidence(research), 1),
        riskScore=round(_risk_score(portfolio), 1),
        commonMistakes=_common_mistakes(portfolio, ceo_decisions, decisions),
        strengths=_strengths(portfolio, decisions, wr),
        recommendations=_recommendations(wr, ca, ra),
        createdAt=_now_iso(),
    )


def record_report(reports: list[CoachReport], report: CoachReport) -> list[CoachReport]:
    updated = [*reports, report]
    if len(updated) > MAX_COACH_REPORTS:
        del updated[: len(updated) - MAX_COACH_REPORTS]
    return updated
