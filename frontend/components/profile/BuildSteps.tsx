"use client";

import { usePreferences } from "@/components/layout/PreferencesProvider";
import { CATEGORIES } from "@/lib/photos";
import type { BuildStage, PhotoCategory } from "@/lib/types";

const ORDER: BuildStage["stage"][] = ["sources", "gap_fill", "vision", "finalizing"];

type Props = { stage: BuildStage | null; active: boolean };

/** Steps after the sources: gap search, visual check with a live counter, final assembly. */
export function BuildSteps({ stage, active }: Props) {
  const { t } = usePreferences();
  const current = ORDER.indexOf(stage?.stage ?? "sources");
  const tab = (c: string) => t.tabs[CATEGORIES.indexOf(c as PhotoCategory) + 1]?.toLowerCase() ?? c;

  const steps = [
    { id: "sources", label: t.stages.sources },
    {
      id: "gap_fill",
      label: stage?.stage === "gap_fill" && stage.categories?.length
        ? `${t.stages.gapFill}: ${stage.categories.map(tab).join(", ")}`
        : t.stages.gapFill,
    },
    { id: "vision", label: t.stages.vision },
    { id: "finalizing", label: t.stages.finalizing },
  ];

  return (
    <div>
      <div className="micro-label mb-3">{t.stages.title}</div>
      <ol className="m-0 flex list-none flex-col gap-2.5 p-0">
        {steps.map((step, i) => {
          const done = i < current || (!active && i <= current);
          const now = i === current && active;
          const vision = step.id === "vision" && now && stage?.total ? stage : null;
          return (
            <li key={step.id} className={`text-[13px] ${done ? "text-ink-2" : now ? "text-ink" : "text-ink-3"}`}>
              <div className="flex items-center gap-2.5">
                <span
                  className={`flex size-[18px] shrink-0 items-center justify-center rounded-full text-[10px] ${
                    done ? "bg-ok text-bg" : now ? "animate-vc-pulse bg-accent text-bg" : "border border-line"
                  }`}
                >
                  {done ? "✓" : ""}
                </span>
                <span className={now ? "font-medium" : ""}>{step.label}</span>
                {vision && (
                  <span className="ml-auto font-mono text-xs tabular-nums text-accent">
                    {vision.checked} {t.stages.of} {vision.total}
                  </span>
                )}
              </div>
              {vision && vision.total ? (
                <div className="ml-7 mt-1.5 h-1 overflow-hidden rounded-full bg-surface-2">
                  <div
                    className="h-full rounded-full bg-accent transition-[width] duration-300"
                    style={{ width: `${Math.round(((vision.checked ?? 0) / vision.total) * 100)}%` }}
                  />
                </div>
              ) : null}
            </li>
          );
        })}
      </ol>
    </div>
  );
}
