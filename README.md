# Visual Campus

**LOCUS Hackathon · Case 1 «Visual Campus»**

## Задача

Абитуриент хочет понять, как на самом деле выглядят кампус и студенческая жизнь вуза, но фотографии разбросаны по разным сайтам, часто без источника и с чужими местами. Нужно за ≤30 секунд по названию университета собрать **проверенный визуальный профиль**: фото по категориям, у каждого — источник, лицензия и уровень достоверности.

## Решение

1. **Распознавание** — пользователь вводит название (с опечатками, на любом языке). Бэкенд параллельно ищет в ROR и Wikidata, объединяет кандидатов и либо однозначно определяет вуз, либо предлагает выбрать.
2. **Сбор и проверка фото** *(следующий шаг)* — Wikimedia Commons, OpenStreetMap, Mapillary, Flickr, официальный сайт; для каждого фото считается шкала достоверности по доказательствам: геотег внутри контура кампуса, категория Commons, упоминания в описании, AI-распознавание сцены.
3. **Профиль** — фото по категориям, карта кампуса (2D / 3D / прогулка по панорамам), гид-маскот «Кампи», который отвечает только по найденным источникам.

## Стек

| Часть | Технологии |
|---|---|
| Backend | Python 3.12, FastAPI, httpx (asyncio), Pydantic v2, python-dotenv, Shapely |
| Frontend | Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS v4 |
| Дизайн | Claude Design (исходники в `design/`) |

## Структура репозитория

```
visual-campus/
├── design/                 экспорт макетов из Claude Design (.dc.html + README с токенами и контрактами данных)
├── backend/
│   ├── app/
│   │   ├── main.py         FastAPI, CORS, логирование времени запросов
│   │   ├── config.py       настройки из .env
│   │   ├── models.py       Pydantic-модели ответов
│   │   ├── routers/        /health, /resolve
│   │   └── services/       клиенты ROR и Wikidata, объединение и скоринг кандидатов
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── app/                страницы: / (поиск, реальный API), /collecting, /profile, /compare, /guide, /wardrobe, /unavailable
│   ├── components/         search, profile, photos, map, chat, guide, mascot, wardrobe, compare, ui, layout
│   ├── lib/
│   │   ├── api.ts          клиент бэкенда
│   │   ├── types.ts        типы данных (контракты из design/README.md)
│   │   ├── i18n.ts         тексты RU/EN
│   │   └── mock/           демо-данные для экранов, ещё не подключённых к API
│   └── .env.local.example
└── README.md
```

## Запуск локально

### Backend

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # ключи пока не нужны для /resolve
uvicorn app.main:app --reload --port 8000
```

Проверка:

```bash
curl localhost:8000/health
curl "localhost:8000/resolve?q=Korea%20University"
```

Документация API: http://localhost:8000/docs

### Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local   # NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev                        # http://localhost:3000
```

## API

### `GET /resolve?q=<название>`

Параллельно (asyncio + httpx, таймаут 5 с на источник) опрашивает:

- **ROR API v2** — сначала affiliation-матчер (устойчив к «грязным» названиям), затем обычный поиск для аббревиатур вроде `KAIST`;
- **Wikidata** — `wbsearchentities` → `wbgetentities` (координаты P625, сайт P856, категория Commons P373, ROR ID P6782). Если ничего не найдено, берётся исправление опечатки из поиска Wikipedia (`Koera Univrsity` → `korea university`), и ROR повторно опрашивается уже с исправленным запросом.

Кандидаты объединяются по ROR ID / Wikidata QID, иначе по совпадению названия и расстоянию ≤15 км. `match_score` = похожесть названия (с учётом алиасов и опечаток) + согласие двух источников + известность (число sitelinks в Wikidata).

| status | когда |
|---|---|
| `resolved` | лучший кандидат почти точно совпал по названию и заметно опережает остальных; запрос не является просто названием города |
| `ambiguous` | до 5 кандидатов на выбор |
| `not_found` | нет похожих кандидатов |

Если один источник упал или не ответил, ответ всё равно приходит, а в `sources_status` будет `timeout` или `error`. Если недоступны оба источника, возвращается `503`.

## Готовые компоненты, AI и внешние API

- **ROR (Research Organization Registry)** — https://ror.org, API v2: поиск организаций, ROR ID, города, сайты.
- **Wikidata** — https://www.wikidata.org: сущности вузов, координаты, категории Commons, связка с ROR.
- **Wikipedia Search API** — подсказка исправления опечаток в названии.
- **Claude Design** — дизайн интерфейса, персонажа и состояний; исходники в `design/`.
- **Claude Code** — разработка: перенос дизайна в Next.js, бэкенд, проверки.
- **Шрифты** — Instrument Sans и JetBrains Mono (Google Fonts через `next/font`).

*Раздел будет дополняться по мере подключения источников фото, карт (MapLibre GL JS, OpenStreetMap), панорам (Mapillary, Kakao Roadview) и LLM.*

## Ограничения

- С реальным API работает **только поиск университета** (`/`): найден, неоднозначно, не найден, загрузка, ошибка.
- Остальные экраны — загрузка профиля, профиль, детальный просмотр фото, карта кампуса, гид и чат, гардероб, сравнение — сверстаны на **демо-данных** (`frontend/lib/mock/`) и помечены плашкой **DEMO DATA**.
- Карта, 3D-вид и панорамы — CSS-заглушки из макетов. Компоненты уже разделены под MapLibre GL JS и MapillaryJS / Kakao Roadview (см. `frontend/components/map/types.ts`).
- В макете у поиска есть автоподсказки, но пока их нет: `/resolve` отвечает 2–4 с, для подсказок при вводе нужен отдельный быстрый эндпоинт.
- Классификация resolved/ambiguous подобрана эвристически и проверена на ограниченном наборе запросов.
