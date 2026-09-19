"use client";

import { useEffect, useRef, useState } from "react";
import "maplibre-gl/dist/maplibre-gl.css";
import type { Map as MlMap } from "maplibre-gl";
import { usePreferences } from "@/components/layout/PreferencesProvider";
import { loadCampus } from "@/lib/api";
import { loadMaplibre, mapStyleUrl } from "@/lib/maplibre";
import type { BuildingType, CampusMap, ProfileUniversity } from "@/lib/types";

// MapLibre does not parse oklch(): the building palette of lib/map/geometry.ts in hex.
const TYPE_COLOR: Record<BuildingType, string> = {
  academic: "#6f7fc6",
  dorm: "#4f9bb0",
  library: "#4c9f7c",
  sport: "#a99a4c",
  lab: "#9477c0",
  food: "#c98a5e",
  other: "#9ea2ab",
};
const TIER_COLOR = { verified: "#2f8a55", likely: "#c28a1f", unconfirmed: "#9ea2ab" };
const CAMPUS_COLOR = "#4f5bd5";
const PITCH_3D = 60;
const LEVEL_M = 3.2;

type Props = {
  university: ProfileUniversity;
  onOpenPhoto: (photoId: string) => void;
};

type Mode = "2d" | "3d";

/** Real campus map from GET /campus: outline, typed buildings, photo pins, route to the centre; 2D or tilted 3D. */
export function LiveCampusMap({ university, onOpenPhoto }: Props) {
  const { t, lang, theme } = usePreferences();
  const container = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MlMap | null>(null);
  const [data, setData] = useState<CampusMap | null>(null);
  const [failed, setFailed] = useState(false);
  const [mode, setMode] = useState<Mode>("2d");
  const openPhoto = useRef(onOpenPhoto);
  const modeRef = useRef<Mode>("2d");
  useEffect(() => {
    openPhoto.current = onOpenPhoto;
  }, [onOpenPhoto]);

  useEffect(() => {
    const controller = new AbortController();
    loadCampus(university.id, lang, controller.signal)
      .then(setData)
      .catch(() => !controller.signal.aborted && setFailed(true));
    return () => controller.abort();
  }, [university.id, lang]);

  useEffect(() => {
    if (!data || !container.current) return;
    let cancelled = false;
    let map: MlMap | undefined;
    loadMaplibre().then((maplibregl) => {
      if (cancelled || !container.current) return;
      const { campus } = data;
      const bounds = new maplibregl.LngLatBounds([campus.center.lng, campus.center.lat], [campus.center.lng, campus.center.lat]);
      for (const point of campus.polygon ?? []) bounds.extend(point as [number, number]);
      for (const b of data.buildings) for (const point of b.polygon) bounds.extend(point as [number, number]);
      map = new maplibregl.Map({
        container: container.current,
        style: mapStyleUrl(),
        bounds,
        fitBoundsOptions: { padding: 48, maxZoom: 16.5 },
        cooperativeGestures: true,
        attributionControl: { compact: true },
      });
      mapRef.current = map;
      map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "top-right");

      map.on("load", () => {
        if (!map) return;
        const route = university.center_route?.geometry;
        if (campus.city_center) {
          const line = route?.length ? route : [[campus.center.lng, campus.center.lat], [campus.city_center.lng, campus.city_center.lat]];
          map.addSource("route", { type: "geojson", data: { type: "Feature", properties: {}, geometry: { type: "LineString", coordinates: line } } });
          map.addLayer({
            id: "route", type: "line", source: "route",
            layout: { "line-cap": "round", "line-join": "round" },
            paint: { "line-color": CAMPUS_COLOR, "line-width": 2.5, "line-opacity": 0.6, ...(route ? {} : { "line-dasharray": [2, 2] }) },
          });
          new maplibregl.Marker({ color: "#e0533d", scale: 0.7 }).setLngLat([campus.city_center.lng, campus.city_center.lat]).addTo(map);
        }

        if (campus.polygon?.length) {
          map.addSource("campus", { type: "geojson", data: { type: "Feature", properties: {}, geometry: { type: "Polygon", coordinates: [campus.polygon] } } });
          map.addLayer({ id: "campus-fill", type: "fill", source: "campus", paint: { "fill-color": CAMPUS_COLOR, "fill-opacity": 0.07 } });
          map.addLayer({ id: "campus-line", type: "line", source: "campus", paint: { "line-color": CAMPUS_COLOR, "line-width": 2, "line-dasharray": [3, 2] } });
        }

        // Every building of the basemap gets a volume in 3D (OpenMapTiles render_height).
        const basemap = Object.entries(map.getStyle().sources).find(([, s]) => s.type === "vector")?.[0];
        if (basemap) {
          map.addLayer({
            id: "basemap-3d", type: "fill-extrusion", source: basemap, "source-layer": "building", minzoom: 13,
            layout: { visibility: "none" },
            paint: {
              "fill-extrusion-color": theme === "dark" ? "#3a3d45" : "#d9dbe0",
              "fill-extrusion-height": ["coalesce", ["get", "render_height"], 10],
              "fill-extrusion-base": ["coalesce", ["get", "render_min_height"], 0],
              "fill-extrusion-opacity": 0.85,
            },
          });
        }

        const buildings = {
          type: "FeatureCollection" as const,
          features: data.buildings.map((b) => ({
            type: "Feature" as const,
            properties: {
              name: b.name, color: TYPE_COLOR[b.type] ?? TYPE_COLOR.other, inside: b.inside_campus,
              height: b.height_m ?? (b.levels ? b.levels * LEVEL_M : 12),
            },
            geometry: { type: "Polygon" as const, coordinates: [b.polygon] },
          })),
        };
        map.addSource("buildings", { type: "geojson", data: buildings });
        map.addLayer({
          id: "buildings-2d", type: "fill", source: "buildings",
          paint: { "fill-color": ["get", "color"], "fill-opacity": ["case", ["get", "inside"], 0.75, 0.3] },
        });
        map.addLayer({
          id: "buildings-3d", type: "fill-extrusion", source: "buildings", layout: { visibility: "none" },
          paint: {
            "fill-extrusion-color": ["get", "color"], "fill-extrusion-height": ["get", "height"],
            "fill-extrusion-opacity": 0.92,
          },
        });

        map.addSource("pins", {
          type: "geojson",
          data: {
            type: "FeatureCollection",
            features: data.photo_pins
              .filter((p) => p.tier !== "unconfirmed")
              .map((p) => ({
                type: "Feature" as const,
                properties: { id: p.photo_id, color: TIER_COLOR[p.tier] },
                geometry: { type: "Point" as const, coordinates: [p.lng, p.lat] },
              })),
          },
        });
        map.addLayer({
          id: "pins", type: "circle", source: "pins",
          paint: {
            "circle-radius": 5.5, "circle-color": ["get", "color"],
            "circle-stroke-color": "#ffffff", "circle-stroke-width": 1.5,
          },
        });
        map.on("click", "pins", (e) => {
          const id = e.features?.[0]?.properties?.id;
          if (typeof id === "string") openPhoto.current(id);
        });
        map.on("mouseenter", "pins", () => map && (map.getCanvas().style.cursor = "pointer"));
        map.on("mouseleave", "pins", () => map && (map.getCanvas().style.cursor = ""));
        applyMode(map, modeRef.current, false); // a map rebuilt (theme switch) keeps the chosen mode
      });
    });
    return () => {
      cancelled = true;
      mapRef.current = null;
      map?.remove();
    };
  }, [data, theme, university.center_route]);

  // 2D ⇄ 3D: flat typed footprints vs. tilted extruded buildings.
  useEffect(() => {
    modeRef.current = mode;
    const map = mapRef.current;
    if (map?.isStyleLoaded()) applyMode(map, mode, true);
  }, [mode]);

  if (failed) {
    return <div className="rounded-[20px] bg-surface-2 p-[38px] text-[13px] text-ink-3">{t.live.noMapFacts}</div>;
  }

  const counts = data ? countByType(data) : [];
  const pins = data?.photo_pins.filter((p) => p.tier !== "unconfirmed").length ?? 0;

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-2">
        {(["2d", "3d"] as const).map((m, i) => (
          <button
            key={m}
            onClick={() => setMode(m)}
            className={`rounded-full border-none px-4 py-2 text-[13px] ${
              mode === m ? "bg-ink font-medium text-bg" : "bg-surface-2 text-ink-2"
            }`}
          >
            {t.map.modes[i]}
          </button>
        ))}
        <span className="ml-auto font-mono text-xs text-ink-3">
          {data?.campus.area_km2 != null && `${data.campus.area_km2.toFixed(2)} ${t.km}² · `}
          {data && `${data.buildings.length} ${t.liveMap.buildings} · ${pins} ${t.liveMap.pins}`}
        </span>
      </div>

      <div ref={container} className="ph-grid h-[560px] overflow-hidden rounded-[20px] [--g:24px]" />

      <div className="flex flex-wrap gap-x-4 gap-y-1.5 text-xs text-ink-3">
        <Legend color={CAMPUS_COLOR} dashed label={t.liveMap.outline} />
        {counts.map(([type, n]) => (
          <Legend key={type} color={TYPE_COLOR[type]} label={`${t.map.types[type]} · ${n}`} />
        ))}
        <Legend color={TIER_COLOR.verified} dot label={t.verified} />
        <Legend color={TIER_COLOR.likely} dot label={t.likely} />
        <span className="basis-full text-[11.5px]">{t.liveMap.hint}</span>
        {data && data.buildings.length === 0 && <span className="basis-full text-[11.5px]">{t.liveMap.noBuildings}</span>}
      </div>
    </div>
  );
}

