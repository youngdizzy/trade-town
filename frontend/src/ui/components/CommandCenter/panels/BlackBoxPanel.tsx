import { useMemo, useState } from "react";
import { useGameStore } from "@/ui/hooks/useGameStore";
import { NexusManager } from "@/game/systems/NexusManager";
import { AGENT_PROFILES } from "@/game/systems/AgentProfiles";
import { api } from "@/net/api";
import type { AgentId, BlackBoxPriority, BlackBoxProject } from "@/types";
import { DataRow, EmptyState, Glass, Meter, StatusPill, TerminalLabel } from "../ui";

const CATEGORY_LABEL: Record<BlackBoxProject["category"], string> = {
  new_trading_framework: "New Trading Framework",
  portfolio_allocation: "Portfolio Allocation",
  statistical_edge: "Statistical Edge",
  ai_communication: "AI Communication",
  risk_model: "Risk Model",
  decision_framework: "Decision Framework",
  journaling_improvement: "Journaling",
  automation_improvement: "Automation",
  market_regime_detection: "Market Regime Detection",
  portfolio_optimization: "Portfolio Optimization",
  academy_improvement: "Academy Improvement",
};

const STATUS_TONE: Record<BlackBoxProject["status"], "cyan" | "amber" | "green" | "red" | "neutral"> = {
  active: "cyan",
  paused: "amber",
  under_review: "amber",
  completed: "green",
  failed: "red",
};

/**
 * v0.7 — the Advanced Quantitative Research Division / CEO Research
 * Dashboard. See backend/app/black_box.py's module docstring for what
 * this extends vs. builds new: Devil's Advocate, Innovation Points, the
 * backtesting engine, the Founder Council, and the Museum of Discoveries
 * all reuse existing systems rather than duplicating them. No new
 * physical "Quant Lab" scene was built — Vector (the Chief Quantitative
 * Strategist) works out of the existing Simulation Lab room, and this
 * panel is the dashboard.
 */
