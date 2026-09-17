"use client";

import { usePreferences } from "@/components/layout/PreferencesProvider";

const PROVIDER_LABEL = { mapillary: "Mapillary", kakao: "Kakao Roadview", google: "Google Street View" };

/** «Walk» mode when no street-level panoramas were found (or no provider was checked). */
export function PanoramaEmpty({ checked, onBack }: { checked: string[]; onBack: () => void }) {
  const { t } = usePreferences();
  return (
    <div className="flex h-[clamp(300px,46vh,460px)] flex-col items-center justify-center gap-2.5 rounded-[20px] bg-surface-2 p-6 text-center">
      <div className="text-base font-medium">{t.map.panoEmpty}</div>
      <div className="font-mono text-xs text-ink-3">
        {checked.length > 0
          ? `${t.map.panoChecked}: ${checked.map((p) => PROVIDER_LABEL[p as keyof typeof PROVIDER_LABEL] ?? p).join(", ")}`
          : t.map.panoNotChecked}
      </div>
      <button onClick={onBack} className="mt-1.5 rounded-full border-none bg-ink px-[18px] py-2.5 text-[13px] text-bg">
        {t.map.backTo3d}
      </button>
    </div>
  );
}
