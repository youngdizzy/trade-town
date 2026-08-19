"""CEO directive "Professional Trading Firm — Market-Analysis Knowledge
+ Session Intelligence Expansion," Phase 6 — the Confluence Engine.

RESEARCH FIRST (per the directive's own mandatory rule, and its own
explicit warning against exactly this anti-pattern — "RSI says buy +
MACD says buy + MA says buy = 3 confirmations" when the underlying
signals aren't genuinely independent): a full audit of every one of the
six real analyst votes app/executive.py's `generate_analyst_votes()`
produces found they are NOT all mutually independent:

  - `technical` (Echo) is real and independent: a real trend/volatility
    read over the symbol's own real (mock) candles.
  - `risk` (Sentinel) is real and independent: a real `RiskWarning` from
    app/risk_engine.py.
  - `sentiment` (Pulse) is real and independent: a real `ScannerAlert`
    from app/scanner.py.
  - `news` (Scout) and `macro` (Nova) are NOT mutually independent:
    app/voting.py's `researcher_vote()` is called for both, and for
    either one, when it isn't the research item's originating agent,
    the vote is a probability-weighted random roll keyed ENTIRELY off
    the same single number — `ResearchItem.confidence` — the same real
    random-walk gauge app/research.py's own module docstring already
    discloses ("not derived from any real analysis"). Two independent
    dice rolls conditioned on the identical input are not two
    independent pieces of evidence; they are the same evidence, counted
    twice. (When one of the two IS the originating agent, its vote is
    deterministically "buy" — a real attribution artifact, not new
    evidence either.)
  - `execution` (Atlas) is not independent at all: app/executive.py's
    `_execution_vote()` docstring already states this plainly — "not a
    fabricated sixth signal — majority of the other five." It contributes
    zero new information to a confluence count.

ALSO RESEARCHED, AND DELIBERATELY NOT DUPLICATED: `app/process_
adherence.py` already considered and explicitly rejected a "confluence
requirements" checklist — but that was a PLANNED-vs-ACTUAL plan-
adherence check (did this trade follow its own pre-declared entry
conditions), which this codebase has no order-plan infrastructure to
honestly support. This module is a different, narrower, honestly-
buildable thing: real-time independence reasoning over the CURRENT
proposal's already-real evidence, never a plan-adherence audit.

THE METRIC: `independent_evidence_count` (see ConfluenceRead's own
schema docstring) is real and mechanical — it is never a claim that
fewer confirmations means a worse setup, only an honest count of how
much of the naive tally is actually new information. This module does
not gate, veto, or adjust anything in the real Gatekeeper/Risk/Model
Validation pipeline — it is a new, additional, informational read,
computed fresh, never persisted.
"""
from __future__ import annotations

from app.schemas import AnalystRole, AnalystVote, ConfluenceRead, CorrelatedSignalPair

# The real correlation this module's own audit found — see module
# docstring. A frozenset pair, since correlation is symmetric.
_CORRELATED_ROLE_PAIRS: tuple[tuple[AnalystRole, AnalystRole, str], ...] = (
    (
        "news",
        "macro",
        "Both news and macro votes are driven by the same underlying ResearchItem.confidence value via the same "
        "probabilistic mechanism (app/voting.py's researcher_vote()) — the same evidence, expressed twice, not two "
        "independent reads.",
    ),
)

# execution's vote is a majority synthesis of the other five
# (app/executive.py's _execution_vote()) — it never counts as
# independent evidence, and is excluded from both counts entirely
# rather than folded into a correlated pair (it isn't correlated with
# any ONE other vote, it's derived from all of them).
_NON_INDEPENDENT_ROLES = frozenset({"execution"})


def assess_confluence(votes: list[AnalystVote], overall_recommendation: str) -> ConfluenceRead:
    agreeing = [v for v in votes if v.choice == overall_recommendation]
    naive_count = len(agreeing)

    independent_roles: set[str] = set()
    correlated_pairs: list[CorrelatedSignalPair] = []
    agreeing_roles = {v.role for v in agreeing}
    for role_a, role_b, reason in _CORRELATED_ROLE_PAIRS:
        if role_a in agreeing_roles and role_b in agreeing_roles:
            correlated_pairs.append(CorrelatedSignalPair(roleA=role_a, roleB=role_b, reason=reason))

    counted_correlated_groups: set[frozenset[str]] = set()
    for vote in agreeing:
        if vote.role in _NON_INDEPENDENT_ROLES:
            continue
        group = next((frozenset((a, b)) for a, b, _ in _CORRELATED_ROLE_PAIRS if vote.role in (a, b) and a in agreeing_roles and b in agreeing_roles), None)
        if group is not None:
            if group in counted_correlated_groups:
                continue
            counted_correlated_groups.add(group)
            independent_roles.add(f"correlated:{'+'.join(sorted(group))}")
        else:
            independent_roles.add(vote.role)

    independent_count = len(independent_roles)
    if independent_count == naive_count:
        detail = f"{naive_count} vote(s) agree with {overall_recommendation.upper()}, and all {independent_count} are genuinely independent evidence."
    else:
        detail = (
            f"{naive_count} vote(s) agree with {overall_recommendation.upper()}, but only {independent_count} real independent "
            f"evidence source(s) back it — see correlatedPairs for which votes share an underlying signal or contribute no new evidence."
        )
    return ConfluenceRead(
        naiveConfirmationCount=naive_count,
        independentEvidenceCount=independent_count,
        correlatedPairs=correlated_pairs,
        detail=detail,
    )
