"""TalentDiscovery — v0.7 Feature 44, the Talent Discovery System.

Scoped hard against this codebase's fixed-roster architecture
(app/founders.py's module docstring: "no new-hire system... no employee
ever joins the company after the game starts... nothing to onboard" —
the same boundary that rules out any real role-change mechanism).
`AgentProfile` is `@dataclass(frozen=True)` (app/agents.py); no agent's
occupation, schedule, or room ever changes anywhere in this codebase,
confirmed by grep. This rules out the brief's entire "Career
Development" section (Technical Analyst -> Quantitative Researcher,
etc.) and most of "CEO Decision" (Cross-train/Transfer Departments would
require exactly that) — deliberately not built here, not even as flavor
text implying a mechanic that doesn't exist.

What's real:

  Performance Analysis - already fully real, under different names:
                          app/mentor.py's ThinkingProfile (6 per-agent
                          traits: curiosity, evidence_quality,
                          open_mindedness, humility, reasoning,
                          collaboration) and app/coach.py's AgentScore
                          (researchAccuracy, confidenceCalibration).
                          Surfaced together on the frontend Talent tab —
                          no new backend computation needed for this
                          section.
  Discovery Events      - genuinely new: generate_talent_reports()
                          below, a real evidence-based threshold check
                          (mirrors app/devils_advocate.py's "one
                          specific real signal, cited, never fabricated"
                          convention) over an agent's current
                          ThinkingProfile plus their real score history
                          across recent CoachReports — "reviewed the
                          last N Coach Reports" is real; the brief's own
                          "reviewed the last 45 trading days" phrasing
                          would require daily per-agent snapshots this
                          codebase doesn't keep, and isn't claimed here.
  CEO Decision           - real "seen" tracking (mirrors
                          app/black_box.py's mark_breakthrough_viewed)
                          is the only real mechanic offered: acknowledge
                          or ignore. "Keep current role"/"cross-train"/
                          "transfer departments"/"assign mentor" are
                          each either a no-op dressed up as a choice or
                          would require touching the frozen roster — not
                          offered.
  Growth History         - reconstructed entirely in the frontend from
                          real, already-timestamped per-agent
                          participation records this codebase already
                          keeps (DisciplineReview.attendees,
                          ReasoningChallenge.contributions,
                          ReflectionSession.insights,
                          ChallengeReport.assignedAgent, Black Box team
                          membership, CoachReport.agentRankings) — see
                          frontend/.../lib/derive.ts's
                          computeGrowthHistory(). No new backend state.
  Career Development     - cut entirely (see above).
  Team Optimization      - cut, with one exception: "better research
                          partners" is answerable from real data
                          (DebateTurn.respondingTo already records who
                          responded to whom, and with what stance) — see
                          the frontend's computeBestCollaborators().
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.agents import AGENT_PROFILES
from app.schemas import AgentId, CoachReport, TalentReport, ThinkingProfile

MAX_TALENT_REPORTS = 30
MAX_VIEWED_TALENT_REPORT_IDS = 60
# A trait must read at or above this to be worth surfacing at all.
TALENT_SCORE_THRESHOLD = 80.0
# How many of the company's most recent Coach Reports "reviewed the
# track record" checks against — real, bounded evidence, not an
# unfulfillable claim about calendar days.
CONSISTENCY_REPORT_WINDOW = 3
CONSISTENCY_MIN_SCORE = 70.0

_TRAIT_NARRATIVE: dict[str, str] = {
    "curiosity": "a real appetite for self-directed learning",
    "evidence_quality": "unusually deep, well-sourced research",
    "open_mindedness": "a real willingness to entertain more than one real thesis at once",
    "humility": "honest, well-calibrated acknowledgment of real uncertainty",
    "reasoning": "rigorous, evidence-driven reasoning under real scrutiny",
    "collaboration": "genuine cross-team collaboration",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _best_trait(profile: ThinkingProfile):
    if not profile.traits:
        return None
    return max(profile.traits, key=lambda t: t.score)


def _score_history(agent_id: AgentId, coach_reports: list[CoachReport]) -> list[float]:
    return [row.score for report in coach_reports for row in report.agent_rankings if row.agent_id == agent_id]


def generate_talent_reports(
    agent_ids: tuple[AgentId, ...],
    thinking_profiles: dict[AgentId, ThinkingProfile],
    coach_reports: list[CoachReport],
    existing_report_ids: set[str],
    *,
    sim_day: int,
) -> list[TalentReport]:
    """Only ever files a report once per agent per trait (existing_report_ids
    guards against re-filing the same discovery every tick) — a real,
    permanent record the same way a Black Box breakthrough is, not a
    recurring notification."""
    new_reports: list[TalentReport] = []
    for agent_id in agent_ids:
        profile = thinking_profiles.get(agent_id)
        if profile is None:
            continue
        best = _best_trait(profile)
        if best is None or best.score < TALENT_SCORE_THRESHOLD:
            continue

        history = _score_history(agent_id, coach_reports)
        if len(history) < CONSISTENCY_REPORT_WINDOW:
            continue
        recent = history[-CONSISTENCY_REPORT_WINDOW:]
        if any(score < CONSISTENCY_MIN_SCORE for score in recent):
            continue

        report_id = f"talent-{agent_id}-{best.id}"
        if report_id in existing_report_ids:
            continue

        name = AGENT_PROFILES[agent_id].name
        narrative_phrase = _TRAIT_NARRATIVE.get(best.id, best.name.lower())
        new_reports.append(
            TalentReport(
                id=report_id,
                agentId=agent_id,
                traitId=best.id,
                traitName=best.name,
                title=f"{name} shows exceptional {best.name}",
                narrative=(
                    f"I believe {name} has demonstrated {narrative_phrase} after reviewing the last "
                    f"{len(recent)} Coach Reports — {best.name} currently reads {best.score:.0f}/100."
                ),
                evidence=[best.detail],
                examples=[f"Coach Report score: {score:.0f}/100" for score in recent],
                currentScore=best.score,
                sampleSize=len(recent),
                suggestedFocus=(
                    f"No formal role change occurs — TradeTown's roster is fixed. The honest next step is to keep "
                    f"leaning on {name}'s {best.name.lower()} where the company already puts it to work."
                ),
                expectedBenefits=f"Continued {best.name.lower()} at this level keeps compounding the same real signal that surfaced it — no new mechanic is introduced by this recommendation.",
                simDay=sim_day,
                createdAt=_now_iso(),
            )
        )
    return new_reports


def record_talent_reports(reports: list[TalentReport], new_reports: list[TalentReport]) -> list[TalentReport]:
    updated = [*reports, *new_reports]
    if len(updated) > MAX_TALENT_REPORTS:
        del updated[: len(updated) - MAX_TALENT_REPORTS]
    return updated


def mark_talent_report_viewed(viewed_ids: list[str], report_id: str) -> list[str]:
    if report_id in viewed_ids:
        return viewed_ids
    updated = [*viewed_ids, report_id]
    if len(updated) > MAX_VIEWED_TALENT_REPORT_IDS:
        del updated[: len(updated) - MAX_VIEWED_TALENT_REPORT_IDS]
    return updated
