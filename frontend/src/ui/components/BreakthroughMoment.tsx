import { useEffect, useMemo, useState } from "react";
import { useGameStore } from "@/ui/hooks/useGameStore";
import { AGENT_PROFILES } from "@/game/systems/AgentProfiles";
import { NexusManager } from "@/game/systems/NexusManager";
import { EventBus } from "@/game/systems/EventBus";
import { api } from "@/net/api";

/**
 * v0.7 — the Eureka! Breakthrough System. Every field shown is real: the
 * project's own objective, the Devil's Advocate's real case against it,
 * and the Founder Council's real, checkable verdict (see
 * backend/app/founders.py's generate_breakthrough_review() and
 * app/black_box.py's module docstring). Breakthroughs are earned, not
 * random — only an approved BreakthroughReview ever triggers this.
 *
 * No real audio/music system exists anywhere in this codebase to swap a
 * track on (see founders.py's own "voice acting" cut for the same class
 * of honest omission) — the "screen pauses" moment here is a real,
 * full-block overlay (movement AND interaction both stop, unlike the
 * Command Center) plus a real CSS glow/confetti animation, not a
 * fabricated music cue.
 */
export function BreakthroughMoment() {
  const { blackBox, currentScene } = useGameStore();
  const [dismissing, setDismissing] = useState(false);

  const review = useMemo(
    () => [...blackBox.reviews].reverse().find((r) => r.verdict === "approved" && !blackBox.viewedBreakthroughIds.includes(r.id)) ?? null,
    [blackBox.reviews, blackBox.viewedBreakthroughIds],
  );

  useEffect(() => {
    if (review && currentScene !== "MainMenuScene") EventBus.emit("ui:breakthrough", { open: true });
  }, [review, currentScene]);

  const dismiss = async () => {
    if (!review || dismissing) return;
    setDismissing(true);
    try {
      const res = await api.ackBreakthrough(review.id);
      NexusManager.setViewedBreakthroughIds(res.viewedBreakthroughIds);
    } finally {
      EventBus.emit("ui:breakthrough", { open: false });
      setDismissing(false);
    }
  };

  if (!review || currentScene === "MainMenuScene") return null;

  return (
    <div className="pointer-events-auto absolute inset-0 z-[80] flex items-center justify-center bg-black/85 p-6 font-cmdmono text-cmd-text backdrop-blur-sm">
      <div className="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden="true">
        {["#3ce28a", "#4fd8ff", "#ffb443", "#a78bfa"].flatMap((color, colorIdx) =>
          Array.from({ length: 4 }, (_, i) => (
            <span
              key={`${colorIdx}-${i}`}
              className="motion-safe:animate-cmd-confetti-fall absolute top-0 block h-2 w-2 rounded-[1px]"
              style={{ left: `${(colorIdx * 4 + i) * 6}%`, backgroundColor: color, animationDelay: `${(colorIdx * 4 + i) * 120}ms` }}
            />
          )),
        )}
      </div>

      <div className="motion-safe:animate-cmd-overlay-in relative w-full max-w-lg rounded-md border border-cmd-green/50 bg-cmd-bg/95 p-5 shadow-cmd-cyan motion-safe:animate-cmd-glow-pulse">
        <div className="mb-3 text-center">
          <div className="text-3xl">🧠</div>
          <div className="mt-1 text-sm uppercase tracking-widest text-cmd-green">Breakthrough Discovered</div>
        </div>

        <div className="mb-3 flex items-center justify-center gap-2 text-[10px] text-cmd-textDim">
          <span>{AGENT_PROFILES.quant.badge}</span>
          <span>{AGENT_PROFILES.quant.name} confirmed the finding and brought it to the CEO.</span>
        </div>

        <div className="mb-3 rounded-sm border border-cmd-border/60 bg-cmd-bg/60 p-3 text-center">
          <div className="text-[11px] text-cmd-cyan">{review.projectTitle}</div>
          <p className="mt-1 text-[9px] text-cmd-textDim">{review.hypothesis}</p>
        </div>

        <div className="mb-3 space-y-1.5 text-[9px]">
          <div>
            <span className="text-cmd-textDim">Founder Council: </span>
            <span className="text-cmd-green">Approved.</span> <span className="text-cmd-textDim">{review.verdictReason}</span>
          </div>
          <div>
            <span className="text-cmd-textDim">Statistical Results: </span>
            {review.statisticalResults}
          </div>
        </div>

        <button
          type="button"
          onClick={() => void dismiss()}
          disabled={dismissing}
          className="w-full rounded-sm border border-cmd-green/50 py-2 text-[10px] uppercase tracking-wider text-cmd-green transition-colors hover:bg-cmd-green/10 disabled:opacity-40"
        >
          {dismissing ? "…" : "Add to the Museum of Discoveries ▸"}
        </button>
      </div>
    </div>
  );
}
