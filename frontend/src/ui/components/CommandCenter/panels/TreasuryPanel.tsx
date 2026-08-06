import { useMemo, useState } from "react";
import { useGameStore } from "@/ui/hooks/useGameStore";
import { NexusManager } from "@/game/systems/NexusManager";
import { api } from "@/net/api";
import type { Account, AccountType, PropFirmStatus, SavingsRuleType, TreasuryTransaction } from "@/types";
import { ACCOUNT_TYPE_LABEL } from "@/types";
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
  const { treasury, paperPortfolio, accounts, activeAccountId } = useGameStore();
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

      <AccountsSection accounts={accounts} activeAccountId={activeAccountId} />

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

const ACCOUNT_TYPES: AccountType[] = ["personal", "ira", "business", "prop_firm", "family"];

/**
 * Design Bible Chapter 69 Part 1 — Multi-Account & Fund Management
 * System. Every account here is a real, isolated capital pool (see
 * backend/app/accounts.py's module docstring): its own cash, its own
 * editable risk profile, funded by real, validated transfers to/from
 * the CEO Treasury above — reusing the exact same deposit/withdraw
 * mechanism, never a second transfer system. Honest scope: live trading
 * execution against a non-primary account isn't wired yet, so "Balance"
 * only moves via Allocate/Deallocate here, never a trade fill.
 */
