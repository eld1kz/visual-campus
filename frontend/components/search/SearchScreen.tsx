"use client";

import { useEffect, useRef, useState } from "react";
import { ServerErrorView } from "@/components/common/ServerErrorView";
import { ApiError, resolveUniversity } from "@/lib/api";
import type { ResolveResponse, UniversityCandidate } from "@/lib/types";
import { DisambiguationView } from "./DisambiguationView";
import { NotFoundView } from "./NotFoundView";
import { ResolvedView } from "./ResolvedView";
import { SearchHero } from "./SearchHero";

type State =
  | { kind: "idle" }
  | { kind: "loading"; query: string }
  | { kind: "result"; data: ResolveResponse; chosen: UniversityCandidate | null }
  | { kind: "error"; query: string; error: ApiError };

function errorCode(error: ApiError): string {
  if (error.kind === "network") return "ERR_NETWORK · resolve";
  const sources = error.sourcesStatus.map((s) => `${s.name}:${s.status}`).join(", ");
  return [`HTTP ${error.status}`, "resolve", sources].filter(Boolean).join(" · ");
}

export function SearchScreen() {
  const [query, setQuery] = useState("");
  const [state, setState] = useState<State>({ kind: "idle" });
  const inFlight = useRef<AbortController | null>(null);

  useEffect(() => () => inFlight.current?.abort(), []);

  async function search(raw: string) {
    const q = raw.trim();
    if (q.length < 2) return;
    inFlight.current?.abort();
    const controller = new AbortController();
    inFlight.current = controller;

    setQuery(q);
    setState({ kind: "loading", query: q });
    try {
      const data = await resolveUniversity(q, controller.signal);
      setState({ kind: "result", data, chosen: data.university });
    } catch (err) {
      if (controller.signal.aborted) return;
      const error = err instanceof ApiError ? err : new ApiError(String(err), "network");
      setState({ kind: "error", query: q, error });
    }
  }

  const reset = () => setState({ kind: "idle" });

  if (state.kind === "error") {
    return <ServerErrorView code={errorCode(state.error)} onRetry={() => search(state.query)} onBack={reset} />;
  }

  if (state.kind === "result") {
    const { data, chosen } = state;
    if (chosen) {
      return (
        <ResolvedView
          query={data.query}
          correctedQuery={data.corrected_query}
          university={chosen}
          sources={data.sources_status}
          tookMs={data.took_ms}
          onSearchAgain={reset}
        />
      );
    }
    if (data.status === "ambiguous") {
      return (
        <DisambiguationView
          query={data.query}
          correctedQuery={data.corrected_query}
          candidates={data.candidates}
          sources={data.sources_status}
          onChoose={(candidate) => setState({ kind: "result", data, chosen: candidate })}
          onNoneOfThese={() => setState({ kind: "result", data: { ...data, status: "not_found" }, chosen: null })}
        />
      );
    }
    return <NotFoundView query={data.query} sources={data.sources_status} onSearch={search} />;
  }

  return <SearchHero query={query} onQueryChange={setQuery} onSearch={search} busy={state.kind === "loading"} />;
}
