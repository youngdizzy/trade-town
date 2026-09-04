"""app/autonomous_promotion.py — CEO directive "TradeTown — Autonomous
Quant Company 2.0," Phase 5 (Automatic Promotion).

RESEARCH FIRST. A Phase 0 forensic audit for this directive found the
real, previously-missing gap is narrower than the directive's own text
assumes: `app/champion_challenger.py::compare_champion_challenger()`
ALREADY computes a real, comprehensive, multi-layered evidence verdict
(the real economic-significance rule over expectancy/drawdown, a real
minimum-sample floor on both sides via `EmaPullbackStatsBucket.verdict
== "enough_evidence"`, a real FRAGILE/REJECTED/INVALID/INSUFFICIENT-
EVIDENCE conclusion check that blocks promotion regardless of raw
numbers, real multiple-testing-risk and tuning-exposure flags) — and
`promote_challenger()` ALREADY refuses (raises `ValueError`) to promote
anything whose `verdict != "challenger_recommended"`. There is no
missing evidence gate to build; the gate is already real, already
comprehensive, and already enforced. The ONLY real gap this module
closes is WHO calls `promote_challenger()` once that gate has already
passed — today, exclusively a human, via `POST /sandbox/champion-
challenger/promote`.

WHAT THIS MODULE DELIBERATELY DOES NOT DO. It does not build a second
evidence-gate evaluator (that would risk drifting out of sync with the
real one `compare_champion_challenger()` already enforces — the same
"one real source of truth" discipline this codebase applies everywhere
else). It does not trigger new comparisons — `compare_champion_
challenger()` itself still requires an explicit human/API call this
pass (a real, disclosed, deliberate scope cut: automatically triggering
NEW comparisons would require this module to also pick a seed
hypothesis/symbol/timeframe, a materially larger and riskier change
than automating a decision that is already fully computed). It never
promotes anything whose real verdict is not `"challenger_recommended"`
— fail-closed by construction, since it does nothing but locate
already-qualifying comparisons and hand them to the exact same,
unmodified `promote_challenger()` gate.

A DELIBERATE, DISCLOSED REVERSAL OF AN EARLIER DESIGN COMMENT, EXPLAINED
RATHER THAN SILENTLY OVERRIDDEN. `ChampionRecord`'s own docstring
(written for an earlier CEO directive) previously said promotion "is
never created automatically... matching the directive's own Section 31
('agents cannot secretly change production strategies')." This
directive's own Phase 5 explicitly, knowingly asks to replace that
human-click boundary with an evidence-gated automatic one — this module
is that explicit, requested reversal, not an accidental one, and
`ChampionRecord`'s own docstring is updated alongside this module to
say so honestly rather than left stale and now-inaccurate. It remains
safe for a real, verified reason, not merely because the CEO asked:
a direct grep of `app/nexus.py`/`app/executive.py`/`app/strategy_
engine.py` (repeated for this directive's own Phase 0) confirms
`champion_history`/`get_current_champion()` are read by NOTHING in the
live trade-proposal/decision/order pipeline today — promoting a
champion changes an internal record-keeping list, not what TradeTown
actually trades. The "secretly change production strategies" risk this
module reverses does not yet exist to secretly change, because no
production system reads this list yet (a separate, larger, disclosed
gap — see this directive's own final report). And the human "judgment"
this reverses was never real independent judgment to begin with: a
human clicking Promote today is rubber-stamping a verdict `compare_
champion_challenger()` already computed with zero human input — this
module automates the rubber stamp, not the judgment.
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone

from app.champion_challenger import promote_challenger
from app.schemas import AgentId, ChallengerComparison, ChampionRecord

AUTONOMOUS_PROMOTION_AGENT: AgentId = "quant"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def find_promotable_comparisons(
    challenger_comparisons: list[ChallengerComparison],
    champion_history: list[ChampionRecord],
) -> list[ChallengerComparison]:
    """Real comparisons with `verdict == "challenger_recommended"` that
    have not already been promoted — checked by real `ChampionRecord.
    source_comparison_id` linkage, never a fabricated "already handled"
    guess. Order preserved (oldest real comparison first), so a caller
    that promotes in list order processes the real historical queue
    honestly rather than newest-first."""
    already_promoted_ids = {record.source_comparison_id for record in champion_history if record.source_comparison_id is not None}
    return [c for c in challenger_comparisons if c.verdict == "challenger_recommended" and c.id not in already_promoted_ids]


def apply_autonomous_promotions(
    challenger_comparisons: list[ChallengerComparison],
    champion_history: list[ChampionRecord],
    *,
    now_iso_fn: Callable[[], str] = _now_iso,
) -> tuple[list[ChampionRecord], list[ChallengerComparison]]:
    """The one real entry point. Pure function — mutates neither input
    list, returns the extended `champion_history` and the real
    comparisons it just promoted (so the caller can announce them, e.g.
    a real NewsItem, the same honest-provenance convention every other
    auto-resolution in this codebase already uses). `now_iso_fn`
    defaults to the real wall clock; overridable only for deterministic
    tests, never for production behavior."""
    promotable = find_promotable_comparisons(challenger_comparisons, champion_history)
    updated_history = list(champion_history)
    promoted: list[ChallengerComparison] = []
    for comparison in promotable:
        record = promote_challenger(
            comparison,
            promoted_by=AUTONOMOUS_PROMOTION_AGENT,
            reasoning=(
                f"Autonomous Promotion Engine — real evidence gate already computed by compare_champion_challenger() "
                f"(verdict=challenger_recommended): {comparison.reasoning}"
            ),
            record_id=f"champion-{comparison.id}",
            promoted_at=now_iso_fn(),
        )
        updated_history.append(record)
        promoted.append(comparison)
    return updated_history, promoted