function applyMode(map: MlMap, mode: Mode, animate: boolean) {
  const three = mode === "3d";
  for (const [id, on] of [["buildings-2d", !three], ["buildings-3d", three], ["basemap-3d", three]] as const) {
    if (map.getLayer(id)) map.setLayoutProperty(id, "visibility", on ? "visible" : "none");
  }
  const camera = { pitch: three ? PITCH_3D : 0, bearing: three ? -20 : 0 };
  if (animate) map.easeTo({ ...camera, duration: 900 });
  else map.jumpTo(camera);
}

function countByType(data: CampusMap): [BuildingType, number][] {
  const counts = new Map<BuildingType, number>();
  for (const b of data.buildings) if (b.inside_campus) counts.set(b.type, (counts.get(b.type) ?? 0) + 1);
  return [...counts.entries()].sort((a, b) => b[1] - a[1]);
}

function Legend({ color, label, dot = false, dashed = false }: { color: string; label: string; dot?: boolean; dashed?: boolean }) {
  return (
    <span className="flex items-center gap-1.5">
      <span
        className={dot ? "size-2.5 rounded-full" : "h-2.5 w-3.5 rounded-[3px]"}
        style={dashed ? { border: `1.5px dashed ${color}` } : { background: color }}
      />
      {label}
    </span>
  );
}
