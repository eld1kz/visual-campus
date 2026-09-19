"use client";

import { useState } from "react";
import { usePreferences } from "@/components/layout/PreferencesProvider";
import { sourceLabel } from "@/lib/sources";
import { filterPhotos, type PhotoSort, type PhotoTab } from "@/lib/photos";
import type { Photo, PhotoTag, ProfileSourceStatus } from "@/lib/types";
import { CategoryTabs } from "./CategoryTabs";
import { EmptyCategory } from "./EmptyCategory";
import { PhotoCard } from "./PhotoCard";
import { PhotoFilters } from "./PhotoFilters";

const PAGE_SIZE = 24;

type Props = {
  photos: Photo[];
  sources: ProfileSourceStatus[];
  initialTab?: PhotoTab;
  onOpen: (list: Photo[], index: number) => void;
};

export function PhotosSection({ photos, sources, initialTab = "all", onOpen }: Props) {
  const { t, lang } = usePreferences();
  const [tab, setTab] = useState<PhotoTab>(initialTab);
  const [tags, setTags] = useState<PhotoTag[]>([]);
  const [sort, setSort] = useState<PhotoSort>("recommended");
  // No toggles: unconfirmed photos stay hidden (only checked photos are shown), historic ones show with their year.
  const showUnconfirmed = false;
  const showHistoric = true;

  const visible = filterPhotos(photos, { tab, tags, sort, showUnconfirmed, showHistoric });
  // Paging restarts whenever the tab or a filter changes.
  const filterKey = [tab, tags.join(","), sort, showUnconfirmed, showHistoric].join("|");
  const [page, setPage] = useState({ key: filterKey, count: PAGE_SIZE });
  const shownCount = page.key === filterKey ? page.count : PAGE_SIZE;
  const shown = visible.slice(0, shownCount);
  const remaining = visible.length - shown.length;
  const inTab = photos.filter((p) => tab === "all" || p.category === tab);
  const matchingTags = inTab.filter((p) => tags.length === 0 || tags.some((tag) => p.tags.includes(tag)));
  const hiddenUnconfirmed = showUnconfirmed ? 0 : matchingTags.filter((p) => p.tier === "unconfirmed").length;
  const filteredOut = tags.length === 0 ? 0 : inTab.filter((p) => p.tier !== "unconfirmed").length - visible.length;
  // Where we looked: sources that actually ran (a failed or skipped source did not search anything).
  const searchedIn = sources.filter((s) => s.status === "ok" || s.status === "timeout").map((s) => sourceLabel(s.name, lang));

  return (
    <>
      <CategoryTabs photos={photos} active={tab} showUnconfirmed={showUnconfirmed} onChange={setTab} />
      <PhotoFilters
        tags={tags}
        onToggleTag={(tag) => setTags((cur) => (cur.includes(tag) ? cur.filter((x) => x !== tag) : [...cur, tag]))}
        sort={sort}
        onSort={setSort}
      />

      {tab !== "all" && !inTab.some((p) => p.freshness === "2024_plus" && p.tier !== "unconfirmed") && inTab.length > 0 && (
        <div className="mb-4 rounded-xl bg-surface-2 px-4 py-3 text-[12.5px] text-ink-2">{t.noRecentPhotos}</div>
      )}

      {visible.length === 0 ? (
        <EmptyCategory
          searchedIn={searchedIn}
          noPhotos={photos.length === 0}
          hiddenUnconfirmed={hiddenUnconfirmed}
          filteredOut={filteredOut}
          onClearFilters={tags.length > 0 ? () => setTags([]) : undefined}
        />
      ) : (
        <>
          <div className="columns-[4_250px] gap-x-3.5">
            {shown.map((photo, i) => (
              <PhotoCard key={photo.id} photo={photo} onOpen={() => onOpen(visible, i)} />
            ))}
          </div>
          {remaining > 0 && (
            <div className="mt-6 flex justify-center">
              <button
                onClick={() => setPage({ key: filterKey, count: shownCount + PAGE_SIZE })}
                className="rounded-full bg-surface-2 px-5 py-2.5 text-[13px] font-medium text-ink transition-opacity hover:opacity-80"
              >
                {t.showMore} ({remaining})
              </button>
            </div>
          )}
        </>
      )}
    </>
  );
}
