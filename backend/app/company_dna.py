"""CompanyDNA — v0.7 Feature 43, the Executive Intelligence Dashboard's
one genuinely net-new concept (see the brief's own overlap research: every
other item in its "Company Health" list already existed here under a
different name).

Five real, descriptive behavioral traits read off the company's own
historical decision/trade record — never predictive, never a fabricated
personality quiz. Each trait has an honest neutral (50.0) default and a
real `sampleSize` until enough history exists to say anything real about
it, the same "don't dress up thin data as a confident reading" convention
`app/coach.py`/`app/mentor.py` already established elsewhere.

  Risk Appetite        - % of executed trades taken on a confidence
                          reading of "moderate" or weaker (the Decision
                          Confidence Engine's own real tier) rather than a
                          strong/elite signal.
  Patience              - average real PaperTrade hold duration against
                          discipline.py's own PATIENCE_TARGET_MINUTES
                          bar — the same real yardstick the Discipline
                          Chamber already uses per trade, applied here as
                          a company-wide average.
  Contrarian Tendency    - % of CeoDecisionRecords where the CEO's real
                          choice disagreed with the AI's recommendation
                          (`agreedWithAi == false`).
  Research Rigor         - average real Decision Confidence Engine score
                          across every graded decision.
  Collaboration Style    - % of decisions where the six analysts cast at
                          least two distinct real vote choices — genuine
                          independent thinking rather than rubber-
                          stamping.

Deliberately distinct from `app/company_health.py`'s `team_chemistry`
(a real support-vs-challenge ratio across recent AI Debates specifically)
and from `app/company_score.py`'s `team_coordination` (a proxy off raw
agent mood) — no trait here reuses either of those signals.

v0.7 Feature 48 — the Company DNA System adds two real, additive pieces
on top of the five traits above, without touching their own tested
formulas or documented meaning:

  Company Identity  - a pure, deterministic label (`classify_identity`)
                      read off the five trait scores that already exist
                      — zero new data, just an honest name for a
                      combination of real numbers. "Not Yet Established"
                      until `sampleSize` is real.
  Legacy            - a small, permanent, capped delta layered on top of
                      the fresh historical-average score (never mixed
                      into the average itself, so the five formulas'
                      documented meaning never changes). Nudged by
                      exactly four real, one-time or rare company events
                      this codebase already tracks: a ratified Black Box
                      breakthrough and a completed Academy project each
                      nudge `research_rigor` up (real completed research
                      effort); a filed `disciplined_process` success
                      study nudges `risk_appetite` down and a filed
                      `patient_execution` success study nudges `patience`
                      up (each one records real behavior that already
                      happened — never a prediction of future behavior);
                      the Founders' one-time, permanent "Legendary
                      Status" retirement (Feature 39) nudges both
                      `risk_appetite` down and `research_rigor` up at
                      once, since Keystone (risk) and Compass (learning)
                      retire together. See `nexus.py`'s `tick()` for
                      exactly where each hook fires.

  Explicit scope cut: this codebase is single-tenant (one company, one
  save slot — see `state.py`'s and `save_modules.py`'s own module
  docstrings), so the brief's "no two companies should think exactly
  alike" and any recruitment/cross-company comparison have no real
  mechanism to attach to and are not built.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.discipline import PATIENCE_TARGET_MINUTES
from app.schemas import CeoDecisionRecord, CompanyDNA, CompanyDnaTrait, PaperTrade, TradeDecision

TRAIT_LABELS: dict[str, str] = {
    "risk_appetite": "Risk Appetite",
    "patience": "Patience",
    "contrarian_tendency": "Contrarian Tendency",
    "research_rigor": "Research Rigor",
    "collaboration_style": "Collaboration Style",
}

# v0.7 Feature 48 — Legacy nudges are small and capped so DNA "changes
# slowly": no single real event can move a trait by more than this many
# points, cumulative, in either direction.
LEGACY_DELTA_CAP = 15.0
BLACK_BOX_BREAKTHROUGH_NUDGE = 2.0
ACADEMY_COMPLETION_NUDGE = 0.5
SUCCESS_STUDY_NUDGE = 1.0
FOUNDER_RETIREMENT_NUDGE = 3.0


def nudge_legacy(deltas: dict[str, float], trait_id: str, amount: float) -> dict[str, float]:
    """Applies one small, permanent, capped nudge to `trait_id`'s Legacy
    delta — a real, one-time company event's lasting mark, layered on top
    of (never mixed into) the five traits' own fresh historical-average
    computation below."""
    updated = dict(deltas)
    current = updated.get(trait_id, 0.0)
    updated[trait_id] = max(-LEGACY_DELTA_CAP, min(LEGACY_DELTA_CAP, current + amount))
    return updated


def classify_identity(traits: list[CompanyDnaTrait], sample_size: int) -> str:
    """A pure, deterministic label read off the five real trait scores —
    zero new data, checked in a fixed priority order so exactly one label
    always applies. Never predictive: describes what the track record
    already shows, the same "descriptive, not predictive" rule the five
    traits themselves follow."""
    if sample_size == 0:
        return "Not Yet Established"

    by_id = {t.id: t.score for t in traits}
    risk_appetite = by_id.get("risk_appetite", 50.0)
    patience = by_id.get("patience", 50.0)
    contrarian_tendency = by_id.get("contrarian_tendency", 50.0)
    research_rigor = by_id.get("research_rigor", 50.0)
    collaboration_style = by_id.get("collaboration_style", 50.0)

    if risk_appetite <= 25.0 and patience >= 60.0:
        return "Ultra Conservative"
    if research_rigor >= 75.0:
        return "Research Driven"
    if patience >= 70.0 and risk_appetite <= 40.0:
        return "Highly Disciplined"
    if contrarian_tendency >= 65.0:
        return "Independent Thinker"
    if collaboration_style >= 70.0:
        return "Collaborative Culture"
    if risk_appetite >= 65.0:
        return "Aggressive Risk-Taker"
    return "Balanced Operator"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _risk_appetite(decisions: list[TradeDecision]) -> tuple[float, int, str]:
    traded = [d for d in decisions if d.outcome == "trade" and d.confidence_engine is not None]
    if not traded:
        return 50.0, 0, "No executed trades with a Decision Confidence Engine reading yet."
    risky = sum(1 for d in traded if d.confidence_engine is not None and d.confidence_engine.tier in ("moderate", "weak", "poor"))
    score = risky / len(traded) * 100.0
    return score, len(traded), f"{risky} of {len(traded)} executed trade(s) were taken on a moderate-or-weaker confidence reading."


def _patience(trades: list[PaperTrade]) -> tuple[float, int, str]:
    if not trades:
        return 50.0, 0, "No closed trades yet."
    avg = sum(t.duration_minutes for t in trades) / len(trades)
    score = min(100.0, avg / PATIENCE_TARGET_MINUTES * 100.0)
    return score, len(trades), f"Average real hold time is {avg:.0f} simulated minutes, against the Discipline Chamber's {PATIENCE_TARGET_MINUTES}-minute patient-hold bar."


def _contrarian_tendency(records: list[CeoDecisionRecord]) -> tuple[float, int, str]:
    if not records:
        return 50.0, 0, "No resolved executive decisions yet."
    overrides = sum(1 for r in records if not r.agreed_with_ai)
    score = overrides / len(records) * 100.0
    return score, len(records), f"The CEO overrode the AI's own recommendation on {overrides} of {len(records)} resolved decision(s)."


def _research_rigor(decisions: list[TradeDecision]) -> tuple[float, int, str]:
    scored = [d.confidence_engine.score for d in decisions if d.confidence_engine is not None]
    if not scored:
        return 50.0, 0, "No decisions with a Decision Confidence Engine reading yet."
    avg = sum(scored) / len(scored)
    return avg, len(scored), f"Average Decision Confidence Engine score across {len(scored)} decision(s): {avg:.0f}/100."


def _collaboration_style(decisions: list[TradeDecision]) -> tuple[float, int, str]:
    if not decisions:
        return 50.0, 0, "No decisions on record yet."
    diverse = sum(1 for d in decisions if len({v.choice for v in d.votes}) >= 2)
    score = diverse / len(decisions) * 100.0
    return score, len(decisions), f"{diverse} of {len(decisions)} decision(s) had at least two distinct real analyst positions on the table."


def _with_legacy(trait_id: str, name: str, base_score: float, sample_size: int, detail: str, legacy_deltas: dict[str, float]) -> CompanyDnaTrait:
    delta = legacy_deltas.get(trait_id, 0.0)
    final_score = max(0.0, min(100.0, base_score + delta))
    if delta != 0.0 and sample_size > 0:
        detail = f"{detail} Includes a permanent Legacy nudge of {delta:+.1f} from real company milestones."
    return CompanyDnaTrait(id=trait_id, name=name, score=round(final_score, 1), detail=detail)


def compute_company_dna(
    decisions: list[TradeDecision],
    trades: list[PaperTrade],
    ceo_decisions: list[CeoDecisionRecord],
    legacy_deltas: dict[str, float] | None = None,
) -> CompanyDNA:
    legacy_deltas = legacy_deltas or {}
    risk_appetite, risk_n, risk_detail = _risk_appetite(decisions)
    patience, patience_n, patience_detail = _patience(trades)
    contrarian, contrarian_n, contrarian_detail = _contrarian_tendency(ceo_decisions)
    rigor, rigor_n, rigor_detail = _research_rigor(decisions)
    collaboration, collab_n, collab_detail = _collaboration_style(decisions)

    traits = [
        _with_legacy("risk_appetite", TRAIT_LABELS["risk_appetite"], risk_appetite, risk_n, risk_detail, legacy_deltas),
        _with_legacy("patience", TRAIT_LABELS["patience"], patience, patience_n, patience_detail, legacy_deltas),
        _with_legacy("contrarian_tendency", TRAIT_LABELS["contrarian_tendency"], contrarian, contrarian_n, contrarian_detail, legacy_deltas),
        _with_legacy("research_rigor", TRAIT_LABELS["research_rigor"], rigor, rigor_n, rigor_detail, legacy_deltas),
        _with_legacy("collaboration_style", TRAIT_LABELS["collaboration_style"], collaboration, collab_n, collab_detail, legacy_deltas),
    ]
    sample_size = max(risk_n, patience_n, contrarian_n, rigor_n, collab_n)

    if sample_size == 0:
        summary = "Not enough history yet to describe this company's real behavioral traits — check back after a few trades have closed."
    else:
        extreme = sorted(traits, key=lambda t: t.score)
        lowest, highest = extreme[0], extreme[-1]
        summary = f"This company's real track record reads highest on {highest.name} ({highest.score:.0f}/100) and lowest on {lowest.name} ({lowest.score:.0f}/100)."

    identity = classify_identity(traits, sample_size)

    return CompanyDNA(traits=traits, summary=summary, identity=identity, sampleSize=sample_size, updatedAt=_now_iso())
