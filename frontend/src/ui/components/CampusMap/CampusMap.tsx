import { useEffect, useMemo, useState } from "react";
import { useGameStore } from "@/ui/hooks/useGameStore";
import { useCloseOnEscape } from "@/ui/hooks/useCloseOnEscape";
import { EventBus } from "@/game/systems/EventBus";
import { GameManager } from "@/game/systems/GameManager";
import { SceneManager } from "@/game/systems/SceneManager";
import { AssetLoader } from "@/game/systems/AssetLoader";
import { AGENT_IDS } from "@/types";
import type { AgentId, AgentLocation } from "@/types";
import { AGENT_PROFILES } from "@/game/systems/AgentProfiles";
import { nextScheduleBlock, scheduleBlockForHour } from "@/game/systems/Schedule";
import { CAMPUS_BUILDINGS, CATEGORY_LABEL, MAP_HEIGHT_PX, MAP_WIDTH_PX, relatedDepartments, type CampusBuilding, type CampusBuildingCategory } from "./buildings";
import { AnimatedGrid, DataRow, Glass, StatusPill, TerminalLabel } from "../CommandCenter/ui";

/**
 * v0.7 Feature 38 — the Company Campus Map (the spec calls this "Feature
 * 37," but that number is already the shipped Work Mode System — tracked
 * internally as 38 to avoid collision).
 *
 * Uses the actual TradeTown world as the map, exactly as asked: every
 * building below is imported straight from LobbyScene.ts's own real
 * `DOORS` array (never a second, hand-authored copy of those
 * coordinates), positioned at its real in-game pixel location, scaled
 * into this schematic viewport. Employee icons sit at their real current
 * `AgentState.location`, animated with a CSS position transition so a
 * location change (delivered on the next ~2s WS tick, same cadence every
 * other live readout in this game already updates on) glides rather than
 * snaps — genuinely alive, without fabricating intermediate waypoints or
 * pathfinding.
 *
 * Explicit scope cuts from the brief, matching this whole session's
 * "real data or don't build it" convention:
 *   - The brief's 17-building "Official Campus Layout" (Think Tank,
 *     Library, a physical Reasoning Lab/Treasury/Headquarters/Cafe/
 *     Garden/Gym/Employee Residence/Park/Museum/Dock) is not built —
 *     this codebase has exactly 11 real doors plus the Lobby courtyard
 *     (see buildings.ts), and several of the brief's named buildings are
 *     Command-Center tabs, not physical scenes, by earlier features' own
 *     established "tab, not new art" precedent (Academy/Reasoning Lab/
 *     Reflection Chamber/Treasury all already made that call). The real
 *     roster is used instead of inventing placeholder rooms for names
 *     with no backing scene.
 *   - Building Upgrade Levels / Construction stages (Empty Lot →
 *     Landmark, scaffolding, cranes, sounds) are cut outright — no
 *     per-building progression is tracked anywhere in this codebase, and
 *     `CompanyHealth.marketCoverage` (renamed from `officeExpansion`
 *     under the CEO's Company/Executive Health directive — same real
 *     formula, honest name) is a single company-wide score, not
 *     11 independent per-building tracks; fabricating one would either
 *     duplicate that real number under 11 fake labels or invent a whole
 *     new random-progress system with no data behind it.
 *   - Per-building statistics (Lifetime Visitors, Most Active Employee,
 *     Monthly Performance, Daily Operating Cost, Power Status, Building
 *     Health) are cut — no per-building visit log, cost/budget system, or
 *     health/power model exists anywhere in this codebase. Where a real
 *     company-wide equivalent exists and genuinely matches a building's
 *     purpose (completed research count for the Brain Room, Hall of Fame
 *     entry count, simulation results for the Simulation Lab, ...), that
 *     real number is shown instead, labeled as what it actually is.
 *   - New per-building decorative animations (floating research icons,
 *     vault security, students entering classrooms, ...) are cut — this
 *     asset pack has no sprites for any of them, the same boundary every
 *     recent feature already drew. The map's "alive" feeling instead
 *     comes from real, live employee movement and status.
 *   - "The camera smoothly flies there" is the same real fade transition
 *     every door in this multi-scene (not single continuous open-world)
 *     game already uses (`SceneManager.goTo`) — not a fabricated
 *     continuous pan across scenes that were never built to be traversed
 *     that way.
 *   - "Current Weather" is cut — no weather system exists anywhere in
 *     this codebase.
 *
 * Addendum: the Campus Overview panel's "HQ Expansion" visual (below)
 * uses five real hand-sliced frames from a legacy Cute Fantasy building-
 * stages sprite sheet the user supplied directly (Old_Sprites.zip ->
 * Houses_Building_Stages_OLD/House_1_Stone_Stages.png, sliced into
 * assets/cute-fantasy-rpg/props/buildings/hq-expansion/stage-{1-5}.png).
 * It's deliberately still bound to the one real company-wide number from
 * the scope-cut above — `CompanyHealth.marketCoverage` (renamed from
 * `officeExpansion` under the CEO's Company/Executive Health directive)
 * — mapped onto
 * whichever of the 5 real stage frames it falls into. This is NOT the
 * brief's fabricated per-building construction system: one visual, tied
 * to one already-real score, not 11 invented per-building progress
 * tracks.
 */

