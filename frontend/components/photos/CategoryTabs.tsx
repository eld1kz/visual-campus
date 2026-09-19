"use client";

import { usePreferences } from "@/components/layout/PreferencesProvider";
import { CATEGORIES, countInTab, type PhotoTab } from "@/lib/photos";
import type { Photo } from "@/lib/types";

type Props = {
  photos: Photo[];
  active: PhotoTab;
  showUnconfirmed: boolean;
  onChange: (tab: PhotoTab) => void;
};

export function CategoryTabs({ photos, active, showUnconfirmed, onChange }: Props) {
  const { t } = usePreferences();
  const labels = new Map<PhotoTab, string>((["all", ...CATEGORIES] as PhotoTab[]).map((tab, i) => [tab, t.tabs[i]]));
  // An empty category is hidden instead of showing "Libraries 0"; the active tab always stays.
  const tabs = [...labels.keys()].filter(
    (tab) => tab === "all" || tab === active || countInTab(photos, tab, showUnconfirmed) > 0,
  );

  return (
    <div className="mb-4 flex flex-wrap gap-1.5 border-b border-line">
      {tabs.map((tab) => {
        const on = tab === active;
        return (
          <button
            key={tab}
            onClick={() => onChange(tab)}
            className={`-mb-px flex items-center gap-[7px] border-x-0 border-b-2 border-t-0 bg-transparent px-3 py-[9px] text-[13.5px] ${
              on ? "border-accent font-medium text-ink" : "border-transparent text-ink-3"
            }`}
          >
            {labels.get(tab)}
            <span className="font-mono text-[11px] text-ink-3">{countInTab(photos, tab, showUnconfirmed)}</span>
          </button>
        );
      })}
    </div>
  );
}
