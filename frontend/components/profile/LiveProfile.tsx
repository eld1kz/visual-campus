"use client";

import { useRouter } from "next/navigation";
import { ServerErrorView } from "@/components/common/ServerErrorView";
import { usePreferences } from "@/components/layout/PreferencesProvider";
import type { ApiError } from "@/lib/api";
import { useProfile } from "@/lib/useProfile";
import { ProfileLoading } from "./ProfileLoading";
import { ProfileView } from "./ProfileView";

function errorCode(error: ApiError, wikidataId: string): string {
  if (error.kind === "network") return `ERR_NETWORK · profile · ${wikidataId}`;
  return `HTTP ${error.status} · profile · ${wikidataId} · ${error.message}`;
}

/** Profile built by the backend from real sources (GET /profile/{wikidataId}). */
export function LiveProfile({ wikidataId, name, params }: { wikidataId: string; name: string | null; params: URLSearchParams }) {
  const { lang } = usePreferences();
  const router = useRouter();
  const { state, retry } = useProfile(wikidataId, lang);

  if (state.kind === "loading") return <ProfileLoading name={name} elapsedMs={state.elapsedMs} />;
  if (state.kind === "error") {
    return <ServerErrorView code={errorCode(state.error, wikidataId)} onRetry={retry} onBack={() => router.push("/")} />;
  }
  return <ProfileView profile={state.data} stats={state.data.stats} live params={params} />;
}
