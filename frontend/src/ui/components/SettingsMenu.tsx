import { useGameStore } from "@/ui/hooks/useGameStore";
import { SettingsManager } from "@/game/systems/SettingsManager";
import { SaveManager } from "@/game/systems/SaveManager";
import { EventBus } from "@/game/systems/EventBus";

export function SettingsMenu() {
  const { settingsOpen, settings } = useGameStore();
  if (!settingsOpen) return null;

  const close = () => EventBus.emit("ui:settings", { open: false });

  return (
    <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/60 font-pixel text-[11px]">
      <div className="w-80 rounded bg-panel p-5 text-parchment shadow-pixel">
        <h2 className="mb-4 text-center text-gold">Settings</h2>

        <SliderRow
          label="Music Volume"
          value={settings.musicVolume}
          onChange={(v) => SettingsManager.update({ musicVolume: v })}
        />
        <SliderRow
          label="SFX Volume"
          value={settings.sfxVolume}
          onChange={(v) => SettingsManager.update({ sfxVolume: v })}
        />

        <div className="mb-3 flex items-center justify-between">
          <span>Autosave every</span>
          <select
            className="rounded bg-panelLight px-2 py-1 text-parchment"
            value={settings.autosaveIntervalSec}
            onChange={(e) => {
              const autosaveIntervalSec = Number(e.target.value);
              SettingsManager.update({ autosaveIntervalSec });
              SaveManager.startAutosave();
            }}
          >
            <option value={30}>30s</option>
            <option value={60}>60s</option>
            <option value={120}>2 min</option>
            <option value={300}>5 min</option>
          </select>
        </div>

        <div className="mb-4 flex items-center justify-between">
          <span>Show FPS</span>
          <input
            type="checkbox"
            checked={settings.showFps}
            onChange={(e) => SettingsManager.update({ showFps: e.target.checked })}
          />
        </div>

        <button
          type="button"
          onClick={close}
          className="w-full rounded bg-gold py-2 text-ink transition-colors hover:brightness-110"
        >
          Close
        </button>
      </div>
    </div>
  );
}

function SliderRow({ label, value, onChange }: { label: string; value: number; onChange: (v: number) => void }) {
  return (
    <div className="mb-3">
      <div className="mb-1 flex justify-between">
        <span>{label}</span>
        <span className="opacity-70">{Math.round(value * 100)}%</span>
      </div>
      <input
        type="range"
        min={0}
        max={1}
        step={0.05}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full accent-gold"
      />
    </div>
  );
}
