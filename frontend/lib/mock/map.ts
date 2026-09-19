// Sample map data for preview screens.
import type { Building, BuildingType, CampusMap } from "@/lib/types";

function bld(
  id: string, name: string, type: BuildingType, lng: number, lat: number, w: number, h: number,
  height: number | null, levels: number | null, photoIds: string[] = [], inside = true,
): Building {
  return {
    id, name, type, height_m: height, levels, photo_ids: photoIds, source: "OpenStreetMap", inside_campus: inside,
    polygon: [[lng - w, lat - h], [lng + w, lat - h], [lng + w, lat + h], [lng - w, lat + h]],
  };
}

export const MAP: CampusMap = {
  campus: {
    center: { lat: 37.5895, lng: 127.0323 },
    polygon: [[127.0268, 37.5862], [127.03, 37.5845], [127.0368, 37.5855], [127.0385, 37.589], [127.037, 37.593], [127.0315, 37.5938], [127.0272, 37.5915]],
    area_km2: 0.61,
    city_center: { name: "Сеул · Jongno", lat: 37.57, lng: 127.0 },
    distance_to_center_km: 4.2,
    transit: [
      { type: "metro", name: "Anam (Korea Univ.)", lat: 37.586, lng: 127.0295, walk_min: 4 },
      { type: "metro", name: "Korea University", lat: 37.5905, lng: 127.0272, walk_min: 7 },
      { type: "bus", name: "Anam-dong", lat: 37.5925, lng: 127.035, walk_min: 3 },
    ],
  },
  buildings: [
    bld("b1", "Main Hall", "academic", 127.0315, 37.5888, 0.0012, 0.0008, 32, 7, ["ph_1002", "ph_1007"]),
    bld("b2", "Central Library", "library", 127.0342, 37.5896, 0.0014, 0.0009, 41, 9, ["ph_1001", "ph_1005", "ph_1013"]),
    bld("b3", "Science Building", "academic", 127.0296, 37.5901, 0.001, 0.0007, 28, 6, ["ph_1004"]),
    bld("b4", "Anam Hall (dorm)", "dorm", 127.0281, 37.5876, 0.0009, 0.001, 24, 8),
    bld("b5", "Frontier Hall (dorm)", "dorm", 127.0288, 37.5866, 0.0008, 0.0007, 21, 7),
    bld("b6", "Hwajeong Gymnasium", "sport", 127.0358, 37.5872, 0.0013, 0.001, 26, 4, ["ph_1003"]),
    bld("b7", "Sports Field", "sport", 127.0336, 37.5862, 0.0016, 0.0008, null, null, ["ph_1010"]),
    bld("b8", "Research Lab A", "lab", 127.0362, 37.5912, 0.0009, 0.0007, 34, 8, ["ph_1008"]),
    bld("b9", "Research Lab B", "lab", 127.035, 37.5922, 0.0008, 0.0006, 30, 7),
    bld("b10", "Student Union", "food", 127.0322, 37.5908, 0.0009, 0.0006, 18, 4, ["ph_1014"]),
    bld("b11", "Cafeteria", "food", 127.0306, 37.5918, 0.0008, 0.0005, 12, 3, ["ph_1009"]),
    bld("b12", "Law School", "academic", 127.033, 37.5878, 0.001, 0.0007, 25, 6),
    bld("b13", "Media Centre", "academic", 127.03, 37.593, 0.0009, 0.0006, 22, 5),
    bld("b14", "Archive Annex", "library", 127.0356, 37.5902, 0.0007, 0.0005, 16, 4),
    bld("b15", "Service Block", "other", 127.029, 37.591, 0.0007, 0.0005, 9, 2),
    bld("b16", "Anam-dong block", "other", 127.0248, 37.5884, 0.0012, 0.0009, 20, 5, [], false),
    bld("b17", "Anam-dong block", "other", 127.0252, 37.5906, 0.001, 0.0008, 17, 5, [], false),
    bld("b18", "Jegi-dong block", "other", 127.0398, 37.5876, 0.0013, 0.001, 23, 6, [], false),
  ],
  photo_pins: [
    { photo_id: "ph_1001", lat: 37.5896, lng: 127.0342, heading_deg: 210, tier: "verified", confidence: 94, thumb_url: null, building_id: "b2" },
    { photo_id: "ph_1002", lat: 37.5888, lng: 127.0315, heading_deg: 45, tier: "verified", confidence: 91, thumb_url: null, building_id: "b1" },
    { photo_id: "ph_1003", lat: 37.5872, lng: 127.0358, heading_deg: 300, tier: "verified", confidence: 88, thumb_url: null, building_id: "b6" },
    { photo_id: "ph_1004", lat: 37.5901, lng: 127.0296, heading_deg: null, tier: "verified", confidence: 85, thumb_url: null, building_id: "b3" },
    { photo_id: "ph_1005", lat: 37.5893, lng: 127.0345, heading_deg: 180, tier: "verified", confidence: 82, thumb_url: null, building_id: "b2" },
    { photo_id: "ph_1013", lat: 37.5898, lng: 127.0339, heading_deg: 120, tier: "verified", confidence: 86, thumb_url: null, building_id: "b2" },
    { photo_id: "ph_1014", lat: 37.5908, lng: 127.0322, heading_deg: 90, tier: "likely", confidence: 77, thumb_url: null, building_id: "b10" },
    { photo_id: "ph_1008", lat: 37.5912, lng: 127.0362, heading_deg: null, tier: "likely", confidence: 71, thumb_url: null, building_id: "b8" },
    { photo_id: "ph_1009", lat: 37.5918, lng: 127.0306, heading_deg: 15, tier: "likely", confidence: 68, thumb_url: null, building_id: "b11" },
    { photo_id: "ph_1010", lat: 37.5862, lng: 127.0336, heading_deg: 270, tier: "likely", confidence: 64, thumb_url: null, building_id: "b7" },
    { photo_id: "ph_1006", lat: 37.593, lng: 127.0318, heading_deg: 340, tier: "likely", confidence: 79, thumb_url: null, building_id: null },
    { photo_id: "ph_1011", lat: 37.588, lng: 127.03, heading_deg: null, tier: "unconfirmed", confidence: 41, thumb_url: null, building_id: null },
    { photo_id: "ph_1012", lat: 37.5924, lng: 127.0372, heading_deg: null, tier: "unconfirmed", confidence: 33, thumb_url: null, building_id: null },
  ],
  bbox: { w: 127.0238, e: 127.0408, s: 37.5836, n: 37.5946 },
};
