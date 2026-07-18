"""PerformanceManager — computes TradeTown's seven-metric CompanyScore
(v0.5 brief, Feature 6). Every sub-metric is a small, named, documented
formula rather than a black-box rating — consistent with
docs/DESIGN_BIBLE.md's "Transparency Over Automation" pillar. `overall`
is a plain mean of the seven; there is no hidden weighting.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.analytics import research_accuracy, win_rate
from app.schemas import CompanyScore, MemoryRecord, PaperPortfolio, ResearchItem, SimulationResult

# Memory categories that represent distilled knowledge rather than raw
# activity logs — see app/knowledge.py.
_KNOWLEDGE_CATEGORIES = ("lesson", "mistake", "strategy")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _team_coordination(agent_moods: list[float]) -> float:
    """Proxy: average mood across the roster. Mood is already a real,
    tracked per-agent number (see app/nexus.py's _tick_agent), so this
    reuses it rather than inventing a second wellbeing metric."""
    if not agent_moods:
        return 50.0
    return sum(agent_moods) / len(agent_moods)


def _knowledge_growth(memory: list[MemoryRecord]) -> float:
    knowledge_records = sum(1 for m in memory if m.category in _KNOWLEDGE_CATEGORIES)
    return min(100.0, knowledge_records * 2.0)


def _simulation_success(results: list[SimulationResult]) -> float:
    if not results:
        return 50.0
    recent = results[-10:]
    return sum(r.win_rate for r in recent) / len(recent)


def _risk_management(portfolio: PaperPortfolio) -> float:
    """100 minus a simple drawdown + concentration penalty — not a real
    VaR/risk model (see docs/KNOWN_LIMITATIONS.md)."""
    drawdown_penalty = max(0.0, -portfolio.total_pnl_pct) * 2.0
    concentration_penalty = len(portfolio.positions) * 5.0
    return max(0.0, 100.0 - drawdown_penalty - concentration_penalty)


def _paper_trading_performance(portfolio: PaperPortfolio) -> float:
    return max(0.0, min(100.0, 50.0 + portfolio.total_pnl_pct * 2.0))


def compute_company_score(
    research: list[ResearchItem],
    portfolio: PaperPortfolio,
    memory: list[MemoryRecord],
    simulation_results: list[SimulationResult],
    agent_moods: list[float],
) -> CompanyScore:
    research_quality = research_accuracy(research)
    decision_quality = win_rate(portfolio.win_count, portfolio.loss_count)
    risk_management = _risk_management(portfolio)
    paper_trading_performance = _paper_trading_performance(portfolio)
    team_coordination = _team_coordination(agent_moods)
    knowledge_growth = _knowledge_growth(memory)
    simulation_success = _simulation_success(simulation_results)

    metrics = [
        research_quality,
        decision_quality,
        risk_management,
        paper_trading_performance,
        team_coordination,
        knowledge_growth,
        simulation_success,
    ]
    overall = sum(metrics) / len(metrics)

    return CompanyScore(
        overall=round(overall, 1),
        researchQuality=round(research_quality, 1),
        decisionQuality=round(decision_quality, 1),
        riskManagement=round(risk_management, 1),
        paperTradingPerformance=round(paper_trading_performance, 1),
        teamCoordination=round(team_coordination, 1),
        knowledgeGrowth=round(knowledge_growth, 1),
        simulationSuccess=round(simulation_success, 1),
        updatedAt=_now_iso(),
    )
