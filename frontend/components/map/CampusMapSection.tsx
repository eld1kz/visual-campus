"use client";

import { useEffect, useState } from "react";
import { usePreferences } from "@/components/layout/PreferencesProvider";
import { ApiError, getCampus } from "@/lib/api";
import { BUILDING_TYPES, hasHeights } from "@/lib/map/geometry";
import type { BuildingType, CampusMap as CampusMapData, Photo } from "@/lib/types";
import { BuildingCard } from "./BuildingCard";
import { CampusMap } from "./CampusMap";
import { CampusSummary } from "./CampusSummary";
import { LayerChips } from "./LayerChips";
import { MapFrame } from "./MapFrame";
import { MapToolbar } from "./MapToolbar";
import { PanoramaEmpty } from "./PanoramaEmpty";
import { PinCard } from "./PinCard";
import type { MapLayers, MapMode } from "./types";

type Props = {
  wikidataId: string;
  photos: Photo[];
  initialBuildingId?: string | null;
  onOpenPhoto: (photoId: string) => void;
};

type Load = { data: CampusMapData } | { error: string } | null;

export function CampusMapSection({ wikidataId, photos, initialBuildingId = null, onOpenPhoto }: Props) {
  const { t, lang } = usePreferences();
  const [load, setLoad] = useState<Load>(null);
  const [mode, setModeState] = useState<MapMode>("2d");
  const [flyover, setFlyover] = useState(false);
  const [recenterKey, setRecenterKey] = useState(0);
  const [buildingId, setBuildingId] = useState<string | null>(initialBuildingId);
  const [pinId, setPinId] = useState<string | null>(null);
  const [buildingQuery, setBuildingQuery] = useState("");
  const [layers, setLayers] = useState<MapLayers>({
    types: Object.fromEntries(BUILDING_TYPES.map((type) => [type, true])) as Record<BuildingType, boolean>,
    pins: true,
    unconfirmedPins: false,
  });

  useEffect(() => {
    const controller = new AbortController();
    getCampus(wikidataId, lang, controller.signal)
      .then((data) => setLoad({ data }))
      .catch((err: unknown) => {
        if (!controller.signal.aborted) setLoad({ error: err instanceof ApiError ? err.message : String(err) });
      });
    return () => controller.abort();
  }, [wikidataId, lang]);

  const setMode = (next: MapMode) => {
    setModeState(next);
    setFlyover(false);
    setPinId(null);
  };
  const selectBuilding = (id: string) => {
    setBuildingId(id);
    setPinId(null);
  };

  if (!load || "error" in load) {
    return (
      <MapFrame className="flex items-center justify-center p-6 text-center">
        <div className={`font-mono text-[11.5px] text-ink-3 ${load ? "" : "animate-[vc-pulse_1.2s_ease-in-out_infinite]"}`}>
          {load ? `${t.map.mapError} · ${load.error}` : t.map.loadingMap}
        </div>
      </MapFrame>
    );
  }

  const { data } = load;
  const selected = data.buildings.find((b) => b.id === buildingId) ?? null;
  const pin = data.photo_pins.find((p) => p.photo_id === pinId) ?? null;
  const pinPhoto = pin ? photos.find((p) => p.id === pin.photo_id) : undefined;
  const flatHeights = !hasHeights(data.buildings);

  return (
    <>
      <MapToolbar
        mode={mode}
        onMode={setMode}
        buildingQuery={buildingQuery}
        onBuildingQuery={setBuildingQuery}
        onRecenter={() => {
          setRecenterKey((k) => k + 1);
          setBuildingId(null);
          setPinId(null);
        }}
      />
      {mode !== "walk" && (
        <LayerChips
          layers={layers}
          presentTypes={BUILDING_TYPES.filter((type) => data.buildings.some((b) => b.type === type))}
          onToggleType={(type) => setLayers((l) => ({ ...l, types: { ...l.types, [type]: !l.types[type] } }))}
          onToggle={(layer) => setLayers((l) => ({ ...l, [layer]: !l[layer] }))}
        />
      )}

      <div className="flex flex-wrap items-start gap-[18px]">
        <div className="min-w-0 flex-[1_1_560px]">
          {mode === "walk" ? (
            <PanoramaEmpty checked={data.panoramas.checked_providers} onBack={() => setMode("3d")} />
          ) : (
            <>
              <CampusMap
                data={data}
                mode={mode}
                layers={layers}
                selectedBuildingId={buildingId}
                recenterKey={recenterKey}
                flyover={flyover}
                onSelectBuilding={selectBuilding}
                onSelectPin={(id) => {
                  setPinId(id);
                  setBuildingId(null);
                }}
              />
              <div className="flex flex-wrap items-start gap-3 pt-[9px]">
                <div className="max-w-[60ch] flex-1 text-[11.5px] leading-normal text-ink-3">
                  {!data.campus.polygon && <div>{t.map.noPolygonNote}</div>}
                  {mode === "3d" && <div>{flatHeights ? t.map.no3dHeights : t.map.note3d}</div>}
                </div>
                {mode === "3d" && (
                  <button
                    onClick={() => setFlyover((f) => !f)}
                    className="rounded-full border-none bg-surface-2 px-3.5 py-2 text-xs text-ink-2"
                  >
                    {flyover ? t.map.flyoverStop : t.map.flyover}
                  </button>
                )}
              </div>
            </>
          )}
        </div>

        <div className="flex min-w-0 max-w-[360px] flex-[1_1_300px] flex-col gap-4">
          {selected ? (
            <BuildingCard
              building={selected}
              photos={photos}
              flatHeights={flatHeights}
              onOpenPhoto={onOpenPhoto}
              onShow3d={() => setMode("3d")}
              onWalk={() => setMode("walk")}
              onClose={() => setBuildingId(null)}
            />
          ) : pin && pinPhoto ? (
            <PinCard pin={pin} photo={pinPhoto} onOpen={() => onOpenPhoto(pinPhoto.id)} onClose={() => setPinId(null)} />
          ) : (
            <CampusSummary
              data={data}
              buildingQuery={buildingQuery}
              selectedBuildingId={buildingId}
              onSelectBuilding={selectBuilding}
            />
          )}
        </div>
      </div>
    </>
  );
}
