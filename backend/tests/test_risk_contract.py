"""Covers app/risk_contract.py — CEO directive "TradeTown — Persisted
Risk Contract + Dynamic Risk Scaling." Every scenario below traces back
to a real, disclosed rule cited in that module's own docstrings:
append-only versioning (app/strategy_registry.py's own proven shape),
DRAFT -> VALIDATED -> ACTIVE -> SUPERSEDED/ARCHIVED lifecycle,
downward-only band composition (app/memecoin_sniper.py's own proven
size_multiplier idiom), and structural-vs-policy validation kept
explicitly separate.
"""
from __future__ import annotations

from app.risk_contract import (
    activate_risk_contract,
    apply_risk_contract_scaling,
    archive_risk_contract,
    classify_scaling_band,
    create_draft_risk_contract,
    evaluate_risk_contract_scaling,
    get_active_risk_contract,
    get_risk_contract_version,
    mark_validated,
    next_version_number,
    validate_risk_contract,
)
from app.schemas import RiskContract, RiskContractScalingBand, RiskContractScalingPolicy, RiskLimits

NOW = "2026-01-01T00:00:00+00:00"


def _draft(history: list[RiskContract] | None = None, *, contract_id: str = "rc-1", limits: RiskLimits | None = None, scaling_policy: RiskContractScalingPolicy | None = None) -> RiskContract:
    return create_draft_risk_contract(
        history=history or [],
        contract_id=contract_id,
        limits=limits or RiskLimits(),
        created_by="ceo",
        reason="Initial contract.",
        created_at=NOW,
        scaling_policy=scaling_policy,
    )


# ---------------------------------------------------------------------------
# Versioning / lifecycle
# ---------------------------------------------------------------------------


def test_next_version_number_is_length_plus_one_never_caller_supplied() -> None:
    assert next_version_number([]) == 1
    draft = _draft()
    assert next_version_number([draft]) == 2


def test_create_draft_is_never_active_and_names_previous_active() -> None:
    draft = _draft()
    assert draft.status == "draft"
    assert draft.previous_version_id is None

    validated = mark_validated(draft, now_iso=NOW)
    active, history = activate_risk_contract([validated], validated.id, now_iso=NOW)
    assert active.status == "active"

    second_draft = _draft([active], contract_id="rc-2")
    assert second_draft.previous_version_id == active.id


def test_activate_requires_validated_status() -> None:
    draft = _draft()
    try:
        activate_risk_contract([draft], draft.id, now_iso=NOW)
        raised = False
    except ValueError:
        raised = True
    assert raised, "Activating a non-validated draft must raise."


def test_activate_supersedes_previous_active_atomically_never_two_active() -> None:
    v1 = mark_validated(_draft(contract_id="rc-1"), now_iso=NOW)
    active_v1, history = activate_risk_contract([v1], "rc-1", now_iso=NOW)

    v2 = mark_validated(_draft(history, contract_id="rc-2"), now_iso=NOW)
    history = [*history, v2]
    active_v2, history = activate_risk_contract(history, "rc-2", now_iso=NOW)

    active_entries = [c for c in history if c.status == "active"]
    assert len(active_entries) == 1
    assert active_entries[0].id == "rc-2"
    superseded = next(c for c in history if c.id == "rc-1")
    assert superseded.status == "superseded"
    assert superseded.superseded_at == NOW


def test_activation_never_rewrites_the_superseded_contracts_own_fields() -> None:
    v1 = mark_validated(_draft(contract_id="rc-1", limits=RiskLimits(riskPerTradePct=1.5)), now_iso=NOW)
    active_v1, history = activate_risk_contract([v1], "rc-1", now_iso=NOW)
    v2 = mark_validated(_draft(history, contract_id="rc-2"), now_iso=NOW)
    history = [*history, v2]
    _, history = activate_risk_contract(history, "rc-2", now_iso=NOW)

    original_v1 = next(c for c in history if c.id == "rc-1")
    assert original_v1.limits.risk_per_trade_pct == 1.5
    assert original_v1.version == 1
    assert original_v1.id == "rc-1"


def test_get_active_risk_contract_returns_none_when_no_active_exists() -> None:
    draft = _draft()
    assert get_active_risk_contract([draft]) is None


