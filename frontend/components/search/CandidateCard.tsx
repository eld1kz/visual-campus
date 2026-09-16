"use client";

import { usePreferences } from "@/components/layout/PreferencesProvider";
import { Button } from "@/components/ui/Button";
import type { UniversityCandidate } from "@/lib/types";
import { MiniMapThumb } from "./MiniMapThumb";
import { placeOf } from "./UniversityCard";

export function CandidateCard({ candidate, onChoose }: { candidate: UniversityCandidate; onChoose: () => void }) {
  const { t } = usePreferences();
  return (
    <div className="flex gap-3.5 rounded-[18px] bg-surface-2 p-4">
      <MiniMapThumb />
      <div className="flex min-w-0 flex-col gap-[5px]">
        <div className="text-[15px] font-semibold leading-tight">{candidate.name}</div>
        <div className="text-[13px] text-ink-2">{placeOf(candidate)}</div>
        {candidate.aliases.length > 0 && (
          <div className="text-xs leading-[1.4] text-ink-3">
            <span className="font-mono">{t.alsoKnown}:</span> {candidate.aliases.slice(0, 4).join(", ")}
          </div>
        )}
        <Button onClick={onChoose} className="mt-auto self-start px-4 py-2 text-[13px]">
          {t.choose}
        </Button>
      </div>
    </div>
  );
}
