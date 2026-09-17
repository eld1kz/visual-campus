# Visual Campus — контракт данных

Единый источник правды для всех агентов и людей. Код обязан ему соответствовать:

- бэкенд — `backend/app/models.py` (Pydantic);
- фронтенд — `frontend/lib/types.ts` (TypeScript).

Эти два файла и этот документ меняет **только главный агент**. Субагент, которому нужно изменение, описывает его в разделе «Нужны ли изменения контракта» своего отчёта и не правит контракт сам.

Общие правила:

- JSON в `snake_case`. Координаты — WGS84. Полигоны — `[[lng, lat], ...]` (порядок GeoJSON, долгота первой).
- Даты — ISO 8601: `YYYY-MM-DD` или `YYYY-MM-DDTHH:MM:SSZ`.
- Поле, которого нет в источнике, — `null` (или `"unknown"` для `license`), **никогда не выдумывается**.
- `lang` (`ru` | `en`) задаёт язык подписей (`evidence.label`, резюме). По умолчанию `ru`.
- Ошибка до начала ответа — JSON `ErrorResponse`: `{ "detail": string, "sources_status": SourceStatus[] }`.

---

## 1. Бюджет времени

| Что | Предел | Кто отвечает |
|---|---|---|
| Весь профиль (от запроса до события `done`) | ≤ 30 с | api-agent (оркестратор) |
| Один источник (сетевой запрос сборщика целиком) | ≤ 8 с, затем статус `timeout` | sources-agent + обёртка `run_source` |
| Первое событие `photo` | ≤ 5 с от запроса | api-agent + sources-agent |
| Повторный запрос того же профиля | из кэша, `done` < 1 с | api-agent |
| `GET /resolve` | как реализовано: таймаут источника `SOURCE_TIMEOUT_S` (5 с) | — |

Следствия:

- Источники запускаются **параллельно**. Медленный или упавший источник не задерживает остальные и не ломает ответ.
- Фото проверяются и отправляются **по мере прихода** пачек, а не после сбора всего.
- Если полигон кампуса (OSM) ещё не пришёл, фото оцениваются по расстоянию до точки вуза. Когда полигон приходит, уже отправленные фото пересчитываются и отправляются повторно с тем же `id` (см. «upsert» ниже).
- Vision-проверка — только если укладывается в бюджет; иначе фото уходит без неё.

---

## 2. `GET /resolve?q=` — реализовано

Распознаёт вуз по названию на любом языке и с опечатками.

```jsonc
// 200 ResolveResponse
{
  "query": "Koera Univrsity",
  "corrected_query": "korea university",   // null, если исправление не понадобилось
  "status": "resolved",                     // "resolved" | "ambiguous" | "not_found"
  "university": UniversityCandidate | null, // только при status = "resolved"
  "candidates": UniversityCandidate[],      // лучшие совпадения, не больше 5
  "sources_status": [{ "name": "ror", "status": "ok" }],  // status: "ok" | "timeout" | "error"
  "took_ms": 812
}

// UniversityCandidate
{
  "id": "https://ror.org/047dqcg40",  // ROR ID, если есть, иначе Wikidata QID
  "name": "Korea University",
  "aliases": ["고려대학교", "KU"],
  "city": "Seoul" | null,
  "country": "South Korea" | null,
  "lat": 37.59 | null, "lng": 127.03 | null,
  "website": "https://www.korea.ac.kr" | null,
  "wikidata_id": "Q39997" | null,        // ← передаётся в /profile и /campus
  "ror_id": "https://ror.org/047dqcg40" | null,
  "commons_category": "Korea University" | null,
  "match_score": 0.93                    // 0..1
}
```

Ошибки: `422` — пустой/слишком длинный `q`; `503` — упали все реестры (`ErrorResponse` со `sources_status`).

---

## 3. `GET /profile/{wikidata_id}?lang=ru` — SSE-стрим

> **Статус:** сейчас эндпоинт отдаёт готовый JSON `ProfileResponse` за один раз. Целевой формат — SSE ниже; перевод делает api-agent. `ProfileResponse` остаётся форматом кэша.

