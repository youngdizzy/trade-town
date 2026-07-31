import { useState } from "react";
import { useGameStore } from "@/ui/hooks/useGameStore";
import { AGENT_PROFILES } from "@/game/systems/AgentProfiles";
import { SettingsManager } from "@/game/systems/SettingsManager";
import { NexusManager } from "@/game/systems/NexusManager";
import { api } from "@/net/api";
import type { AgentId, CertificationRecord, FoundationalMentorId, FoundationalMentorLesson, FoundationalResourceType } from "@/types";
import { ACADEMY_STUDENT_AGENT_IDS, certificationStatusTone, computeAcademyDashboard, type AcademyStudentSummary } from "../lib/derive";
import { DataRow, EmptyState, Glass, StatusPill, TerminalLabel } from "../ui";

const RESOURCE_TYPES: FoundationalResourceType[] = ["video", "book", "article", "pdf", "note"];

const STATUS_TONE: Record<AcademyStudentSummary["graduationStatus"], "neutral" | "cyan" | "green" | "amber"> = {
  in_progress: "cyan",
  pending_approval: "amber",
  graduated: "green",
};

function studentToneFor(status: AcademyStudentSummary["graduationStatus"]): "neutral" | "cyan" | "green" | "amber" {
  return STATUS_TONE[status];
}

/**
 * The Foundational Mentor Program / Professional Academy (v0.7 Feature
 * 49, Phase 3, revised) — see backend/app/foundational_mentors.py's
 * module docstring for the full content-attribution boundary and the
 * "employees are the students" redesign. This is now a MANAGEMENT
 * DASHBOARD: real employee agents auto-progress every tick (no CEO
 * click required — see computeAcademyDashboard in lib/derive.ts, which
 * derives the whole dashboard client-side from data already broadcast).
 * The CEO reviews progress, approves graduations, and runs company-wide
 * controls. CEO Learning Mode (off by default) optionally exposes a
 * separate personal lesson browser below, entirely decoupled from real
 * employee progress.
 */
type CertActionType = "revoke" | "downgrade" | "promote" | "reset" | "details";

