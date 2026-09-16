"use client";

import { usePreferences } from "@/components/layout/PreferencesProvider";
import { polygonPoints, projectionFor } from "@/lib/map/geometry";
import type { CampusMap } from "@/lib/types";
import { CampusPolygon, MapFrame } from "./MapFrame";

type Props = {
  data: CampusMap;
  yaw: number;
  pointIndex: number;
  pointCount: number;
  onYawChange: (yaw: number) => void;
  onStep: (delta: number) => void;
  onExit: () => void;
};

const PROVIDER_LABEL = { mapillary: "Mapillary", kakao: "Kakao Roadview", google: "Google Street View" };

/**
 * Street-level walk placeholder. Real viewer: MapillaryJS (`Viewer` + moveTo(imageId)) or
 * Kakao Roadview (`kakao.maps.Roadview`), driven by the same yaw / point props.
 */
export function PanoramaPlaceholder({ data, yaw, pointIndex, pointCount, onYawChange, onStep, onExit }: Props) {
  const { t } = usePreferences();
  const { provider, start } = data.panoramas;
  const shift = `${-yaw * 2}px 0`;
  const heading = (((Math.round(-yaw) % 360) + 360) % 360) + "°";

  return (
    <MapFrame tall>
      <div
        onMouseMove={(e) => e.buttons === 1 && onYawChange(yaw + e.movementX * 0.4)}
        className="absolute inset-0 cursor-grab bg-[linear-gradient(180deg,var(--ph2)_0%,var(--ph1)_48%,var(--ph2)_100%)]"
        style={{ backgroundPosition: shift }}
      >
        <div
          className="absolute inset-0 bg-[repeating-linear-gradient(90deg,transparent_0_78px,var(--line)_78px_79px)] opacity-50"
          style={{ backgroundPosition: shift }}
        />
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center pr-[clamp(150px,28%,220px)]">
          <span className="px-6 text-center font-mono text-[13px] text-ink-3">
            {t.map.panorama} 360° · {t.map.walkHint}
          </span>
        </div>
      </div>

      <div className="absolute left-3 top-3 flex items-center gap-2 rounded-full bg-surface px-[13px] py-[7px] text-xs text-ink-2 shadow-soft">
        {t.map.panorama}: {provider ? PROVIDER_LABEL[provider] : "—"} · {t.map.captured} {start?.captured_at ?? "—"}
      </div>
      <button
        onClick={onExit}
        className="absolute right-3 top-3 rounded-full border-none bg-surface px-3.5 py-2 text-[12.5px] text-ink-2 shadow-soft"
      >
        {t.map.exitWalk}
      </button>

      <div className="absolute bottom-[18px] left-[18px] flex items-center gap-2.5">
        <button onClick={() => onStep(-1)} className="size-10 rounded-full border-none bg-surface text-[15px] text-ink-2 shadow-soft">
          ←
        </button>
        <span className="font-mono text-[11px] text-ink-3">
          {t.map.point} {pointIndex + 1} / {pointCount} · {heading}
        </span>
        <button onClick={() => onStep(1)} className="size-10 rounded-full border-none bg-surface text-[15px] text-ink-2 shadow-soft">
          →
        </button>
      </div>

      <div className="absolute bottom-3 right-3 aspect-square w-[clamp(132px,26%,200px)] overflow-hidden rounded-[10px] border border-line bg-surface-2">
        <div className="map-lines absolute inset-0 [--g:27px]" />
        {data.campus.polygon && (
          <CampusPolygon points={polygonPoints(data.campus.polygon, projectionFor(data))} fillOpacity={0.1} strokeWidth={1} />
        )}
        <div
          className="absolute left-1/2 top-1/2 size-[58px] origin-bottom bg-accent opacity-20 [clip-path:polygon(50%_100%,6%_0%,94%_0%)]"
          style={{ transform: `translate(-50%,-100%) rotate(${180 - yaw * 0.6}deg)` }}
        />
        <div className="absolute left-1/2 top-1/2 size-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-surface bg-accent" />
      </div>
    </MapFrame>
  );
}

export function PanoramaEmpty({ checked, onBack }: { checked: string[]; onBack: () => void }) {
  const { t } = usePreferences();
  return (
    <div className="flex h-[clamp(300px,46vh,460px)] flex-col items-center justify-center gap-2.5 rounded-[20px] bg-surface-2 p-6 text-center">
      <div className="text-base font-medium">{t.map.panoEmpty}</div>
      <div className="font-mono text-xs text-ink-3">
        {t.map.panoChecked}: {checked.map((p) => PROVIDER_LABEL[p as keyof typeof PROVIDER_LABEL] ?? p).join(", ")}
      </div>
      <button onClick={onBack} className="mt-1.5 rounded-full border-none bg-ink px-[18px] py-2.5 text-[13px] text-bg">
        {t.map.backTo3d}
      </button>
    </div>
  );
}
