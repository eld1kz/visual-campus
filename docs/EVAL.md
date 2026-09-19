# Evaluation

Evaluation date: 2026-09-19 (evening run, commit after "treat charts, rankings and infographics as non-photos").
All numbers are real sequential runs against the live public APIs from the development machine, driven
in-process through `ProfileBuild` (the same code path as `GET /profile/{id}`). Nothing is a fixture or an estimate.

## Conditions

- `FLICKR_API_KEY`, `MAPILLARY_TOKEN`, `BRAVE_SEARCH_API_KEY` and Openverse client credentials were **not** set:
  Flickr, Mapillary and web search report `skipped`, Openverse runs anonymously (page size 20, ~1 request/s).
- Local OpenCLIP ViT-B-32 was enabled with cached weights.
- The profile/source cache was cleared before every university; `lang=en`.
- `first` is the time from starting the build until the first `photo` event, `done` until the `done` event.
- "Candidates" are raw images collected from all sources before deduplication and scoring.
  "2024+" means a normalized capture date (`date_taken`) in 2024 or later; upload and index dates never count.
- Final photos are everything sent in `done.photo_ids`: `unconfirmed` photos are now included (the UI hides them
  behind a toggle), so the "final" count is much higher than in the previous evaluation, which discarded them.

## Results

| University | Candidates | 2024+ candidates | Final V / L / U | Final 2024+ (reliable) | Reliable 2020+ | First photo | Done | Partial |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Nazarbayev University (`Q2783344`) | 163 | 53 | 4 / 7 / 114 | 42 (0) | 0 | 2.04 s | 20.32 s | no |
| KAIST (`Q39949`) | 80 | 0 | 19 / 0 / 24 | 0 (0) | 3 | 1.99 s | 13.25 s | no |
| Al-Farabi KazNU (`Q427677`) | 138 | 9 | 3 / 3 / 114 | 8 (1) | 2 | 1.74 s | 14.85 s | yes |
| Korea University (`Q39997`) | 113 | 0 | 5 / 11 / 70 | 0 (0) | 3 | 1.99 s | 12.85 s | no |
| University of Cambridge (`Q35794`) | 20 | 0 | 0 / 0 / 14 | 0 (0) | 0 | 2.04 s | 8.88 s | yes |

Reliable photos by category (campus / dorms / classrooms / libraries / city): Nazarbayev 9/0/2/0/0,
KAIST 12/0/3/4/0, Al-Farabi 5/0/1/0/0, Korea University 12/0/4/0/0, Cambridge 0/0/0/0/0.

Visual check coverage (candidates OpenCLIP looked at before the deadline): Nazarbayev 57/125, KAIST 38/43,
Al-Farabi 115/120, Korea University 75/86, Cambridge 14/14. Unchecked photos are capped at `likely`
("Not visually checked (time limit)"); none of them reached a reliable tier in this run.

## Per-source candidates and errors

Format: candidates → in final list (status, time). `skipped` means the key is missing; that is a soft failure.

| Source | Nazarbayev | KAIST | Al-Farabi | Korea Univ. | Cambridge |
|---|---|---|---|---|---|
| Wikimedia Commons | 132 → 98 (ok, 7.5 s budget, partial) | 60 → 30 (ok, partial) | 132 → 114 (ok, partial) | 92 → 72 (ok, partial) | 0 (timeout, 7.5 s) |
| Openverse (anonymous) | 21 → 18 (ok, 1.3 s) | 20 → 13 (ok, 0.2 s) | 6 → 6 (ok, 3.2 s, fallback query) | 20 → 14 (ok, 0.2 s) | 20 → 14 (ok, 0.2 s) |
| Official site | 10 → 9 (ok, partial) | 0 (ok, no og:image) | 0 (error: SSL certificate verify failed) | 1 → 0 (ok) | 0 (error: HTTP 403) |
| OpenStreetMap | outline ok, buildings timed out | outline ok, buildings timed out | outline ok, buildings connect error | outline ok, buildings connect error | timeout (no outline) |
| Flickr | skipped (no key) | skipped | skipped | skipped | skipped |
| Mapillary | skipped (no token) | skipped | skipped | skipped | skipped |
| Web search (Brave) | skipped (no key) | skipped | skipped | skipped | skipped |
| Wikipedia / Wikidata | ok | ok | ok | ok | ok |

Recent candidates came only from Commons: 53 for Nazarbayev (a 2026 upload batch), 9 for Al-Farabi, none for
the other three. Openverse contributed no dated photos (it exposes no capture date).

## Openverse: what was wrong

The earlier anonymous runs returned almost nothing because of the query shape, not the API. Verified live:

- `"Nazarbayev University" campus` (quoted, as before): 1 result. `Nazarbayev University campus`: 1.
  `Nazarbayev University`: 64. `Al-Farabi Kazakh National University campus`: 0; bare name: 6.
