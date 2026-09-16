"use client";

import { usePreferences } from "@/components/layout/PreferencesProvider";
import type { SourceStatus, UniversityCandidate } from "@/lib/types";
import { CandidateCard } from "./CandidateCard";
import { QueryEcho } from "./QueryEcho";
import { SourcesBanner } from "./SourcesBanner";

type Props = {
  query: string;
  correctedQuery: string | null;
  candidates: UniversityCandidate[];
  sources: SourceStatus[];
  onChoose: (candidate: UniversityCandidate) => void;
  onNoneOfThese: () => void;
};

export function DisambiguationView({ query, correctedQuery, candidates, sources, onChoose, onNoneOfThese }: Props) {
  const { t } = usePreferences();
  return (
    <div className="mx-auto max-w-[900px] px-[22px] pb-20 pt-14">
      <SourcesBanner sources={sources} />
      <QueryEcho query={query} corrected={correctedQuery} />
      <h2 className="mb-2 text-[28px] font-semibold tracking-[-0.02em]">{t.disambTitle}</h2>
      <p className="mb-[26px] text-[15px] text-ink-2">{t.disambSub}</p>

      <div className="grid grid-cols-[repeat(auto-fill,minmax(min(100%,340px),1fr))] gap-3.5">
        {candidates.map((c) => (
          <CandidateCard key={c.id} candidate={c} onChoose={() => onChoose(c)} />
        ))}
      </div>

      <button
        onClick={onNoneOfThese}
        className="mt-[22px] border-none bg-transparent py-2 text-[13px] text-ink-3 underline"
      >
        {t.noneOfThese}
      </button>
    </div>
  );
}
