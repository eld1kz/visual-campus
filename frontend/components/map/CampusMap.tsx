"use client";

import { AttributionControl, Map as MapLibre, NavigationControl, type GeoJSONSource } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useEffect, useRef, useState } from "react";
import { usePreferences, type Theme } from "@/components/layout/PreferencesProvider";
import {
  ACCENT, BUILDING_TYPES, BUILDING_TYPE_COLOR, TIER_COLOR, boundsOf, buildingsGeoJson, campusBounds, campusGeoJson,
  cityGeoJson, pinsGeoJson,
} from "@/lib/map/geometry";
import type { CampusMap as CampusMapData } from "@/lib/types";
import { MapFrame } from "./MapFrame";
import type { MapViewProps } from "./types";

const STYLE_URL: Record<Theme, string> = {
  light: "https://tiles.openfreemap.org/styles/positron",
  dark: "https://tiles.openfreemap.org/styles/dark",
};
const FONT = ["Noto Sans Regular"];
const PITCH_3D = 58;
const BEARING_3D = -20;
const FALLBACK_ZOOM = 16;
const FIT = { padding: 48, maxZoom: 17.5 };
const FLYOVER_DEG_PER_TICK = 0.3;
const FLYOVER_TICK_MS = 40;

const LAYERS_2D = ["campus-buildings-fill", "campus-buildings-line"];
const LAYERS_3D = ["osm-buildings-3d", "campus-buildings-3d"];
const CLICKABLE = ["campus-buildings-fill", "campus-buildings-3d", "pins", "pin-clusters"];

/** The map is only rendered on the client (after /campus answers), so this never runs on the server. */
function webglSupported(): boolean {
  try {
    return Boolean(document.createElement("canvas").getContext("webgl2") ?? document.createElement("canvas").getContext("webgl"));
  } catch {
    return false;
  }
}

/** Custom sources and layers on top of the base style; a new style (theme switch) drops them, so re-run on style.load. */
function addOverlays(map: MapLibre, data: CampusMapData, theme: Theme, cityLabel: string) {
  const ink = theme === "dark" ? "#f1f1ef" : "#17181a";
  const halo = theme === "dark" ? "#17181a" : "#ffffff";
  const typeColor = ["match", ["get", "type"], ...BUILDING_TYPES.flatMap((type) => [type, BUILDING_TYPE_COLOR[type]]), BUILDING_TYPE_COLOR.other];
  const tierColor = ["match", ["get", "tier"], "verified", TIER_COLOR.verified, "likely", TIER_COLOR.likely, TIER_COLOR.unconfirmed];
  const kind = (value: string) => ["==", ["get", "kind"], value] as never;

  map.addSource("campus", { type: "geojson", data: campusGeoJson(data) });
  map.addSource("buildings", { type: "geojson", data: buildingsGeoJson(data.buildings) });
  map.addSource("pins", { type: "geojson", data: pinsGeoJson([]), cluster: true, clusterRadius: 36, clusterMaxZoom: 17 });
  map.addSource("city", { type: "geojson", data: cityGeoJson(data, cityLabel) });

  map.addLayer({
    id: "city-line", type: "line", source: "city", filter: kind("line"),
    paint: { "line-color": "#6b7079", "line-width": 1.5, "line-dasharray": [3, 3], "line-opacity": 0.7 },
  });
  map.addLayer({ id: "campus-fill", type: "fill", source: "campus", filter: kind("outline"), paint: { "fill-color": ACCENT, "fill-opacity": 0.08 } });
  map.addLayer({ id: "campus-line", type: "line", source: "campus", filter: kind("outline"), paint: { "line-color": ACCENT, "line-width": 2 } });
  // Every OSM building from the vector tiles, extruded by its real height — the 3D context around the campus.
  map.addLayer({
    id: "osm-buildings-3d", type: "fill-extrusion", source: "openmaptiles", "source-layer": "building", minzoom: 14,
    paint: {
      "fill-extrusion-color": theme === "dark" ? "#3a3d42" : "#d9d9d6",
      "fill-extrusion-height": ["coalesce", ["get", "render_height"], 8],
      "fill-extrusion-base": ["coalesce", ["get", "render_min_height"], 0],
      "fill-extrusion-opacity": 0.85,
    },
  });
  map.addLayer({
    id: "campus-buildings-fill", type: "fill", source: "buildings",
    paint: { "fill-color": typeColor as never, "fill-opacity": ["case", ["get", "inside"], 0.75, 0.3] },
  });
  map.addLayer({ id: "campus-buildings-line", type: "line", source: "buildings", paint: { "line-color": ink, "line-width": 2.5, "line-opacity": 0 } });
  map.addLayer({
    id: "campus-buildings-3d", type: "fill-extrusion", source: "buildings",
    paint: { "fill-extrusion-color": typeColor as never, "fill-extrusion-height": ["get", "height"], "fill-extrusion-opacity": 0.9 },
  });
  map.addLayer({
    id: "campus-center", type: "circle", source: "campus", filter: kind("center"),
    paint: { "circle-radius": 6, "circle-color": ACCENT, "circle-stroke-width": 5, "circle-stroke-color": ACCENT, "circle-stroke-opacity": 0.25 },
  });
  map.addLayer({ id: "city-point", type: "circle", source: "city", filter: kind("city"), paint: { "circle-radius": 5, "circle-color": "#5c6066" } });
  map.addLayer({
    id: "city-label", type: "symbol", source: "city", filter: kind("city"),
    layout: { "text-field": ["get", "label"], "text-font": FONT, "text-size": 12, "text-offset": [0, 1.3], "text-anchor": "top" },
    paint: { "text-color": ink, "text-halo-color": halo, "text-halo-width": 1.5 },
  });
  map.addLayer({
    id: "pin-clusters", type: "circle", source: "pins", filter: ["has", "point_count"],
    paint: { "circle-radius": 15, "circle-color": "#ffffff", "circle-stroke-width": 2, "circle-stroke-color": "#5c6066" },
  });
  map.addLayer({
    id: "pin-count", type: "symbol", source: "pins", filter: ["has", "point_count"],
    layout: { "text-field": ["get", "point_count_abbreviated"], "text-font": FONT, "text-size": 11 },
  });
  map.addLayer({
    id: "pins", type: "circle", source: "pins", filter: ["!", ["has", "point_count"]],
    paint: { "circle-radius": 8, "circle-color": "#ffffff", "circle-stroke-width": 3, "circle-stroke-color": tierColor as never },
  });
}