def test_get_risk_contract_version_resolves_historical_snapshot_by_id_and_version() -> None:
    # Real usage (app/state.py) always mints a fresh id for every new
    # draft — id is unique per history entry; `previous_version_id`, not
    # a shared id, links one version to the next. A later RiskDecision
    # can still look a superseded contract up by (id, version) long
    # after it stopped being active.
    v1 = mark_validated(_draft(contract_id="rc-1"), now_iso=NOW)
    active_v1, history = activate_risk_contract([v1], "rc-1", now_iso=NOW)
    v2 = mark_validated(_draft(history, contract_id="rc-2"), now_iso=NOW)
    history = [*history, v2]
    _, history = activate_risk_contract(history, "rc-2", now_iso=NOW)

    resolved_v1 = get_risk_contract_version(history, "rc-1", 1)
    resolved_v2 = get_risk_contract_version(history, "rc-2", 2)
    assert resolved_v1 is not None and resolved_v1.status == "superseded"
    assert resolved_v2 is not None and resolved_v2.status == "active"
    assert get_risk_contract_version(history, "rc-1", 99) is None
    assert get_risk_contract_version(history, "no-such-id", 1) is None


def test_archive_rejects_the_active_contract() -> None:
    v1 = mark_validated(_draft(), now_iso=NOW)
    active, history = activate_risk_contract([v1], v1.id, now_iso=NOW)
    try:
        archive_risk_contract(history, active.id, now_iso=NOW)
        raised = False
    except ValueError:
        raised = True
    assert raised, "Archiving the live active contract directly must raise."


def test_archive_reachable_from_a_superseded_contract() -> None:
    v1 = mark_validated(_draft(contract_id="rc-1"), now_iso=NOW)
    _, history = activate_risk_contract([v1], "rc-1", now_iso=NOW)
    v2 = mark_validated(_draft(history, contract_id="rc-2"), now_iso=NOW)
    history = [*history, v2]
    _, history = activate_risk_contract(history, "rc-2", now_iso=NOW)

    updated = archive_risk_contract(history, "rc-1", now_iso=NOW)
    archived = next(c for c in updated if c.id == "rc-1")
    assert archived.status == "archived"
    assert archived.archived_at == NOW


def test_mark_validated_only_accepts_a_real_draft() -> None:
    v1 = mark_validated(_draft(), now_iso=NOW)
    try:
        mark_validated(v1, now_iso=NOW)
        raised = False
    except ValueError:
        raised = True
    assert raised, "Re-validating an already-validated contract must raise."


# ---------------------------------------------------------------------------
# Validation — structural
# ---------------------------------------------------------------------------


def test_validate_rejects_non_positive_core_limits() -> None:
    contract = _draft(limits=RiskLimits(riskPerTradePct=0.0))
    result = validate_risk_contract(contract)
    assert not result.valid
    assert any(i.field == "limits.riskPerTradePct" and i.category == "structural" for i in result.issues)


def test_validate_rejects_unordered_scaling_band_thresholds() -> None:
    policy = RiskContractScalingPolicy(
        drawdownBands=[
            RiskContractScalingBand(threshold=8.0, factor=0.75, label="a"),
            RiskContractScalingBand(threshold=4.0, factor=0.5, label="b"),
        ]
    )
    contract = _draft(scaling_policy=policy)
    result = validate_risk_contract(contract)
    assert not result.valid
    assert any(i.category == "structural" and "threshold" in i.field for i in result.issues)


def test_validate_rejects_factor_outside_zero_one_range() -> None:
    policy = RiskContractScalingPolicy(drawdownBands=[RiskContractScalingBand(threshold=4.0, factor=1.5, label="bad")])
    contract = _draft(scaling_policy=policy)
    result = validate_risk_contract(contract)
    assert not result.valid
    assert any(i.field == "scalingPolicy.drawdownBands.bad.factor" for i in result.issues)


def test_validate_rejects_upward_factor_as_severity_increases() -> None:
    # Later, more severe band (higher threshold) approving MORE risk than
    # an earlier, milder one — the exact "never increase risk to recover
    # losses" violation this rule exists to catch.
    policy = RiskContractScalingPolicy(
        drawdownBands=[
            RiskContractScalingBand(threshold=4.0, factor=0.5, label="mild"),
            RiskContractScalingBand(threshold=8.0, factor=0.9, label="severe_but_looser"),
        ]
    )
    contract = _draft(scaling_policy=policy)
    result = validate_risk_contract(contract)
    assert not result.valid
    assert any(i.category == "policy" and "downward-only" in i.message for i in result.issues)


