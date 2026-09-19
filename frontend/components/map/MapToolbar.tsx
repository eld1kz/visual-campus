"use client";

import { usePreferences } from "@/components/layout/PreferencesProvider";
import type { MapMode } from "./types";

type Props = {
  mode: MapMode;
  onMode: (mode: MapMode) => void;
  buildingQuery: string;
  onBuildingQuery: (value: string) => void;
  onRecenter: () => void;
};

const MODES: MapMode[] = ["2d", "3d"];

export function MapToolbar({ mode, onMode, buildingQuery, onBuildingQuery, onRecenter }: Props) {
  const { t } = usePreferences();
  return (
    <div className="mb-3.5 flex flex-wrap items-center gap-2.5">
      <div className="flex gap-0.5">
        {MODES.map((m, i) => (
          <button
            key={m}
            onClick={() => onMode(m)}
            className={`rounded-full border-none px-[15px] py-2 text-[12.5px] ${
              mode === m ? "bg-ink font-medium text-bg" : "bg-transparent text-ink-3"
            }`}
          >
            {t.map.modes[i]}
          </button>
        ))}
      </div>
      <input
        value={buildingQuery}
        onChange={(e) => onBuildingQuery(e.target.value)}
        placeholder={t.map.findBuilding}
        className="min-w-0 flex-[1_1_200px] rounded-full border border-transparent bg-surface-2 px-3.5 py-[9px] text-[13px] text-ink outline-none focus:border-accent focus:bg-surface"
      />
      <button
        onClick={onRecenter}
        className="rounded-full border-none bg-surface-2 px-3.5 py-[9px] text-[12.5px] text-ink-2 hover:text-accent"
      >
        {t.map.recenter}
      </button>
    </div>
  );
}
