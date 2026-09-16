"use client";

import { usePreferences } from "@/components/layout/PreferencesProvider";
import { Mascot } from "@/components/mascot/Mascot";
import { DemoDataPlate } from "@/components/ui/DemoDataPlate";
import { BRAND, NEUTRAL_BRAND } from "@/lib/mock/guide";
import { COMPARE_STATS, DEMO_UNIVERSITIES } from "@/lib/mock/profile";
import { CompareColumn } from "./CompareColumn";

export function CompareScreen() {
  const { t } = usePreferences();

  return (
    <div className="mx-auto max-w-[1100px] px-[22px] pb-[90px] pt-9">
      <DemoDataPlate className="mb-[22px]" />
      <h2 className="mb-[18px] text-[28px] font-semibold tracking-[-0.02em]">{t.compareTitle}</h2>

      <div className="mb-[22px] flex flex-wrap gap-[18px]">
        {DEMO_UNIVERSITIES.map((u) => {
          const brand = BRAND[u.id];
          return (
            <div key={u.id} className="flex flex-[1_1_220px] items-end gap-3 rounded-[18px] bg-surface-2 px-[18px] py-3.5">
              <Mascot
                height={120}
                primary={brand.colors.primary ?? NEUTRAL_BRAND.primary}
                secondary={brand.colors.secondary ?? NEUTRAL_BRAND.secondary}
                label={brand.label_text}
              />
              <div className="pb-2.5">
                <div className="text-[13.5px] font-medium">{u.name}</div>
                <div className="text-[11.5px] text-ink-3">{t.guide.wardrobeNote} · DEMO</div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,320px),1fr))] gap-[18px]">
        {DEMO_UNIVERSITIES.map((u) => (
          <CompareColumn key={u.id} university={u} stats={COMPARE_STATS[u.id]} />
        ))}
      </div>
    </div>
  );
}
