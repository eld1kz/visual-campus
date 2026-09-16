# Handoff: Visual Campus — verified campus photo profile, campus map, guide mascot

## Overview
Visual Campus takes a university name and returns, in under 30 seconds, a verified visual profile of the campus and student life: photos with stated sources, licenses and confidence tiers, a campus map (2D / 3D / street-level walk), and an AI guide mascot ("Кампи") that answers questions strictly from the sources collected for that university.

Product values: verifiability, source transparency, speed. Interface language Russian with an RU/EN switch. Light and dark theme. Desktop + mobile.

## About the Design Files
The files in this bundle are **design references written as HTML** (Design Components: a streaming template + a logic class in one `.dc.html` file). They are prototypes showing intended look, copy and behavior — **not production code to copy**.

The task is to **recreate these designs in the target codebase's own environment** (React, Vue, SwiftUI, native, …) using its established patterns, component library and data layer. If no environment exists yet, pick the most appropriate framework and implement there. All data in the prototype is clearly marked `DEMO DATA` and is shaped to match the intended API responses (see "Data contracts").

Two files matter:
- `Visual Campus.dc.html` — the whole app: all screens, states, map, chat, wardrobe.
- `Mascot.dc.html` — the mascot component (layered inline SVG + per-state animation styles).
- `support.js` — runtime for the prototype format only. **Do not port it.**

Open `Visual Campus.dc.html` directly in a browser to click through everything. The top bar has a screen switcher (Поиск · Уточнение · Не найдено · Загрузка · Профиль · Сравнение · Ошибка · Гид · Гардероб) that exists only for review — it is not part of the product navigation.

## Fidelity
**High-fidelity.** Colors, type sizes, spacing, radii, copy (RU + EN) and interaction timings are final-intent values and are listed below. Recreate pixel-close using the codebase's own primitives. Photos, map tiles, 3D buildings and panoramas are **deliberate placeholders** (striped/grid fills with monospace captions) — real imagery comes from the API; never substitute stock photos for a specific campus.

---

## Design tokens

CSS custom properties are defined on `:root` and overridden under `[data-theme="dark"]`.

| Token | Light | Dark | Use |
|---|---|---|---|
| `--bg` | `#fbfbfa` | `#101113` | page background |
| `--surface` | `#ffffff` | `#17181b` | raised surfaces, floating controls |
| `--surface-2` | `#f4f4f2` | `#1e2024` | fills for chips, inputs, cards, map ground |
| `--ink` | `#17181a` | `#f1f1ef` | primary text, primary buttons |
| `--ink-2` | `#5c6066` | `#a0a4ab` | secondary text |
| `--ink-3` | `#8b9098` | `#71757c` | tertiary text, captions |
| `--line` | `#e6e5e2` | `#26282c` | hairlines |
| `--line-2` | `#d8d7d3` | `#32353a` | stronger hairlines |
| `--accent` | `oklch(0.55 0.14 265)` | `oklch(0.7 0.13 265)` | single accent (links, selection, campus polygon) |
| `--accent-soft` | `oklch(0.95 0.02 265)` | `oklch(0.28 0.05 265)` | accent fills |
| `--ok` | `oklch(0.52 0.11 152)` | `oklch(0.72 0.12 152)` | tier "Проверено" |
| `--ok-soft` | `oklch(0.95 0.03 152)` | `oklch(0.26 0.05 152)` | tier badge fill |
| `--warn` | `oklch(0.58 0.11 75)` | `oklch(0.78 0.12 75)` | tier "Вероятно", warnings |
| `--warn-soft` | `oklch(0.95 0.04 75)` | `oklch(0.28 0.05 75)` | warning fills |
| `--mute` | `#8b9098` | `#8b9098` | tier "Не подтверждено" |
| `--mute-soft` | `#f0efec` | `#222428` | unconfirmed badge fill |
| `--ph1` / `--ph2` | `#eceae5` / `#e4e2dc` | `#23262b` / `#1d2024` | photo/map placeholder stripes |
| `--shadow` | `0 1px 2px rgba(20,20,20,.05), 0 8px 24px rgba(20,20,20,.06)` | `0 1px 2px rgba(0,0,0,.4), 0 8px 24px rgba(0,0,0,.35)` | floating controls, popovers |

**Typography** — Instrument Sans 400/500/600 (UI) + JetBrains Mono 400/500 (numbers, IDs, dates, domains, micro-labels). Google Fonts.

