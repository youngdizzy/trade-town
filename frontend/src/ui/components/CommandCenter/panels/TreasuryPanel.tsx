import { useMemo, useState } from "react";
import { useGameStore } from "@/ui/hooks/useGameStore";
import { NexusManager } from "@/game/systems/NexusManager";
import { api } from "@/net/api";
import type { SavingsRuleType, TreasuryTransaction } from "@/types";
import { DataRow, EmptyState, Glass, StatusPill, TerminalLabel } from "../ui";

const RULE_LABEL: Record<SavingsRuleType, string> = {
  percent_of_monthly_profit: "% of Monthly Profit",
  excess_above_reserve: "Excess Above Reserve",
};

const TXN_TONE: Record<TreasuryTransaction["kind"], "green" | "amber" | "cyan"> = {
  deposit: "green",
  withdrawal: "amber",
  auto_save: "cyan",
};

/**
 * v0.7 Feature 33 — the CEO Treasury. Every number here is real: the
 * Treasury balance is a second account structurally isolated from
 * Operating Capital (paperPortfolio.cashBalance) — see
 * backend/app/treasury.py's module docstring for the "no automatic
 * system ever touches it" guarantee. Deposit/Withdraw are real,
 * validated transfers; Smart Savings Rules are the one deliberate
 * exception, and only because the CEO explicitly configured them (and
 * can pause them here at any time). The Savings Growth Timeline reuses
 * the same real transaction log rather than a second, redundant series.
 * No new physical vault-door room was built for this feature — the same
 * Command-Center-tab precedent every recent feature has followed — this
 * panel is the Treasury.
 */
