"use client";

import { usePreferences } from "@/components/layout/PreferencesProvider";
import type { Profile } from "@/lib/types";

type Props = {
  profile: Profile;
  onOpenMap: () => void;
};

export function AboutSection({ profile, onOpenMap }: Props) {
  const { t, lang } = usePreferences();
  const { summary, university } = profile;

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

      <div onClick={onOpenMap} className="cursor-pointer">
        <div className="ph-grid relative flex h-[150px] items-center justify-center overflow-hidden rounded-[18px] [--g:20px]">
          <div className="h-[72px] w-[110px] rounded-md border-[1.5px] border-dashed border-accent bg-accent-soft opacity-85" />
        </div>
        <div className="flex justify-between gap-3 pt-[9px] text-[12.5px] text-ink-3">
          <span>{t.distance}</span>
          <span className="font-mono text-ink-2">
            {university.distance_to_center_km === null ? "—" : `${university.distance_to_center_km.toFixed(1)} ${t.km}`}
          </span>
        </div>
      </div>
    </div>
  );
}
