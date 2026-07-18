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
from app.schemas import AgentId, AgentScore, CoachReport, CompanyScore, PaperPortfolio, ReportPeriod, ResearchItem, TimeState

MAX_COACH_REPORTS = 20


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _risk_score(portfolio: PaperPortfolio) -> float:
    """0-100, higher = riskier — a simple concentration + drawdown proxy,
    not a real risk model (see docs/KNOWN_LIMITATIONS.md)."""
    concentration = len(portfolio.positions) * 10.0
    drawdown = max(0.0, -portfolio.total_pnl_pct) * 2.0
    return min(100.0, concentration + drawdown)


def _common_mistakes(portfolio: PaperPortfolio) -> list[str]:
    losses = [t for t in portfolio.trade_history if t.pnl <= 0]
    if not losses:
        return ["No losing paper trades recorded yet."]
    mistakes: list[str] = []
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
) -> CoachReport:
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
        commonMistakes=_common_mistakes(portfolio),
        recommendations=_recommendations(wr, ca, ra),
        createdAt=_now_iso(),
    )


def record_report(reports: list[CoachReport], report: CoachReport) -> list[CoachReport]:
    updated = [*reports, report]
    if len(updated) > MAX_COACH_REPORTS:
        del updated[: len(updated) - MAX_COACH_REPORTS]
    return updated
