// DEMO DATA — ported from design/Visual Campus.dc.html (PHOTOS).
import type { Evidence, Photo } from "@/lib/types";

const EV = {
  geo: (m: number): Evidence => ({
    type: "geo",
    label: `Геотег в ${m} м внутри границ кампуса`,
    label_en: `Geotag ${m} m inside campus boundary`,
    weight: 28,
  }),
  cat: (c: string): Evidence => ({
    type: "category",
    label: `Находится в категории Commons «${c}»`,
    label_en: `In Commons category “${c}”`,
    weight: 22,
  }),
  txt: (s: string): Evidence => ({
    type: "text",
    label: `Описание упоминает «${s}»`,
    label_en: `Description mentions “${s}”`,
    weight: 14,
  }),
  vis: (s: string, sEn: string, c: string): Evidence => ({
    type: "vision",
    label: `AI: ${s} (уверенность ${c})`,
    label_en: `AI: ${sEn} (confidence ${c})`,
    weight: 11,
  }),
  noGeo: { type: "missing", label: "Нет геотега", label_en: "No geotag", weight: -18 } as Evidence,
  noLic: {
    type: "missing",
    label: "Лицензия не указана на странице источника",
    label_en: "No license stated on source page",
    weight: -12,
  } as Evidence,
};

const dup = (id: string, domain: string) => ({ id, thumb_url: null, source_url: `https://${domain}` });

function photo(n: number, o: Partial<Photo>): Photo {
  return {
    id: `ph_${1000 + n}`,
    thumb_url: null,
    full_url: null,
    category: "campus",
    tags: [],
    confidence: 70,
    tier: "likely",
    source_url: "https://commons.wikimedia.org",
    source_domain: "commons.wikimedia.org",
    author: "Demo Contributor",
    license: "CC BY-SA 4.0",
    published_at: "2024-05-12",
    retrieved_at: "2026-09-16",
    evidence: [],
    duplicates: [],
    placeholder_height: 190,
    placeholder_caption: "campus photo · placeholder",
    ...o,
  };
}

