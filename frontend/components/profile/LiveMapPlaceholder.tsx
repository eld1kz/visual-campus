"use client";

import { usePreferences } from "@/components/layout/PreferencesProvider";
import type { ProfileUniversity } from "@/lib/types";

/** Live profile «Карта» section: no demo map, only the campus facts the sources actually returned. */
export function LiveMapPlaceholder({ university: u }: { university: ProfileUniversity }) {
  const { t } = usePreferences();
  const facts = [
    u.campus_area_km2 != null && { label: t.map.area, value: `${u.campus_area_km2.toFixed(2)} ${t.km}²` },
    u.distance_to_center_km != null && { label: t.distance, value: `${u.distance_to_center_km.toFixed(1)} ${t.km}` },
    u.lat != null && u.lng != null && { label: t.live.coords, value: `${u.lat.toFixed(4)}, ${u.lng.toFixed(4)}` },
  ].filter((f): f is { label: string; value: string } => Boolean(f));

  return (
    <div className="rounded-[20px] bg-surface-2 p-[38px]">
      <div className="mb-2 text-base font-medium">{t.live.mapLater}</div>
      <div className="mb-4 text-[13px] text-ink-3">{facts.length || u.osm_url ? t.live.mapLaterBody : t.live.noMapFacts}</div>
      {facts.length > 0 && (
        <div className="mb-3 flex max-w-[420px] flex-col">
          {facts.map((f) => (
            <div key={f.label} className="flex justify-between gap-3 border-b border-line py-[7px] text-[13px]">
              <span className="text-ink-3">{f.label}</span>
              <span className="font-mono text-ink-2">{f.value}</span>
            </div>
          ))}
        </div>
      )}
      {u.osm_url && (
        <a href={u.osm_url} target="_blank" rel="noreferrer" className="text-[13px]">
          {t.live.openOsm} ↗
        </a>
      )}
    </div>
  );
}
