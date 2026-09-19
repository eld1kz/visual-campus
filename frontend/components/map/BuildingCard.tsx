"use client";

import { usePreferences } from "@/components/layout/PreferencesProvider";
import { Button } from "@/components/ui/Button";
import { TierBadge } from "@/components/ui/TierBadge";
import { BUILDING_TYPE_COLOR } from "@/lib/map/geometry";
import type { Building, Photo } from "@/lib/types";

type Props = {
  building: Building;
  photos: Photo[];
  flatHeights: boolean;
  onOpenPhoto: (id: string) => void;
  onShow3d: () => void;
  onClose: () => void;
};

export function BuildingCard({ building: b, photos, flatHeights, onOpenPhoto, onShow3d, onClose }: Props) {
  const { t } = usePreferences();
  const own = photos.filter((p) => b.photo_ids.includes(p.id));
  const height =
    b.height_m && !flatHeights ? `${b.height_m} ${t.map.m} · ${b.levels ?? "—"} ${t.map.floors}` : t.map.noHeightRow;

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-start gap-2.5">
        <div className="min-w-0">
          <div className="text-[17px] font-semibold leading-tight tracking-[-0.01em]">{b.name}</div>
          <div className="mt-[5px] flex items-center gap-[7px] text-[12.5px] text-ink-2">
            <span className="size-2 rounded-sm" style={{ background: BUILDING_TYPE_COLOR[b.type] }} />
            <span>{t.map.types[b.type]}</span>
            <span className="text-ink-3">· {height}</span>
          </div>
        </div>
        <button onClick={onClose} className="ml-auto border-none bg-transparent text-base leading-none text-ink-3">
          ×
        </button>
      </div>

      {own.length > 0 ? (
        <div className="flex gap-2 overflow-x-auto pb-1">
          {own.map((p) => (
            <div
              key={p.id}
              onClick={() => onOpenPhoto(p.id)}
              className="ph-stripes relative h-[92px] w-[132px] shrink-0 cursor-pointer overflow-hidden rounded-lg [--s:8px]"
            >
              <TierBadge tier={p.tier} confidence={p.confidence} showLabel={false} variant="thumb" className="absolute left-1.5 top-1.5" />
            </div>
          ))}
        </div>
      ) : (
        <div className="text-[12.5px] leading-normal text-ink-3">{t.map.buildingNoPhotos}</div>
      )}

      <div className="text-[11.5px] text-ink-3">
        {t.map.buildingSource}: © {b.source} contributors
      </div>
      <Button onClick={onShow3d} className="px-4 py-[9px] text-[12.5px]">
        {t.map.show3d}
      </Button>
    </div>
  );
}