- `page_size=50` anonymously → HTTP 401 `page_size may not exceed 20 for anonymous requests`.
- Rate-limit headers: `x-ratelimit-limit-anon_burst: 20/min`, `anon_sustained: 200/day`.

The collector now searches `<name> campus` first and falls back to the bare name when fewer than 10 results come
back, spaced by one second for anonymous access, and logs status, detail and rate-limit headers on failure.
With client credentials it uses page size 50.

## Junk spot-check after the softer vision rule

Every reliable (`verified`/`likely`) photo in the run was listed with its evidence; three suspicious titles were
opened and viewed.

- **0 reliable photos carry a negative OpenCLIP verdict.** The soft penalty did not lift any CLIP-negative photo
  into a reliable tier: every reliable photo is either CLIP-positive or inconclusive with strong metadata.
- **Junk found and fixed (not caused by the vision rule):**
  - Cambridge: five Harvard/MIT photos from Openverse were `likely` at 60 because Wikidata lists the bare alias
    "Cambridge" and "Description mentions Cambridge" earned +14. Single Latin-word aliases that are not acronyms
    are no longer search names; those photos are now `unconfirmed` at 46 and hidden by default.
  - Al-Farabi: `KazNU QS 2012-2024.jpg` is a ranking line chart that OpenCLIP labelled "campus place" (+12),
    reaching `likely`. Chart/ranking/infographic words are now treated as non-photos; it is gone from the profile.
- **Borderline but kept:** `Korea Institute of Science and Technology Information building.jpg` (KAIST, verified
  82) is a real building in the KAIST Commons category but belongs to a neighbouring institute;
  `SunPower Oasis C-7.JPG` (Nazarbayev, likely 70) shows solar trackers in front of the campus technopark sign.

## The Nazarbayev 2026 case

The 53 recent Nazarbayev candidates are a 2026 Commons upload batch of research photos: "RAs at Nazarbayev
University", "Research group meeting", "Mixing soil samples", "Robot dog", moon-over-Astana shots, and so on.
The best of them has a geotag inside the outline (+28), the official category (+22) and the name in the
description (+14) but is a photo of people; the text rule "Looks like a photo of people or an event" (−15) and
the soft CLIP penalty (−20) keep it `unconfirmed` at 59. None of the 53 is a photo of a campus place, so no 2024+
photo can honestly be `verified` for Nazarbayev from Commons alone. The unit test for the metadata-beats-soft-CLIP
rule covers the intended case; with real data the missing ingredient is a recent *place* photo, which is what the
Flickr and Mapillary keys are for.

## Timing

First photo in 1.7–2.0 s for every profile; `done` between 8.9 s and 20.3 s, all inside the 30 s budget.
The slowest profile (Nazarbayev) spends the time on 163 candidates: pHash grouping plus 57 OpenCLIP checks.

## Remaining limits

- Flickr and Mapillary are `skipped` until `FLICKR_API_KEY` and `MAPILLARY_TOKEN` are set; the collectors ask
  for 2024+ captures first and fall back to older material.
- Commons times out with zero images for the University of Cambridge (the category tree is very large), and hits
  its 7.5 s budget with partial results for the other four. The newest-first sort costs nothing (0.5–0.8 s per
  page with or without it, measured live), the harvest itself needs a smaller first pass.
- OSM building queries time out or fail for four of five campuses; the outline still arrives, so geotag evidence
  works, but building-level evidence is missing.
- Official sites: cam.ac.uk answers 403, kaznu.kz has a certificate chain the local Python cannot verify.
- Anonymous Openverse is limited to 20 results per request and ~1 request/s; it carries no capture dates.

## Run with Mapillary, Brave and the Claude visual check (2026-09-19, later)

Keys: Mapillary, Brave, Anthropic (`LLM_API_KEY`). Flickr and Openverse credentials not set.
Reliable targets raised to `campus=60,dorms=20,classrooms=25,libraries=20,city=20` (was 12/6/4/4/4: every profile
hit the campus cap of 12, and reliable photos over the cap were dropped). Claude (`claude-opus-5`, low effort; since switched to `claude-haiku-4-5`)
checks up to 80 borderline photos per profile in batches of 5, 16 requests in parallel, next to OpenCLIP.

| University | Candidates | Final V / L / U | Reliable before → after | Reliable 2024+ | Claude checked | Done |
|---|---:|---:|---:|---:|---:|---:|
| Nazarbayev University | 490 | 30 / 34 / 300 | 17 → 64 | 0 | 80 in 6.9 s | 23.5 s |
| KAIST | 416 | 65 / 5 / 68 | 20 → 70 | 56 | 80 in 8.0 s | 20.3 s |
| Al-Farabi KazNU | 198 | 3 / 58 / 115 | 12 → 61 | 1 | 20 in 7.2 s | 15.4 s |
| Korea University | 391 | 6 / 54 / 306 | 17 → 60 | 0 | 0 (credit balance too low) | 20.2 s |
| University of Cambridge | 394 | 10 / 75 / 241 | 20 → 85 | 14 | 0 (credit balance too low) | 17.8 s |