def test_validate_accepts_a_well_formed_contract() -> None:
    contract = _draft()
    result = validate_risk_contract(contract)
    assert result.valid
    assert result.issues == []


# ---------------------------------------------------------------------------
# Validation — policy (structurally valid but internally unwise)
# ---------------------------------------------------------------------------


def test_validate_rejects_daily_loss_exceeding_lifetime_drawdown_ceiling() -> None:
    contract = _draft(limits=RiskLimits(maxDailyLossPct=20.0, maxDrawdownPct=10.0))
    result = validate_risk_contract(contract)
    assert not result.valid
    assert any(i.field == "limits.maxDailyLossPct" and i.category == "policy" for i in result.issues)


def test_validate_rejects_kill_switch_threshold_beyond_max_drawdown() -> None:
    policy = RiskContractScalingPolicy(drawdownBands=[RiskContractScalingBand(threshold=50.0, factor=0.0, label="kill")])
    contract = _draft(limits=RiskLimits(maxDrawdownPct=20.0), scaling_policy=policy)
    result = validate_risk_contract(contract)
    assert not result.valid
    assert any(i.field == "scalingPolicy.drawdownBands" and i.category == "policy" for i in result.issues)


# ---------------------------------------------------------------------------
# Dynamic scaling — band classification
# ---------------------------------------------------------------------------


def test_classify_scaling_band_returns_full_factor_when_no_threshold_crossed() -> None:
    bands = [RiskContractScalingBand(threshold=4.0, factor=0.75, label="a")]
    label, factor = classify_scaling_band(2.0, bands)
    assert label is None
    assert factor == 1.0


def test_classify_scaling_band_most_severe_crossed_band_wins_never_averaged() -> None:
    bands = [
        RiskContractScalingBand(threshold=4.0, factor=0.75, label="moderate"),
        RiskContractScalingBand(threshold=8.0, factor=0.5, label="severe"),
        RiskContractScalingBand(threshold=12.0, factor=0.0, label="kill"),
    ]
    label, factor = classify_scaling_band(9.0, bands)
    assert label == "severe"
    assert factor == 0.5


def test_classify_scaling_band_deterministic_same_input_same_output() -> None:
    bands = [RiskContractScalingBand(threshold=4.0, factor=0.75, label="a"), RiskContractScalingBand(threshold=8.0, factor=0.5, label="b")]
    results = {classify_scaling_band(6.0, bands) for _ in range(20)}
    assert len(results) == 1


# ---------------------------------------------------------------------------
# Dynamic scaling — evaluate_risk_contract_scaling
# ---------------------------------------------------------------------------


def test_evaluate_scaling_no_condition_met_returns_combined_factor_one() -> None:
    contract = mark_validated(_draft(), now_iso=NOW)
    scaling = evaluate_risk_contract_scaling(contract=contract, drawdown_pct=0.0, consecutive_losses=0)
    assert scaling.combined_factor == 1.0
    assert not scaling.kill_switch_triggered
    assert scaling.approved_risk_per_trade_pct == scaling.base_risk_per_trade_pct


def test_evaluate_scaling_drawdown_band_narrows_approved_risk() -> None:
    contract = mark_validated(_draft(limits=RiskLimits(riskPerTradePct=1.0, maxPositionPct=10.0)), now_iso=NOW)
    scaling = evaluate_risk_contract_scaling(contract=contract, drawdown_pct=5.0, consecutive_losses=0)
    assert scaling.drawdown_band_label == "moderate_drawdown"
    assert scaling.drawdown_factor == 0.75
    assert scaling.combined_factor == 0.75
    assert scaling.approved_risk_per_trade_pct == 0.75


def test_evaluate_scaling_composes_drawdown_and_losing_streak_multiplicatively() -> None:
    contract = mark_validated(_draft(limits=RiskLimits(riskPerTradePct=1.0)), now_iso=NOW)
    scaling = evaluate_risk_contract_scaling(contract=contract, drawdown_pct=5.0, consecutive_losses=3)
    # drawdown factor 0.75 * losing-streak factor 0.75 = 0.5625
    assert scaling.drawdown_factor == 0.75
    assert scaling.losing_streak_factor == 0.75
    assert abs(scaling.combined_factor - 0.5625) < 1e-9


