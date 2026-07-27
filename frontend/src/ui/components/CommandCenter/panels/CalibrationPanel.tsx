import { useState } from "react";
import { useGameStore } from "@/ui/hooks/useGameStore";
import type { SignalChallenge, SignalChoice } from "@/types";
import { api } from "@/net/api";
import { NexusManager } from "@/game/systems/NexusManager";
import { CandlestickChart } from "../CandlestickChart";
import { DataRow, EmptyState, Glass, StatusPill, TerminalLabel } from "../ui";

const LEVEL_NAMES: Record<number, string> = {
  1: "Level 1 — Trend",
  2: "Level 2 — Risk/Reward",
  3: "Level 3 — Trend & Regime",
  4: "Level 4 — Conflicting Evidence",
  5: "Level 5 — Full Analysis",
};

interface Result {
  correct: boolean;
  correctChoice: SignalChoice;
  rubricNotes: string;
  energyAwarded: number;
}

/**
 * Signal Calibration (v0.6.2 Phase 7) — a five-level ENTER/WAIT/AVOID
 * practice mini-game. Every challenge is graded against a fixed rubric
 * computed from real signals visible *at challenge time* (trend/
 * volatility/risk/research — see backend/app/signal_calibration.py),
 * never against what price did next, so a correct answer always means
 * "read the same information a real trader had," not "got lucky."
 */
export function CalibrationPanel() {
  const { signalCalibration } = useGameStore();
  const [level, setLevel] = useState(signalCalibration.unlockedLevel);
  const [challenge, setChallenge] = useState<SignalChallenge | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<Result | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const effectiveLevel = Math.min(level, signalCalibration.unlockedLevel);

  const newChallenge = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    setChallenge(null);
    try {
      const c = await api.getCalibrationChallenge(effectiveLevel);
      setChallenge(c);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  const answer = async (choice: SignalChoice) => {
    if (!challenge || submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      const res = await api.submitCalibrationChoice(challenge.id, choice);
      NexusManager.setSignalCalibration(res.signalCalibration);
      NexusManager.setAgentEnergy(res.agentEnergy);
      const attempt = res.signalCalibration.attempts[res.signalCalibration.attempts.length - 1];
      if (attempt) {
        setResult({ correct: attempt.correct, correctChoice: attempt.correctChoice, rubricNotes: attempt.rubricNotes, energyAwarded: attempt.energyAwarded });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  };

  const recentAttempts = [...signalCalibration.attempts].reverse().slice(0, 8);

  return (
    <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
      <Glass className="p-3 lg:col-span-1">
        <TerminalLabel>Progress</TerminalLabel>
        <DataRow label="Unlocked level" value={`${signalCalibration.unlockedLevel} / 5`} />
        <DataRow label="Correct" value={`${signalCalibration.correctCount} / ${signalCalibration.totalCount}`} />
        <div className="mt-3 space-y-1">
          {[1, 2, 3, 4, 5].map((l) => (
            <button
              key={l}
              type="button"
              disabled={l > signalCalibration.unlockedLevel}
              onClick={() => {
                setLevel(l);
                setChallenge(null);
                setResult(null);
              }}
              className={`block w-full rounded-sm border px-2 py-1 text-left ${
                effectiveLevel === l
                  ? "border-cmd-cyan/50 bg-cmd-cyan/10 text-cmd-cyan"
                  : l > signalCalibration.unlockedLevel
                    ? "border-cmd-border text-cmd-textDim opacity-30"
                    : "border-cmd-border text-cmd-textDim hover:text-cmd-text"
              }`}
            >
              {LEVEL_NAMES[l]} {l > signalCalibration.unlockedLevel ? "🔒" : ""}
            </button>
          ))}
        </div>
        <div className="mt-2 text-[9px] text-cmd-textDim">3 correct in a row at your current level unlocks the next.</div>
      </Glass>

      <div className="lg:col-span-2" data-testid="calibration-round">
      <Glass className="p-3">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>{LEVEL_NAMES[effectiveLevel]}</TerminalLabel>
          <button
            type="button"
            onClick={() => void newChallenge()}
            disabled={loading}
            className="rounded-sm border border-cmd-border px-2 py-1 text-cmd-textDim hover:enabled:text-cmd-cyan hover:enabled:border-cmd-cyan/50 disabled:opacity-40"
          >
            {loading ? "…" : challenge ? "New Round" : "Start Round"}
          </button>
        </div>

        {error && <div className="mb-2 text-[9px] text-cmd-red">{error}</div>}

        {!challenge && !loading && <EmptyState>Click "Start Round" to get a real symbol and read the signals.</EmptyState>}

        {challenge && (
          <div className="space-y-3">
            <div className="font-cmdmono text-cmd-cyan">{challenge.symbol}</div>
            <CandlestickChart candles={challenge.candles} loading={false} error={null} dataStatus={challenge.candles[0]?.dataStatus ?? null} height={200} />
            <div className="space-y-1">
              {challenge.factors.map((f, i) => (
                <div key={i} className="text-cmd-textDim">
                  — {f}
                </div>
              ))}
            </div>
            <div className="text-cmd-text">{challenge.prompt}</div>

            {!result ? (
              <div className="flex gap-2">
                <ChoiceButton label="ENTER" tone="green" disabled={submitting} onClick={() => void answer("enter")} />
                <ChoiceButton label="WAIT" tone="amber" disabled={submitting} onClick={() => void answer("wait")} />
                <ChoiceButton label="AVOID" tone="red" disabled={submitting} onClick={() => void answer("avoid")} />
              </div>
            ) : (
              <Glass className={`p-2 ${result.correct ? "border-cmd-green/50" : "border-cmd-red/50"}`}>
                <div className="flex items-center gap-2">
                  <StatusPill tone={result.correct ? "green" : "red"}>{result.correct ? "CORRECT" : "MISSED"}</StatusPill>
                  <span className="text-cmd-textDim">Disciplined answer: {result.correctChoice.toUpperCase()}</span>
                  {result.energyAwarded > 0 && <span className="text-cmd-cyan">+{result.energyAwarded}⚡</span>}
                </div>
                <div className="mt-1 text-[9px] text-cmd-textDim">{result.rubricNotes}</div>
              </Glass>
            )}
          </div>
        )}
      </Glass>
      </div>

      <Glass className="p-3 lg:col-span-3">
        <TerminalLabel>Recent Attempts</TerminalLabel>
        {recentAttempts.length === 0 ? (
          <EmptyState>No attempts yet.</EmptyState>
        ) : (
          <div className="divide-y divide-cmd-border/60">
            {recentAttempts.map((a) => (
              <div key={a.id} className="flex items-center justify-between gap-2 py-1.5">
                <span className="font-cmdmono text-cmd-cyan">{a.symbol}</span>
                <span className="text-cmd-textDim">L{a.level}</span>
                <span className="text-cmd-textDim">chose {a.choice.toUpperCase()}</span>
                <StatusPill tone={a.correct ? "green" : "red"}>{a.correct ? "CORRECT" : "MISSED"}</StatusPill>
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
