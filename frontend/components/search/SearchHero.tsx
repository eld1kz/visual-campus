"use client";

import { usePreferences } from "@/components/layout/PreferencesProvider";
import { SearchForm } from "./SearchForm";

const EXAMPLES = ["Korea University", "KAIST", "Назарбаев Университет", "TU Munich"];

type Props = {
  query: string;
  onQueryChange: (value: string) => void;
  onSearch: (query: string) => void;
  busy: boolean;
};

export function SearchHero({ query, onQueryChange, onSearch, busy }: Props) {
  const { t } = usePreferences();

  return (
    <div className="mx-auto max-w-[720px] px-[22px] pb-[100px] pt-[16vh]">
      <h1 className="mb-[18px] text-[clamp(34px,5vw,52px)] font-medium leading-[1.05] tracking-[-0.035em] text-pretty">
        {t.searchTitle}
      </h1>
      <p className="mb-10 max-w-[48ch] text-[16.5px] leading-[1.55] text-ink-2">{t.searchSub}</p>

      <SearchForm value={query} onChange={onQueryChange} onSubmit={() => onSearch(query)} busy={busy} />

      <div className="mt-[18px] flex flex-wrap items-center gap-2">
        {busy ? (
          <span className="animate-vc-pulse font-mono text-xs tracking-[.04em] text-accent">{t.searchingNote}…</span>
        ) : (
          <>
            <span className="font-mono text-xs tracking-[.04em] text-ink-3">{t.examples}</span>
            {EXAMPLES.map((name) => (
              <button
                key={name}
                onClick={() => onSearch(name)}
                className="rounded-full border-none bg-surface-2 px-3.5 py-[7px] text-[13px] text-ink-2 hover:text-accent"
              >
                {name}
              </button>
            ))}
          </>
        )}
      </div>

      <div className="mt-14 max-w-[58ch] text-[13px] leading-[1.65] text-ink-3">{t.note}</div>
    </div>
  );
}
