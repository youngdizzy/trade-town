"""Covers app/audit_log.py — Design Bible Chapter 73, the Compliance,
Audit & Governance System. Every AuditEntry must trace back to one real,
already-persisted record's own fields — never a fabricated event, a
fabricated field (Broker/User/Software Version), or a second incident
list that could drift from the real Audit Log.
"""
from __future__ import annotations

from app.audit_log import (
    GOVERNANCE_LAYERS,
    compute_audit_log,
    compute_ceo_overrides,
    compute_compliance_overview,
    compute_compliance_score,
    compute_incidents,
    filter_audit_log,
)
from app.portfolio import default_portfolio
from app.risk_engine import default_risk_limits
from app.schemas import (
    Account,
    BlackSwanEventRecord,
    CeoDecisionRecord,
    DisciplineReview,
    ExecutiveMeetingLogEntry,
    GatekeeperRejection,
    MemoryRecord,
    OpportunityRejection,
    PostDecisionReview,
    RiskWarning,
    Rule,
)


def _ceo_decision(*, decision_id: str = "d1", agreed: bool = True, outcome: str = "pending") -> CeoDecisionRecord:
    return CeoDecisionRecord(
        id=decision_id,
        proposalId=f"prop-{decision_id}",
        symbol="AAPL",
        category="stock",
        aiRecommendation="buy",
        ceoDecision="buy" if agreed else "sell",
        agreedWithAi=agreed,
        decisionId=None,
        outcome=outcome,  # type: ignore[arg-type]
        resolvedBy="ceo",
        createdAt="2026-01-02T00:00:00Z",
    )


def _gatekeeper_rejection() -> GatekeeperRejection:
    return GatekeeperRejection(
        id="gk1",
        proposalId="prop-gk1",
        symbol="TSLA",
        ceoChoice="buy",
        reasons=["Active risk warning on file."],
        priceAtRejection=100.0,
        rejectedSimMinutes=1440,
        createdAt="2026-01-01T12:00:00Z",
    )


def _opportunity_rejection() -> OpportunityRejection:
    return OpportunityRejection(
        id="opp1",
        symbol="MSFT",
        wouldHaveRecommended="buy",
        reasons=["Decision Score below the real threshold."],
        decisionScoreAtRejection=40.0,
        expectedValueAtRejectionPct=-1.0,
        priceAtRejection=300.0,
        rejectedSimMinutes=1440,
        createdAt="2026-01-01T13:00:00Z",
    )


def _risk_warning(severity: str = "critical") -> RiskWarning:
    return RiskWarning(id="risk1", symbol="AAPL", severity=severity, message="Portfolio drawdown breached the limit.", createdAt="2026-01-01T14:00:00Z")  # type: ignore[arg-type]


def _discipline_review(tier: str = "reckless") -> DisciplineReview:
    return DisciplineReview(
        id="disc1",
        decisionId="decision-1",
        symbol="AAPL",
        score=20.0,
        tier=tier,  # type: ignore[arg-type]
        factors=[],
        attendees=["sentinel"],  # type: ignore[list-item]
        summary="Ignored an active risk warning before entering.",
        postDecisionReview=PostDecisionReview(),
        outcome="loss",
        tradePnlPct=-5.0,
        holdDurationMinutes=60,
        simDay=3,
        createdAt="2026-01-03T00:00:00Z",
    )


def _memory(category: str, title: str, body: str = "detail") -> MemoryRecord:
    return MemoryRecord(id=f"memory-{category}-{title}", category=category, title=title, body=body, timestamp="2026-01-04T00:00:00Z")  # type: ignore[arg-type]


def _black_swan_event() -> BlackSwanEventRecord:
    return BlackSwanEventRecord(
        id="bs1",
        triggerReason="Manually activated by the CEO.",
        peakTier="red",
        activatedAt="2026-01-05T00:00:00Z",
        deactivatedAt="2026-01-05T01:00:00Z",
        durationSimMinutes=60,
        equityAtActivation=100000.0,
        equityAtDeactivation=99000.0,
        equityChangePct=-1.0,
        largestContributingFactor="Liquidity",
        affectedSymbols=["AAPL"],
        lesson="Defensive Mode episode ended.",
        createdAt="2026-01-05T01:00:00Z",
    )


def _account_with_rule() -> Account:
    portfolio = default_portfolio()
    return Account(
        id="acct1",
        name="Business",
        accountType="business",  # type: ignore[arg-type]
        portfolio=portfolio,
        riskLimits=default_risk_limits(),
        createdAt="2026-01-01T00:00:00Z",
        peakEquity=portfolio.starting_balance,
        # A real, deterministic failure regardless of portfolio state:
        # default RiskLimits.risk_per_trade_pct is 2.0%, always > 0.
        customRules=[Rule(id="rule1", ruleType="max_risk_per_trade_pct", label="Max Risk Per Trade", limit=0, weekday=None, enabled=True)],  # type: ignore[arg-type]
    )


