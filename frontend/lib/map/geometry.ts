// GeoJSON and colours for the MapLibre campus map. MapLibre cannot parse oklch(), so colours are hex.
import type { Building, BuildingType, CampusMap, LngLat, PhotoPin, Tier } from "@/lib/types";

export const BUILDING_TYPE_COLOR: Record<BuildingType, string> = {
  academic: "#6c85bd",
  dorm: "#3396a0",
  library: "#4b916e",
  sport: "#a3924f",
  lab: "#8d72ac",
  food: "#c78669",
  other: "#a1a5ab",
};

export const BUILDING_TYPES = Object.keys(BUILDING_TYPE_COLOR) as BuildingType[];

export const ACCENT = "#496dc3";

export const TIER_COLOR: Record<Tier, string> = { verified: "#2d7b48", likely: "#a07020", unconfirmed: "#8b9098" };

/** Metres per floor when OSM has building:levels but no height. */
const FLOOR_M = 3.2;
const DEFAULT_HEIGHT_M = 10;

export type Bounds = [[number, number], [number, number]];

export function boundsOf(points: LngLat[]): Bounds | null {
  if (points.length === 0) return null;
  const lngs = points.map((p) => p[0]);
  const lats = points.map((p) => p[1]);
  return [[Math.min(...lngs), Math.min(...lats)], [Math.max(...lngs), Math.max(...lats)]];
}

/** What the map opens on: the campus outline and the buildings inside the campus; neither → null (centre + zoom). */
export function campusBounds(map: CampusMap): Bounds | null {
  const inside = map.buildings.filter((b) => b.inside_campus).flatMap((b) => b.polygon);
  return boundsOf([...(map.campus.polygon ?? []), ...inside]);
}

export function hasHeights(buildings: Building[]): boolean {
  return buildings.some((b) => b.height_m != null || b.levels != null);
}

export function buildingsGeoJson(buildings: Building[]): GeoJSON.FeatureCollection {
  return {
    type: "FeatureCollection",
    features: buildings.map((b) => ({
      type: "Feature",
      properties: {
        id: b.id,
        type: b.type,
        inside: b.inside_campus,
        height: b.height_m ?? (b.levels != null ? b.levels * FLOOR_M : DEFAULT_HEIGHT_M),
      },
      geometry: { type: "Polygon", coordinates: [b.polygon] },
    })),
  };
}

export function pinsGeoJson(pins: PhotoPin[]): GeoJSON.FeatureCollection {
  return {
    type: "FeatureCollection",
    features: pins.map((p) => ({
      type: "Feature",
      properties: { photo_id: p.photo_id, tier: p.tier },
      geometry: { type: "Point", coordinates: [p.lng, p.lat] },
    })),
  };
}

export function campusGeoJson(map: CampusMap): GeoJSON.FeatureCollection {
  const { center, polygon } = map.campus;
  const features: GeoJSON.Feature[] = [
    { type: "Feature", properties: { kind: "center" }, geometry: { type: "Point", coordinates: [center.lng, center.lat] } },
  ];
  if (polygon) {
    features.push({ type: "Feature", properties: { kind: "outline" }, geometry: { type: "Polygon", coordinates: [polygon] } });
  }
  return { type: "FeatureCollection", features };
}

/** Dashed line from the campus centre to the city centre, with a labelled end point. */
export function cityGeoJson(map: CampusMap, label: string): GeoJSON.FeatureCollection {
  const { center, city_center: city } = map.campus;
  if (!city) return { type: "FeatureCollection", features: [] };
  return {
    type: "FeatureCollection",
    features: [
      {
        type: "Feature",
        properties: { kind: "line" },
        geometry: { type: "LineString", coordinates: [[center.lng, center.lat], [city.lng, city.lat]] },
      },
      { type: "Feature", properties: { kind: "city", label }, geometry: { type: "Point", coordinates: [city.lng, city.lat] } },
    ],
  };
}
