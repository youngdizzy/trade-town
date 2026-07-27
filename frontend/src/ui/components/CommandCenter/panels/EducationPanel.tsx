import { useEffect, useState } from "react";
import { useGameStore } from "@/ui/hooks/useGameStore";
import type { EducationLesson, EducationTopic } from "@/types";
import { api } from "@/net/api";
import { NexusManager } from "@/game/systems/NexusManager";
import { DataRow, EmptyState, Glass, StatusPill, TerminalLabel } from "../ui";

/**
 * Trading Education (v0.6.2 Phase 9) — a ten-topic curriculum, ordered as
 * a real progression (candlesticks → wicks → trends → support/resistance
 * → ENTER/WAIT/AVOID → stop loss → take profit → risk/reward → position
 * sizing → why NO TRADE can be correct). Lesson content is fetched once
 * from the backend (the canonical source — see backend/app/education.py)
 * rather than duplicated in the frontend bundle.
 */
export function EducationPanel({ openLessonId }: { openLessonId?: EducationTopic | null } = {}) {
  const { education } = useGameStore();
  const [lessons, setLessons] = useState<EducationLesson[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<EducationTopic | null>(openLessonId ?? null);
  const [selectedOption, setSelectedOption] = useState<number | null>(null);
  const [quizResult, setQuizResult] = useState<{ correct: boolean; correctOption: string } | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    api
      .getLessons()
      .then(setLessons)
      .catch((err) => setError(err instanceof Error ? err.message : String(err)));
  }, []);

  useEffect(() => {
    if (openLessonId) setSelectedId(openLessonId);
  }, [openLessonId]);

  const selected = lessons?.find((l) => l.id === selectedId) ?? null;

  const openLesson = (lesson: EducationLesson) => {
    setSelectedId(lesson.id);
    setSelectedOption(null);
    setQuizResult(null);
    if (!education.viewedLessonIds.includes(lesson.id)) {
      void api.markLessonViewed(lesson.id).then((res) => NexusManager.setEducation(res.education));
    }
  };

  const submitQuiz = async (lesson: EducationLesson) => {
    if (selectedOption === null || submitting) return;
    setSubmitting(true);
    try {
      const res = await api.submitQuiz(lesson.id, selectedOption);
      NexusManager.setEducation(res.education);
      setQuizResult({ correct: res.correct, correctOption: res.correctOption });
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  };

  if (error) return <div className="text-cmd-red">{error}</div>;
  if (!lessons) return <EmptyState>Loading curriculum…</EmptyState>;

  return (
    <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
      <Glass className="p-3 lg:col-span-1">
        <TerminalLabel>Curriculum</TerminalLabel>
        <DataRow label="Completed" value={`${education.completedLessonIds.length} / ${lessons.length}`} />
        <div className="mt-2 space-y-1">
          {lessons.map((lesson) => {
            const completed = education.completedLessonIds.includes(lesson.id);
            const viewed = education.viewedLessonIds.includes(lesson.id);
            return (
              <button
                key={lesson.id}
                type="button"
                onClick={() => openLesson(lesson)}
                className={`flex w-full items-center justify-between gap-2 rounded-sm border px-2 py-1 text-left ${
                  selectedId === lesson.id ? "border-cmd-cyan/50 bg-cmd-cyan/10 text-cmd-cyan" : "border-cmd-border text-cmd-textDim hover:text-cmd-text"
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

      <div className="lg:col-span-2" data-testid="education-lesson">
        <Glass className="p-3">
          {!selected ? (
            <EmptyState>Pick a lesson to begin.</EmptyState>
          ) : (
            <div className="space-y-3">
              <TerminalLabel>{selected.title}</TerminalLabel>
              <div className="text-cmd-text">{selected.simpleExplanation}</div>
              <div className="border-l-2 border-cmd-cyan/40 pl-2 text-cmd-textDim">{selected.visualExampleNote}</div>
              <details>
                <summary className="cursor-pointer text-cmd-textDim hover:text-cmd-cyan">Deeper explanation</summary>
                <div className="mt-1 text-cmd-textDim">{selected.deeperExplanation}</div>
              </details>

              <div className="border-t border-cmd-border pt-3">
                <TerminalLabel>Practice Challenge</TerminalLabel>
                <div className="mb-2 text-cmd-text">{selected.quizQuestion}</div>
                <div className="space-y-1">
                  {selected.quizOptions.map((option, i) => (
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
                    onClick={() => void submitQuiz(selected)}
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
        </Glass>
      </div>
    </div>
  );
}
