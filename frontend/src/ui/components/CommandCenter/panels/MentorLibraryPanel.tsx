import { useState } from "react";
import { useGameStore } from "@/ui/hooks/useGameStore";
import type { FoundationalMentorId, FoundationalMentorLesson, FoundationalMentorProfile, FoundationalMentorStatus, FoundationalResourceType } from "@/types";
import { api } from "@/net/api";
import { NexusManager } from "@/game/systems/NexusManager";
import { DataRow, EmptyState, Glass, StatusPill, TerminalLabel } from "../ui";

const STATUS_TONE: Record<FoundationalMentorStatus, "neutral" | "cyan" | "green" | "amber"> = {
  planned: "neutral",
  active: "cyan",
  paused: "amber",
  graduated: "green",
};

const RESOURCE_TYPES: FoundationalResourceType[] = ["video", "book", "article", "pdf", "note"];

/**
 * The Foundational Mentor Program (v0.7 Feature 49, Phase 3) — see
 * backend/app/foundational_mentors.py's module docstring for the full
 * content-attribution boundary. Real named educators are CEO-assigned
 * track labels only; every lesson's content is original TradeTown-
 * authored material, disclaimed explicitly below. Data already arrives
 * on gameStore.foundationalMentorState via the WS tick broadcast, so
 * unlike EducationPanel there's no separate fetch-on-mount here.
 */
