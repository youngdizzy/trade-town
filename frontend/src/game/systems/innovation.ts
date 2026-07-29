import type { InnovationTierName } from "@/types";

/**
 * v0.7 Feature 41 — Innovation Points display labels, mirrored from
 * backend/app/innovation.py's TIER_LABELS (the same "real content
 * mirrored client-side" convention founders.ts/careerLevels.ts already
 * established). The points/tier themselves are always server-computed —
 * this only supplies the human-readable name for each real tier.
 */
export const INNOVATION_TIER_LABEL: Record<InnovationTierName, string> = {
  research_contributor: "Research Contributor",
  research_specialist: "Research Specialist",
  innovation_leader: "Innovation Leader",
  chief_innovator: "Chief Innovator",
  legendary_innovator: "Legendary Innovator",
};
