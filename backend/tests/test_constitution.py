"""Covers app/constitution.py — v0.7 Feature 46, the Company
Constitution. The 8 seeded Articles must match the brief verbatim, every
citation must trace to a real source, and the amendment pipeline
(Founder debate -> Coach evaluation -> Employee vote -> CEO ratification)
must be real, checkable computations over the amendment's own real
proposed text — never a fabricated debate transcript.
"""
from __future__ import annotations

from app.constitution import (
    MAX_CONSTITUTION_CITATIONS,
    MISTAKE_ARTICLE_MAP,
    cite_article,
    decide_amendment,
    default_constitution,
    generate_coach_evaluation,
    generate_employee_votes,
    generate_founder_debate,
    propose_amendment,
    ratify_amendment,
)
from app.schemas import CompanyHealth


def _health(**overrides: float) -> CompanyHealth:
    base = dict(
        overall=60.0,
        tier="stable",
        operationalStability=60.0,
        departmentEfficiency=60.0,
        employeeMorale=60.0,
        researchProgress=60.0,
        capitalHealth=60.0,
        resourceUsage=60.0,
        reputation=60.0,
        technologyLevel=60.0,
        officeExpansion=60.0,
        educationProgress=60.0,
        recommendations=[],
        updatedAt="2026-01-01T00:00:00+00:00",
    )
    base.update(overrides)
    return CompanyHealth(**base)  # type: ignore[arg-type]


class TestDefaultConstitution:
    def test_seeds_exactly_the_briefs_eight_articles(self) -> None:
        constitution = default_constitution()
        assert [a.id for a in constitution.articles] == ["I", "II", "III", "IV", "V", "VI", "VII", "VIII"]
        assert constitution.articles[0].text == "Protect capital first."
        assert constitution.articles[-1].text == "Continuous learning is mandatory."
        assert constitution.citations == []
        assert constitution.amendments == []


class TestMistakeArticleMap:
    def test_every_real_case_study_category_has_a_mapped_article(self) -> None:
        expected_categories = {
            "overconfidence",
            "incomplete_research",
            "unchallenged_assumptions",
            "acted_too_quickly",
            "ignored_dissent",
            "confirmation_bias",
            "disciplined_process",
            "rigorous_cross_examination",
            "patient_execution",
        }
        assert set(MISTAKE_ARTICLE_MAP.keys()) == expected_categories
        valid_ids = {a for a in "I II III IV V VI VII VIII".split()}
        assert all(v in valid_ids for v in MISTAKE_ARTICLE_MAP.values())

    def test_mistake_and_its_positive_inversion_cite_the_same_article(self) -> None:
        assert MISTAKE_ARTICLE_MAP["unchallenged_assumptions"] == MISTAKE_ARTICLE_MAP["rigorous_cross_examination"]
        assert MISTAKE_ARTICLE_MAP["acted_too_quickly"] == MISTAKE_ARTICLE_MAP["patient_execution"]


class TestCiteArticle:
    def test_appends_a_real_citation(self) -> None:
        citations = cite_article([], "III", "devils_advocate", "Challenged the NEXA thesis.", sim_day=5)
        assert len(citations) == 1
        assert citations[0].article_id == "III"
        assert citations[0].source == "devils_advocate"
        assert citations[0].sim_day == 5

    def test_caps_at_the_max(self) -> None:
        citations: list = []
        for i in range(MAX_CONSTITUTION_CITATIONS + 10):
            citations = cite_article(citations, "I", "risk_department", f"warning {i}", sim_day=1)
        assert len(citations) == MAX_CONSTITUTION_CITATIONS


