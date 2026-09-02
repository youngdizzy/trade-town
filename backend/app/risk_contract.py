"""app/risk_contract.py — CEO directive "TradeTown — Persisted Risk
Contract + Dynamic Risk Scaling."

PHASE 0 FORENSIC RECON, SUMMARIZED (the full three-pass recon is in this
session's own transcript). `app/schemas.py::RiskLimits` is this
codebase's one real, live-enforced risk boundary — but it is a single,
unversioned, mutable object (`app/state.py::update_risk_limits()`
mutates it in place, no history, no draft/active/superseded lifecycle).
`app/gatekeeper.py::evaluate_gatekeeper()` remains, unmodified, the ONE
real centralized risk gate (15 checks, pure `all()`) — this module never
adds a second gate. `app/position_sizing.py` already fully solves
volatility/regime/session/correlation-based sizing narrowing — this
module never re-implements any of that. `app/analytics.py::
max_drawdown_pct()` remains the one authoritative live-portfolio
drawdown formula, reused here unchanged. `app/trading_modes.py::
compute_consecutive_losses()` remains the one real consecutive-loss
counter, reused here unchanged.

WHAT THIS MODULE ADDS. A persisted, versioned `RiskContract` (Phase 1)
that WRAPS a real `RiskLimits` snapshot rather than re-declaring its ~29
fields under new names — the versioning shape is a deliberate,
line-for-line copy of this codebase's own already-proven precedent for
exactly this problem, `app/strategy_registry.py::register_strategy_
version()`: append-only history, `version = len(existing) + 1` (never a
caller-supplied number), immutable historical snapshots. A Dynamic Risk
Scaling engine (Phase 3) that generalizes `app/memecoin_sniper.py::
update_risk_state_after_trade()`'s own real, already-proven,
deterministic, DOWNWARD-ONLY `size_multiplier` pattern (previously
isolated to that one subsystem) into the main equities pipeline, using
the SAME `min(factor, ...)` band-composition idiom that module already
established. The scaling step composes into `app/nexus.py`'s existing
`effective_risk_limits` narrowing chain (alongside `apply_circuit_
breaker_tightening()`/`apply_travel_mode_tightening()`, which this
module imitates the exact shape of) — never a fourth, independent
tightening mechanic, never a second gate.

DELIBERATELY NOT IN THIS MODULE'S OWN SCALING POLICY: a volatility
factor (already solved, independently, by `app/position_sizing.py`'s
own real ATR/inverse-vol/regime/session caps — folding it in here too
would be a second, redundant implementation of the same real math) and
a "strategy health" factor (the real Strategy Health State Machine this
directive's own second half explicitly queues as separate, later work —
fabricating a placeholder factor ahead of that real system would violate
Section 19's "no performance fabrication" rule). Both are named,
disclosed cuts, not silent gaps.

FAIL-CLOSED WITHOUT BREAKING EVERY EXISTING SAVE. The directive's own
Phase 12 requires: "If the system cannot determine the active Risk
Contract... it should NOT approve a new paper trade." Taken literally on
an empty `risk_contracts` history (every save that predates this
feature), that would instantly halt trading for every existing player.
This module resolves that honestly rather than by fabrication or by
silently weakening the rule: `app/state.py::ensure_active_risk_contract()`
derives and PERSISTS a real v1 contract from the CEO's own actual,
already-configured `RiskLimits` the first time one is needed — never
invented numbers, and from that point forward a real, versioned contract
genuinely exists and every one of Phase 12's fail-closed guarantees
holds unconditionally.
"""
from __future__ import annotations

from app.schemas import (
    RiskContract,
    RiskContractScalingBand,
    RiskContractScalingPolicy,
    RiskContractScalingRead,
    RiskContractStatus,
    RiskContractValidationIssue,
    RiskContractValidationResult,
    RiskLimits,
)