/** MapLibre GL map on OpenFreeMap tiles: real streets and buildings, with the /campus data on top. */
export function CampusMap(props: MapViewProps) {
  const { t, theme } = usePreferences();
  const { data, mode, layers, selectedBuildingId, recenterKey, flyover } = props;
  const container = useRef<HTMLDivElement>(null);
  const [supported] = useState(webglSupported);
  /** Set once overlays exist; `version` changes after every style load so the effects re-apply. */
  const [ready, setReady] = useState<{ map: MapLibre; version: number } | null>(null);

  const cityLabel = data.campus.city_center
    ? `${data.campus.city_center.name}${
        data.campus.distance_to_center_km != null ? ` · ${data.campus.distance_to_center_km.toFixed(1)} ${t.km}` : ""
      }`
    : "";

  // Latest values for MapLibre callbacks, which are registered once per map.
  const latest = useRef({ props, theme, cityLabel });
  /** Theme of the style currently loaded in the map. */
  const styleTheme = useRef<Theme | null>(null);
  useEffect(() => {
    latest.current = { props, theme, cityLabel };
  });

  useEffect(() => {
    if (!supported || !container.current) return;
    const bounds = campusBounds(data);
    const { center } = data.campus;
    const map = new MapLibre({
      container: container.current,
      style: STYLE_URL[latest.current.theme],
      attributionControl: false,
      ...(bounds ? { bounds, fitBoundsOptions: FIT } : { center: [center.lng, center.lat], zoom: FALLBACK_ZOOM }),
    });
    map.addControl(new AttributionControl({ compact: true }));
    map.addControl(new NavigationControl({ visualizePitch: true }), "bottom-right");
    map.on("style.load", () => {
      styleTheme.current = latest.current.theme;
      addOverlays(map, data, latest.current.theme, latest.current.cityLabel);
      setReady((r) => ({ map, version: (r?.version ?? 0) + 1 }));
    });

    for (const layer of ["campus-buildings-fill", "campus-buildings-3d"]) {
      map.on("click", layer, (e) => {
        const id = e.features?.[0]?.properties?.id;
        if (typeof id === "string") latest.current.props.onSelectBuilding(id);
      });
    }
    map.on("click", "pins", (e) => {
      const id = e.features?.[0]?.properties?.photo_id;
      if (typeof id === "string") latest.current.props.onSelectPin(id);
    });
    map.on("click", "pin-clusters", async (e) => {
      const feature = e.features?.[0];
      if (!feature || feature.geometry.type !== "Point") return;
      const zoom = await map.getSource<GeoJSONSource>("pins")?.getClusterExpansionZoom(feature.properties.cluster_id);
      if (zoom != null) map.easeTo({ center: feature.geometry.coordinates as [number, number], zoom });
    });
    for (const layer of CLICKABLE) {
      map.on("mouseenter", layer, () => (map.getCanvas().style.cursor = "pointer"));
      map.on("mouseleave", layer, () => (map.getCanvas().style.cursor = ""));
    }
    return () => map.remove();
  }, [data, supported]);

  // Theme: swap the base style; style.load re-adds the overlays in the new colours.
  const map = ready?.map;
  useEffect(() => {
    if (map && styleTheme.current !== theme) map.setStyle(STYLE_URL[theme]);
  }, [map, theme]);

  // Mode: camera tilt and which building layers are drawn.
  useEffect(() => {
    if (!ready) return;
    for (const id of LAYERS_2D) ready.map.setLayoutProperty(id, "visibility", mode === "2d" ? "visible" : "none");
    for (const id of LAYERS_3D) ready.map.setLayoutProperty(id, "visibility", mode === "3d" ? "visible" : "none");
    ready.map.setMaxPitch(mode === "3d" ? 85 : 0);
    ready.map.easeTo(mode === "3d" ? { pitch: PITCH_3D, bearing: BEARING_3D } : { pitch: 0, bearing: 0 });
  }, [ready, mode]);

  // Building type chips and the selected building's highlight.
  useEffect(() => {
    if (!ready) return;
    const enabled = BUILDING_TYPES.filter((type) => layers.types[type]);
    const filter = ["in", ["get", "type"], ["literal", enabled]] as never;
    for (const id of ["campus-buildings-fill", "campus-buildings-line", "campus-buildings-3d"]) ready.map.setFilter(id, filter);
    const isSelected = ["==", ["get", "id"], selectedBuildingId ?? ""];
    ready.map.setPaintProperty("campus-buildings-line", "line-opacity", ["case", isSelected, 1, 0] as never);
    ready.map.setPaintProperty("campus-buildings-3d", "fill-extrusion-color", [
      "case", isSelected, ACCENT, ready.map.getPaintProperty("campus-buildings-fill", "fill-color"),
    ] as never);
  }, [ready, layers.types, selectedBuildingId]);

  // Photo pins: unconfirmed ones only when asked.
  useEffect(() => {
    if (!ready) return;
    const pins = layers.pins ? data.photo_pins.filter((p) => p.tier !== "unconfirmed" || layers.unconfirmedPins) : [];
    ready.map.getSource<GeoJSONSource>("pins")?.setData(pinsGeoJson(pins));
  }, [ready, data, layers.pins, layers.unconfirmedPins]);

  // Fly to the selected building.
  useEffect(() => {
    const building = data.buildings.find((b) => b.id === selectedBuildingId);
    const bounds = building && boundsOf(building.polygon);
    if (map && bounds) map.fitBounds(bounds, { padding: 120, maxZoom: 18 });
  }, [map, data, selectedBuildingId]);

  // «Centre on campus».
  useEffect(() => {
    const { mode: current } = latest.current.props;
    if (!map || recenterKey === 0) return;
    const bounds = campusBounds(data);
    const camera = current === "3d" ? { pitch: PITCH_3D, bearing: BEARING_3D } : { pitch: 0, bearing: 0 };
    if (bounds) map.fitBounds(bounds, { ...FIT, ...camera });
    else map.easeTo({ center: [data.campus.center.lng, data.campus.center.lat], zoom: FALLBACK_ZOOM, ...camera });
  }, [map, data, recenterKey]);

  // Flyover: slow rotation around the current centre.
  useEffect(() => {
    if (!map || !flyover) return;
    const timer = setInterval(() => map.setBearing(map.getBearing() + FLYOVER_DEG_PER_TICK), FLYOVER_TICK_MS);
    return () => clearInterval(timer);
  }, [map, flyover]);

  if (!supported) {
    return (
      <MapFrame className="flex items-center justify-center p-6 text-center text-[13px] text-ink-3">{t.map.mapUnsupported}</MapFrame>
    );
  }
  return (
    <MapFrame>
      <div ref={container} className="h-full w-full" />
    </MapFrame>
  );
}
