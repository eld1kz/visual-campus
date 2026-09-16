"use client";

import { useEffect, useState } from "react";
import { usePreferences } from "@/components/layout/PreferencesProvider";
import { RoundButton } from "@/components/ui/Button";
import { TierBadge } from "@/components/ui/TierBadge";
import { EVIDENCE_ICON, evidenceLabel, tierMeta } from "@/lib/tiers";
import type { Photo } from "@/lib/types";
import { licenseView, photoAlt } from "./PhotoCard";
import { PhotoImage } from "./PhotoImage";

type Props = {
  photo: Photo;
  onPrev: () => void;
  onNext: () => void;
  onClose: () => void;
};

function MetaRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex justify-between gap-3 text-[13px]">
      <span className="text-ink-3">{label}</span>
      {children}
    </div>
  );
}

/** Right-side overlay: Escape closes, ←/→ navigate, click on the scrim closes. */
export function PhotoDetail({ photo, onPrev, onNext, onClose }: Props) {
  const { t, lang } = usePreferences();
  const [dupOpen, setDupOpen] = useState(false);
  const [reported, setReported] = useState(false);
  const meta = tierMeta(photo.tier, t);
  const license = licenseView(photo.license, t.unknownLicense);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "ArrowRight") onNext();
      if (e.key === "ArrowLeft") onPrev();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose, onNext, onPrev]);

  return (
    <div onClick={onClose} className="fixed inset-0 z-[60] flex justify-end bg-[rgba(10,10,12,.62)] animate-[vc-in_.18s_ease_both]">
      <div
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        className="flex h-full w-[min(100%,980px)] flex-col overflow-hidden bg-bg"
      >
        <div className="flex items-center gap-3 bg-bg px-5 py-3.5">
          <TierBadge tier={photo.tier} variant="panel" />
          <span className="font-mono text-xs text-ink-3">{photo.id}</span>
          <div className="ml-auto flex gap-1.5">
            <RoundButton onClick={onPrev} aria-label="←">←</RoundButton>
            <RoundButton onClick={onNext} aria-label="→">→</RoundButton>
            <RoundButton onClick={onClose} aria-label="×">×</RoundButton>
          </div>
        </div>

        <div className="grid min-h-0 flex-1 grid-cols-[repeat(auto-fit,minmax(min(100%,380px),1fr))] overflow-auto">
          <div className="flex flex-col gap-3 p-[18px]">
            <div className="ph-stripes relative flex aspect-[4/3] items-center justify-center overflow-hidden rounded-[18px] [--s:10px]">
              {photo.thumb_url ? (
                <PhotoImage key={photo.id} src={photo.thumb_url} alt={photoAlt(photo)} fit="fill" />
              ) : (
                <span className="font-mono text-xs text-ink-3">{photo.placeholder_caption}</span>
              )}
            </div>
            <div className="flex flex-col gap-[7px]">
              <MetaRow label={t.source}>
                <a href={photo.source_url} target="_blank" rel="noreferrer" className="font-mono">
                  {photo.source_domain}
                </a>
              </MetaRow>
              <MetaRow label={t.author}>
                <span>{photo.author}</span>
              </MetaRow>
              <MetaRow label={t.license}>
                <span style={{ color: license.color }}>{license.label}</span>
              </MetaRow>
              <MetaRow label={t.published}>
                <span className="font-mono">{photo.published_at}</span>
              </MetaRow>
              <MetaRow label={t.retrieved}>
                <span className="font-mono">{photo.retrieved_at}</span>
              </MetaRow>
            </div>
          </div>

          <div className="flex flex-col gap-[22px] bg-surface-2 p-5">
            <div>
              <div className="micro-label mb-2 text-[10.5px] tracking-[.07em]">{t.confScale}</div>
              <div className="mb-2 flex items-baseline gap-2.5">
                <span className="font-mono text-[30px] font-medium" style={{ color: meta.color }}>
                  {photo.confidence}
                </span>
                <span className="text-[13px] text-ink-3">/ 100</span>
              </div>
              <div className="h-1.5 overflow-hidden rounded-[3px] bg-surface">
                <div className="h-full" style={{ width: `${photo.confidence}%`, background: meta.color }} />
              </div>
            </div>

            <div>
              <div className="mb-2.5 text-sm font-semibold">{t.whyTitle}</div>
              <div className="flex flex-col gap-2">
                {photo.evidence.map((e, i) => (
                  <div key={i} className="flex items-start gap-2.5 border-b border-line py-[9px]">
                    <span className="text-sm leading-[1.3]">{EVIDENCE_ICON[e.type]}</span>
                    <span className="text-[13px] leading-[1.45] text-ink">{evidenceLabel(e, lang)}</span>
                    <span
                      className="ml-auto font-mono text-[11.5px] font-medium"
                      style={{ color: e.weight > 0 ? "var(--ok)" : "var(--warn)" }}
                    >
                      {e.weight > 0 ? "+" : ""}
                      {e.weight}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <button
                onClick={() => setDupOpen((v) => !v)}
                className="flex w-full items-center gap-2 border-x-0 border-b-0 border-t border-line bg-transparent py-[9px] text-left text-[13px] text-ink-2"
              >
                <span>
                  {t.dupTitle}: {photo.duplicates.length}
                </span>
                <span className="ml-auto text-ink-3">{dupOpen ? "▴" : "▾"}</span>
              </button>
              {dupOpen && (
                <div className="mt-2.5 flex flex-col gap-2">
                  {photo.duplicates.map((d) => (
                    <div key={d.id} className="flex items-center gap-2.5">
                      <div className="ph-stripes relative h-[38px] w-[52px] shrink-0 overflow-hidden rounded-md border border-line [--s:6px]">
                        <PhotoImage src={d.thumb_url} alt={d.id} fit="fill" />
                      </div>
                      <div className="min-w-0">
                        <div className="font-mono text-[11px] text-ink-3">{d.id}</div>
                        <a href={d.source_url} target="_blank" rel="noreferrer" className="text-xs">
                          {new URL(d.source_url).hostname}
                        </a>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <button
              onClick={() => setReported(true)}
              className="mt-auto self-start rounded-full border-none bg-surface px-4 py-2.5 text-[13px] text-ink-2 hover:text-warn"
            >
              {reported ? t.reported : t.report}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
