"use client";

import Link from "next/link";
import { usePreferences } from "@/components/layout/PreferencesProvider";
import { Button } from "@/components/ui/Button";
import type { SourceStatus, UniversityCandidate } from "@/lib/types";
import { QueryEcho } from "./QueryEcho";
import { SourcesBanner } from "./SourcesBanner";
import { UniversityCard } from "./UniversityCard";

type Props = {
  query: string;
  correctedQuery: string | null;
  university: UniversityCandidate;
  sources: SourceStatus[];
  tookMs: number;
  onSearchAgain: () => void;
};

export function ResolvedView({ query, correctedQuery, university, sources, tookMs, onSearchAgain }: Props) {
  const { t } = usePreferences();
  return (
    <div className="mx-auto max-w-[900px] px-[22px] pb-20 pt-14">
      <SourcesBanner sources={sources} />
      <QueryEcho query={query} corrected={correctedQuery} />
      <h2 className="mb-2 text-[28px] font-semibold tracking-[-0.02em]">{t.resolvedTitle}</h2>
      <p className="mb-[26px] text-[15px] text-ink-2">{t.resolvedSub}</p>

      <UniversityCard university={university} />

      <div className="mt-[22px] flex flex-wrap items-center gap-2">
        <Link href="/collecting" className="hover:no-underline">
          <Button className="px-[22px] py-[13px] text-sm">{t.buildProfile}</Button>
        </Link>
        <Button variant="secondary" onClick={onSearchAgain} className="px-[22px] py-[13px] text-sm">
          {t.searchAnother}
        </Button>
        <span className="ml-auto font-mono text-[11px] text-ink-3">
          ROR · Wikidata · {(tookMs / 1000).toFixed(1)} {t.sec}
        </span>
      </div>
    </div>
  );
}
