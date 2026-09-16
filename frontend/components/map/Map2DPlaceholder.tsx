"use client";

import { usePreferences } from "@/components/layout/PreferencesProvider";
import {
  BUILDING_TYPE_COLOR, LABEL_ZOOM, boxOf, cityCentreMarker, layoutPins, panoSegments, polygonPoints, projectionFor,
} from "@/lib/map/geometry";
import { tierMeta } from "@/lib/tiers";
import { CampusPolygon, MapButton, MapFrame } from "./MapFrame";
import type { MapViewProps } from "./types";

/** CSS placeholder for the 2D campus map. Replace with MapLibre GL JS keeping MapViewProps. */
export function Map2DPlaceholder(props: MapViewProps) {
  const { t, lang } = usePreferences();
  const { data, camera, layers, selectedBuildingId } = props;
  const P = projectionFor(data);
  const zoom = camera.zoom;
  const counter = `scale(${(1 / zoom).toFixed(2)})`;
  const selected = data.buildings.find((b) => b.id === selectedBuildingId);
  const origin = selected ? boxOf(selected.polygon, P) : { cx: 50, cy: 50 };
  const pins = layers.pins
    ? layoutPins(data.photo_pins.filter((p) => p.tier !== "unconfirmed" || layers.unconfirmedPins), P, zoom)
    : [];
  const city = cityCentreMarker(data);

  return (
    <MapFrame>
      <div
        className="absolute inset-0 transition-transform duration-500 ease-[cubic-bezier(.2,.7,.2,1)]"
        style={{ transformOrigin: `${origin.cx}% ${origin.cy}%`, transform: `scale(${zoom})` }}
      >
        <div className="map-lines absolute inset-0" />
        {props.showPolygon && data.campus.polygon && (
          <CampusPolygon points={polygonPoints(data.campus.polygon, P)} fillOpacity={0.09} />
        )}
        {layers.panoramas &&
          panoSegments(data.pano_paths ?? [], P).map((s) => (
            <div
              key={s.key}
              className="absolute h-[3px] origin-[0_50%] rounded-sm opacity-50"
              style={{ left: `${s.x}%`, top: `${s.y}%`, width: `${s.length}%`, background: "oklch(0.6 0.13 250)", transform: `rotate(${s.angle}deg)` }}
            />
          ))}
        {data.buildings.filter((b) => layers.types[b.type]).map((b) => {
          const box = boxOf(b.polygon, P);
          const on = b.id === selectedBuildingId;
          return (
            <div key={b.id}>
              <div
                onClick={() => props.onSelectBuilding(b.id)}
                title={b.name}
                className="absolute cursor-pointer rounded-[3px]"
                style={{
                  left: `${box.l}%`, top: `${box.t}%`, width: `${box.w}%`, height: `${box.h}%`,
                  background: BUILDING_TYPE_COLOR[b.type],
                  opacity: !b.inside_campus ? 0.28 : on ? 0.95 : 0.6,
                  boxShadow: on ? "0 0 0 2px var(--ink)" : "none",
                }}
              />
              <div
                className="pointer-events-none absolute whitespace-nowrap text-[9.5px] tracking-[.01em] text-ink-2 transition-opacity duration-200"
                style={{
                  left: `${box.cx}%`, top: `${box.t + box.h}%`,
                  transform: `translate(-50%,3px) ${counter}`,
                  opacity: zoom >= LABEL_ZOOM && b.inside_campus ? 1 : 0,
                }}
              >
                {b.name}
              </div>
            </div>
          );
        })}
        {layers.transit &&
          data.campus.transit.map((stop) => {
            const pt = P(stop.lng, stop.lat);
            return (
              <div
                key={stop.name}
                title={stop.name}
                className="absolute flex size-[18px] items-center justify-center rounded-[5px] border border-line-2 bg-surface font-mono text-[9.5px] text-ink-2"
                style={{ left: `${pt.x}%`, top: `${pt.y}%`, transform: `translate(-50%,-50%) ${counter}` }}
              >
                {stop.type === "metro" ? "M" : "B"}
              </div>
            );
          })}
        {city && (
          <>
            <div
              className="absolute left-1/2 top-1/2 h-0 origin-[0_50%] border-t border-dashed border-ink-3 opacity-60"
              style={{ width: `${city.length}%`, transform: `rotate(${city.angle}deg)` }}
            />
            <div
              className="absolute flex items-center gap-1.5 whitespace-nowrap"
              style={{ left: `${city.x}%`, top: `${city.y}%`, transform: "translate(-5px,-50%)" }}
            >
              <div className="size-[9px] rounded-full bg-ink-2" />
              <div className="flex flex-col gap-px">
                <span className="text-[11px] text-ink-2">{city.name}</span>
                <span className="font-mono text-[10px] text-ink-3">
                  {data.campus.distance_to_center_km?.toFixed(1) ?? "—"} {lang === "en" ? "km" : "км"} {t.map.toCenterLong}
                </span>
              </div>
            </div>
          </>
        )}
        <div
          className="absolute left-1/2 top-1/2 size-3 rounded-full bg-accent shadow-[0_0_0_5px_var(--accent-soft)]"
          style={{ transform: `translate(-50%,-50%) ${counter}` }}
        />
        {pins.map((item) => {
          const cluster = item.count > 1;
          return (
            <div
              key={item.key}
              onClick={() => (cluster ? props.onZoomToCluster() : props.onSelectPin(item.pin.photo_id))}
              className={`absolute flex cursor-pointer items-center justify-center rounded-full border-2 font-mono text-[11px] text-ink shadow-[0_1px_4px_rgba(0,0,0,.18)] ${
                cluster ? "size-[30px] bg-surface" : "ph-stripes size-[26px] [--s:5px]"
              }`}
              style={{
                left: `${item.x}%`, top: `${item.y}%`,
                transform: `translate(-50%,-50%) ${counter}`,
                borderColor: cluster ? "var(--ink-2)" : tierMeta(item.pin.tier, t).color,
              }}
            >
              {cluster ? item.count : ""}
            </div>
          );
        })}
      </div>

      <div className="absolute bottom-3 right-3 flex flex-col gap-[5px]">
        <MapButton onClick={() => props.onCameraChange({ zoom: Math.min(2.6, zoom * 1.3) })}>+</MapButton>
        <MapButton onClick={() => props.onCameraChange({ zoom: Math.max(1, zoom / 1.3) })}>−</MapButton>
      </div>
      <div className="absolute bottom-2.5 left-3 font-mono text-[10px] text-ink-3">© OpenStreetMap contributors · DEMO DATA</div>
    </MapFrame>
  );
}