"Reliable before" is the previous run with the same keys, old targets and no working Claude check. The last two
profiles ran after the Anthropic account ran out of credits: every Claude batch returned HTTP 400 and the profile
was built on the OpenCLIP verdicts, as designed. In the earlier run where Claude worked for all five, Claude
labelled most borderline Mapillary street views "not a campus place" and lifted 8–16 photos per profile to verified.


## Final submission check — 2026-09-19, 06:41–06:48 UTC

Code under test: `d2d19be`; Python 3.12 local backend, production Next.js frontend.
155 backend tests passed (5.64 s), frontend lint and default `npm run build` passed, `pip check` passed.
Keys enabled: Brave, Mapillary, Anthropic. Local OpenCLIP enabled. No secret values are recorded here.

These are actual HTTP/SSE runs. Korea University EN was built first. An initial concurrent batch
included four universities and an incorrectly selected non-university QID; that fifth entry is excluded.
The corrected batch used five universities together (RU): SNU, KAIST, Nazarbayev, Cambridge, UCA.
Finished RU profiles were uncached; shared source/shape/model caches from earlier EN requests were warm.
Thus this is a warm-service concurrency test, not a cold-start deployment benchmark.
`First event` is the first photo event, which can be provisional, not necessarily a verified photo.
Times exclude the preceding resolve request. Counts include historic photos and hidden unconfirmed photos.

| University | Batch / language | V / L / U | Reliable campus/dorms/classrooms/libraries/city | Capture date known | Reliable taken 2024+ | Median reliable capture age | First event | Done | Source errors |
|---|---|---|---|---|---|---|---|---|---|
| Korea University | initial / EN | 19/115/285 | 86/2/16/14/16 | 41/134 reliable | 0/134 | 15.7 years | 2.40 s | 21.42 s | none |
| Al-Farabi KazNU | initial / EN | 4/120/17 | 122/1/1/0/0 | 7/124 reliable | 1/124 | 11.7 years | 3.41 s | 22.00 s | official_site: error |
| Seoul National University | corrected 5-way / RU | 25/84/69 | 86/5/10/7/1 | 16/109 reliable | 1/109 | 9.0 years | 2.83 s | 25.06 s | none |
| KAIST | corrected 5-way / RU | 100/215/160 | 295/3/14/3/0 | 228/315 reliable | 197/315 | 1.5 years | 0.90 s | 16.09 s | none |
| Nazarbayev University | corrected 5-way / RU | 24/13/345 | 12/1/21/0/3 | 10/37 reliable | 0/37 | 9.8 years | 0.77 s | 25.50 s | none |
| University of Cambridge | corrected 5-way / RU | 121/176/81 | 240/17/15/25/0 | 219/297 reliable | 219/297 | 0.2 years | 1.34 s | 21.23 s | wikimedia_commons: timeout, official_site: error |
| University of Central Asia | corrected 5-way / RU | 5/129/171 | 125/0/1/1/7 | 16/134 reliable | 5/134 | 6.8 years | 3.27 s | 30.58 s | web_search: error |

Median age uses only reliable photos with capture dates; year-only/month-only dates use January 1/the first day for this approximate age statistic. Upload dates do not count.

Resolve checks: Korea University resolved in 2.68 s; `Koera Univrsity` resolved to Korea University in 2.20 s; `Cambridge` ambiguous in 2.81 s; `zzzxqv nonexistent university 917263` returned not_found in 2.58 s. All HTTP 200. SNU and UCA IDs were obtained from `/resolve`. Every retained photo in the recorded profiles has a nonempty source URL. This does not certify that every external link remains reachable.

Browser check: production search → resolved university → live profile; displayed images, summary citations, dates, author/license/evidence detail, and city map rendered. The RU Korea browser run took 20.9 s. No full visual error-rate estimate was measured. A screenshot spot-check found a posed-person/event photo in the Korea gallery with a verified label; this is a remaining accuracy defect. Repeated thumbnails and all categories were not exhaustively manually audited.

Remaining failures: UCA took 30.58 s under five-way load (over the target); Cambridge Commons timed out in both batches; official Cambridge/Al-Farabi sources failed; a late UCA Brave gap search reported an error while preserving prior candidates. Brave was successful in the other recorded profiles. Public deployment availability was not verified without its URL.

Security check: no current credential values in the tracked working files. A current Mapillary token was found in an old backend/.env.example revision reachable only through the local backup ref `refs/original/refs/heads/main`. Neither HEAD/main nor fetched origin/main history contains its value. Do not distribute the local .git directory; rotate if the token was previously exposed. Git history was not rewritten during this check.
