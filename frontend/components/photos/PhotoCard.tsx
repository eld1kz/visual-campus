"use client";

import { usePreferences } from "@/components/layout/PreferencesProvider";
import { TierBadge } from "@/components/ui/TierBadge";
import type { Photo } from "@/lib/types";
import { freshnessBadge } from "@/lib/photos";
import { PhotoImage } from "./PhotoImage";

export function licenseView(license: string, unknownLabel: string, officialLabel?: string) {
  const unknown = license === "unknown";
  return { label: unknown ? (officialLabel ?? unknownLabel) : license, color: unknown ? "var(--mute)" : "var(--ink-3)" };
}

export const isOfficialPhoto = (photo: Photo) =>
  photo.evidence.some((e) => e.type === "text" && /official|официальн/i.test(e.label));

export const photoAlt = (photo: Photo) => photo.placeholder_caption ?? `${photo.source_domain} · ${photo.author}`;

/** Masonry card: the real thumbnail when the API has one, striped placeholder otherwise (demo data). */
export function PhotoCard({ photo, onOpen }: { photo: Photo; onOpen: () => void }) {
  const { t, lang } = usePreferences();
  const license = licenseView(photo.license, t.unknownLicense, isOfficialPhoto(photo) ? t.officialRights : undefined);

  return (
    <div onClick={onOpen} className="mb-5 cursor-pointer break-inside-avoid animate-vc-in">
      <div
        className="ph-stripes relative min-h-[120px] overflow-hidden rounded-2xl"
        style={photo.thumb_url ? undefined : { height: photo.placeholder_height ?? 190 }}
      >
        <PhotoImage src={photo.thumb_url} alt={photoAlt(photo)} />
        <TierBadge tier={photo.tier} confidence={photo.confidence} className="absolute left-[9px] top-[9px]" />
        <span className="absolute right-[9px] top-[9px] rounded-full bg-[rgba(255,255,255,.92)] px-2 py-1 font-mono text-[10px] text-ink-2">
          {freshnessBadge(photo, lang)}
        </span>
        {!photo.thumb_url && (
          <span className="absolute bottom-2 left-2.5 font-mono text-[10px] text-ink-3">{photo.placeholder_caption}</span>
        )}
      </div>
      <div className="flex justify-between gap-2 pt-2 font-mono text-[11.5px] text-ink-3">
        <a href={photo.source_url} target="_blank" rel="noreferrer" onClick={(e) => e.stopPropagation()}>
          {photo.source_domain}
        </a>
        <span>{photo.date_taken ?? (photo.date_uploaded ? `${lang === "ru" ? "загружено" : "uploaded"} ${photo.date_uploaded}` : (lang === "ru" ? "дата неизвестна" : "date unknown"))}</span>
      </div>
      <div className="pt-[3px] font-mono text-[11px]" style={{ color: license.color }}>
        {license.label}
      </div>
    </div>
  );
}
