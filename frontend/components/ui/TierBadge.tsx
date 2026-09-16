"use client";

import { usePreferences } from "@/components/layout/PreferencesProvider";
import { tierMeta } from "@/lib/tiers";
import type { Tier } from "@/lib/types";

type Variant = "card" | "panel" | "thumb" | "pin";

const VARIANTS: Record<Variant, string> = {
  card: "gap-[5px] rounded-full px-[9px] py-1 text-[11px]",
  panel: "gap-1.5 rounded-[7px] border px-2.5 py-[5px] text-xs",
  thumb: "gap-1 rounded-[5px] px-1.5 py-[3px] text-[10px]",
  pin: "gap-[5px] rounded-md px-2 py-1 text-[11px]",
};

export function TierBadge({
  tier,
  confidence,
  variant = "card",
  showLabel = true,
  className = "",
}: {
  tier: Tier;
  confidence?: number;
  variant?: Variant;
  showLabel?: boolean;
  className?: string;
}) {
  const { t } = usePreferences();
  const meta = tierMeta(tier, t);
  const text = [showLabel ? meta.label : null, confidence !== undefined ? `${confidence}%` : null]
    .filter(Boolean)
    .join(" ");

  return (
    <div
      className={`flex items-center font-medium ${VARIANTS[variant]} ${className}`}
      style={{ background: meta.soft, color: meta.color, borderColor: meta.color }}
    >
      <span>{meta.icon}</span>
      <span>{text}</span>
    </div>
  );
}
