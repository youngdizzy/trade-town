import { useState } from "react";
import { useGameStore } from "@/ui/hooks/useGameStore";
import { useCloseOnEscape } from "@/ui/hooks/useCloseOnEscape";
import { EventBus } from "@/game/systems/EventBus";
import { AGENT_PROFILES } from "@/game/systems/AgentProfiles";
import type { CoachReport, ReportPeriod } from "@/types";

/**
 * The Coach Dashboard (v0.5 brief, Feature 1) — Coach's evaluation of the
 * company: overall score, agent rankings, research/confidence accuracy,
 * paper trading performance, risk, common mistakes, and recommendations.
 * Coach only ever evaluates here; nothing on this screen places or closes
 * a trade (see backend/app/coach.py's module docstring).
 */
export function CoachDashboard() {
  const { coachDashboardOpen, coachReports, companyScore, paperPortfolio } = useGameStore();
  const [period, setPeriod] = useState<ReportPeriod>("weekly");
  const close = () => EventBus.emit("ui:coachDashboard", { open: false });
  useCloseOnEscape(coachDashboardOpen, close);
  if (!coachDashboardOpen) return null;
  const report = latestReportFor(coachReports, period);

  return (
    <div className="pointer-events-auto absolute inset-0 z-50 flex items-center justify-center bg-black/60 font-pixel text-[11px]">
      <div className="flex max-h-[85vh] w-[34rem] flex-col overflow-hidden rounded bg-parchment text-ink shadow-pixel">
        <div className="p-5 pb-3">
          <h2 className="mb-1 text-center text-lg">Coach Dashboard</h2>
          <p className="mb-3 text-center text-[9px] opacity-60">Performance &amp; Improvement — evaluation only, never executes trades</p>

          <div className="mb-3 flex items-center justify-between gap-2 rounded border border-ink/20 bg-white/40 px-3 py-2">
            <span className="opacity-70">Overall Company Score</span>
            <span className="text-lg text-gold">{Math.round(companyScore.overall)}/100</span>
          </div>

          <div className="flex gap-1.5">
            <PeriodTab label="Weekly Report" active={period === "weekly"} onClick={() => setPeriod("weekly")} />
            <PeriodTab label="Monthly Report" active={period === "monthly"} onClick={() => setPeriod("monthly")} />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto border-t border-ink/20 px-5 py-3">
          {report === null ? (
            <p className="opacity-50">
              No {period} report yet. Coach reviews every evening (see the Performance Center); {period} reports post on the {period === "weekly" ? "7-day" : "30-day"} cycle.
            </p>
          ) : (
            <>
              <Row label="Research Accuracy" value={`${Math.round(report.researchAccuracy)}%`} />
              <Row label="Win / Loss Rate" value={`${Math.round(report.winRate)}% / ${Math.round(report.lossRate)}%`} />
              <Row label="Average Confidence" value={`${Math.round(report.averageConfidence)}%`} />
              <Row label="Risk Score" value={`${Math.round(report.riskScore)}/100`} />
              <Row
                label="Paper P&L"
                value={`${paperPortfolio.totalPnl >= 0 ? "+" : ""}${paperPortfolio.totalPnl.toFixed(2)} (${paperPortfolio.totalPnlPct.toFixed(1)}%)`}
              />

              <DashSection title="Agent Rankings">
                {report.agentRankings.length === 0 && <p className="opacity-50">No ranked agents yet.</p>}
                <ol className="space-y-1">
                  {report.agentRankings.map((score, i) => (
                    <li key={score.agentId} className="flex items-center justify-between gap-2">
                      <span>
                        {i + 1}. {AGENT_PROFILES[score.agentId].name}
                      </span>
                      <span className="opacity-70">
                        score {Math.round(score.score)} · research {Math.round(score.researchAccuracy)}% · calibration {Math.round(score.confidenceCalibration)}%
                      </span>
                    </li>
                  ))}
                </ol>
              </DashSection>

              <DashSection title="Most Common Mistakes">
                {report.commonMistakes.length === 0 && <p className="opacity-50">None flagged this period.</p>}
                <ul className="list-inside list-disc space-y-1">
                  {report.commonMistakes.map((m, i) => (
                    <li key={i}>{m}</li>
                  ))}
                </ul>
              </DashSection>

              <DashSection title="Strengths">
                {report.strengths.length === 0 && <p className="opacity-50">None flagged this period.</p>}
                <ul className="list-inside list-disc space-y-1">
                  {report.strengths.map((s, i) => (
                    <li key={i}>{s}</li>
                  ))}
                </ul>
              </DashSection>

              <DashSection title="Recommended Improvements">
                {report.recommendations.length === 0 && <p className="opacity-50">Nothing to recommend right now — keep it up.</p>}
                <ul className="list-inside list-disc space-y-1">
                  {report.recommendations.map((r, i) => (
                    <li key={i}>{r}</li>
                  ))}
                </ul>
              </DashSection>

              <p className="mt-3 text-[9px] opacity-50">Filed {new Date(report.createdAt).toLocaleString()}</p>
            </>
          )}
        </div>

        <div className="p-5 pt-3">
          <button
            type="button"
            onClick={close}
            className="w-full rounded bg-panelLight py-2 text-parchment transition-colors hover:bg-gold hover:text-ink"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

function latestReportFor(reports: CoachReport[], period: ReportPeriod): CoachReport | null {
  for (let i = reports.length - 1; i >= 0; i--) {
    const report = reports[i];
    if (report && report.period === period) return report;
  }
  return null;
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="mb-1.5 flex items-center justify-between gap-2 border-b border-ink/10 pb-1">
      <span className="opacity-70">{label}</span>
      <span className="text-gold">{value}</span>
    </div>
  );
}

function DashSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-3 mt-3">
      <h3 className="mb-1.5 border-b border-ink/30 pb-1 text-[10px] uppercase tracking-wide opacity-70">{title}</h3>
      {children}
    </div>
  );
}

function PeriodTab({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded px-2.5 py-1 text-[9px] transition-colors ${active ? "bg-ink text-parchment" : "bg-ink/10 text-ink hover:bg-ink/20"}`}
    >
      {label}
    </button>
  );
}
