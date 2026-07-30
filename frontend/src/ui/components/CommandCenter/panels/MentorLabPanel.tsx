import { useState } from "react";
import { useGameStore } from "@/ui/hooks/useGameStore";
import { NexusManager } from "@/game/systems/NexusManager";
import { api } from "@/net/api";
import type { FoundationalMentorId } from "@/types";
import { computeCompanyConceptsLearned, computeMentorComparison } from "../lib/derive";
import { DataRow, EmptyState, Glass, StatusPill, TerminalLabel } from "../ui";

/**
 * Mentor Lab — the headquarters for the Foundational Mentor Library
 * (v0.7 Command Center UI Revision). Mentor-centric browsing, distinct
 * from the ACADEMY tab's employee-centric management dashboard: pick a
 * mentor to see its own curriculum, philosophy (focus areas), company
 * notes (content disclaimer), and real graduation status. Also where
 * the CEO really expands the library — Add New Mentor / Add Lesson —
 * see backend/app/foundational_mentors.py's "Mentor Lab" module
 * docstring section for the full design.
 *
 * "Concepts Validated" / "Concepts Rejected" (from the brief) are
 * deliberately NOT shown as numbers here — no real cross-system
 * validation pipeline exists in this codebase to back them (every
 * concept would need to be Discussed → Backtested → Paper Traded →
 * Sandbox Tested → Quant Reviewed → Risk Reviewed → Devil's Advocate
 * Reviewed → Founder Council Reviewed, none of which this module wires
 * up — see the same module docstring's scope-cut list). "Company
 * Concepts Learned" IS shown, since it's a real, checkable count.
 */