class TestFounderDebate:
    def test_keystone_matches_a_risk_themed_amendment(self) -> None:
        amendment = propose_amendment("Size limits", "Never risk more capital than the company can afford to lose.", sim_day=10)
        verdicts = generate_founder_debate(amendment, default_constitution().articles)
        keystone = next(v for v in verdicts if v.founder_id == "keystone")
        assert "domain" in keystone.verdict.lower() or "risk" in keystone.verdict.lower()

    def test_compass_matches_a_learning_themed_amendment(self) -> None:
        amendment = propose_amendment("Study reviews", "Every employee must research and learn from company mistakes.", sim_day=10)
        verdicts = generate_founder_debate(amendment, default_constitution().articles)
        compass = next(v for v in verdicts if v.founder_id == "compass")
        assert compass.redundant_with_article_id is not None or "learning" in compass.verdict.lower()

    def test_flags_redundancy_against_an_existing_article(self) -> None:
        amendment = propose_amendment("Restated Article", "Protect capital first at all times.", sim_day=10)
        verdicts = generate_founder_debate(amendment, default_constitution().articles)
        assert any(v.redundant_with_article_id == "I" for v in verdicts)

    def test_no_domain_match_and_no_redundancy_gives_a_neutral_verdict(self) -> None:
        amendment = propose_amendment("Office plants", "Add more plants to the break room.", sim_day=10)
        verdicts = generate_founder_debate(amendment, default_constitution().articles)
        assert all(v.redundant_with_article_id is None for v in verdicts)
        assert all("outside my domain" in v.verdict for v in verdicts)


class TestCoachEvaluation:
    def test_cites_risk_subscores_for_a_risk_themed_amendment(self) -> None:
        amendment = propose_amendment("Risk cap", "Limit real capital exposure and risk per trade.", sim_day=10)
        evaluation = generate_coach_evaluation(amendment, _health(operationalStability=42.0))
        assert "42" in evaluation

    def test_cites_learning_subscores_for_a_learning_themed_amendment(self) -> None:
        amendment = propose_amendment("Study time", "Mandate weekly research and learning time.", sim_day=10)
        evaluation = generate_coach_evaluation(amendment, _health(researchProgress=77.0))
        assert "77" in evaluation

    def test_falls_back_to_overall_health_when_no_theme_matches(self) -> None:
        amendment = propose_amendment("Office plants", "Add more plants to the break room.", sim_day=10)
        evaluation = generate_coach_evaluation(amendment, _health(overall=88.0))
        assert "88" in evaluation


class TestEmployeeVotes:
    def test_excludes_the_two_founders(self) -> None:
        amendment = propose_amendment("Office plants", "Add more plants to the break room.", sim_day=10)
        votes = generate_employee_votes(amendment, [], ("keystone", "compass", "echo", "guardian"))
        assert {v.agent_id for v in votes} == {"echo", "guardian"}

    def test_occupation_match_votes_support_with_a_real_reason(self) -> None:
        amendment = propose_amendment("Portfolio review", "Strengthen portfolio protection reviews every week.", sim_day=10)
        votes = generate_employee_votes(amendment, [], ("guardian",))
        assert votes[0].choice == "support"
        assert "portfolio" in votes[0].reason.lower()

    def test_abstains_when_founders_flagged_redundancy_and_no_occupation_match(self) -> None:
        amendment = propose_amendment("Office plants", "Add more plants to the break room.", sim_day=10)
        founder_verdicts = generate_founder_debate(propose_amendment("Restated", "Protect capital first.", sim_day=10), default_constitution().articles)
        votes = generate_employee_votes(amendment, founder_verdicts, ("scout",))
        assert votes[0].choice == "abstain"

    def test_defaults_to_support_with_no_redundancy_and_no_occupation_match(self) -> None:
        amendment = propose_amendment("Office plants", "Add more plants to the break room.", sim_day=10)
        votes = generate_employee_votes(amendment, [], ("scout",))
        assert votes[0].choice == "support"


class TestAmendmentDecision:
    def test_approval_ratifies_a_new_article_with_the_next_roman_numeral(self) -> None:
        constitution = default_constitution()
        amendment = propose_amendment("New Rule", "A brand new company rule.", sim_day=20)
        decided = decide_amendment(amendment, True, sim_day=20)
        assert decided.ceo_decision == "approved"
        articles, ratified = ratify_amendment(constitution.articles, decided, sim_day=20)
        assert articles[-1].id == "IX"
        assert articles[-1].text == "A brand new company rule."
        assert ratified.ratified_article_id == "IX"
        assert len(articles) == len(constitution.articles) + 1

    def test_rejection_never_touches_the_articles_list(self) -> None:
        amendment = propose_amendment("New Rule", "A brand new company rule.", sim_day=20)
        decided = decide_amendment(amendment, False, sim_day=20)
        assert decided.ceo_decision == "rejected"
        assert decided.ratified_article_id is None
