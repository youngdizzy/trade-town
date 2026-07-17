import type { MeetingMinutes, MeetingState, MemoryRecord, NewsItem, ResearchItem, Task, WatchlistEntry } from "@/types";
import { EventBus } from "./EventBus";

interface NexusSnapshot {
  tasks: Task[];
  whiteboards: Record<string, string>;
  meeting: MeetingState;
  news: NewsItem[];
  research: ResearchItem[];
  watchlist: WatchlistEntry[];
  memory: MemoryRecord[];
  meetingMinutes: MeetingMinutes[];
}

/**
 * Frontend mirror of the backend's NexusManager — holds the company-wide
 * state (tasks, whiteboards, meeting status, news feed, research queue,
 * watchlist, company memory, meeting minutes) that isn't tied to any
 * single agent. Diffs incoming server snapshots against the previous one
 * to emit the discrete events other systems (UI, dialogue) care about,
 * the same way NPCManager does per-agent.
 */
export class NexusManager {
  private static tasks: Task[] = [];
  private static whiteboards: Record<string, string> = {};
  private static meeting: MeetingState = { active: false, participants: [], discussion: [] };
  private static news: NewsItem[] = [];
  private static research: ResearchItem[] = [];
  private static watchlist: WatchlistEntry[] = [];
  private static memory: MemoryRecord[] = [];
  private static meetingMinutes: MeetingMinutes[] = [];

  static getTasks(): Task[] {
    return this.tasks;
  }

  static getWhiteboard(boardId: string): string {
    return this.whiteboards[boardId] ?? "";
  }

  static getAllWhiteboards(): Record<string, string> {
    return this.whiteboards;
  }

  static getMeeting(): MeetingState {
    return this.meeting;
  }

  static getNews(): NewsItem[] {
    return this.news;
  }

  static getResearch(): ResearchItem[] {
    return this.research;
  }

  static getWatchlist(): WatchlistEntry[] {
    return this.watchlist;
  }

  static getMemory(): MemoryRecord[] {
    return this.memory;
  }

  static getMeetingMinutes(): MeetingMinutes[] {
    return this.meetingMinutes;
  }

  static applyServerUpdate(update: NexusSnapshot): void {
    for (const task of update.tasks) {
      const previous = this.tasks.find((t) => t.id === task.id);
      if (!previous) EventBus.emit("task:assigned", task);
      else if (previous.status !== "completed" && task.status === "completed") EventBus.emit("task:completed", task);
    }
    this.tasks = update.tasks;

    for (const [boardId, text] of Object.entries(update.whiteboards)) {
      if (this.whiteboards[boardId] !== text) EventBus.emit("whiteboard:updated", { boardId, text });
    }
    this.whiteboards = update.whiteboards;

    if (!this.meeting.active && update.meeting.active) EventBus.emit("meeting:started", update.meeting);
    else if (this.meeting.active && !update.meeting.active) EventBus.emit("meeting:ended", undefined);
    this.meeting = update.meeting;

    if (update.news.length !== this.news.length) EventBus.emit("news:updated", update.news);
    this.news = update.news;

    for (const item of update.research) {
      const previous = this.research.find((r) => r.id === item.id);
      if (previous && previous.status !== "completed" && item.status === "completed") {
        EventBus.emit("research:completed", item);
      }
    }
    if (update.research !== this.research) EventBus.emit("research:updated", update.research);
    this.research = update.research;

    if (update.watchlist !== this.watchlist) EventBus.emit("watchlist:updated", update.watchlist);
    this.watchlist = update.watchlist;

    if (update.memory.length !== this.memory.length) EventBus.emit("memory:updated", update.memory);
    this.memory = update.memory;

    if (update.meetingMinutes.length !== this.meetingMinutes.length) {
      const newest = update.meetingMinutes[update.meetingMinutes.length - 1];
      if (newest) EventBus.emit("meeting:minutesRecorded", newest);
    }
    this.meetingMinutes = update.meetingMinutes;
  }

  static loadFromSave(save: NexusSnapshot): void {
    this.tasks = save.tasks;
    this.whiteboards = save.whiteboards;
    this.meeting = save.meeting;
    this.news = save.news;
    this.research = save.research;
    this.watchlist = save.watchlist;
    this.memory = save.memory;
    this.meetingMinutes = save.meetingMinutes;
  }
}
