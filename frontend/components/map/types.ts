import type { BuildingType, CampusMap } from "@/lib/types";

export type MapMode = "2d" | "3d" | "walk";

export type MapLayers = {
  types: Record<BuildingType, boolean>;
  pins: boolean;
  unconfirmedPins: boolean;
};

/**
 * Props of the MapLibre campus map. One map instance serves both modes:
 * 2D — flat, north-up, typed building fills; 3D — pitched camera, fill-extrusion by height.
 */
export type MapViewProps = {
  data: CampusMap;
  mode: "2d" | "3d";
  layers: MapLayers;
  selectedBuildingId: string | null;
  /** Bumped by «Centre on campus»: fit the campus again. */
  recenterKey: number;
  flyover: boolean;
  onSelectBuilding: (id: string) => void;
  onSelectPin: (photoId: string) => void;
};
