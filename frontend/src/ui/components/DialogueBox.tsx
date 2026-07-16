import { useEffect } from "react";
import { useGameStore } from "@/ui/hooks/useGameStore";
import { gameStore } from "@/state/gameStore";

export function DialogueBox() {
  const { dialogue } = useGameStore();

  useEffect(() => {
    if (!dialogue.open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.code === "Space" || e.code === "Enter" || e.code === "KeyE") {
        gameStore.advanceDialogue();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [dialogue.open]);

  if (!dialogue.open) return null;
  const line = dialogue.lines[dialogue.index] ?? "";

  return (
    <div className="pointer-events-none absolute bottom-20 left-0 right-0 flex justify-center font-pixel text-[12px]">
      <div
        role="button"
        tabIndex={0}
        onClick={() => gameStore.advanceDialogue()}
        className="pointer-events-auto max-w-lg cursor-pointer rounded border-2 border-gold bg-panel/95 px-5 py-4 text-parchment shadow-pixel"
      >
        <div className="mb-2 text-gold">{dialogue.speaker}</div>
        <div>{line}</div>
        <div className="mt-2 text-right text-[9px] opacity-50">
          {dialogue.index + 1 < dialogue.lines.length ? "[Space] Continue" : "[Space] Close"}
        </div>
      </div>
    </div>
  );
}
