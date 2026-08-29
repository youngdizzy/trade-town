import type { EvidenceConfluenceRead } from "@/types";
import { DataRow, Glass, TerminalLabel } from "./ui";

/**
 * CEO directive "TradeTown — 11/10 Market Intelligence + Quant Research
 * Engine" — Trade Inspection Panel. This exact card previously existed,
 * byte-for-byte duplicated, in both MarketIntelPanel.tsx and
 * WarRoomPanel.tsx; adding a third copy for DecisionDetail.tsx would
 * have made three independently-drifting renderings of the same real
 * backend/app/evidence_confluence.py read, so it's extracted here
 * instead and all three call sites now share it.
 */
export function EvidenceConfluenceCard({ confluence, title }: { confluence: EvidenceConfluenceRead; title: string }) {
  return (
    <Glass className="p-3">
      <div className="mb-1.5 flex items-center justify-between">
        <TerminalLabel>{title}</TerminalLabel>
        <span className="text-[9px] text-cmd-textDim">Raw signals vs. independent evidence families</span>
      </div>
      <div className="grid grid-cols-2 gap-x-4 sm:grid-cols-3">
        <DataRow label="Raw Signal Count" value={confluence.rawSignalCount} />
        <DataRow
          label="Independent Families"
          value={confluence.independentFamilyCount}
          valueClassName={confluence.independentFamilyCount < confluence.rawSignalCount ? "text-cmd-amber" : "text-cmd-green"}
        />
        <DataRow label="Majority Direction" value={confluence.majorityDirection} />
      </div>
      <div className="mt-1.5 space-y-1">
        {confluence.families.map((f) => (
          <div key={f.family} className="rounded-sm border border-cmd-border/50 bg-cmd-bg/40 p-1.5 text-[9px]">
            <div className="flex items-center justify-between">
              <span className="text-cmd-cyan">{f.family.replace(/_/g, " ")}</span>
              <span className={f.netDirection === "bullish" ? "text-cmd-green" : f.netDirection === "bearish" ? "text-cmd-red" : "text-cmd-textDim"}>{f.netDirection}</span>
            </div>
            <div className="mt-0.5 text-cmd-textDim">{f.signals.map((s) => s.name).join(", ")}</div>
          </div>
        ))}
      </div>
      <p className="mt-1.5 text-[8px] italic text-cmd-textDim">{confluence.detail}</p>
    </Glass>
  );
}
