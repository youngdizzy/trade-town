import { useState } from "react";
import { useGameStore } from "@/ui/hooks/useGameStore";
import { useCloseOnEscape } from "@/ui/hooks/useCloseOnEscape";
import { EventBus } from "@/game/systems/EventBus";
import type { MemoryCategory } from "@/types";

const CATEGORY_LABEL: Record<MemoryCategory, string> = {
  research: "Research",
  meeting: "Meeting",
  whiteboard: "Whiteboard",
  event: "Event",
  discussion: "Discussion",
  discovery: "Discovery",
  future_trade: "Future Trade",
  lesson: "Lesson",
  mistake: "Mistake",
  strategy: "Strategy",
  coach_review: "Coach Review",
  simulation: "Simulation",
  paper_trade: "Paper Trade",
  alert: "Scanner Alert",
  vote: "Vote",
  decision: "Decision",
  order: "Order",
  academy: "Academy",
  mentorship: "Mentorship",
  executive: "Executive Review",
};

const CATEGORIES: MemoryCategory[] = [
  "research",
  "discovery",
  "meeting",
  "discussion",
  "whiteboard",
  "event",
  "future_trade",
  "lesson",
  "mistake",
  "strategy",
  "coach_review",
  "simulation",
  "paper_trade",
  "alert",
  "vote",
  "decision",
  "order",
  "academy",
  "mentorship",
  "executive",
];

/**
 * TradeTown's long-term company memory — a searchable log of everything
 * Scribe has recorded (research, meetings, discussions, discoveries,
 * flagged future-trade candidates). Filters the already-synced `memory`
 * list client-side (see backend/app/memory.py's `search()` docstring for
 * why there's no server round-trip) rather than a REST search endpoint.
 */
export function CompanyMemory() {
  const { companyMemoryOpen, memory } = useGameStore();
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState<MemoryCategory | null>(null);
  const close = () => EventBus.emit("ui:companyMemory", { open: false });
  useCloseOnEscape(companyMemoryOpen, close);
  if (!companyMemoryOpen) return null;

  const needle = query.trim().toLowerCase();
  const filtered = [...memory]
    .reverse()
    .filter((record) => (category === null || record.category === category))
    .filter((record) => needle === "" || record.title.toLowerCase().includes(needle) || record.body.toLowerCase().includes(needle))
    .slice(0, 80);

  return (
    <div className="pointer-events-auto absolute inset-0 z-50 flex items-center justify-center bg-black/60 font-pixel text-[11px]">
      <div className="flex max-h-[80vh] w-[30rem] flex-col overflow-hidden rounded bg-parchment text-ink shadow-pixel">
        <div className="p-5 pb-3">
          <h2 className="mb-1 text-center text-lg">Company Memory</h2>
          <p className="mb-3 text-center text-[9px] opacity-60">{memory.length} records logged by Scribe</p>

          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search research, meetings, discoveries..."
            className="mb-2 w-full rounded border border-ink/30 bg-white/60 px-2 py-1.5 text-ink outline-none focus:border-ink/60"
          />
          <div className="flex flex-wrap gap-1">
            <FilterChip label="All" active={category === null} onClick={() => setCategory(null)} />
            {CATEGORIES.map((c) => (
              <FilterChip key={c} label={CATEGORY_LABEL[c]} active={category === c} onClick={() => setCategory(c)} />
            ))}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto border-t border-ink/20 px-5 py-3">
          {filtered.length === 0 ? (
            <p className="opacity-50">No matching records.</p>
          ) : (
            <ul className="space-y-3">
              {filtered.map((record) => (
                <li key={record.id} className="border-b border-ink/10 pb-2">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-bold">{record.title}</span>
                    <span className="shrink-0 rounded bg-ink/10 px-1.5 py-0.5 text-[8px] uppercase tracking-wide opacity-70">
                      {CATEGORY_LABEL[record.category]}
                    </span>
                  </div>
                  <p className="mt-0.5 opacity-80">{record.body}</p>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="p-5 pt-3">
          <button
            type="button"
            onClick={close}
            className="w-full rounded bg-panelLight py-2 text-parchment transition-colors hover:bg-gold hover:text-ink"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

function FilterChip({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded px-2 py-1 text-[9px] transition-colors ${active ? "bg-ink text-parchment" : "bg-ink/10 text-ink hover:bg-ink/20"}`}
    >
      {label}
    </button>
  );
}
