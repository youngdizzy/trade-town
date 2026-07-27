import { GameCanvas } from "@/ui/components/GameCanvas";
import { TopStatusBar } from "@/ui/components/TopStatusBar";
import { BottomToolbar } from "@/ui/components/BottomToolbar";
import { DialogueBox } from "@/ui/components/DialogueBox";
import { SettingsMenu } from "@/ui/components/SettingsMenu";
import { PauseMenu } from "@/ui/components/PauseMenu";
import { DebugOverlay } from "@/ui/components/DebugOverlay";
import { BrainRoomHud } from "@/ui/components/BrainRoomHud";
import { MarketObservatoryHud } from "@/ui/components/MarketObservatoryHud";
import { Newspaper } from "@/ui/components/Newspaper";
import { CompanyMemory } from "@/ui/components/CompanyMemory";
import { CoachDashboard } from "@/ui/components/CoachDashboard";
import { CommandCenter } from "@/ui/components/CommandCenter/CommandCenter";
import { TradeOutcomePopup } from "@/ui/components/TradeOutcomePopup";

export default function App() {
  return (
    <div className="relative h-screen w-screen overflow-hidden bg-black">
      <GameCanvas />
      <TopStatusBar />
      <DebugOverlay />
      <BrainRoomHud />
      <MarketObservatoryHud />
      <DialogueBox />
      <Newspaper />
      <CompanyMemory />
      <CoachDashboard />
      <BottomToolbar />
      <PauseMenu />
      <SettingsMenu />
      <CommandCenter />
      <TradeOutcomePopup />
    </div>
  );
}