type BuildingStatus = "normal" | "busy" | "meeting" | "attention" | "idle";

const STATUS_META: Record<BuildingStatus, { label: string; dot: string; tone: "green" | "amber" | "purple" | "red" | "neutral" }> = {
  normal: { label: "Operating Normally", dot: "🟢", tone: "green" },
  busy: { label: "Busy", dot: "🟡", tone: "amber" },
  meeting: { label: "Meeting in Progress", dot: "🟣", tone: "purple" },
  attention: { label: "Requires Attention", dot: "🔴", tone: "red" },
  idle: { label: "Idle", dot: "⚪", tone: "neutral" },
};

const CATEGORIES: CampusBuildingCategory[] = ["research", "trading", "leadership", "housing", "entertainment", "operations"];

/** Five real sprite frames (see this file's module docstring addendum),
 * mapped onto the one real company-wide `CompanyHealth.marketCoverage`
 * score (renamed from `officeExpansion`) — never a fabricated
 * per-building progress track. */
const HQ_EXPANSION_STAGES = [
  { id: "props/buildings/hq-expansion/stage-1", label: "Foundation" },
  { id: "props/buildings/hq-expansion/stage-2", label: "Framing" },
  { id: "props/buildings/hq-expansion/stage-3", label: "Structure Raised" },
  { id: "props/buildings/hq-expansion/stage-4", label: "Walls & Roof" },
  { id: "props/buildings/hq-expansion/stage-5", label: "Complete" },
] as const;

function HQExpansionVisual({ marketCoverage }: { marketCoverage: number }) {
  const stageIndex = Math.min(HQ_EXPANSION_STAGES.length - 1, Math.floor((marketCoverage / 100) * HQ_EXPANSION_STAGES.length));
  const stage = HQ_EXPANSION_STAGES[stageIndex] ?? HQ_EXPANSION_STAGES[0];
  return (
    <div
      className="flex shrink-0 items-center gap-2 border-t border-cmd-border/50 pt-2 sm:border-l sm:border-t-0 sm:pl-3 sm:pt-0"
      title={`Market Coverage — ${marketCoverage.toFixed(0)}% (${stage.label})`}
    >
      <img src={AssetLoader.get(stage.id).url} alt={`HQ expansion stage: ${stage.label}`} className="h-14 w-auto [image-rendering:pixelated]" />
      <div className="text-[9px]">
        <div className="uppercase tracking-wide text-cmd-textDim">HQ Expansion</div>
        <div className="text-cmd-cyan">
          {marketCoverage.toFixed(0)}% — {stage.label}
        </div>
      </div>
    </div>
  );
}

