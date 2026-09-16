"use client";

import { useSearchParams } from "next/navigation";
import { PROFILE, PROFILE_STATS } from "@/lib/mock/profile";
import { LiveProfile } from "./LiveProfile";
import { ProfileView } from "./ProfileView";

const WIKIDATA_ID = /^Q\d+$/;

/**
 * /profile?id=Q39997 → real profile from the API; /profile without an id → the design's demo profile.
 * Other query params (section, tab, building, photo) come from guide actions; a change remounts the view.
 */
export function ProfileScreen() {
  const params = useSearchParams();
  const id = params.get("id");

  if (id && WIKIDATA_ID.test(id)) {
    return <LiveProfile key={params.toString()} wikidataId={id} name={params.get("name")} params={params} />;
  }
  return <ProfileView key={params.toString()} profile={PROFILE} stats={PROFILE_STATS} live={false} params={params} />;
}