export function BlackBoxPanel() {
  const { blackBox } = useGameStore();
  const { active, archive, reviews } = blackBox;
  const [amount, setAmount] = useState("500");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const recentArchive = useMemo(() => [...archive].reverse(), [archive]);
  const recentReviews = useMemo(() => [...reviews].reverse(), [reviews]);
  const museumExhibits = useMemo(() => [...archive].filter((p) => p.status === "completed").reverse(), [archive]);

  const run = async (key: string, action: () => Promise<{ blackBox: typeof blackBox }>) => {
    if (busy) return;
    setBusy(key);
    setError(null);
    try {
      const res = await action();
      NexusManager.setBlackBox(res.blackBox);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(null);
    }
  };

  const fund = () => {
    const value = Number(amount);
    if (!value || value <= 0) return;
    void run("fund", () => api.fundBlackBoxProject(value));
  };

  const setPriority = (priority: BlackBoxPriority) => void run("priority", () => api.setBlackBoxPriority(priority));

  const addNote = () => {
    const trimmed = note.trim();
    if (!trimmed) return;
    void run("note", () => api.addBlackBoxNote(trimmed)).then(() => setNote(""));
  };

  return (
    <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
      <Glass className="p-3 lg:col-span-3">
        <div className="mb-1.5 flex items-center gap-2">
          <span className="text-lg">{AGENT_PROFILES.quant.badge}</span>
          <div>
            <div className="text-cmd-cyan">{AGENT_PROFILES.quant.name}, {AGENT_PROFILES.quant.occupation}</div>
            <div className="text-[9px] text-cmd-textDim">{AGENT_PROFILES.quant.personality}</div>
          </div>
        </div>
      </Glass>

      {active === null ? (
        <Glass className="p-3 lg:col-span-3">
          <EmptyState>No Black Box Research Project is currently active — one starts automatically at the next evening review.</EmptyState>
        </Glass>
      ) : (
        <>
          <Glass className="p-3 lg:col-span-3">
            <div className="mb-1.5 flex items-center justify-between">
              <TerminalLabel>Current Project — {CATEGORY_LABEL[active.category]}</TerminalLabel>
              <StatusPill tone={STATUS_TONE[active.status]}>{active.status.replace("_", " ").toUpperCase()}</StatusPill>
            </div>
            <div className="mb-2 text-[10px] text-cmd-text">{active.title}</div>
            <p className="mb-2 text-[9px] text-cmd-textDim">{active.objective}</p>
            <div className="mb-2 grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div>
                <div className="mb-1 flex items-center justify-between text-[9px] text-cmd-textDim">
                  <span>Progress</span>
                  <span className="tabular-nums text-cmd-text">{active.progress.toFixed(1)}%</span>
                </div>
                <Meter value={active.progress} tone="cyan" />
              </div>
              <div>
                <div className="mb-1 flex items-center justify-between text-[9px] text-cmd-textDim">
                  <span>Confidence Level</span>
                  <span className="tabular-nums text-cmd-text">{active.confidenceLevel.toFixed(0)}/100</span>
                </div>
                <Meter value={active.confidenceLevel} tone={active.confidenceLevel >= 55 ? "green" : "amber"} />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 border-t border-cmd-border/50 pt-2 sm:grid-cols-4">
              <DataRow label="Budget" value={`$${active.budget.toLocaleString(undefined, { maximumFractionDigits: 0 })}`} />
              <DataRow label="Started" value={`Day ${active.startedSimDay}`} />
              <DataRow label="Est. Completion" value={`Day ${active.estimatedCompletionSimDay}`} />
              <DataRow label="Devil's Advocate" value={`${AGENT_PROFILES[active.devilsAdvocate].badge} ${AGENT_PROFILES[active.devilsAdvocate].name}`} />
            </div>
          </Glass>

          <Glass className="p-3">
            <TerminalLabel>Research Team</TerminalLabel>
            <div className="space-y-1">
              {active.team.map((member) => (
                <TeamRow key={member.agentId} agentId={member.agentId} role={member.role} team={active.team} />
              ))}
            </div>
          </Glass>

          <Glass className="p-3">
            <TerminalLabel>Obstacles</TerminalLabel>
            {active.obstacles.length === 0 ? (
              <EmptyState>No obstacles logged yet.</EmptyState>
            ) : (
              <ul className="space-y-1 text-[9px] text-cmd-amber">
                {active.obstacles.map((o, i) => (
                  <li key={i}>▸ {o}</li>
                ))}
              </ul>
            )}
          </Glass>

          <Glass className="p-3">
            <TerminalLabel>CEO Controls</TerminalLabel>
            <div className="mb-2 flex gap-2">
              <input
                type="number"
                min={1}
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                className="w-20 rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1.5 text-[10px] text-cmd-text focus:border-cmd-cyan/50 focus:outline-none"
              />
              <button
                type="button"
                onClick={fund}
                disabled={busy !== null}
                className="flex-1 rounded-sm border border-cmd-green/50 py-1.5 text-[10px] uppercase tracking-wider text-cmd-green transition-colors hover:bg-cmd-green/10 disabled:opacity-40"
              >
                {busy === "fund" ? "…" : "Increase Funding"}
              </button>
            </div>
            <div className="mb-2 flex gap-2">
              <button
                type="button"
                onClick={() => void run("pause-resume", () => (active.status === "paused" ? api.resumeBlackBoxProject() : api.pauseBlackBoxProject()))}
                disabled={busy !== null || active.status === "under_review"}
                className="flex-1 rounded-sm border border-cmd-amber/50 py-1.5 text-[10px] uppercase tracking-wider text-cmd-amber transition-colors hover:bg-cmd-amber/10 disabled:opacity-40"
              >
                {active.status === "paused" ? "Resume" : "Pause"}
              </button>
              <button
                type="button"
                onClick={() => void run("cancel", () => api.cancelBlackBoxProject())}
                disabled={busy !== null}
                className="flex-1 rounded-sm border border-cmd-red/50 py-1.5 text-[10px] uppercase tracking-wider text-cmd-red transition-colors hover:bg-cmd-red/10 disabled:opacity-40"
              >
                Cancel
              </button>
            </div>
            <div className="mb-2 flex gap-1">
              {(["low", "normal", "high"] as BlackBoxPriority[]).map((p) => (
                <button
                  key={p}
                  type="button"
                  onClick={() => setPriority(p)}
                  disabled={busy !== null}
                  className={`flex-1 rounded-sm border py-1 text-[9px] uppercase tracking-wider transition-colors disabled:opacity-40 ${
                    active.priority === p ? "border-cmd-cyan/60 bg-cmd-cyan/10 text-cmd-cyan" : "border-cmd-border text-cmd-textDim hover:border-cmd-cyan/40"
                  }`}
                >
                  {p}
                </button>
              ))}
            </div>
            <div className="flex gap-2">
              <input
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="Add a research idea…"
                className="flex-1 rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1.5 text-[10px] text-cmd-text focus:border-cmd-cyan/50 focus:outline-none"
              />
              <button
                type="button"
                onClick={addNote}
                disabled={busy !== null}
                className="rounded-sm border border-cmd-cyan/50 px-3 py-1.5 text-[10px] uppercase tracking-wider text-cmd-cyan transition-colors hover:bg-cmd-cyan/10 disabled:opacity-40"
              >
                {busy === "note" ? "…" : "Add"}
              </button>
            </div>
            {error && <div className="mt-2 text-[9px] text-cmd-red">{error}</div>}
          </Glass>

          <Glass className="max-h-[16rem] overflow-y-auto p-3 lg:col-span-3">
            <TerminalLabel>Quant Journal — Research Notes</TerminalLabel>
            <div className="space-y-1 text-[9px]">
              {active.researchNotes.length > 0 && (
                <div className="mb-1.5 space-y-0.5 border-b border-cmd-border/40 pb-1.5">
                  {active.researchNotes.map((n, i) => (
                    <div key={i} className="text-cmd-cyan">
                      💡 {n}
                    </div>
                  ))}
                </div>
              )}
              {[...active.quantJournal].reverse().map((line, i) => (
                <div key={i} className="text-cmd-textDim">
                  {line}
                </div>
              ))}
            </div>
          </Glass>
        </>
      )}

      <Glass className="max-h-[20rem] overflow-y-auto p-3">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Founder Council Reviews</TerminalLabel>
          <StatusPill tone="cyan">{reviews.length}</StatusPill>
        </div>
        {recentReviews.length === 0 ? (
          <EmptyState>No project has reached review yet.</EmptyState>
        ) : (
          <div className="space-y-1.5">
            {recentReviews.map((review) => (
              <div key={review.id} className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-1.5 text-[9px]">
                <div className="mb-1 flex items-center justify-between">
                  <span className="text-cmd-text">{review.projectTitle}</span>
                  <StatusPill tone={review.verdict === "approved" ? "green" : "red"}>{review.verdict.toUpperCase()}</StatusPill>
                </div>
                <div className="text-cmd-textDim">{review.verdictReason}</div>
              </div>
            ))}
          </div>
        )}
      </Glass>

      <Glass className="max-h-[20rem] overflow-y-auto p-3">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Museum of Discoveries</TerminalLabel>
          <StatusPill tone="green">{museumExhibits.length}</StatusPill>
        </div>
        {museumExhibits.length === 0 ? (
          <EmptyState>No breakthrough has survived Founder Council review yet.</EmptyState>
        ) : (
          <div className="space-y-1.5">
            {museumExhibits.map((exhibit) => (
              <div key={exhibit.id} className="rounded-sm border border-cmd-green/40 bg-cmd-green/5 p-1.5 text-[9px]">
                <div className="mb-0.5 text-cmd-green">🧠 {exhibit.title}</div>
                <div className="text-cmd-textDim">
                  Day {exhibit.startedSimDay} – {exhibit.completedAt ? new Date(exhibit.completedAt).toLocaleDateString() : "?"}
                </div>
              </div>
            ))}
          </div>
        )}
      </Glass>

      <Glass className="max-h-[20rem] overflow-y-auto p-3">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Research Archives</TerminalLabel>
          <StatusPill tone="neutral">{recentArchive.length}</StatusPill>
        </div>
        {recentArchive.length === 0 ? (
          <EmptyState>No project has closed out yet — nothing is ever wasted here.</EmptyState>
        ) : (
          <div className="space-y-1.5">
            {recentArchive.map((project) => (
              <ArchiveEntry key={project.id} project={project} />
            ))}
          </div>
        )}
      </Glass>
    </div>
  );
}