`wikidata_id` — `^Q\d+$`.

**До начала стрима** (обычный JSON, не SSE): `422` — неверный ID; `404` — в Wikidata нет такого элемента; `503` — Wikidata недоступна.

**Стрим:** `Content-Type: text/event-stream`. Каждое событие:

```
event: <тип>
data: <одна строка JSON>

```

### Порядок событий

1. `source_status` для **каждого** источника со статусом `pending` — сразу после старта.
2. Вперемешку, по мере готовности: `source_status` (итоговый статус источника), `photo`, `summary`.
3. `done` — **всегда последнее** событие; после него сервер закрывает стрим.

Клиент считает стрим оборванным, если соединение закрылось без `done`.

### `source_status`

```jsonc
{
  "name": "wikimedia_commons",
  "status": "pending",   // "pending" | "ok" | "timeout" | "error" | "skipped"
  "count": 0,            // сколько фото из источника прошло в профиль (после проверки и дедупликации)
  "took_ms": null        // int, когда источник завершился; null пока pending
}
```

- `skipped` — источник не запускался по честной причине: нет API-ключа, нет координат вуза и т. п.
- Одно имя может прийти несколько раз; клиент заменяет запись по `name`.

Имена источников (ровно эти строки):

| `name` | Что даёт |
|---|---|
| `wikidata` | карточка вуза, координаты, сайт, категория Commons, центр города |
| `openstreetmap` | полигон кампуса, здания с типами |
| `wikimedia_commons` | фото (категория, подкатегории, геопоиск) |
| `wikipedia` | тексты для резюме |
| `flickr` | фото с CC-лицензиями в гео-рамке (нужен `FLICKR_API_KEY`) |
| `mapillary` | уличные снимки (нужен `MAPILLARY_TOKEN`) |
| `official_site` | `og:image` с официального сайта вуза |

### `photo`

Объект `Photo`. **Upsert по `id`**: повторное событие с тем же `id` заменяет прежнее фото целиком (новая оценка после прихода полигона, результат vision, найденные дубли).

```jsonc
{
  "id": "commons-12345678",            // "<префикс источника>-<id в источнике>", стабилен между запросами
  "thumb_url": "https://…/320px-….jpg" | null,
  "full_url": "https://…/….jpg",
  "category": "campus",                // "campus" | "dorms" | "classrooms" | "libraries" | "city" — ровно одна
  "tags": ["sport"],                   // подмножество "sport" | "labs" | "dorm" | "student_life"
  "confidence": 86,                    // 0..100
  "tier": "verified",                  // "verified" | "likely" | "unconfirmed"
  "source_url": "https://commons.wikimedia.org/wiki/File:….jpg",  // страница фото у источника
  "source_domain": "commons.wikimedia.org",
  "author": "Jane Doe",                // "unknown", если не указан
  "license": "CC BY-SA 4.0",           // "unknown", если источник не указывает
  "published_at": "2019-05-02" | null, // дата съёмки, иначе дата публикации
  "retrieved_at": "2026-09-17",        // когда мы получили данные
  "lat": 37.5891 | null,
  "lng": 127.0318 | null,
  "heading_deg": 135 | null,           // направление съёмки, 0 = север, по часовой
  "evidence": [
    { "type": "geo", "label": "Геотег внутри границ кампуса, 240 м от центра", "weight": 28 }
  ],
  "duplicates": [
    { "id": "flickr-5555", "thumb_url": "…" | null, "source_url": "https://www.flickr.com/photos/…" }
  ]
}
```

**Evidence** — почему мы верим (или не верим), что на фото этот кампус:

| `type` | Смысл | Знак `weight` |
|---|---|---|
| `geo` | геотег относительно полигона/точки кампуса | + внутри/рядом, − далеко |
| `category` | категория/подкатегория Commons вуза, тег здания OSM | + |
| `text` | название вуза в заголовке/описании; официальный домен | + |
| `vision` | результат визуальной проверки моделью | + или − |
| `missing` | нет важного признака (геотега, лицензии) | − |
| `date` | снимок старый — кампус мог измениться | − |
| `content` | похоже на людей/мероприятие/логотип, а не на место | − |

