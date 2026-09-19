"use client";

import { useCallback, useMemo, useState, useEffect } from "react";
import { BackButton } from "@/components/ui/BackButton";
import { useGuide } from "@/components/guide/GuideProvider";
import { GuideGreeting } from "@/components/guide/GuideGreeting";
import { usePreferences } from "@/components/layout/PreferencesProvider";
import { CampusMapSection } from "@/components/map/CampusMapSection";
import { PhotoDetail } from "@/components/photos/PhotoDetail";
import { PhotosSection } from "@/components/photos/PhotosSection";
import { DemoDataPlate } from "@/components/ui/DemoDataPlate";
import { WarningBanner } from "@/components/ui/WarningBanner";
import { MAP } from "@/lib/mock/map";
import { CATEGORIES, type PhotoTab } from "@/lib/photos";
import type { Photo, PhotoCategory, Profile, ProfileStats } from "@/lib/types";
import { AboutSection } from "./AboutSection";
import { LiveCampusMap } from "./LiveCampusMap";
import { PartialBanner } from "./PartialBanner";
import { ProfileHeader } from "./ProfileHeader";
import { SectionTabs, type ProfileSection } from "./SectionTabs";

type OpenPhoto = { list: Photo[]; index: number };

type Props = {
  profile: Profile;
  stats: ProfileStats;
  /** true: data from GET /profile; false: the design's demo data. */
  live: boolean;
  /** Live only: the backend marked the profile incomplete (done.partial). */
  partial?: boolean;
  params: URLSearchParams;
  /** Live profiles: back to a new search. */
  onBack?: () => void;
};

export function ProfileView({ profile, stats, live, partial = false, params, onBack }: Props) {
  const { setAvailable } = useGuide();
  // The demo profile has canned answers about the demo university; a live profile turns the guide on itself.
  useEffect(() => {
    if (live) return;
    setAvailable(true);
    return () => setAvailable(false);
  }, [live, setAvailable]);
  const { t } = usePreferences();
  const tabParam = params.get("tab");
  const initialTab: PhotoTab = CATEGORIES.includes(tabParam as PhotoCategory) ? (tabParam as PhotoCategory) : "all";
  const byConfidence = useMemo(() => [...profile.photos].sort((a, b) => b.confidence - a.confidence), [profile.photos]);

  const [section, setSection] = useState<ProfileSection>(params.get("section") === "map" ? "map" : "photos");
  const [banner, setBanner] = useState(true);
  const [open, setOpen] = useState<OpenPhoto | null>(() => {
    const index = byConfidence.findIndex((p) => p.id === params.get("photo"));
    return index >= 0 ? { list: byConfidence, index } : null;
  });

  const step = useCallback(
    (delta: number) =>
      setOpen((cur) => cur && { ...cur, index: (cur.index + delta + cur.list.length) % cur.list.length }),
    [],
  );
  const close = useCallback(() => setOpen(null), []);
  const prev = useCallback(() => step(-1), [step]);
  const next = useCallback(() => step(1), [step]);
  const openById = (id: string) => {
    const index = byConfidence.findIndex((p) => p.id === id);
    if (index >= 0) setOpen({ list: byConfidence, index });
  };

  return (
    <div className="mx-auto max-w-[1240px] px-[22px] pb-[90px] pt-[30px]">
      {onBack && (
        <BackButton onClick={onBack} className="mb-3">
          {t.navNewSearch}
        </BackButton>
      )}
      {live ? (
        <PartialBanner partial={partial} sources={profile.sources_status} />
      ) : (
        <>
          <DemoDataPlate className="mb-[18px]" />
          {banner && (
            <WarningBanner onDismiss={() => setBanner(false)} className="mb-[22px]">
              {t.bannerFlickr}
            </WarningBanner>
          )}
        </>
      )}

      <ProfileHeader
        university={profile.university}
        generatedInMs={profile.generated_in_ms}
        stats={stats}
        aside={
          <GuideGreeting universityName={profile.university.name} />
        }
      />
      <AboutSection profile={profile} onOpenMap={() => setSection("map")} />
      <SectionTabs active={section} onChange={setSection} />

      {section === "photos" && (
        <PhotosSection
          photos={profile.photos}
          sources={profile.sources_status}
          initialTab={initialTab}
          onOpen={(list, index) => setOpen({ list, index })}
        />
      )}

      {section === "map" &&
        (live ? (
          <LiveCampusMap university={profile.university} photos={profile.photos} onOpenPhoto={openById} />
        ) : (
          <CampusMapSection
            data={MAP}
            photos={profile.photos}
            initialBuildingId={params.get("building")}
            onOpenPhoto={openById}
          />
        ))}

      {open && <PhotoDetail photo={open.list[open.index]} onPrev={prev} onNext={next} onClose={close} />}
    </div>
  );
}
