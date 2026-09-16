"use client";

import { usePreferences } from "@/components/layout/PreferencesProvider";

export function LoadingSteps({ elapsedMs, times }: { elapsedMs: number; times: number[] }) {
  const { t } = usePreferences();

  return (
    <div>
      <div className="micro-label mb-3">{t.stepsTitle}</div>
      <div className="flex flex-col gap-0.5">
        {t.stepNames.map((label, i) => {
          const done = elapsedMs >= times[i];
          const active = !done && (i === 0 || elapsedMs >= times[i - 1]);
          const color = done ? "var(--ok)" : active ? "var(--accent)" : "var(--ink-3)";
          return (
            <div key={label} className="flex items-center gap-2.5 py-2">
              <span
                className={`flex size-[18px] shrink-0 items-center justify-center rounded-full border text-[10px] ${active ? "animate-vc-pulse" : ""}`}
                style={{ borderColor: color, color }}
              >
                {done ? "✓" : active ? "•" : ""}
              </span>
              <span
                className={`text-[13.5px] ${active ? "font-medium" : ""}`}
                style={{ color: done || active ? "var(--ink)" : "var(--ink-3)" }}
              >
                {label}
              </span>
              <span className="ml-auto font-mono text-[11px] text-ink-3">
                {done ? `${(times[i] / 1000).toFixed(1)} ${t.sec}` : active ? t.running : ""}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
