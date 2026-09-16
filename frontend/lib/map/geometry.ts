// Placeholder projection used until MapLibre GL JS renders real tiles:
// a linear lng/lat → percentage mapping inside a fixed bbox (as in the design prototype).
import type { BuildingType, CampusMap, LngLat, PhotoPin } from "@/lib/types";

export type Point = { x: number; y: number };
export type Box = { l: number; t: number; w: number; h: number; cx: number; cy: number };
export type Projection = (lng: number, lat: number) => Point;

export const BUILDING_TYPE_COLOR: Record<BuildingType, string> = {
  academic: "oklch(0.62 0.09 265)",
  dorm: "oklch(0.62 0.09 205)",
  library: "oklch(0.6 0.09 160)",
  sport: "oklch(0.66 0.09 95)",
  lab: "oklch(0.6 0.09 305)",
  food: "oklch(0.68 0.09 45)",
  other: "oklch(0.72 0.01 265)",
};

export const BUILDING_TYPES = Object.keys(BUILDING_TYPE_COLOR) as BuildingType[];

/** Zoom level at which building labels appear and pin clusters split. */
export const LABEL_ZOOM = 1.35;

export function projectionFor(map: CampusMap): Projection {
  const b = map.bbox ?? { w: map.campus.center.lng - 0.01, e: map.campus.center.lng + 0.01, s: map.campus.center.lat - 0.006, n: map.campus.center.lat + 0.006 };
  return (lng, lat) => ({ x: ((lng - b.w) / (b.e - b.w)) * 100, y: ((b.n - lat) / (b.n - b.s)) * 100 });
}

export function boxOf(polygon: LngLat[], P: Projection): Box {
  const pts = polygon.map(([lng, lat]) => P(lng, lat));
  const xs = pts.map((p) => p.x);
  const ys = pts.map((p) => p.y);
  const l = Math.min(...xs), r = Math.max(...xs), t = Math.min(...ys), b = Math.max(...ys);
  return { l, t, w: r - l, h: b - t, cx: (l + r) / 2, cy: (t + b) / 2 };
}

export function polygonPoints(polygon: LngLat[], P: Projection): string {
  return polygon.map(([lng, lat]) => {
    const p = P(lng, lat);
    return `${p.x.toFixed(2)},${p.y.toFixed(2)}`;
  }).join(" ");
}

export type PinItem = { key: string; x: number; y: number; pin: PhotoPin; count: number };

/** Below LABEL_ZOOM nearby pins collapse into clusters (MapLibre: clustered symbol layer). */
export function layoutPins(pins: PhotoPin[], P: Projection, zoom: number): PinItem[] {
  if (zoom >= LABEL_ZOOM) {
    return pins.map((pin) => ({ key: pin.photo_id, ...P(pin.lng, pin.lat), pin, count: 1 }));
  }
  const cells = new Map<string, { pin: PhotoPin; pt: Point }[]>();
  for (const pin of pins) {
    const pt = P(pin.lng, pin.lat);
    const key = `${Math.round(pt.x / 13)}_${Math.round(pt.y / 13)}`;
    cells.set(key, [...(cells.get(key) ?? []), { pin, pt }]);
  }
  return [...cells.entries()].map(([key, group]) => ({
    key,
    x: group.reduce((a, g) => a + g.pt.x, 0) / group.length,
    y: group.reduce((a, g) => a + g.pt.y, 0) / group.length,
    pin: group[0].pin,
    count: group.length,
  }));
}

/** Street segments with panorama coverage, as absolutely positioned bars. */
export function panoSegments(paths: LngLat[][], P: Projection) {
  return paths.flatMap((path, pi) =>
    path.slice(0, -1).map((start, i) => {
      const a = P(start[0], start[1]);
      const b = P(path[i + 1][0], path[i + 1][1]);
      const dx = b.x - a.x, dy = b.y - a.y;
      return { key: `${pi}-${i}`, x: a.x, y: a.y, length: Math.hypot(dx, dy), angle: (Math.atan2(dy, dx) * 180) / Math.PI };
    }),
  );
}

/** Direction marker towards the city centre, drawn from the campus centre (50%, 50%). */
export function cityCentreMarker(map: CampusMap) {
  const { center, city_center } = map.campus;
  if (!city_center) return null;
  const ang = Math.atan2(city_center.lat - center.lat, city_center.lng - center.lng);
  const x = 50 + Math.cos(ang) * 44, y = 50 - Math.sin(ang) * 44;
  return { name: city_center.name, x, y, length: Math.hypot(x - 50, y - 50), angle: (Math.atan2(y - 50, x - 50) * 180) / Math.PI };
}
