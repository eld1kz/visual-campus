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
  const [showUnconfirmed, setShowUnconfirmed] = useState(false);
  const [showHistoric, setShowHistoric] = useState(false);

  const visible = filterPhotos(photos, { tab, tags, sort, showUnconfirmed, showHistoric });
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
        showUnconfirmed={showUnconfirmed}
        onToggleUnconfirmed={() => setShowUnconfirmed((v) => !v)}
        showHistoric={showHistoric}
        onToggleHistoric={() => setShowHistoric((v) => !v)}
      />

      {tab !== "all" && !inTab.some((p) => p.freshness === "2024_plus" && p.tier !== "unconfirmed") && inTab.length > 0 && (
        <div className="mb-4 rounded-xl bg-surface-2 px-4 py-3 text-[12.5px] text-ink-2">{t.noRecentPhotos}</div>
      )}

      {showUnconfirmed && (
        <div className="mb-4 flex items-center gap-[9px] rounded-full bg-surface-2 px-[15px] py-[11px] text-[12.5px] text-ink-2">
          <span className="text-mute">?</span>
          <span>{t.tierWarn}</span>
        </div>
      )}

      {visible.length === 0 ? (
        <EmptyCategory
          searchedIn={searchedIn}
          noPhotos={photos.length === 0}
          hiddenUnconfirmed={hiddenUnconfirmed}
          filteredOut={filteredOut}
          onShowUnconfirmed={hiddenUnconfirmed > 0 ? () => setShowUnconfirmed(true) : undefined}
          onClearFilters={tags.length > 0 ? () => setTags([]) : undefined}
        />
      ) : (
        <div className="columns-[4_250px] gap-x-3.5">
          {visible.map((photo, i) => (
            <PhotoCard key={photo.id} photo={photo} onOpen={() => onOpen(visible, i)} />
          ))}
        </div>
      )}
    </>
  );
}
