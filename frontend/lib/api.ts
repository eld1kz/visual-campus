import type { Lang } from "@/lib/i18n";
import type { ProfileResponse, ResolveResponse, SourceStatus } from "@/lib/types";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

const RESOLVE_TIMEOUT_MS = 20_000;
/** Building a profile queries four sources; the backend budget is ≤30 s. */
const PROFILE_TIMEOUT_MS = 45_000;

export class ApiError extends Error {
  constructor(
    message: string,
    readonly kind: "network" | "http",
    readonly status: number | null = null,
    readonly sourcesStatus: SourceStatus[] = [],
  ) {
    super(message);
  }
}

export function resolveUniversity(query: string, signal?: AbortSignal): Promise<ResolveResponse> {
  return getJson(`/resolve?q=${encodeURIComponent(query)}`, RESOLVE_TIMEOUT_MS, signal);
}

export function getProfile(wikidataId: string, lang: Lang, signal?: AbortSignal): Promise<ProfileResponse> {
  return getJson(`/profile/${encodeURIComponent(wikidataId)}?lang=${lang}`, PROFILE_TIMEOUT_MS, signal);
}

async function getJson<T>(path: string, timeoutMs: number, signal?: AbortSignal): Promise<T> {
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
  return response.json();
}
