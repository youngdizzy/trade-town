"""Mobile Command Center & Remote Operations — Design Bible Chapter 73.5
(see docs/DesignBible/volumes/09-departments/chapter-73-5-mobile-
command-center-remote-operations.md for the full honesty boundary).

Travel Mode is the one real, load-bearing mechanic this chapter adds
server-side: a CEO-configurable conservative operating posture that
composes with Company Priority's and Chapter 75's own derived-override
seam (app/nexus.py's `_effective_risk_limits()` / `min_confidence_
override`) rather than inventing a fourth parallel tightening
mechanic — this codebase has exactly three tightening patterns
(Company Priority, Chapter 72's Defensive Mode, Chapter 75's Circuit
Breaker), confirmed by direct inspection before writing this module.
Like the Circuit Breaker — and unlike Defensive Mode — it never
mutates the CEO's own persisted `RiskLimits`; it derives a fresh,
non-persisted copy every tick.

Manual activation/deactivation is real. "Automatic" activation is real
but honestly narrower than the brief's calendar-based description: this
codebase has no wall-clock/timezone/calendar concept tied to the
player's real-life schedule, only a simulated in-game day counter — so
automatic activation instead reacts to a real, measurable signal: how
long the CEO has actually gone without taking a real action on a
pending trade decision (`should_auto_activate`). Calendar-based
"scheduled" activation is not built — see the chapter's own
Implementation Notes.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.schemas import (
    CeoDecisionRecord,
    GatekeeperRejection,
    MemoryRecord,
    PaperPortfolio,
    RiskLimits,
    RiskWarning,
    TravelModeActivationSource,
    TravelModeBriefing,
    TravelModeSettings,
    TravelModeState,
)

MAX_TRAVEL_MODE_BRIEFINGS = 20

# Disclosed floor/ceiling on the CEO's own configurable caps — the same
# "conservative but arbitrary, no real regulatory requirement behind it"
# honesty already carried by RiskLimits itself.
SETTINGS_PCT_FLOOR = 25.0
SETTINGS_PCT_CEILING = 75.0
AUTO_ACTIVATE_MINUTES_FLOOR = 15
AUTO_ACTIVATE_MINUTES_CEILING = 240

# Sits between Chapter 75's Tier 1 (10) and Tier 2 (20) Gatekeeper
# confidence bonus — a real, disclosed, mid-severity posture in its own
# right, not a Circuit Breaker tier itself. Composes with any active
# tier's own bonus via max(), never adds on top of it (see
# app/nexus.py's tick()).
TRAVEL_MODE_CONFIDENCE_BONUS = 15.0


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clamp_settings(settings: TravelModeSettings) -> TravelModeSettings:
    return settings.model_copy(
        update={
            "position_size_cap_pct": max(SETTINGS_PCT_FLOOR, min(SETTINGS_PCT_CEILING, settings.position_size_cap_pct)),
            "daily_risk_cap_pct": max(SETTINGS_PCT_FLOOR, min(SETTINGS_PCT_CEILING, settings.daily_risk_cap_pct)),
            "auto_activate_after_minutes": max(
                AUTO_ACTIVATE_MINUTES_FLOOR, min(AUTO_ACTIVATE_MINUTES_CEILING, settings.auto_activate_after_minutes)
            ),
        }
    )


def update_travel_mode_settings(state: TravelModeState, update: dict[str, object]) -> TravelModeState:
    """The CEO's real settings PATCH — clamps every bounded field to its
    disclosed floor/ceiling (see module docstring) rather than trusting
    client input directly."""
    new_settings = _clamp_settings(state.settings.model_copy(update=update))
    return state.model_copy(update={"settings": new_settings})


def activate_travel_mode(
    state: TravelModeState, *, source: TravelModeActivationSource, now_iso: str, now_sim_minutes: int
) -> tuple[TravelModeState, MemoryRecord]:
    updated = state.model_copy(
        update={
            "active": True,
            "activated_at": now_iso,
            "activation_source": source,
            "deactivated_at": None,
            "activated_sim_minutes": now_sim_minutes,
        }
    )
    reason = (
        "the CEO manually activated it"
        if source == "manual"
        else f"{state.settings.auto_activate_after_minutes} simulated minutes passed with no CEO decision activity"
    )
    memory = MemoryRecord(
        id=f"travel-mode-on-{now_sim_minutes}",
        category="alert",
        title="Travel Mode activated",
        body=(
            f"Travel Mode is now active — {reason}. Position sizing capped at "
            f"{state.settings.position_size_cap_pct:.0f}% of normal, daily risk capped at "
            f"{state.settings.daily_risk_cap_pct:.0f}%, notification sensitivity set to "
            f"{state.settings.notification_sensitivity.replace('_', ' ')}."
        ),
        timestamp=now_iso,
    )
    return updated, memory


def deactivate_travel_mode(state: TravelModeState, *, now_iso: str) -> tuple[TravelModeState, MemoryRecord]:
    updated = state.model_copy(update={"active": False, "deactivated_at": now_iso, "activation_source": None})
    memory = MemoryRecord(
        id=f"travel-mode-off-{now_iso}",
        category="alert",
        title="Travel Mode deactivated",
        body="The CEO returned to full operations — Travel Mode's tightened limits and notification filter are lifted.",
        timestamp=now_iso,
    )
    return updated, memory


def apply_travel_mode_tightening(limits: RiskLimits, travel_mode: TravelModeState) -> RiskLimits:
    """A derived, non-persisted RiskLimits copy — the identical pattern
    Chapter 75's `apply_circuit_breaker_tightening()` already uses.
    Composes with that function's own output in app/nexus.py (Travel
    Mode applies on top of whatever the Circuit Breaker already
    produced), never independently of it."""
    if not travel_mode.active:
        return limits
    settings = travel_mode.settings
    position_factor = settings.position_size_cap_pct / 100.0
    risk_factor = settings.daily_risk_cap_pct / 100.0
    return limits.model_copy(
        update={
            "risk_per_trade_pct": round(limits.risk_per_trade_pct * risk_factor, 2),
            "max_position_pct": round(limits.max_position_pct * position_factor, 2),
            "max_open_positions": max(1, limits.max_open_positions // 2),
        }
    )


def travel_mode_confidence_bonus(travel_mode: TravelModeState) -> float:
    """The real, disclosed points added to Gatekeeper's minimum
    confidence threshold while Travel Mode is active — see
    app/gatekeeper.py's evaluate_gatekeeper() min_confidence_override
    param."""
    return TRAVEL_MODE_CONFIDENCE_BONUS if travel_mode.active else 0.0


def should_auto_activate(travel_mode: TravelModeState, last_ceo_decision_sim_minutes: int | None, now_sim_minutes: int) -> bool:
    """A real, measurable "the CEO has actually gone quiet" signal —
    never a calendar or clock-time-of-day check, neither of which this
    codebase has. Only fires when the CEO opted in
    (`auto_activate_enabled`) and Travel Mode isn't already active."""
    if travel_mode.active or not travel_mode.settings.auto_activate_enabled:
        return False
    if last_ceo_decision_sim_minutes is None:
        return False
    return now_sim_minutes - last_ceo_decision_sim_minutes >= travel_mode.settings.auto_activate_after_minutes


