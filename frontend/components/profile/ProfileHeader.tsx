"use client";

import { usePreferences } from "@/components/layout/PreferencesProvider";
import type { ProfileUniversity } from "@/lib/types";

type Props = {
  university: ProfileUniversity;
  generatedInMs: number;
  stats: { photos: number; verified: number; likely: number; hidden: number };
  /** Guide block on the right (mascot + greeting). */
  aside?: React.ReactNode;
};

export function ProfileHeader({ university: u, generatedInMs, stats, aside }: Props) {
  const { t, lang } = usePreferences();
  const place = lang === "en" ? `${u.city}, ${u.country}` : `${u.city_ru ?? u.city}, ${u.country_ru ?? u.country}`;
  const statItems = [
    { value: stats.photos, label: t.statPhotos, color: "var(--ink)" },
    { value: stats.verified, label: t.statVerified, color: "var(--ok)" },
    { value: stats.likely, label: t.statLikely, color: "var(--warn)" },
    { value: stats.hidden, label: t.statHidden, color: "var(--mute)" },
  ];

  return (
    <div className="flex flex-wrap items-start gap-6 border-b border-line pb-[22px]">
      <div className="min-w-0 flex-[1_1_380px]">
        <h1 className="mb-2.5 text-[clamp(28px,3.4vw,40px)] font-medium leading-[1.05] tracking-[-0.035em]">{u.name}</h1>
        <div className="flex flex-wrap items-center gap-3.5 text-sm text-ink-2">
          <span>
            {u.flag} {place}
          </span>
          <a href={u.website} target="_blank" rel="noreferrer">
            {u.website.replace(/^https?:\/\//, "")}
          </a>
          <span className="font-mono text-xs text-ink-3">
            {t.genIn} {(generatedInMs / 1000).toFixed(1)} {t.sec}
          </span>
        </div>
      </div>
      <div className="flex flex-wrap items-baseline gap-2.5 font-mono text-[12.5px] text-ink-3">
        {statItems.map((s) => (
          <span key={s.label}>
            <span style={{ color: s.color }}>{s.value}</span> {s.label}
          </span>
        ))}
      </div>
      {aside}
    </div>
  );
}