function buildingStatus(building: CampusBuilding, agentsHere: AgentId[], meetingActive: boolean, tradingAttention: boolean): BuildingStatus {
  if (building.location === "meeting-room" && meetingActive) return "meeting";
  if (building.sceneId === "TradingFloorScene" && tradingAttention) return "attention";
  if (agentsHere.length === 0) return "idle";
  if (agentsHere.length >= 3) return "busy";
  return "normal";
}

/** One real, relevant metric per building — never a fabricated per-
 * building stat (see this file's own scope-cut note above). */
function buildingMetric(building: CampusBuilding, store: ReturnType<typeof useGameStore>): { label: string; value: string } | null {
  switch (building.sceneId) {
    case "BrainRoomScene":
      return { label: "Active Research Items", value: String(store.research.filter((r) => r.status === "in_progress").length) };
    case "SimulationLabScene":
      return { label: "Backtests Completed", value: String(store.simulationResults.length) };
    case "HallOfFameScene":
      return { label: "Hall of Fame Entries", value: String(store.hallOfFame.length) };
    case "TradingFloorScene":
      return { label: "Closed Trades", value: String(store.paperPortfolio.winCount + store.paperPortfolio.lossCount) };
    case "PerformanceCenterScene":
      return { label: "Performance Snapshots", value: String(store.performanceSnapshots.length) };
    case "ExecutiveBoardroomScene":
      return { label: "Executive Reviews Filed", value: String(store.executiveReviews.length) };
    case "MeetingRoomScene":
      return { label: "Meetings Held Today", value: String(store.meetingMinutes.filter((m) => m.day === store.time.day).length) };
    case "MarketObservatoryScene":
      return { label: "Symbols Watched", value: String(store.watchlist.length) };
    case "ScoutOfficeScene":
      return { label: "News Items Filed", value: String(store.news.length) };
    default:
      return null;
  }
}

