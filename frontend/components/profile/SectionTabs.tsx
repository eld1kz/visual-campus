"use client";

import { usePreferences } from "@/components/layout/PreferencesProvider";

export type ProfileSection = "photos" | "map";

export function SectionTabs({ active, onChange }: { active: ProfileSection; onChange: (s: ProfileSection) => void }) {
  const { t } = usePreferences();
  const items: { key: ProfileSection; label: string }[] = [
    { key: "photos", label: t.map.secPhotos },
    { key: "map", label: t.map.secMap },
  ];

  return (
    <div className="mb-4 flex gap-0.5">
      {items.map((item) => {
        const on = item.key === active;
        return (
          <button
            key={item.key}
            onClick={() => onChange(item.key)}
            className={`rounded-[7px] border-none px-[13px] py-[7px] text-[13px] ${
              on ? "bg-surface-2 font-medium text-ink" : "bg-transparent text-ink-3"
            }`}
          >
            {item.label}
          </button>
        );
      })}
    </div>
  );
}
