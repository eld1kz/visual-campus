"use client";

import { useCallback, useEffect, useState } from "react";
import { ApiError, getProfile } from "@/lib/api";
import type { Lang } from "@/lib/i18n";
import type { ProfileResponse } from "@/lib/types";

export type ProfileState =
  | { kind: "loading"; elapsedMs: number }
  | { kind: "ready"; data: ProfileResponse }
  | { kind: "error"; error: ApiError };

type Result = { key: string; data?: ProfileResponse; error?: ApiError };

const TICK_MS = 100;

/**
 * Loads GET /profile/{id}. The only place that knows how the profile arrives:
 * when the endpoint becomes an SSE stream (docs/CONTRACT.md §3), change this hook, not the screens.
 */
export function useProfile(wikidataId: string, lang: Lang): { state: ProfileState; retry: () => void } {
  const [attempt, setAttempt] = useState(0);
  const [elapsedMs, setElapsedMs] = useState(0);
  const [result, setResult] = useState<Result | null>(null);
  const key = `${wikidataId}|${lang}|${attempt}`;

  useEffect(() => {
    const controller = new AbortController();
    const started = Date.now();
    const timer = setInterval(() => setElapsedMs(Date.now() - started), TICK_MS);
    getProfile(wikidataId, lang, controller.signal)
      .then((data) => setResult({ key, data }))
      .catch((err) => {
        if (controller.signal.aborted) return;
        setResult({ key, error: err instanceof ApiError ? err : new ApiError(String(err), "network") });
      })
      .finally(() => clearInterval(timer));
    return () => {
      controller.abort();
      clearInterval(timer);
    };
  }, [key, wikidataId, lang]);

  const retry = useCallback(() => {
    setElapsedMs(0);
    setAttempt((n) => n + 1);
  }, []);

  if (result?.key === key && result.data) return { state: { kind: "ready", data: result.data }, retry };
  if (result?.key === key && result.error) return { state: { kind: "error", error: result.error }, retry };
  return { state: { kind: "loading", elapsedMs }, retry };
}
