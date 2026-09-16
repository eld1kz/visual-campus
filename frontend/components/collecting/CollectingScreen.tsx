"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { usePreferences } from "@/components/layout/PreferencesProvider";
import { DemoDataPlate } from "@/components/ui/DemoDataPlate";
import { LOADING_SOURCE_TIMES, LOADING_STEP_TIMES, PROFILE } from "@/lib/mock/profile";
import { sourceLabel } from "@/lib/sources";
import { LoadingSteps } from "./LoadingSteps";
import { LoadingSources } from "./LoadingSources";

const TICK_MS = 100;
const DONE_MS = LOADING_STEP_TIMES[LOADING_STEP_TIMES.length - 1];
const FIRST_PHOTO_MS = 4200;
const PHOTO_EVERY_MS = 900;

/** Streaming build of a profile. Demo: timings are scripted; the API will stream real progress. */
export function CollectingScreen() {
  const { t, lang } = usePreferences();
  const router = useRouter();
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => setElapsed((ms) => Math.min(ms + TICK_MS, DONE_MS)), TICK_MS);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    if (elapsed < DONE_MS) return;
    const next = setTimeout(() => router.push("/profile"), 450);
    return () => clearTimeout(next);
  }, [elapsed, router]);

  const revealed = Math.min(9, Math.floor(Math.max(0, elapsed - FIRST_PHOTO_MS) / PHOTO_EVERY_MS));

  return (
    <div className="mx-auto max-w-[1100px] px-[22px] pb-20 pt-11">
      <DemoDataPlate className="mb-[26px]" />
      <div className="mb-[26px] flex flex-wrap items-baseline gap-3.5">
        <h2 className="text-2xl font-semibold tracking-[-0.02em]">{t.loadingTitle}</h2>
        <span className="text-[15px] text-ink-2">{PROFILE.university.name}</span>
        <span className="ml-auto font-mono text-[26px] font-medium tabular-nums text-accent">
          {(elapsed / 1000).toFixed(1)} {t.sec}
        </span>
      </div>

      <div className="mb-[34px] grid grid-cols-[repeat(auto-fit,minmax(min(100%,280px),1fr))] gap-[26px]">
        <LoadingSteps elapsedMs={elapsed} times={LOADING_STEP_TIMES} />
        <LoadingSources
          elapsedMs={elapsed}
          sources={PROFILE.sources_status.map((s, i) => ({ ...s, name: sourceLabel(s.name, lang), at: LOADING_SOURCE_TIMES[i] }))}
        />
      </div>

      <div className="micro-label mb-3">{t.photosAppearing}</div>
      <div className="columns-[4_200px] gap-x-3">
        {PROFILE.photos.slice(0, revealed).map((p) => (
          <div key={p.id} className="mb-3 break-inside-avoid overflow-hidden rounded-[10px] border border-line animate-[vc-in_.35s_ease_both]">
            <div className="ph-stripes" style={{ height: p.placeholder_height }} />
          </div>
        ))}
      </div>
    </div>
  );
}
