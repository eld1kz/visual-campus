"""Evidence labels in the profile language (docs/CONTRACT.md §3)."""

LABELS = {
    "ru": {
        "geo_inside": "Геотег внутри границ кампуса, {d} от центра",
        "geo_edge": "Геотег в {d} за границей кампуса — у самой границы",
        "geo_just_outside": "Геотег в {d} за границей кампуса",
        "geo_near_point": "Геотег в {d} от точки университета",
        "geo_point": "Геотег в {d} от точки университета; границы кампуса неизвестны",
        "geo_away": "Геотег в {d} от кампуса",
        "no_geo": "Нет геотега",
        "category": "Находится в категории Commons «{c}»",
        "subcategory": "Находится в подкатегории Commons «{c}»",
        "building": "Геотег внутри здания OSM «{b}» ({t})",
        "name": "Описание упоминает «{n}»",
        "official": "Фото с официального сайта {s}",
        "no_license": "Лицензия не указана на странице источника",
        "old": "Снимок {y} года — кампус мог измениться",
        "people": "Похоже на фото людей или мероприятия, а не места",
        "other_institution": "Похоже на другое учреждение («{m}»), а не на кампус",
        "unnamed_building": "без названия",
        "quality": "Отмечено на Commons как качественный снимок («{c}»)",
        "vision_place": "Модель видит место: {w}",
        "vision_not_place": "Модель видит не место, а {w}",
    },
    "en": {
        "geo_inside": "Geotag inside campus boundary, {d} from centre",
        "geo_edge": "Geotag {d} outside campus boundary — right at the edge",
        "geo_just_outside": "Geotag {d} outside campus boundary",
        "geo_near_point": "Geotag {d} from the university point",
        "geo_point": "Geotag {d} from the university point; campus boundary unknown",
        "geo_away": "Geotag {d} from campus",
        "no_geo": "No geotag",
        "category": "In Commons category “{c}”",
        "subcategory": "In Commons subcategory “{c}”",
        "building": "Geotag inside OSM building “{b}” ({t})",
        "name": "Description mentions “{n}”",
        "official": "Image from the official website {s}",
        "no_license": "No license stated on source page",
        "old": "Taken in {y} — the campus may have changed",
        "people": "Looks like a photo of people or an event, not a place",
        "other_institution": "Looks like a different institution (“{m}”), not the campus",
        "unnamed_building": "unnamed",
        "quality": "Marked on Commons as a quality picture (“{c}”)",
        "vision_place": "The model sees a place: {w}",
        "vision_not_place": "The model sees not a place but {w}",
    },
}


# What CLIP saw (pipeline/vision.py PROMPTS keys), as it reads inside the vision labels above.
VISION_NAMES = {
    "ru": {
        "building": "корпус снаружи", "campus": "территория кампуса", "aerial": "кампус с высоты",
        "gate": "главный вход или ворота", "library": "читальный зал", "classroom": "аудитория",
        "sport": "спортивный объект", "interior": "холл или атриум", "cafeteria": "столовая",
        "portrait": "портрет человека", "event": "людей на мероприятии", "group": "групповое фото",
        "car": "автомобиль", "sign": "табличку или текст", "document": "документ или книгу",
        "artwork": "гравюру, рисунок или картину", "chart": "график или скриншот", "object": "предмет крупным планом",
        "statue": "статую или скульптуру", "nature": "животное или растение крупным планом",
        "lab_people": "людей в лаборатории", "lab_equipment": "лабораторное оборудование", "logo": "логотип",
    },
    "en": {
        "building": "a building exterior", "campus": "campus grounds", "aerial": "an aerial view of the campus",
        "gate": "the main gate or entrance", "library": "a library reading room", "classroom": "a lecture hall",
        "sport": "a sports facility", "interior": "an atrium or hallway",
        "cafeteria": "a cafeteria", "portrait": "a portrait of a person", "event": "people at an event",
        "group": "a group photo", "car": "a car", "sign": "a sign or text", "document": "a document or book",
        "artwork": "an engraving, drawing or painting", "chart": "a chart or screenshot",
        "object": "an object close-up", "statue": "a statue or sculpture", "nature": "an animal or plant close-up",
        "lab_people": "people in a laboratory", "lab_equipment": "laboratory equipment", "logo": "a logo",
    },
}


def vision_name(key: str, lang: str) -> str:
    return VISION_NAMES.get(lang, VISION_NAMES["en"]).get(key, key)


def labels(lang: str) -> dict[str, str]:
    return LABELS.get(lang, LABELS["en"])


def fmt_distance(meters: float, lang: str) -> str:
    if meters < 1000:
        return f"{round(meters / 10) * 10:.0f} {'м' if lang == 'ru' else 'm'}"
    return f"{meters / 1000:.1f} {'км' if lang == 'ru' else 'km'}"
