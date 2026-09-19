import type { Lang } from "@/lib/i18n";
import { createSseParser } from "@/lib/sse";
import type { CampusMap, ChatMessage, ProfileEvent, ProfileResponse, ResolveResponse, SourceStatus } from "@/lib/types";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

const RESOLVE_TIMEOUT_MS = 20_000;
/** Building a profile queries four sources; the backend budget is ≤30 s. */
const PROFILE_TIMEOUT_MS = 45_000;

const CLIENT_ID_KEY = "vc-client-id";

/** Anonymous per-browser id: the backend's daily AI limit is counted per user (X-Client-Id, else the IP). */
function clientId(): string | null {
  if (typeof window === "undefined") return null;
  try {
    let id = window.localStorage.getItem(CLIENT_ID_KEY);
    if (!id) {
      id = crypto.randomUUID();
      window.localStorage.setItem(CLIENT_ID_KEY, id);
    }
    return id;
  } catch {
    return null; // private mode or blocked storage: the backend falls back to the IP
  }
}

function clientHeaders(extra: Record<string, string> = {}): Record<string, string> {
  const id = clientId();
  return id ? { ...extra, "X-Client-Id": id } : extra;
}

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
    response = await fetch(url, { headers: clientHeaders(), signal: signal ? AbortSignal.any([signal, timeout]) : timeout });
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

const CHAT_TIMEOUT_MS = 50_000; // a web search answer takes 5–15 s

/** POST /chat — Kampi answers about a profile built in the last 30 minutes, only from its collected data. */
export async function askGuide(
  body: { wikidata_id: string; lang: Lang; message: string; history: { role: "user" | "assistant"; text: string }[] },
  signal?: AbortSignal,
): Promise<ChatMessage> {
  const timeout = AbortSignal.timeout(CHAT_TIMEOUT_MS);
  let response: Response;
  try {
    response = await fetch(`${API_URL}/chat`, {
      method: "POST",
      headers: clientHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(body),
      signal: signal ? AbortSignal.any([signal, timeout]) : timeout,
    });
  } catch (err) {
    throw new ApiError(`Network error: ${(err as Error).message}`, "network");
  }
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new ApiError(data.detail ?? response.statusText, "http", response.status);
  }
  return response.json();
}

const CAMPUS_TIMEOUT_MS = 20_000;

/** GET /campus/{id} — outline, typed buildings and photo pins for the campus map (docs/CONTRACT.md §4). */
export function loadCampus(wikidataId: string, lang: Lang, signal?: AbortSignal): Promise<CampusMap> {
  return getJson(`/campus/${encodeURIComponent(wikidataId)}?lang=${lang}`, CAMPUS_TIMEOUT_MS, signal);
}
