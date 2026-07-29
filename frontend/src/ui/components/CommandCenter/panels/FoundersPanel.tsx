import { useMemo } from "react";
import { useGameStore } from "@/ui/hooks/useGameStore";
import { AGENT_PROFILES } from "@/game/systems/AgentProfiles";
import { FOUNDER_IDS, FOUNDER_PHILOSOPHY, FOUNDER_QUOTES, FOUNDER_SPECIALTIES, FOUNDER_TEACHING_STYLE } from "@/game/systems/founders";
import type { FounderId } from "@/types";
import { DataRow, EmptyState, Glass, StatusPill, TerminalLabel } from "../ui";

/**
 * v0.7 Feature 39 — the Original Founders. Keystone and Compass are the
 * spiritual originators of two already-real system clusters this
 * codebase built across earlier features (Discipline Chamber/Library of
 * Mistakes/Risk Engine, and Academy/Reasoning Lab/Reflection Chamber) —
 * see backend/app/founders.py's module docstring for why this is
 * deliberately NOT a second Socratic-teaching mechanic competing with
 * Sage's own already-shipped one (MentorPanel). Their philosophy/
 * specialties/quotes/teaching style below are real, hand-authored
 * content taken directly from the brief — never claimed to be freshly
 * generated. The Founder Log below is one real dialogue line per day,
 * alternating between them, reacting to whichever real event most
 * recently landed in that Founder's own domain. Legendary Status flips
 * permanently once Company Health reaches its real "excellent" tier —
 * the most comprehensive real milestone this codebase computes.
 */
export function FoundersPanel() {
  const { founderState, companyHealth } = useGameStore();
  const log = useMemo(() => [...founderState.log].reverse(), [founderState.log]);
  const councilSessions = useMemo(() => [...founderState.councilSessions].reverse(), [founderState.councilSessions]);

  return (
    <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
      <Glass className="p-3 lg:col-span-2">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Legendary Status</TerminalLabel>
          <StatusPill tone={founderState.retired ? "amber" : "cyan"}>{founderState.retired ? "RETIRED — HALL OF FOUNDERS" : "ACTIVE LEADERSHIP"}</StatusPill>
        </div>
        {founderState.retired ? (
          <p className="text-[9px] text-cmd-textDim">
            The Founders have formally retired into the Hall of Founders as of{" "}
            {founderState.retiredAt ? new Date(founderState.retiredAt).toLocaleDateString() : "an earlier session"} — Company Health reached its "excellent" tier. Their
            personalities, dialogue, and philosophy remain exactly the same; employees still visit them for mentorship.
          </p>
        ) : (
          <p className="text-[9px] text-cmd-textDim">
            The Founders retire into the Hall of Founders the first time Company Health reaches its "excellent" tier. Current tier: <span className="text-cmd-cyan">{companyHealth.tier.replace("_", " ")}</span>{" "}
            ({companyHealth.overall.toFixed(0)}/100).
          </p>
        )}
      </Glass>

      {FOUNDER_IDS.map((id) => (
        <FounderCard key={id} founderId={id} />
      ))}

      <Glass className="max-h-[24rem] overflow-y-auto p-3">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Founder Log</TerminalLabel>
          <StatusPill tone="cyan">{founderState.log.length}</StatusPill>
        </div>
        {log.length === 0 ? (
          <EmptyState>Neither Founder has had a real event in their domain to react to yet.</EmptyState>
        ) : (
          <div className="space-y-1.5">
            {log.map((entry) => (
              <div key={entry.id} className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-1.5 text-[9px]">
                <div className="mb-0.5 flex items-center gap-1.5 text-cmd-textDim">
                  <span>{AGENT_PROFILES[entry.founderId].badge}</span>
                  <span className="text-cmd-cyan">{AGENT_PROFILES[entry.founderId].name}</span>
                  <span>· Day {entry.simDay}</span>
                </div>
                <div className="text-cmd-text">{entry.line}</div>
              </div>
            ))}
          </div>
        )}
      </Glass>

      <Glass className="max-h-[24rem] overflow-y-auto p-3">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Founder Council</TerminalLabel>
          <StatusPill tone="cyan">{founderState.councilSessions.length}</StatusPill>
        </div>
        {councilSessions.length === 0 ? (
          <EmptyState>The Coach's first real monthly sit-down with the Founders hasn't happened yet.</EmptyState>
        ) : (
          <div className="space-y-1.5">
            {councilSessions.map((session) => (
              <div key={session.id} className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-1.5 text-[9px]">
                <div className="mb-1 text-cmd-textDim">Day {session.simDay}</div>
                <DataRow label="Coach" value={session.coachHighlight} />
                <DataRow label="Keystone" value={session.keystoneNote} />
                <DataRow label="Compass" value={session.compassNote} />
              </div>
            ))}
          </div>
        )}
      </Glass>
    </div>
  );
}

function FounderCard({ founderId }: { founderId: FounderId }) {
  const profile = AGENT_PROFILES[founderId];
  return (
    <Glass className="p-3">
      <div className="mb-1 flex items-center gap-2">
        <span className="text-lg">{profile.badge}</span>
        <div>
          <div className="text-cmd-cyan">{profile.name}</div>
          <div className="text-[9px] uppercase tracking-wide text-cmd-textDim">{profile.occupation}</div>
        </div>
      </div>
      <p className="mb-2 border-t border-cmd-border/50 pt-2 text-[9px] italic text-cmd-text">&quot;{FOUNDER_PHILOSOPHY[founderId]}&quot;</p>
      <div className="mb-2 space-y-1">
        <DataRow label="Personality" value={profile.personality} />
      </div>
      <div className="mb-2">
        <div className="mb-1 text-[9px] uppercase tracking-wide text-cmd-textDim">Specialties</div>
        <div className="flex flex-wrap gap-1">
          {FOUNDER_SPECIALTIES[founderId].map((s) => (
            <span key={s} className="rounded-sm border border-cmd-border/60 px-1.5 py-0.5 text-[8px] text-cmd-textDim">
              {s}
            </span>
          ))}
        </div>
      </div>
      <div className="mb-2">
        <div className="mb-1 text-[9px] uppercase tracking-wide text-cmd-textDim">Common Quotes</div>
        <div className="space-y-0.5 text-[9px] text-cmd-text">
          {FOUNDER_QUOTES[founderId].map((q) => (
            <div key={q}>&quot;{q}&quot;</div>
          ))}
        </div>
      </div>
      <div>
        <div className="mb-1 text-[9px] uppercase tracking-wide text-cmd-textDim">Teaching Style</div>
        <p className="text-[9px] text-cmd-textDim">{FOUNDER_TEACHING_STYLE[founderId]}</p>
      </div>
    </Glass>
  );
}
