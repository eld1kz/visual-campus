"use client";

import { useState } from "react";
import { usePreferences } from "@/components/layout/PreferencesProvider";
import { WarningBanner } from "@/components/ui/WarningBanner";
import { fill } from "@/lib/i18n";
import { sourceLabel } from "@/lib/sources";
import type { ProfileSourceStatus } from "@/lib/types";

/** «Профиль неполный»: names the sources that timed out or failed (skipped sources don't count). */
export function PartialBanner({ partial, sources }: { partial: boolean; sources: ProfileSourceStatus[] }) {
  const { t, lang } = usePreferences();
  const [dismissed, setDismissed] = useState(false);
  const failed = sources.filter((s) => s.status === "timeout" || s.status === "error").map((s) => sourceLabel(s.name, lang));
  if (dismissed || (!partial && !failed.length)) return null;

  return (
    <WarningBanner onDismiss={() => setDismissed(true)} className="mb-[22px]">
      {failed.length ? fill(t.live.partialSources, { sources: failed.join(", ") }) : t.live.partialDeadline}
    </WarningBanner>
  );
}
