"use client";

import { usePreferences } from "@/components/layout/PreferencesProvider";

/** Prominent marker for screens that are not connected to the API yet. */
export function DemoDataPlate({ className = "" }: { className?: string }) {
  const { t } = usePreferences();
  return (
    <div
      role="note"
      className={`flex flex-wrap items-center gap-2.5 rounded-full border border-dashed border-warn bg-warn-soft px-4 py-2.5 text-[13px] text-ink ${className}`}
    >
      <span className="rounded-full bg-warn px-2.5 py-0.5 font-mono text-[11px] font-medium tracking-[.09em] text-bg">
        {t.demoBadge}
      </span>
      <span>{t.demoPlate}</span>
    </div>
  );
}
