"use client";

import { usePreferences } from "@/components/layout/PreferencesProvider";
import { fill } from "@/lib/i18n";

/** Honest empty state: say where we looked instead of padding with weak photos. `noPhotos`: the whole profile is empty. */
export function EmptyCategory({
  searchedIn,
  noPhotos = false,
  hiddenUnconfirmed = 0,
  filteredOut = 0,
  onShowUnconfirmed,
  onClearFilters,
}: {
  searchedIn: string[];
  noPhotos?: boolean;
  hiddenUnconfirmed?: number;
  filteredOut?: number;
  onShowUnconfirmed?: () => void;
  onClearFilters?: () => void;
}) {
  const { t } = usePreferences();
  const hasActions = Boolean(onShowUnconfirmed || onClearFilters);
  return (
    <div className="rounded-[20px] bg-surface-2 p-[38px]">
      <div className="mb-2 text-base font-medium">{noPhotos ? t.live.emptyAll : fill(t.emptyCategory, { n: String(searchedIn.length) })}</div>
      {(hiddenUnconfirmed > 0 || filteredOut > 0) && (
        <div className="mb-4 max-w-[70ch] text-[13px] leading-normal text-ink-2">
          {hiddenUnconfirmed > 0 && fill(t.emptyHidden, { n: String(hiddenUnconfirmed) })}
          {hiddenUnconfirmed > 0 && filteredOut > 0 ? " " : ""}
          {filteredOut > 0 && fill(t.emptyFiltered, { n: String(filteredOut) })}
        </div>
      )}
      {hasActions && (
        <div className="mb-5 flex flex-wrap gap-2">
          {onShowUnconfirmed && (
            <button onClick={onShowUnconfirmed} className="rounded-full border-none bg-accent px-3.5 py-2 text-[12.5px] font-medium text-white">
              {t.emptyShowHidden}
            </button>
          )}
          {onClearFilters && (
            <button onClick={onClearFilters} className="rounded-full border-none bg-surface px-3.5 py-2 text-[12.5px] text-ink-2">
              {t.emptyClearFilters}
            </button>
          )}
        </div>
      )}
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
