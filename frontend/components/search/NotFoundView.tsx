"use client";

import { useState } from "react";
import { usePreferences } from "@/components/layout/PreferencesProvider";
import type { SourceStatus } from "@/lib/types";
import { SearchForm } from "./SearchForm";
import { SourcesBanner } from "./SourcesBanner";

type Props = {
  query: string;
  sources: SourceStatus[];
  onSearch: (query: string) => void;
};

export function NotFoundView({ query, sources, onSearch }: Props) {
  const { t } = usePreferences();
  const [value, setValue] = useState(query);

  return (
    <div className="mx-auto max-w-[620px] px-[22px] pb-20 pt-[12vh]">
      <SourcesBanner sources={sources} />
      <div className="mb-[18px] flex size-[38px] items-center justify-center rounded-full bg-surface-2 text-[17px] text-ink-3">
        ?
      </div>
      <h2 className="mb-2.5 text-[26px] font-semibold tracking-[-0.02em]">{t.notFoundTitle}</h2>
      <p className="mb-5 text-[15px] leading-[1.55] text-ink-2">{t.notFoundBody}</p>
      <ul className="mb-[26px] list-disc pl-[18px] text-sm leading-[1.9] text-ink-2">
        {t.notFoundTips.map((tip) => (
          <li key={tip}>{tip}</li>
        ))}
      </ul>
      <SearchForm
        value={value}
        onChange={setValue}
        onSubmit={() => onSearch(value)}
        size="compact"
        buttonLabel={t.tryAgain}
      />
    </div>
  );
}
