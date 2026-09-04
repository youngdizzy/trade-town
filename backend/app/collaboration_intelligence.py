""""TradeTown — Department Debate & Collaboration Intelligence 1.0."

Phase 0 forensic audit for this directive (four parallel Learning
Organization 1.0 research passes plus a dedicated fifth pass this
milestone) found the "candidate → department opinions → disagreement →
challenge → synthesis" loop already ~90% real and built, just never
exposed as one addressable read:

- `app/executive_intelligence.py::ExecutiveMeetingLogEntry` is already
  the real, permanent (capped `MAX_MEETING_LOG_ENTRIES=200`), decision-
  time (never trade-closure-gated) record of one real Executive
  Intelligence Network synthesis: real `DepartmentOpinion`s (role,
  agent_id, stance, summary, confidence_pct, evidence, concerns,
  benefits — app/schemas.py's own docstring: "Populated from each
  department's own already-real inputs... never fabricated"), the
  network's real recommended action + reason, the CEO's real decision,
  and whether the two agreed — generated once per real
  `resolve_proposal()` call (buy, sell, OR wait), never gated behind
  that trade eventually closing.
- Genuine department-level disagreement is ALREADY computed from real
  `ExecutiveStance` values (agree/disagree/request_more_research/
  recommend_waiting/recommend_position_change/recommend_rejecting) —
  never from a raw confidence-number difference — by
  `compute_executive_recommendation()`'s own `supporting`/`opposing`
  split and `consensus_pct` (share of departments that plainly AGREE,
  a deliberately different real number from average confidence). This
  module never recomputes that split from scratch; `distinct_stance_
  count` below reads the exact same real `stance` field.
- `_build_disagreement_summary()` (`app/executive_intelligence.py`) is
  already a real, generated (never fabricated) narrative naming every
  real opposing/hedging department and its own real reason. Reused here
  verbatim, not reimplemented.
- Real challenge/rebuttal already exists via `app/devils_advocate.py`'s
  `ChallengeReport` (severity/hidden_risks/weak_assumptions/missing_
  evidence/historical_comparisons/final_recommendation), joined to its
  `ExecutiveMeetingLogEntry` by the same real `proposal_id` both already
  carry.
- Knowledge application (a documented Institutional Memory lesson
  actually cited during a live challenge) is already wired — see
  app/knowledge_sharing.py's `record_knowledge_application_from_
  challenge()`, built in "Learning Organization 1.0" and unchanged here.

What was genuinely missing, and is genuinely new in this module:

1. Real cross-department EVIDENCE REUSE detection — nothing in this
   codebase previously checked whether one department's real evidence
   bullets showed up, reworded or not, in another department's own real
   evidence. `_evidence_overlap_pairs()` below is the one new piece of
   detection logic this milestone adds, and it reuses
   app/constitution.py's own `_significant_words()` word-overlap
   primitive (already reused cross-module by
   app/institutional_memory.py's `find_related_memory()`) rather than
   inventing a second text-similarity heuristic.
2. One computed-fresh join (`build_collaboration_case_summary()`) that
   answers the directive's own explicit synthesis questions — which
   departments contributed, where they agreed/disagreed, what evidence
   was considered, what challenge was raised, whether it changed the
   conclusion — over already-permanent state. Deliberately NOT a new
   persisted record: every input already lives somewhere permanent
   (`ExecutiveMeetingLogEntry`, `ChallengeReport`), matching this
   codebase's own `ExecutiveRecommendation`/`compute_executive_
   accuracy_scores()` "computed fresh, never a second driftable copy"
   convention — zero new persistence, zero migration risk.
3. A real, disclosed, bounded collaboration-case score
   (`average_collaboration_case_score()`) that reuses two formula
   shapes already established elsewhere in this codebase rather than
   inventing a new weighting scheme: app/discipline.py's own 3-tier
   `viewpoint_diversity` threshold (>=3/2/1 distinct real stances ->
   100/65/35), plus a small capped bonus in the same shape as its own
   `assumptions_challenged` factor (`min(100, count*40)`) for real
   cross-department evidence reuse.

Explicitly NOT built here, and why: no new persisted event log
(`COLLABORATION_CASE_OPENED` etc.) — everything below is computed fresh
from data this codebase already persists permanently, which is a
strictly safer design than a parallel event store (no new migration
surface, no double-counting risk, no drift between two copies of the
same fact). No second opinion/debate/challenge/synthesis engine — this
module only ever reads `ExecutiveMeetingLogEntry`/`ChallengeReport`,
never constructs its own. "Research Council" (app/research_council.py)
is a real but entirely unrelated existing system (Strategy Factory
candidate research, not trade-candidate department opinions) — this
milestone does not touch it and does not reuse that name, to avoid the
naming collision the Phase 0 audit found.
"""
from __future__ import annotations

from app.constitution import _significant_words
from app.executive_intelligence import _build_disagreement_summary
from app.schemas import ChallengeReport, CollaborationCaseSummary, DepartmentOpinion, ExecutiveMeetingLogEntry

