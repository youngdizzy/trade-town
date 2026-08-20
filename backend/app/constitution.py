"""app/constitution.py — v0.7 Feature 46, the Company Constitution.

GOAL (from the brief): a permanent rulebook that "influences every
department and every major decision throughout the company's lifetime,"
not a static text page nobody ever reads.

Researched first. Two halves, two very different builds:

  The Articles themselves    - genuinely new: no rule-of-conduct concept
                                existed anywhere in this codebase before
                                this feature. `default_constitution()`
                                seeds the brief's own 8 example Articles
                                verbatim, permanent from game start.
  "Live Enforcement"          - the brief's real ask: "Coach quotes it,
                                Founders teach it, Academy explains it,
                                Risk Department enforces it, Devil's
                                Advocate references it." Built as a real,
                                permanent `ConstitutionCitation` log fed
                                by hooks at five real event points this
                                codebase already has (app/nexus.py's
                                tick()) — a case study/success study
                                being filed, a Devil's Advocate
                                ChallengeReport being filed, a new
                                critical RiskWarning appearing, an
                                Academy project completing, a Founder
                                Council monthly session, and a weekly/
                                monthly CoachReport carrying real
                                commonMistakes. Every citation traces to
                                one specific real event that just
                                happened and names the specific real
                                Article that event's own detected pattern
                                maps to (see `MISTAKE_ARTICLE_MAP` below)
                                — never a fabricated quote attributed to
                                nobody, and never a citation with no real
                                trigger.

  "No revenge trading" (Article V) deliberately gets exactly one real
  trigger — CaseStudyCategory's own `acted_too_quickly` (a trade closed
  inside `QUICK_CLOSE_MINUTES`, and its positive inversion
  `patient_execution`) — rather than a second, independently-invented
  "revenge trading" detector; this codebase has no real signal for
  literally re-entering a position out of anger after a loss, and
  building one would mean inventing behavior-classification
  infrastructure this session's whole discipline exists to avoid.

Articles IX-XIII — the Probability First Trading Philosophy. Not a
feature: a permanent foundational principle documented in full in
docs/DESIGN_BIBLE.md's "Probability First Trading Philosophy" section,
seeded here verbatim exactly like Articles I-VIII, so every department,
strategy, simulation, and future feature inherits it automatically
without ever needing to redefine it. Deliberately scoped to the
Articles themselves — no new "Live Enforcement" citation hooks were
added for IX-XIII (that would be new detection engineering, which is
explicitly out of scope for a documentation-driven addition); the
existing six hooks above continue to cite only I-VIII, since those are
the only Articles with a real, already-existing detector behind them.

Article XIV — the CEO Company Health + Live Market Realism directive's
Section 25 decision principle ("TradeTown optimizes for statistically
validated expected value and long-term survival, not simply win rate,
individual trade size, or minimum risk"), seeded the same way as
IX-XIII: permanent from game start, no new Live Enforcement hook. See
its own seed-list comment below for why this isn't purely aspirational
text — `app/opportunity_gatekeeper.py` already enforces the real
mechanism this Article names.

Amendments — the CEO may create new Articles; Founders debate them;
Coach evaluates them; Employees vote (advisory only); approved Articles
become permanent. Every step is a real, checkable computation over the
amendment's own real proposed text, never a fabricated debate
transcript:

  Founder debate     - Keystone (Chief Risk Architect) and Compass
                       (Chief Learning Architect) each check the
                       proposed text against their own real domain
                       keyword set, and both run a real redundancy
                       check (word-overlap against every existing
                       Article's own text) — see `_founder_verdict`.
  Coach evaluation    - a real templated read of whichever real
                       CompanyHealth sub-score the proposed text's own
                       keywords match (risk -> operational_stability/
                       capital_health, learning -> research_progress/
                       education_progress), never a fabricated
                       simulation of "how this rule would have changed
                       history."
  Employee vote       - every one of the 13 non-founder-exempt agents
                       casts a real vote: "support" if their own real
                       AgentProfile.occupation keyword-matches the
                       amendment's theme (a real, named reason), an
                       across-the-board "support" by default (advisory,
                       never gates anything), or "abstain" only when a
                       Founder's own real redundancy flag was raised —
                       a genuine conditional link to that real verdict,
                       never a random vote.
  CEO ratification    - the CEO's own real, manual, final call
                       (`POST /api/constitution/decide`) — Automation
                       Mode is deliberately NOT wired into this one
                       decision (unlike the Research Sandbox's Company
                       Review): amending the company's permanent law is
                       exactly the kind of decision the brief frames as
                       inherently the CEO's, never auto-resolved.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.agents import AGENT_PROFILES
from app.schemas import (
    AgentId,
    CaseStudyCategory,
    CompanyHealth,
    ConstitutionAmendment,
    ConstitutionArticle,
    ConstitutionCitation,
    ConstitutionCitationSource,
    ConstitutionEmployeeVote,
    ConstitutionFounderVerdict,
    ConstitutionState,
    FounderId,
)

MAX_CONSTITUTION_CITATIONS = 120
REDUNDANCY_WORD_OVERLAP_THRESHOLD = 0.35
MIN_SHARED_WORDS_FOR_REDUNDANCY = 2

_STOPWORDS = {"the", "a", "an", "of", "to", "and", "or", "before", "over", "first", "must", "is", "are", "be", "no", "every", "always", "than"}

_ARTICLE_SEED: list[tuple[str, str, str]] = [
    ("I", "Protect capital first", "Protect capital first."),
    ("II", "Research before execution", "Research before execution."),
    ("III", "Challenge assumptions", "Challenge assumptions."),
    ("IV", "Evidence over opinions", "Evidence over opinions."),
    ("V", "No revenge trading", "No revenge trading."),
    ("VI", "Every mistake must teach something", "Every mistake must teach something."),
    ("VII", "Respect risk", "Respect risk."),
    ("VIII", "Continuous learning is mandatory", "Continuous learning is mandatory."),
    # Articles IX-XIII — the Probability First Trading Philosophy (see
    # docs/DESIGN_BIBLE.md's "Probability First Trading Philosophy"
    # section). Not a feature: a permanent foundational principle,
    # seeded verbatim exactly like Articles I-VIII above, that every
    # department, strategy, and future feature inherits without ever
    # needing to redefine it.
    ("IX", "We trade probabilities, not predictions", "We trade probabilities, not predictions."),
    ("X", "A single trade does not determine success", "A single trade does not determine success."),
    ("XI", "Risk must be accepted before entry", "Risk must be accepted before entry."),
    ("XII", "Process is more important than outcome", "Process is more important than outcome."),
    (
        "XIII",
        "Statistics become meaningful only through consistent execution over a large sample of trades",
        "Statistics become meaningful only through consistent execution over a large sample of trades.",
    ),
    # Article XIV — the CEO Company Health + Live Market Realism
    # directive's Section 25 decision principle, seeded verbatim exactly
    # like IX-XIII above: a permanent foundational principle, not a
    # live-amended one, so it's present from game start rather than
    # only from whatever sim day a CEO happened to ratify it. Same
    # deliberate scope boundary as IX-XIII: no new "Live Enforcement"
    # citation hook was added — that would be new detection engineering
    # for a documentation-driven addition. The principle isn't only
    # aspirational text, though: app/opportunity_gatekeeper.py already
    # enforces the real mechanism behind it (RiskLimits.min_expected_value_pct
    # gates every pre-proposal candidate on real computed Expected Value,
    # not win rate), so this Article names, in the company's own
    # permanent law, a real behavior this codebase already has — the
    # same "cited, not rebuilt" relationship this module's own docstring
    # describes for Articles I-VIII's Live Enforcement hooks.
    (
        "XIV",
        "TradeTown optimizes for statistically validated expected value and long-term survival, not simply win rate, individual trade size, or minimum risk",
        "TradeTown optimizes for statistically validated expected value and long-term survival, not simply win rate, individual trade size, or minimum risk.",
    ),
]

# app/mistakes.py's CaseStudyCategory (6 mistake categories) and
# app/successes.py's 3 positive inversions, each mapped to whichever
# real Article that specific detected pattern violates or honors — see
# this module's own docstring for the full rationale.
MISTAKE_ARTICLE_MAP: dict[CaseStudyCategory, str] = {
    "overconfidence": "VII",
    "incomplete_research": "II",
    "unchallenged_assumptions": "III",
    "acted_too_quickly": "V",
    "ignored_dissent": "IV",
    "confirmation_bias": "IV",
    "disciplined_process": "I",
    "rigorous_cross_examination": "III",
    "patient_execution": "V",
}

RISK_KEYWORDS = {"risk", "capital", "loss", "losses", "drawdown", "protect", "exposure", "danger", "safety"}
LEARNING_KEYWORDS = {"learn", "learning", "research", "knowledge", "mistake", "mistakes", "teach", "study", "evidence", "question", "questions"}

# Keystone = Chief Risk Architect, Compass = Chief Learning Architect
# (see app/founders.py) — their own real domains, not arbitrary.
FOUNDER_DOMAIN_KEYWORDS: dict[FounderId, set[str]] = {"keystone": RISK_KEYWORDS, "compass": LEARNING_KEYWORDS}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_constitution() -> ConstitutionState:
    now = _now_iso()
    articles = [ConstitutionArticle(id=aid, title=title, text=text, ratifiedSimDay=1, createdAt=now) for aid, title, text in _ARTICLE_SEED]
    return ConstitutionState(articles=articles, citations=[], amendments=[], updatedAt=now)


def article_lookup(articles: list[ConstitutionArticle]) -> dict[str, ConstitutionArticle]:
    return {a.id: a for a in articles}


def cite_article(citations: list[ConstitutionCitation], article_id: str, source: ConstitutionCitationSource, detail: str, sim_day: int) -> list[ConstitutionCitation]:
    # `len(citations)` alone collides once the list below is capped at
    # MAX_CONSTITUTION_CITATIONS and old entries start getting trimmed off
    # the front: the length then stays pinned at the cap, so any two
    # citations of the same source+article after that point get the exact
    # same id (a real, observed React duplicate-key warning on the OPS
    # tab's citation feed — `constitution-citation-cite-academy-VIII-120`
    # twice). A real microsecond-precision timestamp component keeps every
    # id unique regardless of how long the list has been capped.
    citation = ConstitutionCitation(
        id=f"cite-{source}-{article_id}-{len(citations)}-{int(datetime.now(timezone.utc).timestamp() * 1_000_000)}",
        articleId=article_id,
        source=source,
        detail=detail,
        simDay=sim_day,
        createdAt=_now_iso(),
    )
    updated = [*citations, citation]
    if len(updated) > MAX_CONSTITUTION_CITATIONS:
        del updated[: len(updated) - MAX_CONSTITUTION_CITATIONS]
    return updated


# v0.7 Feature 47 — Company Operating System's "Real-Time Guidance":
# "the system references company principles when giving advice... 'This
# violates Company Principle 8'... 'conflicts with historical evidence.'"
# Each real concern bucket a ChallengeReport already computes for itself
# (app/devils_advocate.py) maps to the one real Article it most directly
# speaks to — surfaced on the report itself, distinct from nexus.py's own
# separate global enforcement-log hook (which always cites III on any
# filed report, and IV only when evidence is missing, for the permanent
# "Live Enforcement" feed). No new detection logic — purely a read of
# fields that already exist.
def articles_for_challenge(*, hidden_risks: list[str], weak_assumptions: list[str], missing_evidence: list[str], historical_comparisons: list[str]) -> list[str]:
    ids: list[str] = []
    if hidden_risks:
        ids.append("VII")  # Respect risk
    if weak_assumptions:
        ids.append("III")  # Challenge assumptions
    if missing_evidence:
        ids.append("IV")  # Evidence over opinions
    if historical_comparisons:
        ids.append("VI")  # Every mistake must teach something
    return ids


def _significant_words(text: str) -> set[str]:
    return {w for w in "".join(c.lower() if c.isalnum() else " " for c in text).split() if w not in _STOPWORDS and len(w) > 2}


def _next_roman(existing_ids: list[str]) -> str:
    romans = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "XIII", "XIV", "XV", "XVI", "XVII", "XVIII", "XIX", "XX"]
    for r in romans:
        if r not in existing_ids:
            return r
    return f"XX+{len(existing_ids)}"


def propose_amendment(title: str, text: str, sim_day: int) -> ConstitutionAmendment:
    return ConstitutionAmendment(id=f"amendment-{title.lower().replace(' ', '-')[:24]}-{sim_day}", proposedTitle=title, proposedText=text, status="proposed", simDay=sim_day, createdAt=_now_iso())


def _founder_verdict(founder_id: FounderId, amendment_words: set[str], articles: list[ConstitutionArticle]) -> ConstitutionFounderVerdict:
    domain_hits = amendment_words & FOUNDER_DOMAIN_KEYWORDS[founder_id]

    # Real word overlap, but never on a single shared word alone — the
    # seeded Articles are each one short sentence (as few as 2
    # significant words), so a bare one-word match would flag nearly
    # any proposal as "redundant" against whichever Article happens to
    # share that one word. Requiring >= MIN_SHARED_WORDS keeps this a
    # genuine restatement check, not a coincidence detector.
    redundant_with: str | None = None
    best_overlap = 0.0
    for article in articles:
        article_words = _significant_words(article.text)
        shared = amendment_words & article_words
        if not article_words or len(shared) < MIN_SHARED_WORDS_FOR_REDUNDANCY:
            continue
        overlap = len(shared) / len(article_words)
        if overlap > best_overlap:
            best_overlap = overlap
            redundant_with = article.id
    if best_overlap < REDUNDANCY_WORD_OVERLAP_THRESHOLD:
        redundant_with = None

    name = "Keystone" if founder_id == "keystone" else "Compass"
    domain = "risk" if founder_id == "keystone" else "learning"
    if redundant_with:
        verdict = f'{name}: this overlaps significantly with Article {redundant_with} — consider whether it adds a genuinely new rule or restates one we already have.'
    elif domain_hits:
        verdict = f'{name}: this speaks directly to my domain ({domain}) — real terms in it: {", ".join(sorted(domain_hits))}. No conflict with existing Articles.'
    else:
        verdict = f"{name}: outside my domain ({domain}) — no conflict from my seat, but I'd defer to whichever department this actually touches."

    return ConstitutionFounderVerdict(founderId=founder_id, verdict=verdict, redundantWithArticleId=redundant_with)


def generate_founder_debate(amendment: ConstitutionAmendment, articles: list[ConstitutionArticle]) -> list[ConstitutionFounderVerdict]:
    words = _significant_words(amendment.proposed_text)
    return [_founder_verdict("keystone", words, articles), _founder_verdict("compass", words, articles)]


def generate_coach_evaluation(amendment: ConstitutionAmendment, company_health: CompanyHealth) -> str:
    words = _significant_words(amendment.proposed_text)
    if words & RISK_KEYWORDS:
        return (
            f"Coach: reading this against the real numbers — Operational Stability is {company_health.operational_stability:.0f}/100 "
            f"and Capital Health is {company_health.capital_health:.0f}/100 right now. A risk-themed rule lands on real, current ground."
        )
    if words & LEARNING_KEYWORDS:
        return (
            f"Coach: reading this against the real numbers — Research Progress is {company_health.research_progress:.0f}/100 "
            f"and Education Progress is {company_health.education_progress:.0f}/100 right now. A learning-themed rule lands on real, current ground."
        )
    return f"Coach: this doesn't map to a specific tracked sub-score — overall Company Health is {company_health.overall:.0f}/100 ({company_health.tier}) for context."


def generate_employee_votes(amendment: ConstitutionAmendment, founder_verdicts: list[ConstitutionFounderVerdict], agent_ids: tuple[AgentId, ...]) -> list[ConstitutionEmployeeVote]:
    words = _significant_words(amendment.proposed_text)
    any_redundant = any(v.redundant_with_article_id is not None for v in founder_verdicts)

    votes: list[ConstitutionEmployeeVote] = []
    for agent_id in agent_ids:
        if agent_id in ("keystone", "compass"):
            continue  # the Founders already weighed in via the debate itself
        occupation_words = _significant_words(AGENT_PROFILES[agent_id].occupation)
        matched = occupation_words & words
        if matched:
            votes.append(ConstitutionEmployeeVote(agentId=agent_id, choice="support", reason=f"{AGENT_PROFILES[agent_id].name}: this touches my own work directly ({', '.join(sorted(matched))})."))
        elif any_redundant:
            votes.append(ConstitutionEmployeeVote(agentId=agent_id, choice="abstain", reason=f"{AGENT_PROFILES[agent_id].name}: deferring to the Founders' redundancy concern — not my department to weigh in on."))
        else:
            votes.append(ConstitutionEmployeeVote(agentId=agent_id, choice="support", reason=f"{AGENT_PROFILES[agent_id].name}: no real objection on record."))
    return votes


def decide_amendment(amendment: ConstitutionAmendment, approve: bool, sim_day: int) -> ConstitutionAmendment:
    return amendment.model_copy(update={"ceo_decision": "approved" if approve else "rejected", "status": "approved" if approve else "rejected"})


def ratify_amendment(articles: list[ConstitutionArticle], amendment: ConstitutionAmendment, sim_day: int) -> tuple[list[ConstitutionArticle], ConstitutionAmendment]:
    new_id = _next_roman([a.id for a in articles])
    article = ConstitutionArticle(id=new_id, title=amendment.proposed_title, text=amendment.proposed_text, ratifiedSimDay=sim_day, createdAt=_now_iso())
    return [*articles, article], amendment.model_copy(update={"ratified_article_id": new_id})
