import type { TimeState } from "@/types";
import { isDaytime } from "@/types";
import { EventBus } from "./EventBus";

/**
 * Client-side clock. The backend simulation is authoritative (it keeps
 * ticking Scout's schedule even between client renders); this manager just
 * mirrors the latest `time:tick` broadcast from the WebSocket and,
 * between server ticks, interpolates locally so the HUD clock doesn't look
 * frozen. See backend/app/sim.py for the authoritative tick loop.
 */
export class TimeManager {
  private static _time: TimeState = { day: 1, hour: 8, minute: 0 };
  private static localTickHandle: number | null = null;

  static get current(): TimeState {
    return this._time;
  }

  static get isDay(): boolean {
    return isDaytime(this._time);
  }

  /** Called when an authoritative tick arrives from the backend over WebSocket. */
  static setFromServer(time: TimeState): void {
    this._time = time;
    EventBus.emit("time:tick", this._time);
  }

  /** Starts a local ~1-minute-per-2s ticker as a smoothing fallback while offline. */
  static startLocalFallback(): void {
    if (this.localTickHandle !== null) return;
    this.localTickHandle = window.setInterval(() => {
      let { day, hour, minute } = this._time;
      minute += 1;
      if (minute >= 60) {
        minute = 0;
        hour += 1;
      }
      if (hour >= 24) {
        hour = 0;
        day += 1;
      }
      this._time = { day, hour, minute };
      EventBus.emit("time:tick", this._time);
    }, 2000);
  }

  static stopLocalFallback(): void {
    if (this.localTickHandle !== null) {
      window.clearInterval(this.localTickHandle);
      this.localTickHandle = null;
    }
  }

  static formatClock(time: TimeState = this._time): string {
    const h = time.hour.toString().padStart(2, "0");
    const m = time.minute.toString().padStart(2, "0");
    return `Day ${time.day} — ${h}:${m}`;
  }
}
