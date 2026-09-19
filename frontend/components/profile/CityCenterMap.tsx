"use client";

import { useEffect, useRef } from "react";
import "maplibre-gl/dist/maplibre-gl.css";
import { usePreferences } from "@/components/layout/PreferencesProvider";
import { loadMaplibre, mapStyleUrl } from "@/lib/maplibre";
import type { ProfileUniversity } from "@/lib/types";

const CAMPUS_COLOR = "#4f5bd5";
const CENTER_COLOR = "#e0533d";

type Props = { university: ProfileUniversity };

/** Mini-map you can drag and zoom: campus point, city centre point and the road route (or a straight line). */
export function CityCenterMap({ university }: Props) {
  const container = useRef<HTMLDivElement>(null);
  const { theme } = usePreferences(); // the map style follows the site theme
  const { lat, lng, city_center: center, center_route: route } = university;

  useEffect(() => {
    if (!container.current || lat == null || lng == null || !center) return;
    let map: import("maplibre-gl").Map | undefined;
    let cancelled = false;
    loadMaplibre().then((maplibregl) => {
      if (cancelled || !container.current) return;
      const line: [number, number][] = route?.geometry.length
        ? (route.geometry as [number, number][])
        : [[lng, lat], [center.lng, center.lat]];
      const bounds = line.reduce(
        (b, point) => b.extend(point),
        new maplibregl.LngLatBounds([lng, lat], [lng, lat]),
      ).extend([center.lng, center.lat]);
      const instance = new maplibregl.Map({
        container: container.current,
        style: mapStyleUrl(),
        bounds,
        fitBoundsOptions: { padding: { top: 44, bottom: 24, left: 32, right: 32 } },  // pins point down: room on top
        // Drag and pinch work directly; the mouse wheel zooms only with Ctrl/⌘ so the page still scrolls.
        cooperativeGestures: true,
        dragRotate: false,
        attributionControl: { compact: true },
      });
      instance.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
      instance.touchZoomRotate.disableRotation();
      map = instance;
      instance.on("load", () => {
        instance.addSource("route", {
          type: "geojson",
          data: { type: "Feature", properties: {}, geometry: { type: "LineString", coordinates: line } },
        });
        instance.addLayer({
          id: "route",
          type: "line",
          source: "route",
          layout: { "line-cap": "round", "line-join": "round" },
          paint: { "line-color": CAMPUS_COLOR, "line-width": 3, ...(route ? {} : { "line-dasharray": [2, 2] }) },
        });
      });
      for (const [point, color] of [[[lng, lat], CAMPUS_COLOR], [[center.lng, center.lat], CENTER_COLOR]] as const) {
        new maplibregl.Marker({ color, scale: 0.7 }).setLngLat(point as [number, number]).addTo(instance);
      }
    });
    return () => {
      cancelled = true;
      map?.remove();
    };
  }, [lat, lng, center, route, theme]);

  return <div ref={container} className="h-[190px] overflow-hidden rounded-[18px] bg-surface-2" />;
}
