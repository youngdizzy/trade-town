import { useEffect, useMemo, useRef, useState } from "react";
import { useGameStore } from "@/ui/hooks/useGameStore";
import { useCloseOnEscape } from "@/ui/hooks/useCloseOnEscape";
import { EventBus } from "@/game/systems/EventBus";
import { GameManager } from "@/game/systems/GameManager";
import { SettingsManager } from "@/game/systems/SettingsManager";
import { SaveManager } from "@/game/systems/SaveManager";
import { AGENT_PROFILES } from "@/game/systems/AgentProfiles";
import { TAB_SECTION } from "./CommandCenter/lib/navigation";
import { AGENT_IDS, type OperatingMode } from "@/types";

/**
 * Design Bible Chapter 67 (TTOS) Part 3 — the Command Palette
 * (Cmd/Ctrl+K), doubling as Universal Search. Real commands and real
 * search results only, per the brief's own constraint — every command
 * entry maps to an already-real EventBus event or manager call this
 * codebase already uses elsewhere (BottomToolbar.tsx's own Save/Load/
 * Memory/Coach/Dashboard/Settings/Pause buttons, QuickActionDock.tsx's
 * own Automation Mode cycle and tab quick-jumps, EmergencyStopControl
 * .tsx's own confirm-dialog trigger), and every search result reads a
 * real gameStore field. Two of the brief's own example commands are
 * deliberately absent: "Open Charles Schwab" (no live broker
 * integration exists anywhere — see app/broker.py's own "Completely
 * simulated" docstring) and "Swing/Day Trading Mode" (no such mode
 * exists under any name). The 34 "Go to X" tab commands are derived
 * from `navigation.ts`'s own `TAB_SECTION` map rather than a fourth
 * hand-maintained tab list.
 *
 * Universal Search is built into this same overlay rather than as a
 * second Ctrl+K-shaped surface — both need the identical type/filter/
 * arrow-nav/enter-to-act shape (the same "index of what we already
 * have, never a new source of truth" pattern `CompanyMemory.tsx`'s own
 * client-side filter already established, no new backend endpoint),
 * so building two competing overlays for the same interaction pattern
 * would have been the duplication this codebase's own convention warns
 * against. Real, already-loaded entities are searchable: the 14 real
 * employees (jumps to AGENTS), closed trades from `paperPortfolio
 * .tradeHistory` (jumps to REPLAY, where trade history is actually
 * browsable), research items (jumps to RESEARCH), and Company Memory
 * records (opens the real Company Memory overlay, where its own
 * existing search can narrow further — this palette only gets the CEO
 * to the right surface, it doesn't reimplement CompanyMemory's own
 * search a second time). The rendered list is capped at 50 matches
 * (`MAX_RESULTS`) so a broad query against a mature save's full trade/
 * research/memory history stays scrollable — the underlying search
 * still runs across every real record, only the render is capped.
 */
interface Command {
  id: string;
  label: string;
  hint: string;
  run: () => void;
}

const ALL_TABS = Object.keys(TAB_SECTION) as (keyof typeof TAB_SECTION)[];
const MAX_RESULTS = 50;