function AccountsSection({ accounts, activeAccountId }: { accounts: Account[]; activeAccountId: string | null }) {
  const [name, setName] = useState("");
  const [accountType, setAccountType] = useState<AccountType>("personal");
  const [startingBalance, setStartingBalance] = useState("1000");
  const [busyId, setBusyId] = useState<string | null>(null);
  const [amounts, setAmounts] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

  const create = async () => {
    if (busyId || !name.trim()) return;
    setBusyId("create");
    setError(null);
    try {
      const res = await api.createAccount(name.trim(), accountType, Number(startingBalance));
      NexusManager.setAccounts(res.accounts);
      setName("");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusyId(null);
    }
  };

  const transfer = async (accountId: string, direction: "allocate" | "deallocate") => {
    const amount = Number(amounts[accountId] ?? "");
    if (!amount || amount <= 0 || busyId) return;
    setBusyId(accountId);
    setError(null);
    try {
      const res = direction === "allocate" ? await api.allocateAccountCapital(accountId, amount) : await api.deallocateAccountCapital(accountId, amount);
      NexusManager.setAccounts(res.accounts);
      NexusManager.setTreasury(res.treasury);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusyId(null);
    }
  };

  const close = async (accountId: string) => {
    if (busyId) return;
    setBusyId(accountId);
    setError(null);
    try {
      const res = await api.closeAccount(accountId);
      NexusManager.setAccounts(res.accounts);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusyId(null);
    }
  };

  const switchActive = async (accountId: string | null) => {
    if (busyId) return;
    try {
      const res = await api.switchActiveAccount(accountId);
      NexusManager.setActiveAccountId(res.activeAccountId);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  return (
    <Glass className="p-3 lg:col-span-3">
      <div className="mb-2 flex items-center justify-between">
        <TerminalLabel>Multi-Account & Fund Management</TerminalLabel>
        <StatusPill tone="cyan">{accounts.length} account{accounts.length === 1 ? "" : "s"}</StatusPill>
      </div>
      <p className="mb-2 text-[9px] text-cmd-textDim">
        Each account below is a real, isolated capital pool with its own risk profile, funded by real transfers to/from the Treasury above. Live
        trading execution against a non-primary account isn&apos;t wired yet — balances here move only through Allocate/Deallocate.
      </p>

      <div className="mb-2 flex flex-wrap items-end gap-2 border-b border-cmd-border/50 pb-2">
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Account name"
          className="min-w-[10rem] flex-1 rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1.5 text-[10px] text-cmd-text placeholder:text-cmd-textDim/60 focus:border-cmd-cyan/50 focus:outline-none"
        />
        <select
          value={accountType}
          onChange={(e) => setAccountType(e.target.value as AccountType)}
          className="rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1.5 text-[10px] text-cmd-text focus:border-cmd-cyan/50 focus:outline-none"
        >
          {ACCOUNT_TYPES.map((t) => (
            <option key={t} value={t}>
              {ACCOUNT_TYPE_LABEL[t]}
            </option>
          ))}
        </select>
        <input
          type="number"
          min={1}
          value={startingBalance}
          onChange={(e) => setStartingBalance(e.target.value)}
          className="w-28 rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1.5 text-[10px] text-cmd-text focus:border-cmd-cyan/50 focus:outline-none"
        />
        <button
          type="button"
          onClick={() => void create()}
          disabled={busyId !== null || !name.trim()}
          className="rounded-sm border border-cmd-cyan/50 px-3 py-1.5 text-[10px] uppercase tracking-wider text-cmd-cyan transition-colors hover:bg-cmd-cyan/10 disabled:opacity-40"
        >
          {busyId === "create" ? "…" : "Create Account"}
        </button>
      </div>

      {error && <div className="mb-2 text-[9px] text-cmd-red">{error}</div>}

      {accounts.length === 0 ? (
        <EmptyState>No sub-accounts yet — create one above to start a real, isolated capital pool.</EmptyState>
      ) : (
        <div className="space-y-1.5">
          <button
            type="button"
            onClick={() => void switchActive(null)}
            className={`flex w-full items-center justify-between rounded-sm border p-1.5 text-[9px] transition-colors ${
              activeAccountId === null ? "border-cmd-cyan/60 bg-cmd-cyan/10" : "border-cmd-border/50 bg-cmd-bg/40 hover:border-cmd-cyan/40"
            }`}
          >
            <span className="text-cmd-text">Primary (Operating Capital)</span>
            {activeAccountId === null && <StatusPill tone="cyan">VIEWING</StatusPill>}
          </button>
          {accounts.map((account) => {
            const canClose = account.portfolio.cashBalance <= 0 && account.portfolio.positions.length === 0;
            return (
              <div key={account.id} className="rounded-sm border border-cmd-border/50 bg-cmd-bg/40 p-2 text-[9px]">
                <button type="button" onClick={() => void switchActive(account.id)} className="mb-1 flex w-full items-center justify-between gap-2 text-left">
                  <span className="flex items-center gap-1.5">
                    <span className="text-cmd-text">{account.name}</span>
                    <span className="text-cmd-textDim">{ACCOUNT_TYPE_LABEL[account.accountType]}</span>
                  </span>
                  {activeAccountId === account.id && <StatusPill tone="cyan">VIEWING</StatusPill>}
                </button>
                <div className="mb-1 grid grid-cols-2 gap-x-3 gap-y-0.5 text-cmd-textDim">
                  <span>
                    Balance: <span className="tabular-nums text-cmd-text">${account.portfolio.cashBalance.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
                  </span>
                  <span>
                    Max Drawdown Limit: <span className="tabular-nums text-cmd-text">{account.riskLimits.maxDrawdownPct.toFixed(0)}%</span>
                  </span>
                </div>
                <div className="flex flex-wrap items-center gap-1.5">
                  <input
                    type="number"
                    min={1}
                    value={amounts[account.id] ?? ""}
                    onChange={(e) => setAmounts((prev) => ({ ...prev, [account.id]: e.target.value }))}
                    placeholder="Amount"
                    className="w-24 rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1 text-[9px] text-cmd-text placeholder:text-cmd-textDim/60 focus:border-cmd-cyan/50 focus:outline-none"
                  />
                  <button
                    type="button"
                    onClick={() => void transfer(account.id, "allocate")}
                    disabled={busyId !== null}
                    className="rounded-sm border border-cmd-green/50 px-2 py-1 text-cmd-green transition-colors hover:enabled:bg-cmd-green/10 disabled:opacity-40"
                  >
                    {busyId === account.id ? "…" : "Allocate ▸"}
                  </button>
                  <button
                    type="button"
                    onClick={() => void transfer(account.id, "deallocate")}
                    disabled={busyId !== null}
                    className="rounded-sm border border-cmd-amber/50 px-2 py-1 text-cmd-amber transition-colors hover:enabled:bg-cmd-amber/10 disabled:opacity-40"
                  >
                    {busyId === account.id ? "…" : "◂ Deallocate"}
                  </button>
                  <button
                    type="button"
                    onClick={() => void close(account.id)}
                    disabled={busyId !== null || !canClose}
                    title={canClose ? "Close this account" : "Deallocate all funds before closing"}
                    className="ml-auto rounded-sm border border-cmd-red/40 px-2 py-1 text-cmd-red transition-colors hover:enabled:bg-cmd-red/10 disabled:opacity-40"
                  >
                    Close
                  </button>
                </div>
                {account.accountType === "prop_firm" && <PropFirmCard account={account} />}
              </div>
            );
          })}
        </div>
      )}
    </Glass>
  );
}

/**
 * Design Bible Chapter 69 Part 2 — Prop Firm Rule Engine. Configures the
 * account's own real Trailing Drawdown / Consistency / Challenge Window
 * fields, then fetches and displays the real, computed-fresh compliance
 * status behind those numbers. See backend/app/prop_firm.py — every
 * number here is real; leverage is explicitly stated as not applicable
 * rather than fabricated, since this is a 100% cash account.
 */
function PropFirmCard({ account }: { account: Account }) {
  const { time } = useGameStore();
  const [showConfig, setShowConfig] = useState(false);
  const [trailingLimit, setTrailingLimit] = useState(account.trailingDrawdownLimitPct?.toString() ?? "");
  const [consistencyLimit, setConsistencyLimit] = useState(account.consistencyLimitPct?.toString() ?? "");
  const [challengeDuration, setChallengeDuration] = useState(account.challengeDurationDays?.toString() ?? "30");
  const [challengeTarget, setChallengeTarget] = useState(account.challengeProfitTargetPct?.toString() ?? "8");
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState<PropFirmStatus | null>(null);
  const [statusLoading, setStatusLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadStatus = async () => {
    setStatusLoading(true);
    setError(null);
    try {
      const res = await api.getPropFirmStatus(account.id);
      setStatus(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setStatusLoading(false);
    }
  };

  const toggleConfig = () => {
    const next = !showConfig;
    setShowConfig(next);
    if (next && !status) void loadStatus();
  };

  const save = async () => {
    if (saving) return;
    setSaving(true);
    setError(null);
    try {
      const res = await api.configurePropFirmRules(account.id, {
        trailingDrawdownLimitPct: trailingLimit ? Number(trailingLimit) : null,
        consistencyLimitPct: consistencyLimit ? Number(consistencyLimit) : null,
        challengeStartSimDay: account.challengeStartSimDay ?? null,
        challengeDurationDays: challengeDuration ? Number(challengeDuration) : null,
        challengeProfitTargetPct: challengeTarget ? Number(challengeTarget) : null,
      });
      NexusManager.setAccounts(res.accounts);
      await loadStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  };

  const startChallenge = async () => {
    if (saving) return;
    setSaving(true);
    setError(null);
    try {
      const res = await api.configurePropFirmRules(account.id, {
        trailingDrawdownLimitPct: trailingLimit ? Number(trailingLimit) : null,
        consistencyLimitPct: consistencyLimit ? Number(consistencyLimit) : null,
        challengeStartSimDay: time.day,
        challengeDurationDays: challengeDuration ? Number(challengeDuration) : null,
        challengeProfitTargetPct: challengeTarget ? Number(challengeTarget) : null,
      });
      NexusManager.setAccounts(res.accounts);
      await loadStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="mt-1.5 border-t border-cmd-border/40 pt-1.5">
      <button type="button" onClick={toggleConfig} className="text-[9px] text-cmd-purple underline-offset-2 hover:underline">
        {showConfig ? "Hide Prop Firm Rules ▲" : "Prop Firm Rules ▼"}
      </button>
      {showConfig && (
        <div className="mt-1.5 space-y-1.5 text-[9px]">
          <div className="flex flex-wrap items-center gap-1.5">
            <label className="flex items-center gap-1 text-cmd-textDim">
              Trailing DD %
              <input
                type="number"
                min={0}
                value={trailingLimit}
                onChange={(e) => setTrailingLimit(e.target.value)}
                className="w-14 rounded-sm border border-cmd-border bg-cmd-bg/60 px-1.5 py-0.5 text-cmd-text focus:border-cmd-cyan/50 focus:outline-none"
              />
            </label>
            <label className="flex items-center gap-1 text-cmd-textDim">
              Consistency %
              <input
                type="number"
                min={0}
                max={100}
                value={consistencyLimit}
                onChange={(e) => setConsistencyLimit(e.target.value)}
                className="w-14 rounded-sm border border-cmd-border bg-cmd-bg/60 px-1.5 py-0.5 text-cmd-text focus:border-cmd-cyan/50 focus:outline-none"
              />
            </label>
            <label className="flex items-center gap-1 text-cmd-textDim">
              Duration (days)
              <input
                type="number"
                min={1}
                value={challengeDuration}
                onChange={(e) => setChallengeDuration(e.target.value)}
                className="w-14 rounded-sm border border-cmd-border bg-cmd-bg/60 px-1.5 py-0.5 text-cmd-text focus:border-cmd-cyan/50 focus:outline-none"
              />
            </label>
            <label className="flex items-center gap-1 text-cmd-textDim">
              Target %
              <input
                type="number"
                min={0}
                value={challengeTarget}
                onChange={(e) => setChallengeTarget(e.target.value)}
                className="w-14 rounded-sm border border-cmd-border bg-cmd-bg/60 px-1.5 py-0.5 text-cmd-text focus:border-cmd-cyan/50 focus:outline-none"
              />
            </label>
          </div>
          <div className="flex gap-1.5">
            <button
              type="button"
              onClick={() => void save()}
              disabled={saving}
              className="rounded-sm border border-cmd-cyan/50 px-2 py-1 text-cmd-cyan transition-colors hover:enabled:bg-cmd-cyan/10 disabled:opacity-40"
            >
              {saving ? "…" : "Save Rules"}
            </button>
            <button
              type="button"
              onClick={() => void startChallenge()}
              disabled={saving}
              className="rounded-sm border border-cmd-green/50 px-2 py-1 text-cmd-green transition-colors hover:enabled:bg-cmd-green/10 disabled:opacity-40"
            >
              {saving ? "…" : "Start Challenge Today"}
            </button>
          </div>
          {error && <div className="text-cmd-red">{error}</div>}

          {statusLoading && <div className="text-cmd-textDim">Computing compliance…</div>}
          {status && (
            <div className="space-y-1 rounded-sm border border-cmd-border/50 bg-cmd-bg/40 p-1.5">
              <div className="flex items-center justify-between">
                <span className="text-cmd-textDim">
                  Compliance Score ({status.weekday})
                </span>
                <span
                  className={
                    status.complianceScore.overall >= 70 ? "text-cmd-green" : status.complianceScore.overall >= 40 ? "text-cmd-amber" : "text-cmd-red"
                  }
                >
                  {status.complianceScore.overall.toFixed(0)}/100
                </span>
              </div>
              <div className="grid grid-cols-2 gap-x-3 gap-y-0.5 text-cmd-textDim">
                <span>
                  Trailing Drawdown: <span className="tabular-nums text-cmd-text">{status.trailingDrawdown.drawdownPct.toFixed(1)}%</span>
                  {status.trailingDrawdown.breached && <span className="ml-1 text-cmd-red">BREACHED</span>}
                </span>
                <span>
                  Scaling Tier: <span className="tabular-nums text-cmd-text">{status.scaling.currentTier}</span>
                </span>
                {status.challenge.applicable ? (
                  <>
                    <span>
                      Challenge: <span className="tabular-nums text-cmd-text">Day {status.challenge.daysElapsed}/{status.challenge.durationDays}</span>
                    </span>
                    <span>
                      Progress: <span className="tabular-nums text-cmd-text">{status.challenge.profitPct.toFixed(1)}%</span> of{" "}
                      <span className="tabular-nums text-cmd-text">{status.challenge.targetPct?.toFixed(1)}%</span>
                      {status.challenge.onPace === false && <span className="ml-1 text-cmd-amber">BEHIND PACE</span>}
                    </span>
                  </>
                ) : (
                  <span className="col-span-2">No challenge window started yet.</span>
                )}
                {status.consistency.applicable && (
                  <span className="col-span-2">
                    Consistency: largest day is <span className="tabular-nums text-cmd-text">{status.consistency.largestSingleDaySharePct.toFixed(0)}%</span>{" "}
                    of cumulative profit
                    {status.consistency.breached && <span className="ml-1 text-cmd-red">BREACHED</span>}
                  </span>
                )}
              </div>
              <div className="text-cmd-textDim">{status.leverageNote}</div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