# Section 20 ("Never let missing data weaken safety") applied to this
# module's own defaults: a genuinely unreachable factor floor, never
# negative (a negative factor would flip a "reduce risk" instruction
# into "take on debt-financed risk," meaningless in this domain).
_MIN_FACTOR = 0.0
_MAX_FACTOR = 1.0


def next_version_number(history: list[RiskContract]) -> int:
    """The real next version — `len(history) + 1`, never a caller-
    supplied guess. Direct analog of
    `app/strategy_registry.py::register_strategy_version()`'s own
    `len(existing_versions) + 1` rule."""
    return len(history) + 1


def create_draft_risk_contract(
    *,
    history: list[RiskContract],
    contract_id: str,
    limits: RiskLimits,
    created_by: str,
    reason: str,
    created_at: str,
    scaling_policy: RiskContractScalingPolicy | None = None,
    detail: str = "",
) -> RiskContract:
    """A real, new DRAFT version — never persisted as ACTIVE by this
    function alone (see `activate_risk_contract()` for the only real
    ACTIVE-producing step). `previous_version_id` names the currently
    ACTIVE contract, if any, so a reader can trace exactly what this
    draft would supersede."""
    previous = get_active_risk_contract(history)
    return RiskContract(
        id=contract_id,
        version=next_version_number(history),
        status="draft",
        createdAt=created_at,
        createdBy=created_by,
        reason=reason,
        limits=limits,
        scalingPolicy=scaling_policy if scaling_policy is not None else RiskContractScalingPolicy(),
        previousVersionId=previous.id if previous is not None else None,
        detail=detail or f"Draft risk contract v{next_version_number(history)}.",
    )


def _validate_bands(field: str, bands: list[RiskContractScalingBand]) -> list[RiskContractValidationIssue]:
    """Structural validation for one scaling ladder — real, disclosed
    rules: thresholds strictly increasing (a ladder, not an unordered
    set), factors within [0, 1] (Section 20: never a negative or
    risk-increasing factor), and factors non-increasing as threshold
    rises (Section 6/Phase 3's own "downward-only" invariant — a later,
    more severe band must never approve MORE risk than an earlier,
    milder one)."""
    issues: list[RiskContractValidationIssue] = []
    previous_threshold: float | None = None
    previous_factor: float | None = None
    for band in bands:
        if not (_MIN_FACTOR <= band.factor <= _MAX_FACTOR):
            issues.append(RiskContractValidationIssue(field=f"{field}.{band.label}.factor", category="structural", message=f"Scaling factor {band.factor} for band '{band.label}' must be within [0.0, 1.0]."))
        if previous_threshold is not None and band.threshold <= previous_threshold:
            issues.append(RiskContractValidationIssue(field=f"{field}.{band.label}.threshold", category="structural", message=f"Band '{band.label}' threshold {band.threshold} must be strictly greater than the previous band's threshold {previous_threshold} — bands must form a real, ordered ladder."))
        if previous_factor is not None and band.factor > previous_factor:
            issues.append(RiskContractValidationIssue(field=f"{field}.{band.label}.factor", category="policy", message=f"Band '{band.label}' factor {band.factor} is larger than an earlier, milder band's factor {previous_factor} — scaling must be downward-only as severity increases (never increase risk to recover losses)."))
        previous_threshold = band.threshold
        previous_factor = band.factor
    return issues


