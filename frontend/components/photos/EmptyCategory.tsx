"use client";

import { usePreferences } from "@/components/layout/PreferencesProvider";

/** Honest empty state: say where we looked instead of padding with weak photos. */
export function EmptyCategory({ searchedIn }: { searchedIn: string[] }) {
  const { t } = usePreferences();
  return (
    <div className="rounded-[20px] bg-surface-2 p-[38px]">
      <div className="mb-2 text-base font-medium">{t.emptyCategory}</div>
      <div className="mb-3 text-[13px] text-ink-3">{t.emptyWhere}</div>
      <div className="flex flex-wrap gap-[7px]">
        {searchedIn.map((s) => (
          <span key={s} className="rounded-full bg-surface px-[11px] py-[5px] font-mono text-[11px] text-ink-2">
            {s}
          </span>
        ))}
      </div>
    </div>
  );
}
