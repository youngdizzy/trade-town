import { useEffect, useState } from "react";
import { api } from "@/net/api";
import type { ResearchCategory, RestrictionScope, TradingRestriction } from "@/types";
import { Glass, StatusPill, TerminalLabel } from "../ui";

const CATEGORY_OPTIONS: ResearchCategory[] = ["stock", "etf", "index", "economy", "gold", "bitcoin", "company", "sector"];

const inputClass = "rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1 text-cmd-text outline-none focus:border-cmd-cyan/50";

/**
 * CEO directive "Layered Kill Switches" — the one layer below the
 * firm-wide Emergency Stop (see EmergencyStop's own dedicated control
 * elsewhere in the UI): a real, scoped, reversible halt on new
 * position-opening for one symbol or one whole category
 * (backend/app/trading_restrictions.py). Never a partial halt — an
 * active restriction blocks both buy and sell on its target.
 */
export function TradingRestrictionsCard() {
  const [restrictions, setRestrictions] = useState<TradingRestriction[] | null>(null);
  const [scope, setScope] = useState<RestrictionScope>("symbol");
  const [target, setTarget] = useState("");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [liftingId, setLiftingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = () => api.getTradingRestrictions().then((res) => setRestrictions(res.tradingRestrictions)).catch(() => undefined);

  useEffect(() => {
    load();
    const interval = setInterval(load, 15_000);
    return () => clearInterval(interval);
  }, []);

  const activate = async () => {
    if (!target.trim() || !reason.trim()) {
      setError("Target and reason are both required.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const res = await api.activateTradingRestriction(scope, target.trim(), reason.trim());
      setRestrictions(res.tradingRestrictions);
      setTarget("");
      setReason("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to activate the restriction.");
    } finally {
      setBusy(false);
    }
  };

  const lift = async (restrictionId: string) => {
    setLiftingId(restrictionId);
    setError(null);
    try {
      const res = await api.liftTradingRestriction(restrictionId, "");
      setRestrictions(res.tradingRestrictions);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to lift the restriction.");
    } finally {
      setLiftingId(null);
    }
  };

  if (restrictions === null) return null;

  const active = restrictions.filter((r) => r.active);
  const history = restrictions.filter((r) => !r.active);

  return (
    <Glass className="p-3">
      <div className="mb-1.5 flex items-center justify-between">
        <TerminalLabel>Trading Restrictions — layered kill switches</TerminalLabel>
        <span className="text-[8px] uppercase tracking-wide text-cmd-textDim">below Emergency Stop</span>
      </div>
      <div className="text-[9px] text-cmd-textDim">
        Halts new buy AND sell on one symbol or one whole category — never a partial halt. Already-open positions are never force-closed.
      </div>

      {active.length > 0 && (
        <div className="mt-2 space-y-1">
          {active.map((r) => (
            <div key={r.id} className="flex items-center justify-between rounded-sm border border-cmd-red/40 bg-cmd-red/5 px-2 py-1.5 text-[9px]">
              <div>
                <span className="text-cmd-red">{r.scope === "symbol" ? "SYMBOL" : "CATEGORY"}</span>{" "}
                <span className="text-cmd-text">{r.target}</span>
                <div className="mt-0.5 text-cmd-textDim">{r.reason}</div>
              </div>
              <button
                type="button"
                onClick={() => void lift(r.id)}
                disabled={liftingId === r.id}
                className="ml-2 shrink-0 rounded-sm border border-cmd-cyan/50 px-2 py-1 uppercase tracking-wider text-cmd-cyan hover:bg-cmd-cyan/10 disabled:opacity-40"
              >
                {liftingId === r.id ? "Lifting…" : "Lift"}
              </button>
            </div>
          ))}
        </div>
      )}
      {active.length === 0 && <div className="mt-2 text-[9px] text-cmd-textDim">No active trading restrictions right now.</div>}

      <div className="mt-3 grid grid-cols-1 gap-2 border-t border-cmd-border/50 pt-3 sm:grid-cols-4">
        <label className="flex flex-col gap-1 text-[9px] text-cmd-textDim">
          Scope
          <select value={scope} onChange={(e) => setScope(e.target.value as RestrictionScope)} className={inputClass}>
            <option value="symbol">Symbol</option>
            <option value="category">Category</option>
          </select>
        </label>
        <label className="flex flex-col gap-1 text-[9px] text-cmd-textDim">
          {scope === "symbol" ? "Symbol" : "Category"}
          {scope === "symbol" ? (
            <input type="text" value={target} onChange={(e) => setTarget(e.target.value.toUpperCase())} placeholder="e.g. NEXA" className={inputClass} />
          ) : (
            <select value={target} onChange={(e) => setTarget(e.target.value)} className={inputClass}>
              <option value="">Select…</option>
              {CATEGORY_OPTIONS.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          )}
        </label>
        <label className="flex flex-col gap-1 text-[9px] text-cmd-textDim sm:col-span-2">
          Reason
          <input type="text" value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Why is this being restricted?" className={inputClass} />
        </label>
      </div>
      <button
        type="button"
        onClick={() => void activate()}
        disabled={busy}
        className="mt-2 rounded-sm border border-cmd-red/50 px-3 py-1 text-[9px] uppercase tracking-wider text-cmd-red hover:bg-cmd-red/10 disabled:opacity-40"
      >
        {busy ? "Activating…" : "Activate Restriction"}
      </button>
      {error && <div className="mt-1.5 text-[9px] text-cmd-red">{error}</div>}

      {history.length > 0 && (
        <div className="mt-3 border-t border-cmd-border/50 pt-2">
          <div className="mb-1 text-[9px] text-cmd-textDim">History ({history.length})</div>
          <div className="space-y-1">
            {history.map((r) => (
              <div key={r.id} className="flex items-center justify-between text-[9px] text-cmd-textDim">
                <span>
                  <StatusPill tone="neutral">LIFTED</StatusPill> {r.scope} {r.target} — {r.reason}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </Glass>
  );
}
