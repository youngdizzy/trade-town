import { useGameStore } from "@/ui/hooks/useGameStore";
import { EventBus } from "@/game/systems/EventBus";
import type { NewsCategory } from "@/types";

const CATEGORY_LABEL: Record<NewsCategory, string> = {
  company: "Company News",
  discovery: "Agent Discoveries",
  market: "Market Headlines (placeholder)",
};

/** The Lobby newspaper stand's "TradeTown Daily" — company news, agent discoveries, and placeholder market headlines. */
export function Newspaper() {
  const { newspaperOpen, news, time } = useGameStore();
  if (!newspaperOpen) return null;

  const close = () => EventBus.emit("ui:newspaper", { open: false });
  const categories: NewsCategory[] = ["company", "discovery", "market"];

  return (
    <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/60 font-pixel text-[11px]">
      <div className="max-h-[80vh] w-96 overflow-y-auto rounded bg-parchment p-5 text-ink shadow-pixel">
        <h2 className="mb-1 text-center text-lg">TradeTown Daily</h2>
        <p className="mb-4 text-center text-[9px] opacity-60">Day {time.day} · Fresh off the press</p>

        {categories.map((category) => {
          const items = news.filter((n) => n.category === category).slice(-5).reverse();
          return (
            <div key={category} className="mb-4">
              <h3 className="mb-1.5 border-b border-ink/30 pb-1 text-[10px] uppercase tracking-wide opacity-70">
                {CATEGORY_LABEL[category]}
              </h3>
              {items.length === 0 ? (
                <p className="opacity-50">Nothing to report yet.</p>
              ) : (
                <ul className="space-y-1.5">
                  {items.map((item) => (
                    <li key={item.id}>{item.headline}</li>
                  ))}
                </ul>
              )}
            </div>
          );
        })}

        <button
          type="button"
          onClick={close}
          className="w-full rounded bg-panelLight py-2 text-parchment transition-colors hover:bg-gold hover:text-ink"
        >
          Close
        </button>
      </div>
    </div>
  );
}
