"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { ServerErrorView } from "@/components/common/ServerErrorView";
import { useGuide } from "@/components/guide/GuideProvider";
import { usePreferences } from "@/components/layout/PreferencesProvider";
import type { ApiError } from "@/lib/api";
import type { Dict } from "@/lib/i18n";
import { useProfile } from "@/lib/useProfile";
import { ProfileLoading } from "./ProfileLoading";
import { ProfileView } from "./ProfileView";

function errorCode(error: ApiError, wikidataId: string): string {
  if (error.kind === "network") return `ERR_NETWORK · profile · ${wikidataId}`;
  if (error.kind === "stream") return `ERR_STREAM · profile · ${wikidataId} · ${error.message}`;
  return `HTTP ${error.status} · profile · ${wikidataId} · ${error.message}`;
}

function errorCopy(error: ApiError, t: Dict): { title?: string; body?: string } {
  if (error.kind === "stream") return { title: t.live.streamTitle, body: t.live.streamBody };
  if (error.status === 404) return { title: t.live.err404Title, body: t.live.err404Body };
  if (error.status === 422) return { title: t.live.err422Title, body: t.live.err422Body };
  if (error.status === 503) return { title: t.live.err503Title, body: t.live.err503Body };
  return {};
}

/** Profile built by the backend from real sources (GET /profile/{wikidataId}). */
export function LiveProfile({ wikidataId, name, params }: { wikidataId: string; name: string | null; params: URLSearchParams }) {
  const { t, lang } = usePreferences();
  const router = useRouter();
  const { setAvailable } = useGuide();
  const { state, retry } = useProfile(wikidataId, lang);

  // The guide only knows the demo university: keep its FAB and chat off while a real profile is shown.
  useEffect(() => {
    setAvailable(false);
    return () => setAvailable(true);
  }, [setAvailable]);

  const home = () => router.push("/");
  if (state.kind === "loading") {
    return <ProfileLoading name={name} progress={state.progress} elapsedMs={state.elapsedMs} onCancel={home} />;
  }
  if (state.kind === "error") {
    const view = (
      <ServerErrorView
        {...errorCopy(state.error, t)}
        code={errorCode(state.error, wikidataId)}
        onRetry={retry}
        onBack={() => router.push("/")}
        compact={state.error.kind === "stream"}
      />
    );
    // A broken stream keeps what already arrived on screen.
    if (state.error.kind !== "stream") return view;
    return (
      <ProfileLoading
        name={name}
        progress={state.progress}
        elapsedMs={null}
        onCancel={home}
        header={
          <>
            {view}
            <div className="micro-label mb-3">{t.live.received}</div>
          </>
        }
      />
    );
  }
  const { profile, stats, partial } = state.ready;
  return <ProfileView profile={profile} stats={stats} live partial={partial} params={params} onBack={home} />;
}
