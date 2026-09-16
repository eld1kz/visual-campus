"use client";

import { useSearchParams } from "next/navigation";
import { useCallback, useState } from "react";
import { usePreferences } from "@/components/layout/PreferencesProvider";
import { CampusMapSection } from "@/components/map/CampusMapSection";
import { PhotoDetail } from "@/components/photos/PhotoDetail";
import { PhotosSection } from "@/components/photos/PhotosSection";
import { DemoDataPlate } from "@/components/ui/DemoDataPlate";
import { WarningBanner } from "@/components/ui/WarningBanner";
import { MAP } from "@/lib/mock/map";
import { PROFILE, PROFILE_STATS } from "@/lib/mock/profile";
import { CATEGORIES, type PhotoTab } from "@/lib/photos";
import type { Photo, PhotoCategory } from "@/lib/types";
import { AboutSection } from "./AboutSection";
import { ProfileHeader } from "./ProfileHeader";
import { SectionTabs, type ProfileSection } from "./SectionTabs";

type OpenPhoto = { list: Photo[]; index: number };

const byConfidence = [...PROFILE.photos].sort((a, b) => b.confidence - a.confidence);

/** Query params (section, tab, building, photo) come from guide actions; a change remounts the view. */
export function ProfileScreen() {
  const params = useSearchParams();
  return <ProfileView key={params.toString()} params={params} />;
}

function ProfileView({ params }: { params: URLSearchParams }) {
  const { t } = usePreferences();
  const tabParam = params.get("tab");
  const initialTab: PhotoTab = CATEGORIES.includes(tabParam as PhotoCategory) ? (tabParam as PhotoCategory) : "all";

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
      <DemoDataPlate className="mb-[18px]" />
      {banner && (
        <WarningBanner onDismiss={() => setBanner(false)} className="mb-[22px]">
          {t.bannerFlickr}
        </WarningBanner>
      )}

      <ProfileHeader university={PROFILE.university} generatedInMs={PROFILE.generated_in_ms} stats={PROFILE_STATS} />
      <AboutSection profile={PROFILE} onOpenMap={() => setSection("map")} />
      <SectionTabs active={section} onChange={setSection} />

      {section === "photos" && (
        <PhotosSection
          photos={PROFILE.photos}
          sources={PROFILE.sources_status}
          initialTab={initialTab}
          onOpen={(list, index) => setOpen({ list, index })}
        />
      )}

      {section === "map" && (
        <CampusMapSection
          data={MAP}
          photos={PROFILE.photos}
          initialBuildingId={params.get("building")}
          onOpenPhoto={openById}
        />
      )}

      {open &&<PhotoDetail photo={open.list[open.index]} onPrev={prev} onNext={next} onClose={close} />}
    </div>
  );
}
