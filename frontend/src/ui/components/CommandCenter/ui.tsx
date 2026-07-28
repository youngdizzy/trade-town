import type { ReactNode } from "react";
import type { RiskLevel } from "./lib/derive";

/** Shared visual primitives for the Command Center's terminal aesthetic — kept separate from the fantasy-RPG `pixel`-themed components so the two visual languages never bleed into each other. */

export function Glass({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div className={`rounded-sm border border-cmd-border bg-cmd-panel/80 backdrop-blur-sm ${className}`}>{children}</div>
  );
}

export function TerminalLabel({ children }: { children: ReactNode }) {
  return <div className="mb-1.5 text-[9px] uppercase tracking-[0.15em] text-cmd-textDim">{children}</div>;
}

export function DataRow({ label, value, valueClassName = "text-cmd-text" }: { label: string; value: ReactNode; valueClassName?: string }) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-cmd-border/60 py-1 last:border-0">
      <span className="text-cmd-textDim">{label}</span>
      <span className={`text-right tabular-nums ${valueClassName}`}>{value}</span>
    </div>
  );
}

const RISK_DOT: Record<RiskLevel, string> = {
  green: "bg-cmd-green shadow-cmd-green",
  yellow: "bg-cmd-amber shadow-cmd-amber",
  red: "bg-cmd-red shadow-cmd-red animate-pulse",
};

export function RiskDot({ level, className = "" }: { level: RiskLevel; className?: string }) {
  return <span className={`inline-block h-2 w-2 rounded-full ${RISK_DOT[level]} ${className}`} />;
}

export function StatusPill({ children, tone = "neutral" }: { children: ReactNode; tone?: "neutral" | "cyan" | "green" | "amber" | "red" | "purple" }) {
  const toneClass: Record<string, string> = {
    neutral: "border-cmd-border text-cmd-textDim",
    cyan: "border-cmd-cyan/50 text-cmd-cyan shadow-cmd-cyan",
    green: "border-cmd-green/50 text-cmd-green shadow-cmd-green",
    amber: "border-cmd-amber/50 text-cmd-amber shadow-cmd-amber",
    red: "border-cmd-red/50 text-cmd-red shadow-cmd-red",
    purple: "border-cmd-purple/50 text-cmd-purple",
  };
  return (
    <span className={`inline-flex items-center gap-1 rounded-sm border bg-cmd-bg/60 px-2 py-0.5 text-[9px] uppercase tracking-wider ${toneClass[tone]}`}>
      {children}
    </span>
  );
}

export function Meter({ value, max = 100, tone = "cyan" }: { value: number; max?: number; tone?: "cyan" | "green" | "amber" | "red" }) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100));
  const barClass: Record<string, string> = {
    cyan: "bg-cmd-cyan",
    green: "bg-cmd-green",
    amber: "bg-cmd-amber",
    red: "bg-cmd-red",
  };
  return (
    <div className="h-1 w-full overflow-hidden rounded-full bg-cmd-bg">
      <div className={`h-full rounded-full transition-all duration-500 ease-out ${barClass[tone]}`} style={{ width: `${pct}%` }} />
    </div>
  );
}

export function EmptyState({ children }: { children: ReactNode }) {
  return <div className="py-3 text-center text-cmd-textDim">{children}</div>;
}

/** Faint drifting grid — v0.6.3 Feature 14's "animated grid background."
 * Pure CSS background-position animation (no canvas/WebGL, no per-frame
 * JS), so it costs nothing while charts/AI panels are also updating.
 * `pointer-events-none` so it never intercepts clicks meant for the
 * panels layered above it. */
export function AnimatedGrid({ className = "" }: { className?: string }) {
  return (
    <div
      className={`pointer-events-none absolute inset-0 opacity-[0.05] motion-safe:animate-cmd-grid-drift ${className}`}
      style={{
        backgroundImage:
          "linear-gradient(rgba(79,216,255,0.5) 1px, transparent 1px), linear-gradient(90deg, rgba(79,216,255,0.5) 1px, transparent 1px)",
        backgroundSize: "24px 24px",
      }}
    />
  );
}