`date` и `content` уже реализованы в `backend/app/services/evidence.py` и потому входят в контракт.

**Уровни и честная неопределённость:**

- `confidence = clamp(40 + Σ weight, 0, 100)`.
- `verified` — ≥ 80; `likely` — 60..79; `unconfirmed` — < 60.
- Без положительных доказательств места (`geo`, `category`, `text`) фото не может подняться выше `unconfirmed`. Нет данных — низкая оценка, а не догадка.
- `unconfirmed` отправляются клиенту; UI скрывает их по умолчанию.
- Логотипы, схемы, карты, скриншоты в профиль не попадают вовсе.

**Дубли:** в профиль идёт одна копия — с наибольшим `confidence`; остальные попадают в её `duplicates`.

### `summary`

```jsonc
{
  "text": "Кампус расположен … [1]. Общежития … [2].",
  "citations": [ { "n": 1, "title": "Wikipedia — Korea University", "url": "https://…" } ]
}
```

- Генерируется LLM **только** по текстам, собранным из источников этого профиля. Каждое утверждение опирается на сноску `[n]`, каждое `n` есть в `citations`.
- Без `LLM_API_KEY` — извлечение из Wikipedia без переписывания (как сейчас).
- Нет текстов — `{ "text": "", "citations": [] }`; событие всё равно отправляется.

### `done`

```jsonc
{
  "university": ProfileUniversity,
  "stats": { "photos": 42, "verified": 20, "likely": 15, "hidden": 7, "duplicates": 5 },
  "generated_in_ms": 18400,
  "cached": false,
  "partial": false
}
```

`hidden` — число `unconfirmed`. `stats` считаются по финальному состоянию всех `photo`.

`partial` — `true`, если хотя бы один источник закончился `timeout` или `error` (`skipped` не считается) либо сработал общий дедлайн 30 с. UI показывает честную плашку «профиль неполный», кэш хранит такой профиль меньше.

```jsonc
// ProfileUniversity
{
  "id": "Q39997",
  "name": "Korea University",
  "aliases": ["고려대학교"],
  "city": "Seoul" | null, "country": "South Korea" | null,
  "website": "https://www.korea.ac.kr" | null,
  "lat": 37.59 | null, "lng": 127.03 | null,
  "campus_polygon": [[127.03, 37.59], …] | null,   // внешний контур крупнейшего полигона OSM
  "campus_area_km2": 0.61 | null,
  "distance_to_center_km": 4.8 | null,
  "city_center": { "name": "Seoul", "lat": 37.57, "lng": 126.98 } | null,
  "wikidata_id": "Q39997",
  "ror_id": "https://ror.org/…" | null,
  "commons_category": "Korea University" | null,
  "osm_url": "https://www.openstreetmap.org/way/…" | null
}
```

### Кэш

Готовый профиль хранится как `ProfileResponse` (`university`, `generated_in_ms`, `sources_status`, `summary`, `stats`, `photos`) по ключу `(wikidata_id, lang)`. Запрос из кэша проигрывает те же события в том же порядке и заканчивается `done` с `cached: true` (`partial` — как при сборке). Частичный профиль (упал источник) кэшируется на меньший срок, чем полный.

---

## 4. `GET /campus/{wikidata_id}` — данные для карты

Форма повторяет `design/README.md` → «Data contracts → campus map» и `CampusMap` во фронтенде.

