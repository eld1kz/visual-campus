/** Shared MapLibre setup: the worker path fix and a map style that follows the site theme. */

type MapLibre = typeof import("maplibre-gl");

let loading: Promise<MapLibre> | null = null;

/** Next bundles maplibre without an http import.meta.url, so its worker URL would resolve to the page itself
 *  and tiles would never load. The worker files are copied to public/maplibre by the postinstall script. */
export function loadMaplibre(): Promise<MapLibre> {
  loading ??= import("maplibre-gl").then((maplibregl) => {
    maplibregl.setWorkerUrl(`${window.location.origin}/maplibre/maplibre-gl-worker.mjs`);
    return maplibregl;
  });
  return loading;
}

export function mapStyleUrl(): string {
  const dark = document.documentElement.getAttribute("data-theme") === "dark";
  return `https://tiles.openfreemap.org/styles/${dark ? "dark" : "positron"}`;
}
