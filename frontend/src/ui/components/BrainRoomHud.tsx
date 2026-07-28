import { useGameStore } from "@/ui/hooks/useGameStore";
import { useCloseOnEscape } from "@/ui/hooks/useCloseOnEscape";
import { EventBus } from "@/game/systems/EventBus";
import { AGENT_PROFILES } from "@/game/systems/AgentProfiles";
import { upcomingEvents } from "@/game/systems/UpcomingEvents";
import type { AgentId, TimeState } from "@/types";

const AGENT_ORDER: AgentId[] = ["scout", "atlas", "echo", "nova", "scribe", "coach", "sentinel", "pulse", "guardian", "cio", "sage"];
const RESEARCHER_ORDER: AgentId[] = ["scout", "atlas", "echo", "nova"];

function formatClock(time: TimeState): string {
  return `Day ${time.day} · ${String(time.hour).padStart(2, "0")}:${String(time.minute).padStart(2, "0")}`;
}

/**
 * The Brain Room's "Mission Control" readouts. Rendered as a React
 * overlay (not in-world Phaser text) so it stays legible regardless of
 * the room's camera zoom; the holographic core and monitor props in
 * BrainRoomScene are the "physical" centerpiece, this panel is the actual
 * readable dashboard. All progress/confidence bars use a CSS transition
 * on width so they visibly animate as values change tick to tick, rather
 * than snapping.
 *
 * Shows automatically (ambient, no close button) while physically standing
 * in Brain Room, same as always — but can also be pulled up from anywhere
 * via the toolbar's "Dashboard" button (ui:brainRoomHud), same pattern as
 * Newspaper/Company Memory/Coach Dashboard, since the numbers here are
 * genuinely company-wide, not something that should require a walk back to
 * one specific room to check.
 */
