import { useGameStore } from "@/ui/hooks/useGameStore";
import { useCloseOnEscape } from "@/ui/hooks/useCloseOnEscape";
import { EventBus } from "@/game/systems/EventBus";
import { AGENT_PROFILES } from "@/game/systems/AgentProfiles";
import { upcomingEvents } from "@/game/systems/UpcomingEvents";
import type { AgentId } from "@/types";

const AGENT_ORDER: AgentId[] = ["scout", "atlas", "echo", "nova", "scribe"];

function companyRatingLabel(overall: number): string {
  if (overall >= 85) return "A — Excellent";
  if (overall >= 70) return "B — Strong";
  if (overall >= 55) return "C — Steady";
  if (overall >= 40) return "D — Needs Work";
  return "F — Struggling";
}

/** The Lobby newspaper stand's "TradeTown Daily" — company news, research updates, agent activity, paper trading results, and placeholder market headlines. */
export function Newspaper() {
  const { newspaperOpen, news, research, tasks, time, paperPortfolio, coachReports, scannerAlerts, companyScore } = useGameStore();
  const close = () => EventBus.emit("ui:newspaper", { open: false });
  useCloseOnEscape(newspaperOpen, close);
  if (!newspaperOpen) return null;

  const companyNews = news.filter((n) => n.category === "company").slice(-5).reverse();
  const marketHeadlines = news.filter((n) => n.category === "market").slice(-5).reverse();
  const researchUpdates = [...research]
    .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt))
    .slice(0, 5);
  const agentActivity = [...tasks].reverse().slice(0, 5);
  const events = upcomingEvents(AGENT_ORDER, time, 5);

  // "Today's trades" — most recently closed trades, the same recency-slice
  // idiom every other section here uses (see companyNews/researchUpdates
  // above) rather than a strict calendar-day filter.
  const todaysTrades = [...paperPortfolio.tradeHistory].reverse().slice(0, 5);
  const topOpportunities = [...research].sort((a, b) => b.confidence - a.confidence).slice(0, 3);
  const latestCoachReport = coachReports[coachReports.length - 1] ?? null;
  const recentAlerts = [...scannerAlerts].slice(-5).reverse();

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

        <NewsSection title="Today's Trades">
          {todaysTrades.length === 0 && <p className="opacity-50">No trades closed yet.</p>}
          <ul className="space-y-1.5">
            {todaysTrades.map((trade) => (
              <li key={trade.id}>
                {trade.symbol}: {trade.pnl >= 0 ? "+" : ""}
                {trade.pnl.toFixed(2)} ({trade.pnlPct.toFixed(1)}%) — {trade.reason}
              </li>
            ))}
          </ul>
        </NewsSection>

        <NewsSection title="Top Opportunities">
          {topOpportunities.length === 0 && <p className="opacity-50">Nothing flagged yet.</p>}
          <ul className="space-y-1.5">
            {topOpportunities.map((item) => (
              <li key={item.id}>
                {AGENT_PROFILES[item.assignedAgent].name}: {item.title} — {Math.round(item.confidence)}% confidence
              </li>
            ))}
          </ul>
        </NewsSection>

        <NewsSection title="Performance">
          <p>
            Cash ${paperPortfolio.cashBalance.toFixed(0)} · Total P&amp;L {paperPortfolio.totalPnl >= 0 ? "+" : ""}
            {paperPortfolio.totalPnl.toFixed(2)} ({paperPortfolio.totalPnlPct.toFixed(1)}%)
          </p>
          <p>
            {paperPortfolio.winCount}W / {paperPortfolio.lossCount}L — simulated, no real capital
          </p>
        </NewsSection>

        <NewsSection title="Coach's Review">
          {latestCoachReport === null && <p className="opacity-50">No Coach report yet — check back this evening.</p>}
          {latestCoachReport !== null && (
            <>
              <p className="mb-1.5">
                {latestCoachReport.period} score: {Math.round(latestCoachReport.companyScore)}/100 · win rate {Math.round(latestCoachReport.winRate)}%
              </p>
              <ul className="space-y-1.5">
                {latestCoachReport.recommendations.map((rec, i) => (
                  // Recommendations are freeform strings with no stable id of
                  // their own (see backend/app/coach.py) — index is safe here
                  // since the whole list is replaced wholesale each report.
                  <li key={i}>{rec}</li>
                ))}
              </ul>
            </>
          )}
        </NewsSection>

        <NewsSection title="Scanner Alerts">
          {recentAlerts.length === 0 && <p className="opacity-50">Pulse hasn't flagged anything yet.</p>}
          <ul className="space-y-1.5">
            {recentAlerts.map((alert) => (
              <li key={alert.id}>
                {alert.symbol}: {alert.message}
              </li>
            ))}
          </ul>
        </NewsSection>

        <NewsSection title="Company Rating">
          <p>
            {Math.round(companyScore.overall)}/100 — {companyRatingLabel(companyScore.overall)}
          </p>
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
