"use client";

import { usePreferences } from "@/components/layout/PreferencesProvider";
import { Button } from "@/components/ui/Button";
import { TierBadge } from "@/components/ui/TierBadge";
import { categoryLabel } from "@/lib/photos";
import { EVIDENCE_ICON, evidenceLabel } from "@/lib/tiers";
import type { Photo, PhotoPin } from "@/lib/types";

type Props = { pin: PhotoPin; photo: Photo; onOpen: () => void; onClose: () => void };

export function PinCard({ pin, photo, onOpen, onClose }: Props) {
  const { t, lang } = usePreferences();
  const rows = [
    { label: t.map.category, value: <span>{categoryLabel(photo.category, t.tabs)}</span> },
    {
      label: t.source,
      value: (
        <a href={photo.source_url} target="_blank" rel="noreferrer" className="font-mono">
          {photo.source_domain}
        </a>
      ),
    },
    { label: t.published, value: <span className="font-mono">{photo.published_at}</span> },
  ];

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-2.5">
        <TierBadge tier={photo.tier} confidence={photo.confidence} variant="pin" />
        <span className="text-xs text-ink-3">{t.map.photoPin}</span>
        <button onClick={onClose} className="ml-auto border-none bg-transparent text-base leading-none text-ink-3">
          ×
        </button>
      </div>
      <div className="ph-stripes flex h-[150px] items-end rounded-[10px] p-[9px]">
        <span className="font-mono text-[10px] text-ink-3">{photo.placeholder_caption}</span>
      </div>
      <div className="flex flex-col gap-1.5">
        {rows.map((r) => (
          <div key={r.label} className="flex justify-between text-[12.5px]">
            <span className="text-ink-3">{r.label}</span>
            {r.value}
          </div>
        ))}
        <div className="text-xs text-ink-3">
          {pin.heading_deg !== null ? `${t.map.heading}: ${pin.heading_deg}°` : t.map.noHeading}
        </div>
      </div>
      <div className="flex flex-col">
        {photo.evidence.slice(0, 2).map((e, i) => (
          <div key={i} className="flex items-start gap-[9px] border-b border-line py-2 text-[12.5px] leading-[1.45]">
            <span>{EVIDENCE_ICON[e.type]}</span>
            <span>{evidenceLabel(e, lang)}</span>
          </div>
        ))}
      </div>
      <Button onClick={onOpen} className="self-start px-4 py-[9px] text-[12.5px]">
        {t.map.openPhoto}
      </Button>
    </div>
  );
}
