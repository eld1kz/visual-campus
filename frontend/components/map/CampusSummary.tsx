"use client";

import { usePreferences } from "@/components/layout/PreferencesProvider";
import { BUILDING_TYPES, BUILDING_TYPE_COLOR } from "@/lib/map/geometry";
import type { CampusMap } from "@/lib/types";

type Props = {
  data: CampusMap;
  buildingQuery: string;
  selectedBuildingId: string | null;
  onSelectBuilding: (id: string) => void;
};

/** Default side panel: key numbers and buildings grouped by type. */
export function CampusSummary({ data, buildingQuery, selectedBuildingId, onSelectBuilding }: Props) {
  const { t } = usePreferences();
  const inside = data.buildings.filter((b) => b.inside_campus);
  const query = buildingQuery.toLowerCase();
  const rows = [
    { label: t.map.area, value: `${data.campus.area_km2.toFixed(2)} ${t.km}²` },
    { label: t.map.buildingsFound, value: String(inside.length) },
    { label: t.map.toCenter, value: `${data.campus.distance_to_center_km.toFixed(1)} ${t.km}` },
  ];

  const groups = BUILDING_TYPES.map((type) => {
    const all = inside.filter((b) => b.type === type);
    return { type, count: all.length, items: all.filter((b) => !query || b.name.toLowerCase().includes(query)) };
  }).filter((g) => g.count > 0 && (g.items.length > 0 || !query));

  return (
    <>
      <div className="flex flex-col gap-[7px]">
        {rows.map((r) => (
          <div key={r.label} className="flex justify-between text-[13px]">
            <span className="text-ink-3">{r.label}</span>
            <span className="font-mono">{r.value}</span>
          </div>
        ))}
      </div>
      <div className="flex flex-col gap-4">
        {groups.map((g) => (
          <div key={g.type}>
            <div className="mb-1.5 flex items-center gap-2">
              <span className="size-2 rounded-sm" style={{ background: BUILDING_TYPE_COLOR[g.type] }} />
              <span className="text-[12.5px] font-medium">{t.map.types[g.type]}</span>
              <span className="ml-auto font-mono text-[11px] text-ink-3">{g.count}</span>
            </div>
            {g.items.map((b) => (
              <button
                key={b.id}
                onClick={() => onSelectBuilding(b.id)}
                className={`flex w-full items-center gap-2 border-x-0 border-b border-t-0 border-line bg-transparent py-[7px] text-left text-[13px] ${
                  b.id === selectedBuildingId ? "text-accent" : "text-ink-2"
                }`}
              >
                <span>{b.name}</span>
                <span className="ml-auto font-mono text-[10.5px] text-ink-3">{b.photo_ids.length || ""}</span>
              </button>
            ))}
          </div>
        ))}
      </div>
    </>
  );
}