```jsonc
{
  "campus": {
    "center": { "lat": 37.5895, "lng": 127.0323 },
    "polygon": [[lng, lat], …] | null,
    "area_km2": 0.61 | null,
    "city_center": { "name": "Seoul", "lat": 37.57, "lng": 126.98 } | null,
    "distance_to_center_km": 4.8 | null,       // по прямой от center до city_center
    "transit": [ { "type": "metro", "name": "Anam", "lat": …, "lng": …, "walk_min": 6 } ]  // может быть []
  },
  "buildings": [
    {
      "id": "osm-way-123",
      "name": "Main Building",                // "" если в OSM нет имени
      "type": "academic",                     // "academic" | "dorm" | "library" | "sport" | "lab" | "food" | "other"
      "polygon": [[lng, lat], …],
      "height_m": 22.5 | null,                // из OSM height; не выдумывается
      "levels": 5 | null,                     // из OSM building:levels
      "photo_ids": ["commons-12345678"],      // фото, чей геотег внутри здания
      "source": "OpenStreetMap",
      "inside_campus": true
    }
  ],
  "photo_pins": [
    {
      "photo_id": "commons-12345678",
      "lat": 37.5891, "lng": 127.0318,
      "heading_deg": 135 | null,
      "tier": "verified", "confidence": 86,
      "thumb_url": "…" | null,
      "building_id": "osm-way-123" | null
    }
  ],
  "panoramas": {
    "provider": "mapillary" | "kakao" | "google" | null,  // null, если панорам нет
    "available": true,
    "checked_providers": ["mapillary", "kakao"],        // что реально проверили
    "start": { "lat": …, "lng": …, "captured_at": "2023-06-01" } | null
  }
}
```

- `404` — нет такого элемента в Wikidata; `503` — Wikidata недоступна. Центр вуза без координат — `404` с понятным `detail`.
- `photo_pins` берутся из кэша профиля (только фото с `lat`/`lng`). Нет профиля в кэше — `[]`, а не выдумка.
- Сопоставление типов OSM → `type`: `university|college|school` → `academic`; `dormitory` → `dorm`; `library` (amenity) → `library`; `sports_centre|stadium|pitch` → `sport`; `laboratory|research_institute` → `lab`; `restaurant|cafe|canteen|food_court` → `food`; остальное → `other`.

---

## 5. `POST /chat` — гид-маскот (зона mascot-agent)

```jsonc
// запрос
{ "wikidata_id": "Q39997", "lang": "ru", "messages": [ { "role": "user", "text": "Где общежития?" } ] }

// 200 ChatMessage
{
  "role": "assistant",
  "text": "Общежития стоят на склоне к западу [1].",
  "mascot_state": "talking",          // "talking" | "pointing" | "dont_know"
  "citations": [ { "n": 1, "title": "…", "url": "…" } ],
  "actions": [ { "type": "tab", "tab": "dorms" } ],  // "photos" {photo_ids} | "map" {building_id?} | "tab" {tab}
  "checked": null                      // при dont_know — строка: где искали
}
```

Отвечает только по собранному профилю (кэш): резюме и его источники, метаданные фото, здания OSM. Нет ответа в источниках → `mascot_state: "dont_know"`, пустые `citations`, заполненный `checked`. Профиля нет в кэше → `409` с `detail`.

---

## 6. Внутренний формат: `RawImage` (сборщики → пайплайн проверки)

Pydantic-модель в `backend/app/models.py`. Сборщик заполняет только то, что источник действительно отдаёт; остальное — `None`/пусто. Сборщик **ничего не оценивает**: не ставит категорию, уровень и уверенность.

```python
class RawImage(BaseModel):
    id: str                        # "commons-<pageid>", "flickr-<id>", "mapillary-<id>", "site-<sha1(url)[:12]>"
    source: SourceName             # имя источника из таблицы в §3
    source_url: str                # страница фото у источника (для ссылки в UI)
    source_domain: str             # "commons.wikimedia.org", "www.flickr.com", "korea.ac.kr", …
    full_url: str
    thumb_url: str | None = None
    title: str = ""
    description: str = ""          # без HTML
    source_categories: list[str] = []   # категории Commons / теги Flickr, как есть
    matched_category: str | None = None # категория вуза, через которую нашли файл (Commons)
    matched_subcategory: bool = False   # True, если через подкатегорию, а не саму категорию
    found_by: Literal["category", "geosearch", "bbox", "site", "text"]  # как нашли
    author: str | None = None
    license: str | None = None     # короткое имя: "CC BY-SA 4.0", "CC0", …
    license_url: str | None = None
    published_at: str | None = None  # ISO; дата съёмки, иначе дата публикации
    lat: float | None = None
    lng: float | None = None
    heading_deg: float | None = None
    width: int | None = None
    height: int | None = None
    sha1: str | None = None        # если источник отдаёт хеш файла
    is_official_site: bool = False # фото с домена из website вуза
```

