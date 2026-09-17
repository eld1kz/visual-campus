"use client";

import { useEffect, useRef, useState } from "react";
import { GuideMascot } from "@/components/guide/GuideMascot";
import { useGuide } from "@/components/guide/GuideProvider";
import { usePreferences } from "@/components/layout/PreferencesProvider";
import { Button } from "@/components/ui/Button";
import { PROFILE } from "@/lib/mock/profile";
import { QA_CHIPS } from "@/lib/mock/guide";
import { ChatMessageItem } from "./ChatMessageItem";

/** Right drawer with the guide chat. Demo: answers come from lib/mock/guide.ts. */
export function ChatDrawer() {
  const { t, lang } = usePreferences();
  const guide = useGuide();
  const [input, setInput] = useState("");
  const body = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (body.current) body.current.scrollTop = body.current.scrollHeight;
  }, [guide.messages, guide.error]);

  if (!guide.chatOpen || !guide.available) return null;

  const submit = () => {
    if (guide.busy) return;
    guide.send(input);
    setInput("");
  };

  return (
    <div className="fixed inset-y-0 right-0 z-[55] flex w-[min(100%,430px)] flex-col bg-bg shadow-[-12px_0_40px_rgba(0,0,0,.14)] animate-[vc-in_.2s_ease_both]">
      <div className="flex items-center gap-3 px-[18px] py-3">
        <div className="w-[58px] flex-none">
          <GuideMascot height={82} />
        </div>
        <div className="min-w-0">
          <div className="text-sm font-semibold">{t.guide.chatTitle}</div>
          <div className="text-[11.5px] text-ink-3">
            {PROFILE.university.name} · <span className="font-mono tracking-[.06em] text-warn">{t.demoBadge}</span>
          </div>
        </div>
        <button
          onClick={guide.closeChat}
          aria-label="×"
          className="ml-auto size-[30px] rounded-full border-none bg-surface-2 text-ink-2"
        >
          ×
        </button>
      </div>

      <div ref={body} className="flex min-h-0 flex-1 flex-col gap-4 overflow-auto px-3.5 py-4">
        {guide.messages.length === 0 && (
          <div className="max-w-[40ch] text-[13.5px] leading-[1.6] text-ink-2">{t.guide.emptyChat}</div>
        )}
        {guide.messages.map((m, i) => (
          <ChatMessageItem key={i} message={m} onAction={guide.runAction} />
        ))}
        {guide.error && (
          <div className="flex flex-col gap-[9px] rounded-[18px] bg-warn-soft px-4 py-3.5">
            <span className="text-[13px]">{t.guide.chatErr}</span>
            <Button onClick={guide.retry} className="self-start px-4 py-2 text-[12.5px]">
              {t.guide.retry}
            </Button>
          </div>
        )}
      </div>

      <div className="flex flex-col gap-2.5 px-[18px] pb-4 pt-3">
        <div className="flex gap-[7px] overflow-x-auto pb-0.5">
          {QA_CHIPS[lang].map((chip) => (
            <button
              key={chip.key}
              onClick={() => !guide.busy && guide.ask(chip.key, chip.label)}
              className="flex-none whitespace-nowrap rounded-[20px] border border-line bg-transparent px-3 py-[7px] text-[12.5px] text-ink-2"
            >
              {chip.label}
            </button>
          ))}
        </div>
        <form
          className="flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            submit();
          }}
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={t.guide.chatPh}
            className="min-w-0 flex-1 rounded-full border border-transparent bg-surface-2 px-4 py-3 text-[13.5px] text-ink outline-none focus:border-accent focus:bg-surface"
          />
          <Button type="submit" className="px-[18px] py-3 text-[13px]">
            {t.guide.send}
          </Button>
        </form>
        <div className="text-[11px] leading-[1.45] text-ink-3">{t.guide.chatNote}</div>
      </div>
    </div>
  );
}
