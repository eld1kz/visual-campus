"use client";

import type { ChatMessageView } from "@/components/guide/GuideProvider";
import { usePreferences } from "@/components/layout/PreferencesProvider";
import { TierBadge } from "@/components/ui/TierBadge";
import { PHOTOS } from "@/lib/mock/photos";
import { categoryLabel } from "@/lib/photos";
import type { ChatAction } from "@/lib/types";

type Props = { message: ChatMessageView; onAction: (action: ChatAction) => void };

export function ChatMessageItem({ message, onAction }: Props) {
  const { t } = usePreferences();

  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[82%] rounded-[18px_18px_5px_18px] bg-surface-2 px-[15px] py-2.5 text-[13.5px] leading-normal">
          {message.text}
        </div>
      </div>
    );
  }

  const done = !message.streaming;
  const actions = message.actions ?? [];
  const photoIds = actions.flatMap((a) => (a.type === "photos" ? a.photo_ids : []));
  const photos = PHOTOS.filter((p) => photoIds.includes(p.id));

  return (
    <div className="flex flex-col gap-[9px]">
      <div className="max-w-[94%] whitespace-pre-wrap text-[13.5px] leading-[1.65] text-ink">{message.text}</div>

      {done && photos.length > 0 && (
        <div className="flex gap-2 overflow-x-auto pb-1">
          {photos.map((p) => (
            <div
              key={p.id}
              onClick={() => onAction({ type: "photos", photo_ids: [p.id] })}
              className="ph-stripes relative h-[88px] w-[124px] shrink-0 cursor-pointer overflow-hidden rounded-[9px] [--s:8px]"
            >
              <TierBadge tier={p.tier} confidence={p.confidence} showLabel={false} variant="thumb" className="absolute left-1.5 top-1.5" />
            </div>
          ))}
        </div>
      )}

      {done && actions.some((a) => a.type !== "photos") && (
        <div className="flex flex-wrap gap-[7px]">
          {actions
            .filter((a) => a.type !== "photos")
            .map((a, i) => (
              <button
                key={i}
                onClick={() => onAction(a)}
                className="rounded-full border-none bg-surface-2 px-3.5 py-2 text-[12.5px] text-ink-2 hover:text-accent"
              >
                {a.type === "map" ? t.guide.actMap : a.type === "tab" ? `${t.guide.actTab} ${categoryLabel(a.tab, t.tabs)}` : ""}
              </button>
            ))}
        </div>
      )}

      {done && message.checked && <div className="text-xs leading-normal text-ink-3">{message.checked}</div>}

      {done && message.from_web && (
        <div className="self-start rounded-full bg-surface-2 px-2.5 py-1 font-mono text-[10.5px] tracking-[.04em] text-ink-3">
          {t.guide.fromWeb}
        </div>
      )}

      {done && message.citations && message.citations.length > 0 && (
        <div className="flex flex-col gap-1">
          <div className="micro-label text-[10px] tracking-[.07em]">{t.guide.sources}</div>
          {message.citations.map((c) => (
            <div key={c.n} className="text-[11.5px] text-ink-3">
              [{c.n}]{" "}
              <a href={c.url} target="_blank" rel="noreferrer">
                {new URL(c.url).hostname}
              </a>{" "}
              · {c.title}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
