"use client";

import { usePreferences } from "@/components/layout/PreferencesProvider";
import type { Profile } from "@/lib/types";

/** The real campus outline as SVG points: lng scaled by cos(lat) so the shape is not stretched, y flipped. */
function outlineSvg(polygon: [number, number][]) {
  const k = Math.cos((polygon[0][1] * Math.PI) / 180);
  const pts = polygon.map(([lng, lat]) => [lng * k, -lat]);
  const xs = pts.map((p) => p[0]);
  const ys = pts.map((p) => p[1]);
  const x0 = Math.min(...xs), y0 = Math.min(...ys);
  const w = Math.max(...xs) - x0 || 1e-6, h = Math.max(...ys) - y0 || 1e-6;
  const scale = 100 / Math.max(w, h);
  return {
    viewBox: `0 0 ${(w * scale).toFixed(2)} ${(h * scale).toFixed(2)}`,
    points: pts.map(([x, y]) => `${((x - x0) * scale).toFixed(2)},${((y - y0) * scale).toFixed(2)}`).join(" "),
  };
}

type Props = {
  profile: Profile;
  onOpenMap: () => void;
};

export function AboutSection({ profile, onOpenMap }: Props) {
  const { t, lang } = usePreferences();
  const { summary, university } = profile;
  const outline = university.campus_polygon ? outlineSvg(university.campus_polygon) : null;

  return (
    <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,320px),1fr))] gap-7 pb-[34px] pt-[30px]">
      <div>
        <p className="mb-3 max-w-[64ch] text-[15px] leading-[1.7] text-pretty text-ink">
          {lang === "en" && summary.text_en ? summary.text_en : summary.text}
          {summary.citations.map((c) => (
            <a key={c.n} href={c.url} target="_blank" rel="noreferrer" className="ml-px align-super text-xs">
              [{c.n}]
            </a>
          ))}
        </p>
        <div className="flex flex-col gap-1">
          {summary.citations.map((c) => (
            <div key={c.n} className="text-xs text-ink-3">
              [{c.n}]{" "}
              <a href={c.url} target="_blank" rel="noreferrer">
                {c.title}
              </a>
            </div>
          ))}
        </div>
      </div>

      <div onClick={onOpenMap} className="cursor-pointer">
        <div className="ph-grid relative flex h-[150px] items-center justify-center overflow-hidden rounded-[18px] [--g:20px]">
          {outline ? (
            <svg viewBox={outline.viewBox} className="h-[118px] w-[70%]" preserveAspectRatio="xMidYMid meet">
              <polygon
                points={outline.points}
                fill="var(--accent-soft)"
                stroke="var(--accent)"
                strokeWidth={1.5}
                vectorEffect="non-scaling-stroke"
              />
            </svg>
          ) : (
            <span className="text-[13px] text-ink-2">{t.map.secMap} →</span>
          )}
        </div>
        <div className="flex justify-between gap-3 pt-[9px] text-[12.5px] text-ink-3">
          <span>{t.distance}</span>
          <span className="font-mono text-ink-2">
            {university.distance_to_center_km === null ? "—" : `${university.distance_to_center_km.toFixed(1)} ${t.km}`}
          </span>
        </div>
      </div>
    </div>
  );
}
