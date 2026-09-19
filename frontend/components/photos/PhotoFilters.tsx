"use client";

import { usePreferences } from "@/components/layout/PreferencesProvider";
import { FILTER_TAGS, type PhotoSort } from "@/lib/photos";
import type { PhotoTag } from "@/lib/types";

type Props = {
  tags: PhotoTag[];
  onToggleTag: (tag: PhotoTag) => void;
  sort: PhotoSort;
  onSort: (sort: PhotoSort) => void;
};

export function PhotoFilters({ tags, onToggleTag, sort, onSort }: Props) {
  const { t } = usePreferences();

  return (
    <div className="mb-[18px] flex flex-wrap items-center gap-2">
      {FILTER_TAGS.map((tag, i) => {
        const on = tags.includes(tag);
        return (
          <button
            key={tag}
            onClick={() => onToggleTag(tag)}
            className={`rounded-full border-none px-3 py-1.5 text-xs ${on ? "bg-accent-soft text-accent" : "bg-surface-2 text-ink-2"}`}
          >
            {t.chips[i]}
          </button>
        );
      })}
      <div className="ml-auto flex items-center gap-2">
        <select
          value={sort}
          onChange={(e) => onSort(e.target.value as PhotoSort)}
          aria-label={t.sortBy}
          className="cursor-pointer rounded-full border-none bg-surface-2 px-3 py-1.5 text-xs text-ink-2"
        >
          <option value="recommended">{t.sortRecommended}</option>
          <option value="confidence">{t.sortConf}</option>
          <option value="date">{t.sortDate}</option>
        </select>
      </div>
    </div>
  );
}
