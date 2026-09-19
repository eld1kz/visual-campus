"use client";

import { useEffect, useState } from "react";
import { usePreferences } from "@/components/layout/PreferencesProvider";
import { BUILDING_TYPES, polygonPoints, projectionFor } from "@/lib/map/geometry";
import type { BuildingType, CampusMap, Photo } from "@/lib/types";
import { BuildingCard } from "./BuildingCard";
import { CampusSummary } from "./CampusSummary";
import { DemoStateToggles } from "./DemoStateToggles";
import { LayerChips } from "./LayerChips";
import { Map2DPlaceholder } from "./Map2DPlaceholder";
import { Map3DPlaceholder } from "./Map3DPlaceholder";
import { CampusPolygon, MapFrame } from "./MapFrame";
import { MapToolbar } from "./MapToolbar";
import { PinCard } from "./PinCard";
import type { MapCamera, MapDemoFlags, MapLayers, MapMode, MapViewProps } from "./types";

const SKELETON_MS = 850;
const SELECTED_ZOOM = 1.7;
const DEFAULT_CAMERA: MapCamera = { zoom: 1, bearing: 0, tilt: 58 };

type Props = {
  data: CampusMap;
  photos: Photo[];
  initialBuildingId?: string | null;
  onOpenPhoto: (photoId: string) => void;
};

export function CampusMapSection({ data, photos, initialBuildingId = null, onOpenPhoto }: Props) {
  const { t } = usePreferences();
  const [ready, setReady] = useState(false);
  const [mode, setModeState] = useState<MapMode>("2d");
  const [camera, setCamera] = useState<MapCamera>(
    initialBuildingId ? { ...DEFAULT_CAMERA, zoom: SELECTED_ZOOM } : DEFAULT_CAMERA,
  );
  const [flyover, setFlyover] = useState(false);
  const [buildingId, setBuildingId] = useState<string | null>(initialBuildingId);
  const [pinId, setPinId] = useState<string | null>(null);
  const [buildingQuery, setBuildingQuery] = useState("");
  const [layers, setLayers] = useState<MapLayers>({
    types: Object.fromEntries(BUILDING_TYPES.map((type) => [type, true])) as Record<BuildingType, boolean>,
    pins: true,
    unconfirmedPins: false,
    transit: true,
  });
  const [flags, setFlags] = useState<MapDemoFlags>({ noPolygon: false, noHeights: false, no3d: false });

  useEffect(() => {
    const timer = setTimeout(() => setReady(true), SKELETON_MS);
    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (!flyover) return;
    const timer = setInterval(() => setCamera((c) => ({ ...c, bearing: (c.bearing + 0.8) % 360 })), 60);
    return () => clearInterval(timer);
  }, [flyover]);

  const setMode = (next: MapMode) => {
    setModeState(next === "3d" && flags.no3d ? "2d" : next);
    setFlyover(false);
    setPinId(null);
  };
  const selectBuilding = (id: string) => {
    setBuildingId(id);
    setPinId(null);
    setCamera((c) => ({ ...c, zoom: SELECTED_ZOOM }));
  };
  const toggleFlag = (flag: keyof MapDemoFlags) => {
    const on = !flags[flag];
    setFlags({ ...flags, [flag]: on });
    if (flag === "no3d" && on && mode === "3d") setModeState("2d");
  };

  const selected = data.buildings.find((b) => b.id === buildingId) ?? null;
  const pin = data.photo_pins.find((p) => p.photo_id === pinId) ?? null;
  const pinPhoto = pin ? photos.find((p) => p.id === pin.photo_id) : undefined;

  const viewProps: MapViewProps = {
    data,
    camera,
    layers,
    showPolygon: !flags.noPolygon,
    flatHeights: flags.noHeights,
    selectedBuildingId: buildingId,
    onSelectBuilding: selectBuilding,
    onSelectPin: (id) => {
      setPinId(id);
      setBuildingId(null);
    },
    onZoomToCluster: () => {
      setCamera((c) => ({ ...c, zoom: 1.8 }));
      setPinId(null);
      setBuildingId(null);
    },
    onCameraChange: (change) => setCamera((c) => ({ ...c, ...change })),
  };

  return (
    <>
      <MapToolbar
        mode={mode}
        onMode={setMode}
        buildingQuery={buildingQuery}
        onBuildingQuery={setBuildingQuery}
        onRecenter={() => {
          setCamera((c) => ({ ...c, zoom: 1, bearing: 0 }));
          setBuildingId(null);
          setPinId(null);
        }}
      />
      {flags.no3d && (
        <div className="mb-3 rounded-full bg-surface-2 px-[15px] py-2.5 text-[12.5px] text-ink-2">{t.map.no3dDevice}</div>
      )}
      <LayerChips
        layers={layers}
        onToggleType={(type) => setLayers((l) => ({ ...l, types: { ...l.types, [type]: !l.types[type] } }))}
        onToggle={(layer) => setLayers((l) => ({ ...l, [layer]: !l[layer] }))}
      />

      <div className="flex flex-wrap items-start gap-[18px]">
        <div className="min-w-0 flex-[1_1_560px]">
          {!ready ? (
            <MapFrame>
              {data.campus.polygon && (
                <div className="absolute inset-0 animate-[vc-in_.4s_ease_both]">
                  <CampusPolygon points={polygonPoints(data.campus.polygon, projectionFor(data))} fillOpacity={0.07} />
                </div>
              )}
              <div className="absolute inset-x-0 bottom-4 animate-[vc-pulse_1.2s_ease-in-out_infinite] text-center font-mono text-[11.5px] text-ink-3">
                {t.map.loadingMap}
              </div>
            </MapFrame>
          ) : mode === "2d" ? (
            <Map2DPlaceholder {...viewProps} />
          ) : (
            <Map3DPlaceholder {...viewProps} flyover={flyover} onToggleFlyover={() => setFlyover((f) => !f)} />
          )}
          {flags.noPolygon && (
            <div className="max-w-[60ch] pt-[9px] text-xs leading-normal text-ink-3">{t.map.noPolygonNote}</div>
          )}
        </div>

        <div className="flex min-w-0 max-w-[360px] flex-[1_1_300px] flex-col gap-4">
          {selected ? (
            <BuildingCard
              building={selected}
              photos={photos}
              flatHeights={flags.noHeights}
              onOpenPhoto={onOpenPhoto}
              onShow3d={() => setMode("3d")}
              onClose={() => {
                setBuildingId(null);
                setCamera((c) => ({ ...c, zoom: 1 }));
              }}
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
          <DemoStateToggles flags={flags} onToggle={toggleFlag} />
        </div>
      </div>
    </>
  );
}
