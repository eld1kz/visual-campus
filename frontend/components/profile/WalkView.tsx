"use client";

import { useEffect, useRef, useState } from "react";
import "maplibre-gl/dist/maplibre-gl.css";
import "mapillary-js/dist/mapillary.css";
import type { Map as MlMap, Marker } from "maplibre-gl";
import type { Viewer } from "mapillary-js";
import { usePreferences } from "@/components/layout/PreferencesProvider";
import { loadMaplibre, mapStyleUrl } from "@/lib/maplibre";
import type { CampusMap } from "@/lib/types";

const TOKEN = process.env.NEXT_PUBLIC_MAPILLARY_TOKEN ?? "";
const POINT_COLOR = "#4f5bd5";

type Point = { image_id: string; lat: number; lng: number; captured_at: string | null };
type Props = { data: CampusMap; startId: string };

/** Walk mode: the MapillaryJS street-level viewer next to a small map of every shot around the campus. */
export function WalkView({ data, startId }: Props) {
  const { t, lang, theme } = usePreferences();
  const viewerBox = useRef<HTMLDivElement>(null);
  const mapBox = useRef<HTMLDivElement>(null);
  const viewerRef = useRef<Viewer | null>(null);
  const markerRef = useRef<Marker | null>(null);
  const [current, setCurrent] = useState<{ lng: number; lat: number; capturedAt: number } | null>(null);
  const [failed, setFailed] = useState(!TOKEN);
  const points = (data.panoramas.points ?? []).filter((p): p is Point => Boolean(p.image_id));

  // Street-level viewer, started at the given image.
  useEffect(() => {
    if (!TOKEN || !viewerBox.current) return;
    let viewer: Viewer | undefined;
    let cancelled = false;
    import("mapillary-js")
      .then(({ Viewer }) => {
        if (cancelled || !viewerBox.current) return;
        viewer = new Viewer({ accessToken: TOKEN, container: viewerBox.current, imageId: startId });
        viewerRef.current = viewer;
        viewer.on("image", (e) => setCurrent({ ...e.image.lngLat, capturedAt: e.image.capturedAt }));
      })
      .catch(() => setFailed(true));
    return () => {
      cancelled = true;
      viewerRef.current = null;
      viewer?.remove();
    };
  }, [startId]);

  // Small map: all shots as dots, a click jumps the viewer there.
  useEffect(() => {
    if (!mapBox.current) return;
    let map: MlMap | undefined;
    let cancelled = false;
    loadMaplibre().then((maplibregl) => {
      if (cancelled || !mapBox.current) return;
      const start = points.find((p) => p.image_id === startId) ?? data.campus.center;
      map = new maplibregl.Map({
        container: mapBox.current, style: mapStyleUrl(), center: [start.lng, start.lat], zoom: 16,
        attributionControl: { compact: true }, cooperativeGestures: true,
      });
      map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
      markerRef.current = new maplibregl.Marker({ color: "#e0533d", scale: 0.8 }).setLngLat([start.lng, start.lat]).addTo(map);
      map.on("load", () => {
        if (!map) return;
        if (data.campus.polygon?.length) {
          map.addSource("campus", { type: "geojson", data: { type: "Feature", properties: {}, geometry: { type: "Polygon", coordinates: [data.campus.polygon] } } });
          map.addLayer({ id: "campus-line", type: "line", source: "campus", paint: { "line-color": POINT_COLOR, "line-width": 1.5, "line-dasharray": [3, 2] } });
        }
        map.addSource("shots", {
          type: "geojson",
          data: {
            type: "FeatureCollection",
            features: points.map((p) => ({
              type: "Feature" as const, properties: { id: p.image_id }, geometry: { type: "Point" as const, coordinates: [p.lng, p.lat] },
            })),
          },
        });
        map.addLayer({
          id: "shots", type: "circle", source: "shots",
          paint: { "circle-radius": 4, "circle-color": POINT_COLOR, "circle-opacity": 0.75, "circle-stroke-color": "#fff", "circle-stroke-width": 1 },
        });
        map.on("click", "shots", (e) => {
          const id = e.features?.[0]?.properties?.id;
          if (typeof id === "string") void viewerRef.current?.moveTo(id).catch(() => undefined);
        });
        map.on("mouseenter", "shots", () => map && (map.getCanvas().style.cursor = "pointer"));
        map.on("mouseleave", "shots", () => map && (map.getCanvas().style.cursor = ""));
      });
    });
    return () => {
      cancelled = true;
      markerRef.current = null;
      map?.remove();
    };
    // points/data come from one /campus response; theme rebuilds the basemap
  }, [data, startId, theme]); // eslint-disable-line react-hooks/exhaustive-deps

  // Keep the red marker on the image the viewer shows.
  useEffect(() => {
    if (current) markerRef.current?.setLngLat([current.lng, current.lat]);
  }, [current]);

  if (failed) {
    return <div className="rounded-[20px] bg-surface-2 p-[38px] text-[13px] text-ink-3">{t.liveMap.walkUnavailable}</div>;
  }

  const date = current?.capturedAt
    ? new Date(current.capturedAt).toLocaleDateString(lang === "ru" ? "ru-RU" : "en-GB", { year: "numeric", month: "long" })
    : null;

  return (
    <div className="flex flex-col gap-3">
      <div className="grid gap-3 md:grid-cols-[2fr_1fr]">
        <div ref={viewerBox} className="relative h-[560px] overflow-hidden rounded-[20px] bg-surface-2" />
        <div ref={mapBox} className="h-[560px] overflow-hidden rounded-[20px] bg-surface-2" />
      </div>
      <div className="flex flex-wrap gap-x-4 text-xs text-ink-3">
        <span>{t.liveMap.walkHint}</span>
        <span className="ml-auto font-mono">
          {points.length} {t.liveMap.walkShots}
          {date && ` · ${t.liveMap.walkTaken} ${date}`} · Mapillary, CC BY-SA 4.0
        </span>
      </div>
    </div>
  );
}