export const PHOTOS: Photo[] = [
  photo(1, {
    category: "libraries", tags: ["student_life"], confidence: 94, tier: "verified", placeholder_height: 240,
    placeholder_caption: "library interior · placeholder",
    source_url: "https://commons.wikimedia.org/wiki/Category:Korea_University_Library", author: "J. Park",
    evidence: [EV.geo(120), EV.cat("Korea University Library"), EV.txt("Central Library"), EV.vis("интерьер библиотеки", "library interior", "0.91")],
    duplicates: [dup("ph_2210", "flickr.com"), dup("ph_2211", "commons.wikimedia.org"), dup("ph_2212", "mapillary.com")],
  }),
  photo(2, {
    category: "campus", tags: ["student_life"], confidence: 91, tier: "verified", placeholder_height: 170,
    placeholder_caption: "main quad · placeholder", source_url: "https://www.openstreetmap.org",
    source_domain: "openstreetmap.org", license: "ODbL", author: "OSM contributor", published_at: "2025-03-02",
    evidence: [EV.geo(40), EV.cat("Korea University Campus"), EV.vis("историческое здание", "historic building", "0.88")],
    duplicates: [dup("ph_2301", "flickr.com")],
  }),
  photo(3, {
    category: "campus", tags: ["sport"], confidence: 88, tier: "verified", placeholder_height: 210,
    placeholder_caption: "sports field · placeholder", author: "S. Lim", published_at: "2023-10-18",
    evidence: [EV.geo(260), EV.cat("Sports facilities in Seoul"), EV.txt("Hwajeong Gymnasium")],
  }),
  photo(4, {
    category: "classrooms", tags: ["labs"], confidence: 85, tier: "verified", placeholder_height: 185,
    placeholder_caption: "lecture hall · placeholder", source_url: "https://www.korea.ac.kr", source_domain: "korea.ac.kr",
    license: "© Официальный сайт, разрешено к показу", author: "Korea University", published_at: "2025-01-24",
    evidence: [EV.cat("Официальный сайт: /campus/facilities"), EV.txt("Lecture Hall 301"), EV.vis("аудитория", "lecture hall", "0.93"), EV.noGeo],
    duplicates: [dup("ph_2410", "korea.ac.kr")],
  }),
  photo(5, {
    category: "libraries", tags: ["labs"], confidence: 82, tier: "verified", placeholder_height: 150,
    placeholder_caption: "reading room · placeholder", author: "H. Choi", published_at: "2024-11-06",
    evidence: [EV.geo(85), EV.cat("Korea University Library"), EV.vis("читальный зал", "reading room", "0.79")],
  }),
  photo(6, {
    category: "city", tags: ["student_life"], confidence: 79, tier: "likely", placeholder_height: 225,
    placeholder_caption: "anam-dong street · placeholder", source_url: "https://www.mapillary.com",
    source_domain: "mapillary.com", author: "Mapillary user", published_at: "2025-06-14",
    evidence: [EV.geo(640), EV.txt("Anam-dong"), EV.vis("городская улица", "city street", "0.84"), EV.noGeo],
    duplicates: [dup("ph_2510", "mapillary.com")],
  }),
  photo(7, {
    category: "campus", tags: ["student_life"], confidence: 74, tier: "likely", placeholder_height: 160,
    placeholder_caption: "campus path · placeholder", author: "Anonymous", published_at: "2022-09-30",
    evidence: [EV.cat("Universities in Seoul"), EV.txt("campus"), EV.noGeo],
  }),
  photo(8, {
    category: "classrooms", tags: ["labs"], confidence: 71, tier: "likely", placeholder_height: 200,
    placeholder_caption: "lab bench · placeholder", source_url: "https://www.flickr.com", source_domain: "flickr.com",
    license: "CC BY 2.0", author: "flickr user", published_at: "2023-04-11",
    evidence: [EV.txt("KU research lab"), EV.vis("лаборатория", "laboratory", "0.76"), EV.noGeo],
    duplicates: [dup("ph_2610", "flickr.com")],
  }),
  photo(9, {
    category: "city", tags: ["student_life"], confidence: 68, tier: "likely", placeholder_height: 175,
    placeholder_caption: "student cafe · placeholder", author: "Y. Kim", published_at: "2024-02-20",
    evidence: [EV.geo(910), EV.txt("student district"), EV.noGeo],
  }),
  photo(10, {
    category: "campus", tags: ["sport"], confidence: 64, tier: "likely", placeholder_height: 145,
    placeholder_caption: "stadium stand · placeholder", source_url: "https://www.flickr.com", source_domain: "flickr.com",
    license: "CC BY 2.0", author: "flickr user", published_at: "2021-11-02",
    evidence: [EV.txt("Korea University stadium"), EV.vis("стадион", "stadium", "0.72"), EV.noGeo],
  }),
  photo(11, {
    category: "campus", confidence: 41, tier: "unconfirmed", placeholder_height: 195,
    placeholder_caption: "unidentified building · placeholder", source_url: "https://example-blog.kr",
    source_domain: "example-blog.kr", license: "unknown", author: "—", published_at: "2020-07-15",
    evidence: [EV.txt("university"), EV.noGeo, EV.noLic],
  }),
  photo(12, {
    category: "city", confidence: 33, tier: "unconfirmed", placeholder_height: 165,
    placeholder_caption: "street view · placeholder", source_url: "https://web-search-result.example",
    source_domain: "web-search-result.example", license: "unknown", author: "—", published_at: "2019-05-08",
    evidence: [EV.vis("город", "city", "0.58"), EV.noGeo, EV.noLic],
  }),
  photo(13, {
    category: "libraries", tags: ["labs"], confidence: 86, tier: "verified", placeholder_height: 155,
    placeholder_caption: "archive shelves · placeholder", author: "D. Seo", published_at: "2025-08-01",
    evidence: [EV.geo(70), EV.cat("Korea University Library"), EV.vis("книжные стеллажи", "bookshelves", "0.9")],
  }),
  photo(14, {
    category: "classrooms", tags: ["student_life"], confidence: 77, tier: "likely", placeholder_height: 215,
    placeholder_caption: "seminar room · placeholder", author: "M. Han", published_at: "2024-09-19",
    evidence: [EV.geo(150), EV.txt("seminar"), EV.vis("семинар", "seminar", "0.81")],
  }),
];
