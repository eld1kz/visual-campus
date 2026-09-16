"use client";

import { usePreferences } from "@/components/layout/PreferencesProvider";

export function QueryEcho({ query, corrected }: { query: string; corrected?: string | null }) {
  const { t } = usePreferences();
  return (
    <div className="mb-2.5 font-mono text-xs text-ink-3">
      {t.queryEcho}: {query}
      {corrected ? ` · ${t.correctedTo}: ${corrected}` : ""}
    </div>
  );
}
