import type { SettingsState } from "@/types";
import { EventBus } from "./EventBus";

const STORAGE_KEY = "tradetown:settings";

const DEFAULT_SETTINGS: SettingsState = {
  musicVolume: 0.5,
  sfxVolume: 0.7,
  autosaveIntervalSec: 60,
  showFps: false,
  operatingMode: "learning",
  companyPriority: "balanced",
  workMode: "work",
  ceoAcademyLearningMode: false,
  activeWeightProfile: "balanced_institutional",
  customDepartmentWeights: {},
};

/** Persists user preferences to localStorage and broadcasts changes on the EventBus. */
export class SettingsManager {
  private static _current: SettingsState = SettingsManager.loadFromStorage();

  static get current(): SettingsState {
    return this._current;
  }

  static update(partial: Partial<SettingsState>): SettingsState {
    this._current = { ...this._current, ...partial };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(this._current));
    EventBus.emit("settings:changed", this._current);
    return this._current;
  }

  static reset(): SettingsState {
    this._current = { ...DEFAULT_SETTINGS };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(this._current));
    EventBus.emit("settings:changed", this._current);
    return this._current;
  }

  private static loadFromStorage(): SettingsState {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return { ...DEFAULT_SETTINGS };
      const parsed = JSON.parse(raw) as Partial<SettingsState>;
      return { ...DEFAULT_SETTINGS, ...parsed };
    } catch {
      return { ...DEFAULT_SETTINGS };
    }
  }
}
