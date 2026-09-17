"use client";

import { usePreferences } from "@/components/layout/PreferencesProvider";
import { sourceLabel } from "@/lib/sources";
import type { ProfileSourceStatus } from "@/lib/types";

const COLOR: Record<ProfileSourceStatus["status"], string> = {
  pending: "var(--accent)",
  ok: "var(--ok)",
  timeout: "var(--warn)",
  error: "var(--warn)",
  skipped: "var(--mute)",
};

/** Source statuses as the server reports them (same look as the demo's LoadingSources). */
export function LiveSources({ sources, active }: { sources: ProfileSourceStatus[]; active: boolean }) {
  const { t, lang } = usePreferences();
  const took = (s: ProfileSourceStatus) => (s.took_ms == null ? "" : ` · ${(s.took_ms / 1000).toFixed(1)} ${t.sec}`);
  const label = (s: ProfileSourceStatus) => {
    if (s.status === "pending") return active ? t.live.queried : t.stUnavail;
    if (s.status === "ok") return `${t.stOk} · ${s.count}${took(s)}`;
    if (s.status === "timeout") return `${t.stTimeout}${took(s)}`;
    if (s.status === "error") return `${t.live.stError}${took(s)}`;
    return t.live.stSkipped;
  };

  return (
    <div>
      <div className="micro-label mb-3">{t.sourcesTitle}</div>
      <div className="flex flex-col">
        {sources.map((s) => (
          <div key={s.name} className="flex w-full items-center gap-2 border-b border-line py-[5px] text-[12.5px] text-ink-2">
            <span>{sourceLabel(s.name, lang)}</span>
            <span
              className={`ml-auto font-mono text-[10.5px] tracking-[.03em] ${s.status === "pending" && active ? "animate-vc-pulse" : ""}`}
              style={{ color: COLOR[s.status] }}
            >
              {label(s)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