export function CommandPalette() {
  const { currentScene, paused, settings, emergencyStop, agents, paperPortfolio, research, memory } = useGameStore();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const inGame = currentScene !== "MainMenuScene";

  const close = () => setOpen(false);
  useCloseOnEscape(open, close);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (!inGame) return;
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((o) => !o);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [inGame]);

  useEffect(() => {
    if (open) {
      setQuery("");
      setSelected(0);
      // Focus after the input actually mounts.
      setTimeout(() => inputRef.current?.focus(), 0);
    }
  }, [open]);

  const commands = useMemo<Command[]>(() => {
    // Real BottomToolbar.tsx actions.
    const list: Command[] = [
      { id: "save", label: "Save", hint: "Game", run: () => void SaveManager.save() },
      { id: "load", label: "Load", hint: "Game", run: () => void SaveManager.load() },
      { id: "memory", label: "Open Company Memory", hint: "Overlay", run: () => EventBus.emit("ui:companyMemory", { open: true }) },
      { id: "coach", label: "Open Coach Dashboard", hint: "Overlay", run: () => EventBus.emit("ui:coachDashboard", { open: true }) },
      { id: "dashboard", label: "Open Brain Room Dashboard", hint: "Overlay", run: () => EventBus.emit("ui:brainRoomHud", { open: true }) },
      { id: "settings", label: "Open Settings", hint: "Overlay", run: () => EventBus.emit("ui:settings", { open: true }) },
      // Design Bible Chapter 67 (TTOS) Part 3 — the Executive Alert Center.
      { id: "alerts", label: "Open Alert Center", hint: "Overlay", run: () => EventBus.emit("ui:alertCenter", { open: true }) },
      // Design Bible Chapter 67 (TTOS) Part 3 — Navigation polish. Newspaper
      // and Campus Map were the only two of this app's 6 real standalone
      // overlays with no path into the CEO's own central navigation surface
      // (Newspaper was diegetic-only — walk to the stand in the Lobby;
      // Campus Map lived only in QuickView/PauseMenu/FullCommandCenter's
      // own buttons) — added here for parity with Memory/Coach/Dashboard/
      // Alerts above, not a new overlay.
      { id: "newspaper", label: "Open Newspaper", hint: "Overlay", run: () => EventBus.emit("ui:newspaper", { open: true }) },
      { id: "campus", label: "Open Campus Map", hint: "Overlay", run: () => EventBus.emit("ui:campusMap", { open: true }) },
    ];
    list.push({
      id: "pause",
      label: paused ? "Resume Simulation" : "Pause Simulation",
      hint: "Sim clock",
      run: () => GameManager.getInstance()?.togglePause(),
    });
    list.push({
      id: "workmode",
      label: settings.workMode === "work" ? "Switch to Rest Mode" : "Switch to Work Mode",
      hint: "Work Mode",
      run: () => SettingsManager.update({ workMode: settings.workMode === "work" ? "rest" : "work" }),
    });
    // Operating Mode — all three always offered, matching CompanyPanel's own three-button layout.
    (["learning", "assisted", "executive"] as OperatingMode[]).forEach((mode) => {
      if (mode === settings.operatingMode) return;
      list.push({
        id: `mode-${mode}`,
        label: `Set Automation Mode: ${mode.toUpperCase()}`,
        hint: "Operating Mode",
        run: () => SettingsManager.update({ operatingMode: mode }),
      });
    });
    // Emergency Stop — opens the real confirm dialog, never bypasses it.
    list.push({
      id: "emergency",
      label: emergencyStop.active ? "Resume Trading (Emergency Stop)" : "Activate Emergency Stop",
      hint: "Safety",
      run: () => EventBus.emit("ui:emergencyStopConfirm", { pending: emergencyStop.active ? "resume" : "activate" }),
    });
    // 34 real Command Center tabs.
    for (const tab of ALL_TABS) {
      list.push({
        id: `tab-${tab}`,
        label: `Go to ${tab}`,
        hint: TAB_SECTION[tab],
        run: () => EventBus.emit("ui:commandCenterJump", { tab }),
      });
    }
    // Universal Search — real employees.
    if (agents) {
      for (const id of AGENT_IDS) {
        const profile = AGENT_PROFILES[id];
        list.push({
          id: `agent-${id}`,
          label: `${profile.name} — ${profile.occupation}`,
          hint: "Employee",
          run: () => EventBus.emit("ui:commandCenterJump", { tab: "AGENTS" }),
        });
      }
    }
    // Universal Search — real closed trades.
    for (const trade of paperPortfolio.tradeHistory) {
      list.push({
        id: `trade-${trade.id}`,
        label: `${trade.symbol} ${trade.side.toUpperCase()} — ${trade.pnlPct >= 0 ? "+" : ""}${trade.pnlPct.toFixed(1)}%`,
        hint: "Trade",
        run: () => EventBus.emit("ui:commandCenterJump", { tab: "REPLAY" }),
      });
    }
    // Universal Search — real research items.
    for (const item of research) {
      list.push({
        id: `research-${item.id}`,
        label: `${item.title}${item.symbol ? ` (${item.symbol})` : ""}`,
        hint: "Research",
        run: () => EventBus.emit("ui:commandCenterJump", { tab: "RESEARCH" }),
      });
    }
    // Universal Search — real Company Memory records. Opens the real
    // overlay rather than duplicating its own search a second time.
    for (const record of memory) {
      list.push({
        id: `memory-${record.id}`,
        label: record.title,
        hint: "Company Memory",
        run: () => EventBus.emit("ui:companyMemory", { open: true }),
      });
    }
    return list;
  }, [paused, settings.workMode, settings.operatingMode, emergencyStop.active, agents, paperPortfolio.tradeHistory, research, memory]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return commands;
    return commands.filter((c) => c.label.toLowerCase().includes(q) || c.hint.toLowerCase().includes(q));
  }, [commands, query]);

  // The underlying search runs across every real record above; only the
  // render is capped, so a broad query against a mature save's full
  // trade/research/memory history stays scrollable.
  const visible = filtered.slice(0, MAX_RESULTS);

  const execute = (cmd: Command | undefined) => {
    if (!cmd) return;
    cmd.run();
    close();
  };

  if (!open || !inGame) return null;

  return (
    <div className="pointer-events-auto absolute inset-0 z-[70] flex items-start justify-center bg-black/60 pt-[12vh]" onClick={close}>
      <div
        data-testid="command-palette"
        className="flex max-h-[70vh] w-full max-w-lg flex-col overflow-hidden rounded-md border border-cmd-cyan/30 bg-cmd-bg font-cmdmono text-[11px] text-cmd-text shadow-cmd-cyan"
        onClick={(e) => e.stopPropagation()}
      >
        <input
          ref={inputRef}
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setSelected(0);
          }}
          onKeyDown={(e) => {
            if (e.key === "ArrowDown") {
              e.preventDefault();
              setSelected((i) => Math.min(i + 1, visible.length - 1));
            } else if (e.key === "ArrowUp") {
              e.preventDefault();
              setSelected((i) => Math.max(i - 1, 0));
            } else if (e.key === "Enter") {
              e.preventDefault();
              execute(visible[selected]);
            }
          }}
          placeholder="Search or type a command…"
          className="border-b border-cmd-border bg-transparent px-3 py-2.5 text-cmd-text outline-none placeholder:text-cmd-textDim"
        />
        <div className="overflow-y-auto">
          {visible.length === 0 ? (
            <div className="px-3 py-3 text-cmd-textDim">No matching command or result.</div>
          ) : (
            visible.map((cmd, i) => (
              <button
                key={cmd.id}
                type="button"
                onClick={() => execute(cmd)}
                onMouseEnter={() => setSelected(i)}
                className={`flex w-full items-center justify-between px-3 py-1.5 text-left ${i === selected ? "bg-cmd-cyan/10 text-cmd-cyan" : "text-cmd-text"}`}
              >
                <span>{cmd.label}</span>
                <span className="text-[9px] uppercase tracking-wide text-cmd-textDim">{cmd.hint}</span>
              </button>
            ))
          )}
          {filtered.length > MAX_RESULTS && (
            <div className="px-3 py-1.5 text-cmd-textDim">+{filtered.length - MAX_RESULTS} more — refine your search</div>
          )}
        </div>
      </div>
    </div>
  );
}