| Role | Size / weight / tracking |
|---|---|
| Hero (search) | `clamp(34px,5vw,52px)` / 500 / `-0.035em` / line-height 1.05 |
| Page title (profile) | `clamp(28px,3.4vw,40px)` / 500 / `-0.035em` / 1.05 |
| Section title | 28px / 600 / `-0.02em` |
| Card title | 17–19px / 600 / `-0.01em` |
| Body | 15px / 400 / line-height 1.65–1.7, `max-width: 62–64ch`, `text-wrap: pretty` |
| Secondary body | 13–13.5px / 400 / 1.5 |
| Caption | 11.5–12.5px / 400 (`--ink-3`) |
| Micro-label (mono) | 10–11px / letter-spacing `.07–.09em`, uppercase (`--ink-3`) |
| Data value (mono) | 12–14px, `font-variant-numeric: tabular-nums` where numeric |
| Loading timer (mono) | 26px / 500 / `--accent` |

**Spacing / shape** — 8px-ish rhythm (4 · 6 · 8 · 10 · 14 · 18 · 22 · 26 · 34px). Page padding `30–36px 22px 90px`, max widths: 720px (search), 900px (disambiguation), 1100px (loading/compare/guide), 1240px (profile). Radii: pills `999px` (all buttons, chips, inputs, badges, small controls), `14–20px` (cards, media, map, modals), `2–3px` (map building footprints). Borders are used sparingly: hairline `1px solid var(--line)` only for list separators and popovers; buttons/chips/inputs are **borderless fills** (`--surface-2`) — this is the main reason the UI reads as calm rather than webby.

**Motion** — `@keyframes`: `vc-in` (opacity+6px rise, 180–400ms), `vc-pulse` (1.1–1.2s ease-in-out, active/loading), `vc-bounce` (1.6s ×3, first appearance of the guide button). Map camera transitions: 2D zoom `transform .5s cubic-bezier(.2,.7,.2,1)`, 3D orbit `transform .25s linear`. Flyover: bearing +0.8°/60ms.

---

## Screens

### 1. Search (`screen: search`)
**Purpose** — enter a university name.
**Layout** — single column, `max-width 720px`, centered, top padding `16vh`.
- H1 hero copy: «Проверенный визуальный профиль кампуса за 30 секунд».
- Sub (16.5px, `--ink-2`, `max-width 48ch`).
- Search row: pill input (`padding 17px 20px`, 17px text, fill `--surface-2`, transparent 1px border → `--accent` on focus with `--surface` fill) + primary pill button (`--ink` bg, `--bg` text, `padding 17px 26px`).
- Autocomplete popover: `top: calc(100% + 8px)`, `--surface`, `1px --line`, radius 18px, `--shadow`; rows `padding 12px 16px` with flag · name (14px/500) · city, country (13px, `--ink-3`, right-aligned); hover fill `--surface-2`. Opens as soon as the query is non-empty and matches.
- Example chips (mono micro-label «ПРИМЕРЫ» + 4 pills, fill `--surface-2`): Korea University, KAIST, Назарбаев Университет, TU Munich. Click = run the search.
- Footnote (13px, `--ink-3`, `max-width 58ch`) about supported countries and "only photos with a stated source".

**Behavior** — Enter or button submits. Exact name match → loading. Partial matches → disambiguation. No match → not-found.

### 2. Disambiguation (`screen: disamb`)
Query echo (mono, `--ink-3`), H2 «Возможно, вы имели в виду…», sub, then a responsive grid `repeat(auto-fill, minmax(min(100%,340px),1fr))`, gap 14px. Card: fill `--surface-2`, radius 18px, padding 16px, 96×96 mini-map thumb (grid placeholder + accent dot with `box-shadow: 0 0 0 5px var(--accent-soft)`), name 15px/600, flag + city/country, aliases line («Другие названия: …»), pill «Выбрать» (`--ink`). Below: text link «Ничего из этого — искать заново».

### 3. Not found (`screen: notfound`)
Circular `?` mark (38px, `--surface-2`), H2, explanation («Мы проверили 6 источников…»), 4 tips as a bulleted list (line-height 1.9), then pill input + «Повторить поиск».