export function CampusMap() {
  const store = useGameStore();
  const { campusMapOpen, agents, time, meeting, riskWarnings, paperPortfolio, treasury, academyState, wisdomState, companyHealth, calendar, settings, currentScene } = store;
  const [selectedBuilding, setSelectedBuilding] = useState<string | null>(null);
  const [selectedAgent, setSelectedAgent] = useState<AgentId | null>(null);
  const [categoryFilter, setCategoryFilter] = useState<CampusBuildingCategory | "all">("all");
  const [statusFilter, setStatusFilter] = useState<"all" | "busy" | "idle">("all");

  const close = () => EventBus.emit("ui:campusMap", { open: false });
  useCloseOnEscape(campusMapOpen, close);

  // The M key toggles the map open/closed from anywhere — mirrors Tab's
  // own always-listening pattern in CommandCenter.tsx. Ignored while
  // typing in a form field, the same guard every other global shortcut
  // in this game already uses.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key.toLowerCase() !== "m") return;
      const target = e.target as HTMLElement | null;
      if (target && ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName)) return;
      if (campusMapOpen) close();
      else EventBus.emit("ui:campusMap", { open: true });
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [campusMapOpen]);

  const tradingAttention = riskWarnings.some((w) => w.severity === "critical");

  const agentsByLocation = useMemo(() => {
    const map: Partial<Record<AgentLocation, AgentId[]>> = {};
    if (!agents) return map;
    for (const id of AGENT_IDS) {
      const loc = agents[id]?.location;
      if (!loc) continue;
      (map[loc] ??= []).push(id);
    }
    return map;
  }, [agents]);

  const buildingsWithStatus = useMemo(
    () =>
      CAMPUS_BUILDINGS.map((b) => {
        const here = b.location ? (agentsByLocation[b.location] ?? []) : [];
        return { building: b, agentsHere: here, status: buildingStatus(b, here, meeting.active, tradingAttention) };
      }),
    [agentsByLocation, meeting.active, tradingAttention]
  );

  const visibleBuildings = buildingsWithStatus.filter(({ building, status }) => {
    if (categoryFilter !== "all" && building.category !== categoryFilter) return false;
    if (statusFilter === "busy" && status !== "busy" && status !== "meeting") return false;
    if (statusFilter === "idle" && status !== "idle") return false;
    return true;
  });

  if (!campusMapOpen) return null;

  const selected = selectedBuilding ? buildingsWithStatus.find((b) => b.building.sceneId === selectedBuilding) ?? null : null;
  const todayEvents = calendar.systemEvents.filter((e) => e.day === time.day);
  const avgMood = agents ? AGENT_IDS.reduce((sum, id) => sum + (agents[id]?.mood ?? 0), 0) / AGENT_IDS.length : 0;
  const avgEnergy = agents ? AGENT_IDS.reduce((sum, id) => sum + (agents[id]?.energy ?? 0), 0) / AGENT_IDS.length : 0;

  const fastTravel = (sceneId: CampusBuilding["sceneId"]) => {
    const gm = GameManager.getInstance();
    if (!gm) return;
    const currentSceneObj = gm.game.scene.getScene(gm.playerTransform.scene);
    close();
    if (currentSceneObj) {
      SceneManager.goTo(currentSceneObj, sceneId, { fromScene: gm.playerTransform.scene });
    } else {
      gm.applyLoadedTransform({ scene: sceneId, x: 0, y: 0, facing: "down" });
    }
  };

  return (
    <div className="pointer-events-auto absolute inset-0 z-50 flex items-center justify-center bg-black/70 p-[4vh] font-cmdmono text-[11px] text-cmd-text backdrop-blur-sm">
      <div className="motion-safe:animate-cmd-overlay-in relative flex h-full w-full max-w-[1500px] flex-col overflow-hidden rounded-md border border-cmd-cyan/30 bg-cmd-bg shadow-cmd-cyan">
        <AnimatedGrid />
        <header className="relative flex items-center justify-between border-b border-cmd-border px-4 py-2.5">
          <div className="flex items-center gap-3">
            <span className="tracking-[0.2em] text-cmd-cyan">COMPANY CAMPUS MAP</span>
            <span className="text-cmd-textDim">
              Day {time.day} · {String(time.hour).padStart(2, "0")}:{String(time.minute).padStart(2, "0")}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[9px] text-cmd-textDim">Press M or Esc to close</span>
            <button
              type="button"
              onClick={close}
              className="rounded-sm border border-cmd-border px-2.5 py-1 text-cmd-textDim transition-colors hover:border-cmd-red/50 hover:text-cmd-red"
            >
              CLOSE ✕
            </button>
          </div>
        </header>

        <div className="relative grid flex-1 grid-cols-1 gap-3 overflow-y-auto p-3 lg:grid-cols-4">
          {/* Campus Overview */}
          <Glass className="p-3 lg:col-span-4">
            <TerminalLabel>Campus Overview</TerminalLabel>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start">
              <div className="grid flex-1 grid-cols-2 gap-x-4 gap-y-1 sm:grid-cols-4 lg:grid-cols-6">
                <DataRow label="Company Score" value={store.companyScore.overall.toFixed(0)} />
                <DataRow label="Treasury" value={`$${treasury.balance.toLocaleString(undefined, { maximumFractionDigits: 0 })}`} />
                <DataRow label="Operating Capital" value={`$${paperPortfolio.cashBalance.toLocaleString(undefined, { maximumFractionDigits: 0 })}`} />
                <DataRow label="Knowledge Score" value={academyState.totalPoints.toFixed(0)} />
                <DataRow label="Wisdom Score" value={wisdomState.score.toFixed(0)} />
                <DataRow label="Research Progress" value={`${companyHealth.researchProgress.toFixed(0)}%`} />
                <DataRow label="Employee Count" value={String(AGENT_IDS.length)} />
                <DataRow label="Avg. Happiness" value={avgMood.toFixed(0)} />
                <DataRow label="Avg. Energy" value={avgEnergy.toFixed(0)} />
                <DataRow label="Today's Events" value={String(todayEvents.length)} />
                <DataRow label="Company Priority" value={settings.companyPriority.replace("_", " ").toUpperCase()} />
                <DataRow label="Work Mode" value={settings.workMode === "rest" ? "REST" : "WORK"} />
              </div>
              <HQExpansionVisual marketCoverage={companyHealth.marketCoverage} />
            </div>
          </Glass>

          {/* Filters */}
          <Glass className="p-2.5 lg:col-span-4">
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="mr-1 text-[9px] uppercase tracking-wide text-cmd-textDim">Filter:</span>
              <FilterChip active={categoryFilter === "all"} onClick={() => setCategoryFilter("all")} label="All" />
              {CATEGORIES.map((c) => (
                <FilterChip key={c} active={categoryFilter === c} onClick={() => setCategoryFilter(c)} label={CATEGORY_LABEL[c]} />
              ))}
              <span className="mx-1 text-cmd-border">|</span>
              <FilterChip active={statusFilter === "all"} onClick={() => setStatusFilter("all")} label="All Status" />
              <FilterChip active={statusFilter === "busy"} onClick={() => setStatusFilter("busy")} label="Busy" />
              <FilterChip active={statusFilter === "idle"} onClick={() => setStatusFilter("idle")} label="Idle" />
            </div>
          </Glass>

          {/* Map */}
          <Glass className="relative min-h-[420px] overflow-hidden p-2 lg:col-span-3">
            <div className="relative h-full w-full" style={{ aspectRatio: `${MAP_WIDTH_PX} / ${MAP_HEIGHT_PX}` }}>
              {buildingsWithStatus.map(({ building, status }) => {
                const visible = visibleBuildings.some((v) => v.building.sceneId === building.sceneId);
                const leftPct = (building.x / MAP_WIDTH_PX) * 100;
                const topPct = (building.y / MAP_HEIGHT_PX) * 100;
                const meta = STATUS_META[status];
                const isSelected = selectedBuilding === building.sceneId;
                return (
                  <button
                    key={building.sceneId}
                    type="button"
                    onClick={() => {
                      setSelectedBuilding(building.sceneId);
                      setSelectedAgent(null);
                    }}
                    onDoubleClick={() => fastTravel(building.sceneId)}
                    className={`absolute flex -translate-x-1/2 -translate-y-1/2 flex-col items-center gap-0.5 transition-all duration-700 ease-out ${visible ? "opacity-100" : "opacity-20"}`}
                    style={{ left: `${leftPct}%`, top: `${topPct}%` }}
                    title={`${building.label} — double-click to fast travel`}
                  >
                    <span
                      className={`flex h-9 w-9 items-center justify-center rounded-full border text-[13px] transition-colors motion-safe:animate-cmd-glow-pulse ${
                        isSelected ? "border-cmd-cyan bg-cmd-cyan/20 shadow-cmd-cyan" : "border-cmd-cyan/40 bg-cmd-bg/80"
                      }`}
                    >
                      {meta.dot}
                    </span>
                    <span className="whitespace-nowrap rounded-sm bg-cmd-bg/80 px-1 text-[8px] uppercase tracking-wide text-cmd-text">{building.label}</span>
                  </button>
                );
              })}

              {AGENT_IDS.map((id) => {
                const state = agents?.[id];
                if (!state) return null;
                const building = CAMPUS_BUILDINGS.find((b) => b.location === state.location);
                if (!building) return null;
                const peers = agentsByLocation[state.location] ?? [];
                const indexAmongPeers = peers.indexOf(id);
                const angle = (indexAmongPeers / Math.max(peers.length, 1)) * Math.PI * 2;
                // v0.7 Feature 39 grew the roster to 13, and every agent's
                // real schedule shares the same break-room location during
                // sleep (0:00-6:00) — a fixed radius that worked for a
                // handful of peers left icons overlapping (and blocking
                // each other's clicks) once a dozen could crowd one spot.
                // Scale with peer count so the circle's circumference keeps
                // pace with how many icons need to fit on it.
                const offsetRadius = peers.length > 1 ? Math.max(20, peers.length * 7) : 0;
                const leftPct = ((building.x + Math.cos(angle) * offsetRadius) / MAP_WIDTH_PX) * 100;
                const topPct = ((building.y + Math.sin(angle) * offsetRadius - 26) / MAP_HEIGHT_PX) * 100;
                return (
                  <button
                    key={id}
                    type="button"
                    onClick={() => {
                      setSelectedAgent(id);
                      setSelectedBuilding(null);
                    }}
                    className={`absolute flex h-5 w-5 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full border text-[10px] transition-all duration-1000 ease-out ${
                      selectedAgent === id ? "border-cmd-amber bg-cmd-amber/30 shadow-cmd-amber" : "border-cmd-green/60 bg-cmd-bg"
                    }`}
                    style={{ left: `${leftPct}%`, top: `${topPct}%` }}
                    title={`${AGENT_PROFILES[id].name} — ${state.currentTask}`}
                  >
                    {AGENT_PROFILES[id].badge}
                  </button>
                );
              })}
            </div>
          </Glass>

          {/* Side panel */}
          <div className="flex flex-col gap-3 lg:col-span-1">
            {selected && <BuildingInfoPanel entry={selected} store={store} onFastTravel={() => fastTravel(selected.building.sceneId)} />}
            {selectedAgent && <EmployeePanel agentId={selectedAgent} store={store} />}
            {!selected && !selectedAgent && (
              <Glass className="p-3 text-[9px] text-cmd-textDim">
                Click a building or an employee icon on the map for details. Double-click a building to fast travel there.
                {currentScene && <div className="mt-2 text-cmd-cyan">Currently in: {currentScene}</div>}
              </Glass>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function FilterChip({ active, onClick, label }: { active: boolean; onClick: () => void; label: string }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-sm border px-2 py-1 text-[9px] uppercase tracking-wide transition-colors ${
        active ? "border-cmd-cyan/50 bg-cmd-cyan/10 text-cmd-cyan" : "border-cmd-border/60 text-cmd-textDim hover:text-cmd-text"
      }`}
    >
      {label}
    </button>
  );
}

function BuildingInfoPanel({
  entry,
  store,
  onFastTravel,
}: {
  entry: { building: CampusBuilding; agentsHere: AgentId[]; status: BuildingStatus };
  store: ReturnType<typeof useGameStore>;
  onFastTravel: () => void;
}) {
  const { building, agentsHere, status } = entry;
  const meta = STATUS_META[status];
  const metric = buildingMetric(building, store);
  const departments = relatedDepartments(building.location);

  return (
    <Glass className="max-h-[70vh] overflow-y-auto p-3">
      <div className="mb-1 flex items-center justify-between">
        <span className="text-cmd-cyan">{building.label}</span>
        <StatusPill tone={meta.tone}>
          {meta.dot} {meta.label}
        </StatusPill>
      </div>
      <p className="mb-2 text-[9px] text-cmd-textDim">{building.purpose}</p>

      <div className="mb-2 space-y-1 border-t border-cmd-border/50 pt-2">
        <DataRow label="Category" value={CATEGORY_LABEL[building.category]} />
        <DataRow label="Current Employees" value={String(agentsHere.length)} />
        {metric && <DataRow label={metric.label} value={metric.value} />}
      </div>

      {agentsHere.length > 0 && (
        <div className="mb-2 border-t border-cmd-border/50 pt-2">
          <div className="mb-1 text-[9px] uppercase tracking-wide text-cmd-textDim">Current Activity</div>
          <div className="space-y-1">
            {agentsHere.map((id) => (
              <div key={id} className="text-[9px]">
                <span className="text-cmd-text">{AGENT_PROFILES[id].name}</span> <span className="text-cmd-textDim">— {store.agents?.[id]?.currentTask}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {departments.length > 0 && (
        <div className="mb-2 border-t border-cmd-border/50 pt-2">
          <div className="mb-1 text-[9px] uppercase tracking-wide text-cmd-textDim">Related Departments</div>
          <div className="text-[9px] text-cmd-textDim">{departments.map((id) => AGENT_PROFILES[id].name).join(", ")}</div>
        </div>
      )}

      <button
        type="button"
        onClick={onFastTravel}
        className="mt-2 w-full rounded-sm border border-cmd-cyan/50 py-1.5 text-[10px] uppercase tracking-wider text-cmd-cyan transition-colors hover:bg-cmd-cyan/10"
      >
        Fast Travel ▸
      </button>
    </Glass>
  );
}

function EmployeePanel({ agentId, store }: { agentId: AgentId; store: ReturnType<typeof useGameStore> }) {
  const state = store.agents?.[agentId];
  const profile = AGENT_PROFILES[agentId];
  if (!state) return null;

  const activeResearch = store.research.find((r) => r.assignedAgent === agentId && r.status === "in_progress") ?? null;
  const level = store.agentKnowledge[agentId]?.level ?? null;
  const inMeeting = store.meeting.active && store.meeting.participants.includes(agentId);
  const lastLine = inMeeting && store.meeting.discussion.length > 0 ? store.meeting.discussion[store.meeting.discussion.length - 1] : null;

  // Destination/ETA: an active meeting/break override's own real
  // remainingMinutes if one is running, else the agent's next real
  // scheduled block — never a guess.
  let destinationLabel: string;
  let etaLabel: string;
  if (state.override) {
    const overrideBuilding = CAMPUS_BUILDINGS.find((b) => b.location === state.override!.location);
    destinationLabel = overrideBuilding?.label ?? state.override.location;
    etaLabel = `in ${state.override.remainingMinutes} sim-min (${state.override.reason})`;
  } else {
    const next = nextScheduleBlock(agentId, store.time.hour);
    const nextBuilding = CAMPUS_BUILDINGS.find((b) => b.location === next.location);
    destinationLabel = nextBuilding?.label ?? next.location;
    etaLabel = `at ${String(next.startHour).padStart(2, "0")}:00`;
  }
  const currentBuilding = CAMPUS_BUILDINGS.find((b) => b.location === state.location);
  const currentBlockTask = scheduleBlockForHour(agentId, store.time.hour).task;

  return (
    <Glass className="max-h-[70vh] overflow-y-auto p-3">
      <div className="mb-1 flex items-center justify-between">
        <span className="text-cmd-cyan">
          {profile.badge} {profile.name}
        </span>
        <span className="text-[9px] uppercase text-cmd-textDim">{profile.occupation}</span>
      </div>

      <div className="space-y-1 border-t border-cmd-border/50 pt-2">
        <DataRow label="Current Task" value={state.currentTask} />
        <DataRow label="Current Building" value={currentBuilding?.label ?? state.location} />
        <DataRow label="Destination" value={destinationLabel} />
        <DataRow label="ETA" value={etaLabel} />
        <DataRow label="Knowledge Level" value={level ? level.toUpperCase() : "—"} />
        <DataRow label="Mood" value={Math.round(state.mood)} />
        <DataRow label="Energy" value={Math.round(state.energy)} />
      </div>

      {activeResearch && (
        <div className="mt-2 border-t border-cmd-border/50 pt-2 text-[9px]">
          <span className="text-cmd-textDim">Researching </span>
          <span className="text-cmd-text">{activeResearch.title}</span>
          <span className="text-cmd-textDim"> — {Math.round(activeResearch.confidence)}% confidence</span>
        </div>
      )}

      {lastLine ? (
        <div className="mt-2 rounded-sm border border-cmd-border/50 bg-cmd-bg/40 p-1.5 text-[9px]">
          <span className="text-cmd-cyan">{AGENT_PROFILES[lastLine.speaker].name}:</span> <span className="text-cmd-textDim">&quot;{lastLine.line}&quot;</span>
        </div>
      ) : (
        <div className="mt-2 text-[9px] text-cmd-textDim">{state.override ? `Not currently in a meeting.` : `Not currently in a meeting — normally at ${currentBlockTask}.`}</div>
      )}
    </Glass>
  );
}
