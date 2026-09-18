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
        "building_subject": "Здание кампуса: «{b}»",
        "name": "Описание упоминает «{n}»",
        "official": "Фото с официального сайта {s}",
        "no_license": "Лицензия не указана на странице источника",
        "old": "Снимок {y} года — кампус мог измениться",
        "not_visually_checked": "Не проверено визуально (лимит времени)",
        "vision_campus_place": "Визуальная проверка: похоже на место кампуса",
        "vision_not_campus_place": "Визуальная проверка: не похоже на место кампуса",
        "vision_veto": "Визуальная проверка: уверенно не место кампуса (логотип, люди, объект крупным планом)",
        "vision_inconclusive": "Визуальная проверка неубедительна",
        "claude_campus_place": "Проверка Claude: на фото место кампуса",
        "claude_not_campus_place": "Проверка Claude: на фото не место кампуса",
        "claude_vision_veto": "Проверка Claude: это не фотография (схема, логотип, документ)",
        "claude_inconclusive": "Проверка Claude неубедительна",
        "people": "Похоже на фото людей или мероприятия, а не места",
        "specimen": "Похоже на снимок образца или опыта крупным планом, а не места",
        "food_closeup": "Похоже на еду крупным планом, а не на место кампуса",
        "other_institution": "Похоже на другое учреждение («{m}»), а не на кампус",
        "unnamed_building": "без названия",
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
        "building_subject": "Campus building: “{b}”",
        "name": "Description mentions “{n}”",
        "official": "Image from the official website {s}",
        "no_license": "No license stated on source page",
        "old": "Taken in {y} — the campus may have changed",
        "not_visually_checked": "Not visually checked (time limit)",
        "vision_campus_place": "Visual check: looks like a campus place",
        "vision_not_campus_place": "Visual check: does not look like a campus place",
        "vision_veto": "Visual check: confidently not a campus place (logo, people or close-up object)",
        "vision_inconclusive": "Visual check inconclusive",
        "claude_campus_place": "Claude check: shows a campus place",
        "claude_not_campus_place": "Claude check: not a campus place",
        "claude_vision_veto": "Claude check: not a photograph (chart, logo, document)",
        "claude_inconclusive": "Claude check inconclusive",
        "people": "Looks like a photo of people or an event, not a place",
        "specimen": "Looks like a close-up of a sample or experiment, not a place",
        "food_closeup": "Looks like a close-up of food, not a campus place",
        "other_institution": "Looks like a different institution (“{m}”), not the campus",
        "unnamed_building": "unnamed",
    },
}


def labels(lang: str) -> dict[str, str]:
    return LABELS.get(lang, LABELS["en"])


def fmt_distance(meters: float, lang: str) -> str:
    if meters < 1000:
        return f"{round(meters / 10) * 10:.0f} {'м' if lang == 'ru' else 'm'}"
    return f"{meters / 1000:.1f} {'км' if lang == 'ru' else 'km'}"
