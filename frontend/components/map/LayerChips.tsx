"use client";

import { usePreferences } from "@/components/layout/PreferencesProvider";
import { BUILDING_TYPE_COLOR } from "@/lib/map/geometry";
import type { BuildingType } from "@/lib/types";
import type { MapLayers } from "./types";

export const toggleChip = (on: boolean) =>
  `rounded-full border-none px-3 py-1.5 text-xs ${on ? "bg-accent-soft text-accent" : "bg-surface-2 text-ink-3"}`;

type Props = {
  layers: MapLayers;
  /** Only types that occur among this campus's buildings get a chip. */
  presentTypes: BuildingType[];
  onToggleType: (type: BuildingType) => void;
  onToggle: (layer: Exclude<keyof MapLayers, "types">) => void;
};

export function LayerChips({ layers, presentTypes, onToggleType, onToggle }: Props) {
  const { t } = usePreferences();
  return (
    <div className="mb-3 flex flex-wrap gap-[7px]">
      {presentTypes.map((type) => {
        const on = layers.types[type];
        return (
          <button
            key={type}
            onClick={() => onToggleType(type)}
            className={`flex items-center gap-1.5 rounded-full border-none bg-surface-2 px-3 py-1.5 text-xs ${on ? "text-ink-2" : "text-ink-3 opacity-50"}`}
          >
            <span className="size-[7px] rounded-sm" style={{ background: BUILDING_TYPE_COLOR[type], opacity: on ? 1 : 0.4 }} />
            {t.map.types[type]}
          </button>
        );
      })}
      {presentTypes.length > 0 && <span className="mx-1 my-0.5 w-px bg-line" />}
      <button onClick={() => onToggle("pins")} className={toggleChip(layers.pins)}>
        {t.map.showPins}
      </button>
      <button onClick={() => onToggle("unconfirmedPins")} className={toggleChip(layers.unconfirmedPins)}>
        {t.tierToggle}
      </button>
    </div>
  );
}
