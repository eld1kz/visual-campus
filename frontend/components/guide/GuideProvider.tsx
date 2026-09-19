"use client";

import { useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { usePreferences } from "@/components/layout/PreferencesProvider";
import { askGuide } from "@/lib/api";
import { BRAND, NEUTRAL_BRAND, QA, QA_CHECKED, QA_CHIPS, type QaKey } from "@/lib/mock/guide";
import type { ChatAction, ChatMessage, MascotState, Outfit } from "@/lib/types";

export type ChatMessageView = ChatMessage & { streaming?: boolean };

type Guide = {
  brand: { primary: string; secondary: string; label: string; source: string; sourceUrl: string | null; hasColors: boolean };
  mascot: MascotState;
  playMascot: (state: MascotState, backToIdleMs?: number) => void;
  outfit: Outfit;
  setOutfitPart: <K extends keyof Outfit>(part: K, value: Outfit[K]) => void;
  randomOutfit: () => void;
  hidden: boolean;
  setHidden: (hidden: boolean) => void;
  bounce: boolean;
  chatOpen: boolean;
  openChat: () => void;
  closeChat: () => void;
  messages: ChatMessageView[];
  busy: boolean;
  error: boolean;
  ask: (key: QaKey, label: string) => void;
  send: (text: string) => void;
  retry: () => void;
  runAction: (action: ChatAction) => void;
  /** false hides the FAB and chat (kept for pages without a university). */
  available: boolean;
  setAvailable: (available: boolean) => void;
  /** A real profile on screen: the guide answers through POST /chat about it; null = the demo university. */
  setLiveProfile: (profile: { id: string; name: string } | null) => void;
  /** Name of the university the guide is talking about, when it is a real profile. */
  liveName: string | null;
};

const GuideContext = createContext<Guide | null>(null);

const THINKING_MS = 900;
const STREAM_TICK_MS = 26;
const STREAM_CHARS = 3;
/** Demo: the guide speaks for the demo university. */
const UNIVERSITY_ID = "ku";

/** "Nazarbayev University" -> "NU": the short label on the mascot's hoodie. */
const initials = (name: string) =>
  name.split(/[\s-]+/).filter((w) => /^\p{Lu}/u.test(w)).map((w) => w[0]).join("").slice(0, 4) || name.slice(0, 3).toUpperCase();

const pick = <T,>(items: T[]) => items[Math.floor(Math.random() * items.length)];

export function GuideProvider({ children }: { children: React.ReactNode }) {
  const { lang } = usePreferences();
  const router = useRouter();
  const [mascot, setMascot] = useState<MascotState>("idle");
  const [outfit, setOutfit] = useState<Outfit>(BRAND[UNIVERSITY_ID].outfit);
  const [hidden, setHidden] = useState(false);
  const [bounce, setBounce] = useState(true);
  const [chatOpen, setChatOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessageView[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(false);
  // Only a profile page turns the guide on: elsewhere there is no university to talk about.
  const [available, setAvailableState] = useState(false);
  const [live, setLive] = useState<{ id: string; name: string } | null>(null);
  const chatAbort = useRef<AbortController | null>(null);
  const mascotTimer = useRef<ReturnType<typeof setTimeout>>(undefined);
  const thinkTimer = useRef<ReturnType<typeof setTimeout>>(undefined);
  const streamTimer = useRef<ReturnType<typeof setInterval>>(undefined);

  useEffect(
    () => () => {
      clearTimeout(mascotTimer.current);
      clearTimeout(thinkTimer.current);
      clearInterval(streamTimer.current);
    },
    [],
  );

  const playMascot = useCallback((state: MascotState, backToIdleMs?: number) => {
    clearTimeout(mascotTimer.current);
    setMascot(state);
    if (backToIdleMs) mascotTimer.current = setTimeout(() => setMascot("idle"), backToIdleMs);
  }, []);

  const ask = useCallback(
    (key: QaKey, label: string) => {
      clearTimeout(thinkTimer.current);
      clearInterval(streamTimer.current);
      const qa = QA[key];
      const answer = qa[lang];
      setMessages((m) => [
        ...m,
        { role: "user", text: label },
        {
          role: "assistant", text: "", streaming: true, mascot_state: qa.state,
          citations: qa.citations, actions: qa.actions, checked: qa.checked ? QA_CHECKED[lang] : undefined,
        },
      ]);
      setBusy(true);
      setError(false);
      playMascot("thinking");

      thinkTimer.current = setTimeout(() => {
        playMascot("talking");
        let shown = 0;
        streamTimer.current = setInterval(() => {
          shown = Math.min(answer.length, shown + STREAM_CHARS);
          const done = shown >= answer.length;
          setMessages((m) => [...m.slice(0, -1), { ...m[m.length - 1], text: answer.slice(0, shown), streaming: !done }]);
          if (done) {
            clearInterval(streamTimer.current);
            setBusy(false);
            playMascot(qa.state === "dont_know" ? "dont_know" : qa.actions?.length ? "pointing" : "idle", 3500);
          }
        }, STREAM_TICK_MS);
      }, THINKING_MS);
    },
    [lang, playMascot],
  );

  const askLive = useCallback(
    async (text: string) => {
      if (!live) return;
      chatAbort.current?.abort();
      const controller = new AbortController();
      chatAbort.current = controller;
      const history = messages.filter((m) => m.text).map((m) => ({ role: m.role, text: m.text })).slice(-10);
      setMessages((m) => [...m, { role: "user", text }, { role: "assistant", text: "", streaming: true }]);
      setBusy(true);
      setError(false);
      playMascot("thinking");
      try {
        const reply = await askGuide({ wikidata_id: live.id, lang, message: text, history }, controller.signal);
        setMessages((m) => [...m.slice(0, -1), { ...reply, streaming: false }]);
        const state = reply.mascot_state ?? "talking";
        playMascot(state === "dont_know" ? "dont_know" : reply.actions?.length ? "pointing" : "talking", 3500);
      } catch {
        if (controller.signal.aborted) return;
        setMessages((m) => m.slice(0, -1));
        setError(true);
        playMascot("dont_know", 2500);
      } finally {
        if (!controller.signal.aborted) setBusy(false);
      }
    },
    [live, messages, lang, playMascot],
  );

  const send = useCallback(
    (text: string) => {
      const value = text.trim();
      if (!value || busy) return;
      if (live) {
        void askLive(value);
        return;
      }
      const lower = value.toLowerCase();
      const key = (Object.keys(QA) as QaKey[]).find((k) => QA[k].match?.some((w) => lower.includes(w)));
      ask(key ?? "unknown", value);
    },
    [ask, askLive, busy, live],
  );

  const runAction = useCallback(
    (action: ChatAction) => {
      playMascot("pointing", 2600);
      setChatOpen(false);
      const base = live ? `/profile?id=${live.id}&name=${encodeURIComponent(live.name)}&` : "/profile?";
      if (live && action.type === "tab") {
        router.push(`${base}tab=${action.tab}`);
        return;
      }
      if (action.type === "map") {
        router.push(`/profile?section=map${action.building_id ? `&building=${action.building_id}` : ""}`);
      } else if (action.type === "tab") {
        router.push(`/profile?tab=${action.tab}`);
      } else if (action.photo_ids[0]) {
        router.push(`/profile?photo=${action.photo_ids[0]}`);
      }
    },
    [playMascot, router, live],
  );

  const setLiveProfile = useCallback((profile: { id: string; name: string } | null) => {
    setLive((cur) => {
      if (cur?.id === profile?.id) return cur;
      chatAbort.current?.abort();
      setMessages([]); // a new university starts a new conversation
      setBusy(false);
      setError(false);
      return profile;
    });
  }, []);

  const setAvailable = useCallback((value: boolean) => {
    setAvailableState(value);
    if (!value) setChatOpen(false);
  }, []);

  const raw = live
    ? {
        ...BRAND[UNIVERSITY_ID],
        colors: { primary: null, secondary: null, source: "none" as const, source_url: null },
        label_text: initials(live.name),
      }
    : BRAND[UNIVERSITY_ID];
  const brand = {
    primary: raw.colors.primary ?? NEUTRAL_BRAND.primary,
    secondary: raw.colors.secondary ?? NEUTRAL_BRAND.secondary,
    label: raw.label_text,
    source: raw.colors.source,
    sourceUrl: raw.colors.source_url,
    hasColors: raw.colors.primary !== null,
  };

  const value: Guide = {
    brand,
    mascot,
    playMascot,
    outfit,
    setOutfitPart: (part, v) => {
      setOutfit((o) => ({ ...o, [part]: v }));
      playMascot("changing", 700);
    },
    randomOutfit: () => {
      setOutfit({ top: pick(["hoodie", "tshirt", "varsity"]), head: pick(["cap", "none"]), accessory: pick(["backpack", "scarf", "none"]) });
      playMascot("changing", 800);
    },
    hidden,
    setHidden: (h) => {
      setHidden(h);
      if (h) setChatOpen(false);
    },
    bounce,
    chatOpen,
    openChat: () => {
      setChatOpen(true);
      setBounce(false);
      playMascot("hello", 2600);
    },
    closeChat: () => {
      playMascot("idle");
      setChatOpen(false);
    },
    messages,
    busy,
    error,
    ask: (key, label) => (live ? send(label) : ask(key, label)),
    send,
    retry: () => {
      setError(false);
      const lastUser = [...messages].reverse().find((m) => m.role === "user");
      if (live && lastUser) {
        setMessages((m) => m.slice(0, m.lastIndexOf(lastUser)));
        void askLive(lastUser.text);
        return;
      }
      const chip = QA_CHIPS[lang][0];
      ask(chip.key, chip.label);
    },
    runAction,
    available,
    setAvailable,
    setLiveProfile,
    liveName: live?.name ?? null,
  };

  return <GuideContext.Provider value={value}>{children}</GuideContext.Provider>;
}

export function useGuide(): Guide {
  const value = useContext(GuideContext);
  if (!value) throw new Error("useGuide must be used inside GuideProvider");
  return value;
}
