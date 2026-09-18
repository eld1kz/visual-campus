"use client";

import { useEffect, useRef } from "react";
import "maplibre-gl/dist/maplibre-gl.css";
import type { ProfileUniversity } from "@/lib/types";

const STYLE_URL = "https://tiles.openfreemap.org/styles/positron";
const CAMPUS_COLOR = "#4f5bd5";
const CENTER_COLOR = "#e0533d";

type Props = { university: ProfileUniversity };

/** Static mini-map: campus point, city centre point and the road route (or a straight line) between them. */
export function CityCenterMap({ university }: Props) {
  const container = useRef<HTMLDivElement>(null);
  const { lat, lng, city_center: center, center_route: route } = university;

  useEffect(() => {
    if (!container.current || lat == null || lng == null || !center) return;
    let map: import("maplibre-gl").Map | undefined;
    let cancelled = false;
    import("maplibre-gl").then((maplibregl) => {
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
        style: STYLE_URL,
        bounds,
        fitBoundsOptions: { padding: 28 },
        interactive: false,
        attributionControl: { compact: true },
      });
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
  }, [lat, lng, center, route]);

  return <div ref={container} className="h-[150px] overflow-hidden rounded-[18px] bg-surface-2" />;
}
