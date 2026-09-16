"use client";

import { useState } from "react";
import { usePreferences } from "@/components/layout/PreferencesProvider";
import { sourceLabel } from "@/lib/mock/profile";
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
  const [sort, setSort] = useState<PhotoSort>("confidence");
  const [showUnconfirmed, setShowUnconfirmed] = useState(false);

  const visible = filterPhotos(photos, { tab, tags, sort, showUnconfirmed });
  const searchedIn = sources.filter((s) => s.status !== "unavailable").map((s) => sourceLabel(s.name, lang));

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
      />

      {showUnconfirmed && (
        <div className="mb-4 flex items-center gap-[9px] rounded-full bg-surface-2 px-[15px] py-[11px] text-[12.5px] text-ink-2">
          <span className="text-mute">?</span>
          <span>{t.tierWarn}</span>
        </div>
      )}

      {visible.length === 0 ? (
        <EmptyCategory searchedIn={searchedIn} />
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