# Evidence bullets are short, structured phrases (not full paragraphs),
# so this module tunes its own real-word-overlap thresholds separately
# from app/institutional_memory.py's MIN_SHARED_WORDS_FOR_RELATION/
# RELATION_WORD_OVERLAP_THRESHOLD (tuned for much longer observation/
# lesson text) — a disclosed, this-module-only research assumption, the
# same provenance discipline that module's own threshold table already
# uses.
MIN_SHARED_WORDS_FOR_EVIDENCE_REUSE = 2
EVIDENCE_REUSE_WORD_OVERLAP_THRESHOLD = 0.4

# Small, capped bonus per real evidence-reuse pair found — same
# disclosed-assumption shape as app/discipline.py's own
# assumptions_challenged factor (min(100, challenge_turns * 40)).
EVIDENCE_REUSE_BONUS_PER_PAIR = 10.0
MAX_EVIDENCE_REUSE_BONUS = 20.0


def _evidence_overlap_pairs(opinions: list[DepartmentOpinion]) -> list[tuple[str, str]]:
    """Real cross-department evidence reuse: significant-word overlap
    between two DIFFERENT departments' own real `evidence` bullets
    (never their free-text `summary`, which shares far more incidental
    phrasing and would false-positive constantly). Self-pairs (same
    role) are never counted; an opinion with no real evidence bullets
    contributes no pairs. Order is insertion order over `opinions`, each
    unordered pair reported once."""
    pairs: list[tuple[str, str]] = []
    word_sets = [(o.role, _significant_words(" ".join(o.evidence))) for o in opinions]
    for i, (role_a, words_a) in enumerate(word_sets):
        if not words_a:
            continue
        for role_b, words_b in word_sets[i + 1 :]:
            if role_b == role_a or not words_b:
                continue
            shared = words_a & words_b
            if len(shared) < MIN_SHARED_WORDS_FOR_EVIDENCE_REUSE:
                continue
            overlap = len(shared) / min(len(words_a), len(words_b))
            if overlap >= EVIDENCE_REUSE_WORD_OVERLAP_THRESHOLD:
                pairs.append((role_a, role_b))
    return pairs


def build_collaboration_case_summary(
    entry: ExecutiveMeetingLogEntry,
    challenge_report: ChallengeReport | None,
) -> CollaborationCaseSummary:
    """One real collaboration case per real `ExecutiveMeetingLogEntry` —
    `challenge_report` is the real `ChallengeReport` sharing the same
    `proposal_id`, if the caller found one, or `None` when this
    candidate never got one (a real, honest absence, never fabricated)."""
    distinct_stances = len({o.stance for o in entry.opinions})
    evidence_pairs = _evidence_overlap_pairs(entry.opinions)
    consensus_summary = (
        _build_disagreement_summary(entry.opinions) if entry.opinions else "No department opinions were recorded for this case."
    )
    challenge_heeded = challenge_report is not None and challenge_report.severity != "none_found" and entry.recommended_action != "trade_normally"
    return CollaborationCaseSummary(
        id=f"collab-{entry.proposal_id}",
        proposalId=entry.proposal_id,
        symbol=entry.symbol,
        simDay=entry.sim_day,
        departmentCount=len(entry.opinions),
        distinctStanceCount=distinct_stances,
        consensusSummary=consensus_summary,
        evidenceReuseCount=len(evidence_pairs),
        evidenceReusePairs=[f"{a}->{b}" for a, b in evidence_pairs],
        challengeSeverity=challenge_report.severity if challenge_report is not None else None,
        challengeHeeded=challenge_heeded,
        recommendedAction=entry.recommended_action,
        ceoDecision=entry.ceo_decision,
        networkAgreed=entry.network_agreed,
        createdAt=entry.created_at,
    )


def compute_collaboration_case_summaries(
    meeting_log: list[ExecutiveMeetingLogEntry],
    challenge_reports: list[ChallengeReport],
) -> list[CollaborationCaseSummary]:
    """Computed fresh over already-permanent state every call — never a
    second persisted copy of `meeting_log`/`challenge_reports`."""
    challenge_by_proposal = {c.proposal_id: c for c in challenge_reports}
    return [build_collaboration_case_summary(entry, challenge_by_proposal.get(entry.proposal_id)) for entry in meeting_log]


def _collaboration_case_score(summary: CollaborationCaseSummary) -> float:
    if summary.department_count == 0:
        return 0.0
    base = 100.0 if summary.distinct_stance_count >= 3 else 65.0 if summary.distinct_stance_count == 2 else 35.0
    bonus = min(MAX_EVIDENCE_REUSE_BONUS, summary.evidence_reuse_count * EVIDENCE_REUSE_BONUS_PER_PAIR)
    return min(100.0, base + bonus)


def average_collaboration_case_score(summaries: list[CollaborationCaseSummary]) -> float | None:
    """`None` — NOT ENOUGH EVIDENCE — when there are no real
    collaboration cases yet, never a forced weak answer."""
    if not summaries:
        return None
    return round(sum(_collaboration_case_score(s) for s in summaries) / len(summaries), 1)
