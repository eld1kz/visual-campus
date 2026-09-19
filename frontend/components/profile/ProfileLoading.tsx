"use client";

import { BackButton } from "@/components/ui/BackButton";
import { usePreferences } from "@/components/layout/PreferencesProvider";
import { PhotoImage } from "@/components/photos/PhotoImage";
import { photoAlt } from "@/components/photos/PhotoCard";
import { TierBadge } from "@/components/ui/TierBadge";
import type { ProfileProgress } from "@/lib/useProfile";
import { LiveSources } from "./LiveSources";

/** Sources the JSON endpoint queries; shown without timings until the server reports real statuses. */
const JSON_SOURCES = ["wikidata", "openstreetmap", "wikimedia_commons", "wikipedia"];
/** Thumbnails requested at once: upload.wikimedia.org answers 429 to bursts. */
const MAX_PREVIEW = 16;

type Props = {
  name: string | null;
  progress: ProfileProgress;
  /** Live timer while loading; null when the load has stopped (stream broke). */
  elapsedMs: number | null;
  /** Replaces the title row, e.g. the error block after a broken stream. */
  header?: React.ReactNode;
  /** Leave the build: closing the stream stops the sources on the server. */
  onCancel?: () => void;
};

/** Live build of a profile: real source statuses and photos as the SSE stream delivers them. */
export function ProfileLoading({ name, progress, elapsedMs, header, onCancel }: Props) {
  const { t } = usePreferences();
  const active = elapsedMs !== null;
  const sources = progress.sources.length
    ? progress.sources
    : JSON_SOURCES.map((id) => ({ name: id, status: "pending" as const, count: 0, took_ms: null }));
  // Unconfirmed photos stay hidden, as in the profile.
  const shown = progress.photos.filter((p) => p.tier !== "unconfirmed");

  return (
    <div className="mx-auto max-w-[1100px] px-[22px] pb-20 pt-8">
      {onCancel && (
        <BackButton onClick={onCancel} className="mb-4">
          {active ? t.navCancel : t.navNewSearch}
        </BackButton>
      )}
      {header ?? (
        <>
          <div className="mb-2 flex flex-wrap items-baseline gap-3.5">
            <h2 className="text-2xl font-semibold tracking-[-0.02em]">{t.loadingTitle}</h2>
            {name && <span className="text-[15px] text-ink-2">{name}</span>}
            {elapsedMs !== null && (
              <span className="ml-auto font-mono text-[26px] font-medium tabular-nums text-accent">
                {(elapsedMs / 1000).toFixed(1)} {t.sec}
              </span>
            )}
          </div>
          <p className="mb-[26px] max-w-[64ch] text-[13.5px] text-ink-3">
            {progress.mode === "stream" ? t.live.note : t.live.noteJson}
          </p>
        </>
      )}

      <div className="mb-[34px] max-w-[420px]">
        <LiveSources sources={sources} active={active} />
      </div>

      {progress.mode === "stream" && (
        <>
          <div className="micro-label mb-3">
            {t.photosAppearing} · {shown.length}
          </div>
          {shown.length === 0 ? (
            <div className="text-[13px] text-ink-3">{t.live.waitingPhotos}</div>
          ) : (
            <div className="columns-[4_200px] gap-x-3">
              {shown.slice(0, MAX_PREVIEW).map((p) => (
                <div
                  key={p.id}
                  className="ph-stripes relative mb-3 min-h-[90px] break-inside-avoid overflow-hidden rounded-[10px] border border-line animate-[vc-in_.35s_ease_both]"
                >
                  <PhotoImage src={p.thumb_url} alt={photoAlt(p)} />
                  <TierBadge tier={p.tier} confidence={p.confidence} className="absolute left-[7px] top-[7px]" />
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
