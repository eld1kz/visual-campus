import type { Photo, PhotoCategory, PhotoTag } from "@/lib/types";

export const CATEGORIES: PhotoCategory[] = ["campus", "dorms", "classrooms", "libraries", "city"];
export const FILTER_TAGS: PhotoTag[] = ["dorm", "sport", "labs", "student_life"];

export type PhotoTab = "all" | PhotoCategory;
export type PhotoSort = "confidence" | "date";

export type PhotoFilter = {
  tab: PhotoTab;
  tags: PhotoTag[];
  showUnconfirmed: boolean;
  showHistoric: boolean;
  sort: PhotoSort;
};

export function filterPhotos(photos: Photo[], f: PhotoFilter): Photo[] {
  const list = photos.filter(
    (p) =>
      (f.tab === "all" || p.category === f.tab) &&
      (p.tier !== "unconfirmed" || f.showUnconfirmed) &&
      (p.freshness !== "historic" || f.showHistoric) &&
      (f.tags.length === 0 || f.tags.some((tag) => p.tags.includes(tag))),
  );
  return f.sort === "confidence"
    ? list.sort((a, b) => b.confidence - a.confidence)
    : list.sort((a, b) => {
        const aRank = `${a.date_taken ? "2" : a.date_uploaded ? "1" : "0"}${a.date_taken ?? a.date_uploaded ?? ""}`;
        const bRank = `${b.date_taken ? "2" : b.date_uploaded ? "1" : "0"}${b.date_taken ?? b.date_uploaded ?? ""}`;
        return bRank.localeCompare(aRank);
      });
}

export function freshnessBadge(photo: Photo, lang: "ru" | "en" = "en"): string {
  if (photo.date_taken) return photo.freshness === "2024_plus" ? "2024+" : photo.date_taken.slice(0, 4);
  if (photo.date_uploaded) return `${lang === "ru" ? "загружено" : "uploaded"} ${photo.date_uploaded.slice(0, 4)}`;
  return lang === "ru" ? "дата неизвестна" : "date unknown";
}

export function dateSourceLabel(photo: Photo, lang: "ru" | "en" = "en"): string {
  const en = {
    exif: "EXIF",
    source_metadata: "source metadata",
    structured_data: "structured data",
    upload_only: "upload date only",
    text_hint: "text hint only",
    unknown: "unknown",
  };
  const ru = {
    exif: "EXIF",
    source_metadata: "метаданные источника",
    structured_data: "структурированные данные",
    upload_only: "только дата загрузки",
    text_hint: "подсказка только в тексте",
    unknown: "неизвестно",
  };
  return (lang === "ru" ? ru : en)[photo.date_source];
}

export function countInTab(photos: Photo[], tab: PhotoTab, showUnconfirmed: boolean): number {
  return photos.filter((p) => (tab === "all" || p.category === tab) && (p.tier !== "unconfirmed" || showUnconfirmed))
    .length;
}

export function categoryLabel(category: PhotoCategory, tabs: string[]): string {
  return tabs[CATEGORIES.indexOf(category) + 1];
}
