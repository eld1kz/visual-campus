// DEMO DATA — ported from design/Visual Campus.dc.html (UNIS, summary, sources).
import type { Profile, ProfileUniversity } from "@/lib/types";
import { MAP } from "./map";
import { PHOTOS } from "./photos";

export type DemoUniversity = ProfileUniversity & { climate: string; climate_en: string };

export const DEMO_UNIVERSITIES: DemoUniversity[] = [
  {
    id: "ku", name: "Korea University", flag: "🇰🇷", city: "Seoul", country: "South Korea",
    city_ru: "Сеул", country_ru: "Республика Корея", aliases: ["고려대학교", "KU", "Korea Univ."],
    website: "https://www.korea.ac.kr", lat: 37.5895, lng: 127.0323, campus_polygon: MAP.campus.polygon,
    distance_to_center_km: 4.8, climate: "Dfa / влажный континентальный", climate_en: "Dfa / humid continental",
  },
  {
    id: "kaist", name: "KAIST", flag: "🇰🇷", city: "Daejeon", country: "South Korea",
    city_ru: "Тэджон", country_ru: "Республика Корея",
    aliases: ["한국과학기술원", "Korea Advanced Institute of Science and Technology"],
    website: "https://www.kaist.ac.kr", lat: 36.372, lng: 127.363, campus_polygon: null,
    distance_to_center_km: 6.2, climate: "Dwa / муссонный", climate_en: "Dwa / monsoon",
  },
];

export const PROFILE: Profile = {
  university: DEMO_UNIVERSITIES[0],
  generated_in_ms: 18400,
  sources_status: [
    { name: "Wikimedia Commons", status: "ok", count: 23 },
    { name: "OpenStreetMap", status: "ok", count: 4 },
    { name: "Flickr", status: "unavailable", count: 0 },
    { name: "Mapillary", status: "ok", count: 6 },
    { name: "Официальный сайт", status: "ok", count: 7 },
    { name: "Веб-поиск", status: "timeout", count: 2 },
  ],
  summary: {
    text: "Кампус Korea University расположен в районе Анам на севере Сеула и занимает около 0,6 км². Ядро кампуса — каменные корпуса начала XX века вокруг главной площади, вокруг них — библиотека, лаборатории и спортивный комплекс. Студенческая жизнь сосредоточена в кварталах Анам-донг сразу за воротами: кафе, книжные, недорогие столовые. Общежития стоят на склоне холма к западу от учебных корпусов.",
    text_en:
      "The Korea University campus sits in the Anam district of northern Seoul and covers roughly 0.6 km². Early-20th-century stone buildings frame the main square, with the library, laboratories and sports complex around them. Student life concentrates in Anam-dong right outside the gates: cafés, bookshops, cheap canteens. Dormitories stand on the hillside west of the teaching buildings.",
    citations: [
      { n: 1, title: "Wikimedia Commons — Korea University", url: "https://commons.wikimedia.org" },
      { n: 2, title: "OpenStreetMap — Korea University campus", url: "https://www.openstreetmap.org" },
    ],
  },
  photos: PHOTOS,
};

const SOURCE_NAMES_EN: Record<string, string> = { "Официальный сайт": "Official website", "Веб-поиск": "Web search" };

export const sourceLabel = (name: string, lang: "ru" | "en") => (lang === "en" ? (SOURCE_NAMES_EN[name] ?? name) : name);

/** Summary line in the profile header («42 фото · 27 проверено · 11 вероятно · 4 скрыто»). */
export const PROFILE_STATS = { photos: 42, verified: 27, likely: 11, hidden: 4 };

/** Loading screen: when each step and source settles, in ms. */
export const LOADING_STEP_TIMES = [4200, 7000, 11500, 13500, 16000, 18400];
export const LOADING_SOURCE_TIMES = [5200, 6100, 9800, 7400, 8200, 12000];

/** Compare screen: verified photos per category (campus, dorms, classrooms, libraries, city). */
export const COMPARE_STATS: Record<string, { verified: number; sources: string; byCategory: number[] }> = {
  ku: { verified: 27, sources: "4 / 6", byCategory: [9, 0, 6, 7, 5] },
  kaist: { verified: 19, sources: "5 / 6", byCategory: [7, 3, 4, 3, 2] },
};
