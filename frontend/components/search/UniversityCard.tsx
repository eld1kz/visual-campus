"use client";

import { usePreferences } from "@/components/layout/PreferencesProvider";
import type { UniversityCandidate } from "@/lib/types";
import { MiniMapThumb } from "./MiniMapThumb";

export const placeOf = (u: UniversityCandidate) => [u.city, u.country].filter(Boolean).join(", ");

function IdRow({ label, value, href }: { label: string; value: string | null; href?: string }) {
  if (!value) return null;
  return (
    <div className="flex justify-between gap-3 text-[13px]">
      <span className="text-ink-3">{label}</span>
      {href ? (
        <a href={href} target="_blank" rel="noreferrer" className="truncate font-mono">
          {value}
        </a>
      ) : (
        <span className="truncate font-mono">{value}</span>
      )}
    </div>
  );
}

/** "Found" state: the resolved university with its registry identifiers. */
export function UniversityCard({ university }: { university: UniversityCandidate }) {
  const { t } = usePreferences();
  const u = university;
  const coords = u.lat !== null && u.lng !== null ? `${u.lat.toFixed(4)}, ${u.lng.toFixed(4)}` : null;

  return (
    <div className="flex flex-wrap gap-[18px] rounded-[18px] bg-surface-2 p-[18px] animate-vc-in">
      <MiniMapThumb size={120} />
      <div className="flex min-w-0 flex-[1_1_300px] flex-col gap-[7px]">
        <div className="text-[19px] font-semibold leading-tight tracking-[-0.01em]">{u.name}</div>
        <div className="flex flex-wrap items-center gap-3.5 text-sm text-ink-2">
          {placeOf(u) && <span>{placeOf(u)}</span>}
          {u.website && (
            <a href={u.website} target="_blank" rel="noreferrer">
              {u.website.replace(/^https?:\/\//, "").replace(/\/$/, "")}
            </a>
          )}
          <span className="font-mono text-xs text-ink-3">
            {t.matchScore} {Math.round(u.match_score * 100)}%
          </span>
        </div>
        {u.aliases.length > 0 && (
          <div className="text-xs leading-[1.4] text-ink-3">
            <span className="font-mono">{t.alsoKnown}:</span> {u.aliases.slice(0, 6).join(", ")}
          </div>
        )}
        <div className="mt-2 flex flex-col gap-[5px] border-t border-line pt-2.5">
          <IdRow label="ROR" value={u.ror_id} href={u.ror_id ? `https://ror.org/${u.ror_id}` : undefined} />
          <IdRow
            label="Wikidata"
            value={u.wikidata_id}
            href={u.wikidata_id ? `https://www.wikidata.org/wiki/${u.wikidata_id}` : undefined}
          />
          <IdRow
            label="Commons"
            value={u.commons_category}
            href={
              u.commons_category
                ? `https://commons.wikimedia.org/wiki/Category:${encodeURIComponent(u.commons_category.replace(/ /g, "_"))}`
                : undefined
            }
          />
          <IdRow label="lat, lng" value={coords} />
        </div>
      </div>
    </div>
  );
}
