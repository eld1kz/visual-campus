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

const toggle = (on: boolean) =>
  `flex cursor-pointer items-center gap-[7px] whitespace-nowrap rounded-full px-3 py-1.5 text-xs ${
    on ? "bg-accent-soft text-accent" : "bg-surface-2 text-ink-2"
  }`;

export function PhotoFilters({ tags, onToggleTag, sort, onSort, showUnconfirmed, onToggleUnconfirmed, showHistoric, onToggleHistoric }: Props) {
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
        <label className={toggle(showUnconfirmed)}>
          <input type="checkbox" checked={showUnconfirmed} onChange={onToggleUnconfirmed} className="m-0 accent-accent" />
          <span>{t.unconfirmedShort}</span>
        </label>
        <label className={toggle(showHistoric)}>
          <input type="checkbox" checked={showHistoric} onChange={onToggleHistoric} className="m-0 accent-accent" />
          <span>{t.historicShort}</span>
        </label>
      </div>
    </div>
  );
}
