"use client";

import { usePreferences } from "@/components/layout/PreferencesProvider";
import { fill } from "@/lib/i18n";
import { GuideMascot } from "./GuideMascot";
import { useGuide } from "./GuideProvider";

/** Profile header block: waving mascot with a speech bubble, or a link to bring it back. */
export function GuideGreeting({ universityName }: { universityName: string }) {
  const { t } = usePreferences();
  const { hidden, setHidden, openChat } = useGuide();

  if (hidden) {
    return (
      <button onClick={() => setHidden(false)} className="border-none bg-transparent p-0 text-xs text-ink-3 underline">
        {t.guide.show}
      </button>
    );
  }

  return (
    <div className="flex flex-none items-end gap-2.5">
      <div className="flex max-w-[210px] flex-col items-end gap-2">
        <div
          onClick={openChat}
          className="relative cursor-pointer rounded-[18px_18px_4px_18px] bg-surface-2 px-[15px] py-[11px] text-[12.5px] leading-[1.45] text-ink"
        >
          {fill(t.guide.greet, { uni: universityName })}
        </div>
        <button onClick={() => setHidden(true)} className="border-none bg-transparent p-0 text-[11.5px] text-ink-3 underline">
          {t.guide.hide}
        </button>
      </div>
      <div onClick={openChat} className="cursor-pointer">
        <GuideMascot height={140} state="hello" />
      </div>
    </div>
  );
}
