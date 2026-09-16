"use client";

import { LoadingSources } from "@/components/collecting/LoadingSources";
import { usePreferences } from "@/components/layout/PreferencesProvider";
import { sourceLabel } from "@/lib/sources";

const SOURCES = ["wikidata", "openstreetmap", "wikimedia_commons", "wikipedia"];

/** Shown while GET /profile is running: the university name, a live timer and the sources being queried. */
export function ProfileLoading({ name, elapsedMs }: { name: string | null; elapsedMs: number }) {
  const { t, lang } = usePreferences();

  return (
    <div className="mx-auto max-w-[1100px] px-[22px] pb-20 pt-11">
      <div className="mb-2 flex flex-wrap items-baseline gap-3.5">
        <h2 className="text-2xl font-semibold tracking-[-0.02em]">{t.loadingTitle}</h2>
        {name && <span className="text-[15px] text-ink-2">{name}</span>}
        <span className="ml-auto font-mono text-[26px] font-medium tabular-nums text-accent">
          {(elapsedMs / 1000).toFixed(1)} {t.sec}
        </span>
      </div>
      <p className="mb-[26px] text-[13.5px] text-ink-3">{t.loadingNote}</p>
      <div className="max-w-[420px]">
        <LoadingSources
          elapsedMs={elapsedMs}
          sources={SOURCES.map((id) => ({ name: sourceLabel(id, lang), status: "pending", count: 0, at: Infinity }))}
        />
      </div>
    </div>
  );
}
