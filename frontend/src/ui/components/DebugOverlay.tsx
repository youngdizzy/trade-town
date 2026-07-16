import { useEffect, useRef } from "react";
import { useGameStore } from "@/ui/hooks/useGameStore";
import { GameManager } from "@/game/systems/GameManager";

/** Renders a live FPS + player-position readout when Settings > Show FPS is enabled. */
export function DebugOverlay() {
  const { settings } = useGameStore();
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!settings.showFps) return;
    let raf: number;
    const tick = () => {
      const game = GameManager.getInstance();
      if (ref.current && game) {
        const fps = Math.round(game.game.loop.actualFps);
        const { x, y, scene } = game.playerTransform;
        ref.current.textContent = `${fps} FPS — ${scene} (${Math.round(x)}, ${Math.round(y)})`;
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [settings.showFps]);

  if (!settings.showFps) return null;

  return (
    <div
      ref={ref}
      className="pointer-events-none absolute right-2 top-14 z-10 rounded bg-black/70 px-2 py-1 font-pixel text-[10px] text-bullish"
    />
  );
}
