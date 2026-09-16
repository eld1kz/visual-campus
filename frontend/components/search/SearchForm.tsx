"use client";

import { usePreferences } from "@/components/layout/PreferencesProvider";
import { Button } from "@/components/ui/Button";

type Props = {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  busy?: boolean;
  size?: "hero" | "compact";
  buttonLabel?: string;
};

export function SearchForm({ value, onChange, onSubmit, busy = false, size = "hero", buttonLabel }: Props) {
  const { t } = usePreferences();
  const hero = size === "hero";

  return (
    <form
      className="flex gap-2"
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit();
      }}
    >
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={t.inputPh}
        aria-label={t.inputPh}
        className={`min-w-0 flex-1 rounded-full border border-transparent bg-surface-2 text-ink outline-none focus:border-accent ${
          hero ? "px-5 py-[17px] text-[17px] focus:bg-surface" : "px-[18px] py-3.5 text-[15px]"
        }`}
      />
      <Button type="submit" disabled={busy} className={hero ? "px-[26px] py-[17px] text-[15px]" : "px-[22px] py-3.5 text-sm"}>
        {busy ? t.searching : (buttonLabel ?? t.searchBtn)}
      </Button>
    </form>
  );
}
