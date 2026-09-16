"use client";

import { usePreferences } from "@/components/layout/PreferencesProvider";
import type { ProfileSourceStatus } from "@/lib/types";

type TimedSource = ProfileSourceStatus & { at: number };

export function LoadingSources({ elapsedMs, sources }: { elapsedMs: number; sources: TimedSource[] }) {
  const { t } = usePreferences();

  return (
    <div>
      <div className="micro-label mb-3">{t.sourcesTitle}</div>
      <div className="flex flex-col">
        {sources.map((s) => {
          const kind = elapsedMs >= s.at ? s.status : "loading";
          const color =
            kind === "ok" ? "var(--ok)" : kind === "loading" ? "var(--accent)" : kind === "timeout" ? "var(--warn)" : "var(--mute)";
          const label =
            kind === "ok" ? `${t.stOk} · ${s.count}` : kind === "loading" ? t.stLoading : kind === "timeout" ? t.stTimeout : t.stUnavail;
          return (
            <div key={s.name} className="flex w-full items-center gap-2 border-b border-line py-[5px] text-[12.5px] text-ink-2">
              <span>{s.name}</span>
              <span
                className={`ml-auto font-mono text-[10.5px] tracking-[.03em] ${kind === "loading" ? "animate-vc-pulse" : ""}`}
                style={{ color }}
              >
                {label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
