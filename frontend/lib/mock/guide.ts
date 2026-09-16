// DEMO DATA — ported from design/Visual Campus.dc.html (BRAND, QA, MASCOT_STATES).
import type { ChatAction, Citation, MascotConfig, MascotState } from "@/lib/types";

export const BRAND: Record<string, MascotConfig> = {
  ku: {
    outfit: { top: "hoodie", head: "cap", accessory: "backpack" },
    colors: { primary: "#8B0029", secondary: "#F7F5F2", source: "wikidata", source_url: "https://www.wikidata.org" },
    label_text: "KU",
  },
  kaist: {
    outfit: { top: "hoodie", head: "cap", accessory: "backpack" },
    colors: { primary: "#1F3C6E", secondary: "#EDEFF2", source: "website", source_url: "https://www.kaist.ac.kr" },
    label_text: "KAIST",
  },
};

/** Service palette when a university has no brand colors. */
export const NEUTRAL_BRAND = { primary: "#5f66c7", secondary: "#f4f4f2" };

export type QaKey = "dorms" | "center" | "gym" | "library" | "climate" | "unknown";

export const QA_CHIPS: Record<"ru" | "en", { key: QaKey; label: string }[]> = {
  ru: [
    { key: "dorms", label: "Какие общежития?" },
    { key: "center", label: "Далеко ли до центра?" },
    { key: "gym", label: "Есть ли спортзал?" },
    { key: "library", label: "Покажи библиотеку" },
    { key: "climate", label: "Какой климат?" },
    { key: "unknown", label: "Сколько стоит обучение?" },
  ],
  en: [
    { key: "dorms", label: "Which dormitories?" },
    { key: "center", label: "How far is the centre?" },
    { key: "gym", label: "Is there a gym?" },
    { key: "library", label: "Show me the library" },
    { key: "climate", label: "What is the climate?" },
    { key: "unknown", label: "How much is tuition?" },
  ],
};

export const QA_CHECKED = {
  ru: "Проверено: Wikimedia Commons, OpenStreetMap, Mapillary, официальный сайт.",
  en: "Checked: Wikimedia Commons, OpenStreetMap, Mapillary, official website.",
};

const CIT_OSM: Citation = { n: 1, title: "OpenStreetMap — Korea University campus", url: "https://www.openstreetmap.org" };
const CIT_WC: Citation = { n: 2, title: "Wikimedia Commons — Korea University", url: "https://commons.wikimedia.org" };

export type QaEntry = {
  match?: string[];
  ru: string;
  en: string;
  state: MascotState;
  citations?: Citation[];
  actions?: ChatAction[];
  checked?: boolean;
};

export const QA: Record<QaKey, QaEntry> = {
  dorms: {
    match: ["общежит", "dorm"],
    ru: "В границах кампуса найдены два общежития: Anam Hall и Frontier Hall [1]. Проверенных фотографий общежитий пока нет — источники дали только контуры зданий [2].",
    en: "Two dormitories were found inside the campus boundary: Anam Hall and Frontier Hall [1]. There are no verified dormitory photos yet — the sources only provided building outlines [2].",
    state: "pointing",
    citations: [CIT_OSM, CIT_WC],
    actions: [{ type: "map", building_id: "b4" }, { type: "tab", tab: "dorms" }],
  },
  center: {
    match: ["центр", "centre", "center"],
    ru: "До центра Сеула 4.2 км — около 15 минут на метро от станции Anam, 4 минуты пешком до входа в кампус [1].",
    en: "The city centre is 4.2 km away — about 15 minutes by metro from Anam station, a 4-minute walk from the campus gate [1].",
    state: "talking",
    citations: [CIT_OSM],
    actions: [{ type: "map" }],
  },
  gym: {
    match: ["спорт", "gym", "sport"],
    ru: "Да: внутри кампуса есть Hwajeong Gymnasium и спортивное поле [1]. Нашлось 2 фотографии спортивных объектов — одна проверенная, одна вероятная [2].",
    en: "Yes: the campus has Hwajeong Gymnasium and a sports field [1]. Two photos of sports facilities were found — one verified, one likely [2].",
    state: "pointing",
    citations: [CIT_OSM, CIT_WC],
    actions: [{ type: "photos", photo_ids: ["ph_1003", "ph_1010"] }, { type: "map", building_id: "b6" }],
  },
  library: {
    match: ["библиотек", "librar"],
    ru: "Central Library — крупнейшая библиотека кампуса, 9 этажей [1]. Нашлось 3 проверенных фотографии интерьера [2].",
    en: "Central Library is the largest library on campus, 9 floors [1]. Three verified interior photos were found [2].",
    state: "pointing",
    citations: [CIT_OSM, CIT_WC],
    actions: [{ type: "photos", photo_ids: ["ph_1001", "ph_1005", "ph_1013"] }, { type: "map", building_id: "b2" }],
  },
  climate: {
    match: ["климат", "climate", "погод", "weather"],
    ru: "Климат Dfa — влажный континентальный: тёплое влажное лето и холодная сухая зима [1].",
    en: "The climate is Dfa — humid continental: warm humid summers and cold dry winters [1].",
    state: "talking",
    citations: [CIT_OSM],
  },
  unknown: {
    ru: "В найденных источниках нет информации об этом.",
    en: "The sources we found contain no information about this.",
    state: "dont_know",
    checked: true,
  },
};

export const MASCOT_STATES: { key: MascotState; ru: string; en: string; note: string; noteEn: string }[] = [
  { key: "hello", ru: "Привет", en: "Hello", note: "Машет рукой при открытии профиля и чата.", noteEn: "Waves when the profile or chat opens." },
  { key: "idle", ru: "Ожидание", en: "Idle", note: "Лёгкое покачивание и моргание.", noteEn: "Gentle sway and blinking." },
  { key: "thinking", ru: "Думает", en: "Thinking", note: "Рука у подбородка, три точки над головой.", noteEn: "Hand to chin, three dots overhead." },
  { key: "talking", ru: "Говорит", en: "Talking", note: "Движение рта и жест во время стриминга ответа.", noteEn: "Mouth movement and gesture while the answer streams." },
  { key: "pointing", ru: "Показывает", en: "Pointing", note: "Указывает в сторону фото или карты.", noteEn: "Points towards photos or the map." },
  { key: "dont_know", ru: "Не знаю", en: "Don't know", note: "Разводит руками, когда данных нет.", noteEn: "Shrugs when the data is missing." },
  { key: "changing", ru: "Переодевается", en: "Changing", note: "Короткий эффект смены одежды.", noteEn: "A short outfit-change effect." },
];