def _empty_log_kwargs() -> dict:
    return dict(
        ceo_decisions=[],
        gatekeeper_rejections=[],
        opportunity_rejections=[],
        risk_warnings=[],
        discipline_reviews=[],
        memory=[],
        black_swan_events=[],
        accounts=[],
        current_sim_day=1,
    )


class TestComputeAuditLog:
    def test_empty_state_produces_an_empty_log_never_a_fabricated_entry(self) -> None:
        assert compute_audit_log(**_empty_log_kwargs()) == []

    def test_ceo_decision_override_is_flagged_and_agreement_is_not(self) -> None:
        kwargs = _empty_log_kwargs()
        kwargs["ceo_decisions"] = [_ceo_decision(decision_id="d1", agreed=True), _ceo_decision(decision_id="d2", agreed=False)]
        entries = compute_audit_log(**kwargs)
        override_entry = next(e for e in entries if "audit-ceo-d2" in e.id)
        agreed_entry = next(e for e in entries if "audit-ceo-d1" in e.id)
        assert "Overrode" in override_entry.summary
        assert override_entry.severity == "warning"
        assert "Followed" in agreed_entry.summary
        assert agreed_entry.severity == "info"

    def test_gatekeeper_rejection_produces_a_real_entry_with_real_reasons(self) -> None:
        kwargs = _empty_log_kwargs()
        kwargs["gatekeeper_rejections"] = [_gatekeeper_rejection()]
        entries = compute_audit_log(**kwargs)
        assert len(entries) == 1
        assert entries[0].category == "gatekeeper_rejection"
        assert "Active risk warning on file." in entries[0].detail

    def test_only_critical_risk_warnings_become_audit_entries(self) -> None:
        kwargs = _empty_log_kwargs()
        kwargs["risk_warnings"] = [_risk_warning("critical"), _risk_warning("warning")]
        entries = compute_audit_log(**kwargs)
        assert len(entries) == 1
        assert entries[0].severity == "critical"

    def test_only_weak_and_reckless_discipline_reviews_become_audit_entries(self) -> None:
        kwargs = _empty_log_kwargs()
        kwargs["discipline_reviews"] = [_discipline_review("reckless"), _discipline_review("exemplary")]
        entries = compute_audit_log(**kwargs)
        assert len(entries) == 1
        assert entries[0].category == "discipline_review"
        assert entries[0].severity == "critical"

    def test_emergency_stop_memory_records_become_audit_entries(self) -> None:
        kwargs = _empty_log_kwargs()
        kwargs["memory"] = [_memory("emergency", "Emergency Stop activated"), _memory("emergency", "Trading resumed")]
        entries = compute_audit_log(**kwargs)
        assert len(entries) == 2
        activated = next(e for e in entries if "activated" in e.summary.lower())
        assert activated.severity == "critical"
        assert activated.category == "emergency_stop"

    def test_crisis_briefing_memory_records_become_audit_entries_other_alerts_do_not(self) -> None:
        kwargs = _empty_log_kwargs()
        kwargs["memory"] = [_memory("alert", "Crisis Briefing — Risk Level RED"), _memory("alert", "Some unrelated alert")]
        entries = compute_audit_log(**kwargs)
        assert len(entries) == 1
        assert entries[0].category == "crisis_briefing"

    def test_black_swan_event_becomes_an_audit_entry(self) -> None:
        kwargs = _empty_log_kwargs()
        kwargs["black_swan_events"] = [_black_swan_event()]
        entries = compute_audit_log(**kwargs)
        assert len(entries) == 1
        assert entries[0].category == "defensive_mode"
        assert "RED" in entries[0].summary

    def test_failed_rule_check_becomes_a_real_rule_violation_entry(self) -> None:
        kwargs = _empty_log_kwargs()
        kwargs["accounts"] = [_account_with_rule()]
        entries = compute_audit_log(**kwargs)
        assert len(entries) == 1
        assert entries[0].category == "rule_violation"
        assert "Business" in entries[0].summary

    def test_entries_are_sorted_newest_first(self) -> None:
        kwargs = _empty_log_kwargs()
        kwargs["gatekeeper_rejections"] = [_gatekeeper_rejection()]
        kwargs["black_swan_events"] = [_black_swan_event()]
        entries = compute_audit_log(**kwargs)
        timestamps = [e.timestamp for e in entries]
        assert timestamps == sorted(timestamps, reverse=True)

    def test_never_fabricates_broker_user_or_version_fields(self) -> None:
        kwargs = _empty_log_kwargs()
        kwargs["gatekeeper_rejections"] = [_gatekeeper_rejection()]
        entries = compute_audit_log(**kwargs)
        dumped = entries[0].model_dump()
        assert "broker" not in dumped
        assert "user" not in dumped
        assert "softwareVersion" not in dumped
        assert "software_version" not in dumped


