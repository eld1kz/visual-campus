"use client";

import { useCallback, useEffect, useState } from "react";
import { ApiError, loadProfile } from "@/lib/api";
import type { Lang } from "@/lib/i18n";
import type { Citation, Photo, Profile, ProfileEvent, ProfileSourceStatus, ProfileStats } from "@/lib/types";

/** What has arrived so far. With the JSON endpoint nothing arrives until the whole profile is ready. */
export type ProfileProgress = {
  /** null: no answer yet; "stream": SSE events are arriving. */
  mode: "stream" | null;
  sources: ProfileSourceStatus[];
  photos: Photo[];
  summary: { text: string; citations: Citation[] } | null;
};

export type ReadyProfile = {
  profile: Profile;
  stats: ProfileStats;
  /** A source timed out or failed (or the backend deadline hit): the profile is incomplete. */
  partial: boolean;
};

export type ProfileState =
  | { kind: "loading"; elapsedMs: number; progress: ProfileProgress }
  | { kind: "ready"; ready: ReadyProfile }
  | { kind: "error"; error: ApiError; progress: ProfileProgress };

type Store = { key: string; progress: ProfileProgress; ready?: ReadyProfile; error?: ApiError };

const TICK_MS = 100;
const EMPTY: ProfileProgress = { mode: null, sources: [], photos: [], summary: null };

const upsert = <T,>(list: T[], item: T, same: (a: T) => boolean) => {
  const i = list.findIndex(same);
  return i < 0 ? [...list, item] : list.map((x, j) => (j === i ? item : x));
};

function apply(store: Store, e: ProfileEvent): Store {
  const p = { ...store.progress, mode: "stream" as const };
  if (e.event === "source_status") return { ...store, progress: { ...p, sources: upsert(p.sources, e.data, (s) => s.name === e.data.name) } };
  if (e.event === "photo") return { ...store, progress: { ...p, photos: upsert(p.photos, e.data, (x) => x.id === e.data.id) } };
  if (e.event === "summary") return { ...store, progress: { ...p, summary: e.data } };
  const d = e.data;
  const byId = new Map(p.photos.map((photo) => [photo.id, photo]));
  const finalPhotos = d.photo_ids.flatMap((id) => byId.get(id) ?? []); // keep the server ranking

  const profile: Profile = {
    university: d.university,
    generated_in_ms: d.generated_in_ms,
    sources_status: p.sources,
    summary: p.summary ?? { text: "", citations: [] },
    photos: finalPhotos,
  };
  return { ...store, progress: { ...p, photos: finalPhotos }, ready: { profile, stats: d.stats, partial: d.partial } };
}

/**
 * Loads GET /profile/{id}: an SSE stream (docs/CONTRACT.md §3) or, until the backend switches, one JSON ProfileResponse.
 * Leaving the page (unmount) or retrying aborts the request.
 */
export function useProfile(wikidataId: string, lang: Lang): { state: ProfileState; retry: () => void } {
  const [attempt, setAttempt] = useState(0);
  const [elapsedMs, setElapsedMs] = useState(0);
  const key = `${wikidataId}|${lang}|${attempt}`;
  const [store, setStore] = useState<Store>({ key, progress: EMPTY });

  useEffect(() => {
    const controller = new AbortController();
    const started = Date.now();
    const timer = setInterval(() => setElapsedMs(Date.now() - started), TICK_MS);
    const update = (fn: (s: Store) => Store) => {
      if (!controller.signal.aborted) setStore((s) => fn(s.key === key ? s : { key, progress: EMPTY }));
    };

    loadProfile(
      wikidataId,
      lang,
      {
        onJson: (data) =>
          update((s) => ({
            ...s,
            ready: {
              profile: data,
              stats: data.stats,
              partial: data.sources_status.some((x) => x.status === "timeout" || x.status === "error"),
            },
          })),
        onEvent: (event) => update((s) => apply(s, event)),
      },
      controller.signal,
    )
      .catch((err) => {
        const error = err instanceof ApiError ? err : new ApiError(String(err), "network");
        update((s) => ({ ...s, error }));
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

  const current = store.key === key ? store : { key, progress: EMPTY };
  if (current.ready) return { state: { kind: "ready", ready: current.ready }, retry };
  if (current.error) return { state: { kind: "error", error: current.error, progress: current.progress }, retry };
  return { state: { kind: "loading", elapsedMs: store.key === key ? elapsedMs : 0, progress: current.progress }, retry };
}
