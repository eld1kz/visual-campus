"use client";

import { usePathname } from "next/navigation";
import { usePreferences } from "@/components/layout/PreferencesProvider";
import { GuideMascot } from "./GuideMascot";
import { useGuide } from "./GuideProvider";

/** 62px round button that opens the chat. Hidden on the live search page (the guide is demo-only). */
export function GuideFab() {
  const { t } = usePreferences();
  const { hidden, chatOpen, openChat, bounce } = useGuide();
  const pathname = usePathname();
  if (hidden || chatOpen || pathname === "/") return null;

  return (
    <button
      onClick={openChat}
      title={t.guide.askMe}
      aria-label={t.guide.askMe}
      className={`fixed bottom-5 right-5 z-[45] size-[62px] overflow-hidden rounded-full border border-line bg-surface p-0 shadow-soft ${
        bounce ? "animate-vc-bounce" : ""
      }`}
    >
      <div className="absolute left-1/2 top-[calc(50%-37px)] -translate-x-1/2">
        <GuideMascot height={128} state="idle" />
      </div>
    </button>
  );
}