def validate_risk_contract(contract: RiskContract) -> RiskContractValidationResult:
    """Phase 2 — structural validation (malformed data) kept explicitly
    separate from policy validation (structurally valid but risk-unwise)
    per the directive's own instruction. Never blocks on an opinion this
    module can't actually justify — every issue below cites a concrete,
    checkable reason."""
    issues: list[RiskContractValidationIssue] = []
    limits = contract.limits

    # Structural: malformed/out-of-range numeric configuration.
    if contract.version <= 0:
        issues.append(RiskContractValidationIssue(field="version", category="structural", message="version must be a positive integer."))
    if limits.risk_per_trade_pct <= 0:
        issues.append(RiskContractValidationIssue(field="limits.riskPerTradePct", category="structural", message="risk_per_trade_pct must be positive."))
    if limits.max_position_pct <= 0:
        issues.append(RiskContractValidationIssue(field="limits.maxPositionPct", category="structural", message="max_position_pct must be positive."))
    if limits.max_daily_loss_pct <= 0:
        issues.append(RiskContractValidationIssue(field="limits.maxDailyLossPct", category="structural", message="max_daily_loss_pct must be positive."))
    if limits.max_drawdown_pct <= 0:
        issues.append(RiskContractValidationIssue(field="limits.maxDrawdownPct", category="structural", message="max_drawdown_pct must be positive."))
    if limits.max_open_positions <= 0:
        issues.append(RiskContractValidationIssue(field="limits.maxOpenPositions", category="structural", message="max_open_positions must be positive."))
    if limits.max_correlated_positions <= 0:
        issues.append(RiskContractValidationIssue(field="limits.maxCorrelatedPositions", category="structural", message="max_correlated_positions must be positive."))
    issues.extend(_validate_bands("scalingPolicy.drawdownBands", contract.scaling_policy.drawdown_bands))
    issues.extend(_validate_bands("scalingPolicy.losingStreakBands", contract.scaling_policy.losing_streak_bands))

    # Policy: structurally valid, but internally inconsistent as a real
    # risk policy.
    if limits.max_daily_loss_pct > limits.max_drawdown_pct:
        issues.append(RiskContractValidationIssue(field="limits.maxDailyLossPct", category="policy", message=f"max_daily_loss_pct ({limits.max_daily_loss_pct:g}%) exceeds max_drawdown_pct ({limits.max_drawdown_pct:g}%) — a single day could exhaust more than the contract's own lifetime drawdown ceiling allows."))
    drawdown_kill_bands = [b for b in contract.scaling_policy.drawdown_bands if b.factor == 0.0]
    if drawdown_kill_bands:
        kill_threshold = min(b.threshold for b in drawdown_kill_bands)
        if kill_threshold > limits.max_drawdown_pct:
            issues.append(RiskContractValidationIssue(field="scalingPolicy.drawdownBands", category="policy", message=f"The drawdown kill-switch threshold ({kill_threshold:g}%) is beyond max_drawdown_pct ({limits.max_drawdown_pct:g}%) — the hard drawdown ceiling would already be breached before this contract's own kill switch could ever fire."))

    return RiskContractValidationResult(valid=not issues, issues=issues)


def mark_validated(contract: RiskContract, *, now_iso: str) -> RiskContract:
    """A real, disclosed transition — only from `draft`, never skips a
    real validation pass (raises otherwise)."""
    if contract.status != "draft":
        raise ValueError(f"Only a draft risk contract can be marked validated (got status={contract.status!r}).")
    result = validate_risk_contract(contract)
    if not result.valid:
        raise ValueError(f"Risk contract {contract.id} failed validation: {[i.message for i in result.issues]}")
    return contract.model_copy(update={"status": "validated", "detail": f"{contract.detail} Validated {now_iso}."})


def activate_risk_contract(history: list[RiskContract], contract_id: str, *, now_iso: str) -> tuple[RiskContract, list[RiskContract]]:
    """The one real ACTIVE-producing step. Requires the named contract
    to already be `validated` (raises otherwise — an unvalidated
    contract can never become the live ceiling). Supersedes whatever
    contract is currently `active`, in the SAME real, atomic update —
    there is never a moment with two simultaneously-active contracts,
    and the previous version's own historical record is never rewritten
    (only its `status`/`supersededAt` change; every trade/decision that
    already referenced its `id`/`version` keeps a valid, immutable
    reference)."""
    target = next((c for c in history if c.id == contract_id), None)
    if target is None:
        raise ValueError(f"No risk contract with id {contract_id!r} exists in this history.")
    if target.status != "validated":
        raise ValueError(f"Risk contract {contract_id} must be 'validated' before activation (got status={target.status!r}).")

    activated = target.model_copy(update={"status": "active", "activated_at": now_iso})
    updated_history: list[RiskContract] = []
    for c in history:
        if c.id == contract_id:
            updated_history.append(activated)
        elif c.status == "active":
            updated_history.append(c.model_copy(update={"status": "superseded", "superseded_at": now_iso}))
        else:
            updated_history.append(c)
    return activated, updated_history


