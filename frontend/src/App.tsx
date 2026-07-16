import { GameCanvas } from "@/ui/components/GameCanvas";
import { TopStatusBar } from "@/ui/components/TopStatusBar";
import { BottomToolbar } from "@/ui/components/BottomToolbar";
import { DialogueBox } from "@/ui/components/DialogueBox";
import { SettingsMenu } from "@/ui/components/SettingsMenu";
import { PauseMenu } from "@/ui/components/PauseMenu";
import { DebugOverlay } from "@/ui/components/DebugOverlay";

export default function App() {
  return (
    <div className="relative h-screen w-screen overflow-hidden bg-black">
      <GameCanvas />
      <TopStatusBar />
      <DebugOverlay />
      <DialogueBox />
      <BottomToolbar />
      <PauseMenu />
      <SettingsMenu />
    </div>
  );
}
