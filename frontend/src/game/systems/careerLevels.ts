import type { AgentKnowledgeState, KnowledgeLevel } from "@/types";

/**
 * v0.7 Feature 40 — "Career Level" + "Company Major." The backend's
 * academy.py already tracks one real, monotonically-growing knowledge
 * level per agent (KnowledgeLevel — 7 tiers, novice through mentor, see
 * that module's docstring for exactly what earns each point). Rather than
 * inventing a second progression system for the brief's Student-through-
 * Legend ladder, this just relabels those same 7 real tiers.
 */
const CAREER_LEVEL_LABEL: Record<KnowledgeLevel, string> = {
  novice: "Student",
  beginner: "Junior",
  intermediate: "Professional",
  advanced: "Senior",
  expert: "Expert",
  master: "Master",
  mentor: "Legend",
};

export function careerLevelLabel(level: KnowledgeLevel): string {
  return CAREER_LEVEL_LABEL[level];
}

// "Company Major" is the honest analogue of a declared specialization: an
// agent's real KNOWLEDGE_BRANCH (backend/app/academy.py) once its points
// have actually sustained a specialization, not from day one. Gated at
// "advanced" (tier 3, this ladder's "Senior") — below that there's no real
// signal yet, so companyMajor() returns null (an honest empty state)
// rather than a fabricated placeholder.
const GRADUATED_TIER = 3;

export function companyMajor(state: AgentKnowledgeState): string | null {
  if (state.tier < GRADUATED_TIER) return null;
  return `Bachelor of ${state.branch}`;
}