def get_active_risk_contract(history: list[RiskContract]) -> RiskContract | None:
    """The real, single source of truth for "which contract governs
    trading right now" — a contract is ACTIVE by construction of
    `activate_risk_contract()` (which enforces at most one at a time),
    so this never needs to pick among candidates."""
    return next((c for c in history if c.status == "active"), None)


def get_risk_contract_version(history: list[RiskContract], contract_id: str, version: int) -> RiskContract | None:
    """Resolves a real, historical, immutable snapshot by (id, version)
    — the same real lookup shape as
    `app/strategy_registry.py::get_compiled_definition_version()`, for a
    persisted `RiskDecision` to look up exactly which contract state
    governed it, long after that version may have been superseded."""
    return next((c for c in history if c.id == contract_id and c.version == version), None)


def archive_risk_contract(history: list[RiskContract], contract_id: str, *, now_iso: str) -> list[RiskContract]:
    """Real, disclosed terminal transition — reachable from any
    non-active state (an active contract must be superseded by
    activating its replacement first, never archived out from under
    live trading)."""
    target = next((c for c in history if c.id == contract_id), None)
    if target is None:
        raise ValueError(f"No risk contract with id {contract_id!r} exists in this history.")
    if target.status == "active":
        raise ValueError(f"Risk contract {contract_id} is active — activate a replacement version instead of archiving the live contract directly.")
    return [c.model_copy(update={"status": "archived", "archived_at": now_iso}) if c.id == contract_id else c for c in history]


def classify_scaling_band(value: float, bands: list[RiskContractScalingBand]) -> tuple[str | None, float]:
    """The real, deterministic band-selection rule — the exact same
    `factor = min(factor, band.factor)` composition
    `app/memecoin_sniper.py::update_risk_state_after_trade()` already
    established, generalized from that module's two hardcoded checks
    into a real, CEO-editable ladder. Every band whose threshold `value`
    has reached or exceeded contributes its own factor; the MOST severe
    (smallest) factor wins — never averaged, never interpolated. Returns
    `(None, 1.0)` when no band's threshold was crossed."""
    factor = _MAX_FACTOR
    label: str | None = None
    for band in bands:
        if value >= band.threshold and band.factor <= factor:
            factor = band.factor
            label = band.label
    return label, factor


