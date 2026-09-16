import type { Dict } from "@/lib/i18n";
import type { Tier } from "@/lib/types";

// Tier vocabulary: color is always paired with an icon and a text label.
export function tierMeta(tier: Tier, t: Dict) {
  if (tier === "verified") return { color: "var(--ok)", soft: "var(--ok-soft)", icon: "🛡", label: t.verified };
  if (tier === "likely") return { color: "var(--warn)", soft: "var(--warn-soft)", icon: "✓", label: t.likely };
  return { color: "var(--mute)", soft: "var(--mute-soft)", icon: "?", label: t.unconfirmed };
}