export function MentorLabPanel() {
  const { foundationalMentorState } = useGameStore();
  const [selectedMentorId, setSelectedMentorId] = useState<FoundationalMentorId | null>(foundationalMentorState.activeMentorId);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [showAddMentor, setShowAddMentor] = useState(false);
  const [showAddLesson, setShowAddLesson] = useState(false);

  const mentor = foundationalMentorState.mentors.find((m) => m.id === selectedMentorId) ?? null;
  const conceptsLearned = computeCompanyConceptsLearned(foundationalMentorState);
  const comparison = computeMentorComparison(foundationalMentorState);

  const activateMentor = async (mentorId: FoundationalMentorId) => {
    setBusy(true);
    setError(null);
    try {
      const res = await api.setActiveAcademyMentor(mentorId);
      NexusManager.setFoundationalMentorState(res.foundationalMentorState);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  if (foundationalMentorState.mentors.length === 0) return <EmptyState>Loading Mentor Lab…</EmptyState>;

  return (
    <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
      <div className="space-y-3 lg:col-span-1">
        <Glass className="p-3">
          <div className="mb-1.5 flex items-center justify-between">
            <TerminalLabel>Mentor Roadmap</TerminalLabel>
            <button type="button" onClick={() => setShowAddMentor(true)} className="rounded-sm border border-cmd-cyan/50 px-2 py-1 text-[9px] uppercase tracking-wide text-cmd-cyan hover:bg-cmd-cyan/10">
              + Add New Mentor
            </button>
          </div>
          <div className="space-y-1">
            {foundationalMentorState.mentors.map((m) => (
              <button
                key={m.id}
                type="button"
                onClick={() => setSelectedMentorId(m.id)}
                className={`flex w-full items-center justify-between gap-2 rounded-sm border px-2 py-1 text-left ${
                  selectedMentorId === m.id ? "border-cmd-cyan/50 bg-cmd-cyan/10 text-cmd-cyan" : "border-cmd-border text-cmd-textDim hover:text-cmd-text"
                }`}
              >
                <span>{m.trackLabel}</span>
                <StatusPill tone={m.id === foundationalMentorState.activeMentorId ? "cyan" : m.status === "graduated" ? "green" : m.status === "paused" ? "amber" : "neutral"}>
                  {m.status.toUpperCase()}
                </StatusPill>
              </button>
            ))}
          </div>
        </Glass>

        <Glass className="p-3">
          <TerminalLabel>Company Concepts Learned</TerminalLabel>
          <div className="font-cmdmono text-lg text-cmd-text">{conceptsLearned}</div>
          <div className="mt-1 text-[9px] text-cmd-textDim">
            Distinct lessons, across every mentor track, at least one real employee has completed. "Concepts Validated" and "Concepts Rejected" aren't shown — no real
            cross-system validation pipeline exists in this codebase to back those numbers honestly.
          </div>
        </Glass>

        <Glass className="p-3">
          <TerminalLabel>Mentor Comparison</TerminalLabel>
          <div className="space-y-1.5">
            {comparison.map((row) => (
              <div key={row.mentorId} className="flex items-center justify-between gap-2 border-b border-cmd-border/60 py-1 last:border-0">
                <span className="text-cmd-text">{row.name}</span>
                <span className="text-[9px] text-cmd-textDim">
                  {row.lessonCount} lesson{row.lessonCount === 1 ? "" : "s"} · {row.avgCompletionPct.toFixed(0)}% avg completion
                </span>
              </div>
            ))}
          </div>
        </Glass>
      </div>

      <div className="lg:col-span-2">
        {error && <div className="mb-2 text-cmd-red">{error}</div>}
        {!mentor ? (
          <Glass className="p-3">
            <EmptyState>Pick a track to see its curriculum.</EmptyState>
          </Glass>
        ) : (
          <div className="space-y-3">
            <Glass className="p-3">
              <div className="flex items-center justify-between gap-2">
                <TerminalLabel>{mentor.trackLabel}</TerminalLabel>
                <StatusPill tone={mentor.id === foundationalMentorState.activeMentorId ? "cyan" : mentor.status === "graduated" ? "green" : mentor.status === "paused" ? "amber" : "neutral"}>
                  {mentor.status.toUpperCase()}
                </StatusPill>
              </div>
              <div className="mt-2 flex flex-wrap gap-1">
                {mentor.focusAreas.map((area) => (
                  <span key={area} className="rounded-sm border border-cmd-border px-1.5 py-0.5 text-[9px] text-cmd-textDim">
                    {area}
                  </span>
                ))}
              </div>
              <div className="mt-2 border-t border-cmd-border/60 pt-2 text-[9px] text-cmd-textDim">{mentor.contentNote}</div>
              <div className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-3">
                <DataRow label="Lessons" value={mentor.lessons.length} />
                <DataRow label="Graduated (company)" value={mentor.companyGraduatedSimDay !== null ? `Day ${mentor.companyGraduatedSimDay}` : "Not yet"} />
                <DataRow label="Currently active" value={mentor.id === foundationalMentorState.activeMentorId ? "Yes" : "No"} />
              </div>
              <div className="mt-2 flex flex-wrap gap-2">
                {mentor.id !== foundationalMentorState.activeMentorId && mentor.lessons.length > 0 && (
                  <button type="button" disabled={busy} onClick={() => void activateMentor(mentor.id)} className="rounded-sm border border-cmd-border px-2 py-1 text-[9px] uppercase text-cmd-textDim hover:border-cmd-cyan/50 hover:text-cmd-cyan disabled:opacity-40">
                    Make Active Track
                  </button>
                )}
                <button type="button" onClick={() => setShowAddLesson(true)} className="rounded-sm border border-cmd-cyan/50 px-2 py-1 text-[9px] uppercase tracking-wide text-cmd-cyan hover:bg-cmd-cyan/10">
                  + Add Lesson (Build Curriculum)
                </button>
              </div>
            </Glass>

            <Glass className="p-3">
              <TerminalLabel>Curriculum</TerminalLabel>
              {mentor.lessons.length === 0 ? (
                <EmptyState>No lessons authored yet for this track.</EmptyState>
              ) : (
                <div className="space-y-1.5">
                  {[...mentor.lessons]
                    .sort((a, b) => a.order - b.order)
                    .map((lesson) => (
                      <div key={lesson.id} className="border-b border-cmd-border/60 py-1.5 last:border-0">
                        <div className="text-cmd-text">
                          {lesson.order}. {lesson.title}
                        </div>
                        <div className="text-[9px] text-cmd-textDim">{lesson.simpleExplanation}</div>
                      </div>
                    ))}
                </div>
              )}
            </Glass>
          </div>
        )}
      </div>

      {showAddMentor && <AddMentorModal onClose={() => setShowAddMentor(false)} onCreated={(id) => setSelectedMentorId(id)} />}
      {showAddLesson && mentor && <AddLessonModal mentorId={mentor.id} onClose={() => setShowAddLesson(false)} />}
    </div>
  );
}

function AddMentorModal({ onClose, onCreated }: { onClose: () => void; onCreated: (mentorId: FoundationalMentorId) => void }) {
  const [name, setName] = useState("");
  const [trackLabel, setTrackLabel] = useState("");
  const [focusAreasText, setFocusAreasText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const submit = async () => {
    if (submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      const focusAreas = focusAreasText
        .split(",")
        .map((f) => f.trim())
        .filter(Boolean);
      const res = await api.addAcademyMentor(name.trim(), trackLabel.trim() || `${name.trim()} Track`, focusAreas);
      NexusManager.setFoundationalMentorState(res.foundationalMentorState);
      onCreated(res.mentorId);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center bg-cmd-bg/80 p-4 backdrop-blur-sm" onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()} className="w-full max-w-md">
        <Glass className="p-4">
          <div className="mb-2 flex items-center justify-between">
            <TerminalLabel>Add New Mentor</TerminalLabel>
            <button type="button" onClick={onClose} className="text-cmd-textDim hover:text-cmd-red">
              ✕
            </button>
          </div>
          {error && <div className="mb-2 text-cmd-red">{error}</div>}
          <div className="space-y-2">
            <label className="flex flex-col gap-1 text-[9px] text-cmd-textDim">
              Mentor name
              <input type="text" value={name} onChange={(e) => setName(e.target.value)} className="rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1 text-cmd-text outline-none focus:border-cmd-cyan/50" />
            </label>
            <label className="flex flex-col gap-1 text-[9px] text-cmd-textDim">
              Track label (optional — defaults to "Name Track")
              <input type="text" value={trackLabel} onChange={(e) => setTrackLabel(e.target.value)} className="rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1 text-cmd-text outline-none focus:border-cmd-cyan/50" />
            </label>
            <label className="flex flex-col gap-1 text-[9px] text-cmd-textDim">
              Focus areas (comma-separated)
              <input type="text" value={focusAreasText} onChange={(e) => setFocusAreasText(e.target.value)} placeholder="Order Flow, Tape Reading" className="rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1 text-cmd-text outline-none focus:border-cmd-cyan/50" />
            </label>
          </div>
          <div className="mt-2 text-[9px] text-cmd-textDim">This track's content will be entirely CEO-authored — added to the end of the real roadmap.</div>
          <button type="button" onClick={() => void submit()} disabled={submitting || !name.trim()} className="mt-3 rounded-sm border border-cmd-cyan/50 px-3 py-1 text-[9px] uppercase tracking-wider text-cmd-cyan hover:bg-cmd-cyan/10 disabled:opacity-40">
            {submitting ? "…" : "Add Mentor"}
          </button>
        </Glass>
      </div>
    </div>
  );
}

function AddLessonModal({ mentorId, onClose }: { mentorId: FoundationalMentorId; onClose: () => void }) {
  const [title, setTitle] = useState("");
  const [simpleExplanation, setSimpleExplanation] = useState("");
  const [deeperExplanation, setDeeperExplanation] = useState("");
  const [quizQuestion, setQuizQuestion] = useState("");
  const [options, setOptions] = useState<string[]>(["", "", "", ""]);
  const [correctIndex, setCorrectIndex] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const submit = async () => {
    if (submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      const res = await api.addAcademyLesson(mentorId, title.trim(), simpleExplanation.trim(), deeperExplanation.trim(), quizQuestion.trim(), options, correctIndex);
      NexusManager.setFoundationalMentorState(res.foundationalMentorState);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center bg-cmd-bg/80 p-4 backdrop-blur-sm" onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()} className="w-full max-w-lg">
        <Glass className="max-h-[85vh] overflow-y-auto p-4">
          <div className="mb-2 flex items-center justify-between">
            <TerminalLabel>Add Lesson — Build Academy Curriculum</TerminalLabel>
            <button type="button" onClick={onClose} className="text-cmd-textDim hover:text-cmd-red">
              ✕
            </button>
          </div>
          {error && <div className="mb-2 text-cmd-red">{error}</div>}
          <div className="space-y-2">
            <label className="flex flex-col gap-1 text-[9px] text-cmd-textDim">
              Lesson title
              <input type="text" value={title} onChange={(e) => setTitle(e.target.value)} className="rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1 text-cmd-text outline-none focus:border-cmd-cyan/50" />
            </label>
            <label className="flex flex-col gap-1 text-[9px] text-cmd-textDim">
              Simple explanation
              <textarea value={simpleExplanation} onChange={(e) => setSimpleExplanation(e.target.value)} rows={2} className="rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1 text-cmd-text outline-none focus:border-cmd-cyan/50" />
            </label>
            <label className="flex flex-col gap-1 text-[9px] text-cmd-textDim">
              Deeper explanation
              <textarea value={deeperExplanation} onChange={(e) => setDeeperExplanation(e.target.value)} rows={2} className="rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1 text-cmd-text outline-none focus:border-cmd-cyan/50" />
            </label>
            <label className="flex flex-col gap-1 text-[9px] text-cmd-textDim">
              Quiz question
              <input type="text" value={quizQuestion} onChange={(e) => setQuizQuestion(e.target.value)} className="rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1 text-cmd-text outline-none focus:border-cmd-cyan/50" />
            </label>
            <div className="text-[9px] text-cmd-textDim">Quiz options — select the radio next to the correct one</div>
            {options.map((option, i) => (
              <div key={i} className="flex items-center gap-2">
                <input type="radio" name="correct-option" checked={correctIndex === i} onChange={() => setCorrectIndex(i)} />
                <input
                  type="text"
                  value={option}
                  onChange={(e) => setOptions(options.map((o, idx) => (idx === i ? e.target.value : o)))}
                  placeholder={`Option ${i + 1}`}
                  className="flex-1 rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1 text-cmd-text outline-none focus:border-cmd-cyan/50"
                />
              </div>
            ))}
          </div>
          <button
            type="button"
            onClick={() => void submit()}
            disabled={submitting || !title.trim() || !quizQuestion.trim() || options.some((o) => !o.trim())}
            className="mt-3 rounded-sm border border-cmd-cyan/50 px-3 py-1 text-[9px] uppercase tracking-wider text-cmd-cyan hover:bg-cmd-cyan/10 disabled:opacity-40"
          >
            {submitting ? "…" : "Add Lesson"}
          </button>
        </Glass>
      </div>
    </div>
  );
}
