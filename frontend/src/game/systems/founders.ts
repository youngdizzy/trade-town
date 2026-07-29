import type { FounderId } from "@/types";

/**
 * Static identity content for the Original Founders — mirrors
 * backend/app/founders.py's FOUNDER_QUOTES/FOUNDER_PHILOSOPHY/
 * FOUNDER_SPECIALTIES/FOUNDER_TEACHING_STYLE exactly (verbatim from the
 * brief). Never changes at runtime, so it's a plain frontend mirror the
 * same way Schedule.ts mirrors schedule.py, rather than a new API route
 * for static content.
 */
export const FOUNDER_QUOTES: Record<FounderId, readonly string[]> = {
  keystone: [
    "Protecting capital is the first victory.",
    "Discipline beats emotion.",
    "A trade avoided can be just as valuable as a trade taken.",
    "Great traders survive long enough to become great.",
  ],
  compass: ["Curiosity creates breakthroughs.", "Never stop asking why.", "Knowledge compounds.", "The best companies never stop learning."],
};

export const FOUNDER_PHILOSOPHY: Record<FounderId, string> = {
  keystone: "Protect the company first. Profit comes second.",
  compass: "Every mistake is an opportunity to improve.",
};

export const FOUNDER_SPECIALTIES: Record<FounderId, readonly string[]> = {
  keystone: ["Risk Management", "Capital Preservation", "Position Sizing", "Consistency", "Decision Frameworks", "Process Improvement"],
  compass: ["Research", "Education", "Critical Thinking", "Innovation", "Knowledge Systems", "Long-Term Improvement"],
};

export const FOUNDER_TEACHING_STYLE: Record<FounderId, string> = {
  keystone: "Teaches through questions, case studies, and reviewing mistakes. Rarely gives direct answers — guides employees toward discovering the correct reasoning themselves.",
  compass: "Encourages experimentation, discussion, and challenging assumptions. Rewards thoughtful questions more than quick answers.",
};

export const FOUNDER_IDS: readonly FounderId[] = ["keystone", "compass"];
