import type { Lang } from "@/lib/i18n";
import { createSseParser } from "@/lib/sse";
import type { ProfileEvent, ProfileResponse, ResolveResponse, SourceStatus } from "@/lib/types";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

const RESOLVE_TIMEOUT_MS = 20_000;
/** Building a profile queries four sources; the backend budget is ≤30 s. */
const PROFILE_TIMEOUT_MS = 45_000;

export class ApiError extends Error {
  constructor(
    message: string,
    /** "stream": the SSE stream broke off (or sent garbage) before `done`. */
    readonly kind: "network" | "http" | "stream",
    readonly status: number | null = null,
    readonly sourcesStatus: SourceStatus[] = [],
  ) {
    super(message);
  }
}

export function resolveUniversity(query: string, signal?: AbortSignal): Promise<ResolveResponse> {
  return getJson(`/resolve?q=${encodeURIComponent(query)}`, RESOLVE_TIMEOUT_MS, signal);
}

const PROFILE_EVENTS = new Set<string>(["source_status", "photo", "summary", "stage", "done"]);

export type ProfileHandlers = {
  /** The endpoint answered with a finished JSON ProfileResponse (before the switch to SSE). */
  onJson: (data: ProfileResponse) => void;
  /** One SSE event (docs/CONTRACT.md §3). */
  onEvent: (event: ProfileEvent) => void;
};

/**
 * GET /profile/{id}. Works with both backend shapes: `application/json` → onJson once;
 * `text/event-stream` → onEvent per event. Resolves after `done`; a stream that closes without
 * `done` rejects with ApiError kind "stream". 404/422/503 arrive as JSON before any stream.
 */
export async function loadProfile(
  wikidataId: string,
  lang: Lang,
  handlers: ProfileHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const response = await request(`/profile/${encodeURIComponent(wikidataId)}?lang=${lang}`, PROFILE_TIMEOUT_MS, signal);
  if (!(response.headers.get("content-type") ?? "").includes("text/event-stream")) {
    handlers.onJson(await response.json());
    return;
  }
  if (!response.body) throw new ApiError("Empty stream", "stream");

  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
  let done = false;
  const parser = createSseParser(({ event, data }) => {
    if (done || !PROFILE_EVENTS.has(event)) return;
    let parsed: unknown;
    try {
      parsed = JSON.parse(data);
    } catch {
      throw new ApiError(`Malformed ${event} event`, "stream");
    }
    handlers.onEvent({ event, data: parsed } as ProfileEvent);
    if (event === "done") done = true;
  });

  try {
    while (!done) {
      const chunk = await reader.read();
      if (chunk.done) break;
      parser.push(chunk.value);
    }
  } catch (err) {
    if (signal?.aborted || err instanceof ApiError) throw err;
    throw new ApiError(`Stream error: ${(err as Error).message}`, "stream");
  } finally {
    parser.end();
    reader.cancel().catch(() => {});
  }
  if (!done) throw new ApiError("Stream closed before done", "stream");
}

async function request(path: string, timeoutMs: number, signal?: AbortSignal): Promise<Response> {
  const url = `${API_URL}${path}`;
  const timeout = AbortSignal.timeout(timeoutMs);
  let response: Response;
  try {
    response = await fetch(url, { signal: signal ? AbortSignal.any([signal, timeout]) : timeout });
  } catch (err) {
    if (signal?.aborted) throw err;
    throw new ApiError(`Network error: ${(err as Error).message}`, "network");
  }

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new ApiError(body.detail ?? response.statusText, "http", response.status, body.sources_status ?? []);
  }
  return response;
}

async function getJson<T>(path: string, timeoutMs: number, signal?: AbortSignal): Promise<T> {
  return (await request(path, timeoutMs, signal)).json();
}