export function MentorLibraryPanel() {
  const { foundationalMentorState } = useGameStore();
  const [selectedMentorId, setSelectedMentorId] = useState<FoundationalMentorId | null>(foundationalMentorState.activeMentorId ?? "tjr");
  const [selectedLessonId, setSelectedLessonId] = useState<string | null>(null);
  const [selectedOption, setSelectedOption] = useState<number | null>(null);
  const [quizResult, setQuizResult] = useState<{ correct: boolean; correctOption: string } | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resourceTitle, setResourceTitle] = useState("");
  const [resourceUrl, setResourceUrl] = useState("");
  const [resourceType, setResourceType] = useState<FoundationalResourceType>("video");

  const mentor = foundationalMentorState.mentors.find((m) => m.id === selectedMentorId) ?? null;
  const progress = selectedMentorId ? foundationalMentorState.progress[selectedMentorId] : undefined;
  const selectedLesson = mentor?.lessons.find((l) => l.id === selectedLessonId) ?? null;

  const openMentor = (m: FoundationalMentorProfile) => {
    setSelectedMentorId(m.id);
    setSelectedLessonId(null);
    setSelectedOption(null);
    setQuizResult(null);
  };

  const openLesson = (lesson: FoundationalMentorLesson) => {
    if (!mentor) return;
    setSelectedLessonId(lesson.id);
    setSelectedOption(null);
    setQuizResult(null);
    if (!progress?.viewedLessonIds.includes(lesson.id)) {
      void api
        .viewFoundationalMentorLesson(mentor.id, lesson.id)
        .then((res) => NexusManager.setFoundationalMentorState(res.foundationalMentorState))
        .catch((err) => setError(err instanceof Error ? err.message : String(err)));
    }
  };

  const submitQuiz = async (lesson: FoundationalMentorLesson) => {
    if (!mentor || selectedOption === null || submitting) return;
    setSubmitting(true);
    try {
      const res = await api.submitFoundationalMentorQuiz(mentor.id, lesson.id, selectedOption);
      NexusManager.setFoundationalMentorState(res.foundationalMentorState);
      setQuizResult({ correct: res.correct, correctOption: res.correctOption });
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  };

  const runControl = async (action: "pause" | "resume" | "skip" | "repeat") => {
    if (!mentor) return;
    setError(null);
    try {
      const fn =
        action === "pause"
          ? api.pauseFoundationalMentor
          : action === "resume"
            ? api.resumeFoundationalMentor
            : action === "skip"
              ? api.skipFoundationalMentor
              : api.repeatFoundationalMentor;
      const res = await fn(mentor.id);
      NexusManager.setFoundationalMentorState(res.foundationalMentorState);
      setSelectedLessonId(null);
      setSelectedOption(null);
      setQuizResult(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
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

  if (foundationalMentorState.mentors.length === 0) return <EmptyState>Loading mentor library…</EmptyState>;

  return (
    <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
      <Glass className="p-3 lg:col-span-1">
        <TerminalLabel>Mentor Roadmap</TerminalLabel>
        <div className="mt-2 space-y-1">
          {foundationalMentorState.mentors.map((m) => (
            <button
              key={m.id}
              type="button"
              onClick={() => openMentor(m)}
              className={`flex w-full items-center justify-between gap-2 rounded-sm border px-2 py-1 text-left ${
                selectedMentorId === m.id ? "border-cmd-cyan/50 bg-cmd-cyan/10 text-cmd-cyan" : "border-cmd-border text-cmd-textDim hover:text-cmd-text"
              }`}
            >
              <span>{m.trackLabel}</span>
              <StatusPill tone={STATUS_TONE[m.status]}>{m.status.toUpperCase()}</StatusPill>
            </button>
          ))}
        </div>
      </Glass>

      <div className="lg:col-span-2" data-testid="mentor-library-detail">
        {error && <div className="mb-2 text-cmd-red">{error}</div>}
        {!mentor ? (
          <Glass className="p-3">
            <EmptyState>Pick a track to begin.</EmptyState>
          </Glass>
        ) : (
          <div className="space-y-3">
            <Glass className="p-3">
              <div className="flex items-center justify-between gap-2">
                <TerminalLabel>{mentor.trackLabel}</TerminalLabel>
                <StatusPill tone={STATUS_TONE[mentor.status]}>{mentor.status.toUpperCase()}</StatusPill>
              </div>
              <div className="mt-2 flex flex-wrap gap-1">
                {mentor.focusAreas.map((area) => (
                  <span key={area} className="rounded-sm border border-cmd-border px-1.5 py-0.5 text-[9px] text-cmd-textDim">
                    {area}
                  </span>
                ))}
              </div>
              <div className="mt-2 border-t border-cmd-border/60 pt-2 text-[9px] text-cmd-textDim">{mentor.contentNote}</div>
              <div className="mt-2 grid grid-cols-3 gap-2">
                <DataRow label="Lessons" value={mentor.lessons.length} />
                <DataRow label="Completed" value={progress?.completedLessonIds.length ?? 0} />
                <DataRow label="Graduated" value={progress?.graduatedSimDay !== undefined && progress.graduatedSimDay !== null ? `Day ${progress.graduatedSimDay}` : "—"} />
              </div>
              <div className="mt-2 flex flex-wrap gap-2">
                {mentor.status === "active" && (
                  <button type="button" onClick={() => void runControl("pause")} className="rounded-sm border border-cmd-border px-2 py-1 text-[9px] uppercase text-cmd-textDim hover:border-cmd-amber/50 hover:text-cmd-amber">
                    Pause Track
                  </button>
                )}
                {mentor.status === "paused" && (
                  <button type="button" onClick={() => void runControl("resume")} className="rounded-sm border border-cmd-border px-2 py-1 text-[9px] uppercase text-cmd-textDim hover:border-cmd-cyan/50 hover:text-cmd-cyan">
                    Resume Track
                  </button>
                )}
                {(mentor.status === "active" || mentor.status === "paused") && (
                  <button type="button" onClick={() => void runControl("skip")} className="rounded-sm border border-cmd-border px-2 py-1 text-[9px] uppercase text-cmd-textDim hover:border-cmd-red/50 hover:text-cmd-red">
                    Skip to Next Track
                  </button>
                )}
                {mentor.status === "graduated" && (
                  <button type="button" onClick={() => void runControl("repeat")} className="rounded-sm border border-cmd-border px-2 py-1 text-[9px] uppercase text-cmd-textDim hover:border-cmd-cyan/50 hover:text-cmd-cyan">
                    Repeat Track
                  </button>
                )}
              </div>
            </Glass>

            {mentor.lessons.length === 0 ? (
              <Glass className="p-3">
                <EmptyState>This track is on the roadmap but has no lessons yet — real content hasn&apos;t been authored for it.</EmptyState>
              </Glass>
            ) : (
              <>
                <Glass className="p-3">
                  <TerminalLabel>Lessons</TerminalLabel>
                  <div className="mt-2 space-y-1">
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
                </Glass>

                {selectedLesson && (
                  <div data-testid="mentor-lesson-viewer">
                    <Glass className="p-3">
                      <TerminalLabel>{selectedLesson.title}</TerminalLabel>
                      <div className="mt-1 text-cmd-text">{selectedLesson.simpleExplanation}</div>
                      <details className="mt-1">
                        <summary className="cursor-pointer text-cmd-textDim hover:text-cmd-cyan">Deeper explanation</summary>
                        <div className="mt-1 text-cmd-textDim">{selectedLesson.deeperExplanation}</div>
                      </details>

                      <div className="mt-3 border-t border-cmd-border pt-3">
                        <TerminalLabel>Check Your Understanding</TerminalLabel>
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
                    </Glass>
                  </div>
                )}
              </>
            )}

            <Glass className="p-3">
              <TerminalLabel>External Resources — CEO Reading List</TerminalLabel>
              <div className="mt-1 text-[9px] text-cmd-textDim">
                CEO-provided bookmarks only — TradeTown never fetches, reads, or grades linked material.
              </div>
              {mentor.resources.length === 0 ? (
                <EmptyState>No resources bookmarked yet.</EmptyState>
              ) : (
                <div className="mt-2 space-y-1">
                  {mentor.resources.map((r) => (
                    <div key={r.id} className="flex items-center justify-between gap-2 border-b border-cmd-border/60 py-1 last:border-0">
                      <span className="text-cmd-text">{r.title}</span>
                      <span className="text-[9px] uppercase text-cmd-textDim">{r.resourceType}</span>
                    </div>
                  ))}
                </div>
              )}
              <div className="mt-2 grid grid-cols-1 gap-2 border-t border-cmd-border/50 pt-2 sm:grid-cols-4">
                <input
                  type="text"
                  placeholder="Title"
                  value={resourceTitle}
                  onChange={(e) => setResourceTitle(e.target.value)}
                  className="rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1 text-cmd-text outline-none focus:border-cmd-cyan/50 sm:col-span-2"
                />
                <input
                  type="text"
                  placeholder="URL (optional)"
                  value={resourceUrl}
                  onChange={(e) => setResourceUrl(e.target.value)}
                  className="rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1 text-cmd-text outline-none focus:border-cmd-cyan/50"
                />
                <select
                  value={resourceType}
                  onChange={(e) => setResourceType(e.target.value as FoundationalResourceType)}
                  className="rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1 text-cmd-text outline-none focus:border-cmd-cyan/50"
                >
                  {RESOURCE_TYPES.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
              </div>
              <button
                type="button"
                onClick={() => void addResource()}
                disabled={!resourceTitle.trim()}
                className="mt-2 rounded-sm border border-cmd-cyan/50 px-3 py-1 text-[9px] uppercase tracking-wider text-cmd-cyan hover:bg-cmd-cyan/10 disabled:opacity-40"
              >
                Add Bookmark
              </button>
            </Glass>
          </div>
        )}
      </div>
    </div>
  );
}