def generate_travel_mode_briefing(
    travel_mode: TravelModeState,
    *,
    now_sim_minutes: int,
    now_iso: str,
    memory: list[MemoryRecord],
    ceo_decisions: list[CeoDecisionRecord],
    gatekeeper_rejections: list[GatekeeperRejection],
    risk_warnings: list[RiskWarning],
    portfolio: PaperPortfolio,
    briefing_id: str,
) -> TravelModeBriefing:
    """The real Return-to-Full-Operations briefing, built entirely from
    real records inside [activated_at, now] / [activated_sim_minutes,
    now_sim_minutes] — never a templated recap. Circuit Breaker tier
    changes are counted from the same real MemoryRecords
    `build_circuit_breaker_tier_memory()` already writes — never a
    second, independently-tracked count."""
    activated_at = travel_mode.activated_at or now_iso
    start_sim = travel_mode.activated_sim_minutes

    window_decisions = [d for d in ceo_decisions if d.resolved_at is not None and d.resolved_at >= activated_at]
    window_rejections = [r for r in gatekeeper_rejections if start_sim <= r.rejected_sim_minutes <= now_sim_minutes]
    window_warnings = [w for w in risk_warnings if w.severity == "critical" and w.created_at >= activated_at]
    window_tier_changes = [m for m in memory if m.timestamp >= activated_at and "Circuit Breaker" in m.title]
    window_trades = [t for t in portfolio.trade_history if start_sim <= t.closed_sim_minutes <= now_sim_minutes]
    realized_pnl = round(sum(t.pnl for t in window_trades), 2)

    duration_minutes = max(0, now_sim_minutes - start_sim)
    summary = (
        f"Travel Mode was active for {duration_minutes} simulated minute(s) "
        f"({travel_mode.activation_source or 'manual'}). "
        f"{len(window_decisions)} CEO decision(s) resolved, {len(window_rejections)} Gatekeeper "
        f"rejection(s), {len(window_warnings)} critical risk warning(s), {len(window_tier_changes)} "
        f"Circuit Breaker tier change(s), realized P&L {realized_pnl:+.2f}."
    )
    return TravelModeBriefing(
        id=briefing_id,
        activatedAt=activated_at,
        deactivatedAt=now_iso,
        activationSource=travel_mode.activation_source or "manual",
        decisionsResolved=len(window_decisions),
        gatekeeperRejections=len(window_rejections),
        criticalRiskWarnings=len(window_warnings),
        circuitBreakerTierChanges=len(window_tier_changes),
        realizedPnl=realized_pnl,
        summary=summary,
        createdAt=now_iso,
    )
