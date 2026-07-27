import { useState } from "react";
import { useGameStore } from "@/ui/hooks/useGameStore";
import type { MemoryCategory } from "@/types";
import { EmptyState, Glass, TerminalLabel } from "../ui";

const CATEGORY_TONE: Record<string, string> = {
  decision: "text-cmd-green",
  vote: "text-cmd-cyan",
  order: "text-cmd-amber",
  alert: "text-cmd-red",
  mistake: "text-cmd-red",
  lesson: "text-cmd-green",
};

/** MemoryRecord *is* TradeTown's system log — "the searchable long-term log" per its own doc comment (types.ts) — reused directly rather than inventing a parallel log format. */
export function LogsPanel() {
  const { memory } = useGameStore();
  const [filter, setFilter] = useState<MemoryCategory | "all">("all");

  const categories = Array.from(new Set(memory.map((m) => m.category))).sort();
  const filtered = [...memory].reverse().filter((m) => filter === "all" || m.category === filter);

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <TerminalLabel>System Log ({filtered.length} of {memory.length})</TerminalLabel>
        <div className="flex flex-wrap gap-1">
          <button
            type="button"
            onClick={() => setFilter("all")}
            className={`rounded-sm border px-2 py-0.5 text-[9px] uppercase transition-colors ${filter === "all" ? "border-cmd-cyan/50 text-cmd-cyan" : "border-cmd-border text-cmd-textDim"}`}
          >
            All
          </button>
          {categories.map((c) => (
            <button
              key={c}
              type="button"
              onClick={() => setFilter(c)}
              className={`rounded-sm border px-2 py-0.5 text-[9px] uppercase transition-colors ${filter === c ? "border-cmd-cyan/50 text-cmd-cyan" : "border-cmd-border text-cmd-textDim"}`}
            >
              {c.replace("_", " ")}
            </button>
          ))}
        </div>
      </div>

      {filtered.length === 0 ? (
        <EmptyState>No log entries yet.</EmptyState>
      ) : (
        <Glass className="max-h-[60vh] overflow-y-auto p-3">
          <div className="space-y-1.5">
            {filtered.slice(0, 200).map((entry) => (
              <div key={entry.id} className="border-b border-cmd-border/50 pb-1 last:border-0">
                <div className="flex items-center gap-2">
                  <span className={`text-[9px] uppercase ${CATEGORY_TONE[entry.category] ?? "text-cmd-textDim"}`}>[{entry.category.replace("_", " ")}]</span>
                  <span className="text-cmd-text">{entry.title}</span>
                  <span className="ml-auto shrink-0 text-[9px] text-cmd-textDim">{new Date(entry.timestamp).toLocaleString()}</span>
                </div>
                {entry.body && <div className="text-[9px] text-cmd-textDim">{entry.body}</div>}
              </div>
            ))}
          </div>
        </Glass>
      )}
    </div>
  );
}