def evaluate_risk_contract_scaling(
    *,
    contract: RiskContract,
    drawdown_pct: float,
    consecutive_losses: int,
    base_risk_per_trade_pct: float | None = None,
    base_max_position_pct: float | None = None,
) -> RiskContractScalingRead:
    """Section "Scaling Transparency" — one real, disclosed, itemized
    evaluation. `base_risk_per_trade_pct`/`base_max_position_pct`
    default to the contract's own `limits` values, but a caller already
    holding a further-tightened `RiskLimits` (e.g. `app/nexus.py`'s own
    `effective_risk_limits`, after Company Priority/Circuit-Breaker/
    Travel-Mode composition) may pass those instead, so this reflects
    this mechanism's own real marginal effect on top of whatever was
    already true — never silently discarding an earlier, real
    tightening step."""
    base_risk = base_risk_per_trade_pct if base_risk_per_trade_pct is not None else contract.limits.risk_per_trade_pct
    base_position = base_max_position_pct if base_max_position_pct is not None else contract.limits.max_position_pct

    drawdown_label: str | None = None
    drawdown_factor = 1.0
    if contract.scaling_policy.drawdown_scaling_enabled:
        drawdown_label, drawdown_factor = classify_scaling_band(drawdown_pct, contract.scaling_policy.drawdown_bands)

    losing_streak_label: str | None = None
    losing_streak_factor = 1.0
    if contract.scaling_policy.losing_streak_scaling_enabled:
        losing_streak_label, losing_streak_factor = classify_scaling_band(float(consecutive_losses), contract.scaling_policy.losing_streak_bands)

    combined_factor = round(drawdown_factor * losing_streak_factor, 6)
    approved_risk = round(base_risk * combined_factor, 4)
    approved_position = round(base_position * combined_factor, 4)
    kill_switch_triggered = combined_factor <= 0.0

    detail_parts = [f"Contract v{contract.version} ceiling {base_risk:g}% risk/trade."]
    if drawdown_label is not None:
        detail_parts.append(f"Drawdown {drawdown_pct:.2f}% crossed '{drawdown_label}' -> factor {drawdown_factor:g}.")
    else:
        detail_parts.append(f"Drawdown {drawdown_pct:.2f}% within normal range -> factor {drawdown_factor:g}.")
    if losing_streak_label is not None:
        detail_parts.append(f"{consecutive_losses} consecutive losses crossed '{losing_streak_label}' -> factor {losing_streak_factor:g}.")
    else:
        detail_parts.append(f"{consecutive_losses} consecutive losses -> factor {losing_streak_factor:g}.")
    detail_parts.append(f"Combined factor {combined_factor:g}. Approved risk {approved_risk:g}% (was {base_risk:g}%).")
    if kill_switch_triggered:
        detail_parts.append("KILL SWITCH: combined factor reached 0.0 — no new risk approved.")

    return RiskContractScalingRead(
        riskContractId=contract.id,
        riskContractVersion=contract.version,
        drawdownPct=round(drawdown_pct, 4),
        drawdownBandLabel=drawdown_label,
        drawdownFactor=drawdown_factor,
        consecutiveLosses=consecutive_losses,
        losingStreakBandLabel=losing_streak_label,
        losingStreakFactor=losing_streak_factor,
        combinedFactor=combined_factor,
        baseRiskPerTradePct=round(base_risk, 4),
        approvedRiskPerTradePct=approved_risk,
        baseMaxPositionPct=round(base_position, 4),
        approvedMaxPositionPct=approved_position,
        killSwitchTriggered=kill_switch_triggered,
        detail=" ".join(detail_parts),
    )


def apply_risk_contract_scaling(limits: RiskLimits, *, scaling: RiskContractScalingRead) -> RiskLimits:
    """A derived, non-persisted `RiskLimits` copy — the identical
    pattern `app/nexus.py::_effective_risk_limits()`/
    `app/trading_modes.py::apply_circuit_breaker_tightening()`/
    `apply_travel_mode_tightening()` already use, composed as one more
    real narrowing step in that same chain (never a fourth, independent
    tightening mechanic, never mutates or persists over the CEO's own
    configured `RiskLimits`). A `combinedFactor` of 1.0 (no real
    scaling condition met) returns `limits` unchanged."""
    if scaling.combined_factor >= 1.0:
        return limits
    return limits.model_copy(
        update={
            "risk_per_trade_pct": scaling.approved_risk_per_trade_pct,
            "max_position_pct": scaling.approved_max_position_pct,
        }
    )


__all__ = [
    "RiskContractStatus",
    "next_version_number",
    "create_draft_risk_contract",
    "validate_risk_contract",
    "mark_validated",
    "activate_risk_contract",
    "get_active_risk_contract",
    "get_risk_contract_version",
    "archive_risk_contract",
    "classify_scaling_band",
    "evaluate_risk_contract_scaling",
    "apply_risk_contract_scaling",
]