### 4. Loading / streaming (`screen: loading`)
Header row: H2 + university name + right-aligned live timer (mono 26px, `--accent`, tenths of a second, ticks every 100ms).
Two columns (`repeat(auto-fit,minmax(min(100%,280px),1fr))`, gap 26px):
- **Steps** (mono micro-label «ШАГИ») — Распознавание → Поиск источников → Проверка → Удаление дублей → Категории → Описание. Each row: 18px circular marker (`1px` border, `--ok` + `✓` when done, `--accent` + `•` and `vc-pulse` while active, `--ink-3` when pending), label 13.5px, right note (mono 11px: elapsed «4.2 с» when done, «идёт» while active). Demo completion times: 4.2 / 7.0 / 11.5 / 13.5 / 16.0 / 18.4 s.
- **Sources** (mono micro-label «ИСТОЧНИКИ») — one hairline-separated row per source: Wikimedia Commons (ok, 23), OpenStreetMap (ok, 4), Flickr (unavailable), Mapillary (ok, 6), Официальный сайт (ok, 7), Веб-поиск (timeout, 2). State text is mono 10.5px, colored `--ok` / `--accent` (+`vc-pulse`) / `--warn` (timeout) / `--mute` (unavailable), label «готово · N».
Below: mono micro-label «ФОТО ПОЯВЛЯЮТСЯ ПО МЕРЕ ПРОВЕРКИ» and a masonry (`columns: 4 200px; column-gap:12px`) of placeholder tiles that appear one by one (one every 900ms after 4.2s, each `vc-in`).
At 18.4s the screen auto-advances to the profile.

### 5. Profile (`screen: profile`) — main screen
Max width 1240px.
- **Source banner** (when a source failed): pill-shaped `--warn-soft` bar, `⚠` + «Flickr недоступен — результаты могут быть неполными.» + dismiss `×`.
- **Header row** (`flex-wrap`, hairline bottom): title block (name + flag/city/country + official-site link + mono «собрано за 18.4 с»); summary stats as one mono line «42 фото · 27 проверено · 11 вероятно · 4 скрыто» (values colored `--ink` / `--ok` / `--warn` / `--mute`); guide block (see Mascot).
- **About + mini-map** (`repeat(auto-fit,minmax(min(100%,320px),1fr))`, gap 28px): 3–5 sentence description with superscript footnote links `[1][2]` and a source list under it; mini-map card (150px tall grid placeholder with dashed accent campus rectangle, radius 18px) + row «До центра города — 4.8 км». **Clicking the mini-map opens the Campus map section.**
- **Section switcher**: «Фото» · «Карта кампуса» (pill tabs, active = `--surface-2` fill).

#### 5a. Photos section
- Category tabs with counts (bottom-border active indicator `2px var(--accent)`, count in mono 11px): Все · Кампус · Общежития · Аудитории · Библиотеки · Город.
- Filter chips (multi-select, fill `--surface-2`, active `--accent-soft`/`--accent`): Общежитие · Спорт · Лаборатории · Студенческая жизнь.
- Right-aligned controls: sort segmented pills («по достоверности» / «по дате»), and a pill checkbox «Показать неподтверждённые» (off by default → only verified + likely are shown). When on, a `--surface-2` note explains the risk.
- Masonry grid `columns: 4 250px; column-gap: 14px`. Card (borderless): placeholder media (radius 16px, diagonal stripes, per-photo height 145–240px) with tier badge top-left (`icon + label + confidence%`, pill, `*-soft` fill, tier-colored text) and a mono placeholder caption bottom-left; below the media a mono row with clickable source domain and date, then the license line (unknown license renders «Лицензия неизвестна · веб-поиск» in `--mute`). Click opens the photo detail panel.
- **Honest empty state** when a category has no qualifying photos: `--surface-2` block, radius 20px — «Не удалось найти надёжные фото общежитий. Проверено 5 источников.» + «Где искали:» + pill list of the checked sources.

Tier vocabulary (color **and** icon/text, never color alone): Проверено = `--ok` + 🛡; Вероятно = `--warn` + ✓; Не подтверждено = `--mute` + ?.

#### 5b. Campus map section
Toolbar: mode pills «2D карта» · «3D вид» · «Прогулка» (active = `--ink` fill, `--bg` text), pill search «Найти здание…», pill button «Центрировать на кампусе». Optional banners: «Панорамы временно недоступны», «3D-вид не поддерживается этим устройством — показана 2D-карта».
Layer chips (hidden in walk mode): 7 building-type layers, each with a color swatch; then «Показать фото на карте», «Показать неподтверждённые», «Панорамы», «Транспорт».
Body: `flex` — map `flex: 1 1 560px`, side panel `flex: 1 1 300px; max-width: 360px` (on mobile the panel stacks under the map as a sheet).