export function BrainRoomHud() {
  const {
    currentScene,
    brainRoomHudOpen,
    agents,
    tasks,
    news,
    research,
    watchlist,
    time,
    companyScore,
    backtestSessions,
    paperPortfolio,
    coachReports,
    memory,
    riskLimits,
    riskWarnings,
    scannerAlerts,
    decisions,
  } = useGameStore();
  const close = () => EventBus.emit("ui:brainRoomHud", { open: false });
  useCloseOnEscape(brainRoomHudOpen, close);
  const ambient = currentScene === "BrainRoomScene";
  if ((!ambient && !brainRoomHudOpen) || !agents) return null;

  const working = AGENT_ORDER.filter((id) => !["lobby", "break-room"].includes(agents[id].location)).length;
  const avgMood = Math.round(AGENT_ORDER.reduce((sum, id) => sum + agents[id].mood, 0) / AGENT_ORDER.length);
  const avgEnergy = Math.round(AGENT_ORDER.reduce((sum, id) => sum + agents[id].energy, 0) / AGENT_ORDER.length);

  const recentTasks = [...tasks].reverse().slice(0, 6);
  const discoveries = news.filter((n) => n.category === "discovery").slice(-4).reverse();
  const marketHeadlines = news.filter((n) => n.category === "market").slice(-3).reverse();
  const activeResearch = RESEARCHER_ORDER.map((id) => research.find((r) => r.assignedAgent === id && r.status === "in_progress")).filter(
    (item): item is NonNullable<typeof item> => item != null,
  );

  const upcoming = upcomingEvents(AGENT_ORDER, time);
  const activeSessions = backtestSessions.filter((s) => s.status !== "completed").slice(0, 4);
  const latestReport = coachReports[coachReports.length - 1] ?? null;
  const knowledgeEntries = memory.filter((m) => m.category === "lesson" || m.category === "mistake" || m.category === "strategy").slice(-4).reverse();

  const openPositions = paperPortfolio.positions.slice(0, 6);
  const pendingOrders = paperPortfolio.orders.filter((o) => o.status === "open").slice(0, 6);
  const latestDecision = decisions[decisions.length - 1] ?? null;
  const recentAlerts = [...scannerAlerts].slice(-4).reverse();
  const worstWarning = riskWarnings.some((w) => w.severity === "critical") ? "critical" : riskWarnings.some((w) => w.severity === "warning") ? "warning" : null;

  return (
    <div
      className={`absolute right-3 top-16 bottom-24 w-72 overflow-y-auto rounded border border-[#60d1ff]/40 bg-panel/90 p-3 font-pixel text-[10px] text-parchment shadow-pixel ${
        brainRoomHudOpen ? "pointer-events-auto" : "pointer-events-none"
      }`}
    >
      {brainRoomHudOpen && (
        <button
          type="button"
          onClick={close}
          className="sticky top-0 float-right -mt-1 -mr-1 rounded bg-panelLight px-2 py-0.5 text-parchment shadow-pixel transition-colors hover:bg-gold hover:text-ink"
        >
          Close
        </button>
      )}
      <Section title="Market Clock">
        <div className="text-gold">{formatClock(time)}</div>
      </Section>

      <Section title="Company Status">
        <div>{working} of {AGENT_ORDER.length} agents actively working</div>
        <div>Average mood: {avgMood} · Average energy: {avgEnergy}</div>
      </Section>

      <Section title="Company Rating">
        <div className="flex items-center justify-between gap-1.5">
          <span className="text-gold">Overall</span>
          <span>{Math.round(companyScore.overall)}/100</span>
        </div>
        <ConfidenceBar value={companyScore.overall} />
        <div className="mt-1.5 grid grid-cols-2 gap-x-2 gap-y-0.5 opacity-80">
          <div>Research {Math.round(companyScore.researchQuality)}</div>
          <div>Decisions {Math.round(companyScore.decisionQuality)}</div>
          <div>Risk {Math.round(companyScore.riskManagement)}</div>
          <div>Paper P&amp;L {Math.round(companyScore.paperTradingPerformance)}</div>
          <div>Teamwork {Math.round(companyScore.teamCoordination)}</div>
          <div>Simulation {Math.round(companyScore.simulationSuccess)}</div>
        </div>
      </Section>

      <Section title="Paper Portfolio">
        <div className="flex items-center justify-between gap-1.5">
          <span>Cash</span>
          <span className="text-gold">${paperPortfolio.cashBalance.toFixed(0)}</span>
        </div>
        <div className="flex items-center justify-between gap-1.5">
          <span>Total P&amp;L</span>
          <span className={paperPortfolio.totalPnl >= 0 ? "text-bullish" : "text-bearish"}>
            {paperPortfolio.totalPnl >= 0 ? "+" : ""}
            {paperPortfolio.totalPnl.toFixed(2)} ({paperPortfolio.totalPnlPct.toFixed(1)}%)
          </span>
        </div>
        <div className="opacity-70">
          {paperPortfolio.positions.length} open · {paperPortfolio.winCount}W / {paperPortfolio.lossCount}L — simulated, no real capital
        </div>
      </Section>

      <Section title="Open Positions">
        {openPositions.length === 0 && <div className="opacity-50">No open positions.</div>}
        {openPositions.map((p) => (
          <div key={p.id} className="mb-1 flex items-center justify-between gap-1.5">
            <span className="text-gold">{p.symbol}</span>
            <span className="opacity-70">
              {p.quantity.toFixed(2)} @ ${p.entryPrice.toFixed(2)}
            </span>
            <span className={p.unrealizedPnl >= 0 ? "text-bullish" : "text-bearish"}>
              {p.unrealizedPnl >= 0 ? "+" : ""}
              {p.unrealizedPnlPct.toFixed(1)}%
            </span>
          </div>
        ))}
      </Section>

      <Section title="Pending Orders">
        {pendingOrders.length === 0 && <div className="opacity-50">No pending orders.</div>}
        {pendingOrders.map((o) => (
          <div key={o.id} className="mb-1">
            <div className="flex items-center justify-between gap-1.5">
              <span className="text-gold">{o.symbol}</span>
              <span className="opacity-70">{o.side} · {o.orderType.replace("_", " ")}</span>
            </div>
            <div className="opacity-60">{o.quantity.toFixed(2)} @ ${o.price.toFixed(2)} — {AGENT_PROFILES[o.placedBy].name}</div>
          </div>
        ))}
      </Section>

      <Section title="Risk Management">
        <div className="flex items-center justify-between gap-1.5">
          <span>Risk score</span>
          <span className="text-gold">{Math.round(companyScore.riskManagement)}/100</span>
        </div>
        <div className="opacity-70">
          Max position {riskLimits.maxPositionPct.toFixed(0)}% · Max drawdown {riskLimits.maxDrawdownPct.toFixed(0)}% · Max open {riskLimits.maxOpenPositions}
        </div>
        {worstWarning === null && <div className="mt-1 opacity-50">No active risk warnings.</div>}
        {riskWarnings.slice(0, 4).map((w) => (
          <div key={w.id} className={`mt-1 ${w.severity === "critical" ? "text-bearish" : "text-gold"}`}>
            [{w.severity}] {w.message}
          </div>
        ))}
      </Section>

      <Section title="Latest Decision & Votes">
        {latestDecision === null && <div className="opacity-50">No trade decisions yet.</div>}
        {latestDecision !== null && (
          <div>
            <div className="flex items-center justify-between gap-1.5">
              <span className="text-gold">{latestDecision.symbol}</span>
              <span className={latestDecision.outcome === "trade" ? "text-bullish" : "text-bearish"}>
                {latestDecision.outcome === "trade" ? "TRADE" : "NO TRADE"}
              </span>
            </div>
            <div className="mb-1 opacity-70">{latestDecision.finalReasoning}</div>
            {latestDecision.votes.map((v) => (
              <div key={v.agentId} className="flex items-center justify-between gap-1.5 opacity-80">
                <span>{AGENT_PROFILES[v.agentId].name}</span>
                <span className={v.choice === "buy" ? "text-bullish" : v.choice === "sell" ? "text-bearish" : "opacity-70"}>{v.choice.replace(/_/g, " ")}</span>
              </div>
            ))}
          </div>
        )}
      </Section>

      <Section title="Scanner Alerts">
        {recentAlerts.length === 0 && <div className="opacity-50">Pulse hasn't flagged anything yet.</div>}
        {recentAlerts.map((a) => (
          <div key={a.id} className="mb-1 opacity-80">
            <span className="text-gold">{a.symbol}</span> — {a.message}
          </div>
        ))}
      </Section>

      <Section title="Simulation Queue">
        {activeSessions.length === 0 && <div className="opacity-50">No simulations running.</div>}
        {activeSessions.map((s) => (
          <div key={s.id} className="mb-1.5">
            <div className="flex items-center justify-between gap-1.5">
              <span className="truncate text-gold">{s.strategyName} · {s.symbol}</span>
              <span className="shrink-0 opacity-70">{Math.round(s.progress)}%</span>
            </div>
            <ConfidenceBar value={s.progress} />
          </div>
        ))}
      </Section>

      <Section title="Agent Performance">
        {latestReport === null && <div className="opacity-50">No Coach report yet — check back this evening.</div>}
        {latestReport !== null &&
          latestReport.agentRankings.slice(0, 5).map((score) => (
            <div key={score.agentId} className="mb-1 flex items-center justify-between gap-1.5">
              <span className="text-gold">{AGENT_PROFILES[score.agentId].name}</span>
              <span className="opacity-70">
                score {Math.round(score.score)} · acc {Math.round(score.researchAccuracy)}%
              </span>
            </div>
          ))}
      </Section>

      <Section title="Learning Progress">
        <div className="mb-1 opacity-70">Knowledge growth: {Math.round(companyScore.knowledgeGrowth)}/100</div>
        {knowledgeEntries.length === 0 && <div className="opacity-50">No lessons logged yet.</div>}
        {knowledgeEntries.map((entry) => (
          <div key={entry.id} className="mb-1 opacity-80">
            <span className={entry.category === "mistake" ? "text-bearish" : "text-bullish"}>[{entry.category}]</span> {entry.title}
          </div>
        ))}
      </Section>

      <Section title="Agent Status">
        {AGENT_ORDER.map((id) => {
          const profile = AGENT_PROFILES[id];
          const agent = agents[id];
          return (
            <div key={id} className="mb-1.5">
              <div className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full" style={{ backgroundColor: `#${profile.tint.toString(16).padStart(6, "0")}` }} />
                <span className="text-gold">{profile.name}</span>
                <span className="opacity-60">— {agent.location.replace("-", " ")}</span>
              </div>
              <div className="truncate pl-3.5 opacity-80">{agent.currentTask}</div>
            </div>
          );
        })}
      </Section>

      <Section title="Research Queue">
        {activeResearch.length === 0 && <div className="opacity-50">No active research.</div>}
        {activeResearch.map((item) => (
          <div key={item.id} className="mb-2">
            <div className="flex items-center justify-between gap-1.5">
              <span className="truncate text-gold">{AGENT_PROFILES[item.assignedAgent].name}: {item.title}</span>
              <span className="shrink-0 opacity-70">{Math.round(item.confidence)}%</span>
            </div>
            <ConfidenceBar value={item.confidence} />
          </div>
        ))}
      </Section>

      <Section title="Watchlist">
        {watchlist.length === 0 && <div className="opacity-50">No symbols tracked yet.</div>}
        {watchlist.map((entry) => (
          <div key={entry.symbol} className="mb-2">
            <div className="flex items-center justify-between gap-1.5">
              <span className="text-gold">{entry.symbol}</span>
              <span className={entry.dailyChangePct >= 0 ? "text-bullish" : "text-bearish"}>
                ${entry.lastPrice.toFixed(2)} ({entry.dailyChangePct >= 0 ? "+" : ""}{entry.dailyChangePct.toFixed(2)}%)
              </span>
            </div>
            <div className="flex items-center justify-between gap-1.5 opacity-70">
              <span className="truncate">{entry.name}</span>
              <span>{entry.assignedAgent ? AGENT_PROFILES[entry.assignedAgent].name : "—"}</span>
            </div>
            <ConfidenceBar value={entry.researchProgress} />
          </div>
        ))}
      </Section>

      <Section title="Current Tasks">
        {recentTasks.length === 0 && <div className="opacity-50">No tasks logged yet.</div>}
        {recentTasks.map((task) => (
          <div key={task.id} className="mb-1 flex items-start gap-1.5">
            <span
              className={
                task.status === "working"
                  ? "text-gold"
                  : task.status === "completed"
                    ? "text-bullish"
                    : "text-bearish"
              }
            >
              [{task.status}]
            </span>
            <span className="truncate opacity-80">
              {AGENT_PROFILES[task.owner].name}: {task.description}
            </span>
          </div>
        ))}
      </Section>

      <Section title="Upcoming Events">
        {upcoming.length === 0 && <div className="opacity-50">Nothing scheduled.</div>}
        {upcoming.map((event) => (
          <div key={event.agentId} className="mb-1 opacity-80">
            {AGENT_PROFILES[event.agentId].name} → {event.location.replace("-", " ")} at {String(event.atHour).padStart(2, "0")}:00 ({event.task})
          </div>
        ))}
      </Section>

      <Section title="Market Status">
        <div className="mb-1 opacity-50">Placeholder — not connected to a live feed.</div>
        {marketHeadlines.length === 0 && <div className="opacity-50">No headlines yet.</div>}
        {marketHeadlines.map((n) => (
          <div key={n.id} className="mb-1 opacity-80">
            {n.headline}
          </div>
        ))}
      </Section>

      <Section title="Recent Discoveries">
        {discoveries.length === 0 && <div className="opacity-50">Nothing yet — check back soon.</div>}
        {discoveries.map((n) => (
          <div key={n.id} className="mb-1 opacity-80">
            {n.headline}
          </div>
        ))}
      </Section>
    </div>
  );
}

function ConfidenceBar({ value }: { value: number }) {
  return (
    <div className="mt-0.5 h-1 w-full overflow-hidden rounded-full bg-ink/40">
      <div className="h-full rounded-full bg-[#60d1ff] transition-all duration-500 ease-out" style={{ width: `${Math.min(100, Math.max(0, value))}%` }} />
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-3">
      <div className="mb-1 border-b border-[#60d1ff]/30 pb-0.5 text-[#60d1ff]">{title}</div>
      {children}
    </div>
  );
}
