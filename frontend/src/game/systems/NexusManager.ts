import type { MeetingState, NewsItem, Task } from "@/types";
import { EventBus } from "./EventBus";

/**
 * Frontend mirror of the backend's NexusManager — holds the company-wide
 * state (tasks, whiteboards, meeting status, news feed) that isn't tied to
 * any single agent. Diffs incoming server snapshots against the previous
 * one to emit the discrete events other systems (UI, dialogue) care about,
 * the same way NPCManager does per-agent.
 */
export class NexusManager {
  private static tasks: Task[] = [];
  private static whiteboards: Record<string, string> = {};
  private static meeting: MeetingState = { active: false, participants: [] };
  private static news: NewsItem[] = [];

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

  static applyServerUpdate(update: { tasks: Task[]; whiteboards: Record<string, string>; meeting: MeetingState; news: NewsItem[] }): void {
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
  }

  static loadFromSave(save: { tasks: Task[]; whiteboards: Record<string, string>; meeting: MeetingState; news: NewsItem[] }): void {
    this.tasks = save.tasks;
    this.whiteboards = save.whiteboards;
    this.meeting = save.meeting;
    this.news = save.news;
  }
}
