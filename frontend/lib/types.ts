// Data contracts. /resolve mirrors backend/app/models.py; the rest follow
// design/README.md "Data contracts" and will be wired to the API later.

/* ---------- GET /resolve (live) ---------- */

export type SourceState = "ok" | "timeout" | "error";

export type SourceStatus = {
  name: string;
  status: SourceState;
};

export type UniversityCandidate = {
  id: string;
  name: string;
  aliases: string[];
  city: string | null;
  country: string | null;
  lat: number | null;
  lng: number | null;
  website: string | null;
  wikidata_id: string | null;
  ror_id: string | null;
  commons_category: string | null;
  match_score: number;
};

export type ResolveStatus = "resolved" | "ambiguous" | "not_found";

export type ResolveResponse = {
  query: string;
  corrected_query: string | null;
  status: ResolveStatus;
  university: UniversityCandidate | null;
  candidates: UniversityCandidate[];
  sources_status: SourceStatus[];
  took_ms: number;
};

/* ---------- Profile ---------- */

export type Tier = "verified" | "likely" | "unconfirmed";
export type PhotoCategory = "campus" | "dorms" | "classrooms" | "libraries" | "city";
export type PhotoTag = "dorm" | "sport" | "labs" | "student_life";

export type Evidence = {
  type: "geo" | "category" | "text" | "vision" | "missing" | "date" | "content";
  label: string;
  /** Demo only: English copy of `label` (the API will answer in the requested language). */
  label_en?: string;
  weight: number;
};

export type Duplicate = {
  id: string;
  thumb_url: string | null;
  source_url: string;
};

export type Photo = {
  id: string;
  thumb_url: string | null;
  full_url: string | null;
  category: PhotoCategory;
  tags: PhotoTag[];
  confidence: number;
  tier: Tier;
  source_url: string;
  source_domain: string;
  author: string;
  license: string;
  published_at: string | null;
  retrieved_at: string;
  lat?: number | null;
  lng?: number | null;
  evidence: Evidence[];
  duplicates: Duplicate[];
  /** Demo only: placeholder tile height and caption until real images exist. */
  placeholder_height?: number;
  placeholder_caption?: string;
};

export type ProfileSourceStatus = {
  name: string;
  status: "ok" | "unavailable" | "timeout" | "error";
  count: number;
};

export type Citation = { n: number; title: string; url: string };

export type ProfileUniversity = {
  id: string;
  name: string;
  aliases: string[];
  city: string | null;
  country: string | null;
  website: string | null;
  lat: number | null;
  lng: number | null;
  campus_polygon: [number, number][] | null;
  distance_to_center_km: number | null;
  /** Demo only: display helpers. */
  flag?: string;
  city_ru?: string;
  country_ru?: string;
};

export type ProfileStats = { photos: number; verified: number; likely: number; hidden: number; duplicates?: number };

export type Profile = {
  university: ProfileUniversity;
  generated_in_ms: number;
  sources_status: ProfileSourceStatus[];
  summary: { text: string; text_en?: string; citations: Citation[] };
  photos: Photo[];
};

/* ---------- Campus map ---------- */

export type BuildingType = "academic" | "dorm" | "library" | "sport" | "lab" | "food" | "other";
export type LngLat = [number, number];

export type Building = {
  id: string;
  name: string;
  type: BuildingType;
  polygon: LngLat[];
  height_m: number | null;
  levels: number | null;
  photo_ids: string[];
  source: string;
  /** Buildings around the campus are drawn muted. */
  inside_campus: boolean;
};

export type PhotoPin = {
  photo_id: string;
  lat: number;
  lng: number;
  heading_deg: number | null;
  tier: Tier;
  confidence: number;
  thumb_url: string | null;
  building_id: string | null;
};

export type TransitStop = {
  type: "metro" | "bus";
  name: string;
  lat: number;
  lng: number;
  walk_min: number;
};

export type PanoramaProvider = "mapillary" | "kakao" | "google";

export type CampusMap = {
  campus: {
    center: { lat: number; lng: number };
    polygon: LngLat[] | null;
    area_km2: number;
    city_center: { name: string; lat: number; lng: number };
    distance_to_center_km: number;
    transit: TransitStop[];
  };
  buildings: Building[];
  photo_pins: PhotoPin[];
  panoramas: {
    provider: PanoramaProvider | null;
    available: boolean;
    checked_providers: PanoramaProvider[];
    start: { lat: number; lng: number; captured_at: string };
  };
  /** Demo only: street segments with panorama coverage and the placeholder projection bbox. */
  pano_paths?: LngLat[][];
  bbox?: { w: number; e: number; s: number; n: number };
};

/* ---------- Mascot + chat ---------- */

export type MascotState = "idle" | "hello" | "thinking" | "talking" | "pointing" | "dont_know" | "changing";
export type OutfitTop = "hoodie" | "tshirt" | "varsity";
export type OutfitHead = "cap" | "none";
export type OutfitAccessory = "backpack" | "scarf" | "none";
export type Outfit = { top: OutfitTop; head: OutfitHead; accessory: OutfitAccessory };

export type MascotConfig = {
  outfit: Outfit;
  colors: {
    primary: string | null;
    secondary: string | null;
    source: "wikidata" | "website" | "none";
    source_url: string | null;
  };
  label_text: string;
};

export type ChatAction =
  | { type: "photos"; photo_ids: string[] }
  | { type: "map"; building_id?: string }
  | { type: "tab"; tab: PhotoCategory };

export type ChatMessage = {
  role: "user" | "assistant";
  text: string;
  mascot_state?: MascotState;
  citations?: Citation[];
  actions?: ChatAction[];
  /** Set when the answer is "not in the sources": lists what was checked. */
  checked?: string;
};
