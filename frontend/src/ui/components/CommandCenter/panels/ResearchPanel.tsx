import { useGameStore } from "@/ui/hooks/useGameStore";
import type { ResearchCategory } from "@/types";
import { AGENT_PROFILES } from "@/game/systems/AgentProfiles";
import { EmptyState, Glass, StatusPill, TerminalLabel } from "../ui";

// TradeTown's real research taxonomy (see ResearchCategory in types.ts) —
// asset-class categories, not the technical/fundamental/macro/news/
// sentiment breakdown a generic research desk might use. Grouping by
// anything else would mean inventing a classification the backend
// doesn't actually compute.
const CATEGORIES: ResearchCategory[] = ["stock", "etf", "index", "economy", "gold", "bitcoin", "company", "sector"];

export function ResearchPanel() {
  const { research } = useGameStore();

  if (research.length === 0) {
    return <EmptyState>No research items yet.</EmptyState>;
  }

  return (
    <div className="space-y-3">
      {CATEGORIES.map((cat) => {
        const items = research.filter((r) => r.category === cat);
        if (items.length === 0) return null;
        return (
          <Glass key={cat} className="p-3">
            <TerminalLabel>{cat.toUpperCase()} ({items.length})</TerminalLabel>
            <div className="space-y-1.5">
              {[...items]
                .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt))
                .map((item) => (
                  <div key={item.id} className="flex items-center justify-between gap-2 border-b border-cmd-border/50 py-1 last:border-0">
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-cmd-text">
                        {item.title} {item.symbol && <span className="text-cmd-cyan">[{item.symbol}]</span>}
                      </div>
                      <div className="truncate text-[9px] text-cmd-textDim">
                        {AGENT_PROFILES[item.assignedAgent].name} — {item.summary || "No summary yet."}
                      </div>
                    </div>
                    <span className="shrink-0 text-cmd-textDim">{Math.round(item.confidence)}%</span>
                    <StatusPill tone={item.status === "completed" ? "green" : item.status === "in_progress" ? "cyan" : "neutral"}>
                      {item.status.replace("_", " ")}
                    </StatusPill>
                  </div>
                ))}
            </div>
          </Glass>
        );
      })}
    </div>
  );
}
