"use client";

import { usePreferences } from "@/components/layout/PreferencesProvider";
import { FILTER_TAGS, type PhotoSort } from "@/lib/photos";
import type { PhotoTag } from "@/lib/types";

type Props = {
  tags: PhotoTag[];
  onToggleTag: (tag: PhotoTag) => void;
  sort: PhotoSort;
  onSort: (sort: PhotoSort) => void;
  showUnconfirmed: boolean;
  onToggleUnconfirmed: () => void;
  showHistoric: boolean;
  onToggleHistoric: () => void;
};

const segment = (on: boolean) =>
  `rounded-full border-none px-[13px] py-1.5 text-[12.5px] ${on ? "bg-surface-2 font-medium text-ink" : "bg-transparent text-ink-3"}`;

export function PhotoFilters({ tags, onToggleTag, sort, onSort, showUnconfirmed, onToggleUnconfirmed, showHistoric, onToggleHistoric }: Props) {
  const { t } = usePreferences();

  return (
    <div className="mb-[18px] flex flex-wrap items-center gap-2.5">
      {FILTER_TAGS.map((tag, i) => {
        const on = tags.includes(tag);
        return (
          <button
            key={tag}
            onClick={() => onToggleTag(tag)}
            className={`rounded-full border-none px-3.5 py-[7px] text-[13px] ${on ? "bg-accent-soft text-accent" : "bg-surface-2 text-ink-2"}`}
          >
            {t.chips[i]}
          </button>
        );
      })}
      <div className="ml-auto flex flex-wrap items-center gap-2">
        <span className="text-xs text-ink-3">{t.sortBy}</span>
        <div className="flex gap-0.5">
          <button onClick={() => onSort("confidence")} className={segment(sort === "confidence")}>
            {t.sortConf}
          </button>
          <button onClick={() => onSort("date")} className={segment(sort === "date")}>
            {t.sortDate}
          </button>
        </div>
        <label className="flex cursor-pointer items-center gap-[7px] rounded-full bg-surface-2 px-3 py-1.5 text-xs text-ink-2">
          <input type="checkbox" checked={showUnconfirmed} onChange={onToggleUnconfirmed} className="m-0 accent-accent" />
          <span>{t.tierToggle}</span>
        </label>
        <label className="flex cursor-pointer items-center gap-[7px] rounded-full bg-surface-2 px-3 py-1.5 text-xs text-ink-2">
          <input type="checkbox" checked={showHistoric} onChange={onToggleHistoric} className="m-0 accent-accent" />
          <span>{t.historicToggle}</span>
        </label>
      </div>
    </div>
  );
}
