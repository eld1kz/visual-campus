import type { Lang } from "@/lib/i18n";

// Display names for source ids returned by the API (and the demo data's plain names).
const NAMES: Record<string, Partial<Record<Lang, string>>> = {
  ror: { ru: "ROR", en: "ROR" },
  wikidata: { ru: "Wikidata", en: "Wikidata" },
  openstreetmap: { ru: "OpenStreetMap", en: "OpenStreetMap" },
  wikimedia_commons: { ru: "Wikimedia Commons", en: "Wikimedia Commons" },
  wikipedia: { ru: "Wikipedia", en: "Wikipedia" },
  flickr: { ru: "Flickr", en: "Flickr" },
  mapillary: { ru: "Mapillary", en: "Mapillary" },
  official_site: { ru: "Официальный сайт", en: "Official website" },
  web_search: { ru: "Веб-поиск", en: "Web search" },
  "Официальный сайт": { en: "Official website" },
  "Веб-поиск": { en: "Web search" },
};

export const sourceLabel = (name: string, lang: Lang) => NAMES[name]?.[lang] ?? name;
