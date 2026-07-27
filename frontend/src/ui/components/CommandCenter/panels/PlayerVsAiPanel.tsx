import { useState } from "react";
import { useGameStore } from "@/ui/hooks/useGameStore";
import type { PlayerVsAiPrompt, SignalChoice } from "@/types";
import { api } from "@/net/api";
import { NexusManager } from "@/game/systems/NexusManager";
import { DataRow, EmptyState, Glass, StatusPill, TerminalLabel } from "../ui";

interface Result {
  playerCorrect: boolean;
  aiCorrect: boolean;
  groundTruthChoice: SignalChoice;
  realizedPnlPct: number;
}

/**
 * Player vs AI (v0.6.2 Phase 8) — the player calls ENTER/WAIT/AVOID on a
 * real past trade candidate before the AI's actual call is revealed.
 * Only decisions that led to a trade with a real, already-closed outcome
 * are ever offered (see backend/app/player_vs_ai.py), so grading is
 * always against a real realized P&L — and the AI is graded by the exact
 * same yardstick, never assumed to be right.
 */
export function PlayerVsAiPanel() {
  const { playerVsAi } = useGameStore();
  const [prompt, setPrompt] = useState<PlayerVsAiPrompt | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<Result | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const newRound = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    setPrompt(null);
    try {
      const p = await api.getPlayerVsAiPrompt();
      setPrompt(p);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  const answer = async (choice: SignalChoice) => {
    if (!prompt || submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      const res = await api.submitPlayerVsAiChoice(prompt.id, choice);
      NexusManager.setPlayerVsAi(res.playerVsAi);
      const round = res.playerVsAi.rounds[res.playerVsAi.rounds.length - 1];
      if (round) {
        setResult({ playerCorrect: round.playerCorrect, aiCorrect: round.aiCorrect, groundTruthChoice: round.groundTruthChoice, realizedPnlPct: round.realizedPnlPct });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  };

  const recentRounds = [...playerVsAi.rounds].reverse().slice(0, 8);

  const byRegime = new Map<string, { player: number; ai: number; total: number }>();
  const byCategory = new Map<string, { player: number; ai: number; total: number }>();
  for (const r of playerVsAi.rounds) {
    for (const [map, key] of [
      [byRegime, r.regime],
      [byCategory, r.category],
    ] as const) {
      const entry = map.get(key) ?? { player: 0, ai: 0, total: 0 };
      entry.total += 1;
      if (r.playerCorrect) entry.player += 1;
      if (r.aiCorrect) entry.ai += 1;
      map.set(key, entry);
    }
  }

  return (
    <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
      <Glass className="p-3 lg:col-span-1">
        <TerminalLabel>Head-to-Head</TerminalLabel>
        <DataRow label="Rounds played" value={playerVsAi.totalCount} />
        <DataRow
          label="Player accuracy"
          value={playerVsAi.totalCount ? `${Math.round((playerVsAi.playerCorrectCount / playerVsAi.totalCount) * 100)}%` : "N/A"}
        />
        <DataRow label="AI accuracy" value={playerVsAi.totalCount ? `${Math.round((playerVsAi.aiCorrectCount / playerVsAi.totalCount) * 100)}%` : "N/A"} />
        <div className="mt-3 space-y-2">
          <div>
            <div className="mb-1 text-[9px] uppercase tracking-wide text-cmd-textDim">By Regime</div>
            {byRegime.size === 0 ? (
              <div className="text-cmd-textDim">No data yet.</div>
            ) : (
              [...byRegime.entries()].map(([regime, s]) => (
                <DataRow key={regime} label={regime.replace("_", " ")} value={`you ${Math.round((s.player / s.total) * 100)}% · ai ${Math.round((s.ai / s.total) * 100)}%`} />
              ))
            )}
          </div>
          <div>
            <div className="mb-1 text-[9px] uppercase tracking-wide text-cmd-textDim">By Setup</div>
            {byCategory.size === 0 ? (
              <div className="text-cmd-textDim">No data yet.</div>
            ) : (
              [...byCategory.entries()].map(([category, s]) => (
                <DataRow key={category} label={category} value={`you ${Math.round((s.player / s.total) * 100)}% · ai ${Math.round((s.ai / s.total) * 100)}%`} />
              ))
            )}
          </div>
        </div>
      </Glass>

      <div className="lg:col-span-2" data-testid="player-vs-ai-round">
        <Glass className="p-3">
          <div className="mb-1.5 flex items-center justify-between">
            <TerminalLabel>Blind Round</TerminalLabel>
            <button
              type="button"
              onClick={() => void newRound()}
              disabled={loading}
              className="rounded-sm border border-cmd-border px-2 py-1 text-cmd-textDim hover:enabled:text-cmd-cyan hover:enabled:border-cmd-cyan/50 disabled:opacity-40"
            >
              {loading ? "…" : prompt ? "New Round" : "Start Round"}
            </button>
          </div>

          {error && <div className="mb-2 text-[9px] text-cmd-red">{error}</div>}

          {!prompt && !loading && <EmptyState>Click "Start Round" to compare your call against a real, already-resolved AI trade.</EmptyState>}

          {prompt && (
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <span className="font-cmdmono text-cmd-cyan">{prompt.symbol}</span>
                <StatusPill tone="neutral">{prompt.category}</StatusPill>
                <StatusPill tone="cyan">{prompt.regime.replace("_", " ")}</StatusPill>
              </div>
              <div className="text-cmd-textDim">{prompt.researchSummary}</div>
              <div className="text-cmd-textDim">{prompt.technicalSummary}</div>
              <div className="text-cmd-textDim">{prompt.riskSummary}</div>
              <DataRow label="Research confidence" value={`${Math.round(prompt.confidence)}%`} />
              <div className="text-cmd-text">Would you ENTER, WAIT, or AVOID — before seeing what the AI actually did?</div>

              {!result ? (
                <div className="flex gap-2">
                  <ChoiceButton label="ENTER" tone="green" disabled={submitting} onClick={() => void answer("enter")} />
                  <ChoiceButton label="WAIT" tone="amber" disabled={submitting} onClick={() => void answer("wait")} />
                  <ChoiceButton label="AVOID" tone="red" disabled={submitting} onClick={() => void answer("avoid")} />
                </div>
              ) : (
                <Glass className="p-2">
                  <div className="flex items-center gap-2">
                    <span className="text-cmd-textDim">You:</span>
                    <StatusPill tone={result.playerCorrect ? "green" : "red"}>{result.playerCorrect ? "CORRECT" : "MISSED"}</StatusPill>
                    <span className="text-cmd-textDim">AI:</span>
                    <StatusPill tone={result.aiCorrect ? "green" : "red"}>{result.aiCorrect ? "CORRECT" : "MISSED"}</StatusPill>
                  </div>
                  <div className="mt-1 text-[9px] text-cmd-textDim">
                    The AI entered this trade — real realized result: {result.realizedPnlPct >= 0 ? "+" : ""}
                    {result.realizedPnlPct.toFixed(1)}% ({result.groundTruthChoice === "enter" ? "a winner" : "a loser"}).
                  </div>
                </Glass>
              )}
            </div>
          )}
        </Glass>
      </div>

      <Glass className="p-3 lg:col-span-3">
        <TerminalLabel>Recent Rounds</TerminalLabel>
        {recentRounds.length === 0 ? (
          <EmptyState>No rounds yet.</EmptyState>
        ) : (
          <div className="divide-y divide-cmd-border/60">
            {recentRounds.map((r) => (
              <div key={r.id} className="flex items-center justify-between gap-2 py-1.5">
                <span className="font-cmdmono text-cmd-cyan">{r.symbol}</span>
                <span className="text-cmd-textDim">you {r.playerChoice.toUpperCase()}</span>
                <StatusPill tone={r.playerCorrect ? "green" : "red"}>YOU {r.playerCorrect ? "✓" : "✗"}</StatusPill>
                <StatusPill tone={r.aiCorrect ? "green" : "red"}>AI {r.aiCorrect ? "✓" : "✗"}</StatusPill>
                <span className="text-cmd-textDim">{r.realizedPnlPct >= 0 ? "+" : ""}{r.realizedPnlPct.toFixed(1)}%</span>
              </div>
            ))}
          </div>
        )}
      </Glass>
    </div>
  );
}

function ChoiceButton({ label, tone, disabled, onClick }: { label: string; tone: "green" | "amber" | "red"; disabled: boolean; onClick: () => void }) {
  const toneClass: Record<string, string> = {
    green: "border-cmd-green/50 text-cmd-green hover:bg-cmd-green/10",
    amber: "border-cmd-amber/50 text-cmd-amber hover:bg-cmd-amber/10",
    red: "border-cmd-red/50 text-cmd-red hover:bg-cmd-red/10",
  };
  return (
    <button type="button" onClick={onClick} disabled={disabled} className={`flex-1 rounded-sm border py-2 disabled:opacity-40 ${toneClass[tone]}`}>
      {label}
    </button>
  );
}
