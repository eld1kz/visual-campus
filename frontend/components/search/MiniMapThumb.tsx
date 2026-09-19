"use client";

import { useEffect, useRef } from "react";
import "maplibre-gl/dist/maplibre-gl.css";
import { usePreferences } from "@/components/layout/PreferencesProvider";
import { loadMaplibre, mapStyleUrl } from "@/lib/maplibre";

type Props = { lat: number | null; lng: number | null; width?: number; height?: number };

const ZOOM = 14; // a few blocks around the campus point

/** Static street map around the university point; a click opens it on OpenStreetMap. Grid placeholder without coordinates. */
export function MiniMapThumb({ lat, lng, width = 96, height = 96 }: Props) {
  const { theme } = usePreferences();
  const container = useRef<HTMLDivElement>(null);
  const hasPoint = lat !== null && lng !== null;

  useEffect(() => {
    if (!container.current || lat === null || lng === null) return;
    let map: import("maplibre-gl").Map | undefined;
    let cancelled = false;
    loadMaplibre().then((maplibregl) => {
      if (cancelled || !container.current) return;
      map = new maplibregl.Map({
        container: container.current,
        style: mapStyleUrl(),
        center: [lng, lat],
        zoom: ZOOM,
        interactive: false,
        attributionControl: false,
      });
      new maplibregl.Marker({ color: "#4f5bd5", scale: 0.6 }).setLngLat([lng, lat]).addTo(map);
    });
    return () => {
      cancelled = true;
      map?.remove();
    };
  }, [lat, lng, theme]);

  if (!hasPoint) {
    return (
      <div
        className="ph-grid flex shrink-0 items-center justify-center rounded-[14px] [--g:12px]"
        style={{ width, height }}
      >
        <div className="size-3 rounded-full bg-accent shadow-[0_0_0_5px_var(--accent-soft)]" />
      </div>
    );
  }
  return (
    <a
      href={`https://www.openstreetmap.org/?mlat=${lat}&mlon=${lng}#map=16/${lat}/${lng}`}
      target="_blank"
      rel="noreferrer"
      title="OpenStreetMap"
      className="relative block shrink-0 overflow-hidden rounded-[14px] bg-surface"
      style={{ width, height }}
    >
      <div ref={container} className="size-full" />
      <span className="absolute bottom-1 right-1.5 rounded bg-bg/80 px-1 text-[9px] text-ink-3">© OpenStreetMap</span>
    </a>
  );
}
