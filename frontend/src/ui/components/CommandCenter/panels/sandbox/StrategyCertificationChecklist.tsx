import { useEffect, useState } from "react";
import { api } from "@/net/api";
import type { StrategyCertification } from "@/types";
import { EmptyState, Glass, StatusPill, TerminalLabel } from "../../ui";

/**
 * CEO directive "Live Desk + Trade Observability," Phase 8 — the "STRATEGY
 * EVIDENCE" checklist on a trade's inspector panel. Reads the exact same
 * real endpoint StrategyCertificationView.tsx's Sandbox tab already reads
 * (GET /api/sandbox/certification, v0.7 Feature 53's Company Certification
 * checklist) — no second computation of the requirement list, just a
 * second, terser rendering suited to a trade drill-down rather than the
 * Strategy Lab's own full dossier view. `certified` is always a fresh read
 * of current state; every requirement's `met` is real, never fabricated —
 * an unmet item honestly renders NOT AVAILABLE rather than being hidden.
 */
export function StrategyCertificationChecklist({ strategyId }: { strategyId: string }) {
  const [certification, setCertification] = useState<StrategyCertification | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api
      .getSandboxCertification(strategyId)
      .then((res) => {
        if (!cancelled) setCertification(res);
      })
      .catch(() => {
        if (!cancelled) setCertification(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [strategyId]);

  if (loading && !certification) {
    return (
      <Glass className="p-3">
        <EmptyState>Reading this strategy's real certification requirements…</EmptyState>
      </Glass>
    );
  }
  if (!certification) return null;

  return (
    <Glass className="p-3">
      <div className="mb-1.5 flex items-center justify-between">
        <TerminalLabel>Strategy Evidence</TerminalLabel>
        <StatusPill tone={certification.certified ? "green" : "red"}>{certification.certified ? "CERTIFIED" : "NOT CERTIFIED"}</StatusPill>
      </div>
      <div className="grid grid-cols-1 gap-1 sm:grid-cols-2">
        {certification.requirements.map((r) => (
          <div key={r.id} className="flex items-start gap-1.5 text-[9px]">
            <StatusPill tone={r.met ? "green" : "red"}>{r.met ? "✓" : "NOT AVAILABLE"}</StatusPill>
            <div className="flex-1">
              <div className="text-cmd-text">{r.label}</div>
              <div className="text-cmd-textDim">{r.detail}</div>
            </div>
          </div>
        ))}
      </div>
    </Glass>
  );
}
