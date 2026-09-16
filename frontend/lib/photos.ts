import type { Photo, PhotoCategory, PhotoTag } from "@/lib/types";

export const CATEGORIES: PhotoCategory[] = ["campus", "dorms", "classrooms", "libraries", "city"];
export const FILTER_TAGS: PhotoTag[] = ["dorm", "sport", "labs", "student_life"];

export type PhotoTab = "all" | PhotoCategory;
export type PhotoSort = "confidence" | "date";

export type PhotoFilter = {
  tab: PhotoTab;
  tags: PhotoTag[];
  showUnconfirmed: boolean;
  sort: PhotoSort;
};

export function filterPhotos(photos: Photo[], f: PhotoFilter): Photo[] {
  const list = photos.filter(
    (p) =>
      (f.tab === "all" || p.category === f.tab) &&
      (p.tier !== "unconfirmed" || f.showUnconfirmed) &&
      (f.tags.length === 0 || f.tags.some((tag) => p.tags.includes(tag))),
  );
  return f.sort === "confidence"
    ? list.sort((a, b) => b.confidence - a.confidence)
    : list.sort((a, b) => b.published_at.localeCompare(a.published_at));
}

export function countInTab(photos: Photo[], tab: PhotoTab, showUnconfirmed: boolean): number {
  return photos.filter((p) => (tab === "all" || p.category === tab) && (p.tier !== "unconfirmed" || showUnconfirmed))
    .length;
}

export function categoryLabel(category: PhotoCategory, tabs: string[]): string {
  return tabs[CATEGORIES.indexOf(category) + 1];
}
