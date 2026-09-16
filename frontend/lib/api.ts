import type { ResolveResponse, SourceStatus } from "@/lib/types";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

const REQUEST_TIMEOUT_MS = 20_000;

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

export async function resolveUniversity(query: string, signal?: AbortSignal): Promise<ResolveResponse> {
  const url = `${API_URL}/resolve?q=${encodeURIComponent(query)}`;
  const timeout = AbortSignal.timeout(REQUEST_TIMEOUT_MS);
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
