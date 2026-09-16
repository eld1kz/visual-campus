"use client";

import { usePreferences } from "@/components/layout/PreferencesProvider";
import { DemoDataPlate } from "@/components/ui/DemoDataPlate";
import { MASCOT_STATES } from "@/lib/mock/guide";
import { GuideMascot } from "./GuideMascot";
import { useGuide } from "./GuideProvider";

/** «Кампи: персонаж и состояния» — documentation screen; clicking a card plays that state. */
export function StateSheet() {
  const { t, lang } = usePreferences();
  const { playMascot } = useGuide();

  return (
    <div className="mx-auto max-w-[1100px] px-[22px] pb-[90px] pt-9">
      <DemoDataPlate className="mb-[22px]" />
      <h2 className="mb-2.5 text-[28px] font-semibold tracking-[-0.02em]">{t.guide.statesTitle}</h2>
      <p className="mb-1.5 max-w-[64ch] text-[14.5px] leading-[1.65] text-pretty text-ink-2">{t.guide.statesIntro}</p>
      <p className="mb-7 text-[12.5px] text-ink-3">{t.guide.namesNote}</p>
      <div className="grid grid-cols-[repeat(auto-fill,minmax(min(100%,210px),1fr))] gap-[18px]">
        {MASCOT_STATES.map((s) => (
          <div key={s.key} onClick={() => playMascot(s.key, 3500)} className="flex cursor-pointer flex-col gap-2.5">
            <div className="flex justify-center rounded-[18px] bg-surface-2 py-3.5">
              <GuideMascot height={150} state={s.key} />
            </div>
            <div className="text-sm font-semibold">{lang === "en" ? s.en : s.ru}</div>
            <div className="text-[12.5px] leading-normal text-ink-3">{lang === "en" ? s.noteEn : s.note}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