function ArchiveEntry({ project }: { project: BlackBoxProject }) {
  return (
    <div className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-1.5 text-[9px]">
      <div className="mb-0.5 flex items-center justify-between">
        <span className="text-cmd-text">{project.title}</span>
        <StatusPill tone={project.status === "completed" ? "green" : "red"}>{project.status.toUpperCase()}</StatusPill>
      </div>
      {project.researchNotes.length > 0 && <div className="text-cmd-textDim">{project.researchNotes[project.researchNotes.length - 1]}</div>}
    </div>
  );
}

// The real, bounded reassignment pool: the nine operational agents this
// codebase already routes research/analysis work through elsewhere (see
// backend/app/research.py's RESEARCHER_IDS) — never Quant itself (always
// leader), a Founder, the CIO, or Sage (see backend/app/founders.py's
// module docstring for why those never route through this kind of
// operational work).
const REASSIGN_POOL: AgentId[] = ["scout", "atlas", "echo", "nova", "scribe", "coach", "sentinel", "pulse", "guardian"];

function TeamRow({ agentId, role, team }: { agentId: AgentId; role: string; team: { agentId: AgentId; role: string }[] }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const teamIds = useMemo(() => new Set(team.map((m) => m.agentId)), [team]);
  const options = useMemo(() => REASSIGN_POOL.filter((a) => a === agentId || !teamIds.has(a)), [agentId, teamIds]);

  const reassign = async (newAgentId: AgentId) => {
    if (busy || newAgentId === agentId) return;
    setBusy(true);
    setError(null);
    try {
      const res = await api.reassignBlackBoxSpecialist(agentId, newAgentId);
      NexusManager.setBlackBox(res.blackBox);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  const isLeader = agentId === "quant";

  return (
    <div className="rounded-sm border border-cmd-border/50 bg-cmd-bg/40 p-1.5 text-[9px]">
      <div className="flex items-center justify-between gap-2">
        <span className="flex items-center gap-1.5">
          <span>{AGENT_PROFILES[agentId].badge}</span>
          <span className="text-cmd-text">{AGENT_PROFILES[agentId].name}</span>
        </span>
        {isLeader ? (
          <span className="text-cmd-textDim">{role}</span>
        ) : (
          <select
            value={agentId}
            disabled={busy}
            onChange={(e) => void reassign(e.target.value as AgentId)}
            className="rounded-sm border border-cmd-border bg-cmd-bg/60 px-1 py-0.5 text-[9px] text-cmd-textDim focus:border-cmd-cyan/50 focus:outline-none"
          >
            {options.map((a) => (
              <option key={a} value={a}>
                {AGENT_PROFILES[a].name} — {a === agentId ? role : "Reassign"}
              </option>
            ))}
          </select>
        )}
      </div>
      {error && <div className="mt-1 text-cmd-red">{error}</div>}
    </div>
  );
}
