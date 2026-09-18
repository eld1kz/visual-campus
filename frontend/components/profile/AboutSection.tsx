"use client";

import { usePreferences } from "@/components/layout/PreferencesProvider";
import type { Profile } from "@/lib/types";
import { CityCenterMap } from "./CityCenterMap";

type Props = {
  profile: Profile;
  onOpenMap: () => void;
};

export function AboutSection({ profile, onOpenMap }: Props) {
  const { t, lang } = usePreferences();
  const { summary, university } = profile;
  const route = university.center_route;
  const minutes = (m: number) =>
    m < 60 ? `~${m} ${t.minShort}` : `~${Math.floor(m / 60)} ${t.hourShort} ${m % 60} ${t.minShort}`;
  const rows = [
    university.distance_to_center_km != null && [t.straightLine, `${university.distance_to_center_km.toFixed(1)} ${t.km}`],
    route && [t.byRoad, `${route.road_km.toFixed(1)} ${t.km}`],
    route && [t.byCar, minutes(route.drive_min)],
    route && [t.onFoot, minutes(route.walk_min)],
  ].filter(Boolean) as [string, string][];

  return (
    <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,320px),1fr))] gap-7 pb-[34px] pt-[30px]">
      <div>
        <p className="mb-3 max-w-[64ch] text-[15px] leading-[1.7] text-pretty text-ink">
          {lang === "en" && summary.text_en ? summary.text_en : summary.text}
          {summary.citations.map((c) => (
            <a key={c.n} href={c.url} target="_blank" rel="noreferrer" className="ml-px align-super text-xs">
              [{c.n}]
            </a>
          ))}
        </p>
        <div className="flex flex-col gap-1">
          {summary.citations.map((c) => (
            <div key={c.n} className="text-xs text-ink-3">
              [{c.n}]{" "}
              <a href={c.url} target="_blank" rel="noreferrer">
                {c.title}
              </a>
            </div>
          ))}
        </div>
      </div>

      <div>
        {university.city_center && university.lat != null ? (
          <CityCenterMap university={university} />
        ) : (
          <div className="ph-grid h-[190px] rounded-[18px] [--g:20px]" />
        )}
        <div onClick={onOpenMap} className="cursor-pointer pt-[9px] text-[12.5px] text-ink-3">
          <div className="mb-1 font-medium text-ink-2">
            {t.distance}
            {university.city_center ? ` · ${university.city_center.name}` : ""}
          </div>
          {rows.length === 0 ? (
            <div className="font-mono text-ink-2">—</div>
          ) : (
            rows.map(([label, value]) => (
              <div key={label} className="flex justify-between gap-3">
                <span>{label}</span>
                <span className="font-mono text-ink-2">{value}</span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
