import type { Lang } from "@/lib/i18n";

// Display names for source ids returned by the API (and the demo data's plain names).
const NAMES: Record<string, Partial<Record<Lang, string>>> = {
  ror: { ru: "ROR", en: "ROR" },
  wikidata: { ru: "Wikidata", en: "Wikidata" },
  openstreetmap: { ru: "OpenStreetMap", en: "OpenStreetMap" },
  wikimedia_commons: { ru: "Wikimedia Commons", en: "Wikimedia Commons" },
  wikipedia: { ru: "Wikipedia", en: "Wikipedia" },
  "Официальный сайт": { en: "Official website" },
  "Веб-поиск": { en: "Web search" },
};

export const sourceLabel = (name: string, lang: Lang) => NAMES[name]?.[lang] ?? name;