class TestFilterAuditLog:
    def test_filters_by_category(self) -> None:
        kwargs = _empty_log_kwargs()
        kwargs["gatekeeper_rejections"] = [_gatekeeper_rejection()]
        kwargs["opportunity_rejections"] = [_opportunity_rejection()]
        entries = compute_audit_log(**kwargs)
        filtered = filter_audit_log(entries, category="gatekeeper_rejection")
        assert len(filtered) == 1
        assert filtered[0].category == "gatekeeper_rejection"

    def test_filters_by_severity(self) -> None:
        kwargs = _empty_log_kwargs()
        kwargs["risk_warnings"] = [_risk_warning("critical")]
        kwargs["ceo_decisions"] = [_ceo_decision(agreed=True)]
        entries = compute_audit_log(**kwargs)
        filtered = filter_audit_log(entries, severity="critical")
        assert len(filtered) == 1
        assert filtered[0].severity == "critical"

    def test_search_matches_real_summary_or_detail_text(self) -> None:
        kwargs = _empty_log_kwargs()
        kwargs["gatekeeper_rejections"] = [_gatekeeper_rejection()]
        entries = compute_audit_log(**kwargs)
        assert len(filter_audit_log(entries, search="TSLA")) == 1
        assert len(filter_audit_log(entries, search="nonexistent-keyword")) == 0

    def test_limit_caps_results(self) -> None:
        kwargs = _empty_log_kwargs()
        kwargs["gatekeeper_rejections"] = [_gatekeeper_rejection()]
        kwargs["opportunity_rejections"] = [_opportunity_rejection()]
        entries = compute_audit_log(**kwargs)
        assert len(filter_audit_log(entries, limit=1)) == 1


class TestIncidentsAndOverrides:
    def test_incidents_are_a_pure_filter_never_a_second_list(self) -> None:
        kwargs = _empty_log_kwargs()
        kwargs["gatekeeper_rejections"] = [_gatekeeper_rejection()]
        kwargs["ceo_decisions"] = [_ceo_decision(agreed=True)]
        entries = compute_audit_log(**kwargs)
        incidents = compute_incidents(entries)
        assert len(incidents) == 1
        assert all(i.severity != "info" for i in incidents)
        assert all(i in entries for i in incidents)

    def test_ceo_overrides_reuses_the_real_agreed_with_ai_field(self) -> None:
        decisions = [_ceo_decision(decision_id="d1", agreed=True), _ceo_decision(decision_id="d2", agreed=False)]
        overrides = compute_ceo_overrides(decisions)
        assert len(overrides) == 1
        assert overrides[0].proposal_id == "prop-d2"

    def test_compliance_score_decreases_with_more_incidents_floored_at_40(self) -> None:
        no_incidents_score = compute_compliance_score([])
        kwargs = _empty_log_kwargs()
        kwargs["gatekeeper_rejections"] = [_gatekeeper_rejection()]
        some_incidents = compute_incidents(compute_audit_log(**kwargs))
        some_score = compute_compliance_score(some_incidents)
        assert no_incidents_score == 100.0
        assert some_score < no_incidents_score
        assert compute_compliance_score(some_incidents * 100) >= 40.0


class TestComplianceOverview:
    def test_overview_reuses_real_counts_never_invents_a_new_score(self) -> None:
        kwargs = _empty_log_kwargs()
        kwargs["gatekeeper_rejections"] = [_gatekeeper_rejection()]
        kwargs["ceo_decisions"] = [_ceo_decision(decision_id="d1", agreed=False)]
        entries = compute_audit_log(**kwargs)
        overview = compute_compliance_overview(
            entries=entries,
            ceo_decisions=kwargs["ceo_decisions"],
            meeting_log=[],
            defensive_mode_active=False,
            emergency_stop_active=False,
        )
        assert overview.total_audit_entries == len(entries)
        assert overview.ceo_override_count == 1
        assert overview.ceo_override_rate_pct == 100.0
        assert overview.open_incident_count == len(compute_incidents(entries))
        assert overview.defensive_mode_active is False
        assert overview.emergency_stop_active is False

    def test_executive_meeting_log_type_accepted(self) -> None:
        # A real ExecutiveMeetingLogEntry list must type-check through
        # unchanged into compute_executive_accuracy_scores() — no
        # recomputation happens in this module.
        entry_list: list[ExecutiveMeetingLogEntry] = []
        overview = compute_compliance_overview(
            entries=[],
            ceo_decisions=[],
            meeting_log=entry_list,
            defensive_mode_active=True,
            emergency_stop_active=True,
        )
        assert overview.defensive_mode_active is True
        assert overview.emergency_stop_active is True


class TestGovernanceLayers:
    def test_governance_layers_are_ordered_and_disclosed(self) -> None:
        orders = [layer.order for layer in GOVERNANCE_LAYERS]
        assert orders == sorted(orders)
        assert len(orders) == len(set(orders))

    def test_institutional_rule_engine_is_disclosed_as_not_wired(self) -> None:
        rule_engine_layer = next(layer for layer in GOVERNANCE_LAYERS if "Rule Engine" in layer.name)
        assert rule_engine_layer.wired is False

    def test_every_other_layer_is_disclosed_as_wired(self) -> None:
        for layer in GOVERNANCE_LAYERS:
            if "Rule Engine" in layer.name:
                continue
            assert layer.wired is True