export function TreasuryPanel() {
  const { treasury, paperPortfolio } = useGameStore();
  const [amount, setAmount] = useState("1000");
  const [busy, setBusy] = useState<"deposit" | "withdraw" | "rule" | "pause" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [ruleType, setRuleType] = useState<SavingsRuleType>("percent_of_monthly_profit");
  const [rulePercent, setRulePercent] = useState("10");
  const [ruleReserve, setRuleReserve] = useState("50000");

  const reservePct = treasury.balance + paperPortfolio.cashBalance > 0 ? (treasury.balance / (treasury.balance + paperPortfolio.cashBalance)) * 100 : 0;
  const recentTxns = useMemo(() => [...treasury.transactions].reverse().slice(0, 40), [treasury.transactions]);
  const recentReports = useMemo(() => [...treasury.monthlyReports].reverse(), [treasury.monthlyReports]);

  const runAmount = async (kind: "deposit" | "withdraw") => {
    const value = Number(amount);
    if (!value || value <= 0 || busy) return;
    setBusy(kind);
    setError(null);
    try {
      const res = kind === "deposit" ? await api.depositTreasury(value) : await api.withdrawTreasury(value);
      NexusManager.setTreasury(res.treasury);
      NexusManager.setPaperPortfolio(res.paperPortfolio);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(null);
    }
  };

  const createRule = async () => {
    if (busy) return;
    setBusy("rule");
    setError(null);
    try {
      const res = await api.createSavingsRule(ruleType, Number(rulePercent), ruleType === "excess_above_reserve" ? Number(ruleReserve) : null);
      NexusManager.setTreasury(res.treasury);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(null);
    }
  };

  const toggleRule = async (ruleId: string, active: boolean) => {
    if (busy) return;
    try {
      const res = await api.toggleSavingsRule(ruleId, active);
      NexusManager.setTreasury(res.treasury);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  const pauseAll = async () => {
    if (busy) return;
    setBusy("pause");
    try {
      const res = await api.pauseAllSavingsRules();
      NexusManager.setTreasury(res.treasury);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
      <Glass className="p-3 lg:col-span-3">
        <div className="mb-2 grid grid-cols-1 gap-3 sm:grid-cols-3">
          <div className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-2.5">
            <TerminalLabel>Operating Capital</TerminalLabel>
            <div data-testid="operating-capital-balance" className="font-cmdmono text-xl text-cmd-text">
              ${paperPortfolio.cashBalance.toLocaleString(undefined, { maximumFractionDigits: 0 })}
            </div>
          </div>
          <div className="rounded-sm border border-cmd-cyan/40 bg-cmd-cyan/5 p-2.5">
            <TerminalLabel>CEO Treasury</TerminalLabel>
            <div data-testid="treasury-balance" className="font-cmdmono text-xl text-cmd-cyan">
              ${treasury.balance.toLocaleString(undefined, { maximumFractionDigits: 0 })}
            </div>
          </div>
          <div className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-2.5">
            <TerminalLabel>Reserve Percentage</TerminalLabel>
            <div className="font-cmdmono text-xl text-cmd-text">{reservePct.toFixed(1)}%</div>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 border-t border-cmd-border/50 pt-2 sm:grid-cols-4">
          <DataRow label="Lifetime Deposits" value={`$${treasury.lifetimeDeposits.toLocaleString(undefined, { maximumFractionDigits: 0 })}`} />
          <DataRow label="Largest Balance" value={`$${treasury.largestBalance.toLocaleString(undefined, { maximumFractionDigits: 0 })}`} />
          <DataRow label="Transactions" value={String(treasury.transactions.length)} />
          <DataRow label="Active Rules" value={String(treasury.savingsRules.filter((r) => r.active).length)} />
        </div>
      </Glass>

      <Glass className="p-3">
        <TerminalLabel>Deposit / Withdraw</TerminalLabel>
        <input
          type="number"
          min={1}
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          className="mb-2 w-full rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1.5 text-[10px] text-cmd-text focus:border-cmd-cyan/50 focus:outline-none"
        />
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => void runAmount("deposit")}
            disabled={busy !== null}
            className="flex-1 rounded-sm border border-cmd-green/50 py-1.5 text-[10px] uppercase tracking-wider text-cmd-green transition-colors hover:bg-cmd-green/10 disabled:opacity-40"
          >
            {busy === "deposit" ? "…" : "Deposit ▸"}
          </button>
          <button
            type="button"
            onClick={() => void runAmount("withdraw")}
            disabled={busy !== null}
            className="flex-1 rounded-sm border border-cmd-amber/50 py-1.5 text-[10px] uppercase tracking-wider text-cmd-amber transition-colors hover:bg-cmd-amber/10 disabled:opacity-40"
          >
            {busy === "withdraw" ? "…" : "◂ Withdraw"}
          </button>
        </div>
        <p className="mt-2 text-[9px] text-cmd-textDim">Untouchable by any automated system — every transfer here is a deliberate CEO action.</p>
        {error && <div className="mt-2 text-[9px] text-cmd-red">{error}</div>}
      </Glass>

      <Glass className="p-3 lg:col-span-2">
        <TerminalLabel>Smart Savings Rules</TerminalLabel>
        <div className="mb-2 flex flex-wrap items-end gap-2">
          <select
            value={ruleType}
            onChange={(e) => setRuleType(e.target.value as SavingsRuleType)}
            className="rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1.5 text-[10px] text-cmd-text focus:border-cmd-cyan/50 focus:outline-none"
          >
            <option value="percent_of_monthly_profit">Save % of monthly profit</option>
            <option value="excess_above_reserve">Save excess above reserve</option>
          </select>
          {ruleType === "percent_of_monthly_profit" ? (
            <input
              type="number"
              min={1}
              max={100}
              value={rulePercent}
              onChange={(e) => setRulePercent(e.target.value)}
              className="w-16 rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1.5 text-[10px] text-cmd-text focus:border-cmd-cyan/50 focus:outline-none"
            />
          ) : (
            <input
              type="number"
              min={0}
              value={ruleReserve}
              onChange={(e) => setRuleReserve(e.target.value)}
              className="w-24 rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1.5 text-[10px] text-cmd-text focus:border-cmd-cyan/50 focus:outline-none"
            />
          )}
          <button
            type="button"
            onClick={() => void createRule()}
            disabled={busy !== null}
            className="rounded-sm border border-cmd-cyan/50 px-3 py-1.5 text-[10px] uppercase tracking-wider text-cmd-cyan transition-colors hover:bg-cmd-cyan/10 disabled:opacity-40"
          >
            {busy === "rule" ? "…" : "Create Rule"}
          </button>
          <button
            type="button"
            onClick={() => void pauseAll()}
            disabled={busy !== null || treasury.savingsRules.every((r) => !r.active)}
            className="ml-auto rounded-sm border border-cmd-red/40 px-3 py-1.5 text-[10px] uppercase tracking-wider text-cmd-red transition-colors hover:bg-cmd-red/10 disabled:opacity-40"
          >
            Pause All
          </button>
        </div>
        {treasury.savingsRules.length === 0 ? (
          <EmptyState>No Smart Savings Rules yet — create one to start saving automatically.</EmptyState>
        ) : (
          <div className="space-y-1">
            {[...treasury.savingsRules].reverse().map((rule) => (
              <div key={rule.id} className="flex items-center justify-between gap-2 rounded-sm border border-cmd-border/50 bg-cmd-bg/40 p-1.5 text-[9px]">
                <span className="flex-1">
                  <span className="text-cmd-text">{RULE_LABEL[rule.ruleType]}</span>{" "}
                  <span className="text-cmd-textDim">{rule.ruleType === "percent_of_monthly_profit" ? `${rule.percent.toFixed(0)}%` : `$${(rule.reserveTarget ?? 0).toLocaleString()}`}</span>
                </span>
                <StatusPill tone={rule.active ? "green" : "neutral"}>{rule.active ? "ACTIVE" : "PAUSED"}</StatusPill>
                <button type="button" onClick={() => void toggleRule(rule.id, !rule.active)} className="text-cmd-cyan underline-offset-2 hover:underline">
                  {rule.active ? "Pause" : "Resume"}
                </button>
              </div>
            ))}
          </div>
        )}
      </Glass>

      <Glass className="max-h-[24rem] overflow-y-auto p-3 lg:col-span-2">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Savings Growth Timeline</TerminalLabel>
          <StatusPill tone="cyan">{treasury.transactions.length}</StatusPill>
        </div>
        {recentTxns.length === 0 ? (
          <EmptyState>No Treasury activity yet.</EmptyState>
        ) : (
          <div className="space-y-1">
            {recentTxns.map((txn) => (
              <div key={txn.id} className="flex items-center justify-between gap-2 border-b border-cmd-border/40 py-1 text-[9px] last:border-0">
                <StatusPill tone={TXN_TONE[txn.kind]}>{txn.kind.replace("_", " ")}</StatusPill>
                <span className="flex-1 truncate text-cmd-textDim">{txn.note}</span>
                <span className="tabular-nums text-cmd-text">${txn.amount.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
                <span className="tabular-nums text-cmd-textDim">Day {txn.simDay}</span>
              </div>
            ))}
          </div>
        )}
      </Glass>

      <Glass className="p-3">
        <TerminalLabel>Monthly Savings Report</TerminalLabel>
        {recentReports.length === 0 ? (
          <EmptyState>No monthly report yet — one is filed automatically every in-game month.</EmptyState>
        ) : (
          <div className="space-y-1.5">
            {recentReports.slice(0, 6).map((report) => (
              <div key={report.id} className="rounded-sm border border-cmd-border/50 bg-cmd-bg/40 p-1.5 text-[9px]">
                <div className="mb-1 flex items-center justify-between">
                  <span className="text-cmd-cyan">Day {report.monthEndingDay}</span>
                  <span className="tabular-nums text-cmd-text">${report.endingBalance.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
                </div>
                <div className="text-cmd-textDim">
                  +${report.deposits.toLocaleString()} deposited · −${report.withdrawals.toLocaleString()} withdrawn · +${report.autoSaved.toLocaleString()} auto-saved
                </div>
              </div>
            ))}
          </div>
        )}
      </Glass>
    </div>
  );
}
