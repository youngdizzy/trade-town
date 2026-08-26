import { REPLAY_STAGE_STATUS_LABEL, REPLAY_STAGE_STATUS_TONE, formatStageTime, type ReplayStage } from "./lib/derive";
import { StatusPill } from "./ui";

/**
 * CEO directive "Live Desk + Trade Observability," Phase 9 — a compact,
 * always-expanded rendering of the real decision timeline `derive.ts`'s
 * buildReplayTimeline() already produces (the same data the Replay tab's
 * click-through timeline uses — see ReplayPanel.tsx). Extracted so the
 * Live Desk's trade inspector can show the same real research → signal →
 * debate → risk → CEO → execution → management → exit chain without a
 * second implementation of the stage list or its status styling.
 *
 * Every stage's timestamp (`stage.at`) is a real field off a real record
 * or nothing at all — never invented per-micro-stage times.
 */
export function DecisionTimelineList({ stages }: { stages: ReplayStage[] }) {
  return (
    <div className="space-y-1.5">
      {stages.map((stage) => {
        const time = formatStageTime(stage.at);
        return (
          <div key={stage.key} className="flex items-start gap-2 border-b border-cmd-border/40 py-1 text-[9px] last:border-0">
            <span className="w-16 shrink-0 tabular-nums text-cmd-textDim">{time ?? "—"}</span>
            <div className="flex-1">
              <div className="flex items-center gap-1.5">
                <span className="uppercase tracking-wide text-cmd-cyan">{stage.label}</span>
                <StatusPill tone={REPLAY_STAGE_STATUS_TONE[stage.status]}>{REPLAY_STAGE_STATUS_LABEL[stage.status]}</StatusPill>
              </div>
              <div className="mt-0.5 text-cmd-textDim">{stage.detail}</div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
