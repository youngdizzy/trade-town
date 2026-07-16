import { useEffect, useRef } from "react";
import { GameManager } from "@/game/systems/GameManager";
import { gameSocket } from "@/net/socket";
import { SaveManager } from "@/game/systems/SaveManager";

/** Mounts the Phaser.Game instance into a container div and wires up networking + autosave for the app's lifetime. */
export function GameCanvas() {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    GameManager.bootstrap(el);
    gameSocket.connect();
    SaveManager.startAutosave();

    return () => {
      SaveManager.stopAutosave();
      gameSocket.disconnect();
      GameManager.destroy();
    };
  }, []);

  return <div ref={containerRef} id="game-root" className="absolute inset-0 h-full w-full" />;
}