### Интерфейс сборщика (`backend/app/services/sources/`)

```python
@dataclass
class SourceQuery:
    wikidata_id: str
    names: list[str]              # все названия вуза на всех языках
    lat: float | None
    lng: float | None
    website: str | None
    commons_category: str | None
    bbox: tuple[float, float, float, float] | None  # (west, south, east, north), если известен полигон

class SourceResult(BaseModel):
    name: str                     # имя из таблицы §3
    status: Literal["ok", "timeout", "error", "skipped"]
    took_ms: int
    images: list[RawImage] = []
    detail: str | None = None     # причина error/skipped для логов (не для UI)

async def collect(query: SourceQuery, client: httpx.AsyncClient) -> SourceResult: ...
```

- Каждый сборщик сам ловит свои исключения и таймаут (≤ 8 с) и возвращает `SourceResult` с нужным статусом — исключение наружу не выходит.
- OSM вместо фото отдаёт форму кампуса:

```python
class CampusShape(BaseModel):
    polygon: list[list[float]] | None   # [[lng, lat], …]
    area_km2: float | None
    osm_url: str | None
    buildings: list[Building]           # Building из §4

async def find_campus(query: SourceQuery, client: httpx.AsyncClient) -> tuple[SourceResult, CampusShape | None]: ...
```

### Интерфейс пайплайна (`backend/app/services/pipeline/`)

```python
@dataclass
class CampusContext:
    names: list[str]
    lat: float | None
    lng: float | None
    polygon: BaseGeometry | None      # shapely; None, пока OSM не ответил
    buildings: list[Building]
    official_domains: list[str]       # домен(ы) из website
    today: date
    lang: str

def score(raw: RawImage, ctx: CampusContext) -> Photo | None   # чистая функция, без сети; None — не фото места
def score(raw: RawImage, ctx: CampusContext, vision: VisionResult | None = None) -> Photo | None
async def classify(contents: list[bytes]) -> list[VisionResult | None]  # локальный CLIP по миниатюрам; None — нет вердикта
# VisionResult(place_prob: float, top: str): доля вероятности на «местах» (корпус, территория, читальный зал…).
# place_prob ≥ 0.5 → vision +12; < 0.35 → vision −30 и потолок unconfirmed (как content). Vision сам по себе не место.

class Deduplicator:                  # состояние на один профиль
    def add(self, photo: Photo, raw: RawImage) -> list[Photo]   # фото, которые нужно (пере)отправить событием photo
```

Категория: сначала метаданные (подкатегория Commons, тип здания OSM, в которое попал геотег), затем текст, затем модель. Нет признаков — `campus`, если фото на кампусе, иначе `city`.

---

## 7. Переменные окружения (`backend/.env`)

| Переменная | Кто использует | Без неё |
|---|---|---|
| `FLICKR_API_KEY` | sources-agent | `flickr` → `skipped` |
| `MAPILLARY_TOKEN` | sources-agent, map-agent (бэкенд `/campus`) | `mapillary` → `skipped`, панорамы не проверяются |
| `KAKAO_API_KEY` | map-agent | Kakao не проверяется |
| `LLM_API_KEY` | api-agent (резюме), mascot-agent (чат) | резюме из Wikipedia без LLM; чат отвечает поиском по текстам или `dont_know` |
| `VISION_ENABLED` | verify-agent (локальный CLIP, `pipeline/vision.py`) | по умолчанию `1`; `0` — фото оцениваются только по метаданным |
| `SOURCE_TIMEOUT_S` | `/resolve` | 5 с |

Фронтенд: `NEXT_PUBLIC_API_URL` (по умолчанию `http://localhost:8000`), `NEXT_PUBLIC_MAPILLARY_TOKEN`, `NEXT_PUBLIC_KAKAO_JS_KEY` — ключи для клиентских SDK карты.
