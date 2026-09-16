"use client";

import { usePreferences } from "@/components/layout/PreferencesProvider";
import { TierBadge } from "@/components/ui/TierBadge";
import type { Photo } from "@/lib/types";

export function licenseView(license: string, unknownLabel: string) {
  const unknown = license === "unknown";
  return { label: unknown ? unknownLabel : license, color: unknown ? "var(--mute)" : "var(--ink-3)" };
}

/** Masonry card. Placeholder stripes stand in until `thumb_url` comes from the API. */
export function PhotoCard({ photo, onOpen }: { photo: Photo; onOpen: () => void }) {
  const { t } = usePreferences();
  const license = licenseView(photo.license, t.unknownLicense);

  return (
    <div onClick={onOpen} className="mb-5 cursor-pointer break-inside-avoid animate-vc-in">
      <div
        className="ph-stripes relative overflow-hidden rounded-2xl"
        style={{ height: photo.placeholder_height ?? 190 }}
      >
        <TierBadge tier={photo.tier} confidence={photo.confidence} className="absolute left-[9px] top-[9px]" />
        <span className="absolute bottom-2 left-2.5 font-mono text-[10px] text-ink-3">{photo.placeholder_caption}</span>
      </div>
      <div className="flex justify-between gap-2 pt-2 font-mono text-[11.5px] text-ink-3">
        <a href={photo.source_url} target="_blank" rel="noreferrer" onClick={(e) => e.stopPropagation()}>
          {photo.source_domain}
        </a>
        <span>{photo.published_at}</span>
      </div>
      <div className="pt-[3px] font-mono text-[11px]" style={{ color: license.color }}>
        {license.label}
      </div>
    </div>
  );
}