def test_evaluate_scaling_kill_switch_at_drawdown_ceiling() -> None:
    contract = mark_validated(_draft(), now_iso=NOW)
    scaling = evaluate_risk_contract_scaling(contract=contract, drawdown_pct=15.0, consecutive_losses=0)
    assert scaling.kill_switch_triggered
    assert scaling.combined_factor == 0.0
    assert scaling.approved_risk_per_trade_pct == 0.0


def test_evaluate_scaling_disabled_ladder_never_applies_its_bands() -> None:
    policy = RiskContractScalingPolicy(drawdownScalingEnabled=False)
    contract = mark_validated(_draft(scaling_policy=policy), now_iso=NOW)
    scaling = evaluate_risk_contract_scaling(contract=contract, drawdown_pct=99.0, consecutive_losses=0)
    assert scaling.drawdown_factor == 1.0
    assert scaling.drawdown_band_label is None


def test_evaluate_scaling_respects_caller_supplied_base_over_contract_ceiling() -> None:
    # A caller already holding a further-tightened RiskLimits (e.g.
    # nexus.py's own effective_risk_limits) must see THAT reflected, not
    # silently discarded in favor of the contract's own raw ceiling.
    contract = mark_validated(_draft(limits=RiskLimits(riskPerTradePct=1.0)), now_iso=NOW)
    scaling = evaluate_risk_contract_scaling(contract=contract, drawdown_pct=0.0, consecutive_losses=0, base_risk_per_trade_pct=0.4, base_max_position_pct=3.0)
    assert scaling.base_risk_per_trade_pct == 0.4
    assert scaling.base_max_position_pct == 3.0


def test_evaluate_scaling_never_produces_a_negative_factor_downward_only_floor() -> None:
    contract = mark_validated(_draft(), now_iso=NOW)
    scaling = evaluate_risk_contract_scaling(contract=contract, drawdown_pct=1000.0, consecutive_losses=1000)
    assert scaling.combined_factor >= 0.0
    assert scaling.approved_risk_per_trade_pct >= 0.0


# ---------------------------------------------------------------------------
# apply_risk_contract_scaling — composition into RiskLimits
# ---------------------------------------------------------------------------


def test_apply_scaling_no_op_when_combined_factor_is_one() -> None:
    limits = RiskLimits(riskPerTradePct=1.0, maxPositionPct=10.0)
    contract = mark_validated(_draft(limits=limits), now_iso=NOW)
    scaling = evaluate_risk_contract_scaling(contract=contract, drawdown_pct=0.0, consecutive_losses=0)
    result = apply_risk_contract_scaling(limits, scaling=scaling)
    assert result is limits


def test_apply_scaling_narrows_risk_per_trade_and_max_position() -> None:
    limits = RiskLimits(riskPerTradePct=1.0, maxPositionPct=10.0)
    contract = mark_validated(_draft(limits=limits), now_iso=NOW)
    scaling = evaluate_risk_contract_scaling(contract=contract, drawdown_pct=5.0, consecutive_losses=0)
    result = apply_risk_contract_scaling(limits, scaling=scaling)
    assert result.risk_per_trade_pct == 0.75
    assert result.max_position_pct == 7.5
    # Every other field on the original RiskLimits is untouched — this is
    # a narrowing copy, never a full reconstruction.
    assert result.max_daily_loss_pct == limits.max_daily_loss_pct
    assert result.max_open_positions == limits.max_open_positions


def test_apply_scaling_never_widens_risk_limits() -> None:
    limits = RiskLimits(riskPerTradePct=1.0, maxPositionPct=10.0)
    contract = mark_validated(_draft(limits=limits), now_iso=NOW)
    scaling = evaluate_risk_contract_scaling(contract=contract, drawdown_pct=5.0, consecutive_losses=0)
    result = apply_risk_contract_scaling(limits, scaling=scaling)
    assert result.risk_per_trade_pct <= limits.risk_per_trade_pct
    assert result.max_position_pct <= limits.max_position_pct
