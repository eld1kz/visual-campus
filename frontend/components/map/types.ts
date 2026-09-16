import type { BuildingType, CampusMap } from "@/lib/types";

export type MapMode = "2d" | "3d" | "walk";

export type MapCamera = { zoom: number; bearing: number; tilt: number };

export type MapLayers = {
  types: Record<BuildingType, boolean>;
  pins: boolean;
  unconfirmedPins: boolean;
  panoramas: boolean;
  transit: boolean;
};

/** Demo toggles from the design's «ТЕСТОВЫЕ СОСТОЯНИЯ» (prototype-only). */
export type MapDemoFlags = { noPolygon: boolean; noHeights: boolean; noPano: boolean; no3d: boolean };

/**
 * Contract shared by the 2D and 3D renderers. The placeholders implement it with CSS;
 * the MapLibre GL JS version maps it onto sources/layers:
 *  - buildings → fill (2D) / fill-extrusion by height_m (3D), filtered by layers.types
 *  - campus polygon → fill + line; photo pins → clustered symbol layer
 *  - camera → map.easeTo({ zoom, bearing, pitch: tilt })
 */
export type MapViewProps = {
  data: CampusMap;
  camera: MapCamera;
  layers: MapLayers;
  showPolygon: boolean;
  flatHeights: boolean;
  selectedBuildingId: string | null;
  onSelectBuilding: (id: string) => void;
  onSelectPin: (photoId: string) => void;
  onZoomToCluster: () => void;
  onCameraChange: (camera: Partial<MapCamera>) => void;
};