export function MentorLibraryPanel() {
  const { foundationalMentorState, agentKnowledge, settings, academyState } = useGameStore();
  const [selectedAgentId, setSelectedAgentId] = useState<AgentId | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [certAction, setCertAction] = useState<{ type: CertActionType; record: CertificationRecord } | null>(null);
  const [certBusy, setCertBusy] = useState(false);
  const [certError, setCertError] = useState<string | null>(null);

  const dashboard = computeAcademyDashboard(foundationalMentorState, agentKnowledge);
  const activeMentor = foundationalMentorState.mentors.find((m) => m.id === dashboard.activeMentorId) ?? null;
  const learningMode = settings.ceoAcademyLearningMode;

  const runControl = async (action: () => Promise<{ foundationalMentorState: typeof foundationalMentorState }>) => {
    setBusy(true);
    setError(null);
    try {
      const res = await action();
      NexusManager.setFoundationalMentorState(res.foundationalMentorState);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  const approve = async (agentId: AgentId, mentorId: FoundationalMentorId) => {
    setBusy(true);
    setError(null);
    try {
      const res = await api.approveAcademyGraduation(agentId, mentorId);
      NexusManager.setFoundationalMentorState(res.foundationalMentorState);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  // Certification Management — full CEO controls over an earned
  // certification (Current Certifications, below). One shared runner so
  // every dialog (Revoke/Downgrade/Promote/Reset Progress) closes itself
  // and refreshes real state the same way on success.
  const runCertAction = async (action: () => Promise<{ foundationalMentorState: typeof foundationalMentorState }>) => {
    setCertBusy(true);
    setCertError(null);
    try {
      const res = await action();
      NexusManager.setFoundationalMentorState(res.foundationalMentorState);
      setCertAction(null);
    } catch (err) {
      setCertError(err instanceof Error ? err.message : String(err));
    } finally {
      setCertBusy(false);
    }
  };
  const doRevokeCertification = (record: CertificationRecord, reason: string) => runCertAction(() => api.revokeAcademyCertification(record.agentId, record.mentorId, reason));
  const doDowngradeCertification = (record: CertificationRecord, reason: string) => runCertAction(() => api.downgradeAcademyCertification(record.agentId, record.mentorId, reason));
  const doPromoteCertification = (record: CertificationRecord, reason: string | null) => runCertAction(() => api.promoteAcademyCertification(record.agentId, record.mentorId, reason));
  const doResetCertificationProgress = (record: CertificationRecord) => runCertAction(() => api.resetAcademyCertificationProgress(record.agentId, record.mentorId));

  if (foundationalMentorState.mentors.length === 0) return <EmptyState>Loading Academy…</EmptyState>;

  return (
    <div className="space-y-3">
      <Glass className="p-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <TerminalLabel>Professional Academy</TerminalLabel>
            <StatusPill tone={activeMentor?.status === "paused" ? "amber" : "cyan"}>{dashboard.activeMentorLabel ?? "No active track"}</StatusPill>
          </div>
          <button
            type="button"
            onClick={() => SettingsManager.update({ ceoAcademyLearningMode: !learningMode })}
            className={`rounded-sm border px-2 py-1 text-[9px] uppercase tracking-wide ${
              learningMode ? "border-cmd-cyan/50 bg-cmd-cyan/10 text-cmd-cyan" : "border-cmd-border text-cmd-textDim hover:text-cmd-text"
            }`}
            title="Employees always auto-progress regardless of this setting — it only lets the CEO also personally take lessons."
          >
            CEO Learning Mode: {learningMode ? "ON" : "OFF"}
          </button>
        </div>
        <div className="mt-1 text-[9px] text-cmd-textDim">
          Employees complete Academy training automatically — the CEO manages, reviews, and approves. See backend/app/foundational_mentors.py for the full design.
        </div>
        {error && <div className="mt-2 text-cmd-red">{error}</div>}
        {activeMentor && (
          <div className="mt-2 flex flex-wrap gap-2">
            {activeMentor.status === "active" && (
              <button type="button" disabled={busy} onClick={() => void runControl(() => api.pauseAcademyTraining())} className="rounded-sm border border-cmd-border px-2 py-1 text-[9px] uppercase text-cmd-textDim hover:border-cmd-amber/50 hover:text-cmd-amber disabled:opacity-40">
                Pause Training
              </button>
            )}
            {activeMentor.status === "paused" && (
              <button type="button" disabled={busy} onClick={() => void runControl(() => api.resumeAcademyTraining())} className="rounded-sm border border-cmd-border px-2 py-1 text-[9px] uppercase text-cmd-textDim hover:border-cmd-cyan/50 hover:text-cmd-cyan disabled:opacity-40">
                Resume Training
              </button>
            )}
            {(activeMentor.status === "active" || activeMentor.status === "paused") && (
              <button type="button" disabled={busy} onClick={() => void runControl(() => api.skipAcademyToNextMentor())} className="rounded-sm border border-cmd-border px-2 py-1 text-[9px] uppercase text-cmd-textDim hover:border-cmd-red/50 hover:text-cmd-red disabled:opacity-40">
                Skip to Next Track
              </button>
            )}
            {activeMentor.status === "graduated" && (
              <button type="button" disabled={busy} onClick={() => void runControl(() => api.repeatAcademyMentor(activeMentor.id))} className="rounded-sm border border-cmd-border px-2 py-1 text-[9px] uppercase text-cmd-textDim hover:border-cmd-cyan/50 hover:text-cmd-cyan disabled:opacity-40">
                Repeat Track (Whole Team)
              </button>
            )}
          </div>
        )}
      </Glass>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Glass className="p-3">
          <TerminalLabel>Academy Statistics</TerminalLabel>
          <DataRow label="Avg quiz score" value={`${dashboard.avgQuizScorePct.toFixed(0)}%`} />
          <DataRow label="Avg knowledge points" value={dashboard.avgKnowledgeScore.toFixed(1)} />
          <DataRow label="Students" value={ACADEMY_STUDENT_AGENT_IDS.length} />
          <DataRow label="Certifications earned" value={foundationalMentorState.certifications.length} />
        </Glass>

        <Glass className="p-3">
          <TerminalLabel>Company Knowledge Growth</TerminalLabel>
          <DataRow label="Academy level" value={`${academyState.level} — ${academyState.levelLabel}`} />
          <DataRow label="Total knowledge points" value={academyState.totalPoints.toFixed(0)} />
          <DataRow label="Projects completed" value={academyState.completedProjectCount} />
          <div className="mt-1 text-[9px] text-cmd-textDim">Real, current totals from the AI Academy (KNOWLEDGE tab) — not a fabricated trend line.</div>
        </Glass>

        <StudentListCard title="Currently Studying" students={dashboard.currentlyStudying} onSelect={setSelectedAgentId} emptyText="No one studying right now." />
        <StudentListCard title="Top Students" students={dashboard.topStudents} onSelect={setSelectedAgentId} emptyText="No progress yet." />
        <StudentListCard title="Needing Help" students={dashboard.needingHelp} onSelect={setSelectedAgentId} emptyText="No one is struggling." />
      </div>

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
        <Glass className="p-3">
          <TerminalLabel>Graduation Queue</TerminalLabel>
          {dashboard.graduationQueue.length === 0 ? (
            <EmptyState>No one is awaiting graduation approval.</EmptyState>
          ) : (
            <div className="space-y-1.5">
              {dashboard.graduationQueue.map((s) => (
                <div key={s.agentId} className="flex items-center justify-between gap-2 border-b border-cmd-border/60 py-1 last:border-0">
                  <button type="button" onClick={() => setSelectedAgentId(s.agentId)} className="text-cmd-text hover:text-cmd-cyan">
                    {AGENT_PROFILES[s.agentId].name}
                  </button>
                  <button type="button" disabled={busy} onClick={() => void approve(s.agentId, s.mentorId)} className="rounded-sm border border-cmd-green/50 px-2 py-1 text-[9px] uppercase tracking-wide text-cmd-green hover:bg-cmd-green/10 disabled:opacity-40">
                    Approve Graduation
                  </button>
                </div>
              ))}
            </div>
          )}
        </Glass>

        <Glass className="p-3">
          <TerminalLabel>Coach Recommendations</TerminalLabel>
          {dashboard.recommendations.length === 0 ? (
            <EmptyState>No recommendations right now.</EmptyState>
          ) : (
            <div className="space-y-1.5">
              {dashboard.recommendations.map((r) => (
                <div key={r.agentId} className="border-b border-cmd-border/60 py-1 last:border-0">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-cmd-text">{AGENT_PROFILES[r.agentId].name}</span>
                    <StatusPill tone={r.recommendation === "one_on_one_coaching" ? "amber" : "neutral"}>{r.recommendation === "one_on_one_coaching" ? "ONE-ON-ONE COACHING" : "REPEAT LESSON"}</StatusPill>
                  </div>
                  <div className="text-[9px] text-cmd-textDim">{r.reason}</div>
                </div>
              ))}
            </div>
          )}
        </Glass>
      </div>

      {dashboard.upcomingGraduations.length > 0 && (
        <Glass className="p-3">
          <TerminalLabel>Upcoming Graduations</TerminalLabel>
          <div className="flex flex-wrap gap-2">
            {dashboard.upcomingGraduations.map((s) => (
              <button key={s.agentId} type="button" onClick={() => setSelectedAgentId(s.agentId)} className="rounded-sm border border-cmd-border px-2 py-1 text-[9px] text-cmd-textDim hover:border-cmd-cyan/50 hover:text-cmd-cyan">
                {AGENT_PROFILES[s.agentId].name} — 1 lesson remaining
              </button>
            ))}
          </div>
        </Glass>
      )}

      <CurrentCertifications certifications={foundationalMentorState.certifications} onSelectAction={(type, record) => setCertAction({ type, record })} />

      <Glass className="p-3">
        <TerminalLabel>Mentor Roadmap</TerminalLabel>
        <div className="mt-2 flex flex-wrap gap-2">
          {foundationalMentorState.mentors.map((m) => (
            <div key={m.id} className={`rounded-sm border px-2 py-1 text-[9px] ${m.id === dashboard.activeMentorId ? "border-cmd-cyan/50 bg-cmd-cyan/10 text-cmd-cyan" : "border-cmd-border text-cmd-textDim"}`}>
              {m.trackLabel} — {m.status.toUpperCase()}
            </div>
          ))}
        </div>
      </Glass>

      {selectedAgentId && <EmployeeAcademyReport agentId={selectedAgentId} mentorId={dashboard.activeMentorId} onClose={() => setSelectedAgentId(null)} onApprove={approve} busy={busy} />}

      {certAction && (
        <CertificationActionDialog
          type={certAction.type}
          record={certAction.record}
          busy={certBusy}
          error={certError}
          onClose={() => {
            setCertAction(null);
            setCertError(null);
          }}
          onRevoke={(reason) => void doRevokeCertification(certAction.record, reason)}
          onDowngrade={(reason) => void doDowngradeCertification(certAction.record, reason)}
          onPromote={(reason) => void doPromoteCertification(certAction.record, reason)}
          onResetProgress={() => void doResetCertificationProgress(certAction.record)}
        />
      )}

      {learningMode && <CeoPersonalLearning />}
    </div>
  );
}

/**
 * Certification Management — full CEO controls (a quality-of-life fix).
 * Reads `foundationalMentorState.certifications` directly — the real,
 * permanent, independent registry (see backend/app/foundational_mentors.py's
 * "Certification Management" section) — rather than a client-side
 * re-derivation from graduation status, so every certification is
 * reachable here regardless of which mentor track is currently active
 * (the original bug: a certification on an already-completed track had
 * no reachable Revoke button at all).
 */
function CurrentCertifications({ certifications, onSelectAction }: { certifications: CertificationRecord[]; onSelectAction: (type: CertActionType, record: CertificationRecord) => void }) {
  const current = certifications.filter((c) => c.status === "active" || c.status === "suspended");
  const revoked = certifications.filter((c) => c.status === "revoked");

  return (
    <>
      <Glass className="p-3">
        <TerminalLabel>Current Certifications</TerminalLabel>
        {current.length === 0 ? (
          <EmptyState>No certifications earned yet.</EmptyState>
        ) : (
          <div className="space-y-1.5">
            {current.map((c) => (
              <div key={c.id} className="flex flex-wrap items-center justify-between gap-2 border-b border-cmd-border/60 py-1.5 last:border-0">
                <div className="flex items-center gap-2">
                  <span className="text-cmd-text">{AGENT_PROFILES[c.agentId].name}</span>
                  <span className="text-[9px] text-cmd-textDim">{c.mentorName}</span>
                  <StatusPill tone={certificationStatusTone(c.status)}>{c.status.toUpperCase()}</StatusPill>
                </div>
                <div className="flex flex-wrap gap-1">
                  <button type="button" onClick={() => onSelectAction("details", c)} className="rounded-sm border border-cmd-border px-1.5 py-0.5 text-[9px] uppercase tracking-wide text-cmd-textDim hover:border-cmd-cyan/50 hover:text-cmd-cyan">
                    View / History
                  </button>
                  {c.status === "active" ? (
                    <button type="button" onClick={() => onSelectAction("downgrade", c)} className="rounded-sm border border-cmd-amber/40 px-1.5 py-0.5 text-[9px] uppercase tracking-wide text-cmd-amber hover:bg-cmd-amber/10">
                      Downgrade
                    </button>
                  ) : (
                    <button type="button" onClick={() => onSelectAction("promote", c)} className="rounded-sm border border-cmd-green/40 px-1.5 py-0.5 text-[9px] uppercase tracking-wide text-cmd-green hover:bg-cmd-green/10">
                      Promote
                    </button>
                  )}
                  <button type="button" onClick={() => onSelectAction("revoke", c)} className="rounded-sm border border-cmd-red/40 px-1.5 py-0.5 text-[9px] uppercase tracking-wide text-cmd-red hover:bg-cmd-red/10">
                    Revoke
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </Glass>

      {revoked.length > 0 && (
        <Glass className="p-3">
          <TerminalLabel>Revoked Certifications — awaiting re-earn</TerminalLabel>
          <div className="space-y-1.5">
            {revoked.map((c) => (
              <div key={c.id} className="flex flex-wrap items-center justify-between gap-2 border-b border-cmd-border/60 py-1.5 last:border-0">
                <div className="flex items-center gap-2">
                  <span className="text-cmd-text">{AGENT_PROFILES[c.agentId].name}</span>
                  <span className="text-[9px] text-cmd-textDim">{c.mentorName}</span>
                  <StatusPill tone={certificationStatusTone(c.status)}>{c.status.toUpperCase()}</StatusPill>
                </div>
                <div className="flex flex-wrap gap-1">
                  <button type="button" onClick={() => onSelectAction("details", c)} className="rounded-sm border border-cmd-border px-1.5 py-0.5 text-[9px] uppercase tracking-wide text-cmd-textDim hover:border-cmd-cyan/50 hover:text-cmd-cyan">
                    View / History
                  </button>
                  <button type="button" onClick={() => onSelectAction("reset", c)} className="rounded-sm border border-cmd-border px-1.5 py-0.5 text-[9px] uppercase tracking-wide text-cmd-textDim hover:border-cmd-amber/50 hover:text-cmd-amber">
                    Reset Progress
                  </button>
                </div>
              </div>
            ))}
          </div>
        </Glass>
      )}
    </>
  );
}

/**
 * One shared modal for every Certification Management action — the
 * Revoke copy matches the brief's requested wording exactly. Downgrade/
 * Promote/Reset Progress reuse the same modal shell for a consistent
 * confirm-before-you-act pattern, with lighter copy matching their own
 * lower severity.
 */
function CertificationActionDialog({
  type,
  record,
  busy,
  error,
  onClose,
  onRevoke,
  onDowngrade,
  onPromote,
  onResetProgress,
}: {
  type: CertActionType;
  record: CertificationRecord;
  busy: boolean;
  error: string | null;
  onClose: () => void;
  onRevoke: (reason: string) => void;
  onDowngrade: (reason: string) => void;
  onPromote: (reason: string | null) => void;
  onResetProgress: () => void;
}) {
  const [reason, setReason] = useState("");
  const agentName = AGENT_PROFILES[record.agentId].name;

  if (type === "details") {
    return (
      <div className="fixed inset-0 z-[70] flex items-center justify-center bg-cmd-bg/80 p-4 backdrop-blur-sm" onClick={onClose}>
        <div onClick={(e) => e.stopPropagation()} className="w-full max-w-lg">
          <Glass className="p-4">
            <div className="mb-2 flex items-center justify-between">
              <TerminalLabel>
                {agentName} — {record.mentorName} Certification
              </TerminalLabel>
              <button type="button" onClick={onClose} className="text-cmd-textDim hover:text-cmd-red">
                ✕
              </button>
            </div>
            <div className="mb-2 flex items-center gap-2">
              <StatusPill tone={certificationStatusTone(record.status)}>{record.status.toUpperCase()}</StatusPill>
              <span className="text-[9px] text-cmd-textDim">Last updated sim day {record.updatedSimDay}</span>
            </div>
            <div className="mt-2 border-t border-cmd-border/60 pt-2">
              <TerminalLabel>Certification History — permanent, never edited or deleted</TerminalLabel>
              <div className="mt-1 space-y-1">
                {record.history.map((h) => (
                  <div key={h.id} className="border-b border-cmd-border/40 py-1 text-[9px] last:border-0">
                    <div className="flex items-center justify-between">
                      <span className="uppercase tracking-wide text-cmd-text">{h.action.replace(/_/g, " ")}</span>
                      <span className="text-cmd-textDim">Day {h.simDay}</span>
                    </div>
                    {h.reason && <div className="mt-0.5 text-cmd-textDim">Reason: {h.reason}</div>}
                  </div>
                ))}
              </div>
            </div>
          </Glass>
        </div>
      </div>
    );
  }

  if (type === "reset") {
    return (
      <div className="fixed inset-0 z-[70] flex items-center justify-center bg-cmd-bg/80 p-4 backdrop-blur-sm" onClick={onClose}>
        <div onClick={(e) => e.stopPropagation()} className="w-full max-w-md">
          <Glass className="p-4">
            <TerminalLabel>Reset {agentName}'s {record.mentorName} re-training progress?</TerminalLabel>
            <p className="mt-2 text-[9px] text-cmd-textDim">This wipes any renewed lesson/quiz progress made since the revoke, restarting the repeat attempt from lesson one. The revoked certification's own history is preserved.</p>
            {error && <div className="mt-2 text-cmd-red">{error}</div>}
            <div className="mt-3 flex justify-end gap-2">
              <button type="button" onClick={onClose} className="rounded-sm border border-cmd-border px-3 py-1 text-[10px] uppercase tracking-wider text-cmd-textDim hover:text-cmd-text">
                Cancel
              </button>
              <button type="button" disabled={busy} onClick={onResetProgress} className="rounded-sm border border-cmd-amber/50 px-3 py-1 text-[10px] uppercase tracking-wider text-cmd-amber hover:bg-cmd-amber/10 disabled:opacity-40">
                Reset Progress
              </button>
            </div>
          </Glass>
        </div>
      </div>
    );
  }

  if (type === "promote") {
    return (
      <div className="fixed inset-0 z-[70] flex items-center justify-center bg-cmd-bg/80 p-4 backdrop-blur-sm" onClick={onClose}>
        <div onClick={(e) => e.stopPropagation()} className="w-full max-w-md">
          <Glass className="p-4">
            <TerminalLabel>Reinstate {agentName}'s {record.mentorName} Certification?</TerminalLabel>
            <p className="mt-2 text-[9px] text-cmd-textDim">This returns the certification to Active standing. Only offered while suspended.</p>
            <label className="mt-2 block text-[9px] uppercase tracking-wide text-cmd-textDim">Note (optional)</label>
            <textarea value={reason} onChange={(e) => setReason(e.target.value)} rows={2} className="mt-1 w-full rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1 text-[10px] text-cmd-text outline-none focus:border-cmd-cyan/50" placeholder="Retrained and reviewed." />
            {error && <div className="mt-2 text-cmd-red">{error}</div>}
            <div className="mt-3 flex justify-end gap-2">
              <button type="button" onClick={onClose} className="rounded-sm border border-cmd-border px-3 py-1 text-[10px] uppercase tracking-wider text-cmd-textDim hover:text-cmd-text">
                Cancel
              </button>
              <button type="button" disabled={busy} onClick={() => onPromote(reason.trim() || null)} className="rounded-sm border border-cmd-green/50 px-3 py-1 text-[10px] uppercase tracking-wider text-cmd-green hover:bg-cmd-green/10 disabled:opacity-40">
                Promote Certification
              </button>
            </div>
          </Glass>
        </div>
      </div>
    );
  }

  // "downgrade" and "revoke" both require a real, non-empty reason.
  const isRevoke = type === "revoke";
  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center bg-cmd-bg/80 p-4 backdrop-blur-sm" onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()} className="w-full max-w-md">
        <Glass className="p-4">
          <TerminalLabel>
            Are you sure you want to {isRevoke ? "revoke" : "downgrade"} {agentName}'s {record.mentorName} Certification?
          </TerminalLabel>
          <p className="mt-2 text-[9px] text-cmd-amber">
            {isRevoke
              ? "This will remove the active certification but preserve all historical records."
              : "This suspends the certification (reversible via Promote) but does not touch the employee's underlying progress."}
          </p>
          <label className="mt-2 block text-[9px] uppercase tracking-wide text-cmd-textDim">Reason (required)</label>
          <textarea value={reason} onChange={(e) => setReason(e.target.value)} rows={2} className="mt-1 w-full rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1 text-[10px] text-cmd-text outline-none focus:border-cmd-cyan/50" placeholder="Manual reset for additional training." />
          {error && <div className="mt-2 text-cmd-red">{error}</div>}
          <div className="mt-3 flex justify-end gap-2">
            <button type="button" onClick={onClose} className="rounded-sm border border-cmd-border px-3 py-1 text-[10px] uppercase tracking-wider text-cmd-textDim hover:text-cmd-text">
              Cancel
            </button>
            <button
              type="button"
              disabled={busy || !reason.trim()}
              onClick={() => (isRevoke ? onRevoke(reason.trim()) : onDowngrade(reason.trim()))}
              className="rounded-sm border border-cmd-red/50 px-3 py-1 text-[10px] uppercase tracking-wider text-cmd-red hover:bg-cmd-red/10 disabled:opacity-40"
            >
              {isRevoke ? "Revoke Certification" : "Downgrade Certification"}
            </button>
          </div>
        </Glass>
      </div>
    </div>
  );
}

function StudentListCard({ title, students, onSelect, emptyText }: { title: string; students: AcademyStudentSummary[]; onSelect: (id: AgentId) => void; emptyText: string }) {
  return (
    <Glass className="p-3">
      <TerminalLabel>{title}</TerminalLabel>
      {students.length === 0 ? (
        <EmptyState>{emptyText}</EmptyState>
      ) : (
        <div className="space-y-1">
          {students.map((s) => (
            <button key={s.agentId} type="button" onClick={() => onSelect(s.agentId)} className="flex w-full items-center justify-between gap-2 rounded-sm border border-cmd-border px-2 py-1 text-left hover:border-cmd-cyan/50">
              <span className="text-cmd-text">{AGENT_PROFILES[s.agentId].name}</span>
              <StatusPill tone={studentToneFor(s.graduationStatus)}>{s.completionPct.toFixed(0)}%</StatusPill>
            </button>
          ))}
        </div>
      )}
    </Glass>
  );
}

function EmployeeAcademyReport({
  agentId,
  mentorId,
  onClose,
  onApprove,
  busy,
}: {
  agentId: AgentId;
  mentorId: FoundationalMentorId | null;
  onClose: () => void;
  onApprove: (agentId: AgentId, mentorId: FoundationalMentorId) => void;
  busy: boolean;
}) {
  const { foundationalMentorState, agentKnowledge } = useGameStore();
  const dashboard = computeAcademyDashboard(foundationalMentorState, agentKnowledge);
  const summary = mentorId ? [...dashboard.currentlyStudying, ...dashboard.graduationQueue, ...dashboard.needingHelp, ...dashboard.topStudents].find((s) => s.agentId === agentId) : null;
  const certifications = foundationalMentorState.certifications.filter((c) => c.agentId === agentId);
  const knowledge = agentKnowledge[agentId];

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center bg-cmd-bg/80 p-4 backdrop-blur-sm" onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()} className="w-full max-w-lg">
        <Glass className="p-4">
          <div className="mb-2 flex items-center justify-between">
            <TerminalLabel>{AGENT_PROFILES[agentId].name} — Academy Report</TerminalLabel>
            <button type="button" onClick={onClose} className="text-cmd-textDim hover:text-cmd-red">
              ✕
            </button>
          </div>
          {!summary ? (
            <EmptyState>No active Academy progress for this employee right now.</EmptyState>
          ) : (
            <>
              <DataRow label="Current mentor" value={foundationalMentorState.mentors.find((m) => m.id === summary.mentorId)?.trackLabel ?? summary.mentorId} />
              <DataRow label="Current lesson" value={summary.currentLessonTitle ? `${summary.currentLessonOrder}. ${summary.currentLessonTitle}` : "Track complete"} />
              <DataRow label="Completion" value={`${summary.completedLessonCount} / ${summary.totalLessons} (${summary.completionPct.toFixed(0)}%)`} />
              <DataRow label="Quiz average" value={`${summary.quizAveragePct.toFixed(0)}%`} />
              <DataRow label="Consecutive quiz misses" value={summary.consecutiveQuizFailures} />
              <DataRow label="Graduation status" value={summary.graduationStatus.replace("_", " ")} />
              <DataRow label="Knowledge points" value={knowledge ? `${knowledge.points.toFixed(1)} (${knowledge.level})` : "—"} />
              {summary.graduationStatus === "pending_approval" && (
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => onApprove(agentId, summary.mentorId)}
                  className="mt-2 rounded-sm border border-cmd-green/50 px-3 py-1 text-[9px] uppercase tracking-wide text-cmd-green hover:bg-cmd-green/10 disabled:opacity-40"
                >
                  Approve Graduation
                </button>
              )}
              {summary.coachNote && <div className="mt-2 rounded-sm border border-cmd-amber/40 bg-cmd-amber/10 p-2 text-[9px] text-cmd-amber">{summary.coachNote}</div>}
            </>
          )}
          <div className="mt-3 border-t border-cmd-border/60 pt-2">
            <TerminalLabel>Certifications</TerminalLabel>
            <p className="mb-1 text-[9px] text-cmd-textDim">Full controls (View/Revoke/Downgrade/Promote/Reset Progress/History) live in Current Certifications, below.</p>
            {certifications.length === 0 ? (
              <EmptyState>None yet.</EmptyState>
            ) : (
              certifications.map((c) => (
                <div key={c.id} className="flex items-center justify-between gap-2 py-0.5 text-[9px] text-cmd-textDim">
                  <span>{c.mentorName}</span>
                  <StatusPill tone={certificationStatusTone(c.status)}>{c.status.toUpperCase()}</StatusPill>
                </div>
              ))
            )}
          </div>
        </Glass>
      </div>
    </div>
  );
}

/**
 * The CEO's own entirely optional personal Learning Mode — never
 * touches real employee progress (ceoProgress is a separate bucket).
 * Only rendered when Settings.ceoAcademyLearningMode is on.
 */
function CeoPersonalLearning() {
  const { foundationalMentorState } = useGameStore();
  const [selectedMentorId, setSelectedMentorId] = useState<FoundationalMentorId>("tjr");
  const [selectedLessonId, setSelectedLessonId] = useState<string | null>(null);
  const [selectedOption, setSelectedOption] = useState<number | null>(null);
  const [quizResult, setQuizResult] = useState<{ correct: boolean; correctOption: string } | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resourceTitle, setResourceTitle] = useState("");
  const [resourceUrl, setResourceUrl] = useState("");
  const [resourceType, setResourceType] = useState<FoundationalResourceType>("video");

  const mentor = foundationalMentorState.mentors.find((m) => m.id === selectedMentorId) ?? null;
  const progress = foundationalMentorState.ceoProgress[selectedMentorId];
  const selectedLesson = mentor?.lessons.find((l) => l.id === selectedLessonId) ?? null;

  const openLesson = (lesson: FoundationalMentorLesson) => {
    if (!mentor) return;
    setSelectedLessonId(lesson.id);
    setSelectedOption(null);
    setQuizResult(null);
    if (!progress?.viewedLessonIds.includes(lesson.id)) {
      void api
        .ceoViewAcademyLesson(mentor.id, lesson.id)
        .then((res) => NexusManager.setFoundationalMentorState(res.foundationalMentorState))
        .catch((err) => setError(err instanceof Error ? err.message : String(err)));
    }
  };

  const submitQuiz = async (lesson: FoundationalMentorLesson) => {
    if (!mentor || selectedOption === null || submitting) return;
    setSubmitting(true);
    try {
      const res = await api.ceoSubmitAcademyQuiz(mentor.id, lesson.id, selectedOption);
      NexusManager.setFoundationalMentorState(res.foundationalMentorState);
      setQuizResult({ correct: res.correct, correctOption: res.correctOption });
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  };

  const addResource = async () => {
    if (!mentor || !resourceTitle.trim()) return;
    setError(null);
    try {
      const res = await api.addFoundationalMentorResource(mentor.id, resourceTitle.trim(), resourceUrl.trim() || null, resourceType);
      NexusManager.setFoundationalMentorState(res.foundationalMentorState);
      setResourceTitle("");
      setResourceUrl("");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  return (
    <div data-testid="ceo-personal-learning">
    <Glass className="p-3">
      <TerminalLabel>Your Personal Learning (CEO Learning Mode)</TerminalLabel>
      <div className="mb-2 text-[9px] text-cmd-textDim">
        Entirely optional and separate from real employee progress — never required for company progression.
      </div>
      {error && <div className="mb-2 text-cmd-red">{error}</div>}

      <div className="mb-2 flex flex-wrap gap-1">
        {foundationalMentorState.mentors.map((m) => (
          <button
            key={m.id}
            type="button"
            onClick={() => {
              setSelectedMentorId(m.id);
              setSelectedLessonId(null);
              setSelectedOption(null);
              setQuizResult(null);
            }}
            className={`rounded-sm border px-2 py-1 text-[9px] ${selectedMentorId === m.id ? "border-cmd-cyan/50 bg-cmd-cyan/10 text-cmd-cyan" : "border-cmd-border text-cmd-textDim"}`}
          >
            {m.trackLabel}
          </button>
        ))}
      </div>

      {mentor && (
        <div className="mb-2 text-[9px] text-cmd-textDim">{mentor.contentNote}</div>
      )}

      {!mentor || mentor.lessons.length === 0 ? (
        <EmptyState>This track has no lessons authored yet.</EmptyState>
      ) : (
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
          <div className="space-y-1">
            {mentor.lessons.map((lesson) => {
              const completed = progress?.completedLessonIds.includes(lesson.id) ?? false;
              const viewed = progress?.viewedLessonIds.includes(lesson.id) ?? false;
              return (
                <button
                  key={lesson.id}
                  type="button"
                  onClick={() => openLesson(lesson)}
                  className={`flex w-full items-center justify-between gap-2 rounded-sm border px-2 py-1 text-left ${
                    selectedLessonId === lesson.id ? "border-cmd-cyan/50 bg-cmd-cyan/10 text-cmd-cyan" : "border-cmd-border text-cmd-textDim hover:text-cmd-text"
                  }`}
                >
                  <span>
                    {lesson.order}. {lesson.title}
                  </span>
                  {completed ? <StatusPill tone="green">DONE</StatusPill> : viewed ? <StatusPill tone="neutral">SEEN</StatusPill> : null}
                </button>
              );
            })}
          </div>

          {selectedLesson && (
            <div data-testid="ceo-lesson-viewer">
              <div className="text-cmd-text">{selectedLesson.title}</div>
              <div className="mt-1 text-cmd-textDim">{selectedLesson.simpleExplanation}</div>
              <details className="mt-1">
                <summary className="cursor-pointer text-cmd-textDim hover:text-cmd-cyan">Deeper explanation</summary>
                <div className="mt-1 text-cmd-textDim">{selectedLesson.deeperExplanation}</div>
              </details>
              <div className="mt-3 border-t border-cmd-border pt-3">
                <div className="mb-2 text-cmd-text">{selectedLesson.quizQuestion}</div>
                <div className="space-y-1">
                  {selectedLesson.quizOptions.map((option, i) => (
                    <button
                      key={i}
                      type="button"
                      onClick={() => setSelectedOption(i)}
                      disabled={quizResult !== null}
                      className={`block w-full rounded-sm border px-2 py-1 text-left disabled:opacity-70 ${
                        selectedOption === i ? "border-cmd-cyan/50 bg-cmd-cyan/10 text-cmd-cyan" : "border-cmd-border text-cmd-textDim hover:text-cmd-text"
                      }`}
                    >
                      {option}
                    </button>
                  ))}
                </div>
                {quizResult === null ? (
                  <button
                    type="button"
                    onClick={() => void submitQuiz(selectedLesson)}
                    disabled={selectedOption === null || submitting}
                    className="mt-2 rounded-sm border border-cmd-border px-3 py-1 text-cmd-textDim hover:enabled:text-cmd-cyan hover:enabled:border-cmd-cyan/50 disabled:opacity-40"
                  >
                    {submitting ? "…" : "Submit Answer"}
                  </button>
                ) : (
                  <Glass className={`mt-2 p-2 ${quizResult.correct ? "border-cmd-green/50" : "border-cmd-red/50"}`}>
                    <StatusPill tone={quizResult.correct ? "green" : "red"}>{quizResult.correct ? "CORRECT" : "NOT QUITE"}</StatusPill>
                    {!quizResult.correct && <div className="mt-1 text-[9px] text-cmd-textDim">Correct answer: {quizResult.correctOption}</div>}
                  </Glass>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {mentor && (
        <div className="mt-3 border-t border-cmd-border/50 pt-2">
          <TerminalLabel>External Resources — CEO Reading List</TerminalLabel>
          {mentor.resources.length === 0 ? (
            <EmptyState>No resources bookmarked yet.</EmptyState>
          ) : (
            <div className="space-y-1">
              {mentor.resources.map((r) => (
                <div key={r.id} className="flex items-center justify-between gap-2 border-b border-cmd-border/60 py-1 last:border-0">
                  <span className="text-cmd-text">{r.title}</span>
                  <span className="text-[9px] uppercase text-cmd-textDim">{r.resourceType}</span>
                </div>
              ))}
            </div>
          )}
          <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-4">
            <input type="text" placeholder="Title" value={resourceTitle} onChange={(e) => setResourceTitle(e.target.value)} className="rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1 text-cmd-text outline-none focus:border-cmd-cyan/50 sm:col-span-2" />
            <input type="text" placeholder="URL (optional)" value={resourceUrl} onChange={(e) => setResourceUrl(e.target.value)} className="rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1 text-cmd-text outline-none focus:border-cmd-cyan/50" />
            <select value={resourceType} onChange={(e) => setResourceType(e.target.value as FoundationalResourceType)} className="rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1 text-cmd-text outline-none focus:border-cmd-cyan/50">
              {RESOURCE_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>
          <button type="button" onClick={() => void addResource()} disabled={!resourceTitle.trim()} className="mt-2 rounded-sm border border-cmd-cyan/50 px-3 py-1 text-[9px] uppercase tracking-wider text-cmd-cyan hover:bg-cmd-cyan/10 disabled:opacity-40">
            Add Bookmark
          </button>
        </div>
      )}
    </Glass>
    </div>
  );
}