**Loading skeleton** — map box with the campus polygon drawn first and a pulsing mono caption «Загружаем карту кампуса…» (850ms in the demo).

**2D** — box `height: clamp(360px,56vh,560px)`, radius 20px, `--surface-2`; inner surface scales with `transform-origin` at the selected building. Layers, bottom to top: 44px street grid; campus polygon as `<svg preserveAspectRatio="none">` polygon, `fill var(--accent)/0.09`, `stroke var(--accent)` `1.5px` `vector-effect: non-scaling-stroke`; panorama coverage segments (3px, `oklch(0.6 0.13 250)`, 50% opacity); building footprints (absolutely positioned rects from projected lat/lng bboxes, radius 3px, type color, opacity 0.6 inside campus / 0.28 outside, selected = opacity 0.95 + `0 0 0 2px var(--ink)`); building labels (9.5px, `--ink-2`, counter-scaled `1/zoom`, fade in at zoom ≥ 1.35); transit markers (18px rounded squares, `M`/`B`); dashed line from campus centre to the city-centre marker with «4.2 км до центра · ~15 мин на метро»; campus centre dot (12px accent + 5px `--accent-soft` ring); photo pins.
Photo pins: 26px circular thumbnails with a 2px tier-colored border and `0 1px 4px` shadow; below zoom 1.35 nearby pins collapse into clusters (30px `--surface` circle, 2px `--ink-2` border, mono count). Bottom-left attribution: «© OpenStreetMap contributors · DEMO DATA». Bottom-right `+` / `−` floating round buttons.

**3D** — same content in a `perspective: 1100px` box; surface `rotateX(tilt) rotateZ(bearing) scale(zoom*0.78)` with `transform-style: preserve-3d`. Buildings are extruded by stacking `max(2, min(12, round(height_m/4)))` copies of the footprint at `translateZ(i*3.4px)` with opacity ramping 0.42→0.92 (outside-campus buildings stay muted grey). Photo pins become flags: a 2px tier-colored stem (26px) plus a 20px round head at `translateZ(34px)`, both counter-rotated `rotateZ(-bearing) rotateX(-tilt)` so they face the camera; when `heading_deg` is known a 46px translucent view cone (`clip-path: polygon(50% 100%, 0 0, 100% 0)`) points that way. Bottom-right controls: rotate ↺ / compass `N` (rotates with bearing) / ↻, tilt ▁ / ◢ (20–72°), zoom −/+, and «Облёт кампуса» (auto-orbit). Footnote: «3D-модель построена по данным OpenStreetMap. Высота некоторых зданий приблизительная.» — with no height data: all buildings at one height + «Для этого кампуса нет данных о высоте зданий».

**Walk** — 360° panorama placeholder (vertical `--ph2 → --ph1 → --ph2` gradient plus a 78px vertical line pattern that shifts with yaw; `cursor: grab`, drag `movementX*0.4` = yaw). Top-left attribution pill, always visible: «Панорама: Mapillary · съёмка 2023-05». Top-right «Выйти из прогулки». Bottom-left round ← / → step buttons with mono «точка 1 / 8 · 24°». Bottom-right mini-map (`clamp(132px,26%,200px)` square, radius 10px): campus polygon, user dot, and a translucent accent view cone that rotates with yaw. Empty state: `--surface-2` block — «Для этого кампуса панорамы не найдены.» + «Проверено: Mapillary, Kakao Roadview» + «Вернуться к 3D-виду».

**Side panel** — default summary: Площадь `0.61 км²`, Найдено зданий `15`, До центра города `4.2 км`; then buildings grouped by type (swatch + type + count, items as hairline rows with the photo count in mono; click = select + zoom to building). Selected building: name, type swatch + «41 м · 9 эт.» (or «Высота неизвестна»), horizontal photo strip (132×92 thumbs with tier badges, click = open photo), «Данные о здании: © OpenStreetMap contributors», pills «Показать в 3D» / «Прогуляться отсюда». Selected pin: tier badge + confidence, 150px photo placeholder, Категория / Источник / Дата публикации rows, heading line, 2 evidence rows, pill «Открыть фото». Bottom of the panel: mono «ТЕСТОВЫЕ СОСТОЯНИЯ» + 4 toggles (no boundary / no heights / panoramas down / no 3D) — **prototype-only affordance, drop it in production**.

