"use client";

import { usePreferences } from "@/components/layout/PreferencesProvider";
import { BUILDING_TYPE_COLOR, boxOf, layoutPins, panoSegments, polygonPoints, projectionFor } from "@/lib/map/geometry";
import { tierMeta } from "@/lib/tiers";
import { CampusPolygon, MapButton, MapFrame } from "./MapFrame";
import type { MapViewProps } from "./types";

type Props = MapViewProps & { flyover: boolean; onToggleFlyover: () => void };

/** CSS-perspective placeholder for the 3D view. MapLibre: fill-extrusion by height_m, pitch ≈ 58°. */
export function Map3DPlaceholder(props: Props) {
  const { t } = usePreferences();
  const { data, camera, layers, selectedBuildingId } = props;
  const P = projectionFor(data);
  const selected = data.buildings.find((b) => b.id === selectedBuildingId);
  const origin = selected ? boxOf(selected.polygon, P) : { cx: 50, cy: 50 };
  const faceCamera = `rotateZ(${-camera.bearing}deg) rotateX(${-camera.tilt}deg)`;
  const pins = layers.pins
    ? layoutPins(data.photo_pins.filter((p) => p.tier !== "unconfirmed" || layers.unconfirmedPins), P, camera.zoom)
    : [];

  return (
    <>
      <MapFrame style={{ perspective: 1100 }}>
        <div
          className="absolute inset-0 transition-transform duration-[250ms] ease-linear [transform-style:preserve-3d]"
          style={{
            transformOrigin: `${origin.cx}% ${origin.cy}%`,
            transform: `rotateX(${camera.tilt}deg) rotateZ(${camera.bearing}deg) scale(${camera.zoom * 0.78})`,
          }}
        >
          <div className="map-lines absolute inset-0" />
          {props.showPolygon && data.campus.polygon && (
            <CampusPolygon points={polygonPoints(data.campus.polygon, P)} fillOpacity={0.1} />
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
            const height = props.flatHeights ? 18 : (b.height_m ?? 12);
            const floors = Math.max(2, Math.min(12, Math.round(height / 4)));
            return Array.from({ length: floors }, (_, i) => (
              <div
                key={`${b.id}-${i}`}
                onClick={() => props.onSelectBuilding(b.id)}
                className="absolute cursor-pointer rounded-sm"
                style={{
                  left: `${box.l}%`, top: `${box.t}%`, width: `${box.w}%`, height: `${box.h}%`,
                  background: b.inside_campus ? BUILDING_TYPE_COLOR[b.type] : "var(--line-2)",
                  opacity: b.inside_campus ? 0.42 + 0.5 * (i / floors) : 0.5,
                  transform: `translateZ(${i * 3.4}px)`,
                }}
              />
            ));
          })}
          {pins.map((item) => {
            const color = tierMeta(item.pin.tier, t).color;
            const at = { left: `${item.x}%`, top: `${item.y}%` };
            return (
              <div key={item.key}>
                {item.pin.heading_deg !== null && (
                  <div
                    className="absolute size-[46px] origin-bottom opacity-[.16] [clip-path:polygon(50%_100%,0%_0%,100%_0%)]"
                    style={{ ...at, background: color, transform: `translate(-50%,-100%) rotate(${item.pin.heading_deg + 180}deg)` }}
                  />
                )}
                <div
                  className="absolute h-[26px] w-0.5 origin-bottom opacity-80"
                  style={{ ...at, background: color, transform: `translate(-50%,-100%) ${faceCamera}` }}
                />
                <div
                  onClick={() => props.onSelectPin(item.pin.photo_id)}
                  className="ph-stripes absolute size-5 cursor-pointer rounded-full border-2 [--s:5px]"
                  style={{ ...at, borderColor: color, transform: `translate(-50%,-50%) translateZ(34px) ${faceCamera}` }}
                />
              </div>
            );
          })}
        </div>

        <div className="absolute bottom-3 right-3 flex flex-col items-end gap-[5px]">
          <div className="flex gap-[5px]">
            <MapButton onClick={() => props.onCameraChange({ bearing: camera.bearing - 20 })}>↺</MapButton>
            <div className="flex size-8 items-center justify-center rounded-full bg-surface shadow-soft">
              <span className="font-mono text-[11px] text-ink-2" style={{ transform: `rotate(${-camera.bearing}deg)` }}>
                N
              </span>
            </div>
            <MapButton onClick={() => props.onCameraChange({ bearing: camera.bearing + 20 })}>↻</MapButton>
          </div>
          <div className="flex gap-[5px]">
            <MapButton onClick={() => props.onCameraChange({ tilt: Math.max(20, camera.tilt - 8) })}>▁</MapButton>
            <MapButton onClick={() => props.onCameraChange({ tilt: Math.min(72, camera.tilt + 8) })}>◢</MapButton>
            <MapButton onClick={() => props.onCameraChange({ zoom: Math.max(1, camera.zoom / 1.3) })}>−</MapButton>
            <MapButton onClick={() => props.onCameraChange({ zoom: Math.min(2.6, camera.zoom * 1.3) })}>+</MapButton>
          </div>
          <button
            onClick={props.onToggleFlyover}
            className="rounded-full border-none bg-surface px-3.5 py-2 text-xs text-ink-2 shadow-soft"
          >
            {props.flyover ? t.map.flyoverStop : t.map.flyover}
          </button>
        </div>
      </MapFrame>
      <div className="max-w-[60ch] pt-[9px] text-[11.5px] leading-normal text-ink-3">
        {props.flatHeights ? t.map.no3dHeights : t.map.note3d}
      </div>
    </>
  );
}
