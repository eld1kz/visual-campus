"use client";

import { useState } from "react";
import { usePreferences } from "@/components/layout/PreferencesProvider";
import { WarningBanner } from "@/components/ui/WarningBanner";
import { fill } from "@/lib/i18n";
import type { SourceStatus } from "@/lib/types";

const SOURCE_NAMES: Record<string, string> = { ror: "ROR", wikidata: "Wikidata" };

/** One warning per source that failed or timed out. */
export function SourcesBanner({ sources }: { sources: SourceStatus[] }) {
  const { t } = usePreferences();
  const [dismissed, setDismissed] = useState<string[]>([]);
  const failed = sources.filter((s) => s.status !== "ok" && !dismissed.includes(s.name));
  if (!failed.length) return null;

  return (
    <div className="mb-[22px] flex flex-col gap-2">
      {failed.map((s) => (
        <WarningBanner key={s.name} onDismiss={() => setDismissed((d) => [...d, s.name])}>
          {fill(s.status === "timeout" ? t.sourceTimeout : t.sourceDown, { source: SOURCE_NAMES[s.name] ?? s.name })}
        </WarningBanner>
      ))}
    </div>
  );
}
