"use client";

import { usePreferences } from "@/components/layout/PreferencesProvider";
import { toggleChip } from "./LayerChips";
import type { MapDemoFlags } from "./types";

/** Prototype-only switches for edge states; drop once the map reads real data. */
export function DemoStateToggles({ flags, onToggle }: { flags: MapDemoFlags; onToggle: (flag: keyof MapDemoFlags) => void }) {
  const { t } = usePreferences();
  const items: { key: keyof MapDemoFlags; label: string }[] = [
    { key: "noPolygon", label: t.map.dsPolygon },
    { key: "noHeights", label: t.map.dsHeights },
    { key: "noPano", label: t.map.dsPano },
    { key: "no3d", label: t.map.ds3d },
  ];

  return (
    <div className="mt-1.5 border-t border-line pt-3.5">
      <div className="micro-label mb-2 text-[10px]">{t.map.demoStates}</div>
      <div className="flex flex-wrap gap-1.5">
        {items.map((item) => (
          <button key={item.key} onClick={() => onToggle(item.key)} className={toggleChip(flags[item.key])}>
            {item.label}
          </button>
        ))}
      </div>
    </div>
  );
}