### 6. Photo detail (overlay, opens over any screen)
Right-side panel, `width: min(100%, 980px)`, full height, over `rgba(10,10,12,.62)`; `vc-in` 180ms; Escape closes, ←/→ navigate, click on the scrim closes.
- Top bar: tier badge, mono photo id, round ← → × buttons.
- Left column: 4:3 placeholder (radius 18px) + metadata rows — Источник (domain link), Автор, Лицензия, Дата публикации, Дата получения.
- Right column (`--surface-2`): mono «ИТОГОВАЯ ШКАЛА ДОСТОВЕРНОСТИ», score 30px mono in tier color + «/ 100», 6px progress bar; «Почему мы считаем, что это фото отсюда» — evidence rows (icon, label, signed weight in mono; positives `--ok`, negatives `--warn`), e.g. 📍 «Геотег в 120 м внутри границ кампуса» +28, 📁 «Находится в категории Commons „Korea University Library“» +22, 🏷 «Описание упоминает „Central Library“» +14, 👁 «AI: интерьер библиотеки (уверенность 0.91)» +11, ⚠ «Нет геотега» −18; expandable «Похожие фото, скрытые как дубликаты: 3»; «Сообщить об ошибке» → «Спасибо, отправлено».

### 7. Compare (`screen: compare`)
H2 «Сравнение университетов», then a row of two mascot cards (each in its own university's merch, `--surface-2`, radius 18px), then two columns (`repeat(auto-fit,minmax(min(100%,320px),1fr))`): name/place, map placeholder, rows (До центра, Климат, Проверенных фото, Источников доступно), and «ПРОВЕРЕННЫХ ФОТО ПО КАТЕГОРИЯМ» — per-category count, 4px accent bar, and up to 3 preview thumbs.

### 8. Global error (`screen: error`)
Centered: 44px `--warn-soft` circle with `⚠`, H2 «Сервер недоступен», explanation, pills «Повторить» / «Вернуться к поиску», mono code line `ERR_NETWORK · 503 · verification-service`.

### 9. Guide state sheet (`screen: guide`) — documentation screen
H2 «Кампи: персонаж и состояния», intro (layered construction, portable to Rive/Lottie/SVG+CSS), name note («Варианты имени: Кампи · Квадди · Ора. Выбрано — Кампи.»), then a `minmax(min(100%,210px),1fr)` grid of 7 cards: mascot rendered in that state on a `--surface-2` radius-18 stage, state name, one-line description. Clicking a card plays that state globally.

### 10. Wardrobe (`screen: wardrobe`)
H2 «Гардероб» + caption «Неофициальный мерч.» + link «Цвета: Wikidata» (or «Фирменные цвета не найдены — нейтральная палитра сервиса»). Left: category list (Верх / Голова / Аксессуар) as hairline rows. Centre: 300px mascot on a `linear-gradient(170deg, primary, secondary)` stage (radius 14px, `id="mascot-export"`). Below: option pills for the active category, then «Случайный образ» (`--ink` pill) and «Сохранить картинку». Footnote: «Тестовые цвета и надписи. Официальные логотипы и гербы не используются.»
PNG export: serialize the mascot `<svg>`, draw it on an 800×1000 canvas over a vertical primary→secondary gradient, draw the chest label and a «DEMO DATA · неофициальный мерч» line, download as `kampi-<uniId>.png`.

---

## Mascot ("Кампи")

Original flat-vector character, `viewBox 0 0 160 248`, built from **separate layers** so parts animate independently and the file ports to Rive/Lottie/SVG+CSS unchanged: ground shadow → thinking dots / change sparkles → backpack body → legs + shoes → garment (hoodie / t-shirt / varsity) → backpack straps → arms (each a `<g>` with its own `transform-origin` at the shoulder: left `47,118`, right `112,118`) → neck → scarf → head group (hair, face, ears, fringe, cheeks, eyes group, brows, mouth, cap).

Skin `#e8c6a8` (shaded `#dfb896`), hair/trousers `#3a3733`, shoes `#22201e`, ink details `#26241f`; everything else is the university's `primary` / `secondary`. Garment lettering (e.g. «KU») is HTML text overlaid at `top: 58.5%` (chest, `font-size: 0.072 × height`) and `top: 14.5%` (cap, `0.046 × height`) — the **sway/change animation sits on the wrapper**, so the lettering moves with the body. Never use official logos or crests; text abbreviations only.

States (`@keyframes` in the mascot file): `hello` (wave, `km-wave` 0.6s), `idle` (`km-sway` 3.6s + `km-blink` 5s), `thinking` (hand to chin + three pulsing dots `km-dots`), `talking` (mouth `km-talk` 0.3s + gesture `km-gesture` 1.4s), `pointing` (`km-point` 1.1s), `dont_know` (arms spread, `km-shrug` 1.6s), `changing` (`km-change` 0.55s + `km-spark`). States return to `idle` after ~3.5s (and on chat close); outfit changes play `changing` for 0.7s.

Placement: profile header — full-height mascot (140px) waving + speech bubble «Привет! Спроси меня про {university}» (`--surface-2`, radius `18 18 5 18`) + text link «Скрыть гида» (restorable via «Показать гида»). Everywhere else — a 62px round avatar button fixed at `right/bottom: 20px` (`vc-bounce` ×3 on first appearance; the mascot inside is 128px tall, absolutely positioned at `top: calc(50% - 37px)` so the head centres in the circle). Click opens the chat.

## Chat
Right drawer, `width: min(100%, 430px)`, full height, `-12px 0 40px rgba(0,0,0,.14)`, no left border; full-screen on mobile.
- Header: 82px mascot in current merch + «Кампи · гид по кампусу» + university name + round close.
- Messages: user turns are `--surface-2` bubbles right-aligned (radius `18 18 5 18`); assistant turns are plain text on the background (13.5px / 1.65) — no bubble, which keeps the panel quiet. Answer text streams in (3 characters / 26ms after a 900ms "thinking" delay); the mascot plays `thinking` → `talking` → `pointing`/`idle`/`dont_know`. Auto-scroll to the newest message.
- After streaming: optional photo strip (124×88 thumbs with tier badges → open photo detail), action pills («Показать на карте», «Открыть вкладку Общежития»), the «Проверено: …» line for unknown answers, then «Источники» with `[n] domain · title`.
- Suggestion chips in one horizontally scrolling row: «Какие общежития?», «Далеко ли до центра?», «Есть ли спортзал?», «Покажи библиотеку», «Какой климат?», «Сколько стоит обучение?» (the last one demonstrates the honest-unknown path).
- Input pill + «Спросить» (`--ink`), footnote «Гид отвечает только по источникам, найденным для этого университета.»
- Error state: `--warn-soft` block «Не удалось получить ответ. Проверьте соединение.» + «Повторить».
- Hard rule: **no invented facts.** If the collected sources do not answer, the mascot goes to `dont_know` and the answer is «В найденных источниках нет информации об этом.» + the list of checked sources.

Action semantics: `map` → open the campus map, select `building_id`, mascot `pointing`; `tab` → open the photos section on that category; `photos` → render the thumb strip.

## State model
Single component state in the prototype; in production split per feature.

- Routing/demo: `screen`, `section` (`photos | map`).
- i18n / theme: `lang` (`ru | en`), `theme` (`light | dark`, written to `data-theme` on `<html>`).
- Search: `query`, matches, `uniId`.
- Loading: `elapsedMs` (100ms tick), `revealed` (streamed photo count).
- Photos: `tab`, `activeChips`, `showUnconfirmed`, `sort` (`confidence | date`), `openIdx`, `dupOpen`, `reported`, `banner`.
- Map: `mapMode` (`2d | 3d | walk`), `mapReady`, `zoom`, `bearing`, `tilt`, `buildingId`, `pinId`, `buildingQuery`, `flyover`, `layers` (per building type), `showPins`, `showPano`, `showTransit`, `showUnconfirmedPins`, `yaw`, `panoIdx`, plus the demo flags `noPolygon`, `noHeights`, `noPano`, `no3d`.
- Guide: `guideHidden`, `chatOpen`, `chatInput`, `chatMsgs`, `mascot`, `outfit {top, head, accessory}`, `wardrobeCat`, `chatBusy`, `chatError`.

Timers to clean up on unmount: loading tick, chat streaming, flyover orbit, mascot state reset, map skeleton.

## Data contracts
The prototype's demo data mirrors these shapes exactly; wire them straight to the API.

```jsonc
// profile
{ "university": { "id","name","aliases","city","country","website","lat","lng","campus_polygon","distance_to_center_km" },
  "generated_in_ms": 18400,
  "sources_status": [{ "name","status":"ok|unavailable|timeout","count" }],
  "summary": { "text","citations":[{ "n","title","url" }] },
  "photos": [{ "id","thumb_url","full_url","category","tags":["sport","labs","dorm","student_life"],
    "confidence":0-100,"tier":"verified|likely|unconfirmed",
    "source_url","source_domain","author","license","published_at","retrieved_at",
    "evidence":[{ "type":"geo|category|text|vision|missing","label","weight" }],
    "duplicates":[{ "id","thumb_url","source_url" }] }] }

// campus map
{ "campus": { "center":{"lat","lng"}, "polygon":[[lng,lat]]|null, "area_km2",
    "city_center":{"name","lat","lng"}, "distance_to_center_km",
    "transit":[{ "type":"metro|bus","name","lat","lng","walk_min" }] },
  "buildings": [{ "id","name","type":"academic|dorm|library|sport|lab|food|other",
    "polygon","height_m"|null,"levels"|null,"photo_ids":[],"source":"OpenStreetMap" }],
  "photo_pins": [{ "photo_id","lat","lng","heading_deg"|null,"tier","confidence","thumb_url","building_id"|null }],
  "panoramas": { "provider":"mapillary|kakao|google"|null,"available":true,
    "checked_providers":["mapillary","kakao"],"start":{"lat","lng","captured_at"} } }

// mascot + chat
{ "mascot": { "outfit":{"top":"hoodie","head":"cap","accessory":"backpack"},
    "colors":{"primary":"#8B0029","secondary":"#FFFFFF","source":"wikidata|website|none","source_url"},
    "label_text":"KU" },
  "chat_message": { "role":"assistant","text":"…[1]","mascot_state":"talking|pointing|dont_know",
    "citations":[{ "n","title","url" }],
    "actions":[{ "type":"photos|map|tab","photo_ids":[],"building_id","tab":"dorms" }] } }
```

Building-type colors (map + legend + wardrobe swatches): academic `oklch(0.62 0.09 265)`, dorm `oklch(0.62 0.09 205)`, library `oklch(0.6 0.09 160)`, sport `oklch(0.66 0.09 95)`, lab `oklch(0.6 0.09 305)`, food `oklch(0.68 0.09 45)`, other `oklch(0.72 0.01 265)`.

Map projection in the prototype: a linear lng/lat → percentage mapping inside a fixed bbox. In production replace the whole map layer with **MapLibre GL JS** (2D fill/line/symbol layers + `fill-extrusion` for 3D, `pitch ≈ 58°`, bearing control, clustered symbol layer for photo pins) and the walk mode with **MapillaryJS / Kakao Roadview / Google Street View**, keeping the chrome, panel, states and attribution rules described above. Attribution must stay visible in every mode.

## Responsive
Everything except the fixed-geometry mascot canvas is fluid: `minmax(min(100%,Npx),1fr)` grids, `flex-wrap` rows, `clamp()` type and map heights, `columns: N Xpx` masonry. Breakpoint behavior is driven by content, not media queries: the map panel stacks under the map, the chat drawer becomes full-width, header controls wrap. Mobile hit targets: all pills ≥ 36px tall, map/panorama controls 32–40px round; raise to 44px if the target platform requires it.

## Accessibility
Confidence tiers always pair color with an icon and a text label. Body text meets 4.5:1 on its background in both themes; mono micro-labels are used only for non-critical metadata. The mascot SVG carries `role="img"` + `aria-label`; the guide is fully optional («Скрыть гида») and no functionality depends on it. Keyboard: Enter submits search/chat, Escape closes the photo panel, ←/→ navigate photos.

## Assets
None external. Fonts: Instrument Sans + JetBrains Mono (Google Fonts). All imagery in the prototype is a CSS stripe/grid placeholder with a monospace caption describing what belongs there; the mascot is original inline SVG built from primitives. No third-party logos, crests or stock photos are used, and real photos must always render with their source, license and tier.

## Files
- `Visual Campus.dc.html` — all screens, states, map, chat, wardrobe, demo data.
- `Mascot.dc.html` — mascot component (layers, outfits, animation states).
- `support.js` — prototype runtime only; do not port.
