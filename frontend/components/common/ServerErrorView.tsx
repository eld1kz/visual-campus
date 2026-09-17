"use client";

import { usePreferences } from "@/components/layout/PreferencesProvider";
import { Button } from "@/components/ui/Button";

type Props = {
  code: string;
  onRetry: () => void;
  onBack: () => void;
  /** Defaults: «Сервер недоступен» and its explanation. */
  title?: string;
  body?: string;
  /** Less top padding when content follows the error (e.g. what arrived before a broken stream). */
  compact?: boolean;
};

/** Global error: «Сервер недоступен». */
export function ServerErrorView({ code, onRetry, onBack, title, body, compact = false }: Props) {
  const { t } = usePreferences();
  return (
    <div className={`mx-auto max-w-[560px] px-[22px] text-center ${compact ? "pb-8" : "pb-20 pt-[16vh]"}`}>
      <div className="mx-auto mb-[22px] flex size-11 items-center justify-center rounded-full bg-warn-soft text-[19px] text-warn">
        ⚠
      </div>
      <h2 className="mb-2.5 text-2xl font-semibold tracking-[-0.02em]">{title ?? t.errTitle}</h2>
      <p className="mb-6 text-[15px] leading-[1.6] text-ink-2">{body ?? t.errBody}</p>
      <div className="flex flex-wrap justify-center gap-2">
        <Button onClick={onRetry} className="px-[22px] py-[13px] text-sm">
          {t.retry}
        </Button>
        <Button variant="secondary" onClick={onBack} className="px-[22px] py-[13px] text-sm">
          {t.backToSearch}
        </Button>
      </div>
      <div className="mt-[22px] font-mono text-[11px] text-ink-3">{code}</div>
    </div>
  );
}
