import { useGameStore } from "@/ui/hooks/useGameStore";
import { EventBus } from "@/game/systems/EventBus";
import { AGENT_PROFILES } from "@/game/systems/AgentProfiles";
import { upcomingEvents } from "@/game/systems/UpcomingEvents";
import type { AgentId } from "@/types";

const AGENT_ORDER: AgentId[] = ["scout", "atlas", "echo", "nova", "scribe"];

/** The Lobby newspaper stand's "TradeTown Daily" — company news, research updates, agent activity, and placeholder market headlines. */
export function Newspaper() {
  const { newspaperOpen, news, research, tasks, time } = useGameStore();
  if (!newspaperOpen) return null;

  const close = () => EventBus.emit("ui:newspaper", { open: false });

  const companyNews = news.filter((n) => n.category === "company").slice(-5).reverse();
  const marketHeadlines = news.filter((n) => n.category === "market").slice(-5).reverse();
  const researchUpdates = [...research]
    .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt))
    .slice(0, 5);
  const agentActivity = [...tasks].reverse().slice(0, 5);
  const events = upcomingEvents(AGENT_ORDER, time, 5);

  return (
    <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/60 font-pixel text-[11px]">
      <div className="max-h-[80vh] w-96 overflow-y-auto rounded bg-parchment p-5 text-ink shadow-pixel">
        <h2 className="mb-1 text-center text-lg">TradeTown Daily</h2>
        <p className="mb-4 text-center text-[9px] opacity-60">Day {time.day} · Fresh off the press</p>

        <NewsSection title="Company News">
          {companyNews.length === 0 && <p className="opacity-50">Nothing to report yet.</p>}
          <ul className="space-y-1.5">
            {companyNews.map((item) => (
              <li key={item.id}>{item.headline}</li>
            ))}
          </ul>
        </NewsSection>

        <NewsSection title="Research Updates">
          {researchUpdates.length === 0 && <p className="opacity-50">Nothing to report yet.</p>}
          <ul className="space-y-1.5">
            {researchUpdates.map((item) => (
              <li key={item.id}>
                {AGENT_PROFILES[item.assignedAgent].name}: {item.title} — {item.status === "completed" ? "completed" : `${Math.round(item.confidence)}% confidence`}
              </li>
            ))}
          </ul>
        </NewsSection>

        <NewsSection title="Agent Activity">
          {agentActivity.length === 0 && <p className="opacity-50">Nothing to report yet.</p>}
          <ul className="space-y-1.5">
            {agentActivity.map((task) => (
              <li key={task.id}>
                {AGENT_PROFILES[task.owner].name}: {task.description} [{task.status}]
              </li>
            ))}
          </ul>
        </NewsSection>

        <NewsSection title="Market Headlines (placeholder)">
          {marketHeadlines.length === 0 && <p className="opacity-50">Nothing to report yet.</p>}
          <ul className="space-y-1.5">
            {marketHeadlines.map((item) => (
              <li key={item.id}>{item.headline}</li>
            ))}
          </ul>
        </NewsSection>

        <NewsSection title="Upcoming Events">
          {events.length === 0 && <p className="opacity-50">Nothing scheduled.</p>}
          <ul className="space-y-1.5">
            {events.map((event) => (
              <li key={event.agentId}>
                {AGENT_PROFILES[event.agentId].name} → {event.location.replace("-", " ")} at {String(event.atHour).padStart(2, "0")}:00
              </li>
            ))}
          </ul>
        </NewsSection>

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

function NewsSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-4">
      <h3 className="mb-1.5 border-b border-ink/30 pb-1 text-[10px] uppercase tracking-wide opacity-70">{title}</h3>
      {children}
    </div>
  );
}
