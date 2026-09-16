import type { Dict } from "@/lib/i18n";
import type { Evidence, Tier } from "@/lib/types";

export const EVIDENCE_ICON: Record<Evidence["type"], string> = {
  geo: "📍",
  category: "📁",
  text: "🏷",
  vision: "👁",
  missing: "⚠",
};

export const evidenceLabel = (e: Evidence, lang: "ru" | "en") => (lang === "en" && e.label_en ? e.label_en : e.label);

// Tier vocabulary: color is always paired with an icon and a text label.
export function tierMeta(tier: Tier, t: Dict) {
  if (tier === "verified") return { color: "var(--ok)", soft: "var(--ok-soft)", icon: "🛡", label: t.verified };
  if (tier === "likely") return { color: "var(--warn)", soft: "var(--warn-soft)", icon: "✓", label: t.likely };
  return { color: "var(--mute)", soft: "var(--mute-soft)", icon: "?", label: t.unconfirmed };
}
