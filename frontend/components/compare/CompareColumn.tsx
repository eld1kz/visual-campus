"use client";

import { usePreferences } from "@/components/layout/PreferencesProvider";
import type { DemoUniversity } from "@/lib/mock/profile";
import { CATEGORIES } from "@/lib/photos";

type Props = {
  university: DemoUniversity;
  stats: { verified: number; sources: string; byCategory: number[] };
};

export function CompareColumn({ university: u, stats }: Props) {
  const { t, lang } = usePreferences();
  const place = lang === "en" ? `${u.city}, ${u.country}` : `${u.city_ru}, ${u.country_ru}`;
  const rows = [
    { label: t.rowDistance, value: `${u.distance_to_center_km.toFixed(1)} ${t.km}` },
    { label: t.rowClimate, value: lang === "en" ? u.climate_en : u.climate },
    { label: t.rowVerified, value: String(stats.verified) },
    { label: t.rowSources, value: stats.sources },
  ];

  return (
    <div>
      <div className="pb-3.5">
        <div className="text-[19px] font-semibold tracking-[-0.01em]">{u.name}</div>
        <div className="mt-[3px] text-[13px] text-ink-2">
          {u.flag} {place}
        </div>
      </div>
      <div className="ph-grid relative flex h-[130px] items-center justify-center overflow-hidden rounded-[10px] [--g:18px]">
        <div className="h-[62px] w-24 rounded-md border-[1.5px] border-dashed border-accent bg-accent-soft" />
      </div>
      <div className="flex flex-col gap-[9px] border-b border-line py-4">
        {rows.map((r) => (
          <div key={r.label} className="flex justify-between gap-3 text-[13px]">
            <span className="text-ink-3">{r.label}</span>
            <span className="font-mono">{r.value}</span>
          </div>
        ))}
      </div>
      <div className="py-4">
        <div className="micro-label mb-2.5 text-[10.5px] tracking-[.07em]">{t.verifiedByCat}</div>
        <div className="flex flex-col gap-[9px]">
          {CATEGORIES.map((category, i) => {
            const count = stats.byCategory[i];
            return (
              <div key={category} className="flex flex-col gap-[5px]">
                <div className="flex justify-between text-[12.5px]">
                  <span>{t.tabs[i + 1]}</span>
                  <span className="font-mono text-ink-2">{count}</span>
                </div>
                <div className="h-1 rounded-sm bg-surface-2">
                  <div className="h-full rounded-sm bg-accent" style={{ width: `${Math.min(100, count * 10)}%` }} />
                </div>
                <div className="mt-0.5 flex gap-1.5">
                  {Array.from({ length: Math.min(3, count) }, (_, k) => (
                    <div key={k} className="ph-stripes h-[34px] flex-1 rounded-[5px] border border-line [--s:7px]" />
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
