import { GameCanvas } from "@/ui/components/GameCanvas";
import { TopStatusBar } from "@/ui/components/TopStatusBar";
import { GlobalStatusBar } from "@/ui/components/GlobalStatusBar";
import { QuickActionDock } from "@/ui/components/QuickActionDock";
import { BottomToolbar } from "@/ui/components/BottomToolbar";
import { DialogueBox } from "@/ui/components/DialogueBox";
import { InteractionPrompt } from "@/ui/components/InteractionPrompt";
import { SettingsMenu } from "@/ui/components/SettingsMenu";
import { PauseMenu } from "@/ui/components/PauseMenu";
import { DebugOverlay } from "@/ui/components/DebugOverlay";
import { BrainRoomHud } from "@/ui/components/BrainRoomHud";
import { MarketObservatoryHud } from "@/ui/components/MarketObservatoryHud";
import { Newspaper } from "@/ui/components/Newspaper";
import { CompanyMemory } from "@/ui/components/CompanyMemory";
import { CoachDashboard } from "@/ui/components/CoachDashboard";
import { CommandCenter } from "@/ui/components/CommandCenter/CommandCenter";
import { CampusMap } from "@/ui/components/CampusMap/CampusMap";
import { ExecutiveVoting } from "@/ui/components/CommandCenter/ExecutiveVoting";
import { CyberNotifications } from "@/ui/components/CommandCenter/CyberNotifications";
import { TradeOutcomeBanner } from "@/ui/components/TradeOutcomeBanner";
import { BreakthroughMoment } from "@/ui/components/BreakthroughMoment";
import { EmergencyStopConfirm } from "@/ui/components/EmergencyStopConfirm";

export default function App() {
  return (
    <div className="relative h-screen w-screen overflow-hidden bg-black">
      <GameCanvas />
      <TopStatusBar />
      <GlobalStatusBar />
      <DebugOverlay />
      <BrainRoomHud />
      <MarketObservatoryHud />
      <DialogueBox />
      <InteractionPrompt />
      <Newspaper />
      <CompanyMemory />
      <CoachDashboard />
      <BottomToolbar />
      <QuickActionDock />
      <PauseMenu />
      <SettingsMenu />
      <CommandCenter />
      <CampusMap />
      <ExecutiveVoting />
      <CyberNotifications />
      <TradeOutcomeBanner />
      <BreakthroughMoment />
      <EmergencyStopConfirm />
    </div>
  );
}
